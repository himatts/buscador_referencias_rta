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
        Ejecuta el modo de creación de carpetas siguiendo el flujo:
        1. Buscar en base de datos
        2. Mostrar resultados
        3. Buscar en Google Sheets
        4. Formatear referencias
        5. Crear carpetas
        6. Copiar archivos
        """
        try:
            # 1. Obtener referencias de la tabla
            references = []
            entry = self.main_window.entry
            for i in range(entry.rowCount()):
                item = entry.item(i, 0)
                if item and item.text().strip():
                    references.append(item.text().strip())

            if not references:
                QMessageBox.warning(
                    self.main_window,
                    "Atención",
                    "No hay referencias ingresadas."
                )
                return

            # 2. Verificar configuración
            config = self.config
            credentials_path = config.get_google_credentials_path()
            sheet_key = config.get_google_sheet_key()

            if not credentials_path or not sheet_key:
                QMessageBox.warning(
                    self.main_window,
                    "Configuración Incompleta",
                    "Por favor, configure las credenciales de Google Sheets primero."
                )
                self.show_config_dialog()
                return

            # 3. Crear manager si no existe
            if (not self.folder_creation_manager or 
                self.folder_creation_manager.google_credentials_path != credentials_path or
                self.folder_creation_manager.google_sheet_key != sheet_key):
                
                self.folder_creation_manager = ReferenceFolderCreationManager(
                    google_credentials_path=credentials_path,
                    google_sheet_key=sheet_key,
                    desktop_folder_name=config.get_desktop_folder_name()
                )

            # 4. PRIMER PASO: Buscar en base de datos
            self.main_window.status_label.setText("Buscando referencias en la base de datos...")
            db_results = self.folder_creation_manager.search_in_database_only(references)

            # 5. Mostrar resultados de la base de datos
            self.main_window.results.clear()
            found_count = 0
            not_found = []

            for ref, paths in db_results.items():
                if paths:
                    found_count += 1
                    # Mostrar cada ruta encontrada
                    for path in paths:
                        file_type = "Carpeta" if os.path.isdir(path) else "Archivo"
                        self.results_manager._add_reference_result(
                            found_count - 1,
                            path,
                            file_type,
                            ref
                        )
                else:
                    not_found.append(ref)

            # Actualizar etiquetas y contadores
            self.main_window.ref_info_label.setText(
                f"Referencias encontradas: {found_count} | No encontradas: {len(not_found)}"
            )

            # 6. Confirmar continuación
            if not_found:
                msg = "Las siguientes referencias no se encontraron en la base de datos:\n\n"
                msg += "\n".join(not_found)
                msg += "\n\n¿Desea continuar con el proceso de creación de carpetas?"
            else:
                msg = "Todas las referencias fueron encontradas en la base de datos.\n"
                msg += "¿Desea continuar con el proceso de creación de carpetas?"

            if QMessageBox.question(
                self.main_window,
                "Continuar Proceso",
                msg,
                QMessageBox.Yes | QMessageBox.No
            ) != QMessageBox.Yes:
                return

            # 7. SEGUNDO PASO: Buscar en Google Sheets y formatear
            self.main_window.status_label.setText("Obteniendo información de Google Sheets...")
            formatted_refs = self.folder_creation_manager.fetch_and_format_with_sheets(references)

            # 8. Actualizar tabla de contenido con nombres formateados
            for ref_data in formatted_refs:
                if 'error' not in ref_data:
                    # Buscar la referencia original en la tabla y actualizarla
                    for row in range(entry.rowCount()):
                        item = entry.item(row, 0)
                        if item and item.text().strip() == ref_data['original']:
                            item.setText(ref_data['nombre_formateado'])
                            break

            # 9. TERCER PASO: Crear carpetas y copiar archivos
            self.main_window.status_label.setText("Creando carpetas y copiando archivos...")
            results = self.folder_creation_manager.create_folders_and_copy_files(
                formatted_refs,
                db_results
            )

            # 10. Mostrar resumen final
            processed = len(results["processed"])
            errors = len(results["errors"])
            
            msg = f"Proceso completado:\n\n"
            msg += f"Referencias procesadas exitosamente: {processed}\n"
            if errors > 0:
                msg += f"Errores encontrados: {errors}\n\n"
                msg += "Detalles de errores:\n"
                for error in results["errors"]:
                    msg += f"- {error}\n"
            
            if processed > 0:
                msg += "\nDetalles de carpetas creadas:\n"
                for ref in results["processed"]:
                    msg += f"\n{ref['original']}:\n"
                    msg += f"  Carpeta: {ref['target_folder']}\n"
                    if ref['copied_files'].get('pdf'):
                        msg += f"  PDF: {ref['copied_files']['pdf']}\n"
                    if ref['copied_files'].get('rhino'):
                        msg += f"  Rhino: {ref['copied_files']['rhino']}\n"
            
            QMessageBox.information(
                self.main_window,
                "Resultado del Proceso",
                msg
            )
            
            self.main_window.status_label.setText("Proceso completado.")
            
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
        elif button == self.main_window.button_nombre:
            self.main_window.search_type = 'Nombre de Archivo'
        elif button == self.main_window.button_folder_creation:
            self.main_window.search_type = 'FolderCreation'
        
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
