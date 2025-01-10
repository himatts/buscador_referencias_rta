"""
Nombre del Archivo: secondWindow.py
Descripción: Este programa es una aplicación de escritorio construida con PyQt5 para buscar y visualizar imágenes.
             Permite al usuario cargar una imagen de referencia, ajustar parámetros de búsqueda como el tipo de imagen
             y el umbral de reconocimiento, y visualizar imágenes similares encontradas en una base de datos.
             Utiliza una interfaz gráfica para facilitar la interacción con el usuario.
Autor: RTA Muebles - Área Soluciones IA
Fecha: 2 de Marzo de 2024
"""
# Importaciones necesarias para el programa
import io  # Módulo para trabajar con archivos de entrada y salida
import os  # Módulo para interactuar con el sistema operativo
from PyQt5 import QtCore, QtGui, QtWidgets  # Importaciones relacionadas con PyQt5
from core.imageSearchAlgorithm import ImageSearchEngine  # Importación de la clase ImageSearchEngine del módulo image_search_engine
from PyQt5.QtCore import QThread, pyqtSignal, QRectF, QSize  # Importaciones específicas de PyQt5
from PIL import Image  # Importación de la clase Image del módulo PIL (Python Imaging Library)
from PyQt5.QtGui import QImage, QPixmap, QIcon  # Importaciones específicas de PyQt5
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QLabel  # Importaciones específicas de PyQt5

class ImageViewer(QGraphicsView):
    """
    Clase para visualizar imágenes en la aplicación. Hereda de QGraphicsView para proporcionar
    una vista interactiva de las imágenes. Permite cargar y mostrar imágenes desde una ruta de archivo.
    """
    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.scene = QGraphicsScene(self)  # Creación de una escena gráfica para la visualización de imágenes
        self.setScene(self.scene)

    def displayImage(self, imagePath):
        """
        Carga y muestra una imagen desde la ruta de archivo especificada.

        Args:
            imagePath: Ruta al archivo de imagen que se desea mostrar.
        """
        pixmap = QPixmap(imagePath)  # Creación de un QPixmap a partir de la ruta de la imagen
        self.scene.clear()  # Limpieza de la escena gráfica
        self.scene.addPixmap(pixmap)  # Agregando el QPixmap a la escena
        # Convertir QRect a QRectF explícitamente
        rectF = QRectF(pixmap.rect())  # Creación de un QRectF a partir del rectángulo del QPixmap
        self.scene.setSceneRect(rectF)  # Establecimiento del rectángulo de la escena
        self.fitInView(rectF, QtCore.Qt.KeepAspectRatio)  # Ajuste de la vista de la imagen en la escena


class ImageSearchThread(QThread):
    """
    Clase para buscar imágenes similares en un hilo separado. Hereda de QThread para manejar la búsqueda de imágenes
    sin bloquear la interfaz de usuario, emitiendo una señal cuando la búsqueda está completa con los resultados.
    """

    search_started = pyqtSignal()  # Señal para indicar que la búsqueda ha comenzado
    search_finished = pyqtSignal(list)  # Señal para los resultados

    def __init__(self, image_path, threshold, parent=None):
        super(ImageSearchThread, self).__init__(parent)
        self.image_path = image_path  # Ruta de la imagen de referencia para la búsqueda
        self.threshold = threshold  # Umbral de reconocimiento para la búsqueda
        # Inicialización de la instancia de ImageSearchEngine con la ruta de la base de datos
        self.imageSearchEngine = ImageSearchEngine('//192.168.200.250/rtadiseño/SOLUCIONES IA/BASES DE DATOS/buscador_de_referencias/hashes_imagenes_muebles.db')

    def load_and_process_image(self, image_path):
        # Cargar la imagen utilizando PIL
        image = Image.open(image_path)  # Apertura de la imagen utilizando PIL
        
        # Aquí puedes agregar cualquier procesamiento adicional que necesites,
        # como cambiar el tamaño de la imagen, convertirla a escala de grises, etc.
        # Por ejemplo, para cambiar el tamaño:
        # image = image.resize((nuevo_ancho, nuevo_alto))
        
        return image  # Devolución de la imagen procesada

    def run(self):
        self.search_started.emit()  # Emitir al inicio de la búsqueda
        if os.path.exists(self.image_path):  # Verificación de si la ruta de la imagen existe
            imagen_referencia = self.load_and_process_image(self.image_path)  # Carga y procesamiento de la imagen de referencia
            # Búsqueda de imágenes similares utilizando el motor de búsqueda de imágenes
            resultados = self.imageSearchEngine.buscar_imagenes_similares(imagen_referencia, self.threshold)
            self.search_finished.emit(resultados)  # Emisión de la señal con los resultados de la búsqueda


class MainWindow(QtWidgets.QMainWindow):
    """
    Clase principal de la ventana de la aplicación. Configura la interfaz de usuario, manejando
    la lógica para cargar imágenes de referencia, iniciar búsquedas de imágenes y mostrar los resultados.
    Incluye la configuración de áreas de trabajo y vista previa, así como la conexión de señales y slots.
    """
    def __init__(self):
        super().__init__()  # Inicialización de la clase base QMainWindow
        self.setWindowTitle("Buscador por Imágenes")  # Establecimiento del título de la ventana
        icon_path = os.path.join(os.path.dirname(__file__), '../resources/icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(1080, 840)  # Establecimiento del tamaño mínimo de la ventana

        self.centralWidget = QtWidgets.QWidget(self)  # Creación de un widget central para la ventana
        self.setCentralWidget(self.centralWidget)  # Establecimiento del widget central

        self.mainLayout = QtWidgets.QHBoxLayout(self.centralWidget)  # Creación de un layout horizontal para la disposición principal
        
        # Definición del splitter para dividir la ventana en dos partes
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)  # Creación de un splitter horizontal
        self.mainLayout.addWidget(self.splitter)  # Agregar el splitter al layout principal
        
        # Configuración de las áreas de trabajo y vista previa
        self.setupWorkArea()  # Método para configurar el área de trabajo
        self.setupPreviewArea()  # Método para configurar el área de vista previa

        # Conexión de las señales de los botones y la lista de resultados con los métodos correspondientes
        self.searchButton.clicked.connect(self.on_search_clicked)
        self.loadImageButton.clicked.connect(self.on_load_image_clicked)
        self.resultsTree.itemClicked.connect(self.on_result_selected)

        # Instanciación del motor de búsqueda de imágenes y otros atributos necesarios
        self.imageSearchEngine = ImageSearchEngine('//192.168.200.250/rtadiseño/SOLUCIONES IA/BASES DE DATOS/buscador_de_referencias/hashes_imagenes_muebles.db')
        self.image_loader_thread = None  # Inicialización del hilo de carga de imágenes
        self.imageCache = {}  # Inicialización del caché de imágenes

        self.statusBar = self.statusBar()  # Obtener la barra de estado de QMainWindow
        self.statusMessage = QLabel("Listo")  # QLabel para mostrar mensajes
        self.statusBar.addWidget(self.statusMessage)  # Añadir el QLabel a la barra de estado

        self.activeThreads = []  # Lista para mantener referencias activas a los hilos


    def setupWorkArea(self):
        """
        Configura el área de trabajo de la aplicación, incluyendo botones, etiquetas, controles deslizantes
        y otros widgets para ajustar los parámetros de búsqueda de imágenes y cargar una imagen de referencia.
        """
        workArea = QtWidgets.QWidget()  # Creación de un widget para el área de trabajo
        workArea.setMinimumSize(400, 800)  # Establecimiento del tamaño mínimo del área de trabajo
        workLayout = QtWidgets.QVBoxLayout(workArea)  # Creación de un layout vertical para el área de trabajo

        # Botón para cargar imagen de referencia
        self.loadImageButton = QtWidgets.QPushButton("...")  # Creación de un botón para cargar imágenes
        self.loadImageButton.setFixedHeight(30)
        self.loadImageButton.setText("Selecciona la Imagen de Referencia")
        workLayout.addWidget(self.loadImageButton)  # Agregar el botón al layout

        # Contenedor para el combobox y el slider
        self.optionsContainer = QtWidgets.QWidget()  # Creación de un widget para contener el combobox y el slider
        self.optionsLayout = QtWidgets.QHBoxLayout(self.optionsContainer)  # Creación de un layout horizontal para el contenedor

        # Contenedor y layout para el selector de tipo de imagen
        self.imageTypeContainer = QtWidgets.QWidget()  # Creación de un widget para contener el selector de tipo de imagen
        self.imageTypeLayout = QtWidgets.QVBoxLayout(self.imageTypeContainer)  # Creación de un layout vertical para el contenedor
        self.imageTypeLabel = QtWidgets.QLabel("Selecciona el tipo de imagen:")  # Creación de una etiqueta para el selector de tipo de imagen
        self.imageTypeComboBox = QtWidgets.QComboBox()  # Creación de un combobox para seleccionar el tipo de imagen
        self.imageTypeComboBox.addItems(["Ambientado", "Fondo Blanco"])  # Agregar opciones al combobox
        self.imageTypeLayout.addWidget(self.imageTypeLabel)  # Agregar la etiqueta al layout
        self.imageTypeLayout.addWidget(self.imageTypeComboBox)  # Agregar el combobox al layout
        self.optionsLayout.addWidget(self.imageTypeContainer)  # Agregar el contenedor al layout principal

        # Línea vertical de separación
        self.line = QtWidgets.QFrame()  # Creación de una línea para separación visual
        self.line.setFrameShape(QtWidgets.QFrame.VLine)  # Establecimiento de la forma de la línea
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)  # Establecimiento de la sombra de la línea
        self.optionsLayout.addWidget(self.line)  # Agregar la línea al layout principal

        # Contenedor y layout para el slider de umbral de reconocimiento
        self.thresholdContainer = QtWidgets.QWidget()  # Creación de un widget para contener el slider de umbral
        self.thresholdLayout = QtWidgets.QVBoxLayout(self.thresholdContainer)  # Creación de un layout vertical para el contenedor
        
        self.thresholdLabel = QtWidgets.QLabel("Umbral de reconocimiento: 10")  # Creación de una etiqueta para el slider de umbral
        self.thresholdSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)  # Creación de un slider horizontal
        self.thresholdSlider.setMinimum(0)  # Establecimiento del valor mínimo del slider
        self.thresholdSlider.setMaximum(20)  # Establecimiento del valor máximo del slider
        self.thresholdSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)  # Establecimiento de la posición de las marcas del slider
        self.thresholdSlider.setTickInterval(1)  # Establecimiento del intervalo entre las marcas del slider
        self.thresholdSlider.setValue(10)  # Establecimiento del valor inicial del slider
        self.thresholdSlider.valueChanged.connect(self.update_slider_value_label)  # Conexión de la señal del slider al método correspondiente
        
        self.thresholdLayout.addWidget(self.thresholdLabel)  # Agregar la etiqueta al layout
        self.thresholdLayout.addWidget(self.thresholdSlider)  # Agregar el slider al layout
        self.optionsLayout.addWidget(self.thresholdContainer)  # Agregar el contenedor al layout principal

        workLayout.addWidget(self.optionsContainer)  # Agregar el contenedor de opciones al área de trabajo

        # ImageViewer para la imagen de referencia
        self.referenceImageView = ImageViewer()  # Creación de un ImageViewer para mostrar la imagen de referencia
        self.referenceImageView.setMinimumSize(200, 200)  # Establecimiento del tamaño mínimo del ImageViewer

        workLayout.addWidget(self.referenceImageView)  # Agregar el ImageViewer al área de trabajo

        # Botón de búsqueda
        self.searchButton = QtWidgets.QPushButton("Buscar Imagen")  # Creación de un botón para iniciar la búsqueda
        self.searchButton.setFixedHeight(30)  # Establecimiento de la altura fija del botón
        workLayout.addWidget(self.searchButton)  # Agregar el botón al área de trabajo

        # Crear la barra de progreso
        self.progressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setMaximum(1)  # Configurar el valor máximo en 1
        self.progressBar.setValue(0)  # Establecer el valor inicial en 0
        self.progressBar.setAlignment(QtCore.Qt.AlignCenter)  # Alinear el texto en el centro
        self.progressBar.setTextVisible(True)  # Hacer visible el texto del progreso

        # Añadir la barra de progreso al layout
        workLayout.addWidget(self.progressBar)

        # Lista de resultados
        self.resultsTree = QtWidgets.QTreeWidget()  # Creación de un QTreeWidget para mostrar los resultados de la búsqueda
        self.resultsTree.setHeaderLabels(["Nombre de Archivo"])  # Establecimiento de la etiqueta de la cabecera
        workLayout.addWidget(self.resultsTree)  # Agregar la lista de resultados al área de trabajo
        # Conexión de la señal de cambio de elemento seleccionado con el método correspondiente
        self.resultsTree.currentItemChanged.connect(self.on_result_selected)

        self.splitter.addWidget(workArea)  # Agregar el área de trabajo al splitter
        # Asegurar que el ancho del handle sea suficiente para ser visible.
        self.splitter.setHandleWidth(1)  # Establecimiento del ancho del handle del splitter

        # Aplicación de un estilo específico al handle para garantizar su visibilidad.
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #C0C0C0;
            }
            QSplitter::handle:hover {
                background-color: #808080;
            }
            QSplitter::handle:pressed {
                background-color: #606060;
            }
        """)
        # También puedes ajustar la propiedad de expansión de los widgets para asegurarte de que se muestre la línea divisoria.
        self.splitter.setChildrenCollapsible(False)


    def setupPreviewArea(self):
        """
        Configura el área de vista previa dentro de la ventana principal. Crea y añade una vista de
        ImageViewer al layout para mostrar la imagen seleccionada. También ajusta el tamaño mínimo
        para asegurar que el área de vista previa sea adecuadamente visible.
        """

        previewArea = QtWidgets.QWidget()  # Creación de un widget para el área de vista previa
        previewArea.setMinimumSize(624, 800)  # Establecimiento del tamaño mínimo del área de vista previa
        previewLayout = QtWidgets.QVBoxLayout(previewArea)  # Creación de un layout vertical para el área de vista previa

        # Vista previa de la imagen seleccionada
        self.resultPreviewView = ImageViewer()  # Creación de un ImageViewer para mostrar la vista previa de la imagen
        previewLayout.addWidget(self.resultPreviewView)  # Agregar la vista previa al layout

        self.splitter.addWidget(previewArea)  # Agregar el área de vista previa al splitter

    def on_load_image_clicked(self):
        """
        Maneja el evento de clic en el botón de carga de imagen. Abre un cuadro de diálogo para
        seleccionar una imagen y muestra la imagen seleccionada en el área de vista previa de referencia.
        """
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Selecciona una imagen", "", "Images (*.png *.xpm *.jpg)")  # Mostrar el cuadro de diálogo para seleccionar una imagen
        if filename:  # Verificar si se seleccionó un archivo
            print(f"Imagen seleccionada: {filename}")  # Imprimir la ruta de la imagen seleccionada en la consola
            self.display_reference_image(filename)  # Mostrar la imagen seleccionada en el área de vista previa
        else:
            print("No se seleccionó ninguna imagen.")  # Imprimir un mensaje si no se seleccionó ninguna imagen

    def display_reference_image(self, path):
        """
        Muestra la imagen de referencia seleccionada en el área de vista previa.

        Args:
            path: Ruta del archivo de la imagen de referencia a mostrar.
        """

        self.reference_image_path = path  # Almacenar la ruta de la imagen de referencia
        self.referenceImageView.displayImage(path)  # Mostrar la imagen de referencia en el ImageViewer

    def on_search_clicked(self):
        """
        Inicia la búsqueda de imágenes similares basada en la imagen de referencia y el umbral
        de reconocimiento seleccionado. Muestra los resultados en el árbol de resultados.
        """
        print("Buscar imagen presionado")  # Imprimir un mensaje indicando que se ha presionado el botón de búsqueda
        if hasattr(self, 'reference_image_path'):
            # Si ya existe un hilo de búsqueda y está en ejecución, no iniciamos uno nuevo.
            if hasattr(self, 'search_thread') and self.search_thread.isRunning():
                print("La búsqueda ya está en curso. Por favor, espera a que finalice.")
                return

            # Preparar la barra de progreso para la búsqueda
            self.progressBar.setStyleSheet("QProgressBar {color: black;}")
            self.progressBar.setRange(0, 0)  # Indeterminado

            # Crear un nuevo hilo de búsqueda
            self.search_thread = ImageSearchThread(self.reference_image_path, self.thresholdSlider.value(), self)

            # Desconectar señales previas si existen para evitar duplicidad
            try:
                self.search_thread.search_started.disconnect()
                self.search_thread.search_finished.disconnect()
            except Exception as e:
                pass  # Ignorar si no hay señales conectadas anteriormente

            # Conectar las señales del hilo de búsqueda a los slots correspondientes
            self.search_thread.search_started.connect(self.on_search_started)
            self.search_thread.search_finished.connect(self.on_search_finished)

            # Iniciar el hilo de búsqueda
            self.search_thread.start()
        else:
            print("No se ha cargado ninguna imagen de referencia.")


    def update_slider_value_label(self, value):
        """
        Actualiza el texto del label del slider para reflejar el valor actual del umbral de reconocimiento.

        Args:
            value: Valor actual del slider del umbral de reconocimiento.
        """

        # Actualizar el texto del label para incluir el valor del umbral
        self.thresholdLabel.setText(f"Umbral de reconocimiento: {value}")  # Actualizar el texto del label con el valor actual del umbral

    def populate_results_tree(self, results):
        print("Limpiando resultados anteriores...")
        self.resultsTree.clear()  # Limpiar el árbol de resultados antes de llenarlo con nuevos resultados
        
        # Ordenar los resultados por la diferencia de hash (de menor a mayor)
        results.sort(key=lambda x: x[1])
        
        print(f"Agregando {len(results)} nuevos resultados...")
        for full_path, hash_diff in results:
            filename = os.path.basename(full_path)  # Obtener solo el nombre del archivo de la ruta completa
            item = QtWidgets.QTreeWidgetItem(self.resultsTree)  # Crear un nuevo ítem en el árbol de resultados
            item.setText(0, filename)  # Establecer el texto del ítem con el nombre del archivo
            item.setData(0, QtCore.Qt.UserRole, full_path)  # Asociar la ruta completa del archivo como un dato adicional en el ítem

        # Opcionalmente, puedes ajustar la altura de los ítems si lo consideras necesario
        self.resultsTree.setStyleSheet("QTreeWidget::item { height: 20px; }")


    def on_result_selected(self, current, previous):
        if current is not None:  # Verificar si se ha seleccionado un elemento en la lista de resultados
            full_path = current.data(0, QtCore.Qt.UserRole)  # Obtener la ruta completa del archivo desde los datos del ítem
            print(f"Imagen seleccionada desde los resultados: {full_path}")  # Imprimir la ruta de la imagen seleccionada en la consola

            self.display_result_image(full_path)  # Mostrar la imagen seleccionada en resultPreviewView

    def display_result_image(self, path):
        """Muestra la imagen seleccionada en resultPreviewView."""
        self.resultPreviewView.displayImage(path)  # Asumiendo que displayImage es un método en ImageViewer para mostrar la imagen


    def load_and_cache_image(self, path):
        # Aquí iría el código de carga y procesamiento de la imagen
        # Una vez cargada y procesada la imagen, guárdala en el caché
        original_image = Image.open(path)  # Abrir la imagen original
        original_image = original_image.convert("RGB")  # Convertir la imagen a formato RGB
        max_size = 1000, 1000  # Tamaño máximo permitido
        original_image.thumbnail(max_size, Image.Resampling.LANCZOS)  # Redimensionar la imagen manteniendo su aspecto
        byte_io = io.BytesIO()  # Crear un objeto de BytesIO para almacenar la imagen
        original_image.save(byte_io, 'JPEG')  # Guardar la imagen en formato JPEG en el objeto BytesIO
        qimage = QImage()  # Crear un objeto QImage
        qimage.loadFromData(byte_io.getvalue())  # Cargar la imagen desde los datos almacenados en el objeto BytesIO
        pixmap = QPixmap.fromImage(qimage)  # Crear un QPixmap a partir del QImage
        self.imageCache[path] = pixmap  # Almacenar el QPixmap en el caché
        self.resultPreviewView.setPixmap(pixmap)  # Mostrar la imagen en la vista previa de resultados

    def on_search_started(self):
        self.statusMessage.setText("Buscando...")
        self.progressBar.setRange(0, 0)  # Iniciar la animación de la barra de progreso
        self.progressBar.setStyleSheet("QProgressBar {color: green;}")    

    def on_search_finished(self, resultados):
        self.populate_results_tree(resultados)
        self.statusMessage.setText("Búsqueda completada.")
        self.progressBar.setRange(0, 1)
        self.progressBar.setValue(1)
        self.progressBar.setStyleSheet("QProgressBar {color: black;}")

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)  # Crear una aplicación Qt
    mainWindow = MainWindow()  # Crear la ventana principal
    mainWindow.show()  # Mostrar la ventana principal
    sys.exit(app.exec_())  # Ejecutar el bucle principal de eventos de la aplicación
