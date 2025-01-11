"""
Nombre del Archivo: fileManager.py
Descripción: Manejador de operaciones con archivos y carpetas.
             Encapsula todas las operaciones relacionadas con el sistema de archivos.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

import os
import shutil
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices

class FileManager:
    """
    Manejador de operaciones con archivos y carpetas.
    
    Esta clase encapsula todas las operaciones relacionadas con el sistema de archivos,
    como abrir carpetas, copiar archivos, etc.
    
    Attributes:
        main_controller: Referencia al controlador principal
    """
    
    def __init__(self, main_controller):
        """
        Inicializa el manejador de archivos.
        
        Args:
            main_controller: Referencia al controlador principal
        """
        self.main_controller = main_controller
        
    def open_folder(self, item, column):
        """
        Abre la carpeta o archivo correspondiente al ítem seleccionado.
        
        Args:
            item: Ítem seleccionado en la tabla de resultados
            column: Columna donde se hizo clic
        """
        main_window = self.main_controller.main_window
        path_column = 6 if main_window.search_type == 'Referencia' else 4
        
        path = item.data(path_column, Qt.UserRole)
        if path is None:
            path = item.text(path_column)
            
        if path:
            if os.path.isfile(path):
                folder_path = os.path.dirname(path)
                os.startfile(folder_path)
            else:
                os.startfile(path)
        else:
            print("Error: La ruta es None")
            
    def open_selected(self):
        """Abre las rutas seleccionadas en la tabla de resultados."""
        main_window = self.main_controller.main_window
        for index in range(main_window.results.topLevelItemCount()):
            item = main_window.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                path = item.data(6, Qt.UserRole)
                if path is not None:
                    if os.path.isfile(path):
                        folder_path = os.path.dirname(path)
                        os.startfile(folder_path)
                    else:
                        os.startfile(path)
                else:
                    print("Error: La ruta es None para el ítem:", item.text(1))
                    
    def open_all(self):
        """Abre todas las rutas seleccionadas en el explorador de archivos."""
        main_window = self.main_controller.main_window
        opened_count = 0
        
        for index in range(main_window.results.topLevelItemCount()):
            item = main_window.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                os.system('start "" "{path}"'.format(path=item.data(6, Qt.UserRole)))
                opened_count += 1
                
        if opened_count == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("No hay elementos seleccionados para abrir.")
            msg.setWindowTitle("Información")
            msg.exec_()
            
    def copy_folders(self):
        """Crea copias de las carpetas o archivos seleccionados."""
        main_window = self.main_controller.main_window
        destination_path = QFileDialog.getExistingDirectory(
            main_window, 'Seleccionar ruta de destino'
        )
        
        if not destination_path:
            return
            
        success_copies = []
        failed_copies = []
        
        for index in range(main_window.results.topLevelItemCount()):
            item = main_window.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                source_path = item.data(6, Qt.UserRole)
                file_type = item.text(4)
                
                try:
                    if not os.path.exists(source_path):
                        raise FileNotFoundError(
                            f"El archivo o carpeta '{source_path}' no existe."
                        )
                        
                    if file_type == "Carpeta":
                        shutil.copytree(
                            source_path,
                            os.path.join(destination_path, os.path.basename(source_path)),
                            dirs_exist_ok=True
                        )
                    else:
                        shutil.copy2(source_path, destination_path)
                        
                    success_copies.append(source_path)
                    
                except Exception as e:
                    print(f"Error copiando {source_path}: {e}")
                    failed_copies.append(source_path)
                    
        # Generar mensaje de resumen
        summary_msg = ""
        if success_copies:
            summary_msg += (
                f'Los siguientes archivos fueron copiados correctamente:\n'
                f'{", ".join([os.path.basename(path) for path in success_copies])}\n'
            )
        if failed_copies:
            summary_msg += (
                f'Estos archivos no lograron ser copiados:\n'
                f'{", ".join([os.path.basename(path) for path in failed_copies])}'
            )
        if not success_copies and not failed_copies:
            summary_msg = "No se seleccionaron archivos o carpetas para copiar."
            
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(summary_msg)
        msg.setWindowTitle("Resumen de copia")
        open_button = msg.addButton('Abrir ruta', QMessageBox.ActionRole)
        close_button = msg.addButton('Cerrar', QMessageBox.RejectRole)
        
        msg.exec_()
        
        if msg.clickedButton() == open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(destination_path))
            
    def get_number_from_folder_name(self, folder):
        """
        Extrae un número del nombre de una carpeta.
        
        Args:
            folder (str): Ruta de la carpeta
            
        Returns:
            int: Número extraído del nombre de la carpeta, o 0 si no se encuentra ninguno
        """
        folder_name = os.path.split(folder)[1]
        match = re.search(r'\d+', folder_name)
        return int(match.group(0)) if match else 0
