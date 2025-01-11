"""
Nombre del Archivo: pathsManager.py
Descripción: Manejador de rutas de búsqueda y tipos de archivo.
             Gestiona las rutas predeterminadas, rutas personalizadas y tipos de archivo.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QFileDialog
from PyQt5.QtCore import Qt

class PathsManager:
    """
    Manejador de rutas de búsqueda y tipos de archivo.
    
    Esta clase gestiona las rutas predeterminadas, rutas personalizadas y tipos de archivo
    que se utilizarán en la búsqueda.
    
    Attributes:
        main_controller: Referencia al controlador principal
        default_paths: Diccionario con las rutas predeterminadas
        paths: Lista de rutas activas
    """
    
    def __init__(self, main_controller):
        """
        Inicializa el manejador de rutas.
        
        Args:
            main_controller: Referencia al controlador principal
        """
        self.main_controller = main_controller
        self.paths = []
        
        # Definir las rutas predeterminadas
        self.default_paths = {
            "Ambientes": [
                "\\\\192.168.200.250\\ambientes",
                "\\\\192.168.200.250\\rtadiseño\\AMBIENTES.3"
            ],
            "Baño": [
                "\\\\192.168.200.250\\baño",
                "\\\\192.168.200.250\\rtadiseño\\BAÑO.3"
            ],
            "Cocina": [
                "\\\\192.168.200.250\\cocina",
                "\\\\192.168.200.250\\rtadiseño\\COCINA.3"
            ],
            "Dormitorio": [
                "\\\\192.168.200.250\\dormitorio",
                "\\\\192.168.200.250\\rtadiseño\\DORMITORIO.3"
            ],
            "Imágenes Muebles": [
                "\\\\192.168.200.250\\mercadeo\\IMAGENES MUEBLES",
                "\\\\192.168.200.250\\rtadiseño\\MERCADEO.3\\IMÁGENES MUEBLES"
            ],
            "Animaciones": [
                "\\\\192.168.200.250\\mercadeo\\ANIMACIÓN 3D",
                "\\\\192.168.200.250\\rtadiseño\\MERCADEO.3\\ANIMACIONES"
            ],
            "Otro": []  # Para rutas personalizadas
        }
        
    def get_paths(self):
        """
        Obtiene la lista actual de rutas de búsqueda.
        
        Returns:
            list: Lista de rutas activas
        """
        return self.paths
        
    def reset_paths(self):
        """Reinicia las rutas a su estado inicial."""
        self.paths.clear()
        main_window = self.main_controller.main_window
        
        # Restablecer checkboxes de rutas predefinidas
        for button in main_window.default_paths_buttons_widgets.values():
            if button is not None:
                button.setChecked(False)
                button.setEnabled(True)
                
        # Limpiar layouts de rutas personalizadas
        self.clear_layout(main_window.path_selections_layout)
        self.clear_layout(main_window.custom_paths_layout)
        
        # Agregar un nuevo control de ruta vacío
        self.add_path_controls()
        
    def clear_layout(self, layout):
        """
        Limpia todos los widgets de un layout.
        
        Args:
            layout: Layout a limpiar
        """
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())
                
    def create_path_layout(self):
        """
        Crea un layout para seleccionar rutas de búsqueda adicionales.
        
        Returns:
            QHBoxLayout: Layout con los controles de ruta
        """
        main_window = self.main_controller.main_window
        path_layout = QHBoxLayout()
        
        # Renombrar botón según si "Otro" está activo
        if main_window.default_paths_buttons_widgets["Otro"].isChecked():
            path_button_label = "Agregar otra ruta de búsqueda"
        else:
            path_button_label = "Seleccionar ruta de búsqueda"
            
        path_button = QPushButton(path_button_label)
        path_button.setCheckable(False)
        path_button.clicked.connect(lambda: self.select_path(path_button))
        path_button.setEnabled(main_window.default_paths_buttons_widgets["Otro"].isChecked())
        path_button.setStyleSheet(main_window.button_style)  # Aplicar el mismo estilo
        
        btn_add_path = QPushButton("+")
        btn_add_path.setMaximumWidth(30)
        btn_add_path.setEnabled(False)
        btn_add_path.clicked.connect(self.add_path_controls)
        btn_add_path.setStyleSheet(main_window.button_style)
        
        btn_remove_path = QPushButton("-")
        btn_remove_path.setMaximumWidth(30)
        btn_remove_path.clicked.connect(lambda: self.remove_path_controls(path_layout))
        btn_remove_path.setEnabled(True)  # Cambiar a True para permitir eliminar rutas
        btn_remove_path.setStyleSheet(main_window.button_style)
        
        path_layout.addWidget(path_button)
        path_layout.addWidget(btn_add_path)
        path_layout.addWidget(btn_remove_path)
        
        return path_layout
        
    def select_path(self, button):
        """
        Abre un diálogo para seleccionar una ruta de búsqueda.
        
        Args:
            button: Botón que activó la selección
        """
        prev_path = button.text()
        new_path = QFileDialog.getExistingDirectory(
            self.main_controller.main_window,
            'Seleccionar ruta de búsqueda'
        )
        
        if new_path:
            button.setText(new_path)
            if prev_path and prev_path in self.paths:
                self.paths.remove(prev_path)
            if new_path not in self.paths:
                self.paths.append(new_path)
                
            # Activar el botón "+" de la última fila
            main_window = self.main_controller.main_window
            if main_window.path_selections_layout.count() > 0:
                last_path_layout = main_window.path_selections_layout.itemAt(
                    main_window.path_selections_layout.count() - 1
                )
                last_plus_button = last_path_layout.itemAt(1).widget()
                last_plus_button.setEnabled(True)
                
    def add_path_controls(self):
        """Añade controles para seleccionar rutas de búsqueda personalizadas."""
        main_window = self.main_controller.main_window
        new_path_layout = self.create_path_layout()
        main_window.path_selections_layout.addLayout(new_path_layout)
        
        # Asegurar que el botón "+" se activa solo en la última fila
        for i in range(main_window.path_selections_layout.count() - 1):
            path_layout_item = main_window.path_selections_layout.itemAt(i)
            if path_layout_item is not None:
                path_layout = path_layout_item.layout()
                if path_layout is not None:
                    plus_button = path_layout.itemAt(1).widget()
                    if plus_button is not None:
                        plus_button.setEnabled(False)
                        
        # Activar el botón "+" en la última fila añadida
        last_path_layout_item = main_window.path_selections_layout.itemAt(
            main_window.path_selections_layout.count() - 1
        )
        if last_path_layout_item is not None:
            last_path_layout = last_path_layout_item.layout()
            if last_path_layout is not None:
                last_plus_button = last_path_layout.itemAt(1).widget()
                if last_plus_button is not None:
                    last_plus_button.setEnabled(True)
                    
    def remove_path_controls(self, layout_to_remove):
        """
        Elimina los controles de ruta especificados.
        
        Args:
            layout_to_remove: Layout a eliminar
        """
        main_window = self.main_controller.main_window
        if main_window.path_selections_layout.count() > 1:
            index_to_remove = main_window.path_selections_layout.indexOf(layout_to_remove)
            if layout_to_remove:
                path_button = layout_to_remove.itemAt(0).widget()
                path_to_remove = path_button.text()
                
                if path_to_remove in self.paths:
                    self.paths.remove(path_to_remove)
                    
                for i in reversed(range(layout_to_remove.count())):
                    widget_to_remove = layout_to_remove.itemAt(i).widget()
                    if widget_to_remove is not None:
                        widget_to_remove.deleteLater()
                main_window.path_selections_layout.removeItem(layout_to_remove)
                
            if index_to_remove == main_window.path_selections_layout.count():
                last_path_layout_item = main_window.path_selections_layout.itemAt(
                    main_window.path_selections_layout.count() - 1
                )
                if last_path_layout_item is not None:
                    last_path_layout = last_path_layout_item.layout()
                    if last_path_layout is not None:
                        last_plus_button = last_path_layout.itemAt(1).widget()
                        if last_plus_button is not None:
                            last_plus_button.setEnabled(True)
        else:
            print("No se puede eliminar la única ruta de búsqueda.")
            
    def update_paths_from_buttons(self):
        """Actualiza la lista de rutas basándose en los botones de selección."""
        self.paths = []
        main_window = self.main_controller.main_window
        
        # Procesar rutas predeterminadas
        for label, paths in main_window.default_paths_buttons.items():
            button = main_window.default_paths_buttons_widgets.get(label)
            if label != "Otro":
                if button and button.isChecked():
                    self.paths.extend(paths)
        
        # Procesar rutas personalizadas solo si "Otro" está activo
        otro_button = main_window.default_paths_buttons_widgets.get("Otro")
        if otro_button and otro_button.isChecked():
            # Crear controles de ruta personalizada si no existen
            if main_window.path_selections_layout.count() == 0:
                self.add_path_controls()
            
            # Recopilar rutas personalizadas existentes
            for i in range(main_window.path_selections_layout.count()):
                path_layout_item = main_window.path_selections_layout.itemAt(i)
                if path_layout_item and path_layout_item.layout():
                    path_button = path_layout_item.layout().itemAt(0).widget()
                    path = path_button.text()
                    if path and path not in ["Seleccionar ruta de búsqueda", "Agregar otra ruta de búsqueda"]:
                        self.paths.append(path)
        else:
            # Limpiar controles de ruta personalizada si "Otro" está desactivado
            self.clear_layout(main_window.path_selections_layout)
        
    def update_custom_path_controls(self, otro_button):
        """
        Actualiza el estado de los controles de ruta personalizada.
        
        Args:
            otro_button: Botón de rutas personalizadas
        """
        main_window = self.main_controller.main_window
        for i in range(main_window.path_selections_layout.count()):
            path_layout_item = main_window.path_selections_layout.itemAt(i)
            if path_layout_item and path_layout_item.layout():
                path_layout = path_layout_item.layout()
                path_button = path_layout.itemAt(0).widget()
                btn_add = path_layout.itemAt(1).widget()
                btn_remove = path_layout.itemAt(2).widget()
                
                if otro_button and otro_button.isChecked():
                    path_button.setEnabled(True)
                    if path_button.text() == "Seleccionar ruta de búsqueda":
                        path_button.setText("Agregar otra ruta de búsqueda")
                    btn_add.setEnabled(True)
                    btn_remove.setEnabled(True)
                else:
                    if path_button.text() in ["Seleccionar ruta de búsqueda", "Agregar otra ruta de búsqueda"]:
                        path_button.setEnabled(False)
                        btn_add.setEnabled(False)
                        btn_remove.setEnabled(False)
                        
    def get_selected_file_types(self):
        """
        Obtiene los tipos de archivo seleccionados.
        
        Returns:
            list: Lista de tipos de archivo seleccionados
        """
        main_window = self.main_controller.main_window
        file_types = []
        
        if main_window.btn_folders.isChecked():
            file_types.append("Carpetas")
        if main_window.btn_images.isChecked():
            file_types.append("Imágenes")
        if main_window.btn_videos.isChecked():
            file_types.append("Videos")
        if main_window.btn_ficha_tecnica.isChecked():
            file_types.append("Ficha Técnica")
        if main_window.btn_otro_archivo.isChecked():
            file_types.append("Otro")
            
        return file_types
