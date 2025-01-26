import os
import re
import shutil
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable

import gspread
from google.oauth2.service_account import Credentials
from utils.database import get_db_connection
from utils.helpers import normalize_text, extract_reference
from utils.llm_manager import LLMManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('llm_prompts.log', mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ReferenceFolderCreationManager:
    """
    Gestor para la nueva funcionalidad de búsqueda de referencias con creación de carpetas.
    
    Esta clase se encarga de:
    1. Leer datos de Google Sheets
    2. Reformatear referencias según reglas
    3. Crear estructura de carpetas
    4. Copiar archivos relevantes
    """

    def __init__(self, 
                 google_credentials_path: str,
                 google_sheet_key: str,
                 desktop_folder_name: str = "PEDIDOS MERCADEO",
                 controller=None):
        """
        Inicializa el gestor de creación de carpetas.
        
        Args:
            google_credentials_path: Ruta al archivo de credenciales de Google
            google_sheet_key: Clave de la hoja de Google Sheets
            desktop_folder_name: Nombre de la carpeta en el escritorio
            controller: Referencia al controlador principal
        """
        logger.info("Inicializando ReferenceFolderCreationManager...")
        
        # Validar parámetros
        if not google_credentials_path or not os.path.exists(google_credentials_path):
            raise ValueError("Ruta de credenciales de Google inválida")
            
        if not google_sheet_key:
            raise ValueError("Clave de Google Sheets no proporcionada")
            
        # Guardar configuración
        self.google_credentials_path = google_credentials_path
        self.google_sheet_key = google_sheet_key
        self.desktop_folder_name = desktop_folder_name
        self.controller = controller
        
        # Inicializar LLM
        self.llm = LLMManager()
        
        # Inicializar Google Client
        self.gc = None
        try:
            self._authenticate_google_sheets()
        except Exception as e:
            logger.error(f"Error inicial al autenticar con Google Sheets: {e}")
            
        # Estado del procesamiento
        self._processing_state = {}
        
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
        
        logger.info("ReferenceFolderCreationManager inicializado correctamente\n")

    def fetch_and_format_with_sheets(self, references: List[str]) -> List[dict]:
        """
        Obtiene información de Google Sheets y formatea las referencias.
        
        Args:
            references: Lista de referencias a procesar

        Returns:
            Lista de diccionarios con la información formateada
        """
        logger.info("=== INICIO BÚSQUEDA EN GOOGLE SHEETS ===")
        
        # Verificar que tenemos credenciales configuradas
        if not self.google_credentials_path or not os.path.exists(self.google_credentials_path):
            error_msg = "No se han configurado las credenciales de Google Sheets o el archivo no existe"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not self.gc:
            logger.info("Iniciando autenticación con Google Sheets")
            try:
                self._authenticate_google_sheets()
            except Exception as e:
                error_msg = f"Error al autenticar con Google Sheets: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
        formatted_refs = []
        
        try:
            sheet = self.gc.open_by_key(self.google_sheet_key)
            worksheet = sheet.worksheet('REFERENCIAS 1-2-3-4')
            all_values = worksheet.get_all_values()
            logger.info(f"Datos obtenidos: {len(all_values)} filas")
            
            for ref in references:
                logger.info(f"Procesando referencia: {ref}")
                try:
                    numeric_match = re.search(r"\d{3,5}", ref)
                    if not numeric_match:
                        logger.error(f"✗ No se encontró parte numérica")
                        formatted_refs.append({
                            'original': ref,
                            'error': "No se encontró parte numérica en la referencia"
                        })
                        continue
                        
                    numeric_str = numeric_match.group(0)
                    
                    found_row = None
                    found_index = -1
                    
                    for i, row in enumerate(all_values, 1):
                        if len(row) >= 5 and row[4].strip() == numeric_str:
                            found_row = row
                            found_index = i
                            break
                    
                    if found_row:
                        logger.info(f"✓ Coincidencia encontrada")
                        
                        try:
                            code_3_letters = found_row[3].strip()
                            consecutivo = found_row[4].strip()
                            description = found_row[5].strip()
                            category = found_row[7].strip()
                            
                            logger.info("Datos extraídos correctamente")
                            
                            formatted_name = self._format_reference_name(
                                code_3_letters=code_3_letters,
                                consecutivo=consecutivo,
                                description=description
                            )
                            
                            formatted_refs.append({
                                'original': ref,
                                'code': code_3_letters,
                                'consecutivo': consecutivo,
                                'category': category,
                                'nombre_formateado': formatted_name
                            })
                            
                        except Exception as e:
                            logger.error(f"✗ Error procesando datos: {str(e)}")
                            formatted_refs.append({
                                'original': ref,
                                'error': f"Error al procesar la fila: {str(e)}"
                            })
                    else:
                        logger.warning(f"✗ No se encontró el consecutivo {numeric_str}")
                        formatted_refs.append({
                            'original': ref,
                            'error': f"No se encontró el consecutivo {numeric_str}"
                        })
                        
                except Exception as e:
                    logger.error(f"✗ Error general: {str(e)}")
                    formatted_refs.append({
                        'original': ref,
                        'error': str(e)
                    })
            
            logger.info("=== FIN BÚSQUEDA EN GOOGLE SHEETS ===\n")
            return formatted_refs
            
        except Exception as e:
            error_msg = f"Error al buscar datos en Google Sheets: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def create_folders_and_copy_files(self, formatted_refs: List[dict], db_results: Dict[str, List[str]]) -> Dict:
        """
        Crea las carpetas y copia los archivos usando la información combinada.
        Procesa una referencia a la vez, esperando selección de usuario si es necesario.
        
        Args:
            formatted_refs: Lista de referencias formateadas
            db_results: Diccionario con rutas de la base de datos
        
        Returns:
            Dict con resultados del proceso y estado de procesamiento
        """
        logger.info("=== INICIO PROCESO DE CREACIÓN DE CARPETAS ===")
        logger.info(f"Referencias a procesar: {[ref.get('original') for ref in formatted_refs]}")
        logger.info(f"Resultados de BD disponibles: {list(db_results.keys())}")
        
        # Obtener el estado actual del procesamiento
        current_state = getattr(self, '_processing_state', {})
        if not current_state:
            # Inicializar estado si es la primera vez
            current_state = {
                "processed": [],
                "errors": [],
                "pending_files": {},
                "current_index": 0,
                "refs_to_process": formatted_refs,
                "db_results": db_results  # Guardar los resultados de la BD en el estado
            }
            self._processing_state = current_state
        
        # Si no hay más referencias para procesar, retornar resultados finales
        if current_state["current_index"] >= len(current_state["refs_to_process"]):
            logger.info("=== FIN PROCESO DE CREACIÓN DE CARPETAS ===")
            # Limpiar estado
            self._processing_state = {}
            return {
                "processed": current_state["processed"],
                "errors": current_state["errors"],
                "pending_files": current_state["pending_files"],
                "processing_complete": True
            }
        
        # Obtener la siguiente referencia a procesar
        ref_info = current_state["refs_to_process"][current_state["current_index"]]
        original_ref = ref_info.get('original')
        logger.info(f"\nProcesando referencia {current_state['current_index'] + 1} de {len(current_state['refs_to_process'])}: {original_ref}")
        
        try:
            # Verificar si hay error previo
            if 'error' in ref_info:
                logger.warning(f"✗ Referencia con error previo: {ref_info['error']}")
                current_state["errors"].append(f"Error previo en {original_ref}: {ref_info['error']}")
                current_state["current_index"] += 1
                return self.create_folders_and_copy_files(formatted_refs, current_state["db_results"])
            
            final_name = ref_info['nombre_formateado']
            category = ref_info.get('category', '')
            
            # Verificar rutas en base de datos usando el estado guardado
            if original_ref not in current_state["db_results"] or not current_state["db_results"][original_ref]:
                logger.warning(f"✗ No hay rutas en base de datos para {original_ref}")
                current_state["errors"].append(f"No hay rutas para {original_ref}")
                current_state["current_index"] += 1
                return self.create_folders_and_copy_files(formatted_refs, current_state["db_results"])
            
            # Buscar la carpeta preferida (priorizando la que contiene "instructivo")
            try:
                source_folder = self._find_preferred_folder(original_ref)
                logger.info(f"✓ Carpeta preferida seleccionada: {source_folder}")
            except Exception as e:
                logger.warning(f"No se pudo encontrar carpeta preferida: {str(e)}")
                # Fallback: usar la primera ruta disponible de los resultados guardados
                source_folder = current_state["db_results"][original_ref][0]
                logger.info(f"Usando primera ruta disponible: {source_folder}\n")
            
            # Buscar archivos sin copiarlos
            files_info = self._copy_files(source_folder, None)
            
            # Si necesitamos esperar selección de archivo Rhino
            if files_info.get("waiting_for_rhino"):
                logger.info("Esperando selección de archivo Rhino")
                # Guardar toda la información necesaria en el estado
                current_state["pending_files"][original_ref] = {
                    "source_folder": source_folder,
                    "final_name": final_name,
                    "category": category,
                    "files_info": {
                        "pdf": files_info.get("pdf"),
                        "rhino": files_info.get("rhino"),
                        "rhino_alternatives": files_info.get("rhino_alternatives", []),
                        "errors": files_info.get("errors", []),
                        "waiting_for_rhino": True
                    }
                }
                return {
                    "processed": current_state["processed"],
                    "errors": current_state["errors"],
                    "pending_files": current_state["pending_files"],
                    "waiting_for_rhino": True,
                    "current_ref": original_ref,
                    "processing_complete": False
                }
            
            # Si no hay espera, proceder con la creación de carpetas
            target_folder = self._create_folder_structure(
                reference_name=final_name,
                category=category,
                source_path=source_folder
            )
            logger.info(f"✓ Estructura de carpetas creada: {target_folder}")
            
            # Copiar los archivos
            copy_results = self.copy_selected_files(files_info, target_folder)
            logger.info("✓ Archivos copiados exitosamente")
            
            # Registrar resultado exitoso
            current_state["processed"].append({
                "original": original_ref,
                "final_name": final_name,
                "target_folder": str(target_folder),
                "source_folder": source_folder,
                "copied_files": copy_results
            })
            
            # Avanzar al siguiente índice
            current_state["current_index"] += 1
            
            # Procesar la siguiente referencia
            return self.create_folders_and_copy_files(formatted_refs, current_state["db_results"])
            
        except Exception as e:
            error_msg = f"Error procesando {original_ref}: {str(e)}"
            logger.error(f"✗ {error_msg}")
            current_state["errors"].append(error_msg)
            current_state["current_index"] += 1
            return self.create_folders_and_copy_files(formatted_refs, current_state["db_results"])

    def complete_folder_creation(self, reference: str, selected_rhino: Optional[str] = None) -> Dict:
        """
        Completa la creación de la carpeta copiando los archivos necesarios.
        Los archivos PDF y Rhino se copian en el directorio padre de la carpeta de la referencia.
        
        Args:
            reference: Referencia original
            selected_rhino: Ruta del archivo Rhino seleccionado (opcional)
            
        Returns:
            Dict con los resultados del proceso
        """
        logger.info(f"Completando creación de carpeta para {reference}")
        
        try:
            # Buscar la información en el estado actual
            current_state = getattr(self, '_processing_state', {})
            ref_data = None
            
            for ref in current_state.get("refs_to_process", []):
                if ref["original"] == reference:
                    ref_data = ref
                    break
                    
            if not ref_data:
                raise ValueError(f"No se encontró información para la referencia {reference}")
                
            # Obtener rutas
            source_folder = self._find_preferred_folder(reference)
            if not source_folder:
                raise ValueError(f"No se encontró carpeta fuente para {reference}")
                
            # Crear la estructura de carpetas
            target_folder = self._create_folder_structure(
                reference_name=ref_data['nombre_formateado'],
                category=ref_data.get('category', ''),
                source_path=source_folder
            )
            
            # Obtener el directorio padre donde se copiarán los archivos
            parent_folder = Path(target_folder).parent
            
            # Inicializar diccionario de archivos copiados y errores
            copied_files = {}
            errors = []
            
            # Primero buscar y copiar el PDF
            logger.info("Buscando y copiando archivos PDF...\n")
            copy_result = self._copy_files(source_folder, parent_folder)
            
            # Si hay un PDF encontrado, agregarlo al resultado
            if copy_result.get("pdf"):
                pdf_name = os.path.basename(copy_result["pdf"])
                pdf_target = parent_folder / pdf_name
                
                # Verificar si el archivo ya existe
                if not pdf_target.exists():
                    try:
                        shutil.copy2(copy_result["pdf"], pdf_target)
                        copied_files["pdf"] = pdf_name
                        logger.info(f"✓ PDF copiado: {pdf_name}")
                    except Exception as e:
                        error_msg = f"Error copiando PDF: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                else:
                    copied_files["pdf"] = pdf_name
                    logger.info(f"✓ PDF ya existe en el directorio padre: {pdf_name}")
            
            # Si se proporcionó un archivo Rhino específico, copiarlo
            if selected_rhino and os.path.exists(selected_rhino):
                logger.info("Copiando archivo Rhino seleccionado...")
                rhino_name = os.path.basename(selected_rhino).upper()
                rhino_target = parent_folder / rhino_name
                
                # Verificar si el archivo ya existe
                if not rhino_target.exists():
                    try:
                        shutil.copy2(selected_rhino, rhino_target)
                        copied_files["rhino"] = rhino_name
                        logger.info(f"✓ Archivo Rhino copiado exitosamente: {rhino_name}")
                    except Exception as e:
                        error_msg = f"Error copiando archivo Rhino: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                else:
                    copied_files["rhino"] = rhino_name
                    logger.info(f"✓ Archivo Rhino ya existe en el directorio padre: {rhino_name}")
            else:
                logger.info("No se proporcionó archivo Rhino para copiar")
            
            # Actualizar el estado de procesamiento
            processed_info = {
                "original": reference,
                "final_name": ref_data['nombre_formateado'],
                "target_folder": str(target_folder),
                "parent_folder": str(parent_folder),
                "source_folder": source_folder,
                "copied_files": copied_files
            }
            
            # Agregar al estado actual
            if "processed" not in current_state:
                current_state["processed"] = []
            current_state["processed"].append(processed_info)
            
            # Eliminar de pendientes si existe
            if "pending_files" in current_state and reference in current_state["pending_files"]:
                del current_state["pending_files"][reference]
            
            # Preparar resultado
            result = {
                "processed": [processed_info],
                "errors": errors
            }
            
            # Incrementar el índice actual
            current_state["current_index"] = current_state.get("current_index", 0) + 1
            
            return result
            
        except Exception as e:
            error_msg = f"Error completando la creación de carpeta: {str(e)}"
            logger.error(error_msg)
            return {
                "processed": [],
                "errors": [error_msg]
            }

    def _sanitize_folder_name(self, name: str) -> str:
        """
        Sanitiza el nombre de una carpeta para que sea válido en Windows.
        
        Args:
            name: Nombre original de la carpeta

        Returns:
            Nombre sanitizado
        """
        # 1. Eliminar caracteres ilegales en Windows
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in invalid_chars:
            name = name.replace(char, "-")
            
        # 2. Eliminar espacios al inicio y final
        name = name.strip()
        
        # 3. Asegurar que no termine en punto o espacio
        name = name.rstrip(". ")
        
        # 4. Convertir a mayúsculas
        name = name.upper()
        
        return name

    def _create_folder_structure(self, 
                               reference_name: str, 
                               category: str, 
                               source_path: str) -> Path:
        """
        Crea la estructura de carpetas necesaria usando el LLM para optimizar la estructura.
        
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
                # Convertir plural a singular si es necesario
                if category.endswith('S'):
                    category = category[:-1]
                    logger.debug(f"Categoría convertida a singular: {category}")
            
            # 3. Usar el LLM para determinar la estructura de carpetas óptima
            try:
                # Forzar que el LLM use la categoría en singular
                suggested_structure, _ = self.llm.determine_folder_structure(
                    source_path=source_path,
                    reference_name=reference_name,
                    category=category  # Ya está en singular aquí
                )
                
                # Limpiar y validar la estructura sugerida
                suggested_structure = suggested_structure.strip()
                if not suggested_structure:
                    raise ValueError("El LLM no proporcionó una estructura válida")
                
                # Asegurar que la primera carpeta use la categoría en singular
                folder_parts = suggested_structure.split('/')
                if folder_parts and folder_parts[0].strip().upper().endswith('S'):
                    folder_parts[0] = folder_parts[0][:-1]
                suggested_structure = '/'.join(folder_parts)
                
                logger.info(f"Estructura sugerida por LLM: {suggested_structure}")
                
                # 4. Crear la estructura de carpetas
                current_folder = base_folder
                
                for part in folder_parts:
                    part = part.strip()
                    if part:  # Ignorar partes vacías
                        safe_part = self._sanitize_folder_name(part)
                        current_folder = current_folder / safe_part
                        current_folder.mkdir(parents=True, exist_ok=True)
                        logger.debug(f"Creada carpeta: {safe_part}")
                
                logger.info(f"Estructura de carpetas creada exitosamente: {current_folder}\n")
                return current_folder
                
            except Exception as e:
                logger.error(f"Error con el LLM, usando método fallback: {str(e)}")
                # Si falla el LLM, usar el método anterior como fallback
                return self._create_folder_structure_fallback(
                    reference_name=reference_name,
                    category=category,  # Ya está en singular
                    source_path=source_path,
                    base_folder=base_folder
                )
            
        except Exception as e:
            error_msg = f"Error creando estructura de carpetas: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _create_folder_structure_fallback(self,
                                       reference_name: str,
                                       category: str,
                                       source_path: str,
                                       base_folder: Path) -> Path:
        """
        Método fallback para crear la estructura de carpetas cuando falla el LLM.
        Usa la lógica original del método.
        """
        try:
            # 1. Crear carpeta de categoría
            cat_folder = base_folder / category
            cat_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Carpeta de categoría creada: {cat_folder}")
            
            # 2. Analizar ruta origen para replicar estructura intermedia
            source_parts = Path(source_path).parts
            
            # Encontrar el índice después de la categoría en la ruta origen
            category_index = -1
            for i, part in enumerate(source_parts):
                if any(cat.lower() in part.lower() for cat in ['ambiente', 'baño', 'cocina', 'dormitorio', 'oficina']):
                    category_index = i
                    break
            
            if category_index >= 0 and category_index + 1 < len(source_parts):
                # Tomar partes intermedias hasta encontrar 'NUBE', 'EDITABLE' o carpetas similares
                current_folder = cat_folder
                skip_folders = {'nube', 'editable', '16mm', '3dm', 'renders', 'pdf', 'dwg', 'jpg'}
                
                for part in source_parts[category_index + 1:]:
                    part_lower = part.lower()
                    # Saltar si es una carpeta que no queremos incluir
                    if part_lower in skip_folders or any(folder in part_lower for folder in skip_folders):
                        continue
                    # Sanitizar y crear subcarpeta intermedia
                    safe_part = self._sanitize_folder_name(part)
                    current_folder = current_folder / safe_part
                    current_folder.mkdir(exist_ok=True)
                    logger.debug(f"Creada subcarpeta intermedia: {safe_part}")
            else:
                current_folder = cat_folder
                logger.warning("No se encontró punto de referencia para estructura intermedia")
            
            # 3. Crear carpeta final con el nombre sanitizado de la referencia
            safe_reference_name = self._sanitize_folder_name(reference_name)
            final_folder = current_folder / safe_reference_name
            final_folder.mkdir(exist_ok=True)
            logger.info(f"Carpeta final creada: {final_folder}")
            
            return final_folder
            
        except Exception as e:
            error_msg = f"Error en método fallback: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _authenticate_google_sheets(self) -> None:
        """Autentica con Google Sheets."""
        try:
            # Verificar que el archivo existe
            if not os.path.exists(self.google_credentials_path):
                raise ValueError(f"El archivo de credenciales no existe en la ruta: {self.google_credentials_path}")
                
            # Verificar que el archivo es un JSON válido
            try:
                with open(self.google_credentials_path, 'r', encoding='utf-8') as f:
                    credentials_json = json.load(f)
                    
                # Verificar campos requeridos
                required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                missing_fields = [field for field in required_fields if field not in credentials_json]
                
                if missing_fields:
                    raise ValueError(f"El archivo de credenciales no contiene los campos requeridos: {', '.join(missing_fields)}")
                    
            except json.JSONDecodeError:
                raise ValueError("El archivo de credenciales no es un JSON válido")
                
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            try:
                credentials = Credentials.from_service_account_file(
                    self.google_credentials_path, 
                    scopes=scopes
                )
            except Exception as e:
                raise ValueError(f"Error al cargar las credenciales: {str(e)}")
                
            try:
                self.gc = gspread.authorize(credentials)
                # Intentar una operación simple para verificar la autenticación
                self.gc.open_by_key(self.google_sheet_key)
                logger.info("Autenticación con Google Sheets exitosa")
            except Exception as e:
                raise ValueError(f"Error al autorizar con Google Sheets: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error en autenticación con Google Sheets: {e}")
            raise

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
            str: Nombre formateado (ej: 'CDB 9493 - CLOSET BARILOCHE ECO 150 (DUNA-BLANCO + BLANCO MQZ)')
        """
        logger.info("Formateando nombre con LLM")
        try:
            formatted_name = self.llm.format_reference_name(
                code=code_3_letters,
                number=consecutivo,
                description=description
            )
            
            logger.info(f"✓ Nombre formateado: {formatted_name}")
            return formatted_name
            
        except Exception as e:
            logger.error(f"✗ Error en formateo LLM: {str(e)}")
            logger.info("Usando método de formateo alternativo")
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
        Busca la carpeta preferida en la base de datos, priorizando carpetas que contengan instructivos.
        
        Args:
            reference: Referencia a buscar (ej: 'MBT 11306' o texto completo con descripción)

        Returns:
            Ruta de la carpeta encontrada

        Raises:
            ValueError: Si no se encuentra ninguna carpeta
        """
        logger.debug(f"Buscando carpeta preferida para: {reference}")
        
        # Extraer solo la parte de la referencia (letras y números)
        extracted_ref = extract_reference(reference)
        if not extracted_ref:
            error_msg = f"No se pudo extraer una referencia válida de: {reference}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.info(f"Referencia extraída: {extracted_ref}")
        
        # Normalizar la referencia extraída para búsqueda
        search_ref = normalize_text(extracted_ref)
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
                        WHEN LOWER(path) LIKE '%instructivo%' OR LOWER(folder_name) LIKE '%instructivo%' THEN 1
                        WHEN LOWER(path) LIKE '%\\nube\\%' AND (
                            LOWER(path) LIKE '%instructivo%' OR 
                            LOWER(folder_name) LIKE '%instructivo%'
                        ) THEN 2
                        WHEN LOWER(path) LIKE '%\\nube\\%' THEN 3
                        ELSE 4
                    END,
                    path
            """
            
            cursor.execute(query, (f"%{search_ref}%",))
            paths = cursor.fetchall()
            
            if not paths:
                error_msg = f"No se encontraron carpetas para la referencia: {extracted_ref}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Tomar el primer resultado (ya ordenado por preferencia)
            chosen_path = paths[0][0]
            
            # Verificar si es una carpeta de instructivo
            is_instructivo = "instructivo" in chosen_path.lower()
            log_msg = f"Carpeta seleccionada: {chosen_path}Carpeta seleccionada:\n"
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
                
                paths_info.append(path_info)
            
            # Ordenar las rutas por profundidad para mejor visualización
            paths_info.sort(key=lambda x: (x['depth'], x['path']))
            
            # Registrar solo el total de rutas encontradas
            logger.info(f"Total de rutas encontradas: {len(paths_info)}")
            
            return paths_info
            
        except Exception as e:
            logger.error(f"Error obteniendo rutas desde {start_path}: {str(e)}")
            return []

    def _find_base_folder(self, source_folder: str) -> str:
        """
        Sube en la jerarquía de directorios hasta que el padre sea uno de los 'root_paths' oficiales.
        Devuelve la carpeta base desde donde iniciar la búsqueda.
        
        Args:
            source_folder: Ruta de la carpeta origen
            
        Returns:
            str: Ruta de la carpeta base del proyecto
            
        Ejemplo:
            Si source_folder es '//192.168.200.250/cocina/Mueble Alacena Fenix/MODULO MICROONDAS FENIX 60/NUBE'
            y '//192.168.200.250/cocina' está en root_paths,
            retornará '//192.168.200.250/cocina/Mueble Alacena Fenix'
        """
        logger.info(f"=== INICIO BÚSQUEDA DE CARPETA BASE ===")
        logger.info(f"Analizando ruta: {source_folder}")

        # Normaliza barras para evitar problemas
        current_path = os.path.normpath(source_folder)

        while True:
            parent_path = os.path.normpath(os.path.dirname(current_path))
            
            # Si llegamos a la raíz o no podemos subir más
            if not parent_path or parent_path == current_path:
                logger.warning(f"✗ Llegamos al tope sin encontrar una ruta raíz")
                return current_path

            # Si el padre es una ruta raíz, retornamos la carpeta actual
            if self._is_one_of_my_roots(parent_path):
                logger.info(f"✓ Carpeta base encontrada: {current_path}")
                logger.info(f"=== FIN BÚSQUEDA DE CARPETA BASE ===\n")
                return current_path

            # Guardamos la ruta actual antes de subir
            previous_path = current_path
            current_path = parent_path
            
            # Si no pudimos subir más, usamos la última ruta válida
            if current_path == previous_path:
                logger.warning(f"✗ No se pudo subir más en la jerarquía")
                return current_path

        logger.info(f"=== FIN BÚSQUEDA DE CARPETA BASE ===\n")

    def _is_one_of_my_roots(self, path: str) -> bool:
        """
        Retorna True si 'path' coincide con alguno de los root_paths "oficiales".
        
        Args:
            path: Ruta a verificar
            
        Returns:
            bool: True si la ruta coincide exactamente con alguna ruta raíz
        """
        # Ajusta las barras y minúsculas para comparación consistente
        norm_path = os.path.normpath(path).lower().rstrip('\\')
        
        for root in self.root_paths:
            norm_root = os.path.normpath(root).lower().rstrip('\\')
            if norm_path == norm_root:
                logger.info(f"✓ {path} es una ruta raíz")
                return True
                
        logger.info(f"✗ {path} no es una ruta raíz")
        return False

    def _list_alternative_rhino_files(self, folder: str) -> str:
        """
        Lista archivos .3dm en la carpeta padre de `folder`.
        Retorna un string con formato <file_button>...</file_button> que 
        el chatPanel luego convierte en botones.
        
        Args:
            folder: Ruta de la carpeta donde se buscarán los archivos
            
        Returns:
            str: Mensaje formateado con botones para cada archivo encontrado
        """
        # 1) Obtener la carpeta padre y validar
        parent_path = os.path.dirname(folder)
        if not os.path.isdir(parent_path):
            logger.warning(f"La carpeta padre no existe: {parent_path}")
            return ""

        # 2) Buscar archivos .3dm en la carpeta padre
        rhino_candidates = []
        try:
            for item in os.listdir(parent_path):
                if item.lower().endswith(".3dm"):
                    full_path = os.path.join(parent_path, item)
                    if os.path.isfile(full_path):
                        rhino_candidates.append(full_path)
                        logger.debug(f"Archivo Rhino encontrado: {full_path}")
        except Exception as e:
            logger.error(f"Error buscando archivos .3dm: {str(e)}")
            return ""

        # 3) Si no hay candidatos, retornar vacío
        if not rhino_candidates:
            logger.warning("No se encontraron archivos .3dm alternativos")
            return ""

        # 4) Construir el mensaje con los botones
        message = (
            "No se ha encontrado el archivo de Rhino en la carpeta EDITABLES.\n"
            "Pero se han encontrado estos otros archivos .3dm en la carpeta padre.\n"
            "Revisa y selecciona el que corresponda, o ignora la copia.\n\n"
        )

        # 5) Agregar botones para cada archivo encontrado
        for file_path in rhino_candidates:
            file_name = os.path.basename(file_path)
            message += "---\n\n"
            message += f"**{file_name}**\n"

            # Botón para abrir carpeta
            open_folder_btn = {
                "text": "Abrir carpeta",
                "path": os.path.dirname(file_path),
                "type": "folder"
            }
            message += f"<file_button>{open_folder_btn}</file_button>\n"

            # Botón para abrir archivo
            open_file_btn = {
                "text": "Abrir archivo",
                "path": file_path,
                "type": "rhino"
            }
            message += f"<file_button>{open_file_btn}</file_button>\n"

            # Botón para elegir archivo
            choose_file_btn = {
                "text": "Elegir este archivo",
                "path": file_path,
                "type": "choose_rhino"
            }
            message += f"<file_button>{choose_file_btn}</file_button>\n\n"

        logger.info(f"Mensaje generado con {len(rhino_candidates)} archivos alternativos")
        return message

    def _find_rhino_file(self, source_folder: str) -> Optional[List[str]]:
        logger.info("=== INICIO BÚSQUEDA DE ARCHIVO RHINO ===")
        logger.info(f"Carpeta origen: {source_folder}")
        
        try:
            # 1) Primero, buscar en la carpeta EDITABLES del nivel actual
            # Subir un nivel desde la carpeta actual (ej: desde NUBE subir a MODULO MICROONDAS FENIX 60)
            current_dir = os.path.dirname(os.path.dirname(source_folder))
            logger.info(f"Buscando en el nivel actual: {current_dir}")
            
            # Buscar carpeta EDITABLES en este nivel
            editables_path = os.path.join(current_dir, "EDITABLES")
            if os.path.exists(editables_path) and os.path.isdir(editables_path):
                logger.info(f"Carpeta EDITABLES encontrada: {editables_path}")
                
                # Buscar archivos .3dm en EDITABLES
                rhino_files = []
                for root, _, files in os.walk(editables_path):
                    rhino_files.extend([
                        os.path.join(root, f) 
                        for f in files 
                        if f.lower().endswith('.3dm')
                    ])
                
                if rhino_files:
                    if len(rhino_files) == 1:
                        logger.info(f"✓ Archivo único encontrado en EDITABLES actual: {rhino_files[0]}")
                        return [rhino_files[0]]
                    else:
                        logger.info(f"Múltiples archivos encontrados en EDITABLES actual: {len(rhino_files)}")
                        return rhino_files
                
                logger.info("No se encontraron archivos .3dm en EDITABLES actual")
            else:
                logger.info(f"No se encontró carpeta EDITABLES en: {current_dir}")
            
            # 2) Si no se encontró en EDITABLES actual, buscar en la carpeta base del proyecto
            logger.info("No se encontró en EDITABLES actual, buscando en carpeta base...\n")
            
            base_path = self._find_base_folder(source_folder)
            if not base_path or not os.path.exists(base_path):
                logger.error(f"✗ No se pudo determinar la carpeta base desde: {source_folder}")
                return None
                
            logger.info(f"✓ Carpeta base identificada: {base_path}")
            
            # Verificar que no estemos en una ruta raíz
            if self._is_one_of_my_roots(base_path):
                logger.error("✗ La carpeta base no puede ser una ruta raíz")
                return None
            
            # Obtener todas las rutas posibles desde la carpeta base
            all_paths = self._get_all_possible_paths(base_path)
            logger.info(f"✓ Rutas encontradas en carpeta base: {len(all_paths)}")
            
            # Buscar en otras carpetas EDITABLES del proyecto
            editable_paths = [p['path'] for p in all_paths if p['is_editable']]
            all_rhino_files = []
            
            if editable_paths:
                logger.info("Buscando en otras carpetas EDITABLES del proyecto")
                for editable_path in editable_paths:
                    for root, _, files in os.walk(editable_path):
                        rhino_files = [os.path.join(root, f) for f in files if f.lower().endswith('.3dm')]
                        all_rhino_files.extend(rhino_files)
                        if rhino_files:
                            logger.info(f"Encontrados {len(rhino_files)} archivos en {editable_path}")

            # Si encontramos archivos, retornarlos todos para que el usuario elija
            if all_rhino_files:
                logger.info(f"✓ Total de archivos Rhino encontrados: {len(all_rhino_files)}")
                return all_rhino_files
            
            # Si no se encontró ningún archivo, retornar None
            logger.info("✗ No se encontró ningún archivo Rhino")
            return None
            
        except Exception as e:
            logger.error(f"✗ Error en búsqueda: {str(e)}")
            return None
        finally:
            logger.info("=== FIN BÚSQUEDA DE ARCHIVO RHINO ===\n")

    def _copy_files(self, source_folder: str, target_folder: Optional[Path]) -> Dict:
        """
        Busca y copia los archivos necesarios desde la carpeta origen a la carpeta destino.
        Los archivos se copian en el directorio destino y no se duplican si ya existen.
        
        Args:
            source_folder: Ruta de la carpeta origen
            target_folder: Ruta de la carpeta destino (será el directorio padre de la referencia).
                         Si es None, solo busca los archivos sin copiarlos.
            
        Returns:
            Dict con información de los archivos encontrados y copiados
        """
        logger.info("=== INICIO BÚSQUEDA Y COPIA DE ARCHIVOS ===")
        logger.info(f"Origen: {source_folder}")
        logger.info(f"Destino: {target_folder}")
        
        result = {
            "pdf": None,
            "rhino": None,
            "errors": [],
            "waiting_for_rhino": False,
            "rhino_alternatives": []
        }
        
        try:
            # 1) Buscar PDF
            pdf_candidates = []
            
            # Si la carpeta origen ya contiene 'instructivo', buscar solo en ella
            if 'instructivo' in source_folder.lower():
                logger.info("Carpeta origen contiene 'instructivo', buscando PDF directamente aquí")
                # Buscar solo en esta carpeta, sin recursión
                for file in os.listdir(source_folder):
                    if file.lower().endswith('.pdf'):
                        full_path = os.path.join(source_folder, file)
                        if os.path.isfile(full_path):
                            pdf_candidates.append((full_path, 1))  # Prioridad alta por estar en carpeta instructivo
                            logger.info(f"PDF encontrado en carpeta instructivo: {full_path}")
                
                if not pdf_candidates:
                    logger.warning("✗ No se encontró PDF en la carpeta instructivo")
                    result["errors"].append("No se encontró PDF en la carpeta instructivo")
            else:
                # Si no es una carpeta instructivo, buscar en la estructura completa
                base_folder = self._find_base_folder(source_folder)
                logger.info(f"Buscando PDFs desde carpeta base: {base_folder}")
                
                # Buscar en toda la estructura de carpetas
                for root, _, files in os.walk(base_folder):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            full_path = os.path.join(root, file)
                            # Calcular prioridad del PDF
                            priority = 0
                            path_lower = root.lower()
                            file_lower = file.lower()
                            
                            # Prioridad más alta: archivo y carpeta contienen "instructivo"
                            if 'instructivo' in file_lower and 'instructivo' in path_lower:
                                priority = 1
                            # Segunda prioridad: carpeta contiene "instructivo"
                            elif 'instructivo' in path_lower:
                                priority = 2
                            # Tercera prioridad: archivo contiene "instructivo"
                            elif 'instructivo' in file_lower:
                                priority = 3
                            # Menor prioridad: contiene "mapa de empaque"
                            elif 'mapa de empaque' in file_lower or 'mapa de empaque' in path_lower:
                                priority = 5
                            # Prioridad intermedia para otros PDFs
                            else:
                                priority = 4
                                
                            pdf_candidates.append((full_path, priority))
                            logger.info(f"PDF encontrado: {full_path} (prioridad: {priority})")
            
            # Ordenar candidatos por prioridad y seleccionar el mejor
            if pdf_candidates:
                pdf_candidates.sort(key=lambda x: x[1])  # Ordenar por prioridad (menor número = mayor prioridad)
                selected_pdf = pdf_candidates[0][0]
                result["pdf"] = selected_pdf
                
                # Si se proporcionó una carpeta destino, copiar el PDF
                if target_folder is not None:
                    pdf_name = os.path.basename(selected_pdf)
                    pdf_target = target_folder / pdf_name
                    
                    # Verificar si el archivo ya existe
                    if not pdf_target.exists():
                        shutil.copy2(selected_pdf, pdf_target)
                        logger.info(f"✓ PDF copiado: {pdf_name}")
                    else:
                        logger.info(f"✓ PDF ya existe en el directorio padre: {pdf_name}")
            else:
                logger.warning("✗ No se encontraron archivos PDF")
                result["errors"].append("No se encontraron archivos PDF")
            
            # 2) Buscar archivos Rhino (sin copiar, solo para alternativas)
            rhino_files = []
            for root, _, files in os.walk(source_folder):
                for file in files:
                    if file.lower().endswith('.3dm'):
                        full_path = os.path.join(root, file)
                        rhino_files.append(full_path)
                        logger.info(f"Archivo Rhino encontrado: {full_path}")
            
            if len(rhino_files) > 1:
                result["waiting_for_rhino"] = True
                result["rhino_alternatives"] = rhino_files
                logger.info(f"Múltiples archivos Rhino encontrados: {len(rhino_files)}")
            elif len(rhino_files) == 1:
                result["rhino"] = rhino_files[0]
                # Si se proporcionó una carpeta destino, copiar el archivo Rhino
                if target_folder is not None:
                    rhino_name = os.path.basename(rhino_files[0])
                    rhino_target = target_folder / rhino_name
                    
                    if not rhino_target.exists():
                        shutil.copy2(rhino_files[0], rhino_target)
                        logger.info(f"✓ Archivo Rhino único copiado: {rhino_name}")
                    else:
                        logger.info(f"✓ Archivo Rhino ya existe en el directorio padre: {rhino_name}")
            else:
                logger.warning("✗ No se encontraron archivos Rhino")
                result["errors"].append("No se encontraron archivos Rhino")
            
            return result
            
        except Exception as e:
            error_msg = f"Error buscando y copiando archivos: {str(e)}"
            logger.error(f"✗ {error_msg}")
            result["errors"].append(error_msg)
            return result
        finally:
            logger.info("=== FIN BÚSQUEDA Y COPIA DE ARCHIVOS ===\n")

    def copy_selected_files(self, files_info: Dict, target_folder: Path) -> Dict:
        """
        Copia los archivos seleccionados al directorio padre de la carpeta destino.
        Si los archivos ya existen en el directorio padre, no se duplican.
        
        Args:
            files_info: Diccionario con información de los archivos a copiar
            target_folder: Carpeta destino
            
        Returns:
            Dict con información de los archivos copiados
        """
        result = {}
        
        try:
            # Obtener el directorio padre donde se copiarán los archivos
            parent_folder = target_folder.parent
            
            # Copiar PDF si existe
            if files_info.get("pdf"):
                pdf_source = files_info["pdf"]["source"]
                pdf_name = files_info["pdf"]["filename"]
                pdf_target = parent_folder / pdf_name
                
                # Verificar si el archivo ya existe
                if not pdf_target.exists():
                    shutil.copy2(pdf_source, pdf_target)
                    result["pdf"] = pdf_name
                    logger.info(f"✓ PDF copiado: {pdf_name}")
                else:
                    result["pdf"] = pdf_name
                    logger.info(f"✓ PDF ya existe en el directorio padre: {pdf_name}")
            
            # Copiar Rhino si existe
            if files_info.get("rhino"):
                rhino_source = files_info["rhino"]["source"]
                rhino_name = files_info["rhino"]["filename"]
                rhino_target = parent_folder / rhino_name
                
                # Verificar si el archivo ya existe
                if not rhino_target.exists():
                    shutil.copy2(rhino_source, rhino_target)
                    result["rhino"] = rhino_name
                    logger.info(f"✓ Rhino copiado: {rhino_name}")
                else:
                    result["rhino"] = rhino_name
                    logger.info(f"✓ Rhino ya existe en el directorio padre: {rhino_name}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error copiando archivos: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return {"errors": [error_msg]}

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

    def set_progress_callback(self, callback: Callable[[str], None]):
        """Establece la función de callback para reportar progreso"""
        self._progress_callback = callback
        
    def _report_progress(self, message: str):
        """Reporta progreso si hay un callback configurado"""
        if self._progress_callback:
            self._progress_callback(message)

    def prepare_folder_creation(self, ref_data: Dict) -> Dict:
        """
        Prepara la carpeta y busca los archivos necesarios para una referencia.
        
        Args:
            ref_data: Diccionario con la información de la referencia
            
        Returns:
            Dict con la información de la carpeta y archivos encontrados
        """
        logger.info(f"Preparando creación de carpeta para {ref_data['original']}")
        
        try:
            # Obtener información necesaria
            reference = ref_data['original']
            nombre_formateado = ref_data['nombre_formateado']
            category = ref_data.get('category', '')
            
            # Verificar que tenemos los resultados de la BD
            if not hasattr(self, '_processing_state') or 'db_results' not in self._processing_state:
                raise ValueError("No se encontraron resultados de la base de datos en el estado")
                
            db_results = self._processing_state['db_results']
            if reference not in db_results:
                raise ValueError(f"No se encontraron rutas en la base de datos para {reference}")
                
            # Buscar la carpeta preferida usando las rutas de la BD
            source_paths = db_results[reference]
            source_folder = None
            
            # Primero buscar una carpeta que contenga "instructivo"
            for path in source_paths:
                if 'instructivo' in path.lower():
                    source_folder = path
                    logger.info(f"Encontrada carpeta con instructivo: {path}\n")
                    break
                    
            # Si no hay carpeta con instructivo, usar la primera ruta
            if not source_folder and source_paths:
                source_folder = source_paths[0]
                logger.info(f"Usando primera ruta disponible: {source_folder}\n")
                
            if not source_folder:
                raise ValueError(f"No se encontró carpeta fuente para {reference}")
                
            # Crear estructura de carpetas
            target_folder = self._create_folder_structure(
                reference_name=nombre_formateado,
                category=category,
                source_path=source_folder
            )
            
            # Buscar archivos Rhino
            rhino_alternatives = self._find_rhino_file(source_folder)
            
            # Preparar resultado
            result = {
                "original": reference,
                "nombre_formateado": nombre_formateado,
                "source_folder": source_folder,
                "target_folder": str(target_folder),
                "rhino_alternatives": rhino_alternatives if rhino_alternatives else []
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error preparando carpeta para {ref_data['original']}: {str(e)}")
            raise 