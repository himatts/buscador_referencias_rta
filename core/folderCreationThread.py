from PyQt5.QtCore import QThread, pyqtSignal
from typing import Dict, List, Optional
import queue
import threading
import os

class FolderCreationThread(QThread):
    progress = pyqtSignal(str)  # Para actualizar el estado
    error = pyqtSignal(str)     # Para errores
    finished = pyqtSignal(dict) # Para resultados finales
    rhinoSelectionRequired = pyqtSignal(dict)  # Para solicitar selección de archivo Rhino
    
    def __init__(self, folder_manager, references: List[str], db_results: Optional[Dict[str, List[str]]], 
                 format_only: bool = False, formatted_refs: Optional[List[Dict]] = None):
        super().__init__()
        self.folder_manager = folder_manager
        self.references = references
        self.db_results = db_results
        self.format_only = format_only  # Nuevo flag para indicar si solo formateamos nombres
        self.formatted_refs = formatted_refs  # Referencias ya formateadas
        self._is_running = True
        self._state_lock = threading.Lock()
        self._waiting_for_selection = False
        self._selection_queue = queue.Queue()
        self._current_reference = None
        self._current_results = {}
        
    def stop(self):
        """Detiene la ejecución del hilo de manera segura"""
        self._is_running = False
        
    def set_rhino_selection(self, reference: str, selected_path: Optional[str]):
        """
        Recibe la selección de archivo Rhino del usuario.
        
        Args:
            reference: Referencia para la que se seleccionó el archivo
            selected_path: Ruta del archivo seleccionado o None si se omitió
        """
        if self._waiting_for_selection and reference == self._current_reference:
            self._selection_queue.put((reference, selected_path))
            
    def run(self):
        try:
            if not self._is_running:
                return
            
            # Configurar el callback de progreso
            self.folder_manager.set_progress_callback(
                lambda msg: self.progress.emit(msg) if self._is_running else None
            )
            
            # Si necesitamos formatear nombres
            if not self.formatted_refs:
                # Obtener información de Google Sheets
                self.progress.emit("Obteniendo información de referencias desde Google Sheets...")
                formatted_refs = self.folder_manager.fetch_and_format_with_sheets(self.references)
            else:
                # Usar las referencias ya formateadas
                formatted_refs = self.formatted_refs
                
            if not self._is_running:
                return
            
            # Si solo estamos formateando nombres, retornar los resultados
            if self.format_only:
                self.finished.emit({
                    "formatted_refs": formatted_refs,
                    "format_complete": True
                })
                return
                
            # Procesar cada referencia
            results = {"processed": [], "errors": [], "pending_files": {}}
            total_refs = len(formatted_refs)
            
            # Guardar los resultados de la BD en el estado del folder_manager
            self.folder_manager._processing_state = {
                "db_results": self.db_results,
                "refs_to_process": formatted_refs
            }
            
            for index, ref_data in enumerate(formatted_refs, 1):
                if not self._is_running:
                    return
                    
                try:
                    # Asegurarnos de que nombre_formateado existe en ref_data
                    formatted_name = ref_data.get('nombre_formateado', ref_data['original'])
                    self.progress.emit(f"Procesando referencia {index} de {total_refs}: <b>{formatted_name}</b>")
                    
                    # Verificar si la referencia tiene resultados en la BD
                    if ref_data['original'] not in self.db_results:
                        raise ValueError(f"No se encontraron resultados en la base de datos para {ref_data['original']}")
                    
                    # Crear carpeta y buscar archivos
                    ref_result = self.folder_manager.prepare_folder_creation(ref_data)
                    
                    # Si hay múltiples archivos Rhino, solicitar selección
                    if ref_result.get("rhino_alternatives"):
                        self._current_reference = ref_data["original"]
                        self._waiting_for_selection = True
                        
                        # Emitir señal con la información necesaria
                        selection_data = {
                            "original": ref_data["original"],
                            "nombre_formateado": ref_data["nombre_formateado"],
                            "rhino_alternatives": ref_result["rhino_alternatives"],
                            "target_folder": ref_result["target_folder"],
                            "is_last": index == total_refs  # Indicar si es la última referencia
                        }
                        self.rhinoSelectionRequired.emit(selection_data)
                        
                        # Esperar la selección del usuario
                        reference, selected_path = self._selection_queue.get()
                        self._waiting_for_selection = False
                        
                        # Completar la creación con el archivo seleccionado o sin él
                        final_result = self.folder_manager.complete_folder_creation(
                            ref_data["original"],
                            selected_path  # Puede ser None si se omitió
                        )
                        if final_result.get("processed"):
                            results["processed"].extend(final_result["processed"])
                        if final_result.get("errors"):
                            results["errors"].extend(final_result["errors"])
                    else:
                        # Si no hay alternativas, completar directamente
                        final_result = self.folder_manager.complete_folder_creation(
                            ref_data["original"],
                            ref_result.get("rhino_path")  # Puede ser None
                        )
                        if final_result.get("processed"):
                            results["processed"].extend(final_result["processed"])
                        if final_result.get("errors"):
                            results["errors"].extend(final_result["errors"])
                            
                    # Emitir progreso después de cada referencia procesada
                    self.progress.emit(f"Completada referencia {index} de {total_refs}")
                    
                except Exception as e:
                    error_msg = f"Error procesando {ref_data['original']}: {str(e)}"
                    results["errors"].append(error_msg)
                    self.progress.emit(f"Error en referencia {index} de {total_refs}: {error_msg}")
            
            # Emitir resultados finales si el proceso no fue detenido
            if self._is_running:
                self.progress.emit("Proceso completado. Generando resumen final...")
                self.finished.emit(results)
            
        except Exception as e:
            if self._is_running:
                self.error.emit(str(e))
        finally:
            # Limpiar el callback y estado al terminar
            self.folder_manager.set_progress_callback(None)
            self._waiting_for_selection = False
            self._current_reference = None 