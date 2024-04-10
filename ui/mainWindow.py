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
import re
import shutil
from PyQt5.QtWidgets import (QMainWindow, QWidget, QPushButton, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QApplication, QFileDialog,
                             QCheckBox, QLabel, QProgressBar, QMessageBox, QAbstractItemView,
                             QTreeWidgetItem, QTreeWidget, QHeaderView, QSizePolicy, QMenu, QSplashScreen)
from PyQt5.QtCore import Qt, QEvent, QUrl
from PyQt5.QtGui import QColor, QBrush, QKeySequence, QFont, QDesktopServices, QIcon, QPixmap
from core.searchThread import SearchThread
from ui.imageSearchWindow import MainWindow

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        # Inicializa variables de instancia para almacenar el estado de la aplicación.
        self.initUI()  # Llama a la función para construir la interfaz de usuario.
        self.paths = []  # Inicializa una lista vacía para almacenar las rutas seleccionadas
        self.is_searching = False  # Bandera para indicar si se está realizando una búsqueda.
        self.changing_all_checkboxes = False  # Bandera para controlar la actualización de checkboxes.
        self.search_thread = None  # Variable para almacenar el hilo de búsqueda.
        self.found_refs = set()  # Conjunto para almacenar las referencias encontradas.
        self.update_search_button_state()
        self.action_history = []  # Lista para almacenar el historial de acciones
        self.action_history.append(self.get_table_state())  # Agrega el estado inicial de la tabla
        

    def initUI(self):
        # Configura propiedades iniciales de la ventana.
        self.setWindowTitle('Buscador de Referencias')
        icon_path = os.path.join(os.path.dirname(__file__), '../resources/icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Usa self.main_layout como el layout principal
        self.main_layout = QVBoxLayout(central_widget)

        # Asegúrate de que la siguiente línea esté antes de llamar a self.add_path_controls()
        self.path_selections_layout = QVBoxLayout()

        self.resize(800, 840)  # Establece el tamaño inicial de la ventana.

        # Sección de botones superiores.
        upper_buttons_layout = QHBoxLayout()
        self.main_layout.addLayout(upper_buttons_layout)  # Corrige aquí para usar self.main_layout

        # Botón para pegar información.
        self.paste_button = QPushButton("Pegar Información")
        self.paste_button.clicked.connect(self.handlePaste)
        self.paste_button.setFixedHeight(30)
        upper_buttons_layout.addWidget(self.paste_button)

        # Botón para borrar la selección actual.
        self.delete_button = QPushButton("Borrar Selección")
        self.delete_button.clicked.connect(self.delete_selected)
        self.delete_button.setFixedHeight(30)
        upper_buttons_layout.addWidget(self.delete_button)

        # Botón para borrar todo.
        self.clear_button = QPushButton("Borrar Todo")
        self.clear_button.clicked.connect(self.clear_all)
        self.clear_button.setFixedHeight(30)
        upper_buttons_layout.addWidget(self.clear_button)

        # Sección de botones para copiar resultados.
        copy_buttons_layout = QHBoxLayout()  # Layout horizontal para los botones de copia.
        self.main_layout.addLayout(copy_buttons_layout)  # Agrega el layout de botones de copia al layout principal.

        # Botón para copiar referencias encontradas.
        self.copy_found_button = QPushButton("Copiar REF encontradas")
        self.copy_found_button.clicked.connect(self.copy_found)
        self.copy_found_button.setFixedHeight(30)
        self.copy_found_button.setEnabled(False)  # Deshabilita el botón al inicio.
        copy_buttons_layout.addWidget(self.copy_found_button)

        # Botón para copiar referencias no encontradas.
        self.copy_not_found_button = QPushButton("Copiar REF no encontradas")
        self.copy_not_found_button.clicked.connect(self.copy_not_found)
        self.copy_not_found_button.setFixedHeight(30)
        self.copy_not_found_button.setEnabled(False)  # Deshabilita el botón al inicio.
        copy_buttons_layout.addWidget(self.copy_not_found_button)
    
        # Agregar el botón para abrir la búsqueda por imagen
        self.search_image_button = QPushButton("Buscar con Imagen")
        self.search_image_button.clicked.connect(self.openImageSearchWindow)
        self.search_image_button.setFixedHeight(30)
        copy_buttons_layout.addWidget(self.search_image_button)

        # Tabla para entrada de datos.
        self.entry = QTableWidget(1, 1)  # Tabla sin filas iniciales y una columna.
        self.entry.setHorizontalHeaderLabels(['Contenido'])  # Establece el encabezado de la columna.
        self.entry.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # Ajusta la columna para ocupar todo el ancho disponible.
        self.main_layout.addWidget(self.entry)  # Agrega la tabla al layout principal.
        self.entry.installEventFilter(self)  # Permite que la tabla responda a eventos de filtro.

        # Layout principal para contener las dos secciones lado a lado
        both_sections_layout = QHBoxLayout()

        # Layout de cuadrícula para la selección de tipos de archivo
        file_types_grid = QGridLayout()
        
        # Creando el QLabel para instrucciones y añadiéndolo en la primera fila
        file_types_label = QLabel("Selecciona los tipos de archivos a buscar:")
        file_types_grid.addWidget(file_types_label, 0, 0, 1, -1)  # Coloca el label en la fila 0, columna 0, abarcando 1 fila y todas las columnas
        
        # Actualizar CheckBoxes
        self.cb_folders = QCheckBox("Carpetas")
        self.cb_images = QCheckBox("Imágenes")
        self.cb_videos = QCheckBox("Videos")
        self.cb_ficha_tecnica = QCheckBox("Ficha Técnica")  # Nuevo CheckBox para Ficha Técnica

        # Actualiza las conexiones
        self.cb_folders.stateChanged.connect(self.updateButtonTextsAndLabels)
        self.cb_images.stateChanged.connect(self.updateButtonTextsAndLabels)
        self.cb_videos.stateChanged.connect(self.updateButtonTextsAndLabels)
        self.cb_ficha_tecnica.stateChanged.connect(self.updateButtonTextsAndLabels)  # Cambio aquí

        # Conectar cada CheckBox al nuevo método para actualizar el estado del botón de búsqueda
        self.cb_folders.stateChanged.connect(self.update_search_button_state)
        self.cb_images.stateChanged.connect(self.update_search_button_state)
        self.cb_videos.stateChanged.connect(self.update_search_button_state)
        self.cb_ficha_tecnica.stateChanged.connect(self.update_search_button_state)  # Asumiendo que cambias este por el de "Ficha Técnica"

        # Actualiza la adición de los CheckBoxes a la cuadrícula
        file_types_grid.addWidget(self.cb_folders, 1, 0)
        file_types_grid.addWidget(self.cb_images, 1, 1)
        file_types_grid.addWidget(self.cb_videos, 2, 0)
        file_types_grid.addWidget(self.cb_ficha_tecnica, 2, 1)

        # Contenedor para la sección de selección de tipos de archivo, usando un QGridLayout
        file_types_container = QWidget()
        file_types_container.setLayout(file_types_grid)
        
        # Añadir el contenedor de tipos de archivo al layout principal
        self.main_layout.addWidget(file_types_container)
        
        # Layout para la selección de ruta de búsqueda, dispuesta verticalmente
        self.path_selections_layout = QVBoxLayout()
        self.add_path_controls()  # Esto creará la primera fila de controles de ruta

        # Contenedor para la sección de selección de ruta
        path_selection_container = QWidget()
        path_selection_container.setLayout(self.path_selections_layout)

        # Añadiendo las secciones al layout horizontal principal
        both_sections_layout.addWidget(file_types_container)
        both_sections_layout.addWidget(path_selection_container)

        # Añadir el layout contenedor al layout principal
        self.main_layout.addLayout(both_sections_layout)

        
        # Botón para iniciar la búsqueda.
        self.generate_button = QPushButton("Buscar")
        self.generate_button.clicked.connect(self.generate_text)  # Conecta el clic del botón con la función de búsqueda.
        self.generate_button.setFixedHeight(50)  # Establece la altura fija del botón.
        self.main_layout.addWidget(self.generate_button)  # Agrega el botón al layout principal.

        # Configuración inicial de la etiqueta de información de referencia.
        self.ref_info_label = QLabel()  # Crea una nueva etiqueta para mostrar información.
        self.main_layout.addWidget(self.ref_info_label)  # Agrega la etiqueta al layout principal.
        self.ref_info_label.setAlignment(Qt.AlignCenter)  # Centra el texto en la etiqueta.
        font = self.ref_info_label.font()  # Obtiene la fuente actual de la etiqueta.
        font.setBold(True)  # Establece la fuente en negrita.
        self.ref_info_label.setFont(font)  # Aplica la fuente modificada a la etiqueta.

        # Configuración inicial de la barra de progreso
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setMaximum(100)  # Establecer el máximo en 100 para representar porcentajes
        
        # Añadir la barra de progreso al layout principal
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(self.progress_bar)
        # Suponiendo que main_layout es el QVBoxLayout principal de tu ventana
        self.main_layout.addLayout(progress_layout)

        # Lista de resultados de la búsqueda.
        self.results = QTreeWidget()  # Crea un árbol para mostrar los resultados.

        # Obtén el QHeaderView de tu QTreeWidget
        header = self.results.header()

        # Configura la alineación del texto de los encabezados
        header.setDefaultAlignment(Qt.AlignCenter)

        # Configura la fuente de los encabezados
        font = QFont("Sans Serif", 7)  # Cambia "Courier New" por la fuente monoespaciada de tu preferencia
        font.setBold(True)
        header.setFont(font)

        self.results.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Habilita la selección múltiple.
        self.results.setHeaderLabels(['', 'ID', 'REF', '###', 'TIPO', 'NOMBRE', 'RUTA'])
        self.main_layout.addWidget(self.results)  # Agrega el árbol de resultados al layout principal.
        self.results.itemDoubleClicked.connect(self.open_folder)  # Conecta el doble clic en un ítem con la función para abrir la carpeta.
        self.results.itemClicked.connect(self.handle_item_clicked)  # Conecta el clic en un ítem con la función para manejar clics.
        self.results.setColumnWidth(0, 40) # Ajusta el ancho de las columnas
        self.results.setColumnWidth(1, 15)
        self.results.setColumnWidth(2, 50)
        self.results.setColumnWidth(3, 50)
        self.results.setColumnWidth(4, 90)
        self.results.setColumnWidth(5, 250)
        self.results.setColumnWidth(6, 200)
        self.results.setStyleSheet("QTreeWidget::item { height: 22px; }") # Configuración de la altura de las filas mediante hoja de estilo
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.results.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        header = self.results.header() # Obtiene el encabezado del árbol de resultados.
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Ajusta el modo de redimensionamiento de las columnas.

        # Conectar la señal del clic derecho a un slot
        self.results.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self.openContextMenu)

        # Checkbox para seleccionar/deseleccionar todos los resultados.
        self.selectAllCheckBox = QCheckBox('Seleccionar todos')  # Crea el checkbox.
        self.selectAllCheckBox.setTristate(True)  # Permite tres estados: seleccionado, no seleccionado e indeterminado.
        self.selectAllCheckBox.stateChanged.connect(self.on_select_all_state_changed)  # Conecta el cambio de estado con una función.
        self.main_layout.addWidget(self.selectAllCheckBox)  # Agrega el checkbox al layout principal.


        # Etiqueta para mostrar el conteo de elementos seleccionados.
        self.selectedCountLabel = QLabel("Elementos seleccionados: 0")  # Crea la etiqueta con texto inicial.
        self.main_layout.addWidget(self.selectedCountLabel)  # Agrega la etiqueta al layout principal.

        # Etiqueta de estado para mostrar mensajes como "Listo".
        self.status_label = QLabel("Listo")  # Crea la etiqueta de estado.
        self.main_layout.addWidget(self.status_label)  # Agrega la etiqueta de estado al layout principal.

        # Sección de botones inferiores para operaciones adicionales.
        bottom_buttons_layout = QHBoxLayout()  # Layout horizontal para botones inferiores.
        self.main_layout.addLayout(bottom_buttons_layout)  # Agrega el layout de botones inferiores al layout principal.

        # Botón para abrir los elementos seleccionados.
        self.open_selected_button = QPushButton("Abrir Selección")
        self.open_selected_button.clicked.connect(self.open_selected)  # Conecta el botón con la función para abrir elementos seleccionados.
        self.open_selected_button.setFixedHeight(30)
        bottom_buttons_layout.addWidget(self.open_selected_button)  # Agrega el botón al layout de botones inferiores.

        # Botón para crear copias de los elementos seleccionados.
        self.copy_button = QPushButton("Crear Copia")
        self.copy_button.clicked.connect(self.copy_folders)  # Conecta el botón con la función para copiar elementos seleccionados.
        self.copy_button.setFixedHeight(30)
        bottom_buttons_layout.addWidget(self.copy_button)  # Agrega el botón al layout de botones inferiores.

        self.updateButtonTextsAndLabels()

    def handle_item_clicked(self, item, column):
        if column == 0:  # Columna de checkboxes
            selectedItems = self.results.selectedItems()
            checkState = item.checkState(0)
            if len(selectedItems) > 1:
                for selectedItem in selectedItems:
                    if selectedItem is not item:  # Aplica el cambio solo a otros ítems seleccionados, no al clickeado
                        selectedItem.setCheckState(0, checkState)
            self.update_selected_count()  # Actualizar el conteo después de cambiar el estado de los checkboxes

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

        # Si el estado es 'No seleccionado', desmarca todos los ítems de la lista.
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

    def update_selected_count(self):
        # Calcula el número de ítems seleccionados revisando el estado de los checkboxes.
        selected_count = sum(1 for i in range(self.results.topLevelItemCount())
                            if self.results.topLevelItem(i).checkState(0) == Qt.Checked)
        # Actualiza la etiqueta para mostrar el número actual de elementos seleccionados.
        self.selectedCountLabel.setText(f"Elementos seleccionados: {selected_count}")

        # Actualiza el estado del checkbox 'Seleccionar todos' basado en el número de ítems seleccionados.
        if selected_count == 0:
            self.selectAllCheckBox.blockSignals(True)
            self.selectAllCheckBox.setCheckState(Qt.Unchecked)
            self.selectAllCheckBox.blockSignals(False)
        elif selected_count == self.results.topLevelItemCount():
            self.selectAllCheckBox.blockSignals(True)
            self.selectAllCheckBox.setCheckState(Qt.Checked)
            self.selectAllCheckBox.blockSignals(False)
        else:
            self.selectAllCheckBox.blockSignals(True)
            self.selectAllCheckBox.setCheckState(Qt.PartiallyChecked)
            self.selectAllCheckBox.blockSignals(False)

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
        text_lines = [self.entry.item(i, 0).text().strip() for i in range(self.entry.rowCount()) if self.entry.item(i, 0) and self.entry.item(i, 0).text().strip()]

        if not self.is_searching:
            print("Iniciando la búsqueda...")
            if not self.paths:
                self.status_label.setText("Por favor, selecciona una ruta primero.")
                return
            if self.search_thread is not None and self.search_thread.isRunning():
                return

            selected_file_types = []
            if self.cb_folders.isChecked():
                selected_file_types.append("Carpetas")
            if self.cb_images.isChecked():
                selected_file_types.append("Imágenes")
            if self.cb_videos.isChecked():
                selected_file_types.append("Videos")
            if self.cb_ficha_tecnica.isChecked():
                selected_file_types.append("Ficha Técnica")

            self.results.clear()
            
            text_lines_indices = {line: i for i, line in enumerate(text_lines)}
            self.search_thread = SearchThread(text_lines, text_lines_indices, self.paths, selected_file_types)

            self.search_thread.directoryProcessed.connect(self.updateStatusLabel)
            # Conecta la señal de progreso para actualizar la barra de progreso
            self.search_thread.progress.connect(self.update_progress)
            # Conecta la señal finished para manejar la finalización de la búsqueda
            self.search_thread.finished.connect(self.on_search_finished)
            self.search_thread.start()
            
            # Prepara la barra de progreso para la búsqueda
            self.progress_bar.setValue(0)  # Inicializa el valor de la barra de progreso
            self.progress_bar.setMaximum(100)  # Establece el máximo en 100 para simular porcentaje
            self.generate_button.setText('Detener búsqueda')
            print("Iniciando el hilo de búsqueda.")
            self.is_searching = True
            print("Estado de is_searching al iniciar: ", self.is_searching)
            self.ref_info_label.setText("")
        else:
            print("Deteniendo la búsqueda...")
            if self.search_thread is not None and self.search_thread.isRunning():
                self.search_thread.requestInterruption()  # Solicita la interrupción del hilo de manera segura
                self.search_thread.wait()
                self.status_label.setText("Búsqueda detenida")
                self.generate_button.setText('Buscar')
                print("Búsqueda detenida.")
                self.is_searching = False
                print("Estado de is_searching al detener: ", self.is_searching)
                self.progress_bar.setValue(100)  # Restablece la barra de progreso a 100% para indicar finalización
                self.progress_bar.setMaximum(1)  # Restablece el máximo de la barra de progreso

        self.searched_refs = set(text_lines)
        self.copy_found_button.setEnabled(False)
        self.copy_not_found_button.setEnabled(False)

    def update_progress(self, percentage):
        # Asegura que el valor de porcentaje sea un entero antes de pasarlo
        int_percentage = int(percentage)
        self.progress_bar.setValue(int_percentage)

    def highlight_rows(self, result_folders):
        found_references = set()
        for folder_tuple in result_folders:
            folder, _, search_reference = folder_tuple
            folder_name = os.path.split(folder)[1]
            match = re.search(r'\d+', folder_name)
            if match:
                found_references.add(match.group(0))

        for row in range(self.entry.rowCount()):
            item = self.entry.item(row, 0)
            if item:
                text_line = item.text().strip()
                found = any(ref in text_line for ref in found_references)
                if not found:
                    item.setBackground(QColor(255, 200, 200))  # Resaltar en rojo claro las no encontradas
                else:
                    item.setBackground(QColor(255, 255, 255))  # Mantener el color blanco para las encontradas

    def on_search_finished(self, results_dict):
        self.status_label.setText("Listo")
        self.progress_bar.reset()
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)
        self.is_searching = False
        self.generate_button.setText('Buscar')
        self.copy_found_button.setEnabled(True)
        self.copy_not_found_button.setEnabled(True)

        # Preparar la lista de tuplas result_folders a partir de results_dict
        result_folders = [(folder, file_type, search_reference) for idx, results in results_dict.items() for folder, file_type, search_reference in results]
        
        self.highlight_rows(result_folders)

        found_refs = set()
        # Actualizar found_refs con las referencias encontradas
        for _, _, search_reference in result_folders:
            found_refs.add(search_reference)  # Asumiendo que search_reference es una cadena que representa la referencia encontrada

        self.found_refs = found_refs

        last_ref = None
        color = QColor("lightgray")
        
        for idx, results in sorted(results_dict.items()):
            for folder, file_type, search_reference in results:
                folder_name = os.path.split(folder)[1]

                # Utiliza search_reference para extraer component1 y component2 correctamente
                match = re.match(r"([A-Z]+)\s*(\d+)", search_reference)
                if match:
                    component1 = match.group(1)
                    component2 = match.group(2)
                else:
                    component1 = ''
                    component2 = ''

                item = QTreeWidgetItem(['', str(idx + 1), component1, component2, file_type, folder_name, folder])

                # Alineación centrada para las columnas específicas
                item.setTextAlignment(0, Qt.AlignCenter)  
                item.setTextAlignment(1, Qt.AlignCenter)  # ID
                item.setTextAlignment(2, Qt.AlignCenter)  # REF
                item.setTextAlignment(3, Qt.AlignCenter)  # ###
                item.setTextAlignment(4, Qt.AlignCenter)  # Tipo de Archivo

                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setData(3, Qt.UserRole, folder)
                
                if last_ref != component2:
                    color = QColor("white") if color == QColor("lightgray") else QColor("lightgray")
                for i in range(item.columnCount()):
                    item.setBackground(i, QBrush(color))
                last_ref = component2
                
                self.results.addTopLevelItem(item)

        found_count = len(found_refs)
        searched_count = len(self.searched_refs)  # Asegúrate de que self.searched_refs se haya inicializado correctamente
        self.ref_info_label.setText(f"{found_count} de {searched_count} Referencias encontradas")
        self.results.resizeColumnToContents(6)

    def get_number_from_folder_name(self, folder):
        # Extrae un número del nombre de una carpeta, útil para ordenar carpetas numéricamente.
        folder_name = os.path.split(folder)[1]  # Separa el nombre de la carpeta de la ruta completa.
        match = re.search(r'\d+', folder_name)  # Busca una secuencia numérica en el nombre de la carpeta.
        if match:
            return int(match.group(0))  # Si encuentra un número, lo retorna como entero.
        else:
            return 0  # Si no encuentra un número, retorna 0 como valor predeterminado.

    def open_folder(self):
        # Abre la carpeta seleccionada en el explorador de archivos de Windows.
        item = self.results.currentItem()  # Obtiene el elemento actualmente seleccionado en los resultados.
        if item:
            # Construye y ejecuta el comando para abrir la carpeta en el explorador de archivos.
            os.system('start "" "{path}"'.format(path=os.path.normpath(item.data(3, Qt.UserRole))))

    def delete_selected(self):
        prev_state = self.get_table_state()  # Obtiene el estado actual de la tabla
        selected_rows = set(index.row() for index in self.entry.selectionModel().selectedIndexes())

        for row in sorted(selected_rows, reverse=True):
            self.entry.removeRow(row)

        self.action_history.append(prev_state)  # Agrega el estado anterior de la tabla al historial
        self.action_history.append(self.get_table_state())  # Agrega el estado actual de la tabla al historial

    def clear_all(self):
        # Limpia el contenido de la tabla de entrada.
        self.entry.clearContents()
        self.entry.setRowCount(0)

        # Limpia la lista de resultados.
        self.results.clear()

        # Desmarca todos los checkboxes.
        self.cb_folders.setChecked(False)
        self.cb_images.setChecked(False)
        self.cb_videos.setChecked(False)
        self.cb_ficha_tecnica.setChecked(False)

        # Limpia las rutas seleccionadas y deja solo una ruta de búsqueda.
        while self.path_selections_layout.count() > 1:
            # Elimina el último layout de selección de ruta añadido.
            layout_to_remove = self.path_selections_layout.itemAt(self.path_selections_layout.count() - 1).layout()
            self.remove_path_controls(layout_to_remove)
        # Asegúrate de que el campo de la única ruta de búsqueda restante esté vacío.
        if self.path_selections_layout.count() == 1:
            path_layout = self.path_selections_layout.itemAt(0).layout()
            path_button = path_layout.itemAt(0).widget()
            path_button.setText("Seleccionar ruta de búsqueda")
            self.paths.clear()

        # Reinicia el estado de la aplicación.
        self.status_label.setText("Listo")
        self.progress_bar.reset()
        self.selectAllCheckBox.setCheckState(Qt.Unchecked)
        self.ref_info_label.setText("")
        self.copy_found_button.setEnabled(False)
        self.copy_not_found_button.setEnabled(False)
        self.found_refs.clear()
        self.updateButtonTextsAndLabels()  # Actualiza el texto del botón de búsqueda.

        print("Todo ha sido reiniciado.")

    def open_all(self):
        # Abre todas las carpetas listadas en los resultados.
        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            # Utiliza el comando del sistema para abrir la carpeta en el explorador de archivos.
            os.system('start "" "{path}"'.format(path=item.data(3, Qt.UserRole)))

    def open_selected(self):
        # Abre solo las carpetas o archivos que han sido seleccionados.
        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                # Abre la ubicación especificada si el ítem está seleccionado.
                os.system('start "" "{path}"'.format(path=item.data(3, Qt.UserRole)))

    def copy_folders(self):
        destination_path = QFileDialog.getExistingDirectory(self, 'Seleccionar ruta de destino')
        if not destination_path:
            return

        success_copies = []
        failed_copies = []

        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                source_path = item.data(3, Qt.UserRole)
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
        # Copia al portapapeles todas las referencias que no están resaltadas en rojo claro (es decir, las encontradas).
        text_lines = []  # Lista para almacenar las líneas a copiar.
        for i in range(self.entry.rowCount()):
            item = self.entry.item(i, 0)
            # Verifica si la celda no está resaltada en rojo claro, indicando que la referencia fue encontrada.
            if item.background() != QBrush(QColor(255, 200, 200)):
                text_lines.append(item.text())  # Añade el texto de la referencia a la lista.
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(text_lines))  # Copia todas las referencias encontradas al portapapeles.

    def copy_not_found(self):
        # Copia al portapapeles todas las referencias resaltadas en rojo claro (es decir, las no encontradas).
        text_lines = []  # Lista para almacenar las líneas a copiar.
        for i in range(self.entry.rowCount()):
            item = self.entry.item(i, 0)
            # Verifica si la celda está resaltada en rojo claro, indicando que la referencia no fue encontrada.
            if item.background() == QBrush(QColor(255, 200, 200)):
                text_lines.append(item.text())  # Añade el texto de la referencia a la lista.
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(text_lines))  # Copia todas las referencias no encontradas al portapapeles.

    def updateButtonTextsAndLabels(self):
        selected_file_types = []
        if self.cb_folders.isChecked():
            selected_file_types.append("Carpetas")
        if self.cb_images.isChecked():
            selected_file_types.append("Imágenes")
        if self.cb_videos.isChecked():
            selected_file_types.append("Videos")
        if self.cb_ficha_tecnica.isChecked():
            selected_file_types.append("Ficha Técnica")
        if selected_file_types:
            search_text = "Buscar " + " + ".join(selected_file_types)
        else:
            search_text = "Selecciona tipo(s) de archivo a buscar"
        self.generate_button.setText(search_text)



    def select_path(self, button):
        prev_path = button.text()  # Guarda la ruta anterior, si existe
        new_path = QFileDialog.getExistingDirectory(self, 'Select directory')
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
        # Método para crear un nuevo QHBoxLayout para la selección de ruta
        path_layout = QHBoxLayout()

        path_button = QPushButton("Seleccionar ruta de búsqueda")
        path_button.clicked.connect(lambda: self.select_path(path_button))

        btn_add_path = QPushButton("+")
        btn_add_path.setMaximumWidth(30)
        btn_add_path.setEnabled(False)  # El botón "+" se activará después de seleccionar una ruta
        btn_add_path.clicked.connect(self.add_path_controls)

        btn_remove_path = QPushButton("-")
        btn_remove_path.setMaximumWidth(30)
        btn_remove_path.clicked.connect(lambda: self.remove_path_controls(path_layout))
        btn_remove_path.setEnabled(self.path_selections_layout.count() > 0)  # Se activa si hay más de una fila

        path_layout.addWidget(path_button)
        path_layout.addWidget(btn_add_path)
        path_layout.addWidget(btn_remove_path)

        # Guardamos una referencia al botón "+" para usarla más tarde
        path_button.plus_button = btn_add_path

        return path_layout

    def add_path_controls(self):
        new_path_layout = self.create_path_layout()
        self.path_selections_layout.addLayout(new_path_layout)
        # Asegúrate de que el botón "+" se activa solo en la última fila
        for i in range(self.path_selections_layout.count() - 1):
            path_layout = self.path_selections_layout.itemAt(i)
            plus_button = path_layout.itemAt(1).widget()
            plus_button.setEnabled(False)
        # Activa el botón "+" en la última fila añadida
        self.path_selections_layout.itemAt(self.path_selections_layout.count() - 1).itemAt(1).widget().setEnabled(True)

    def remove_path_controls(self, layout_to_remove):
        if self.path_selections_layout.count() > 1:
            # Encuentra el índice de layout_to_remove dentro del path_selections_layout
            index_to_remove = self.path_selections_layout.indexOf(layout_to_remove)
            path_button = layout_to_remove.itemAt(0).widget()  # Asume que el botón de la ruta es el primer widget en el layout
            path_to_remove = path_button.text()
            
            # Intenta eliminar la ruta correspondiente de self.paths
            if path_to_remove in self.paths:
                self.paths.remove(path_to_remove)
                print(f"Ruta eliminada: {path_to_remove}")
                print(f"Rutas restantes: {self.paths}")

            # Elimina los widgets y el propio layout_to_remove
            for i in reversed(range(layout_to_remove.count())):
                widget_to_remove = layout_to_remove.itemAt(i).widget()
                if widget_to_remove is not None:
                    widget_to_remove.deleteLater()
            self.path_selections_layout.removeItem(layout_to_remove)

            # Activa el botón "+" de la última fila
            if index_to_remove == self.path_selections_layout.count():
                last_path_layout = self.path_selections_layout.itemAt(self.path_selections_layout.count() - 1)
                last_plus_button = last_path_layout.itemAt(1).widget()
                last_plus_button.setEnabled(True)
        else:
            print("No se puede eliminar la única ruta de búsqueda.")

    def update_search_button_state(self):
        # Esta función se mantiene igual que en el ejemplo anterior
        any_checked = self.cb_folders.isChecked() or self.cb_images.isChecked() or \
                      self.cb_videos.isChecked() or self.cb_ficha_tecnica.isChecked()
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

    def copyItemPath(self):
        selectedItems = self.results.selectedItems()
        if selectedItems:
            clipboard = QApplication.clipboard()
            item = selectedItems[0]  # Copiar ruta del primer ítem seleccionado
            itemPath = item.text(6)  # Asegúrate de que este es el índice correcto para la columna de la ruta
            directoryPath = os.path.dirname(itemPath)  # Extrae el directorio contenedor del archivo o carpeta
            clipboard.setText(directoryPath)

    def copyItemInfo(self):
        selectedItems = self.results.selectedItems()
        if selectedItems:
            clipboard = QApplication.clipboard()
            infoText = ""
            for item in selectedItems:  # Modificado para manejar múltiples selecciones
                ref = item.text(2)  # REF
                num = item.text(3)  # ###
                fileType = item.text(4)  # Tipo de Archivo
                itemName = item.text(5)  # Nombre del Archivo o Carpeta
                itemPath = item.text(6)  # Ruta
                # Construye el texto con el formato especificado
                infoText += f"{ref} {num} - [{fileType}] - ({itemName}): \n{itemPath}\n\n"
            clipboard.setText(infoText.strip())  # Copia el texto al portapapeles

    def updateStatusLabel(self, processed, total, path):
        # Obtiene el objeto QFontMetrics del QLabel para calcular cómo ajustar el texto.
        metrics = self.status_label.fontMetrics()

        # Establece el ancho máximo permitido para el texto (podría ser el ancho de la ventana o un valor fijo).
        max_width = self.status_label.width() - 20  # Asumimos 20 píxeles menos para un poco de margen.

        # Usa el método elide para truncar el texto con puntos suspensivos si es demasiado largo.
        elided_path = metrics.elidedText(path, Qt.TextElideMode.ElideMiddle, max_width)

        # Establece el texto ajustado en el QLabel.
        self.status_label.setText(f"Directorios procesados: {processed}/{total}, Revisando: {elided_path}")
   

    def openImageSearchWindow(self):
        self.imageSearchWindow = MainWindow()
        self.imageSearchWindow.show()

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