"""
Nombre del Archivo: searchController.py
Descripción: Controlador que maneja el proceso de búsqueda y la comunicación con el SearchThread.
             Gestiona la creación, configuración y control del hilo de búsqueda.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

import time
from PyQt5.QtCore import Qt
from core.searchThread import SearchThread

class SearchController:
    """
    Controlador que maneja el proceso de búsqueda y la comunicación con el SearchThread.
    
    Esta clase se encarga de crear y configurar el SearchThread, conectar sus señales,
    y manejar el inicio y fin de la búsqueda.
    
    Attributes:
        main_controller: Referencia al controlador principal
        search_thread: Instancia del hilo de búsqueda
        start_time: Tiempo de inicio de la búsqueda
    """
    
    def __init__(self, main_controller):
        """
        Inicializa el controlador de búsqueda.
        
        Args:
            main_controller: Referencia al controlador principal
        """
        self.main_controller = main_controller
        self.search_thread = None
        self.start_time = None
        
    def setup_connections(self):
        """Configura las conexiones de señales del hilo de búsqueda."""
        if self.search_thread:
            self.search_thread.new_result.connect(self.main_controller.results_manager.add_result_item)
            self.search_thread.db_progress.connect(self.update_db_progress)
            self.search_thread.nas_progress.connect(self.update_nas_progress)
            self.search_thread.finished.connect(self.on_search_finished)
            self.search_thread.directoryProcessed.connect(self.update_status_label)
            
    def start_search(self):
        """Inicia el proceso de búsqueda."""
        main_window = self.main_controller.main_window
        
        # Obtener las referencias a buscar
        text_lines = []
        for row in range(main_window.entry.rowCount()):
            item = main_window.entry.item(row, 0)
            if item and item.text().strip():
                text_lines.append(item.text().strip())
                
        if not text_lines:
            main_window.status_label.setText("Por favor, ingresa al menos una referencia.")
            return
            
        # Actualizar el conjunto de referencias buscadas
        self.main_controller.searched_refs = set(text_lines)
            
        # Obtener las rutas seleccionadas
        paths = self.main_controller.paths_manager.get_paths()
        if not paths:
            main_window.status_label.setText("Por favor, selecciona una ruta primero.")
            return
            
        # Preparar el hilo de búsqueda
        text_lines_indices = {line: i for i, line in enumerate(text_lines)}
        file_types = self.main_controller.paths_manager.get_selected_file_types()
        
        self.search_thread = SearchThread(
            text_lines,
            text_lines_indices,
            paths,
            file_types,
            custom_extensions=self.main_controller.custom_extensions,
            search_type=main_window.search_type
        )
        
        # Configurar y comenzar la búsqueda
        self.setup_connections()
        self.start_time = time.time()
        self.search_thread.start()
        
        # Actualizar la interfaz
        main_window.db_progress_bar.setValue(0)
        main_window.nas_progress_bar.setValue(0)
        main_window.generate_button.setText('Detener búsqueda')
        self.main_controller.is_searching = True
        main_window.ref_info_label.setText(
            "Búsqueda en Progreso:\nse ha encontrado información para 0 de 0 referencias buscadas"
        )
        
    def stop_search(self):
        """Detiene el proceso de búsqueda."""
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.requestInterruption()
            self.search_thread.wait()
            
        main_window = self.main_controller.main_window
        main_window.status_label.setText("Búsqueda detenida")
        main_window.generate_button.setText('Buscar')
        self.main_controller.is_searching = False
        
        # Actualizar barras de progreso
        main_window.db_progress_bar.setValue(100)
        main_window.nas_progress_bar.setValue(0)
        main_window.nas_progress_bar.setMaximum(100)
        
        # Deshabilitar botones de copiar referencias
        main_window.copy_found_button.setEnabled(False)
        main_window.copy_not_found_button.setEnabled(False)
        
    def update_db_progress(self, percentage):
        """
        Actualiza la barra de progreso de la base de datos.
        
        Args:
            percentage (float): Porcentaje de progreso
        """
        main_window = self.main_controller.main_window
        int_percentage = int(percentage)
        main_window.db_progress_bar.setValue(int_percentage)
        if int_percentage >= 100:
            main_window.db_progress_bar.setValue(100)
            main_window.db_progress_bar.setMaximum(100)
            
    def update_nas_progress(self, percentage):
        """
        Actualiza la barra de progreso del NAS.
        
        Args:
            percentage (float): Porcentaje de progreso
        """
        main_window = self.main_controller.main_window
        int_percentage = int(percentage)
        main_window.nas_progress_bar.setValue(int_percentage)
        if int_percentage >= 100:
            main_window.nas_progress_bar.setValue(100)
            main_window.nas_progress_bar.setMaximum(100)
            
    def update_status_label(self, processed, total, path):
        """
        Actualiza la etiqueta de estado con el progreso actual.
        
        Args:
            processed (int): Número de directorios procesados
            total (int): Total de directorios a procesar
            path (str): Ruta actual siendo procesada
        """
        main_window = self.main_controller.main_window
        metrics = main_window.status_label.fontMetrics()
        max_width = main_window.status_label.width() - 20
        elided_path = metrics.elidedText(path, Qt.ElideMiddle, max_width)
        main_window.status_label.setText(
            f"Directorios procesados: {processed}/{total}, Revisando: {elided_path}"
        )
        
    def on_search_finished(self, results_dict):
        """
        Maneja la finalización de la búsqueda.
        
        Args:
            results_dict (dict): Diccionario con los resultados de la búsqueda
        """
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"La búsqueda tardó {duration:.2f} segundos.")
        
        main_window = self.main_controller.main_window
        
        # Actualizar estado de la interfaz
        main_window.status_label.setText("Listo")
        main_window.db_progress_bar.setValue(100)
        main_window.nas_progress_bar.setValue(100)
        main_window.generate_button.setText('Buscar')
        main_window.copy_found_button.setEnabled(True)
        main_window.copy_not_found_button.setEnabled(True)
        
        self.main_controller.is_searching = False
        
        # Procesar los resultados finales
        self.main_controller.on_search_finished(results_dict)
