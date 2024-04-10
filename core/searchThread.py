"""
Nombre del Archivo: searchThread.py
"""
import os
from PyQt5.QtCore import QThread, pyqtSignal

from utils.helpers import is_exact_match, is_ficha_tecnica  # Asegúrate de importar las nuevas funciones aquí

class SearchThread(QThread):
    finished = pyqtSignal(dict)  # Emite un diccionario de resultados
    progress = pyqtSignal(float)  # Modificado para emitir un float que representa el porcentaje
    directoryProcessed = pyqtSignal(int, int, str)  # Asume que emitirá tres valores: processed, total, y path


    def __init__(self, text_lines, text_lines_indices, paths, file_types):
        super().__init__()
        self.text_lines = text_lines
        self.text_lines_indices = text_lines_indices
        self.paths = self.optimize_paths(list(set(paths)))
        self.file_types = file_types
        self.results = {}
        self.found_paths = set()  # Inicializa aquí el atributo 'found_paths'
        self.total_directories = self.count_directories()
        self.processed_directories = 0

    def count_directories(self):
        total = 0
        for path in self.paths:
            try:
                total += len(next(os.walk(path))[1])  # Contar solo directorios en el primer nivel
                print(f"Directorios en {path}: {total}")
            except StopIteration:
                pass  # Manejar el caso de que el directorio esté vacío
        print(f"Total de directorios a procesar: {total}")
        return total

    def run(self):
        for path in self.paths:
            self.processPath(path)
        self.finished.emit(self.results)

    def processPath(self, path):
        # Antes de empezar a procesar cada directorio, verifica si se solicitó interrupción.
        if self.isInterruptionRequested():
            print("Interrupción solicitada, terminando búsqueda en:", path)
            return

        print(f"Iniciando la exploración en: {path}")
        first_level_dirs = next(os.walk(path))[1]
        for dir in first_level_dirs:
            # Verifica la solicitud de interrupción al comienzo de cada iteración.
            if self.isInterruptionRequested():
                print("Interrupción solicitada durante la exploración en:", path)
                return

            dir_path = os.path.join(path, dir)
            for root, dirs, files in os.walk(dir_path):
                # Incluso aquí podría ser prudente verificar la interrupción, especialmente si cada directorio puede contener muchos archivos o subdirectorios.
                if self.isInterruptionRequested():
                    return

                self.checkFilesAndDirs(root, dirs, files)

            self.processed_directories += 1
            progress_percentage = (self.processed_directories / self.total_directories) * 100
            print(f"Directorios procesados: {self.processed_directories}/{self.total_directories}, Progreso: {progress_percentage}%")

            self.progress.emit(min(progress_percentage, 100))
            self.directoryProcessed.emit(self.processed_directories, self.total_directories, path)

        print(f"Finalizando la exploración en: {path}")


    def checkFilesAndDirs(self, root, dirs, files):
        for text_line, idx in self.text_lines_indices.items():
            search_reference = text_line  # Asumiendo que text_line ya es la referencia que buscas

            # Manejo de directorios para Carpetas y Nombre de Mueble
            if "Carpetas" in self.file_types:
                for dir in dirs:
                    full_path = os.path.normpath(os.path.join(root, dir))
                    if is_exact_match(search_reference, dir) and full_path not in self.found_paths:
                        self.results.setdefault(idx, []).append((full_path, "Carpeta", search_reference))
                        self.found_paths.add(full_path)  # Marca la ruta como encontrada

            # Manejo de archivos para Imágenes
            if "Imágenes" in self.file_types:
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if is_exact_match(search_reference, file) and full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Imagen", search_reference))
                            self.found_paths.add(full_path)  # Marca la ruta como encontrada

            # Manejo de archivos para Videos
            if "Videos" in self.file_types:
                for file in files:
                    if file.lower().endswith(('.mp4', '.mov', '.wmv', '.flv', '.avi', '.avchd', '.webm', '.mkv')):
                        full_path = os.path.normpath(os.path.join(root, file))
                        if is_exact_match(search_reference, file) and full_path not in self.found_paths:
                            self.results.setdefault(idx, []).append((full_path, "Video", search_reference))
                            self.found_paths.add(full_path)  # Marca la ruta como encontrada

            # Actualizado para incluir la lógica de Ficha Técnica
            if "Ficha Técnica" in self.file_types:
                for file in files:
                    full_path = os.path.normpath(os.path.join(root, file))
                    if full_path not in self.found_paths:
                        if file.lower().endswith(('.xls', '.xlsx')) and is_ficha_tecnica(search_reference, file):
                            self.results.setdefault(idx, []).append((full_path, "Ficha Técnica", search_reference))
                            self.found_paths.add(full_path)


    def optimize_paths(self, paths):
        optimized_paths = []
        paths = sorted(paths, key=lambda x: x.count(os.path.sep), reverse=True)
        for path in paths:
            if not any(path.startswith(op_path) and path != op_path for op_path in optimized_paths):
                optimized_paths.append(path)
        return optimized_paths