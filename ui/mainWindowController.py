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
from managers.referenceFolderCreationManager import ReferenceFolderCreationManager
from managers.chatManager import ChatManager
from utils.config import Config
from ui.configDialog import ConfigDialog
import os

class MainWindowController(QObject):
    """
    Controlador principal que maneja la lógica de negocio de la ventana principal.
    
    Esta clase actúa como intermediario entre la interfaz de usuario y los diferentes
    managers que manejan funcionalidades específicas.
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
        
        # Configuración
        self.config = Config()
        
        # Configuración del gestor de creación de carpetas
        self.folder_creation_manager = None
        
        # Configuración del gestor de chat
        self.chat_manager = None
        
        # Estado de la aplicación
        self.is_searching = False
        self.found_refs = set()
        self.searched_refs = set()
        self.action_history = []
        self.custom_extensions = []

    def show_config_dialog(self):
        """Muestra el diálogo de configuración."""
        dialog = ConfigDialog(self.main_window)
        dialog.exec_()

    def execute_folder_creation_mode(self):
        """
        Ejecuta el modo de creación de carpetas.
        """
        try:
            # 1. Obtener referencias de la tabla
            entry = self.main_window.entry
            references = []
            for row in range(entry.rowCount()):
                item = entry.item(row, 0)
                if item and item.text().strip():
                    references.append(item.text().strip())
                    
            if not references:
                self.main_window.status_label.setText("Por favor, ingresa al menos una referencia.")
                return
                
            # 2. Inicializar managers si no existen
            if not self.folder_creation_manager:
                # Obtener la clave de Google Sheets y ruta de credenciales
                google_sheet_key = self.config.get_google_sheet_key()
                credentials_path = self.config.get_google_credentials_path()
                
                if not google_sheet_key:
                    QMessageBox.critical(
                        self.main_window,
                        "Error de Configuración",
                        "No se ha configurado la clave de Google Sheets.\n"
                        "Por favor, configúrela en el menú de configuración."
                    )
                    return
                    
                if not credentials_path:
                    QMessageBox.critical(
                        self.main_window,
                        "Error de Configuración",
                        "No se han configurado las credenciales de Google.\n"
                        "Por favor, configúrelas en el menú de configuración."
                    )
                    return
                    
                self.folder_creation_manager = ReferenceFolderCreationManager(
                    credentials_path,
                    google_sheet_key,
                    desktop_folder_name=self.config.get_desktop_folder_name()
                )
                
            if not self.chat_manager:
                self.chat_manager = ChatManager(self)
                
            # 3. Desconectar señales existentes de forma segura
            try:
                self.main_window.chat_panel.message_sent.disconnect(self.chat_manager.handle_user_message)
            except:
                pass
            
            try:
                self.chat_manager.llm_response.disconnect(self.main_window.chat_panel.append_message)
            except:
                pass
            
            try:
                self.chat_manager.typing_status_changed.disconnect(self.main_window.chat_panel.set_typing_status)
            except:
                pass
            
            # 4. Conectar señales del chat
            self.main_window.chat_panel.message_sent.connect(self.chat_manager.handle_user_message)
            self.chat_manager.llm_response.connect(self.main_window.chat_panel.append_message)
            self.chat_manager.typing_status_changed.connect(self.main_window.chat_panel.set_typing_status)
            
            # 5. Limpiar el chat y comenzar el proceso
            self.main_window.chat_panel.clear_chat()
            self.chat_manager.start_folder_creation_process(references)
            
        except Exception as e:
            # Si hay error de autenticación, reiniciar el manager
            if "Error en autenticación con Google Sheets" in str(e):
                self.folder_creation_manager = None
                QMessageBox.critical(
                    self.main_window,
                    "Error de Autenticación",
                    "Las credenciales de Google Sheets no son válidas.\n"
                    "Por favor, configure nuevamente las credenciales."
                )
            else:
                QMessageBox.critical(
                    self.main_window,
                    "Error",
                    f"Error durante el proceso:\n{str(e)}"
                )
            self.main_window.status_label.setText("Error en el proceso.")

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
            
            # Limpiar chat
            if self.main_window.chat_panel:
                self.main_window.chat_panel.clear_chat()
            
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
        # Desmarcamos todos los botones excepto el presionado
        buttons = [
            self.main_window.button_referencia,
            self.main_window.button_nombre,
            self.main_window.button_folder_creation
        ]
        
        for btn in buttons:
            if btn != button:
                btn.setChecked(False)
        
        # Aseguramos que el botón presionado esté marcado
        button.setChecked(True)
        
        # Actualizamos el tipo de búsqueda
        if button == self.main_window.button_referencia:
            self.main_window.search_type = 'Referencia'
            self.main_window.chat_panel.hide()
        elif button == self.main_window.button_nombre:
            self.main_window.search_type = 'Nombre de Archivo'
            self.main_window.chat_panel.hide()
        elif button == self.main_window.button_folder_creation:
            self.main_window.search_type = 'FolderCreation'
            self.main_window.chat_panel.show()
        
        self.main_window.updateButtonTextsAndLabels()
        self.results_manager.update_results_headers()
        self.main_window.results.clear()
        
    def handle_search(self):
        """
        Maneja el inicio o detención de la búsqueda según el tipo seleccionado.
        """
        if self.main_window.search_type == 'FolderCreation':
            self.execute_folder_creation_mode()
        else:
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
