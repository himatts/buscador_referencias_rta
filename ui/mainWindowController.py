"""
Nombre del Archivo: mainWindowController.py
Descripción: Controlador principal que maneja la lógica de negocio de la ventana principal.
             Coordina las interacciones entre la interfaz de usuario y los diferentes managers.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

from PyQt5.QtCore import Qt, QUrl, QObject, QEvent
from PyQt5.QtGui import QColor, QBrush, QDesktopServices, QKeySequence
from PyQt5.QtWidgets import (
    QMessageBox, QFileDialog, QApplication, QMenu,
    QTableWidgetItem
)

from managers.searchController import SearchController
from managers.fileManager import FileManager
from managers.pathsManager import PathsManager
from managers.resultsManager import ResultsManager

class MainWindowController(QObject):
    """
    Controlador principal que maneja la lógica de negocio de la ventana principal.
    
    Esta clase actúa como intermediario entre la interfaz de usuario y los diferentes
    managers que manejan funcionalidades específicas.
    
    Attributes:
        main_window: Referencia a la ventana principal
        search_controller: Controlador de búsquedas
        file_manager: Manejador de operaciones con archivos
        paths_manager: Manejador de rutas
        results_manager: Manejador de resultados
    """
    
    def __init__(self, main_window):
        """
        Inicializa el controlador principal.
        
        Args:
            main_window: Referencia a la ventana principal
        """
        super().__init__()
        self.main_window = main_window
        self.search_controller = SearchController(self)
        self.file_manager = FileManager(self)
        self.paths_manager = PathsManager(self)
        self.results_manager = ResultsManager(self)
        
        # Estado de la aplicación
        self.is_searching = False
        self.found_refs = set()
        self.searched_refs = set()
        self.action_history = []
        self.custom_extensions = []
        
    def handle_paste(self):
        """Maneja la acción de pegar desde el portapapeles."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        rows = text.split('\n')
        
        prev_state = self.get_table_state()
        
        entry = self.main_window.entry
        current_row = entry.currentRow() if entry.currentRow() != -1 else 0
        last_row = current_row + len(rows)
        
        for i, row in enumerate(rows):
            if current_row + i >= entry.rowCount():
                entry.insertRow(current_row + i)
            entry.setItem(current_row + i, 0, QTableWidgetItem(row))
            
        entry.insertRow(last_row)
        entry.setCurrentCell(last_row, 0)
        
        self.action_history.append(prev_state)
        self.action_history.append(self.get_table_state())
        
    def delete_selected(self):
        """Elimina las filas seleccionadas de la tabla."""
        prev_state = self.get_table_state()
        entry = self.main_window.entry
        selected_rows = set(index.row() for index in entry.selectionModel().selectedIndexes())
        
        for row in sorted(selected_rows, reverse=True):
            entry.removeRow(row)
            
        self.action_history.append(prev_state)
        self.action_history.append(self.get_table_state())
        
    def clear_all(self):
        """Reinicia todos los elementos de la interfaz."""
        try:
            # Restablecer tipos de archivo
            self.main_window.btn_folders.setChecked(True)
            self.main_window.btn_images.setChecked(False)
            self.main_window.btn_videos.setChecked(False)
            self.main_window.btn_ficha_tecnica.setChecked(False)
            self.main_window.btn_otro_archivo.setChecked(False)
            self.main_window.lineEdit_other.clear()
            self.main_window.lineEdit_other.setEnabled(False)
            
            # Restablecer rutas
            self.paths_manager.reset_paths()
            
            # Limpiar tabla de entrada
            self.main_window.entry.clearContents()
            self.main_window.entry.setRowCount(1)
            
            # Limpiar resultados
            self.main_window.results.clear()
            self.main_window.updateButtonTextsAndLabels()
            self.main_window.status_label.setText("Listo")
            self.main_window.ref_info_label.setText("")
            self.main_window.db_progress_bar.setValue(0)
            self.main_window.nas_progress_bar.setValue(0)
            self.main_window.generate_button.setText('Buscar')
            
            # Restablecer estado
            self.is_searching = False
            self.found_refs.clear()
            self.searched_refs.clear()
            self.action_history.clear()
            self.action_history.append(self.get_table_state())
            
            self.update_action_buttons_state()
            
        except Exception as e:
            print(f"Error al limpiar la interfaz: {e}")
            
    def get_table_state(self):
        """
        Obtiene el estado actual de la tabla.
        
        Returns:
            list: Estado actual de la tabla
        """
        table_state = []
        entry = self.main_window.entry
        for row in range(entry.rowCount()):
            row_data = []
            for column in range(entry.columnCount()):
                item = entry.item(row, column)
                row_data.append(item.text() if item else '')
            table_state.append(row_data)
        return table_state
        
    def update_action_buttons_state(self):
        """Actualiza el estado de los botones de acción."""
        has_selection = False
        results = self.main_window.results
        for index in range(results.topLevelItemCount()):
            item = results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                has_selection = True
                break
                
        self.main_window.copy_button.setEnabled(has_selection)
        self.main_window.open_all_button.setEnabled(has_selection)
        self.main_window.open_selected_button.setEnabled(has_selection)
        
    def toggle_search_buttons(self, button):
        """
        Alterna los botones de tipo de búsqueda.
        
        Args:
            button: Botón que fue presionado
        """
        if button == self.main_window.button_referencia:
            self.main_window.button_nombre.setChecked(False)
            self.main_window.search_type = 'Referencia'
        elif button == self.main_window.button_nombre:
            self.main_window.button_referencia.setChecked(False)
            self.main_window.search_type = 'Nombre de Archivo'
            
        self.main_window.updateButtonTextsAndLabels()
        self.results_manager.update_results_headers()
        self.main_window.results.clear()
        
    def handle_search(self):
        """Maneja el inicio o detención de la búsqueda."""
        if not self.is_searching:
            self.start_search()
        else:
            self.stop_search()
            
    def start_search(self):
        """Inicia el proceso de búsqueda."""
        if not self.paths_manager.get_paths():
            self.main_window.status_label.setText("Por favor, selecciona una ruta primero.")
            return
            
        self.search_controller.start_search()
        
    def stop_search(self):
        """Detiene el proceso de búsqueda."""
        self.search_controller.stop_search()

    def eventFilter(self, obj, event):
        """
        Filtro de eventos para manejar acciones específicas basadas en teclas presionadas.
        """
        if obj == self.main_window.entry:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Backspace:
                    self.delete_selected()
                    return True
                elif event.matches(QKeySequence.Paste):
                    self.handle_paste()
                    return True
                elif event.matches(QKeySequence.Delete):
                    self.delete_selected()
                    return True
        return False

    def keyPressEvent(self, event):
        """
        Maneja los eventos de presión de teclas específicas.
        """
        if event.matches(QKeySequence.Undo):
            self.undo_last_action()
            event.accept()
        else:
            if event.key() == Qt.Key_Escape:
                self.handle_search()
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self.add_table_row()
        
    def on_search_finished(self, results_dict):
        """
        Maneja la finalización de la búsqueda.
        
        Args:
            results_dict: Diccionario con los resultados
        """
        self.results_manager.process_final_results(results_dict)
        self.update_action_buttons_state()
        
    def toggle_other_lineedit(self):
        """Habilita o deshabilita el campo de texto para otros tipos de archivo."""
        self.main_window.lineEdit_other.setEnabled(self.main_window.btn_otro_archivo.isChecked())
        
    def openContextMenu(self, position):
        """Abre el menú contextual en la tabla de resultados."""
        menu = QMenu()
        open_folder = menu.addAction("Abrir carpeta")
        open_folder.triggered.connect(
            lambda: self.file_manager.open_folder(self.main_window.results.currentItem())
        )
        menu.exec_(self.main_window.results.viewport().mapToGlobal(position))
