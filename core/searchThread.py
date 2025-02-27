"""
Módulo principal que implementa la funcionalidad de búsqueda de archivos y carpetas.

Este módulo proporciona una implementación multihilo para buscar referencias y archivos
en múltiples ubicaciones de red (NAS) y bases de datos locales. Soporta dos tipos principales
de búsqueda: por referencia exacta y por nombre de archivo.
"""

import os
from PyQt5.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.helpers import is_exact_match, search_references, is_ficha_tecnica, normalize_text, get_significant_terms, extract_reference
from utils.database import get_folder, insert_folder
import time
import unicodedata

# Lista de palabras de enlace comunes que se ignorarán en la búsqueda
STOPWORDS = {'de', 'la', 'el', 'y', 'en', 'a', 'por', 'para', 'con', 'sin', 'sobre'}

class SearchThread(QThread):
    """
    Hilo de búsqueda que maneja las operaciones de búsqueda en segundo plano.

    Esta clase implementa la lógica principal de búsqueda, permitiendo buscar archivos
    y carpetas tanto por referencia exacta como por nombre de archivo. Utiliza múltiples
    hilos para optimizar el rendimiento en búsquedas a través de la red.

    Signals:
        finished (dict): Emitida cuando la búsqueda se completa, contiene los resultados.
        progress (float): Progreso general de la búsqueda.
        db_progress (float): Progreso de la búsqueda en base de datos.
        nas_progress (float): Progreso de la búsqueda en NAS.
        directoryProcessed (int, int, str): Información sobre el directorio procesado.
        new_result (int, str, str, str): Nuevo resultado encontrado.

    Attributes:
        text_lines (list): Lista de términos de búsqueda.
        text_lines_indices (dict): Mapeo de términos a índices.
        paths (list): Rutas donde buscar.
        file_types (list): Tipos de archivo a buscar.
        search_type (str): Tipo de búsqueda ('Referencia' o 'Nombre de Archivo').
        max_workers (int): Número máximo de hilos concurrentes.
        db_search_limit (int): Límite de resultados de base de datos.
    """

    finished = pyqtSignal(dict)
    progress = pyqtSignal(float)
    db_progress = pyqtSignal(float)
    nas_progress = pyqtSignal(float)
    directoryProcessed = pyqtSignal(int, int, str)
    new_result = pyqtSignal(int, str, str, str)

    def __init__(self, text_lines, text_lines_indices, paths, file_types, custom_extensions=None, search_type='Referencia', max_workers=12, db_search_limit=50):
        """
        Inicializa el hilo de búsqueda con los parámetros especificados.

        Args:
            text_lines (list): Lista de términos de búsqueda.
            text_lines_indices (dict): Diccionario que mapea términos a sus índices.
            paths (list): Lista de rutas donde realizar la búsqueda.
            file_types (list): Lista de tipos de archivo a buscar.
            custom_extensions (list, optional): Lista de extensiones personalizadas. Por defecto None.
            search_type (str, optional): Tipo de búsqueda ('Referencia' o 'Nombre de Archivo'). Por defecto 'Referencia'.
            max_workers (int, optional): Número máximo de hilos concurrentes. Por defecto 12.
            db_search_limit (int, optional): Límite de resultados de base de datos. Por defecto 50.
        """
        super().__init__()
        self.text_lines = text_lines
        self.text_lines_indices = text_lines_indices
        self.paths = self.optimize_paths(list(set(paths)))
        self.file_types = file_types
        self.custom_extensions = custom_extensions if custom_extensions else []
        self.search_type = search_type
        self.results = {}
        self.found_paths = set()
        self.total_directories = self.count_directories()
        self.processed_directories = 0
        self.max_workers = max_workers
        self.db_search_limit = db_search_limit

    def count_directories(self):
        """
        Cuenta el número total de directorios en las rutas especificadas.

        Returns:
            int: Número total de directorios.
        """
        total = 0
        for path in self.paths:
            try:
                total += len(next(os.walk(path))[1])
            except StopIteration:
                pass
        return total

    def run(self):
        """
        Método principal que inicia la búsqueda según el tipo especificado.
        Ejecuta la búsqueda por referencia o por nombre de archivo según corresponda.
        """
        if self.search_type in ['Referencia', 'FolderCreation']: # Si es referencia o creación de carpetas
            self.run_reference_search()
        elif self.search_type == 'Nombre de Archivo':
            self.run_name_search()
        self.finished.emit(self.results)

    def run_reference_search(self):
        """
        Ejecuta la búsqueda por referencia.
        
        Este método realiza una búsqueda en dos fases:
        1. Búsqueda en la base de datos local
        2. Búsqueda en el sistema de archivos (NAS) - Solo si el tipo de búsqueda no es FolderCreation
        
        Emite señales de progreso durante la búsqueda y nuevos resultados encontrados.
        """
        print("Iniciando búsqueda en la base de datos (Referencia)...") 
        total_db_references = len(self.text_lines)
        for idx, text_line in enumerate(self.text_lines):
            if self.isInterruptionRequested():
                break
            
            # Extraer la referencia del texto de búsqueda
            reference = extract_reference(text_line)
            search_text = reference if reference else text_line
            
            print(f"Buscando en la base de datos para la referencia: {search_text}")
            db_results = get_folder(search_text, self.paths, self.db_search_limit)
            print(f"Resultados de la base de datos: {db_results}")
            
            if db_results:
                for result in db_results:
                    path = result['path']
                    folder_name = result['folder_name']
                    last_updated = result['last_updated']
                    
                    # Verificar si es una coincidencia exacta usando el nombre de la carpeta
                    if is_exact_match(search_text, folder_name):
                        if os.path.exists(path):
                            print(f"Ruta válida encontrada en la base de datos: {path}")
                            if path not in self.found_paths:
                                self.results[idx] = [(path, "Carpeta", text_line)]
                                self.found_paths.add(path)
                                self.new_result.emit(idx, path, "Carpeta", text_line)
                                if "Carpetas" not in self.file_types:
                                    self.search_in_folder(path, text_line, idx)
                            # Pre-búsqueda en la ruta obtenida de la base de datos
                            self.pre_search_in_db_path(path, text_line, idx)
                        else:
                            print(f"Ruta inválida encontrada en la base de datos, verificando y actualizando: {path}")
                            self.verify_and_update_path(idx, text_line, path, folder_name)
            else:
                print(f"No se encontraron resultados en la base de datos para la referencia: {text_line}")
            
            self.db_progress.emit((idx + 1) / total_db_references * 100)
        
        print("Finalizada la búsqueda en la base de datos.")

        # Solo realizar búsqueda en NAS si no es FolderCreation
        if self.search_type != 'FolderCreation':
            print("Iniciando búsqueda en la NAS para referencias...")
            self.processed_directories = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.processPath, path) for path in self.paths]
                for future in as_completed(futures):
                    if self.isInterruptionRequested():
                        break
                    future.result()
        else:
            # Para FolderCreation, marcar la búsqueda en NAS como completada
            self.nas_progress.emit(100)
            print("Omitiendo búsqueda en NAS para modo de creación de carpetas.")

    def run_name_search(self):
        """
        Ejecuta la búsqueda por nombre de archivo.
        
        Este método realiza una búsqueda basada en el nombre del archivo o carpeta,
        permitiendo coincidencias parciales y normalizando el texto para mejorar los resultados.
        
        Emite señales de progreso durante la búsqueda y nuevos resultados encontrados.
        """
        print("Iniciando búsqueda por Nombre de Archivo...")
        
        # Búsqueda en la base de datos
        total_queries = len(self.text_lines)
        for idx, query in enumerate(self.text_lines):
            if self.isInterruptionRequested():
                break
                
            print(f"Buscando en la base de datos archivos que contengan: {query}")
            
            if self.search_type == 'Nombre de Archivo':
                normalized_query = normalize_text(query)
                query_terms = get_significant_terms(query)
            else:
                normalized_query = query.lower()
                query_terms = [normalized_query]
                
            db_results = get_folder(query, self.paths, self.db_search_limit)
            
            if db_results:
                for result in db_results:
                    path = result['path']
                    folder_name = result['folder_name']
                    if os.path.exists(path):
                        if self.search_type == 'Nombre de Archivo':
                            normalized_folder_name = folder_name  # Ya está normalizado al insertar
                            if all(term in normalized_folder_name for term in query_terms):
                                full_path = os.path.normpath(path)
                                if full_path not in self.found_paths:
                                    self.results.setdefault(idx, []).append((full_path, "Carpeta", query))
                                    self.found_paths.add(full_path)
                                    self.new_result.emit(idx, full_path, "Carpeta", '')
                        else:
                            if normalized_query in folder_name.lower():
                                full_path = os.path.normpath(path)
                                if full_path not in self.found_paths:
                                    self.results.setdefault(idx, []).append((full_path, "Carpeta", query))
                                    self.found_paths.add(full_path)
                                    self.new_result.emit(idx, full_path, "Carpeta", '')
                            
            else:
                print(f"No se encontraron resultados en la base de datos para la consulta: {query}")
            
            self.db_progress.emit((idx + 1) / total_queries * 100)

        # Búsqueda en el sistema de archivos NAS
        print("Buscando en el sistema de archivos...")
        self.processed_directories = 0
        total_paths = len(self.paths)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.processPath, path) for path in self.paths]
            for future in as_completed(futures):
                if self.isInterruptionRequested():
                    break
                future.result()

        print("Finalizada la búsqueda por Nombre de Archivo.")

    def checkFilesAndDirs(self, root, dirs, files):
        """
        Verifica archivos y directorios en busca de coincidencias.

        Args:
            root (str): Ruta base del directorio actual.
            dirs (list): Lista de subdirectorios en el directorio actual.
            files (list): Lista de archivos en el directorio actual.
        """
        for text_line, idx in self.text_lines_indices.items():
            if self.search_type == 'Nombre de Archivo':
                query = text_line
                normalized_query_terms = get_significant_terms(query)
                
                # Función auxiliar para verificar coincidencias
                def check_terms_in_name(name, terms):
                    normalized_name = normalize_text(name)
                    name_parts = set(normalized_name.split())
                    for term in terms:
                        # Buscar el término como parte de palabra o palabra completa
                        if not (term in normalized_name or term in name_parts):
                            return False
                    return True
                
                # Primero buscar en los directorios si están seleccionados
                if "Carpetas" in self.file_types:
                    for dir in dirs:
                        if check_terms_in_name(dir, normalized_query_terms):
                            full_path = os.path.normpath(os.path.join(root, dir))
                            if full_path not in self.found_paths:
                                self.results.setdefault(idx, []).append((full_path, "Carpeta", query))
                                self.found_paths.add(full_path)
                                self.new_result.emit(idx, full_path, "Carpeta", query)
                
                # Luego buscar en los archivos del directorio actual según los tipos seleccionados
                for file in files:
                    if check_terms_in_name(file, normalized_query_terms) and self.should_process_file(file):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if full_path not in self.found_paths:
                            file_type = self.determine_file_type(file)
                            self.results.setdefault(idx, []).append((full_path, file_type, query))
                            self.found_paths.add(full_path)
                            self.new_result.emit(idx, full_path, file_type, query)
            
            elif self.search_type == 'Referencia':
                # Lógica existente para búsqueda por Referencia
                search_reference = text_line
                if "Carpetas" in self.file_types:
                    for dir in dirs:
                        full_path = os.path.normpath(os.path.join(root, dir))
                        if is_exact_match(search_reference, dir) and full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Carpeta", search_reference))
                            self.found_paths.add(full_path)
                            self.new_result.emit(idx, full_path, "Carpeta", search_reference)

                if "Videos" in self.file_types:
                    for file in files:
                        if file.lower().endswith(('.mp4', '.mov', '.wmv', '.flv', '.avi', '.avchd', '.webm', '.mkv')):
                            full_path = os.path.normpath(os.path.join(root, file))
                            if is_exact_match(search_reference, file) and full_path not in self.found_paths:
                                self.results.setdefault(idx, []).append((full_path, "Video", search_reference))
                                self.found_paths.add(full_path)
                                self.new_result.emit(idx, full_path, "Video", search_reference)

                if "Imágenes" in self.file_types:
                    for file in files:
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                            full_path = os.path.normpath(os.path.join(root, file))
                            if is_exact_match(search_reference, file) and full_path not in self.found_paths:
                                self.results.setdefault(idx, []).append((full_path, "Imagen", search_reference))
                                self.found_paths.add(full_path)
                                self.new_result.emit(idx, full_path, "Imagen", search_reference)

                if "Excel" in self.file_types:
                    for file in files:
                        if file.lower().endswith(('.xls', '.xlsx')) and is_ficha_tecnica(search_reference, file):
                            full_path = os.path.normpath(os.path.join(root, file))
                            if full_path not in self.found_paths:
                                self.results.setdefault(idx, []).append((full_path, "Excel", search_reference))
                                self.found_paths.add(full_path)
                                self.new_result.emit(idx, full_path, "Excel", search_reference)
                continue  # Saltar al siguiente ciclo si es 'Referencia'

    def determine_file_type(self, filename):
        """
        Determina el tipo de archivo basado en su extensión.

        Args:
            filename (str): Nombre del archivo a analizar.

        Returns:
            str: Tipo de archivo ('Imagen', 'Video', 'PDF', etc.) o None si no se reconoce.
        """
        ext = os.path.splitext(filename)[1].lower()
        
        # Verificar extensiones personalizadas primero
        if self.custom_extensions and ext in self.custom_extensions:
            return "Otro"
            
        # Extensiones de imagen
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            return "Imagen"
            
        # Extensiones de video
        elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']:
            return "Video"
            
        # Extensiones de documentos
        elif ext in ['.pdf']:
            return "PDF"
        elif ext in ['.doc', '.docx']:
            return "Word"
        elif ext in ['.txt']:
            return "Texto"
        elif ext in ['.xls', '.xlsx']:
            return "Excel"
            
        return None

    def should_process_file(self, filename):
        """
        Determina si un archivo debe ser procesado según su tipo y las opciones seleccionadas.

        Args:
            filename (str): Nombre del archivo a verificar.

        Returns:
            bool: True si el archivo debe ser procesado, False en caso contrario.
        """
        file_type = self.determine_file_type(filename)
        
        if file_type == "Otro" and "Otro" in self.file_types:
            return True
        elif file_type == "Imagen" and "Imágenes" in self.file_types:
            return True
        elif file_type == "Video" and "Videos" in self.file_types:
            return True
        elif file_type == "PDF" and "PDF" in self.file_types:
            return True
        elif file_type == "Word" and "Word" in self.file_types:
            return True
        elif file_type == "Texto" and "Texto" in self.file_types:
            return True
        elif file_type == "Excel" and "Excel" in self.file_types:
            return True
            
        return False

    def pre_search_in_db_path(self, db_path, search_reference, idx):
        # Solo se ejecuta si search_type es 'Referencia' o 'FolderCreation'
        if self.search_type not in ['Referencia', 'FolderCreation']:
            return
        for root, dirs, files in os.walk(db_path):
            if "Imágenes" in self.file_types:
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if is_exact_match(search_reference, file) and full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Imagen", search_reference))
                            self.found_paths.add(full_path)
                            self.new_result.emit(idx, full_path, "Imagen", search_reference)
                            
            if "Videos" in self.file_types:
                for file in files:
                    if file.lower().endswith(('.mp4', '.mov', '.wmv', '.flv', '.avi', '.avchd', '.webm', '.mkv')):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if is_exact_match(search_reference, file) and full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Video", search_reference))
                            self.found_paths.add(full_path)
                            self.new_result.emit(idx, full_path, "Video", search_reference)

            if "Excel" in self.file_types:
                for file in files:
                    if file.lower().endswith(('.xls', '.xlsx')) and is_ficha_tecnica(search_reference, file):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Excel", search_reference))
                            self.found_paths.add(full_path)
                            self.new_result.emit(idx, full_path, "Excel", search_reference)

    def search_in_folder(self, folder_path, search_reference, idx):
        for root, dirs, files in os.walk(folder_path):
            if "Carpetas" in self.file_types:
                for dir in dirs:
                    full_path = os.path.normpath(os.path.join(root, dir))
                    if is_exact_match(search_reference, dir) and full_path not in self.found_paths:
                        self.results.setdefault(idx, []).append((full_path, "Carpeta", search_reference))
                        self.found_paths.add(full_path)
                        self.new_result.emit(idx, full_path, "Carpeta", search_reference)

            if "Imágenes" in self.file_types:
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if is_exact_match(search_reference, file) and full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Imagen", search_reference))
                            self.found_paths.add(full_path)
                            self.new_result.emit(idx, full_path, "Imagen", search_reference)

            if "Videos" in self.file_types:
                for file in files:
                    if file.lower().endswith(('.mp4', '.mov', '.wmv', '.flv', '.avi', '.avchd', '.webm', '.mkv')):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if is_exact_match(search_reference, file) and full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Video", search_reference))
                            self.found_paths.add(full_path)
                            self.new_result.emit(idx, full_path, "Video", search_reference)

            if "Excel" in self.file_types:
                for file in files:
                    if file.lower().endswith(('.xls', '.xlsx')) and is_ficha_tecnica(search_reference, file):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Excel", search_reference))
                            self.found_paths.add(full_path)
                            self.new_result.emit(idx, full_path, "Excel", search_reference)

    def verify_and_update_path(self, idx: int, text_line: str, path: str, folder_name: str):
        """
        Verifica y actualiza una ruta inválida en la base de datos.
        
        Args:
            idx (int): Índice de la referencia
            text_line (str): Texto de la referencia
            path (str): Ruta a verificar
            folder_name (str): Nombre de la carpeta
        """
        print(f"Verificando y actualizando ruta: {path}")
        
        # Buscar la carpeta en las rutas base
        for base_path in self.paths:
            try:
                for root, dirs, _ in os.walk(base_path):
                    for dir in dirs:
                        if dir == folder_name:
                            new_path = os.path.join(root, dir)
                            if os.path.exists(new_path):
                                print(f"Nueva ruta encontrada: {new_path}")
                                # Actualizar en la base de datos
                                insert_folder(folder_name, new_path)
                                # Agregar a resultados si es una coincidencia exacta
                                if is_exact_match(text_line, folder_name):
                                    if new_path not in self.found_paths:
                                        self.results[idx] = [(new_path, "Carpeta", text_line)]
                                        self.found_paths.add(new_path)
                                        self.new_result.emit(idx, new_path, "Carpeta", text_line)
                                        if "Carpetas" not in self.file_types:
                                            self.search_in_folder(new_path, text_line, idx)
                                # Pre-búsqueda en la nueva ruta
                                self.pre_search_in_db_path(new_path, text_line, idx)
                            return
            except Exception as e:
                print(f"Error verificando ruta {base_path}: {str(e)}")
                continue

    def processPath(self, path):
        if self.isInterruptionRequested():
            return
        try:
            first_level_dirs = next(os.walk(path))[1] # Obtiene los directorios de primer nivel
            for dir in first_level_dirs:
                if '@Recycle' in dir:
                    continue
                dir_path = os.path.join(path, dir)
                for root, dirs, files in os.walk(dir_path):
                    if self.isInterruptionRequested():
                        return
                    self.checkFilesAndDirs(root, dirs, files)
                
                # Actualizar progreso independientemente del tipo de búsqueda
                self.processed_directories += 1
                self.nas_progress.emit((self.processed_directories / self.total_directories) * 100)
                self.directoryProcessed.emit(self.processed_directories, self.total_directories, dir_path)
                
        except (StopIteration, FileNotFoundError, PermissionError):
            self.processed_directories += 1
            self.nas_progress.emit((self.processed_directories / self.total_directories) * 100)
            self.directoryProcessed.emit(self.processed_directories, self.total_directories, path)

    def optimize_paths(self, paths):
        """
        Optimiza la lista de rutas eliminando rutas redundantes.

        Args:
            paths (list): Lista de rutas a optimizar.

        Returns:
            list: Lista optimizada de rutas sin redundancias.
        """
        optimized_paths = []
        paths = sorted(paths, key=lambda x: x.count(os.path.sep), reverse=True)
        for path in paths:
            if not any(path.startswith(op_path) and path != op_path for op_path in optimized_paths):
                optimized_paths.append(path)
        return optimized_paths