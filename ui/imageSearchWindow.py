"""
Nombre del Archivo: imageSearchWindow.py
Descripción: Este módulo implementa la interfaz gráfica para la búsqueda de imágenes por similitud.
             Permite a los usuarios cargar una imagen de referencia y encontrar imágenes similares
             en la base de datos utilizando algoritmos de hash perceptual.

Características Principales:
- Carga y visualización de imágenes de referencia
- Ajuste de parámetros de búsqueda (tipo de imagen y umbral de similitud)
- Visualización de resultados en tiempo real
- Vista previa de imágenes encontradas
- Interfaz dividida para mejor organización visual

Clases Principales:
- ImageViewer: Visualizador personalizado de imágenes
- ImageSearchThread: Manejo asíncrono de búsquedas
- MainWindow: Ventana principal de la interfaz de búsqueda

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

# Importaciones del sistema
import io
import os

# Importaciones de PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, QRectF, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QLabel

# Importaciones locales
from core.imageSearchAlgorithm import ImageSearchEngine
from PIL import Image


class ImageViewer(QGraphicsView):
    """
    Visualizador personalizado de imágenes basado en QGraphicsView.
    
    Esta clase proporciona una vista interactiva para mostrar imágenes, manteniendo
    la relación de aspecto y permitiendo una visualización óptima. Se utiliza tanto
    para mostrar la imagen de referencia como para la vista previa de resultados.

    Attributes:
        scene (QGraphicsScene): Escena que contiene la imagen a mostrar.
    """

    def __init__(self, parent=None):
        """
        Inicializa el visualizador de imágenes.

        Args:
            parent (QWidget, optional): Widget padre al que pertenece este visualizador.
        """
        super(ImageViewer, self).__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

    def displayImage(self, imagePath):
        """
        Carga y muestra una imagen en el visualizador.

        Este método se encarga de cargar una imagen desde una ruta específica,
        ajustarla a la vista manteniendo su relación de aspecto, y mostrarla
        en la escena del visualizador.

        Args:
            imagePath (str): Ruta absoluta al archivo de imagen a mostrar.
        """
        pixmap = QPixmap(imagePath)
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        rectF = QRectF(pixmap.rect())
        self.scene.setSceneRect(rectF)
        self.fitInView(rectF, QtCore.Qt.KeepAspectRatio)


class ImageSearchThread(QThread):
    """
    Hilo dedicado para realizar búsquedas de imágenes similares.

    Esta clase maneja el proceso de búsqueda de imágenes en segundo plano,
    evitando que la interfaz de usuario se bloquee durante búsquedas extensas.
    Utiliza el algoritmo de hash perceptual para encontrar imágenes similares.

    Signals:
        search_started: Emitida cuando comienza la búsqueda.
        search_finished (list): Emitida cuando la búsqueda finaliza, con la lista de resultados.

    Attributes:
        image_path (str): Ruta de la imagen de referencia.
        threshold (float): Umbral de similitud para la búsqueda.
        imageSearchEngine (ImageSearchEngine): Motor de búsqueda de imágenes.
    """

    search_started = pyqtSignal()
    search_finished = pyqtSignal(list)

    def __init__(self, image_path, threshold, parent=None):
        """
        Inicializa el hilo de búsqueda.

        Args:
            image_path (str): Ruta de la imagen de referencia.
            threshold (float): Umbral de similitud (0-20).
            parent (QObject, optional): Objeto padre del hilo.
        """
        super(ImageSearchThread, self).__init__(parent)
        self.image_path = image_path
        self.threshold = threshold
        self.imageSearchEngine = ImageSearchEngine('//192.168.200.250/rtadiseño/SOLUCIONES IA/BASES DE DATOS/buscador_de_referencias/hashes_imagenes_muebles.db')

    def load_and_process_image(self, image_path):
        """
        Carga y procesa una imagen para su uso en la búsqueda.

        Este método utiliza PIL para cargar la imagen y realizar cualquier
        procesamiento necesario antes de la búsqueda. Actualmente solo carga
        la imagen, pero está preparado para añadir procesamientos adicionales
        como redimensionamiento o conversión de color.

        Args:
            image_path (str): Ruta al archivo de imagen a procesar.

        Returns:
            Image: Objeto Image de PIL con la imagen procesada.
        """
        image = Image.open(image_path)
        return image

    def run(self):
        """
        Ejecuta la búsqueda de imágenes similares en segundo plano.

        Este método se ejecuta en un hilo separado cuando se inicia la búsqueda.
        Emite señales al comenzar y finalizar la búsqueda, y procesa la imagen
        de referencia para encontrar imágenes similares en la base de datos.
        """
        self.search_started.emit()
        if os.path.exists(self.image_path):
            imagen_referencia = self.load_and_process_image(self.image_path)
            resultados = self.imageSearchEngine.buscar_imagenes_similares(imagen_referencia, self.threshold)
            self.search_finished.emit(resultados)


class MainWindow(QtWidgets.QMainWindow):
    """
    Ventana principal de la interfaz de búsqueda de imágenes.

    Esta clase implementa la interfaz gráfica principal para la búsqueda de imágenes
    por similitud. Proporciona una interfaz dividida con un área de trabajo para
    configurar la búsqueda y un área de vista previa para visualizar resultados.

    La ventana permite:
    - Cargar imágenes de referencia
    - Ajustar parámetros de búsqueda
    - Visualizar resultados en tiempo real
    - Previsualizar imágenes encontradas
    - Gestionar múltiples búsquedas simultáneas

    Attributes:
        imageSearchEngine (ImageSearchEngine): Motor de búsqueda de imágenes.
        image_loader_thread (QThread): Hilo para cargar imágenes.
        imageCache (dict): Caché de imágenes cargadas.
        activeThreads (list): Lista de hilos activos.
        statusMessage (QLabel): Etiqueta para mostrar mensajes de estado.
    """

    def __init__(self):
        """
        Inicializa la ventana principal de búsqueda de imágenes.

        Configura la interfaz gráfica, inicializa los componentes necesarios
        y establece las conexiones entre señales y slots. También configura
        el layout principal y las áreas de trabajo y vista previa.
        """
        super().__init__()
        self.setWindowTitle("Buscador por Imágenes")
        icon_path = os.path.join(os.path.dirname(__file__), '../resources/icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(1080, 840)

        self.centralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralWidget)

        self.mainLayout = QtWidgets.QHBoxLayout(self.centralWidget)
        
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.mainLayout.addWidget(self.splitter)
        
        self.setupWorkArea()
        self.setupPreviewArea()

        self.searchButton.clicked.connect(self.on_search_clicked)
        self.loadImageButton.clicked.connect(self.on_load_image_clicked)
        self.resultsTree.itemClicked.connect(self.on_result_selected)

        self.imageSearchEngine = ImageSearchEngine('//192.168.200.250/rtadiseño/SOLUCIONES IA/BASES DE DATOS/buscador_de_referencias/hashes_imagenes_muebles.db')
        self.image_loader_thread = None
        self.imageCache = {}

        self.statusBar = self.statusBar()
        self.statusMessage = QLabel("Listo")
        self.statusBar.addWidget(self.statusMessage)

        self.activeThreads = []


    def setupWorkArea(self):
        """
        Configura el área de trabajo de la interfaz.

        Esta área contiene los controles principales para la búsqueda:
        - Botón para cargar imagen de referencia
        - Selector de tipo de imagen (Ambientado/Fondo Blanco)
        - Control deslizante para ajustar el umbral de reconocimiento
        - Vista previa de la imagen de referencia
        - Botón de búsqueda
        - Barra de progreso
        - Lista de resultados
        """
        workArea = QtWidgets.QWidget()
        workArea.setMinimumSize(400, 800)
        workLayout = QtWidgets.QVBoxLayout(workArea)

        # Botón para cargar imagen de referencia
        self.loadImageButton = QtWidgets.QPushButton("...")
        self.loadImageButton.setFixedHeight(30)
        self.loadImageButton.setText("Selecciona la Imagen de Referencia")
        workLayout.addWidget(self.loadImageButton)

        # Contenedor para opciones de búsqueda
        self.optionsContainer = QtWidgets.QWidget()
        self.optionsLayout = QtWidgets.QHBoxLayout(self.optionsContainer)

        # Configuración del selector de tipo de imagen
        self.imageTypeContainer = QtWidgets.QWidget()
        self.imageTypeLayout = QtWidgets.QVBoxLayout(self.imageTypeContainer)
        self.imageTypeLabel = QtWidgets.QLabel("Selecciona el tipo de imagen:")
        self.imageTypeComboBox = QtWidgets.QComboBox()
        self.imageTypeComboBox.addItems(["Ambientado", "Fondo Blanco"])
        self.imageTypeLayout.addWidget(self.imageTypeLabel)
        self.imageTypeLayout.addWidget(self.imageTypeComboBox)
        self.optionsLayout.addWidget(self.imageTypeContainer)

        # Línea separadora vertical
        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.optionsLayout.addWidget(self.line)

        # Configuración del control de umbral
        self.thresholdContainer = QtWidgets.QWidget()
        self.thresholdLayout = QtWidgets.QVBoxLayout(self.thresholdContainer)
        self.thresholdLabel = QtWidgets.QLabel("Umbral de reconocimiento: 10")
        self.thresholdSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.thresholdSlider.setMinimum(0)
        self.thresholdSlider.setMaximum(20)
        self.thresholdSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.thresholdSlider.setTickInterval(1)
        self.thresholdSlider.setValue(10)
        self.thresholdSlider.valueChanged.connect(self.update_slider_value_label)
        
        self.thresholdLayout.addWidget(self.thresholdLabel)
        self.thresholdLayout.addWidget(self.thresholdSlider)
        self.optionsLayout.addWidget(self.thresholdContainer)

        workLayout.addWidget(self.optionsContainer)

        # Vista previa de la imagen de referencia
        self.referenceImageView = ImageViewer()
        self.referenceImageView.setMinimumSize(200, 200)
        workLayout.addWidget(self.referenceImageView)

        # Botón de búsqueda
        self.searchButton = QtWidgets.QPushButton("Buscar Imagen")
        self.searchButton.setFixedHeight(30)
        workLayout.addWidget(self.searchButton)

        # Barra de progreso
        self.progressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setMaximum(1)
        self.progressBar.setValue(0)
        self.progressBar.setAlignment(QtCore.Qt.AlignCenter)
        self.progressBar.setTextVisible(True)
        workLayout.addWidget(self.progressBar)

        # Lista de resultados
        self.resultsTree = QtWidgets.QTreeWidget()
        self.resultsTree.setHeaderLabels(["Nombre de Archivo"])
        workLayout.addWidget(self.resultsTree)
        self.resultsTree.currentItemChanged.connect(self.on_result_selected)

        self.splitter.addWidget(workArea)
        self.splitter.setHandleWidth(1)

        # Estilo del separador
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
        self.splitter.setChildrenCollapsible(False)

    def setupPreviewArea(self):
        """
        Configura el área de vista previa de la interfaz.

        Esta área muestra una vista ampliada de la imagen seleccionada
        de los resultados de búsqueda. Incluye:
        - Visualizador de imagen a tamaño completo
        - Ajuste automático de tamaño manteniendo la relación de aspecto
        """
        previewArea = QtWidgets.QWidget()
        previewArea.setMinimumSize(624, 800)
        previewLayout = QtWidgets.QVBoxLayout(previewArea)

        self.resultPreviewView = ImageViewer()
        previewLayout.addWidget(self.resultPreviewView)

        self.splitter.addWidget(previewArea)

    def on_load_image_clicked(self):
        """
        Maneja el evento de carga de una nueva imagen de referencia.

        Abre un diálogo de selección de archivo para que el usuario elija
        una imagen. Una vez seleccionada, la muestra en el visualizador
        de referencia y actualiza la interfaz.
        """
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Selecciona una imagen",
            "",
            "Images (*.png *.xpm *.jpg)"
        )
        if filename:
            self.display_reference_image(filename)

    def display_reference_image(self, path):
        """
        Muestra la imagen de referencia en el visualizador.

        Args:
            path (str): Ruta al archivo de imagen que se mostrará como referencia.

        La imagen se carga, se procesa y se muestra en el visualizador de referencia.
        También se habilita el botón de búsqueda una vez que hay una imagen cargada.
        """
        self.reference_image_path = path
        self.referenceImageView.load_image(path)
        self.searchButton.setEnabled(True)

    def update_slider_value_label(self, value):
        """
        Actualiza la etiqueta del control deslizante con el valor actual.

        Args:
            value (int): Valor actual del control deslizante.

        La etiqueta se actualiza para mostrar el valor actual del umbral
        de reconocimiento seleccionado por el usuario.
        """
        self.thresholdLabel.setText(f"Umbral de reconocimiento: {value}")

    def on_search_clicked(self):
        """
        Maneja el evento de clic en el botón de búsqueda.

        Inicia el proceso de búsqueda de imágenes similares:
        1. Deshabilita la interfaz durante la búsqueda
        2. Crea y configura un nuevo hilo de búsqueda
        3. Conecta las señales del hilo con los manejadores correspondientes
        4. Inicia la búsqueda en segundo plano
        """
        if not hasattr(self, 'reference_image_path'):
            return

        self.disable_interface()
        self.resultsTree.clear()

        self.search_thread = ImageSearchThread(
            self.reference_image_path,
            self.thresholdSlider.value(),
            self.imageTypeComboBox.currentText()
        )

        self.search_thread.started.connect(self.on_search_started)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.progress.connect(self.update_progress)
        self.search_thread.result_found.connect(self.add_result)

        self.search_thread.start()

    def disable_interface(self):
        """
        Deshabilita los elementos de la interfaz durante la búsqueda.

        Esto incluye:
        - Botón de carga de imagen
        - Selector de tipo de imagen
        - Control deslizante de umbral
        - Botón de búsqueda
        """
        self.loadImageButton.setEnabled(False)
        self.imageTypeComboBox.setEnabled(False)
        self.thresholdSlider.setEnabled(False)
        self.searchButton.setEnabled(False)

    def enable_interface(self):
        """
        Habilita los elementos de la interfaz después de la búsqueda.

        Esto incluye:
        - Botón de carga de imagen
        - Selector de tipo de imagen
        - Control deslizante de umbral
        - Botón de búsqueda
        """
        self.loadImageButton.setEnabled(True)
        self.imageTypeComboBox.setEnabled(True)
        self.thresholdSlider.setEnabled(True)
        self.searchButton.setEnabled(True)

    def on_search_started(self):
        """
        Maneja el evento de inicio de búsqueda.

        Configura la barra de progreso y muestra un mensaje inicial
        indicando que la búsqueda ha comenzado.
        """
        self.progressBar.setFormat("Iniciando búsqueda...")
        self.progressBar.setValue(0)

    def on_search_finished(self):
        """
        Maneja el evento de finalización de búsqueda.

        Realiza las siguientes acciones:
        1. Habilita nuevamente la interfaz
        2. Actualiza la barra de progreso al 100%
        3. Muestra un mensaje de finalización
        4. Limpia las conexiones del hilo de búsqueda
        """
        self.enable_interface()
        self.progressBar.setValue(self.progressBar.maximum())
        self.progressBar.setFormat("Búsqueda completada")
        
        self.search_thread.started.disconnect()
        self.search_thread.finished.disconnect()
        self.search_thread.progress.disconnect()
        self.search_thread.result_found.disconnect()
        self.search_thread = None

    def update_progress(self, current, total):
        """
        Actualiza la barra de progreso durante la búsqueda.

        Args:
            current (int): Número de archivos procesados
            total (int): Número total de archivos a procesar

        Actualiza el valor y el texto de la barra de progreso para
        mostrar el progreso actual de la búsqueda.
        """
        self.progressBar.setMaximum(total)
        self.progressBar.setValue(current)
        self.progressBar.setFormat(f"Procesando... {current}/{total}")

    def add_result(self, path, similarity):
        """
        Añade un resultado a la lista de imágenes encontradas.

        Args:
            path (str): Ruta al archivo de imagen encontrado
            similarity (float): Valor de similitud con la imagen de referencia

        Crea un nuevo elemento en el árbol de resultados con la información
        de la imagen encontrada y su porcentaje de similitud.
        """
        item = QtWidgets.QTreeWidgetItem(self.resultsTree)
        filename = os.path.basename(path)
        similarity_percentage = round((1 - similarity/20) * 100, 2)
        item.setText(0, f"{filename} ({similarity_percentage}% similar)")
        item.setData(0, QtCore.Qt.UserRole, path)

    def on_result_selected(self, current, previous):
        """
        Maneja el evento de selección de un resultado.

        Args:
            current (QTreeWidgetItem): Elemento actualmente seleccionado
            previous (QTreeWidgetItem): Elemento previamente seleccionado

        Cuando se selecciona un resultado en la lista, carga y muestra
        la imagen correspondiente en el visualizador de vista previa.
        """
        if current is None:
            return
            
        path = current.data(0, QtCore.Qt.UserRole)
        if path:
            self.resultPreviewView.load_image(path)

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
