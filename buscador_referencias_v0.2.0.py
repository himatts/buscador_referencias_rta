import os
import sys
import re
import shutil
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QMainWindow, QHeaderView, QTextEdit, QTreeWidget, QTreeWidgetItem, QLabel, QFileDialog, QCheckBox, QProgressBar
from PyQt5.QtWidgets import QSizePolicy, QMessageBox, QAbstractItemView, QComboBox, QScrollBar
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QKeySequence, QColor, QTextDocument, QTextCursor, QTextCharFormat


class SearchThread(QThread):
    finished = pyqtSignal(list)
    progress = pyqtSignal()

    def __init__(self, text_lines, path, file_type):
        super().__init__()
        self.text_lines = text_lines
        self.file_type = file_type
        self.path = path

    def run(self):
        numbers = [re.findall(r'\d+', line)[0] for line in self.text_lines if re.findall(r'\d+', line)]
        results = []

        if self.file_type == "Carpetas":
            for root, dirs, files in os.walk(self.path):
                for dir in dirs:
                    if any(number in dir for number in numbers):
                        results.append(os.path.normpath(os.path.join(root, dir)))
                self.progress.emit()

        elif self.file_type == "Imágenes":
            for root, dirs, files in os.walk(self.path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
                        if any(number in file for number in numbers):
                            results.append(os.path.normpath(os.path.join(root, file)))
                self.progress.emit()

        elif self.file_type == "Videos":
            for root, dirs, files in os.walk(self.path):
                for file in files:
                    if file.lower().endswith(('.mp4', '.mov', '.wmv', '.flv', '.avi', '.avchd', '.webm', '.mkv')):
                        if any(number in file for number in numbers):
                            results.append(os.path.normpath(os.path.join(root, file)))
                self.progress.emit()

        elif self.file_type == "Nombre de Mueble":
            for root, dirs, files in os.walk(self.path):
                for dir in dirs:
                    if all(line.lower() in dir.lower() for line in self.text_lines):  # Verifica si cada línea está contenida en el nombre
                        results.append(os.path.normpath(os.path.join(root, dir)))
                for file in files:
                    if all(line.lower() in file.lower() for line in self.text_lines):  # Verifica si cada línea está contenida en el nombre
                        results.append(os.path.normpath(os.path.join(root, file)))
            self.progress.emit()

        self.finished.emit(results)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = None
        self.is_searching = False  
        self.initUI()
        self.search_thread = None



class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = None
        self.is_searching = False  
        self.initUI()
        self.search_thread = None

    def initUI(self):
        self.setWindowTitle('Buscador de Carpetas')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.layout = QVBoxLayout(central_widget)
        self.resize(800, 600)  # Set initial window size to 800x600

        # Create top buttons
        upper_buttons_layout = QHBoxLayout()
        self.layout.addLayout(upper_buttons_layout)

        self.paste_button = QPushButton("Pegar información")
        self.paste_button.clicked.connect(self.paste_information)
        upper_buttons_layout.addWidget(self.paste_button)

        self.delete_button = QPushButton("Borrar selección")
        self.delete_button.clicked.connect(self.delete_selected)
        upper_buttons_layout.addWidget(self.delete_button)

        self.clear_button = QPushButton("Borrar todo")
        self.clear_button.clicked.connect(self.clear_all)
        upper_buttons_layout.addWidget(self.clear_button)

        # Create input table
        self.entry = QTableWidget(0, 1)
        self.entry.setHorizontalHeaderLabels(['Contenido'])
        self.entry.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.layout.addWidget(self.entry)
        self.entry.installEventFilter(self)

        # Create a QHBoxLayout for the label
        label_layout = QHBoxLayout()
        self.file_type_label = QLabel("Selecciona el tipo de archivo a buscar:")
        label_layout.addWidget(self.file_type_label)
        # Add the QHBoxLayout to the main QVBoxLayout
        self.layout.addLayout(label_layout)

        # Create a QHBoxLayout
        path_layout = QHBoxLayout()

        self.file_type_combo = QComboBox()
        self.file_type_combo.addItem("Carpetas")
        self.file_type_combo.addItem("Imágenes")
        self.file_type_combo.addItem("Videos")
        self.file_type_combo.addItem("Nombre de Mueble")  # Agregar nueva opción
        self.file_type_combo.currentIndexChanged.connect(self.updateButtonTextsAndLabels)
        path_layout.addWidget(self.file_type_combo)

        # Button to select path
        self.path_button = QPushButton("Seleccionar ruta de búsqueda")
        self.path_button.clicked.connect(self.select_path)
        path_layout.addWidget(self.path_button)

        # Add the QHBoxLayout to the main QVBoxLayout
        self.layout.addLayout(path_layout)

        # Create generate button
        self.generate_button = QPushButton("Buscar")
        self.generate_button.clicked.connect(self.generate_text)
        self.generate_button.setFixedHeight(50)  # Set the button's height to 50 pixels
        self.layout.addWidget(self.generate_button)

        # Add a progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setAlignment(Qt.AlignCenter) 
        self.progress_bar.setFormat('%p%')

        # Put the progress bar in a separate layout
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(self.progress_bar)

        # Add the progress_layout to your main layout
        self.layout.addLayout(progress_layout)

        # Create results list
        self.results = QTreeWidget()
        self.results.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Enable multiple selection
        self.results.setHeaderLabels(['', 'REF', '###', 'Nombre', 'Ruta'])
        self.layout.addWidget(self.results)
        self.results.itemDoubleClicked.connect(self.open_folder)
        self.results.itemClicked.connect(self.handle_item_clicked)  # Moved this line here
        self.results.setColumnWidth(0, 50)
        self.results.setColumnWidth(1, 60)
        self.results.setColumnWidth(2, 60)
        self.results.setColumnWidth(3, 800)
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.results.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        header = self.results.header()
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Cambia '3' al índice de la columna que desees que se ajuste.
        for i in range(self.results.columnCount()):
            self.results.resizeColumnToContents(i)


        
        # This line is moved here, after 'self.results' is created
        self.results.itemClicked.connect(self.handle_item_clicked)

        # Status label
        self.status_label = QLabel("Listo")
        self.layout.addWidget(self.status_label)

        # Create bottom buttons
        bottom_buttons_layout = QHBoxLayout()
        self.layout.addLayout(bottom_buttons_layout)

        self.open_all_button = QPushButton("Abrir todo")
        self.open_all_button.clicked.connect(self.open_all)
        bottom_buttons_layout.addWidget(self.open_all_button)

        self.open_selected_button = QPushButton("Abrir selección")
        self.open_selected_button.clicked.connect(self.open_selected)
        bottom_buttons_layout.addWidget(self.open_selected_button)

        self.copy_button = QPushButton("Crear copia")
        self.copy_button.clicked.connect(self.copy_folders)
        bottom_buttons_layout.addWidget(self.copy_button)  

        self.updateButtonTextsAndLabels()


    def handle_item_clicked(self, item, column):
        if column == 0:  # Columna de checkboxes
            state = item.checkState(0)
            selected_items = self.results.selectedItems()
            for selected_item in selected_items:
                selected_item.setCheckState(0, state)


    def eventFilter(self, obj, event):
        if obj == self.entry:
            if event.type() == QEvent.KeyPress:
                if event.matches(QKeySequence.Paste):
                    self.paste_information()
                    return True
                elif event.matches(QKeySequence.Delete):
                    self.delete_selected()
                    return True
        return super().eventFilter(obj, event)

    def generate_text(self):
        if not self.is_searching:
            if self.path is None:
                self.status_label.setText("Por favor, selecciona una ruta primero.")
                return
            if self.search_thread is not None and self.search_thread.isRunning():
                return
            text_lines = [self.entry.item(i, 0).text() for i in range(self.entry.rowCount())]
            self.results.clear()
            self.status_label.setText("Buscando...")
            file_type = self.file_type_combo.currentText()
            self.search_thread = SearchThread(text_lines, self.path, file_type)
            self.search_thread.progress.connect(self.update_progress)
            self.search_thread.start()
            self.search_thread.finished.connect(self.on_search_finished)
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(0)
            self.generate_button.setText('Parar búsqueda')
            self.is_searching = True
        else:
            if self.search_thread is not None and self.search_thread.isRunning():
                self.search_thread.terminate()
                self.search_thread.wait()
                self.status_label.setText("Búsqueda detenida")
                self.generate_button.setText('Buscar')
                self.is_searching = False
                self.progress_bar.setMaximum(1)  # Set maximum to 1 before resetting
                self.progress_bar.reset()


    def update_progress(self):
        # This will just pulse the progress bar to indicate that something is happening
        self.progress_bar.setValue((self.progress_bar.value() + 1) % (self.progress_bar.maximum() + 1))

    def on_search_finished(self, result_folders):
        self.status_label.setText("Listo")
        self.progress_bar.reset()
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(1)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #30BA49; }")
        self.generate_button.setText('Buscar')
        self.is_searching = False
        for folder in result_folders:
            # Parse folder name for additional columns
            folder_name = os.path.split(folder)[1]
            component1 = folder_name[0:3]
            component2 = re.search(r'\d+', folder_name)
            if component2:
                component2 = component2.group(0)
            else:
                component2 = ''

            item = QTreeWidgetItem(['', component1, component2, folder_name, folder])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            item.setData(3, Qt.UserRole, folder)

            self.results.addTopLevelItem(item)

    def open_folder(self):
        item = self.results.currentItem()
        if item:
            os.system('start "" "{path}"'.format(path=os.path.normpath(item.data(3, Qt.UserRole))))
                
    def delete_selected(self):
        selected_rows = set(index.row() for index in self.entry.selectionModel().selectedIndexes())
        for row in sorted(selected_rows, reverse=True):
            self.entry.removeRow(row)

    def clear_all(self):
        self.entry.setRowCount(0)
        self.results.clear()

    def paste_information(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        lines = text.split('\n')
        for line in lines:
            self.entry.insertRow(self.entry.rowCount())
            self.entry.setItem(self.entry.rowCount()-1, 0, QTableWidgetItem(line))

    def select_path(self):
        self.path = QFileDialog.getExistingDirectory(self, 'Select directory')
        if self.path:
            self.status_label.setText("Ruta seleccionada: " + self.path)

    def open_all(self):
        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            os.system('start "" "{path}"'.format(path=item.data(3, Qt.UserRole)))  # updated

    def open_selected(self):
        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:  # updated
                os.system('start "" "{path}"'.format(path=item.data(3, Qt.UserRole)))  # updated

    def copy_folders(self):
        destination_path = QFileDialog.getExistingDirectory(self, 'Seleccionar ruta de destino')
        if not destination_path:
            return
        success_copies = []  # list to hold successful copies
        failed_copies = []  # list to hold failed copies
        for index in range(self.results.topLevelItemCount()):
            item = self.results.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                source_path = item.data(3, Qt.UserRole)
                try:
                    file_type = self.file_type_combo.currentText()
                    if file_type == "Carpetas":
                        shutil.copytree(source_path, os.path.join(destination_path, os.path.basename(source_path)))
                    else:
                        shutil.copy2(source_path, os.path.join(destination_path, os.path.basename(source_path)))
                    success_copies.append(os.path.basename(source_path))  # add successful copy to list
                except FileExistsError:
                    failed_copies.append(os.path.basename(source_path))  # add failed copy to list
                except Exception as e:
                    failed_copies.append(os.path.basename(source_path))  # add failed copy to list

        # Generate summary message
        summary_msg = ""
        if success_copies:
            summary_msg += f'Todos los {file_type.lower()} siguientes fueron copiados correctamente:\n{", ".join(success_copies)}\n'
        if failed_copies:
            summary_msg += f'Estos {file_type.lower()} no lograron ser copiados:\n{", ".join(failed_copies)}'
        if not success_copies and not failed_copies:
            summary_msg = "No se seleccionaron archivos o carpetas para copiar."

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(summary_msg)
        msg.setWindowTitle("Resumen de copia")
        open_button = msg.addButton('Abrir ruta', QMessageBox.ActionRole)
        close_button = msg.addButton('Cerrar', QMessageBox.RejectRole)
        
        msg.exec_()

        # check which button was clicked
        if msg.clickedButton() == open_button:
            os.system('start "" "{path}"'.format(path=destination_path))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.generate_text()

    def updateButtonTextsAndLabels(self):
        # Actualiza el texto del botón de búsqueda y crear copia, y la columna de resultados
        file_type = self.file_type_combo.currentText()
        self.generate_button.setText(f"Buscar {file_type}")
        self.copy_button.setText(f"Crear copia de {file_type}")
        self.results.setHeaderLabels(['', 'REF', '###', f'Nombre de {file_type}', 'Ruta'])
        if self.file_type_combo.currentText() == "Nombre de Mueble":
            self.results.setHeaderLabels(['', 'REF', '###', 'Nombre de Mueble', 'Ruta'])
        else:
            self.results.setHeaderLabels(['', 'REF', '###', f'Nombre de {file_type}', 'Ruta'])
            
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())