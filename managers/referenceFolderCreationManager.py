import os
import re
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import gspread
from google.oauth2.service_account import Credentials
from utils.database import get_db_connection
from utils.helpers import normalize_text
from utils.llm_manager import LLMManager

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ReferenceFolderCreationManager:
    """
    Gestor para la nueva funcionalidad de búsqueda de referencias con creación de carpetas.
    
    Esta clase se encarga de:
    1. Buscar referencias en la base de datos
    2. Leer datos de Google Sheets
    3. Reformatear referencias según reglas
    4. Crear estructura de carpetas
    5. Copiar archivos relevantes
    """

    def __init__(self, 
                 google_credentials_path: str,
                 google_sheet_key: str,
                 desktop_folder_name: str = "PEDIDOS MERCADEO"):
        """
        Inicializa el gestor.

        Args:
            google_credentials_path: Ruta al archivo JSON de credenciales de servicio
            google_sheet_key: ID de la hoja de Google Sheets
            desktop_folder_name: Nombre de la carpeta a crear en el escritorio
        """
        self.google_credentials_path = google_credentials_path
        self.google_sheet_key = google_sheet_key
        self.desktop_folder_name = desktop_folder_name
        self.gc = None
        self.llm = LLMManager()
        
        # Rutas base que no deben ser descendidas
        self.root_paths = [
            "\\\\192.168.200.250\\ambientes",
            "\\\\192.168.200.250\\baño",
            "\\\\192.168.200.250\\cocina",
            "\\\\192.168.200.250\\dormitorio",
            "\\\\192.168.200.250\\mercadeo\\ANIMACIÓN 3D",
            "\\\\192.168.200.250\\mercadeo\\IMAGENES MUEBLES",
            "\\\\192.168.200.250\\rtadiseño\\AMBIENTES.3",
            "\\\\192.168.200.250\\rtadiseño\\BAÑO.3",
            "\\\\192.168.200.250\\rtadiseño\\COCINA.3",
            "\\\\192.168.200.250\\rtadiseño\\DORMITORIO.3",
            "\\\\192.168.200.250\\rtadiseño\\MERCADEO.3\\IMÁGENES MUEBLES",
            "\\\\192.168.200.250\\rtadiseño\\MERCADEO.3\\ANIMACIONES"
        ]
        
        logger.info("Inicializando ReferenceFolderCreationManager...")

    def search_in_database_only(self, references: List[str]) -> Dict[str, List[str]]:
        """
        Busca las referencias únicamente en la base de datos local.
        
        Args:
            references: Lista de referencias a buscar

        Returns:
            Dict con las rutas encontradas por referencia
        """
        logger.info(f"Iniciando búsqueda en base de datos para {len(references)} referencias")
        results = {}
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            for ref in references:
                logger.debug(f"Buscando en BD: {ref}")
                normalized_ref = normalize_text(ref)
                
                query = """
                    SELECT path 
                    FROM folder_references
                    WHERE folder_name LIKE ? 
                      AND is_deleted = 0
                    ORDER BY 
                        CASE 
                            WHEN LOWER(path) LIKE '%instructivo%' THEN 1
                            ELSE 2
                        END,
                        path
                """
                
                cursor.execute(query, (f"%{normalized_ref}%",))
                paths = cursor.fetchall()
                
                if paths:
                    results[ref] = [path[0] for path in paths]
                    logger.info(f"Encontradas {len(paths)} rutas para {ref}")
                else:
                    results[ref] = []
                    logger.warning(f"No se encontraron rutas para {ref}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error en búsqueda de base de datos: {str(e)}"
            logger.error(error_msg)
            raise
            
        finally:
            if 'conn' in locals():
                conn.close()

    def fetch_and_format_with_sheets(self, references: List[str]) -> List[dict]:
        """
        Obtiene información de Google Sheets y formatea las referencias.
        
        Args:
            references: Lista de referencias a procesar

        Returns:
            Lista de diccionarios con la información formateada
        """
        if not self.gc:
            self._authenticate_google_sheets()
            
        logger.info(f"Procesando {len(references)} referencias en Google Sheets")
        formatted_refs = []
        
        for ref in references:
            try:
                # Obtener datos de Google Sheets
                code_3_letters, consecutivo, description, category = self._fetch_reference_data(ref)
                
                # Formatear nombre
                final_name = self._format_reference_name(
                    code_3_letters=code_3_letters,
                    consecutivo=consecutivo,
                    description=description
                )
                
                formatted_refs.append({
                    'original': ref,
                    'code': code_3_letters,
                    'consecutivo': consecutivo,
                    'category': category,
                    'nombre_formateado': final_name
                })
                
                logger.info(f"Referencia {ref} formateada como: {final_name}")
                
            except Exception as e:
                logger.error(f"Error procesando {ref} en Sheets: {str(e)}")
                formatted_refs.append({
                    'original': ref,
                    'error': str(e)
                })
                
        return formatted_refs

    def create_folders_and_copy_files(self, 
                                    formatted_refs: List[dict], 
                                    db_results: Dict[str, List[str]]) -> Dict:
        """
        Crea las carpetas y copia los archivos usando la información combinada.
        
        Args:
            formatted_refs: Lista de referencias formateadas
            db_results: Diccionario con rutas de la base de datos
        
        Returns:
            Dict con resultados del proceso
        """
        results = {
            "processed": [],
            "errors": []
        }
        
        for ref_data in formatted_refs:
            try:
                if 'error' in ref_data:
                    results["errors"].append(f"Error previo con {ref_data['original']}: {ref_data['error']}")
                    continue
                    
                original_ref = ref_data['original']
                final_name = ref_data['nombre_formateado']
                
                # Obtener ruta de la base de datos
                source_paths = db_results.get(original_ref, [])
                if not source_paths:
                    results["errors"].append(f"No hay rutas en BD para {original_ref}")
                    continue
                
                # Usar la primera ruta (ya ordenada por preferencia de 'instructivo')
                source_folder = source_paths[0]
                
                # Determinar la categoría basada en la ruta origen
                category = self._determine_category_from_path(source_folder)
                logger.info(f"Categoría determinada para {original_ref}: {category}")
                
                # Crear estructura de carpetas
                target_folder = self._create_folder_structure(
                    reference_name=final_name,
                    category=category,
                    source_path=source_folder
                )
                
                # Copiar archivos
                copy_results = self._copy_files(
                    source_folder=source_folder,
                    target_folder=target_folder
                )
                
                results["processed"].append({
                    "original": original_ref,
                    "final_name": final_name,
                    "target_folder": str(target_folder),
                    "copied_files": copy_results
                })
                
            except Exception as e:
                results["errors"].append(f"Error procesando {original_ref}: {str(e)}")
                
        return results

    def _sanitize_folder_name(self, name: str) -> str:
        """
        Sanitiza el nombre de una carpeta para que sea válido en Windows.
        
        Args:
            name: Nombre original de la carpeta

        Returns:
            Nombre sanitizado
        """
        # 1. Reemplazar caracteres que Windows interpreta como separadores
        name = name.replace("\\", "-").replace("/", "-")
        
        # 2. Eliminar otros caracteres ilegales en Windows
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            name = name.replace(char, "")
            
        # 3. Reemplazar secuencias problemáticas
        name = name.replace(" + ", " mas ")  # Opcional: mantener el "+" como "mas"
        
        # 4. Eliminar espacios al inicio y final
        name = name.strip()
        
        # 5. Asegurar que no termine en punto o espacio
        name = name.rstrip(". ")
        
        return name

    def _create_folder_structure(self, 
                               reference_name: str, 
                               category: str, 
                               source_path: str) -> Path:
        """
        Crea la estructura de carpetas necesaria.
        
        Args:
            reference_name: Nombre formateado de la referencia
            category: Categoría del mueble
            source_path: Ruta origen en la NAS

        Returns:
            Path de la carpeta final creada
        """
        logger.debug(f"Creando estructura de carpetas para: {reference_name}")
        logger.debug(f"Categoría: {category}")
        logger.debug(f"Ruta origen: {source_path}")
        
        try:
            # 1. Obtener ruta del escritorio
            desktop = Path.home() / "Desktop"
            base_folder = desktop / self.desktop_folder_name
            
            # 2. Ajustar categoría
            category = category.strip().upper()
            
            # Si contiene "escritorio" en la referencia, forzar OFICINA
            if "escritorio" in reference_name.lower():
                category = "OFICINA"
                logger.info("Categoría forzada a OFICINA por contener 'escritorio'")
            else:
                # Convertir plural a singular
                if category.endswith('S'):
                    category = category[:-1]
                    logger.debug(f"Categoría convertida a singular: {category}")
            
            # 3. Crear carpeta base y categoría
            cat_folder = base_folder / category
            cat_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Carpeta de categoría creada: {cat_folder}")
            
            # 4. Analizar ruta origen para replicar estructura intermedia
            source_parts = Path(source_path).parts
            
            # Encontrar el índice después de la categoría en la ruta origen
            category_index = -1
            for i, part in enumerate(source_parts):
                if any(cat.lower() in part.lower() for cat in ['ambiente', 'baño', 'cocina', 'dormitorio', 'oficina']):
                    category_index = i
                    break
            
            if category_index >= 0 and category_index + 1 < len(source_parts):
                # Tomar partes intermedias hasta encontrar 'NUBE' o llegar al final
                current_folder = cat_folder
                for part in source_parts[category_index + 1:]:
                    if part.upper() == 'NUBE':
                        break
                    # Sanitizar y crear subcarpeta intermedia
                    safe_part = self._sanitize_folder_name(part)
                    current_folder = current_folder / safe_part
                    current_folder.mkdir(exist_ok=True)
                    logger.debug(f"Creada subcarpeta intermedia: {safe_part}")
            else:
                current_folder = cat_folder
                logger.warning("No se encontró punto de referencia para estructura intermedia")
            
            # 5. Crear carpeta final con el nombre sanitizado de la referencia
            safe_reference_name = self._sanitize_folder_name(reference_name)
            final_folder = current_folder / safe_reference_name
            final_folder.mkdir(exist_ok=True)
            logger.info(f"Carpeta final creada: {final_folder}")
            
            return final_folder
            
        except Exception as e:
            error_msg = f"Error creando estructura de carpetas: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _authenticate_google_sheets(self) -> None:
        """Autentica con Google Sheets."""
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            credentials = Credentials.from_service_account_file(
                self.google_credentials_path, 
                scopes=scopes
            )
            self.gc = gspread.authorize(credentials)
            logger.info("Autenticación con Google Sheets exitosa")
        except Exception as e:
            logger.error(f"Error en autenticación con Google Sheets: {e}")
            raise

    def _fetch_reference_data(self, reference: str) -> Tuple[str, str, str, str]:
        """
        Obtiene datos de la referencia desde Google Sheets.
        
        Args:
            reference: Referencia a buscar (ej: 'MBT 11306')

        Returns:
            Tupla (code_3_letters, consecutivo, description, category)
            
        Raises:
            ValueError: Si no se encuentra la referencia o hay error en el formato
        """
        logger.debug(f"Buscando datos para referencia: {reference}")
        
        # Extraer parte numérica (consecutivo)
        numeric_match = re.search(r"\d{3,5}", reference)
        if not numeric_match:
            error_msg = f"No se encontró parte numérica en la referencia: {reference}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        numeric_str = numeric_match.group(0)
        logger.debug(f"Parte numérica extraída: {numeric_str}")
        
        try:
            # Abrir la hoja de cálculo
            sheet = self.gc.open_by_key(self.google_sheet_key)
            worksheet = sheet.worksheet('REFERENCIAS 1-2-3-4')  # Nombre específico de la hoja
            logger.info(f"Hoja de cálculo abierta: {sheet.title}")
            logger.info(f"Hoja de trabajo seleccionada: {worksheet.title}")
            
            # Obtener todos los valores de una vez
            all_values = worksheet.get_all_values()
            logger.info(f"Total de filas obtenidas: {len(all_values)}")
            
            # Buscar la coincidencia
            found_row = None
            found_index = -1
            
            for i, row in enumerate(all_values, 1):  # Empezar desde 1 para mantener índices consistentes
                if len(row) >= 5:  # Asegurar que hay suficientes columnas
                    current_value = row[4].strip()  # Columna E (índice 4)
                    logger.debug(f"Fila {i:4d} | Comparando: '{current_value}' con '{numeric_str}'")
                    if current_value == numeric_str:
                        found_row = row
                        found_index = i
                        break
            
            if found_row:
                logger.info(f"¡Coincidencia encontrada en fila {found_index}!")
                logger.info("Contenido de la fila encontrada:")
                for col_idx, value in enumerate(found_row):
                    logger.info(f"  Índice {col_idx:2d} | Columna {chr(65+col_idx)} | Valor: {value}")
                
                try:
                    # Extraer valores relevantes
                    code_3_letters = found_row[3].strip()  # Columna D (índice 3)
                    consecutivo = found_row[4].strip()     # Columna E (índice 4)
                    description = found_row[5].strip()     # Columna F (índice 5)
                    category = found_row[7].strip()        # Columna H (índice 7)
                    
                    logger.info(f"\nDatos extraídos para {reference}:")
                    logger.info(f"  - Código (col D, índice 3): {code_3_letters}")
                    logger.info(f"  - Consecutivo (col E, índice 4): {consecutivo}")
                    logger.info(f"  - Descripción (col F, índice 5): {description}")
                    logger.info(f"  - Categoría (col H, índice 7): {category}")
                    
                    return code_3_letters, consecutivo, description, category
                except IndexError as e:
                    error_msg = f"Error al procesar la fila encontrada: {str(e)}. La fila no tiene el formato esperado."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            # Si llegamos aquí, no se encontró la referencia
            error_msg = f"No se encontró el consecutivo {numeric_str} en la hoja"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        except Exception as e:
            if "Error al procesar la fila encontrada" in str(e):
                raise  # Re-lanzar el error específico de procesamiento
            error_msg = f"Error al buscar datos en Google Sheets: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _format_reference_name(self, 
                             code_3_letters: str,
                             consecutivo: str,
                             description: str) -> str:
        """
        Formatea el nombre de la referencia usando el LLM.
        
        Args:
            code_3_letters: Código de 3 letras (ej: 'CDB')
            consecutivo: Número consecutivo (ej: '9493')
            description: Descripción original del mueble

        Returns:
            Nombre formateado (ej: 'CDB 9493 - CLOSET BARILOCHE ECO 150 (DUNA-BLANCO + BLANCO MQZ)')
        """
        logger.debug(f"Formateando descripción con LLM: {description}")
        
        try:
            # Usar el LLM para formatear el nombre
            formatted_name = self.llm.format_reference_name(
                code=code_3_letters,
                number=consecutivo,
                description=description
            )
            
            logger.info(f"Nombre formateado por LLM: {formatted_name}")
            return formatted_name
            
        except Exception as e:
            logger.error(f"Error al formatear con LLM: {str(e)}")
            # Si falla el LLM, usar el método anterior como fallback
            logger.warning("Usando método de formateo fallback")
            return self._format_reference_name_fallback(
                code_3_letters, 
                consecutivo, 
                description
            )
            
    def _format_reference_name_fallback(self, 
                                      code_3_letters: str,
                                      consecutivo: str,
                                      description: str) -> str:
        """
        Método de respaldo para formatear nombres cuando el LLM falla.
        Usa el método anterior basado en expresiones regulares.
        """
        # Aquí va el código anterior del método _format_reference_name
        text = description.strip()
        
        # Eliminar patrones no deseados
        text = re.sub(r"\(\d+C\)", "", text)
        text = re.sub(r"\d+(?:[.,]\d+)?X\d+(?:[.,]\d+)?X\d+(?:[.,]\d+)?\s*CM", "", text)
        text = re.sub(r"_CAJA\s*\d+/\d+", "", text, flags=re.IGNORECASE)
        
        # Eliminar palabras específicas
        palabras_eliminar = ["HD", "IMAGEN", "DIMENSIONES"]
        for palabra in palabras_eliminar:
            text = re.sub(rf"\b{palabra}\b", "", text, flags=re.IGNORECASE)
        
        # Formatear colores y materiales
        match = re.search(r'(.*?)(?:\s*\((.*?)\))?$', text)
        if match:
            nombre_mueble = match.group(1).strip()
            colores = match.group(2).strip() if match.group(2) else ""
            
            if colores:
                colores = re.sub(r'\s+mas\s+', ' + ', colores, flags=re.IGNORECASE)
                colores = colores.replace("MARQUEZ", "MQZ")
                colores = colores.replace("MARQUÉZ", "MQZ")
                colores = re.sub(r'\s*\+\s*', ' + ', colores)
                text = f"{nombre_mueble} ({colores})"
            else:
                text = nombre_mueble
        
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        
        final_name = f"{code_3_letters} {consecutivo} - {text}"
        logger.info(f"Nombre formateado (fallback): {final_name}")
        return final_name

    def _find_preferred_folder(self, reference: str) -> str:
        """
        Busca la carpeta preferida en la base de datos.
        Prioriza carpetas que contengan 'Instructivo' en su nombre.
        
        Args:
            reference: Referencia a buscar (ej: 'MBT 11306')

        Returns:
            Ruta de la carpeta encontrada

        Raises:
            ValueError: Si no se encuentra ninguna carpeta
        """
        logger.debug(f"Buscando carpeta preferida para: {reference}")
        
        # Normalizar referencia para búsqueda
        search_ref = normalize_text(reference)
        logger.debug(f"Referencia normalizada: {search_ref}")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Buscar todas las carpetas que contengan la referencia
            query = """
                SELECT path 
                FROM folder_references
                WHERE folder_name LIKE ? 
                  AND is_deleted = 0
                ORDER BY 
                    CASE 
                        WHEN LOWER(path) LIKE '%instructivo%' THEN 1
                        ELSE 2
                    END,
                    path
            """
            
            cursor.execute(query, (f"%{search_ref}%",))
            paths = cursor.fetchall()
            
            if not paths:
                error_msg = f"No se encontraron carpetas para la referencia: {reference}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Tomar el primer resultado (ya ordenado por preferencia)
            chosen_path = paths[0][0]
            
            # Verificar si es una carpeta de instructivo
            is_instructivo = "instructivo" in chosen_path.lower()
            log_msg = f"Carpeta encontrada: {chosen_path}"
            if is_instructivo:
                log_msg += " (contiene 'Instructivo')"
            logger.info(log_msg)
            
            return chosen_path
            
        except Exception as e:
            error_msg = f"Error buscando carpeta en base de datos: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        finally:
            if 'conn' in locals():
                conn.close()

    def _is_root_path(self, path: str) -> bool:
        """
        Verifica si una ruta es exactamente una de las rutas base.
        
        Args:
            path: Ruta a verificar
            
        Returns:
            bool: True si es una ruta base exacta, False en caso contrario
        """
        # Normalizar la ruta para comparación
        normalized_path = os.path.normpath(path).lower()
        
        # Verificar si la ruta normalizada es exactamente igual a alguna ruta base
        for root_path in self.root_paths:
            normalized_root = os.path.normpath(root_path).lower()
            if normalized_path == normalized_root:
                logger.info(f"Ruta {path} es una ruta base")
                return True
        return False

    def _get_all_possible_paths(self, start_path: str) -> List[Dict[str, str]]:
        """
        Obtiene TODAS las rutas posibles desde la carpeta padre.
        
        Args:
            start_path: Ruta inicial (carpeta padre) desde donde comenzar la búsqueda
            
        Returns:
            List[Dict[str, str]]: Lista de diccionarios con información de cada ruta
        """
        paths_info = []
        logger.info(f"Obteniendo todas las rutas desde: {start_path}")
        
        try:
            # Primero, obtener la lista completa de directorios
            all_dirs = []
            for root, dirs, _ in os.walk(start_path):
                # Si es una ruta base exacta, no explorar sus subdirectorios
                if self._is_root_path(root):
                    continue
                    
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    # Solo excluir si es una ruta base exacta
                    if not self._is_root_path(full_path):
                        all_dirs.append((full_path, dir_name, root))
            
            # Procesar cada directorio encontrado
            for full_path, dir_name, parent in all_dirs:
                # Crear diccionario con información relevante de la ruta
                path_info = {
                    'path': full_path,
                    'name': dir_name,
                    'is_editable': 'editable' in dir_name.lower() or 'editables' in dir_name.lower(),
                    'is_nube': dir_name.lower() == 'nube',
                    'parent': parent,
                    'relative_to_start': os.path.relpath(full_path, start_path),
                    'depth': len(os.path.relpath(full_path, start_path).split(os.sep))
                }
                
                # Registrar información detallada
                logger.info(f"Carpeta encontrada: {full_path}")
                logger.info(f"  Nombre: {dir_name}")
                logger.info(f"  Es EDITABLE: {path_info['is_editable']}")
                logger.info(f"  Es NUBE: {path_info['is_nube']}")
                logger.info(f"  Ruta relativa: {path_info['relative_to_start']}")
                logger.info(f"  Profundidad: {path_info['depth']}")
                
                paths_info.append(path_info)
            
            # Ordenar las rutas por profundidad para mejor visualización
            paths_info.sort(key=lambda x: (x['depth'], x['path']))
            
            # Registrar resumen
            logger.info(f"Total de rutas encontradas: {len(paths_info)}")
            logger.info("Resumen de rutas:")
            for path_info in paths_info:
                logger.info(f"- {path_info['path']}")
            
            return paths_info
            
        except Exception as e:
            logger.error(f"Error obteniendo rutas desde {start_path}: {str(e)}")
            return []

    def _find_base_folder(self, source_folder: str) -> str:
        """
        Encuentra la carpeta base del proyecto.
        Retrocede en la estructura hasta encontrar una carpeta que:
        1. No sea una carpeta de sistema (NUBE, EDITABLES, etc.)
        2. No sea una ruta base de la NAS
        3. Contenga subcarpetas con archivos del proyecto
        
        Args:
            source_folder: Carpeta origen desde donde iniciar la búsqueda
            
        Returns:
            str: Ruta de la carpeta base identificada
        """
        current_path = source_folder
        system_folders = {'nube', 'editables', 'editable', 'hojas de diseño', 'planos'}
        
        while current_path != os.path.dirname(current_path):  # Mientras no lleguemos a la raíz
            folder_name = os.path.basename(current_path).lower()
            parent_path = os.path.dirname(current_path)
            
            # Si es una ruta base de la NAS, detenerse en el nivel anterior
            if self._is_root_path(current_path):
                return parent_path
                
            # Si es una carpeta de sistema, subir un nivel
            if folder_name in system_folders:
                current_path = parent_path
                continue
                
            try:
                # Verificar si esta carpeta tiene una estructura de proyecto válida
                has_system_folder = False
                for item in os.listdir(current_path):
                    item_lower = item.lower()
                    if item_lower in system_folders:
                        has_system_folder = True
                        break
                
                # Si encontramos una carpeta que contiene subcarpetas de sistema,
                # esta es nuestra carpeta base
                if has_system_folder:
                    return current_path
                    
            except Exception as e:
                logger.error(f"Error explorando {current_path}: {str(e)}")
            
            current_path = parent_path
            
        return source_folder  # Si no encontramos nada, devolver la carpeta original

    def _find_rhino_file(self, source_folder: str) -> Optional[str]:
        """
        Busca el archivo Rhino siguiendo la lógica especificada.
        
        Args:
            source_folder: Carpeta origen donde iniciar la búsqueda
            
        Returns:
            Optional[str]: Ruta del archivo Rhino encontrado o None si no se encuentra
        """
        logger.info(f"Buscando archivo Rhino para: {source_folder}")
        
        try:
            # 1. Encontrar la carpeta base del proyecto
            base_path = self._find_base_folder(source_folder)
            logger.info(f"Carpeta base identificada: {base_path}")
            
            # 2. Obtener todas las rutas posibles desde la carpeta base
            all_paths = self._get_all_possible_paths(base_path)
            
            # Registrar todas las rutas encontradas
            logger.info("Rutas encontradas:")
            for path_info in all_paths:
                logger.info(f"- {path_info['path']}")
                logger.info(f"  Profundidad: {path_info['depth']}")
                logger.info(f"  Es EDITABLE: {path_info['is_editable']}")
                logger.info(f"  Es NUBE: {path_info['is_nube']}")
                logger.info(f"  Ruta relativa: {path_info['relative_to_start']}")
            
            # 3. Usar el LLM para determinar la mejor ruta
            search_path_response, _ = self.llm.determine_rhino_search_strategy(
                source_folder=source_folder,
                reference=os.path.basename(source_folder),
                available_paths=all_paths
            )
            
            search_path = search_path_response.strip()
            logger.info(f"LLM sugiere buscar en: {search_path}")
            
            if not os.path.exists(search_path):
                logger.warning(f"La ruta sugerida no existe: {search_path}")
                return None
                
            # 4. Buscar archivos Rhino en la ruta sugerida
            rhino_files = []
            for root, _, files in os.walk(search_path):
                for file in files:
                    if file.lower().endswith('.3dm'):
                        rhino_files.append(os.path.join(root, file))
                        logger.info(f"Archivo Rhino encontrado: {os.path.join(root, file)}")
            
            if rhino_files:
                # 5. Usar el LLM para seleccionar el mejor archivo
                response, _ = self.llm.suggest_rhino_file(
                    files=rhino_files,
                    reference=os.path.basename(source_folder),
                    source_folder=source_folder
                )
                
                # Verificar que la respuesta sea una ruta válida
                if response and os.path.exists(response.strip()):
                    chosen_file = response.strip()
                    logger.info(f"LLM sugirió el archivo: {chosen_file}")
                    return chosen_file
                else:
                    # Si el LLM no pudo decidir, usar la lógica de prioridad por versión
                    rhino_files.sort(key=lambda x: (
                        0 if 'rhino5' in x.lower() or 'r5' in x.lower() else
                        1 if 'rhino4' in x.lower() or 'r4' in x.lower() else
                        2 if 'rhino6' in x.lower() or 'r6' in x.lower() else
                        3 if 'rhino7' in x.lower() or 'r7' in x.lower() else 4,
                        # Segundo criterio: priorizar archivos en carpetas EDITABLE
                        0 if any(ed in os.path.dirname(x).lower() for ed in ['editable', 'editables']) else 1,
                        # Tercer criterio: profundidad de la ruta (menos es mejor)
                        len(os.path.normpath(x).split(os.sep))
                    ))
                    chosen_file = rhino_files[0]
                    logger.info(f"Seleccionado archivo por prioridad de versión: {chosen_file}")
                    return chosen_file
            
            logger.warning(f"No se encontraron archivos Rhino en {search_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error buscando archivo Rhino: {str(e)}")
            return None

    def _copy_files(self, source_folder: str, target_folder: Path) -> Dict:
        """
        Copia archivos relevantes (PDF, Rhino) a la carpeta destino.
        
        Args:
            source_folder: Carpeta origen en la NAS
            target_folder: Carpeta destino local

        Returns:
            Dict con información de los archivos copiados
        """
        logger.debug(f"Buscando archivos para copiar desde: {source_folder}")
        logger.debug(f"Carpeta destino: {target_folder}")
        
        result = {
            "pdf": None,
            "rhino": None,
            "errors": []
        }
        
        try:
            # 1. Buscar y copiar PDF
            pdf_candidates = []
            for root, _, files in os.walk(source_folder):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_candidates.append(os.path.join(root, file))
            
            if pdf_candidates:
                # Priorizar PDFs que contengan "instructivo"
                instructivo_pdfs = [p for p in pdf_candidates 
                                  if "instructivo" in p.lower()]
                
                if instructivo_pdfs:
                    pdf_to_copy = instructivo_pdfs[0]
                    logger.info(f"Seleccionado PDF con 'instructivo': {pdf_to_copy}")
                else:
                    # Tomar el más reciente
                    pdf_to_copy = max(pdf_candidates, key=os.path.getmtime)
                    logger.info(f"Seleccionado PDF más reciente: {pdf_to_copy}")
                
                # Copiar PDF
                shutil.copy2(pdf_to_copy, target_folder)
                result["pdf"] = os.path.basename(pdf_to_copy)
                logger.info(f"PDF copiado: {result['pdf']}")
            else:
                logger.warning("No se encontraron archivos PDF")
                result["errors"].append("No se encontraron archivos PDF")
            
            # 2. Buscar y copiar archivo Rhino
            try:
                rhino_file = self._find_rhino_file(source_folder)
                if rhino_file:
                    # Copiar archivo Rhino
                    shutil.copy2(rhino_file, target_folder)
                    result["rhino"] = os.path.basename(rhino_file)
                    logger.info(f"Archivo Rhino copiado: {result['rhino']}")
                else:
                    logger.warning("No se encontraron archivos Rhino")
                    result["errors"].append("No se encontraron archivos Rhino")
                    
            except Exception as e:
                error_msg = f"Error buscando archivo Rhino: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
            
            return result
            
        except Exception as e:
            error_msg = f"Error copiando archivos: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            return result

    def _determine_category_from_path(self, path: str) -> str:
        """
        Determina la categoría basada en la ruta del archivo.
        
        Args:
            path: Ruta completa del archivo/carpeta
            
        Returns:
            str: Categoría determinada
        """
        path_lower = path.lower()
        
        # Mapeo de palabras clave a categorías
        category_mapping = {
            'ambiente': 'AMBIENTE',
            'baño': 'BAÑO',
            'cocina': 'COCINA',
            'dormitorio': 'DORMITORIO',
            'oficina': 'OFICINA',
            'escritorio': 'OFICINA'  # Caso especial para escritorios
        }
        
        # Buscar palabras clave en la ruta
        for keyword, category in category_mapping.items():
            if keyword in path_lower:
                logger.info(f"Categoría {category} determinada por palabra clave '{keyword}' en ruta")
                return category
        
        # Si no se encuentra ninguna categoría específica, usar AMBIENTE como predeterminado
        logger.warning(f"No se pudo determinar categoría específica para ruta: {path}")
        return "AMBIENTE" 