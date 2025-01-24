from PyQt5.QtCore import QThread, pyqtSignal
from typing import Dict, List, Optional

class FolderCreationThread(QThread):
    progress = pyqtSignal(str)  # Para actualizar el estado
    error = pyqtSignal(str)     # Para errores
    finished = pyqtSignal(dict) # Para resultados finales
    
    def __init__(self, folder_manager, references: List[str], db_results: Optional[Dict[str, List[str]]]):
        super().__init__()
        self.folder_manager = folder_manager
        self.references = references
        self.db_results = db_results
        self._is_running = True
        
    def stop(self):
        """Detiene la ejecución del hilo de manera segura"""
        self._is_running = False
        
    def run(self):
        try:
            if not self._is_running:
                return
            
            # Configurar el callback de progreso
            self.folder_manager.set_progress_callback(
                lambda msg: self.progress.emit(msg) if self._is_running else None
            )
                
            # Obtener información de Google Sheets
            self.progress.emit("Obteniendo información de referencias desde Google Sheets...")
            formatted_refs = self.folder_manager.fetch_and_format_with_sheets(self.references)
            
            if not self._is_running:
                return
                
            # Crear carpetas y copiar archivos
            self.progress.emit("Creando estructura de carpetas y copiando archivos...")
            results = self.folder_manager.create_folders_and_copy_files(
                formatted_refs, 
                self.db_results
            )
            
            # Incluir las referencias formateadas en los resultados
            results["formatted_refs"] = formatted_refs
            
            # Si hay archivos pendientes de selección, emitir los resultados sin marcar como completado
            if results.get("pending_files"):
                if self._is_running:
                    self.finished.emit(results)
                return
            
            # Solo si no hay pendientes y el proceso fue exitoso, emitir resultados finales
            if self._is_running and results.get("processed"):
                self.finished.emit(results)
            elif self._is_running:
                self.error.emit("No se pudo procesar ninguna referencia correctamente")
            
        except Exception as e:
            if self._is_running:
                self.error.emit(str(e))
        finally:
            # Limpiar el callback al terminar
            self.folder_manager.set_progress_callback(None) 