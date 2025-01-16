"""
Nombre del Archivo: mainWindow.py
Descripción: Este módulo implementa la interfaz gráfica principal del Buscador de Referencias RTA.
             La aplicación permite buscar y visualizar archivos y carpetas basándose en referencias
             de productos, nombres de archivo o similitud de imágenes.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QGridLayout, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QApplication, QFileDialog,
    QCheckBox, QLabel, QProgressBar, QMessageBox, QAbstractItemView,
    QTreeWidgetItem, QTreeWidget, QHeaderView, QSizePolicy, QMenu, QSplashScreen,
    QGroupBox, QRadioButton, QLineEdit, QCommandLinkButton, QFrame, QButtonGroup,
    QSplitter
)
from PyQt5.QtCore import Qt, QEvent, QUrl, QSize
from PyQt5.QtGui import (
    QColor, QBrush, QKeySequence, QFont, QDesktopServices, QIcon, QPixmap
)

from ui.imageSearchWindow import MainWindow as ImageSearchWindow
from ui.resultDetailsWindow import ResultDetailsWindow
from ui.updateDatabaseDialog import UpdateDatabaseDialog
from ui.chatPanel import ChatPanel

def resource_path(relative_path):
    """
    Obtiene la ruta absoluta a un recurso del proyecto.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SplashScreen(QSplashScreen):
    """Implementa la pantalla de carga inicial de la aplicación."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkboxes = []
        splash_image = resource_path("resources/loading.png")
        self.setPixmap(QPixmap(splash_image))

class App(QMainWindow):
    """
    Ventana principal de la aplicación Buscador de Referencias.
    
    Esta clase implementa la interfaz gráfica principal y delega la lógica de negocio
    al controlador principal y los managers especializados.
    """

    def __init__(self):
        super().__init__()
        self.initUI()
        
        # Importar el controlador después de inicializar la UI para evitar imports circulares
        from ui.mainWindowController import MainWindowController
        self.controller = MainWindowController(self)
        
        self.search_type = 'Referencia'
        self.controller.results_manager.update_results_headers()

        # Deshabilitar botones inicialmente
        self.copy_button.setEnabled(False)
        self.open_all_button.setEnabled(False)
        self.open_selected_button.setEnabled(False)

        # Conectar señales
        self.setup_connections()

    def initUI(self):
        """Configura la interfaz de usuario de la ventana principal."""
        self.setWindowTitle('Buscador de Referencias')
        icon_path = resource_path("resources/icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.resize(1200, 850)

        # Layout principal dividido en dos columnas
        main_layout = QHBoxLayout(central_widget)
        left_column_layout = QVBoxLayout()
        right_column_widget = QWidget()
        right_column_layout = QVBoxLayout(right_column_widget)
        
        # Splitter para la columna derecha
        self.right_splitter = QSplitter(Qt.Horizontal)
        self.right_splitter.setChildrenCollapsible(False)
        
        # Widget principal de la columna derecha
        self.main_right_widget = QWidget()
        self.main_right_layout = QVBoxLayout(self.main_right_widget)
        
        # Panel de chat
        self.chat_panel = ChatPanel()
        self.chat_panel.hide()  # Oculto por defecto
        
        # Agregar widgets al splitter
        self.right_splitter.addWidget(self.main_right_widget)
        self.right_splitter.addWidget(self.chat_panel)
        
        # Configurar proporciones del splitter
        self.right_splitter.setStretchFactor(0, 70)  # 70% para el contenido principal
        self.right_splitter.setStretchFactor(1, 30)  # 30% para el chat
        
        right_column_layout.addWidget(self.right_splitter)
        
        main_layout.addLayout(left_column_layout, 35)
        main_layout.addWidget(right_column_widget, 65)

        # 1.1 Selección del Tipo de Búsqueda
        search_type_group = QGroupBox("Seleccione el tipo de búsqueda:")
        search_type_layout = QGridLayout()

        # Definir estilo común para todos los botones
        self.button_style = """
            QPushButton {
                min-height: 20px;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #007bff;
                color: white;
                border: 1px solid #0056b3;
            }
        """

        # Botones de tipo de búsqueda
        self.button_referencia = QPushButton("Referencia")
        self.button_nombre = QPushButton("Nombre de Archivo")
        self.button_folder_creation = QPushButton("Referencias con creación de carpeta")
        
        # Botón de configuración
        self.config_button = QPushButton()
        self.config_button.setIcon(QApplication.style().standardIcon(QApplication.style().SP_FileDialogDetailedView))
        self.config_button.setIconSize(QSize(20, 20))
        self.config_button.setFixedSize(32, 32)
        self.config_button.setToolTip("Configuración")
        self.config_button.setStyleSheet("""
            QPushButton {
                padding: 3px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #0056b3;
            }
        """)
        
        # Configurar botones como checkables
        self.button_referencia.setCheckable(True)
        self.button_nombre.setCheckable(True)
        self.button_folder_creation.setCheckable(True)
        
        # Aplicar estilo
        self.button_referencia.setStyleSheet(self.button_style)
        self.button_nombre.setStyleSheet(self.button_style)
        self.button_folder_creation.setStyleSheet(self.button_style)
        
        # Agregar botones al layout en dos filas
        search_type_layout.addWidget(self.button_referencia, 0, 0)
        search_type_layout.addWidget(self.button_nombre, 0, 1)
        search_type_layout.addWidget(self.button_folder_creation, 1, 0, 1, 2)  # Span 2 columns
        search_type_layout.addWidget(self.config_button, 1, 2)  # En la segunda fila
        
        # Configurar stretch factors y espaciado
        search_type_layout.setColumnStretch(0, 1)
        search_type_layout.setColumnStretch(1, 1)
        search_type_layout.setColumnStretch(2, 0)  # Menos espacio para el botón de configuración
        search_type_layout.setVerticalSpacing(10)  # Añadir espacio vertical entre filas
        search_type_layout.setHorizontalSpacing(10)  # Añadir espacio horizontal entre columnas
        
        # Activar botón de referencia por defecto
        self.button_referencia.setChecked(True)

        search_type_group.setLayout(search_type_layout)
        left_column_layout.addWidget(search_type_group)

        # 1.2 Selección de los Tipos de Archivo
        file_types_group = QGroupBox("Seleccione los tipos de archivo a buscar:")
        file_types_layout = QGridLayout()

        self.btn_folders = QPushButton("Carpetas")
        self.btn_images = QPushButton("Imágenes")
        self.btn_videos = QPushButton("Videos")
        self.btn_ficha_tecnica = QPushButton("Ficha Técnica")
        self.btn_otro_archivo = QPushButton("Otro")
        self.lineEdit_other = QLineEdit()
        self.lineEdit_other.setPlaceholderText("Ingrese extensión (ej: .pdf)")
        self.lineEdit_other.setEnabled(False)

        self.btn_folders.setCheckable(True)
        self.btn_images.setCheckable(True)
        self.btn_videos.setCheckable(True)
        self.btn_ficha_tecnica.setCheckable(True)
        self.btn_otro_archivo.setCheckable(True)
        self.btn_folders.setChecked(True)

        self.btn_folders.setStyleSheet(self.button_style)
        self.btn_images.setStyleSheet(self.button_style)
        self.btn_videos.setStyleSheet(self.button_style)
        self.btn_ficha_tecnica.setStyleSheet(self.button_style)
        self.btn_otro_archivo.setStyleSheet(self.button_style)

        file_types_layout.addWidget(self.btn_folders, 0, 0)
        file_types_layout.addWidget(self.btn_images, 0, 1)
        file_types_layout.addWidget(self.btn_videos, 0, 2)
        file_types_layout.addWidget(self.btn_ficha_tecnica, 1, 0)
        file_types_layout.addWidget(self.btn_otro_archivo, 1, 1)
        file_types_layout.addWidget(self.lineEdit_other, 1, 2)

        file_types_layout.setColumnStretch(0, 1)
        file_types_layout.setColumnStretch(1, 1)
        file_types_layout.setColumnStretch(2, 1)

        file_types_group.setLayout(file_types_layout)
        left_column_layout.addWidget(file_types_group)

        # 1.3 Selección de Rutas
        path_selection_group = QGroupBox("Selecciona las rutas en las cuáles quieres buscar:")
        path_selection_layout = QVBoxLayout()
        self.path_selections_layout = QVBoxLayout()
        self.custom_paths_layout = QVBoxLayout()

        category_grid = QGridLayout()

        self.default_paths_buttons = {
            "Ambientes": ["\\\\192.168.200.250\\ambientes", "\\\\192.168.200.250\\rtadiseño\\AMBIENTES.3"],
            "Baño": ["\\\\192.168.200.250\\baño", "\\\\192.168.200.250\\rtadiseño\\BAÑO.3"],
            "Cocina": ["\\\\192.168.200.250\\cocina", "\\\\192.168.200.250\\rtadiseño\\COCINA.3"],
            "Dormitorio": ["\\\\192.168.200.250\\dormitorio", "\\\\192.168.200.250\\rtadiseño\\DORMITORIO.3"],
            "Imágenes Muebles": ["\\\\192.168.200.250\\mercadeo\\IMAGENES MUEBLES", "\\\\192.168.200.250\\rtadiseño\\MERCADEO.3\\IMÁGENES MUEBLES"],
            "Animaciones": ["\\\\192.168.200.250\\mercadeo\\ANIMACIÓN 3D", "\\\\192.168.200.250\\rtadiseño\\MERCADEO.3\\ANIMACIONES"],
            "Otro": []
        }
        self.default_paths_buttons_widgets = {}

        row = 0
        col = 0
        for label, paths in self.default_paths_buttons.items():
            button = QPushButton(label)
            button.setCheckable(True)
            if label in ["Ambientes", "Baño", "Cocina", "Dormitorio"]:
                button.setChecked(True)
            button.setStyleSheet(self.button_style)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            category_grid.addWidget(button, row, col)
            self.default_paths_buttons_widgets[label] = button

            col += 1
            if col > 2:
                col = 0
                row += 1

        category_grid.setColumnStretch(0, 1)
        category_grid.setColumnStretch(1, 1)
        category_grid.setColumnStretch(2, 1)

        path_selection_layout.addLayout(category_grid)
        path_selection_layout.addLayout(self.path_selections_layout)
        path_selection_layout.addLayout(self.custom_paths_layout)
        path_selection_group.setLayout(path_selection_layout)
        left_column_layout.addWidget(path_selection_group)

        # 1.4 Botones de Control
        control_buttons_layout = QHBoxLayout()
        left_column_layout.addLayout(control_buttons_layout)

        self.paste_button = QPushButton("Pegar Información")
        self.paste_button.setFixedHeight(30)
        self.paste_button.setStyleSheet(self.button_style)
        control_buttons_layout.addWidget(self.paste_button)

        self.delete_button = QPushButton("Borrar Selección")
        self.delete_button.setFixedHeight(30)
        self.delete_button.setStyleSheet(self.button_style)
        control_buttons_layout.addWidget(self.delete_button)

        self.clear_button = QPushButton("Reiniciar Programa")
        self.clear_button.setFixedHeight(30)
        self.clear_button.setStyleSheet(self.button_style)
        control_buttons_layout.addWidget(self.clear_button)

        # 1.5 Ingreso de Datos
        self.entry = QTableWidget(1, 1)
        self.entry.setHorizontalHeaderLabels(['Contenido'])
        self.entry.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        left_column_layout.addWidget(self.entry)

        # 2.1 Botón Buscar
        self.generate_button = QPushButton("Buscar")
        self.generate_button.setFixedHeight(50)
        self.generate_button.setStyleSheet(self.button_style)
        self.main_right_layout.addWidget(self.generate_button)

        # 2.2 Barras de Progreso
        self.db_progress_bar = QProgressBar(self)
        self.db_progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.db_progress_bar.setAlignment(Qt.AlignCenter)
        self.db_progress_bar.setMaximum(100)
        self.db_progress_bar.setFormat("Base de Datos: %p%")

        self.nas_progress_bar = QProgressBar(self)
        self.nas_progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.nas_progress_bar.setAlignment(Qt.AlignCenter)
        self.nas_progress_bar.setMaximum(100)
        self.nas_progress_bar.setFormat("NAS: %p%")

        progress_layout = QVBoxLayout()
        progress_layout.addWidget(self.db_progress_bar)
        progress_layout.addWidget(self.nas_progress_bar)
        self.main_right_layout.addLayout(progress_layout)

        # 2.3 Tabla de Resultados
        self.results = QTreeWidget()
        header = self.results.header()
        header.setDefaultAlignment(Qt.AlignCenter)
        font = QFont("Sans Serif", 7)
        font.setBold(True)
        header.setFont(font)

        self.results.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.results.setHeaderLabels(['', 'ID', 'REF', '###', 'TIPO', 'NOMBRE DE ARCHIVO', 'RUTA'])
        self.main_right_layout.addWidget(self.results)

        self.results.setColumnWidth(0, 40)
        self.results.setColumnWidth(1, 15)
        self.results.setColumnWidth(2, 50)
        self.results.setColumnWidth(3, 50)
        self.results.setColumnWidth(4, 90)
        self.results.setColumnWidth(5, 250)
        self.results.setColumnWidth(6, 200)
        self.results.setStyleSheet("QTreeWidget::item { height: 22px; }")
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.results.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        header = self.results.header()
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        # 2.4 Botones de Acción
        self.checkBox_seleccionar_todos = QCheckBox("Seleccionar todos los resultados")
        self.checkBox_seleccionar_todos.setTristate(True)
        self.main_right_layout.addWidget(self.checkBox_seleccionar_todos)

        self.ref_info_label = QLabel("")
        self.ref_info_label.setAlignment(Qt.AlignCenter)
        self.ref_info_label.setStyleSheet("font-weight: bold;")
        self.main_right_layout.addWidget(self.ref_info_label)

        self.show_details_button = QPushButton("Mostrar detalles de resultados")
        self.show_details_button.setFixedHeight(30)
        self.show_details_button.setStyleSheet(self.button_style)
        self.main_right_layout.addWidget(self.show_details_button)

        self.selectedCountLabel = QLabel("Elementos seleccionados: 0")
        self.main_right_layout.addWidget(self.selectedCountLabel)

        self.status_label = QLabel("Listo")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.status_label.setTextFormat(Qt.PlainText)
        self.status_label.setWordWrap(False)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status_label.setStyleSheet("""
            QLabel {
                min-width: 100px;
                max-width: 800px;
                padding: 2px;
            }
        """)
        self.main_right_layout.addWidget(self.status_label)

        # Botones para copiar referencias
        copy_buttons_layout = QHBoxLayout()
        self.main_right_layout.addLayout(copy_buttons_layout)

        self.copy_found_button = QPushButton("Copiar REF encontradas")
        self.copy_found_button.setFixedHeight(30)
        self.copy_found_button.setEnabled(False)
        self.copy_found_button.setStyleSheet(self.button_style)
        copy_buttons_layout.addWidget(self.copy_found_button)

        self.copy_not_found_button = QPushButton("Copiar REF no encontradas")
        self.copy_not_found_button.setFixedHeight(30)
        self.copy_not_found_button.setEnabled(False)
        self.copy_not_found_button.setStyleSheet(self.button_style)
        copy_buttons_layout.addWidget(self.copy_not_found_button)

        # 2.5 Controles Finales
        bottom_buttons_layout = QHBoxLayout()
        self.main_right_layout.addLayout(bottom_buttons_layout)

        self.open_selected_button = QPushButton("Abrir Selección")
        self.open_selected_button.setFixedHeight(30)
        self.open_selected_button.setStyleSheet(self.button_style)
        bottom_buttons_layout.addWidget(self.open_selected_button)

        self.copy_button = QPushButton("Crear Copias")
        self.copy_button.setFixedHeight(30)
        self.copy_button.setStyleSheet(self.button_style)
        bottom_buttons_layout.addWidget(self.copy_button)

        self.open_all_button = QPushButton("Abrir Rutas")
        self.open_all_button.setFixedHeight(30)
        self.open_all_button.setStyleSheet(self.button_style)
        bottom_buttons_layout.addWidget(self.open_all_button)

        self.update_db_button = QPushButton()
        self.update_db_button.setIcon(QIcon(resource_path("resources/db_update.png")))
        self.update_db_button.setIconSize(QSize(16, 16))
        self.update_db_button.setFixedSize(28, 28)
        self.update_db_button.setStyleSheet("""
            QPushButton {
                padding: 5px;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                background-color: #f8f8f8;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #d0d0d0;
            }
        """)
        self.main_right_layout.addWidget(self.update_db_button, 0, Qt.AlignRight)

        # Frame para estado de búsqueda
        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        frame_layout = QHBoxLayout()
        self.label_busqueda = QLabel("Buscando...")
        frame_layout.addWidget(self.label_busqueda)
        self.frame.setLayout(frame_layout)
        self.main_right_layout.addWidget(self.frame)
        self.frame.hide()

    def setup_connections(self):
        """Configura las conexiones de señales y slots."""
        # Conexiones de botones principales
        self.paste_button.clicked.connect(self.controller.handle_paste)
        self.delete_button.clicked.connect(self.controller.delete_selected)
        self.clear_button.clicked.connect(self.controller.clear_all)
        self.generate_button.clicked.connect(self.controller.handle_search)
        
        # Conexiones de botones de tipo de búsqueda
        self.button_referencia.clicked.connect(
            lambda: self.controller.toggle_search_buttons(self.button_referencia)
        )
        self.button_nombre.clicked.connect(
            lambda: self.controller.toggle_search_buttons(self.button_nombre)
        )
        self.button_folder_creation.clicked.connect(
            lambda: self.toggle_folder_creation_mode(self.button_folder_creation)
        )
        
        # Conexión del botón de configuración
        self.config_button.clicked.connect(self.controller.show_config_dialog)
        
        # Conexiones de tipos de archivo
        self.btn_folders.clicked.connect(self.controller.paths_manager.update_paths_from_buttons)
        self.btn_images.clicked.connect(self.controller.paths_manager.update_paths_from_buttons)
        self.btn_videos.clicked.connect(self.controller.paths_manager.update_paths_from_buttons)
        self.btn_ficha_tecnica.clicked.connect(self.controller.paths_manager.update_paths_from_buttons)
        self.btn_otro_archivo.clicked.connect(self.controller.toggle_other_lineedit)
        
        # Conexiones de rutas
        for button in self.default_paths_buttons_widgets.values():
            button.clicked.connect(self.controller.paths_manager.update_paths_from_buttons)
        
        # Conexiones de resultados
        self.results.itemDoubleClicked.connect(self.controller.file_manager.open_folder)
        self.results.itemClicked.connect(self.handle_item_clicked)
        self.results.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self.controller.openContextMenu)
        
        # Conexiones de acciones
        self.checkBox_seleccionar_todos.stateChanged.connect(
            self.controller.results_manager.on_select_all_state_changed
        )
        self.show_details_button.clicked.connect(self.show_result_details)
        self.copy_found_button.clicked.connect(self.controller.results_manager.copy_found)
        self.copy_not_found_button.clicked.connect(self.controller.results_manager.copy_not_found)
        self.open_selected_button.clicked.connect(self.controller.file_manager.open_selected)
        self.copy_button.clicked.connect(self.controller.file_manager.copy_folders)
        self.open_all_button.clicked.connect(self.controller.file_manager.open_all)
        self.update_db_button.clicked.connect(self.update_database)
        
        # Instalar filtro de eventos
        self.entry.installEventFilter(self.controller)

        # Modificar la conexión del botón "Otro" para rutas personalizadas
        otro_button = self.default_paths_buttons_widgets.get("Otro")
        if otro_button:
            otro_button.clicked.connect(self.handle_otro_button_click)
            
        # Actualizar rutas iniciales
        self.controller.paths_manager.update_paths_from_buttons()

    def handle_item_clicked(self, item, column):
        """Maneja el evento de clic en un ítem de la tabla de resultados."""
        if column == 0:  # Columna de checkboxes
            selectedItems = self.results.selectedItems()
            checkState = item.checkState(0)
            if len(selectedItems) > 1:
                for selectedItem in selectedItems:
                    if selectedItem is not item:
                        selectedItem.setCheckState(0, checkState)
            self.controller.results_manager.update_selected_count()
            self.controller.update_action_buttons_state()

    def show_result_details(self):
        """Muestra la ventana de detalles de resultados."""
        if hasattr(self, 'detailed_results'):
            self.details_window = ResultDetailsWindow(self.detailed_results, self)
            self.details_window.exec_()
        else:
            QMessageBox.warning(
                self, 
                "Advertencia", 
                "No hay resultados disponibles para mostrar. Por favor, realiza una búsqueda primero."
            )

    def open_image_search_window(self):
        """Abre la ventana de búsqueda por imagen."""
        self.image_search_window = ImageSearchWindow()
        self.image_search_window.show()

    def update_database(self):
        """Abre el diálogo de actualización de la base de datos."""
        dialog = UpdateDatabaseDialog(self)
        dialog.exec_()
        
    def updateButtonTextsAndLabels(self):
        """Actualiza los textos de los botones y etiquetas según el tipo de búsqueda."""
        if self.search_type == 'Referencia':
            self.copy_found_button.setText("Copiar REF encontradas")
            self.copy_not_found_button.setText("Copiar REF no encontradas")
        elif self.search_type == 'Nombre de Archivo':
            self.copy_found_button.setText("Copiar nombres encontrados")
            self.copy_not_found_button.setText("Copiar nombres no encontrados")
        elif self.search_type == 'FolderCreation':
            self.copy_found_button.setText("Copiar REF encontradas")
            self.copy_not_found_button.setText("Copiar REF no encontradas")

    def handle_otro_button_click(self):
        """Maneja el clic en el botón 'Otro' de rutas personalizadas."""
        otro_button = self.default_paths_buttons_widgets.get("Otro")
        if otro_button.isChecked():
            # Si se activa "Otro", mostrar controles de ruta personalizada
            if self.path_selections_layout.count() == 0:
                self.controller.paths_manager.add_path_controls()
        else:
            # Si se desactiva "Otro", limpiar controles de ruta personalizada
            while self.path_selections_layout.count():
                item = self.path_selections_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    while item.layout().count():
                        subitem = item.layout().takeAt(0)
                        if subitem.widget():
                            subitem.widget().deleteLater()

    def toggle_folder_creation_mode(self, button):
        """
        Maneja el cambio al modo de creación de carpetas.
        Muestra u oculta el panel de chat según corresponda.
        """
        self.controller.toggle_search_buttons(button)
        self.chat_panel.setVisible(button.isChecked())
