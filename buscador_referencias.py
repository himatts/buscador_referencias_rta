import os
import sys
import re
import shutil
import random
import time
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
        results_with_info = []  # Añade esta línea
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

        for result in results:
            stat_info = os.stat(result)
            size_in_mb = stat_info.st_size / (1024 * 1024)
            mtime = time.ctime(stat_info.st_mtime)
            result_tuple = (result, size_in_mb, mtime)
            results_with_info.append(result_tuple)

        self.finished.emit(results_with_info)
        
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = None
        self.is_searching = False  
        self.changing_all_checkboxes = False  # Nueva variable
        self.colors = {}  # Nuevo diccionario para almacenar los colores
        self.initUI()
        self.search_thread = None

    def get_color_for_result(self, component2):
        if component2 in self.colors:
            return self.colors[component2]
        else:
            random_color = QColor(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255))  # Valores más altos para un color más claro
            self.colors[component2] = random_color
            return random_color

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
        self.results.setColumnWidth(0, 20)
        self.results.setColumnWidth(1, 60)
        self.results.setColumnWidth(2, 60)
        self.results.setColumnWidth(3, 800)
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.results.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        header = self.results.header()
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Cambia '3' al índice de la columna que desees que se ajuste.
        for i in range(self.results.columnCount()):
            self.results.resizeColumnToContents(i)
        self.selectAllCheckBox = QCheckBox('Seleccionar todos')
        self.selectAllCheckBox.setTristate(True)
        self.selectAllCheckBox.stateChanged.connect(self.on_select_all_state_changed)
        self.selectedCountLabel = QLabel()  # Crea la etiqueta
        self.selectedCountLabel.setText("Elementos seleccionados: 0")  # Inicializa el texto
        self.selectAllCheckBox.setCheckState(Qt.PartiallyChecked)
        self.layout.addWidget(self.selectedCountLabel)  # reemplaza 'self.layout' con tu layout actual


        # Asume que self.layout es el layout de tu ventana. Si no es así, reemplaza 'self.layout' por tu layout actual.
        self.layout.addWidget(self.selectAllCheckBox)

       
        # This line is moved here, after 'self.results' is created
        self.results.itemClicked.connect(self.handle_item_clicked)
        self.results.itemChanged.connect(self.update_selected_count)

        self.previousSelectAllState = self.selectAllCheckBox.checkState()  # Nueva línea
 
                
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
            # Desmarcar 'selectAllCheckBox' si un item fue desmarcado
            if item.checkState(0) == Qt.Unchecked:
                self.selectAllCheckBox.blockSignals(True)
                self.selectAllCheckBox.setCheckState(Qt.Unchecked)
                self.selectAllCheckBox.blockSignals(False)

            # Actualizar la etiqueta de cantidad de elementos seleccionados
            self.update_selected_count()

    def on_select_all_state_changed(self, state):
        self.changing_all_checkboxes = True  # Estamos cambiando todos los checkboxes

        if state == Qt.Unchecked:
            for i in range(self.results.topLevelItemCount()):
                self.results.topLevelItem(i).setCheckState(0, Qt.Unchecked)
        elif state == Qt.Checked or state == Qt.PartiallyChecked:
            for i in range(self.results.topLevelItemCount()):
                self.results.topLevelItem(i).setCheckState(0, Qt.Checked)

        self.changing_all_checkboxes = False  # Hemos terminado de cambiar todos los checkboxes
        self.update_selected_count()  # Actualizar el contador después de cambiar los checkboxes

    def update_selected_count(self):
        selected_count = sum(1 for i in range(self.results.topLevelItemCount())
                             if self.results.topLevelItem(i).checkState(0) == Qt.Checked)
        self.selectedCountLabel.setText(f"Elementos seleccionados: {selected_count}")

        # Now also update the state of the 'select all' checkbox.
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
            self.status_label.setText(f"Buscando en {self.path}...")
            file_type = self.file_type_combo.currentText()
            self.search_thread = SearchThread(text_lines, self.path, file_type)
            self.search_thread.progress.connect(self.update_progress)
            self.search_thread.start()
            self.search_thread.finished.connect(self.on_search_finished)
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(0)
            self.generate_button.setText('Parar búsqueda')
            self.is_searching = True
            self.original_order = [self.entry.item(i, 0).text() for i in range(self.entry.rowCount())]
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

    def on_search_finished(self, results):
        grouped_results = {}
        for result in results:
            # Obtén el criterio de búsqueda original para este resultado
            search_criterion = result[0]  # Asume que el criterio de búsqueda es el primer elemento de `result`
            # Añade el resultado a la lista de resultados para este criterio de búsqueda
            if search_criterion in grouped_results:
                grouped_results[search_criterion].append(result)
            else:
                grouped_results[search_criterion] = [result]
        # Ahora `grouped_results` es un diccionario donde las claves son los criterios de búsqueda
        # y los valores son listas de resultados para cada criterio
        # Guarda `grouped_results` para que podamos usarlo más tarde
        self.grouped_results = grouped_results
        self.display_results()

        # Diccionario para guardar la última referencia procesada y su color
        last_reference = {"ref": None, "color": None}

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

            # Si la referencia es la misma que la anterior, usar el mismo color
            if last_reference["ref"] == component2:
                color = last_reference["color"]
            else:
                # Si la referencia ha cambiado, alternar el color
                color = QColor("white") if last_reference["color"] == QColor("lightgray") else QColor("lightgray")

            for i in range(item.columnCount()):
                item.setBackground(i, color)

            # Guardar la referencia y el color actuales para la próxima iteración
            last_reference = {"ref": component2, "color": color}

            self.results.addTopLevelItem(item)

    def display_results(self):
        self.results.clear()
        # Ordena las claves de `grouped_results` según su orden en `original_order`
        ordered_search_criteria = sorted(self.grouped_results.keys(), key=lambda criterion: self.original_order.index(criterion))
        # Recorre los criterios de búsqueda en el orden correcto
        for criterion in ordered_search_criteria:
            # Recorre los resultados para este criterio de búsqueda
            for result in self.grouped_results[criterion]:
                # Aquí `result` es un resultado individual
                # Tendrás que ajustar el siguiente código para que se ajuste a cómo se estructuran tus resultados
                path, size_in_mb, mtime = result
                item = QTreeWidgetItem()
                item.setText(0, path)
                item.setToolTip(0, f"Size: {size_in_mb} MB\nLast modified: {mtime}")
                self.results.addTopLevelItem(item)
        # Cuando termines, actualiza la etiqueta de estado para mostrar cuántos resultados se encontraron
        self.status_label.setText(f"Se encontraron {len(self.results)} resultado(s).")


    def get_number_from_folder_name(self, folder):
        folder_name = os.path.split(folder)[1]
        match = re.search(r'\d+', folder_name)
        if match:
            return int(match.group(0))  # Retornar el número como un entero para que la ordenación sea numérica, no lexicográfica
        else:
            return 0  # Si no hay número, retornar 0 (o cualquier otro valor que tenga sentido en tu contexto)


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