# BUSCADOR_REFERENCIAS_RTA/ui/mainWindow.py

"""
Nombre del Archivo: mainWindow.py
Descripción: Este programa es una aplicación de escritorio construida con PyQt5 para buscar y visualizar imágenes.
             Permite al usuario cargar una imagen de referencia, ajustar parámetros de búsqueda como el tipo de imagen
             y el umbral de reconocimiento, y visualizar imágenes similares encontradas en una base de datos.
             Utiliza una interfaz gráfica para facilitar la interacción con el usuario.
Autor: RTA Muebles - Área Soluciones IA
Fecha: 2 de Marzo de 2024
"""

import os
import sys
import re
import shutil
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QGridLayout, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QApplication, QFileDialog,
    QCheckBox, QLabel, QProgressBar, QMessageBox, QAbstractItemView,
    QTreeWidgetItem, QTreeWidget, QHeaderView, QSizePolicy, QMenu, QSplashScreen,
    QGroupBox, QRadioButton, QLineEdit, QCommandLinkButton, QFrame, QButtonGroup
)
from PyQt5.QtCore import Qt, QEvent, QUrl, QSize
from PyQt5.QtGui import (
    QColor, QBrush, QKeySequence, QFont, QDesktopServices, QIcon, QPixmap
)
from core.searchThread import SearchThread
from ui.imageSearchWindow import MainWindow
from ui.resultDetailsWindow import ResultDetailsWindow
from .updateDatabaseDialog import UpdateDatabaseDialog  # Importar el diálogo de actualización de base de datos

def resource_path(relative_path):
    """Obtiene la ruta absoluta al recurso, funciona tanto en desarrollo como en el ejecutable"""
    try:
        # PyInstaller crea un directorio temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class SplashScreen(QSplashScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkboxes = []  # Asegúrate de que esta lista se inicialice en el constructor
        # Configura la pantalla de splash aquí
        splash_image = resource_path("resources/loading.png")
        self.setPixmap(QPixmap(splash_image))

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.initUI()
        self.checkboxes = []  # Inicializar la lista de checkboxes
        self.is_searching = False
        self.changing_all_checkboxes = False
        self.search_thread = None
        self.found_refs = set()     
        self.custom_extensions = []  # Inicializar custom_extensions
        self.update_search_button_state()
        self.action_history = []
        self.action_history.append(self.get_table_state())
        self.start_time = None  # Variable para almacenar el tiempo de inicio
        self.searched_refs = set()  # Inicializar searched_refs
        
        self.search_type = 'Referencia'  # Añadir atributo para el tipo de búsqueda
        self.update_results_headers()  # Configurar encabezados iniciales

        # Deshabilitar botones inicialmente
        self.copy_button.setEnabled(False)
        self.open_all_button.setEnabled(False)
        self.open_selected_button.setEnabled(False)

    def initUI(self):
        self.setWindowTitle('Buscador de Referencias')
        icon_path = resource_path("resources/icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.resize(1200, 850)  # Ajusta el tamaño inicial para mayor espacio

        # Layout principal dividido en dos columnas
        main_layout = QHBoxLayout(central_widget)

        # Columna Izquierda: Configuración de la Búsqueda
        left_column_layout = QVBoxLayout()

        # Columna Derecha: Resultados
        right_column_layout = QVBoxLayout()

        # Agregar las columnas al layout principal con factores de estiramiento
        main_layout.addLayout(left_column_layout, 35)  # Columna Izquierda: 35%
        main_layout.addLayout(right_column_layout, 65)  # Columna Derecha: 65%

        # 1.1 Selección del Tipo de Búsqueda
        search_type_group = QGroupBox("Seleccione el tipo de búsqueda:")
        search_type_layout = QGridLayout()

        # Crear los botones
        self.button_referencia = QPushButton("Referencia")
        self.button_nombre = QPushButton("Nombre de Archivo")
        self.search_image_button = QPushButton("Buscar con Imagen")

        # Configurar solo los botones de referencia y nombre como checkables
        self.button_referencia.setCheckable(True)
        self.button_nombre.setCheckable(True)
        self.button_referencia.setChecked(True)

        # El botón de búsqueda por imagen no es checkable
        self.search_image_button.setCheckable(False)

        # Conectar las señales
        self.button_referencia.clicked.connect(lambda: self.toggle_search_buttons(self.button_referencia))
        self.button_nombre.clicked.connect(lambda: self.toggle_search_buttons(self.button_nombre))
        self.search_image_button.clicked.connect(self.open_image_search_window)

        # Añadir los botones al layout en una fila con 3 columnas
        search_type_layout.addWidget(self.button_referencia, 0, 0)
        search_type_layout.addWidget(self.button_nombre, 0, 1)
        search_type_layout.addWidget(self.search_image_button, 0, 2)

        # Hacer que las columnas se expandan uniformemente
        search_type_layout.setColumnStretch(0, 1)
        search_type_layout.setColumnStretch(1, 1)
        search_type_layout.setColumnStretch(2, 1)

        search_type_group.setLayout(search_type_layout)
        left_column_layout.addWidget(search_type_group)

        # 1.2 Selección de los Tipos de Archivo a Buscar
        file_types_group = QGroupBox("Seleccione los tipos de archivo a buscar:")
        file_types_layout = QGridLayout()

        # Crear los botones para tipos de archivo
        self.btn_folders = QPushButton("Carpetas")
        self.btn_images = QPushButton("Imágenes")
        self.btn_videos = QPushButton("Videos")
        self.btn_ficha_tecnica = QPushButton("Ficha Técnica")
        self.btn_otro_archivo = QPushButton("Otro")
        self.btn_otro_archivo.setCheckable(True)
        self.btn_otro_archivo.setEnabled(False)  # Inhabilitar el botón
        self.btn_otro_archivo.setToolTip('Inhabilitado. En fase de desarrollo.')  # Agregar tooltip
        self.lineEdit_other = QLineEdit()
        self.lineEdit_other.setPlaceholderText("Ingrese extensión (ej: .pdf)")
        self.lineEdit_other.setEnabled(False)

        # Configurar los botones como checkables
        self.btn_folders.setCheckable(True)
        self.btn_images.setCheckable(True)
        self.btn_videos.setCheckable(True)
        self.btn_ficha_tecnica.setCheckable(True)
        self.btn_otro_archivo.setCheckable(True)
        self.btn_folders.setChecked(True)

        # Conectar las señales
        self.btn_folders.clicked.connect(self.updateButtonTextsAndLabels)
        self.btn_images.clicked.connect(self.updateButtonTextsAndLabels)
        self.btn_videos.clicked.connect(self.updateButtonTextsAndLabels)
        self.btn_ficha_tecnica.clicked.connect(self.updateButtonTextsAndLabels)
        self.btn_otro_archivo.clicked.connect(self.toggle_other_lineedit)  # Conectar la señal
        self.btn_otro_archivo.clicked.connect(self.updateButtonTextsAndLabels)

        # Añadir los botones al layout en una distribución de 2 filas x 3 columnas
        file_types_layout.addWidget(self.btn_folders, 0, 0)
        file_types_layout.addWidget(self.btn_images, 0, 1)
        file_types_layout.addWidget(self.btn_videos, 0, 2)
        file_types_layout.addWidget(self.btn_ficha_tecnica, 1, 0)
        file_types_layout.addWidget(self.btn_otro_archivo, 1, 1)
        file_types_layout.addWidget(self.lineEdit_other, 1, 2)

        # Hacer que las columnas se expandan uniformemente
        file_types_layout.setColumnStretch(0, 1)
        file_types_layout.setColumnStretch(1, 1)
        file_types_layout.setColumnStretch(2, 1)

        # Estilo para los botones (ahora sin ancho fijo)
        button_style = """
            QPushButton {
                min-height: 20px;
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:checked {
                background-color: #007bff;
                color: white;
                border-color: #0056b3;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:checked:hover {
                background-color: #0069d9;
            }
        """

        # Aplicar el estilo a todos los botones
        for button in [self.button_referencia, self.button_nombre, self.search_image_button,
                       self.btn_folders, self.btn_images, self.btn_videos,
                       self.btn_ficha_tecnica, self.btn_otro_archivo]:
            button.setStyleSheet(button_style)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Configurar el QLineEdit para que coincida con el estilo
        self.lineEdit_other.setMinimumHeight(30)
        self.lineEdit_other.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Ajustar el espaciado y márgenes de los layouts
        for layout in [search_type_layout, file_types_layout]:
            layout.setSpacing(10)
            layout.setContentsMargins(10, 10, 10, 10)

        file_types_group.setLayout(file_types_layout)
        left_column_layout.addWidget(file_types_group)

        # 1.3 Selección de Rutas para la Búsqueda
        path_selection_group = QGroupBox("Selecciona las rutas en las cuáles quieres buscar:")
        path_selection_layout = QVBoxLayout()

        # Inicializar ambos layouts necesarios primero
        self.path_selections_layout = QVBoxLayout()
        self.custom_paths_layout = QVBoxLayout()
        
        # Añadir los toggle buttons de categorías en tres columnas
        category_grid = QGridLayout()

        # Definir las rutas predeterminadas
        self.default_paths_buttons = {
            "Ambientes": ["\\\\192.168.200.250\\ambientes", "\\\\192.168.200.250\\rtadiseño\\AMBIENTES.3"],
            "Baño": ["\\\\192.168.200.250\\baño", "\\\\192.168.200.250\\rtadiseño\\BAÑO.3"],
            "Cocina": ["\\\\192.168.200.250\\cocina", "\\\\192.168.200.250\\rtadiseño\\COCINA.3"],
            "Dormitorio": ["\\\\192.168.200.250\\dormitorio", "\\\\192.168.200.250\\rtadiseño\\DORMITORIO.3"],
            "Imágenes Muebles": ["\\\\192.168.200.250\\mercadeo\\IMAGENES MUEBLES", "\\\\192.168.200.250\\rtadiseño\\MERCADEO.3\\IMÁGENES MUEBLES"],
            "Animaciones": ["\\\\192.168.200.250\\mercadeo\\ANIMACIÓN 3D", "\\\\192.168.200.250\\rtadiseño\\MERCADEO.3\\ANIMACIONES"],
            "Otro": []  # Nueva opción "Otro" sin rutas predefinidas
        }
        self.default_paths_buttons_widgets = {}

        # Definir estilo para los toggle buttons
        button_style = """
            QPushButton {
                min-height: 20px;
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:checked {
                background-color: #007bff;
                color: white;
                border-color: #0056b3;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:checked:hover {
                background-color: #0069d9;
            }
        """

        # Crear y añadir los toggle buttons al grid
        row = 0
        col = 0
        for label, paths in self.default_paths_buttons.items():
            button = QPushButton(label)
            button.setCheckable(True)
            if label in ["Ambientes", "Baño", "Cocina", "Dormitorio"]:
                button.setChecked(True)
                self.paths.extend(paths)  # Añadir las rutas directamente
            button.setStyleSheet(button_style)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            category_grid.addWidget(button, row, col)
            self.default_paths_buttons_widgets[label] = button
            
            # Conectar señales
            if label == "Otro":
                button.clicked.connect(self.toggle_other_lineedit)
            button.clicked.connect(self.update_paths_from_buttons)
            
            col += 1
            if col > 2:
                col = 0
                row += 1

        # Establecer estiramiento uniforme para las columnas
        category_grid.setColumnStretch(0, 1)
        category_grid.setColumnStretch(1, 1)
        category_grid.setColumnStretch(2, 1)

        path_selection_layout.addLayout(category_grid)

        # Añade los layouts personalizados
        path_selection_layout.addLayout(self.path_selections_layout)
        path_selection_layout.addLayout(self.custom_paths_layout)

        # Añadir los controles de rutas personalizadas
        self.add_path_controls()
        path_selection_group.setLayout(path_selection_layout)
        left_column_layout.addWidget(path_selection_group)  # Añadido a la columna izquierda

        # 1.4 Botones de Control (Movidos después de la selección de rutas)
        control_buttons_layout = QHBoxLayout()
        left_column_layout.addLayout(control_buttons_layout)

        # Botón para pegar información
        self.paste_button = QPushButton("Pegar Información")
        self.paste_button.clicked.connect(self.handlePaste)
        self.paste_button.setFixedHeight(30)
        control_buttons_layout.addWidget(self.paste_button)

        # Botón para borrar la selección actual
        self.delete_button = QPushButton("Borrar Selección")
        self.delete_button.clicked.connect(self.delete_selected)
        self.delete_button.setFixedHeight(30)
        control_buttons_layout.addWidget(self.delete_button)

        # Botón para reiniciar el programa
        self.clear_button = QPushButton("Reiniciar Programa")
        self.clear_button.clicked.connect(self.clear_all)
        self.clear_button.setFixedHeight(30)
        control_buttons_layout.addWidget(self.clear_button)

        # 1.5 Ingreso de Datos
        self.entry = QTableWidget(1, 1)
        self.entry.setHorizontalHeaderLabels(['Contenido'])
        self.entry.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        left_column_layout.addWidget(self.entry)
        self.entry.installEventFilter(self)

        # 2.1 Botón Buscar (Movido aquí)
        self.generate_button = QPushButton("Buscar")
        self.generate_button.clicked.connect(self.generate_text)
        self.generate_button.setFixedHeight(50)
        right_column_layout.addWidget(self.generate_button)

        # 2.2 Barras de Progreso
        # Crear y configurar las barras de progreso
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

        # Añadir las barras de progreso a la columna derecha
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(self.db_progress_bar)
        progress_layout.addWidget(self.nas_progress_bar)
        right_column_layout.addLayout(progress_layout)

        # 2.3 Tabla de Resultados
        self.results = QTreeWidget()
        header = self.results.header()
        header.setDefaultAlignment(Qt.AlignCenter)
        font = QFont("Sans Serif", 7)
        font.setBold(True)
        header.setFont(font)

        self.results.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.results.setHeaderLabels(['', 'ID', 'REF', '###', 'TIPO', 'NOMBRE DE ARCHIVO', 'RUTA'])
        right_column_layout.addWidget(self.results)
        self.results.itemDoubleClicked.connect(self.open_folder)
        self.results.itemClicked.connect(self.handle_item_clicked)
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

        self.results.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self.openContextMenu)

        # 2.4 Botones de Acción
        # Checkbox para seleccionar todos los resultados
        self.checkBox_seleccionar_todos = QCheckBox("Seleccionar todos los resultados")
        self.checkBox_seleccionar_todos.setTristate(True)
        self.checkBox_seleccionar_todos.stateChanged.connect(self.on_select_all_state_changed)
        right_column_layout.addWidget(self.checkBox_seleccionar_todos)

        # **Añadir la etiqueta una sola vez, antes del botón de detalles**
        self.ref_info_label = QLabel("")  # Crear la etiqueta
        self.ref_info_label.setAlignment(Qt.AlignCenter)  # Centrar el texto
        self.ref_info_label.setStyleSheet("font-weight: bold;")  # Texto en negrita
        right_column_layout.addWidget(self.ref_info_label)  # Añadirla al layout

        # Botón para mostrar los detalles de los resultados
        self.show_details_button = QPushButton("Mostrar detalles de resultados")
        self.show_details_button.setFixedHeight(30)
        self.show_details_button.clicked.connect(self.show_result_details)
        right_column_layout.addWidget(self.show_details_button)

        self.selectedCountLabel = QLabel("Elementos seleccionados: 0")
        right_column_layout.addWidget(self.selectedCountLabel)

        self.status_label = QLabel("Listo")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Permitir que el texto se elida (se corte con ...) cuando sea muy largo
        self.status_label.setTextFormat(Qt.PlainText)
        self.status_label.setWordWrap(False)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Estilo para asegurar que el texto se elida
        self.status_label.setStyleSheet("""
            QLabel {
                min-width: 100px;
                max-width: 800px;
                padding: 2px;
            }
        """)
        right_column_layout.addWidget(self.status_label)

        # Botones para copiar referencias encontradas y no encontradas
        copy_buttons_layout = QHBoxLayout()
        right_column_layout.addLayout(copy_buttons_layout)

        # Botón para copiar referencias encontradas
        self.copy_found_button = QPushButton("Copiar REF encontradas")
        self.copy_found_button.clicked.connect(self.copy_found)
        self.copy_found_button.setFixedHeight(30)
        self.copy_found_button.setEnabled(False)
        copy_buttons_layout.addWidget(self.copy_found_button)

        # Botón para copiar referencias no encontradas
        self.copy_not_found_button = QPushButton("Copiar REF no encontradas")
        self.copy_not_found_button.clicked.connect(self.copy_not_found)
        self.copy_not_found_button.setFixedHeight(30)
        self.copy_not_found_button.setEnabled(False)
        copy_buttons_layout.addWidget(self.copy_not_found_button)

        # 2.5 Controles Finales
        # Layout de botones inferiores
        bottom_buttons_layout = QHBoxLayout()
        right_column_layout.addLayout(bottom_buttons_layout)

        self.open_selected_button = QPushButton("Abrir Selección")
        self.open_selected_button.clicked.connect(self.open_selected)
        self.open_selected_button.setFixedHeight(30)
        bottom_buttons_layout.addWidget(self.open_selected_button)

        self.copy_button = QPushButton("Crear Copias")
        self.copy_button.clicked.connect(self.copy_folders)
        self.copy_button.setFixedHeight(30)
        bottom_buttons_layout.addWidget(self.copy_button)

        self.open_all_button = QPushButton("Abrir Rutas")
        self.open_all_button.clicked.connect(self.open_all)
        self.open_all_button.setFixedHeight(30)
        bottom_buttons_layout.addWidget(self.open_all_button)

        # Botón con ícono para actualizar la base de datos
        self.update_db_button = QPushButton()
        self.update_db_button.setIcon(QIcon(resource_path("resources/db_update.png")))
        self.update_db_button.setIconSize(QSize(16, 16))  # Tamaño del ícono
        self.update_db_button.setFixedSize(28, 28)  # Tamaño cuadrado del botón
        self.update_db_button.clicked.connect(self.update_database)
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
        # Alinear a la derecha
        right_column_layout.addWidget(self.update_db_button, 0, Qt.AlignRight)

        # Frame para mostrar estado de búsqueda
        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        frame_layout = QHBoxLayout()
        self.label_busqueda = QLabel("Buscando...")
        frame_layout.addWidget(self.label_busqueda)
        self.frame.setLayout(frame_layout)
        right_column_layout.addWidget(self.frame)
        self.frame.hide()  # Ocultar inicialmente

        self.updateButtonTextsAndLabels()

        # Añadir después de crear todos los checkboxes
        for label, checkbox in self.default_paths_buttons_widgets.items():
            print(f"Estado final del checkbox '{label}':")
            print(f"  - isEnabled(): {checkbox.isEnabled()}")
            print(f"  - isChecked(): {checkbox.isChecked()}")
            print(f"  - isCheckable(): {checkbox.isCheckable()}")

        # Después de crear todos los checkboxes
        self.default_paths_buttons_widgets["Baño"].setEnabled(True)
        self.default_paths_buttons_widgets["Baño"].setCheckable(True)

    # Funciones Placeholder
    def update_database(self):
        """Abre el diálogo de actualización de la base de datos."""
        dialog = UpdateDatabaseDialog(self)
        dialog.exec_()

    def openImageSearchWindow(self):
        """Función placeholder para abrir la ventana de búsqueda por imagen."""
        print("Función 'openImageSearchWindow' llamada. Implementar lógica aquí.")
        pass

    def show_result_details(self):
        """Función placeholder para mostrar detalles de los resultados."""
        print("Función 'show_result_details' llamada. Implementar lógica aquí.")
        pass


    def setup_connections(self):
        if self.search_thread:
            self.search_thread.new_result.connect(self.add_result_item)
            self.search_thread.db_progress.connect(self.update_db_progress)
            self.search_thread.nas_progress.connect(self.update_nas_progress)
            self.search_thread.finished.connect(self.on_search_finished)
            self.search_thread.directoryProcessed.connect(self.updateStatusLabel)

    
    def start_search(self):
        # Lógica para iniciar la búsqueda
        self.search_thread = SearchThread(self.text_lines, self.text_lines_indices, self.paths, self.file_types)
        self.setup_connections()
        self.search_thread.start()

    def handle_item_clicked(self, item, column):
        if column == 0:  # Columna de checkboxes
            selectedItems = self.results.selectedItems()
            checkState = item.checkState(0)
            if len(selectedItems) > 1:
                for selectedItem in selectedItems:
                    if selectedItem is not item:  # Aplica el cambio solo a otros ítems seleccionados, no al clickeado
                        selectedItem.setCheckState(0, checkState)
            self.update_selected_count()  # Actualizar el conteo después de cambiar el estado de los checkboxes
            self.update_action_buttons_state()

    def handlePaste(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        rows = text.split('\n')

        prev_state = self.get_table_state()  # Obtiene el estado actual de la tabla

        currentRow = self.entry.currentRow() if self.entry.currentRow() != -1 else 0
        lastRow = currentRow + len(rows)

        for i, row in enumerate(rows):
            if currentRow + i >= self.entry.rowCount():
                self.entry.insertRow(currentRow + i)
            self.entry.setItem(currentRow + i, 0, QTableWidgetItem(row))

        # Agregar una nueva fila vacía después de pegar
        self.entry.insertRow(lastRow)
        self.entry.setCurrentCell(lastRow, 0)  # Seleccionar la nueva fila vacía

        self.action_history.append(prev_state)  # Agrega el estado anterior de la tabla al historial
        self.action_history.append(self.get_table_state())  # Agrega el estado actual de la tabla al historial     

    def addTableRow(self):
        prev_state = self.get_table_state()  # Obtiene el estado actual de la tabla
        rowCount = self.entry.rowCount()
        self.entry.insertRow(rowCount)
        self.entry.setCurrentCell(rowCount, 0)
        self.action_history.append(prev_state)  # Agrega el estado anterior de la tabla al historial
        self.action_history.append(self.get_table_state())  # Agrega el estado actual de la tabla al historial

    def on_select_all_state_changed(self, state):
        # Indica que se están cambiando todos los checkboxes, lo que puede ser útil para evitar procesamiento innecesario.
        self.changing_all_checkboxes = True

        # Si el estado es 'No seleccionado', desmarca todos los tems de la lista.
        if state == Qt.Unchecked:
            for i in range(self.results.topLevelItemCount()):
                self.results.topLevelItem(i).setCheckState(0, Qt.Unchecked)

        # Si el estado es 'Seleccionado' o 'Parcialmente seleccionado', marca todos los ítems de la lista.
        elif state == Qt.Checked or state == Qt.PartiallyChecked:
            for i in range(self.results.topLevelItemCount()):
                self.results.topLevelItem(i).setCheckState(0, Qt.Checked)

        # Una vez actualizados todos los checkboxes, se restaura la bandera a su estado original.
        self.changing_all_checkboxes = False

        # Actualiza el contador de ítems seleccionados después de cambiar el estado de los checkboxes.
        self.update_selected_count()
        self.update_action_buttons_state()

    def update_selected_count(self):
        # Calcula el número de ítems seleccionados revisando el estado de los checkboxes.
        selected_count = sum(1 for i in range(self.results.topLevelItemCount())
                            if self.results.topLevelItem(i).checkState(0) == Qt.Checked)
        # Actualiza la etiqueta para mostrar el número actual de elementos seleccionados.
        self.selectedCountLabel.setText(f"Elementos seleccionados: {selected_count}")

        # Actualiza el estado del checkbox 'Seleccionar todos' basado en el número de ítems seleccionados.
        if selected_count == 0:
            self.checkBox_seleccionar_todos.blockSignals(True)
            self.checkBox_seleccionar_todos.setCheckState(Qt.Unchecked)
            self.checkBox_seleccionar_todos.blockSignals(False)
        elif selected_count == self.results.topLevelItemCount():
            self.checkBox_seleccionar_todos.blockSignals(True)
            self.checkBox_seleccionar_todos.setCheckState(Qt.Checked)
            self.checkBox_seleccionar_todos.blockSignals(False)
        else:
            self.checkBox_seleccionar_todos.blockSignals(True)
            self.checkBox_seleccionar_todos.setCheckState(Qt.PartiallyChecked)
            self.checkBox_seleccionar_todos.blockSignals(False)

    def eventFilter(self, obj, event):
        # Filtro de eventos para realizar acciones específicas basadas en teclas presionadas.
        if obj == self.entry:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Backspace:
                    # Acción personalizada para suprimir la fila seleccionada con Backspace.
                    self.delete_selected()
                    return True
                elif event.matches(QKeySequence.Paste):
                    # Acción personalizada para pegar información.
                    self.handlePaste()
                    return True
                elif event.matches(QKeySequence.Delete):
                    # Acción personalizada para borrar la selección actual.
                    self.delete_selected()
                    return True
        return super().eventFilter(obj, event)

    def generate_text(self):
        text_lines = [
            self.entry.item(i, 0).text().strip() 
            for i in range(self.entry.rowCount()) 
            if self.entry.item(i, 0) and self.entry.item(i, 0).text().strip()
        ]

        if not self.is_searching:
            print("Iniciando la búsqueda...")
            if not self.paths:
                self.status_label.setText("Por favor, selecciona una ruta primero.")
                return
            if self.search_thread is not None and self.search_thread.isRunning():
                return

            selected_file_types = self.file_types

            self.results.clear()

            text_lines_indices = {line: i for i, line in enumerate(text_lines)}
            self.search_thread = SearchThread(
                text_lines, 
                text_lines_indices, 
                self.paths, 
                selected_file_types, 
                custom_extensions=self.custom_extensions if hasattr(self, 'custom_extensions') else [],
                search_type=self.search_type
            )
            self.search_thread.results = {}

            self.setup_connections()

            self.start_time = time.time()
            self.search_thread.start()

            self.db_progress_bar.setValue(0)
            self.nas_progress_bar.setValue(0)
            self.db_progress_bar.setMaximum(100)
            self.nas_progress_bar.setMaximum(100)
            self.db_progress_bar.setStyleSheet("")
            self.nas_progress_bar.setStyleSheet("")
            self.generate_button.setText('Detener búsqueda')
            print("Iniciando el hilo de búsqueda.")
            self.is_searching = True
            print("Estado de is_searching al iniciar: ", self.is_searching)
            self.ref_info_label.setText("Búsqueda en Progreso:\nse ha encontrado información para 0 de 0 referencias buscadas")
            self.searched_refs = set(text_lines)  # Inicializar searched_refs aquí
        else:
            print("Deteniendo la búsqueda...")
            if self.search_thread is not None and self.search_thread.isRunning():
                self.search_thread.requestInterruption()
                self.search_thread.wait()
                self.status_label.setText("Búsqueda detenida")
                self.generate_button.setText('Buscar')
                print("Búsqueda detenida.")
                self.is_searching = False
                print("Estado de is_searching al detener: ", self.is_searching)
                self.db_progress_bar.setValue(100)
                self.nas_progress_bar.setValue(0)
                self.nas_progress_bar.setMaximum(100)

            self.searched_refs = set(text_lines)
            self.copy_found_button.setEnabled(False)
            self.copy_not_found_button.setEnabled(False)

    def update_db_progress(self, percentage):
        int_percentage = int(percentage)
        self.db_progress_bar.setValue(int_percentage)
        if int_percentage >= 100:
            self.db_progress_bar.setValue(100)
            self.db_progress_bar.setMaximum(100)  # Mantener el valor máximo en 100 para indicar que se ha completado.

    def update_nas_progress(self, percentage):
        int_percentage = int(percentage)
        self.nas_progress_bar.setValue(int_percentage)
        if int_percentage >= 100:
            self.nas_progress_bar.setValue(100)
            self.nas_progress_bar.setMaximum(100)  # Mantener el valor máximo en 100 para indicar que se ha completado.


    def add_result_item(self, idx, path, file_type, search_reference):
        if self.search_type == 'Referencia':
            # Asegura que se añaden 7 elementos para coincidir con el encabezado
            for i in range(self.results.topLevelItemCount()):
                existing_item = self.results.topLevelItem(i)
                existing_path = existing_item.text(6)  # Columna 'RUTA'
                existing_reference = existing_item.text(2)  # Columna 'REF'
                if existing_path == path and existing_reference == search_reference:
                    print(f"Elemento duplicado encontrado: {path}, {search_reference}. No se añadirá de nuevo.")
                    return

            folder_name = os.path.split(path)[1]
            match = re.match(r"([A-Z]+)\s*(\d+)", search_reference)
            if match:
                component1 = match.group(1)
                component2 = match.group(2)
            else:
                component1 = ''
                component2 = ''

            item = QTreeWidgetItem([
                '',  # Seleccionar
                str(idx + 1),  # ID
                component1,  # REF
                component2,  # ###
                file_type,  # TIPO
                folder_name,  # NOMBRE DE ARCHIVO
                path  # RUTA
            ])
            # Configuraciones adicionales del item
            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            item.setTextAlignment(3, Qt.AlignCenter)
            item.setTextAlignment(4, Qt.AlignCenter)
            item.setTextAlignment(5, Qt.AlignLeft)  # Alinear "Nombre de Archivo" a la izquierda
            item.setTextAlignment(6, Qt.AlignLeft)  # Alinear "Ruta" a la izquierda
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            item.setData(6, Qt.UserRole, path)  # Agregar esta línea para almacenar la ruta en el UserRole

        elif self.search_type == 'Nombre de Archivo':
            # Asegura que se añaden 5 elementos para coincidir con el encabezado
            for i in range(self.results.topLevelItemCount()):
                existing_item = self.results.topLevelItem(i)
                existing_path = existing_item.text(4)  # Columna 'RUTA'
                file_name = existing_item.text(3)  # Columna 'NOMBRE DE ARCHIVO'
                if existing_path == path and file_name == os.path.basename(path):
                    print(f"Elemento duplicado encontrado: {path}. No se añadirá de nuevo.")
                    return

            folder_name = os.path.split(path)[1]

            item = QTreeWidgetItem([
                '',  # Seleccionar
                str(idx + 1),  # ID
                file_type,  # TIPO
                folder_name,  # NOMBRE DE ARCHIVO
                path  # RUTA
            ])
            # Configuración de alineación específica para 'Nombre de Archivo'
            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            item.setTextAlignment(3, Qt.AlignLeft)  # Alinear "Nombre de Archivo" a la izquierda
            item.setTextAlignment(4, Qt.AlignLeft)  # Alinear "Ruta" a la izquierda
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            item.setData(4, Qt.UserRole, path)  # Cambiar esta línea para usar la columna correcta (4 para búsqueda por nombre)

        # Inserción del item en la posición correcta
        inserted = False
        for i in range(self.results.topLevelItemCount()):
            existing_item = self.results.topLevelItem(i)
            existing_idx = int(existing_item.text(1)) - 1
            if idx < existing_idx:
                self.results.insertTopLevelItem(i, item)
                inserted = True
                break
        if not inserted:
            self.results.addTopLevelItem(item)

        self.recolor_results()

        # Después de añadir el item, actualizar el contador en tiempo real
        found_refs = set()
        for i in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(i)
            if self.search_type == 'Referencia':
                ref = f"{item.text(2)}{item.text(3)}"  # Combina REF y ###
            else:
                ref = item.text(3)  # Nombre de archivo
            found_refs.add(ref)
        
        # Actualizar el label en tiempo real
        found_count = len(found_refs)
        searched_count = len(self.searched_refs)
        if self.is_searching:
            self.ref_info_label.setText(f"Búsqueda en Progreso:\nse ha encontrado información para {found_count} de {searched_count} referencias buscadas")

    def recolor_results(self):
        last_ref = None
        color = QColor("lightgray")
        for i in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(i)
            if self.search_type == 'Referencia':
                current_ref = item.text(3)  # Columna '###'
            else:
                current_ref = item.text(2)  # Columna 'TIPO'

            if last_ref != current_ref:
                color = QColor("white") if color == QColor("lightgray") else QColor("lightgray")
            for j in range(item.columnCount()):
                item.setBackground(j, QBrush(color))
            last_ref = current_ref

    def colorize_results(self):
        last_ref = None
        color = QColor("lightgray")

        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            component2 = item.text(3)

            if last_ref != component2:
                color = QColor("white") if color == QColor("lightgray") else QColor("lightgray")
            for i in range(item.columnCount()):
                item.setBackground(i, QBrush(color))
            last_ref = component2

        # Genera los datos para la ventana emergente
        detailed_results = {}
        for idx, results in self.search_thread.results.items():
            folders = sum(1 for result in results if result[1] == "Carpeta")
            videos = sum(1 for result in results if result[1] == "Video")
            images = sum(1 for result in results if result[1] == "Imagen")
            tech_sheets = sum(1 for result in results if result[1] == "Ficha Técnica")
            reference = results[0][2] if results else ""
            detailed_results[idx] = {
                "reference": reference,
                "folders": folders,
                "videos": videos,
                "images": images,
                "tech_sheets": tech_sheets
            }
        # Abre la ventana emergente con los detalles
        self.details_window = ResultDetailsWindow(detailed_results, self)
        self.details_window.exec_()

    def on_search_finished(self, results_dict):
        print("\n=== DEBUGGING RESULTADOS ===")
        print(f"Estructura completa de results_dict:")
        end_time = time.time()  
        duration = end_time - self.start_time  
        print(f"La búsqueda tardó {duration:.2f} segundos.")  

        self.status_label.setText("Listo")
        self.db_progress_bar.setValue(100)
        self.db_progress_bar.setMaximum(100)
        self.nas_progress_bar.setValue(100)
        self.nas_progress_bar.setMaximum(100)
        self.is_searching = False
        self.generate_button.setText('Buscar')
        self.copy_found_button.setEnabled(True)
        self.copy_not_found_button.setEnabled(True)

        accumulated_results = {}

        for idx, results in results_dict.items():
            reference = results[0][2] if results else ""
            if reference not in accumulated_results:
                accumulated_results[reference] = []
            accumulated_results[reference].extend(results)

        found_refs = set()
        detailed_results = {}

        for idx, (reference, all_results) in enumerate(accumulated_results.items()):
            folders = sum(1 for result in all_results if result[1] == "Carpeta")
            videos = sum(1 for result in all_results if result[1] == "Video")
            images = sum(1 for result in all_results if result[1] == "Imagen")
            tech_sheets = sum(1 for result in all_results if result[1] == "Ficha Técnica")

            print(f"\nConteo para referencia {reference}:")
            print(f"Carpetas encontradas: {folders}")
            print(f"Videos encontrados: {videos}")
            print(f"Imágenes encontradas: {images}")
            print(f"Fichas técnicas encontradas: {tech_sheets}")

            detailed_results[idx] = {
                "reference": reference,
                "folders": folders,
                "videos": videos,
                "images": images,
                "tech_sheets": tech_sheets,
                "results": all_results  # Añadimos la clave 'results'
            }
            for _, _, search_reference in all_results:
                found_refs.add(search_reference)

        self.found_refs = found_refs

        for row in range(self.entry.rowCount()):
            item = self.entry.item(row, 0)
            if item:
                text_line = item.text().strip()
                found = any(ref in text_line for ref in found_refs)
                if not found:
                    item.setBackground(QColor(255, 200, 200))
                else:
                    item.setBackground(QColor(255, 255, 255))

        found_count = len(found_refs)
        searched_count = len(self.searched_refs)
        # Actualizar el mensaje final
        self.ref_info_label.setText(f"Búsqueda Finalizada:\nse ha encontrado información para {found_count} de {searched_count} referencias buscadas")
        self.results.resizeColumnToContents(6)
        self.recolor_results()

        # Guardar los resultados detallados para uso posterior
        self.detailed_results = detailed_results

        print("\n=== DETAILED RESULTS FINAL ===")
        print(detailed_results)        

    #Función para mostrar los detalles de los resultados (solo cuando el usuario lo solicite)
    def show_result_details(self):
        if hasattr(self, 'detailed_results'):
            self.details_window = ResultDetailsWindow(self.detailed_results, self)
            self.details_window.exec_()
        else:
            QMessageBox.warning(self, "Advertencia", "No hay resultados disponibles para mostrar. Por favor, realiza una búsqueda primero.")

    def highlight_rows(self, found_references):
        for row in range(self.entry.rowCount()):
            item = self.entry.item(row, 0)
            if item:
                text_line = item.text().strip()
                found = any(ref in text_line for ref in found_references)
                if not found:
                    item.setBackground(QColor(255, 200, 200))  # Rojo para no encontradas
                else:
                    item.setBackground(QColor(255, 255, 255))  # Blanco para encontradas

    def get_number_from_folder_name(self, folder):
        # Extrae un número del nombre de una carpeta, útil para ordenar carpetas numricamente.
        folder_name = os.path.split(folder)[1]  # Separa el nombre de la carpeta de la ruta completa.
        match = re.search(r'\d+', folder_name)  # Busca una secuencia numérica en el nombre de la carpeta.
        if match:
            return int(match.group(0))  # Si encuentra un número, lo retorna como entero.
        else:
            return 0  # Si no encuentra un número, retorna 0 como valor predeterminado.

    def open_folder(self, item, column):
        # Determinar la columna de ruta según el tipo de búsqueda
        path_column = 6 if self.search_type == 'Referencia' else 4
        
        # Obtener la ruta del UserRole de la columna correspondiente
        path = item.data(path_column, Qt.UserRole)
        
        # Si no hay ruta en UserRole, intentar obtenerla del texto de la columna
        if path is None:
            path = item.text(path_column)
        
        if path:
            if os.path.isfile(path):
                # Si es un archivo, abre la carpeta que lo contiene
                folder_path = os.path.dirname(path)
                os.startfile(folder_path)
            else:
                # Si es una carpeta, abre la carpeta
                os.startfile(path)
        else:
            print("Error: La ruta es None")

    def delete_selected(self):
        prev_state = self.get_table_state()  # Obtiene el estado actual de la tabla
        selected_rows = set(index.row() for index in self.entry.selectionModel().selectedIndexes())

        for row in sorted(selected_rows, reverse=True):
            self.entry.removeRow(row)

        self.action_history.append(prev_state)  # Agrega el estado anterior de la tabla al historial
        self.action_history.append(self.get_table_state())  # Agrega el estado actual de la tabla al historial

    def clear_all(self):
        """Reinicia todos los elementos de la interfaz a su estado inicial."""
        try:
            # Restablecer checkboxes de tipos de archivo
            self.btn_folders.setChecked(True)
            self.btn_images.setChecked(False)
            self.btn_videos.setChecked(False)
            self.btn_ficha_tecnica.setChecked(False)
            self.btn_otro_archivo.setChecked(False)
            self.lineEdit_other.clear()
            self.lineEdit_other.setEnabled(False)

            # Restablecer checkboxes de rutas predefinidas
            for checkbox in self.default_paths_buttons_widgets.values():
                if checkbox is not None:
                    checkbox.setChecked(False)
                    checkbox.setEnabled(True)

            # Limpiar rutas personalizadas
            self.paths.clear()
            
            # Limpiar ambos layouts
            self.clear_layout(self.custom_paths_layout)
            self.clear_layout(self.path_selections_layout)
            
            # Agregar un nuevo control de ruta vacío
            self.add_path_controls()

            # Resto de la limpieza
            self.entry.clearContents()
            self.entry.setRowCount(1)  # Mantener una fila vacía
            self.results.clear()
            self.updateButtonTextsAndLabels()
            self.status_label.setText("Listo")
            self.ref_info_label.setText("")
            self.db_progress_bar.setValue(0)
            self.nas_progress_bar.setValue(0)
            self.generate_button.setText('Buscar')
            self.is_searching = False
            self.found_refs.clear()
            self.searched_refs.clear()
            self.action_history.clear()
            self.action_history.append(self.get_table_state())
            
            print("Todo ha sido reiniciado.")
            self.update_action_buttons_state()
            
        except Exception as e:
            print(f"Error al limpiar la interfaz: {e}")

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())

    def open_all(self):
        # Abre solo las carpetas seleccionadas en los resultados.
        opened_count = 0
        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                # Utiliza el comando del sistema para abrir la carpeta en el explorador de archivos.
                os.system('start "" "{path}"'.format(path=item.data(6, Qt.UserRole)))
                opened_count += 1
        
        if opened_count == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("No hay elementos seleccionados para abrir.")
            msg.setWindowTitle("Información")
            msg.exec_()
        
    def open_selected(self):
        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                path = item.data(6, Qt.UserRole)
                print(f"Intentando abrir la ruta: {path} para el ítem: {item.text(1)}")  # Debugging print
                if path is not None:
                    if os.path.isfile(path):
                        # Si es un archivo, abre la carpeta que lo contiene
                        folder_path = os.path.dirname(path)
                        os.startfile(folder_path)
                    else:
                        # Si es una carpeta, abre la carpeta
                        os.startfile(path)
                else:
                    print("Error: La ruta es None para el ítem:", item.text(1))

    def copy_folders(self):
        destination_path = QFileDialog.getExistingDirectory(self, 'Seleccionar ruta de destino')
        if not destination_path:
            return

        success_copies = []
        failed_copies = []

        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                source_path = item.data(6, Qt.UserRole)  # Corregido para usar el índice correcto
                file_type = item.text(4)  # Asumiendo que el tipo de archivo está en la columna 4
                try:
                    if not os.path.exists(source_path):
                        raise FileNotFoundError(f"El archivo o carpeta '{source_path}' no existe.")
                    if file_type == "Carpeta":
                        shutil.copytree(source_path, os.path.join(destination_path, os.path.basename(source_path)), dirs_exist_ok=True)
                    else:
                        shutil.copy2(source_path, destination_path)
                    success_copies.append(source_path)
                except Exception as e:
                    print(f"Error copiando {source_path}: {e}")
                    failed_copies.append(source_path)

        # Generar mensaje de resumen
        summary_msg = ""
        if success_copies:
            summary_msg += f'Los siguientes archivos fueron copiados correctamente:\n{", ".join([os.path.basename(path) for path in success_copies])}\n'
        if failed_copies:
            summary_msg += f'Estos archivos no lograron ser copiados:\n{", ".join([os.path.basename(path) for path in failed_copies])}'
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





    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Undo):  # Verifica si se presionó Control + Z
            self.undo_last_action()
            event.accept()
        else:
            # Maneja eventos de presión de teclas específicas.
            if event.key() == Qt.Key_Escape:
                # Ejecuta la función de búsqueda o detención de la misma si se presiona la tecla Escape.
                self.generate_text()
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self.addTableRow()

    def copy_found(self):
        try:
            text_lines = []
            for i in range(self.entry.rowCount()):
                item = self.entry.item(i, 0)
                if item and item.background().color() != QColor(255, 200, 200):
                    text_lines.append(item.text())
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(text_lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al copiar referencias encontradas: {e}")

    def copy_not_found(self):
        try:
            text_lines = []
            for i in range(self.entry.rowCount()):
                item = self.entry.item(i, 0)
                if item and item.background() == QBrush(QColor(255, 200, 200)):  # Rojo
                    text_lines.append(item.text())
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(text_lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al copiar referencias no encontradas: {e}")

    def updateButtonTextsAndLabels(self):
        self.file_types = []
        if self.btn_folders.isChecked():
            self.file_types.append("Carpetas")
        if self.btn_images.isChecked():
            self.file_types.append("Imágenes")
        if self.btn_videos.isChecked():
            self.file_types.append("Videos")
        if self.btn_ficha_tecnica.isChecked():
            self.file_types.append("Ficha Técnica")
        if self.btn_otro_archivo.isChecked():
            self.file_types.append("Otro")
            # Almacenar la extensión personalizada
            self.custom_extensions = [self.lineEdit_other.text().strip()]
        else:
            self.custom_extensions = []
    
        if self.file_types:
            search_text = "Buscar " + " + ".join(self.file_types)
        else:
            search_text = "Selecciona tipo(s) de archivo a buscar"
        self.generate_button.setText(search_text)
        self.update_search_button_state()

    # Funciones para la selección de rutas modificadas:
    def select_path(self, button):
        prev_path = button.text()  # Guarda la ruta anterior, si existe
        new_path = QFileDialog.getExistingDirectory(self, 'Seleccionar ruta de búsqueda')
        if new_path:
            # Actualiza el texto del botón con la nueva ruta
            button.setText(new_path)
            # Si había una ruta previa en el botón, quítala de self.paths
            if prev_path and prev_path in self.paths:
                self.paths.remove(prev_path)
            # Añade la nueva ruta a self.paths
            if new_path not in self.paths:
                self.paths.append(new_path)
            # Activa el botón "+" de la última fila después de seleccionar una ruta.
            if self.path_selections_layout.count() > 0:
                last_path_layout = self.path_selections_layout.itemAt(self.path_selections_layout.count() - 1)
                last_plus_button = last_path_layout.itemAt(1).widget()
                last_plus_button.setEnabled(True)

    def create_path_layout(self):
        path_layout = QHBoxLayout()

        # Renombrar botón según si "Otro" está activo
        if self.default_paths_buttons_widgets["Otro"].isChecked():
            path_button_label = "Agregar otra ruta de búsqueda"
        else:
            path_button_label = "Seleccionar ruta de búsqueda"

        path_button = QPushButton(path_button_label)
        path_button.setCheckable(False)  # Estos botones no son checkables; solo abren el diálogo
        path_button.clicked.connect(lambda: self.select_path(path_button))
        path_button.setEnabled(self.default_paths_buttons_widgets["Otro"].isChecked())  # Habilitado solo si "Otro" está marcado

        btn_add_path = QPushButton("+")
        btn_add_path.setMaximumWidth(30)
        btn_add_path.setEnabled(False)  # El botón "+" se activará después de seleccionar una ruta
        btn_add_path.clicked.connect(self.add_path_controls)
        btn_add_path.setEnabled(False)  # Deshabilitado por defecto

        btn_remove_path = QPushButton("-")
        btn_remove_path.setMaximumWidth(30)
        btn_remove_path.clicked.connect(lambda: self.remove_path_controls(path_layout))
        btn_remove_path.setEnabled(False)  # Deshabilitado por defecto

        path_layout.addWidget(path_button)
        path_layout.addWidget(btn_add_path)
        path_layout.addWidget(btn_remove_path)

        return path_layout

    def add_path_controls(self):
        new_path_layout = self.create_path_layout()
        self.path_selections_layout.addLayout(new_path_layout)
        
        # Asegúrate de que el botón "+" se activa solo en la última fila
        for i in range(self.path_selections_layout.count() - 1):
            path_layout_item = self.path_selections_layout.itemAt(i)
            if path_layout_item is not None:
                path_layout = path_layout_item.layout()
                if path_layout is not None:
                    plus_button = path_layout.itemAt(1).widget()
                    if plus_button is not None:
                        plus_button.setEnabled(False)

        # Activa el botón "+" en la última fila añadida
        last_path_layout_item = self.path_selections_layout.itemAt(self.path_selections_layout.count() - 1)
        if last_path_layout_item is not None:
            last_path_layout = last_path_layout_item.layout()
            if last_path_layout is not None:
                last_plus_button = last_path_layout.itemAt(1).widget()
                if last_plus_button is not None:
                    last_plus_button.setEnabled(True)

    def remove_path_controls(self, layout_to_remove):
        if self.path_selections_layout.count() > 1:
            index_to_remove = self.path_selections_layout.indexOf(layout_to_remove)
            if layout_to_remove:
                path_button = layout_to_remove.itemAt(0).widget()
                path_to_remove = path_button.text()
                
                if path_to_remove in self.paths:
                    self.paths.remove(path_to_remove)
                    print(f"Ruta eliminada: {path_to_remove}")
                    print(f"Rutas restantes: {self.paths}")

                for i in reversed(range(layout_to_remove.count())):
                    widget_to_remove = layout_to_remove.itemAt(i).widget()
                    if widget_to_remove is not None:
                        widget_to_remove.deleteLater()
                self.path_selections_layout.removeItem(layout_to_remove)

            if index_to_remove == self.path_selections_layout.count():
                last_path_layout_item = self.path_selections_layout.itemAt(self.path_selections_layout.count() - 1)
                if last_path_layout_item is not None:
                    last_path_layout = last_path_layout_item.layout()
                    if last_path_layout is not None:
                        last_plus_button = last_path_layout.itemAt(1).widget()
                        if last_plus_button is not None:
                            last_plus_button.setEnabled(True)
        else:
            print("No se puede eliminar la única ruta de búsqueda.")

    def update_search_button_state(self):
        any_checked = self.btn_folders.isChecked() or self.btn_images.isChecked() or \
                      self.btn_videos.isChecked() or self.btn_ficha_tecnica.isChecked()
        self.generate_button.setEnabled(any_checked)

    def openContextMenu(self, position):
        indexes = self.results.selectedIndexes()
        if indexes:
            menu = QMenu()
            copyPathAction = menu.addAction("Copiar ruta de ubicación")
            copyInfoAction = menu.addAction("Copiar información del resultado")  # Nueva acción
            action = menu.exec_(self.results.viewport().mapToGlobal(position))
            if action == copyPathAction:
                self.copyItemPath()
            elif action == copyInfoAction:
                self.copyItemInfo()  # Llama al nuevo método para manejar esta acción

    def get_column_index(self, column_name):
        """
        Returns the column index based on the column name and the search type.
        """
        headers = [self.results.headerItem().text(i) for i in range(self.results.columnCount())]
        try:
            return headers.index(column_name)
        except ValueError:
            return None


    # Métodos actualizados
    def copyItemPath(self):
        selectedItems = self.results.selectedItems()
        if selectedItems:
            clipboard = QApplication.clipboard()
            item = selectedItems[0]
            
            ruta_columna = self.get_column_index('RUTA')
            tipo_columna = self.get_column_index('TIPO')
            
            if ruta_columna is not None and tipo_columna is not None and ruta_columna < self.results.columnCount():
                itemPath = item.text(ruta_columna)
                itemType = item.text(tipo_columna)
                
                # Si es una carpeta, copiar la ruta completa
                if itemType == "Carpeta":
                    clipboard.setText(itemPath)
                else:
                    # Si es un archivo, copiar solo la ruta del directorio contenedor
                    directoryPath = os.path.dirname(itemPath)
                    clipboard.setText(directoryPath)
            else:
                QMessageBox.warning(self, "Error", "No se pudo copiar la ruta. Índice de columna inválido.")

    def copyItemInfo(self):
        selectedItems = self.results.selectedItems()
        if selectedItems:
            clipboard = QApplication.clipboard()
            infoText = ""
            for item in selectedItems:
                if self.search_type == 'Referencia':
                    ref = item.text(self.get_column_index('REF'))
                    num = item.text(self.get_column_index('###'))
                    fileType = item.text(self.get_column_index('TIPO'))
                    itemName = item.text(self.get_column_index('NOMBRE DE ARCHIVO'))
                    itemPath = item.text(self.get_column_index('RUTA'))
                    infoText += f"{ref} {num} - [{fileType}] - ({itemName}): \n{itemPath}\n\n"
                elif self.search_type == 'Nombre de Archivo':
                    fileType = item.text(self.get_column_index('TIPO'))
                    itemName = item.text(self.get_column_index('NOMBRE DE ARCHIVO'))
                    itemPath = item.text(self.get_column_index('RUTA'))
                    infoText += f"[{fileType}] - ({itemName}): \n{itemPath}\n\n"
            
            if infoText:
                clipboard.setText(infoText.strip())
            else:
                QMessageBox.warning(self, "Error", "No se encontró información para copiar.")

    def updateStatusLabel(self, processed, total, path):
        # Obtiene el objeto QFontMetrics del QLabel para calcular cómo ajustar el texto.
        metrics = self.status_label.fontMetrics()

        # Establece el ancho máximo permitido para el texto (podría ser el ancho de la ventana o un valor fijo).
        max_width = self.status_label.width() - 20  # Asumimos 20 píxeles menos para un poco de margen.

        # Usa el método elide para truncar el texto con puntos suspensivos si es demasiado largo.
        elided_path = metrics.elidedText(path, Qt.TextElideMode.ElideMiddle, max_width)

        # Establece el texto ajustado en el QLabel.
        self.status_label.setText(f"Directorios procesados: {processed}/{total}, Revisando: {elided_path}")


    def undo_last_action(self):
        if len(self.action_history) >= 2:
            self.action_history.pop()  # Elimina el estado actual de la tabla del historial
            prev_state = self.action_history.pop()  # Obtiene el estado anterior de la tabla

            self.entry.clearContents()  # Limpia la tabla
            self.entry.setRowCount(len(prev_state))  # Establece el número de filas

            for row, row_data in enumerate(prev_state):
                for column, item_text in enumerate(row_data):
                    item = QTableWidgetItem(item_text)
                    self.entry.setItem(row, column, item)

    def get_table_state(self):
        table_state = []
        for row in range(self.entry.rowCount()):
            row_data = []
            for column in range(self.entry.columnCount()):
                item = self.entry.item(row, column)
                row_data.append(item.text() if item else '')
            table_state.append(row_data)
        return table_state
    
    def update_action_buttons_state(self):
        """Actualiza el estado de los botones de acción basado en las selecciones de checkbox."""
        has_selection = False
        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                has_selection = True
                break
        
        # Actualizar estado de los botones
        self.copy_button.setEnabled(has_selection)
        self.open_all_button.setEnabled(has_selection)
        self.open_selected_button.setEnabled(has_selection)

    def toggle_search_buttons(self, button):
        # Asegurar que solo un botón esté seleccionado
        if button == self.button_referencia:
            self.button_nombre.setChecked(False)
            self.search_type = 'Referencia'
        elif button == self.button_nombre:
            self.button_referencia.setChecked(False)
            self.search_type = 'Nombre de Archivo'
        self.updateButtonTextsAndLabels()
        self.update_results_headers()  # Actualizar encabezados según el tipo de búsqueda
        self.results.clear()  # Limpiar resultados anteriores

    def open_image_search_window(self):
        """Abre la ventana de búsqueda por imagen"""
        from ui.imageSearchWindow import MainWindow
        self.image_search_window = MainWindow()
        self.image_search_window.show()


    def update_paths_from_buttons(self):
        self.paths = []
        print("\nActualizando rutas desde toggle buttons...")  # Depuración
        
        # Primero procesar las rutas predeterminadas
        for label, paths in self.default_paths_buttons.items():
            button = self.default_paths_buttons_widgets.get(label)
            if label != "Otro":
                print(f"Toggle button '{label}': seleccionado={button.isChecked() if button else False}")  # Depuración
                if button and button.isChecked():
                    self.paths.extend(paths)  # Añadir las rutas directamente
                    print(f"Añadidas rutas para {label}: {paths}")  # Depuración
        
        print(f"\nRutas totales después de procesar predeterminadas: {len(self.paths)}")  # Depuración
        
        # Procesar rutas personalizadas solo si "Otro" está marcado
        otro_button = self.default_paths_buttons_widgets.get("Otro")
        if otro_button and otro_button.isChecked():
            for i in range(self.path_selections_layout.count()):
                path_layout_item = self.path_selections_layout.itemAt(i)
                if path_layout_item and path_layout_item.layout():
                    path_button = path_layout_item.layout().itemAt(0).widget()
                    path = path_button.text()
                    if path and path not in ["Seleccionar ruta de búsqueda", "Agregar otra ruta de búsqueda"]:
                        self.paths.append(path)
                        print(f"Añadida ruta personalizada: {path}")  # Depuración
        
        print(f"\nRutas finales: {self.paths}")  # Depuración
        
        # Actualizar estado de los controles de ruta personalizada
        for i in range(self.path_selections_layout.count()):
            path_layout_item = self.path_selections_layout.itemAt(i)
            if path_layout_item and path_layout_item.layout():
                path_layout = path_layout_item.layout()
                path_button = path_layout.itemAt(0).widget()
                btn_add = path_layout.itemAt(1).widget()
                btn_remove = path_layout.itemAt(2).widget()
                
                # Solo modificar los controles si es una ruta personalizada
                if otro_button and otro_button.isChecked():
                    path_button.setEnabled(True)
                    if path_button.text() == "Seleccionar ruta de búsqueda":
                        path_button.setText("Agregar otra ruta de búsqueda")
                    btn_add.setEnabled(True)
                    btn_remove.setEnabled(True)
                else:
                    # No modificar los botones de rutas predeterminadas
                    if path_button.text() in ["Seleccionar ruta de búsqueda", "Agregar otra ruta de búsqueda"]:
                        path_button.setEnabled(False)
                        btn_add.setEnabled(False)
                        btn_remove.setEnabled(False)

    def toggle_other_lineedit(self):
        """Habilita o deshabilita el QLineEdit para tipos de archivo adicionales."""
        self.lineEdit_other.setEnabled(self.btn_otro_archivo.isChecked())

    def toggle_search_buttons(self, button):
        # Asegurar que solo un botón esté seleccionado
        if button == self.button_referencia:
            self.button_nombre.setChecked(False)
            self.search_type = 'Referencia'
        elif button == self.button_nombre:
            self.button_referencia.setChecked(False)
            self.search_type = 'Nombre de Archivo'
        self.updateButtonTextsAndLabels()
        self.update_results_headers()  # Actualizar encabezados según el tipo de búsqueda
        self.results.clear()  # Limpiar resultados anteriores

    def open_image_search_window(self):
        """Abre la ventana de búsqueda por imagen"""
        from ui.imageSearchWindow import MainWindow
        self.image_search_window = MainWindow()
        self.image_search_window.show()


    def update_results_headers(self):
        self.results.clear()  # Limpiar resultados anteriores
        self.results.setHeaderHidden(False)
        
        if self.search_type == 'Referencia':
            self.results.setColumnCount(7)  # Establecer el número correcto de columnas
            self.results.setHeaderLabels(['', 'ID', 'REF', '###', 'TIPO', 'NOMBRE DE ARCHIVO', 'RUTA'])
            self.results.setColumnWidth(0, 40)
            self.results.setColumnWidth(1, 15)
            self.results.setColumnWidth(2, 50)
            self.results.setColumnWidth(3, 50)
            self.results.setColumnWidth(4, 90)
            self.results.setColumnWidth(5, 250)
            self.results.setColumnWidth(6, 200)
            self.results.header().setSectionResizeMode(6, QHeaderView.Stretch)
        elif self.search_type == 'Imagen':
            self.results.setColumnCount(5)  # Establecer el número correcto de columnas
            self.results.setHeaderLabels(['', 'ID', 'TIPO', 'NOMBRE DE ARCHIVO', 'RUTA'])
            self.results.setColumnWidth(0, 40)
            self.results.setColumnWidth(1, 15)
            self.results.setColumnWidth(2, 90)   # TIPO
            self.results.setColumnWidth(3, 250)  # NOMBRE DE ARCHIVO
            self.results.setColumnWidth(4, 200)  # RUTA
            self.results.header().setSectionResizeMode(4, QHeaderView.Stretch)
        else:  # Nombre de Archivo
            self.results.setColumnCount(5)  # Establecer el número correcto de columnas
            self.results.setHeaderLabels(['', 'ID', 'TIPO', 'NOMBRE DE ARCHIVO', 'RUTA'])
            self.results.setColumnWidth(0, 40)
            self.results.setColumnWidth(1, 15)
            self.results.setColumnWidth(2, 90)   # TIPO
            self.results.setColumnWidth(3, 250)  # NOMBRE DE ARCHIVO
            self.results.setColumnWidth(4, 200)  # RUTA
            self.results.header().setSectionResizeMode(4, QHeaderView.Stretch)
        
        self.recolor_results()  # Recolorear filas según corresponda
