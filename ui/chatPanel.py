from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime
import os
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_prompts.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FileButton(QPushButton):
    """Botón personalizado para archivos y carpetas."""
    file_selected = pyqtSignal(str, str)  # path, type

    def __init__(self, text: str, file_path: str, button_type: str = "default", parent=None):
        super().__init__(text, parent)
        self.file_path = file_path
        self.button_type = button_type
        self.clicked.connect(self._on_click)
        
        # Estilos base
        base_style = """
            QPushButton {
                padding: 4px 8px;
                border-radius: 4px;
                color: white;
                font-size: 12px;
                border: none;
                margin: 2px;
            }
            QPushButton:hover {
                border: none;
            }
            QPushButton:pressed {
                border: none;
            }
        """
        
        # Estilos específicos según tipo
        if button_type == "folder":
            self.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #28a745;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
            """)
        elif button_type == "pdf":
            self.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #dc3545;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
        elif button_type == "rhino":
            self.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #6c757d;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
                QPushButton:pressed {
                    background-color: #545b62;
                }
            """)
        elif button_type in ["choose_rhino", "skip_rhino"]:
            color = "#007bff" if button_type == "choose_rhino" else "#dc3545"
            hover_color = "#0056b3" if button_type == "choose_rhino" else "#c82333"
            pressed_color = "#004085" if button_type == "choose_rhino" else "#bd2130"
            self.setStyleSheet(base_style + f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    min-width: 60px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                }}
                QPushButton:pressed {{
                    background-color: {pressed_color};
                }}
            """)
    
    def _on_click(self):
        """Maneja el clic del botón abriendo el archivo o carpeta."""
        try:
            if self.button_type in ["choose_rhino", "skip_rhino"]:
                # Emitir señal para manejar la selección
                logger.info(f"FileButton: Emitiendo señal de selección para: {self.button_type}")
                self.file_selected.emit(self.file_path, self.button_type)
            else:
                # Comportamiento normal de abrir archivo/carpeta
                os.startfile(self.file_path)
        except Exception as e:
            logger.error(f"Error al manejar {self.file_path}: {str(e)}")

class MessageBubble(QFrame):
    """Widget personalizado para representar un mensaje en el chat."""
    file_selected = pyqtSignal(str, str)  # path, type

    def __init__(self, sender: str, message: str, timestamp: str,
                 is_error: bool = False, parent=None):
        super().__init__(parent)
        self.sender = sender
        self.is_user = (sender.lower() == "usuario")
        self.buttons = []  # Lista para mantener referencia a los botones

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setLineWidth(1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        # Estilos según remitente
        if is_error:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #ffe6e6;
                    border: 1px solid #ffcccc;
                    border-radius: 15px;
                    margin: 5px;
                    width: 100%;
                }
            """)
        elif self.is_user:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #007bff;
                    color: white;
                    border-radius: 15px;
                    margin: 5px;
                    width: 100%;
                }
            """)
        else:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 15px;
                    margin: 5px;
                    width: 100%;
                }
            """)

        # Layout de la burbuja
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)

        # Etiqueta de remitente
        sender_label = QLabel(sender)
        sender_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                font-weight: bold;
                color: {"#ffffff" if self.is_user else "#333333"};
            }}
        """)
        layout.addWidget(sender_label)

        # Contenedor para el mensaje y los botones
        message_container = QWidget()
        message_layout = QVBoxLayout(message_container)
        message_layout.setSpacing(4)
        message_layout.setContentsMargins(0, 0, 0, 0)

        # Procesar el mensaje para extraer botones
        self._process_message(message, message_layout)

        layout.addWidget(message_container)

        # Timestamp
        time_label = QLabel(timestamp)
        time_label.setAlignment(Qt.AlignRight)
        time_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                color: {"#ffffff80" if self.is_user else "#666666"};
            }}
        """)
        layout.addWidget(time_label)

    def _process_message(self, message: str, layout: QVBoxLayout):
        """Procesa el mensaje y crea los botones necesarios."""
        # Dividir el mensaje en partes
        parts = message.split("<file_button>")
        
        # Contenedor para botones de acción
        action_buttons_container = None
        
        for i, part in enumerate(parts):
            if i == 0:
                if part.strip():
                    # Procesar cada línea del texto
                    for line in part.split('\n'):
                        if line.strip():
                            if line.strip() == "---":
                                # Crear divisor
                                divider = QFrame()
                                divider.setFrameShape(QFrame.HLine)
                                divider.setStyleSheet("""
                                    QFrame {
                                        border: none;
                                        background-color: #e9ecef;
                                        height: 1px;
                                        margin: 8px 0;
                                    }
                                """)
                                layout.addWidget(divider)
                            else:
                                label = QLabel(line.strip())
                                label.setWordWrap(True)
                                label.setStyleSheet(f"""
                                    QLabel {{
                                        font-size: 12px;
                                        color: {"#ffffff" if self.is_user else "#333333"};
                                    }}
                                """)
                                layout.addWidget(label)
                continue

            # Procesar botón
            button_info, remaining_text = part.split("</file_button>", 1)
            try:
                button_data = eval(button_info)  # Convierte el string a diccionario
                logger.debug(f"Creando botón: {button_data}")
                
                button = FileButton(
                    text=button_data['text'],
                    file_path=button_data['path'],
                    button_type=button_data['type']
                )
                
                # Conectar señal de selección de archivo y mantener referencia
                button.file_selected.connect(self.file_selected)
                self.buttons.append(button)  # Mantener referencia al botón
                logger.debug(f"Señal conectada para botón: {button_data['type']}")
                
                # Crear contenedor horizontal para el botón
                button_container = QWidget()
                button_layout = QHBoxLayout(button_container)
                button_layout.setContentsMargins(0, 0, 0, 0)
                button_layout.setSpacing(0)
                
                # Si hay indentación especificada
                if button_data.get('indent'):
                    button_layout.addSpacing(20)  # Añadir espacio para indentación
                    
                button_layout.addWidget(button)
                button_layout.addStretch()
                
                layout.addWidget(button_container)
            except Exception as e:
                logger.error(f"Error procesando botón: {str(e)}")

            # Procesar el texto restante
            if remaining_text.strip():
                # Procesar cada línea del texto restante
                for line in remaining_text.split('\n'):
                    if line.strip():
                        if line.strip() == "---":
                            # Crear divisor
                            divider = QFrame()
                            divider.setFrameShape(QFrame.HLine)
                            divider.setStyleSheet("""
                                QFrame {
                                    border: none;
                                    background-color: #e9ecef;
                                    height: 1px;
                                    margin: 8px 0;
                                }
                            """)
                            layout.addWidget(divider)
                        else:
                            label = QLabel(line.strip())
                            label.setWordWrap(True)
                            label.setStyleSheet(f"""
                                QLabel {{
                                    font-size: 12px;
                                    color: {"#ffffff" if self.is_user else "#333333"};
                                }}
                            """)
                            layout.addWidget(label)
                            
        # El botón "No elegir ninguno" ya no es necesario porque se maneja a través del botón "Omitir archivo Rhino"
        # que se envía desde el ChatManager
        
    def _on_skip_button_clicked(self):
        """[DEPRECATED] Este método ya no se usa."""
        pass

class ChatPanel(QWidget):
    """Panel de chat con interacción mediante botones."""
    # Señales
    message_sent = pyqtSignal(str)
    file_selected = pyqtSignal(str, str)  # path, type

    def __init__(self, parent=None):
        super().__init__(parent)

        # Inicializar contadores de tokens
        self.input_tokens = 0
        self.output_tokens = 0

        # Estilo genérico de botones
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
            QPushButton:pressed {
                background-color: #007bff;
                color: white;
                border: 1px solid #0056b3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """

        self.typing_timer = QTimer()
        self.typing_timer.setInterval(500)
        self.typing_timer.timeout.connect(self._update_typing_animation)
        self.typing_dots = 0

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        # Título o encabezado del chat
        title_label = QLabel("Asistente IA")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
        layout.addWidget(title_label)

        # Área scrollable para mostrar los mensajes
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #ffffff;
            }
        """)

        # Contenedor de mensajes
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setSpacing(5)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.addStretch()  # Mantiene los mensajes arriba

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)

        # Indicador de "Asistente escribiendo..."
        self.typing_label = QLabel("")
        self.typing_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-style: italic;
                padding: 3px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.typing_label)

        # (Opcional) Etiqueta de costo
        self.cost_label = QLabel("Costo de la interacción: $0.00")
        self.cost_label.setAlignment(Qt.AlignRight)
        self.cost_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 11px;
                padding: 2px;
                font-style: italic;
            }
        """)
        layout.addWidget(self.cost_label)

        # Etiqueta de tokens
        self.tokens_label = QLabel("Tokens: 0 entrada / 0 salida")
        self.tokens_label.setAlignment(Qt.AlignRight)
        self.tokens_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 11px;
                padding: 2px;
                font-style: italic;
            }
        """)
        layout.addWidget(self.tokens_label)

        self.setStyleSheet("""
            ChatPanel {
                background-color: #ffffff;
            }
        """)

        self.setLayout(layout)

    def append_message(self, sender: str, message: str, is_error: bool = False):
        """Agrega una burbuja de mensaje al panel de chat."""
        current_time = datetime.now().strftime("%H:%M")
        bubble = MessageBubble(sender, message, current_time, is_error, self.messages_container)
        
        # Conectar señal de selección de archivo
        bubble.file_selected.connect(self._handle_file_selection)

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        if sender.lower() == "usuario":
            # Mensajes del usuario a la derecha
            container_layout.addStretch()
            container_layout.addWidget(bubble)
            container_layout.setStretchFactor(bubble, 0)
        else:
            # Mensajes del sistema o asistente a la izquierda
            container_layout.addWidget(bubble)
            container_layout.addStretch()
            container_layout.setStretchFactor(bubble, 0)

        # Insertamos el mensaje justo antes del stretch final
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, container)
        
        # Forzar el redimensionamiento inmediato
        bubble_width = int(self.scroll_area.width() * 0.9)
        bubble.setFixedWidth(bubble_width)
        
        # Programar una actualización adicional para asegurar el tamaño correcto
        QTimer.singleShot(0, lambda: self._update_bubble_sizes())
        
        self._scroll_to_bottom()

    def _handle_file_selection(self, file_path: str, selection_type: str):
        """Maneja la selección de archivos y la reenvía."""
        logger.info(f"ChatPanel: Recibida selección de archivo - Path: {file_path}, Type: {selection_type}")
        self.file_selected.emit(file_path, selection_type)

    def _update_bubble_sizes(self):
        """Actualiza el tamaño de todas las burbujas."""
        bubble_width = int(self.scroll_area.width() * 0.9)
        
        for i in range(self.messages_layout.count()):
            item = self.messages_layout.itemAt(i)
            if item and item.widget():
                container = item.widget()
                layout = container.layout()
                if layout:
                    for j in range(layout.count()):
                        bubble_item = layout.itemAt(j)
                        bubble_widget = bubble_item.widget()
                        if isinstance(bubble_widget, MessageBubble):
                            bubble_widget.setFixedWidth(bubble_width)

    def showEvent(self, event):
        """Se llama cuando el widget se muestra por primera vez."""
        super().showEvent(event)
        QTimer.singleShot(0, self._update_bubble_sizes)

    def resizeEvent(self, event):
        """Ajusta el ancho máximo de las burbujas cuando se redimensiona la ventana."""
        super().resizeEvent(event)
        self._update_bubble_sizes()
        self._scroll_to_bottom()

    def show_action_buttons(self, actions):
        """
        Muestra una fila de botones para que el usuario elija su respuesta.
        `actions` es una lista de diccionarios con: {"text": str, "callback": callable}
        """
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(20, 5, 20, 5)
        layout.setSpacing(10)

        button_list = []

        for action_dict in actions:
            btn = QPushButton(action_dict["text"])
            btn.setStyleSheet(self.button_style + """
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    min-width: 60px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """)

            def make_callback(btn_ref, texto_opcion, original_callback):
                def on_click():
                    # El usuario seleccionó el texto_opcion
                    self.append_message("Usuario", f"{texto_opcion}")
                    # Ejecutamos el callback real (por ejemplo, tu lógica de IA)
                    original_callback()
                    # Deshabilitar todos los botones tras la elección
                    for b in button_list:
                        b.setEnabled(False)
                        b.setStyleSheet(self.button_style + """
                            QPushButton {
                                background-color: #cccccc;
                                color: #666666;
                            }
                        """)
                return on_click

            btn.clicked.connect(make_callback(btn, action_dict["text"], action_dict["callback"]))
            layout.addWidget(btn)
            button_list.append(btn)

        # Insertar los botones en el layout de mensajes
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, container)
        self._scroll_to_bottom()

    def clear_action_buttons(self):
        """Elimina solamente los contenedores de botones; preserva los mensajes."""
        for i in reversed(range(self.messages_layout.count())):
            item = self.messages_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # Si no es la stretch final y no es una burbuja de mensaje, lo quitamos
                if isinstance(widget, QWidget) and not self._is_bubble_container(widget):
                    widget.deleteLater()

    def clear_chat(self):
        """Opcional: Limpia todo el historial de mensajes. Llamar solo si inicias nueva conversación."""
        while self.messages_layout.count() > 1:  # Mantener el stretch final
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.typing_label.clear()
        self.cost_label.setText("Costo de la interacción: $0.00")
        self.tokens_label.setText("Tokens: 0 entrada / 0 salida")
        self.input_tokens = 0
        self.output_tokens = 0

    def set_typing_status(self, is_typing: bool):
        """Muestra u oculta el indicador de 'escribiendo...'."""
        if is_typing:
            self.typing_dots = 0
            self.typing_timer.start()
            self._update_typing_animation()
        else:
            self.typing_timer.stop()
            self.typing_label.setText("")

    def update_cost(self, cost: float):
        """Actualiza el costo de interacción mostrado (opcional)."""
        self.cost_label.setText(f"Costo de la interacción: ${cost:.4f}")

    def _update_typing_animation(self):
        """Actualiza la animación de los puntos suspensivos para 'escribiendo...'."""
        self.typing_dots = (self.typing_dots + 1) % 4
        dots = "." * self.typing_dots
        self.typing_label.setText(f"El asistente está escribiendo{dots}")

    def _scroll_to_bottom(self):
        """Hace scroll hasta el final después de agregar un mensaje/botón."""
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def _is_bubble_container(self, widget):
        """Verifica si el widget dado contiene una burbuja de mensaje."""
        if not widget.layout():
            return False
        for i in range(widget.layout().count()):
            child = widget.layout().itemAt(i).widget()
            if isinstance(child, MessageBubble):
                return True
        return False

    def update_tokens(self, input_tokens: int, output_tokens: int):
        """
        Actualiza el contador de tokens mostrado.
        
        Args:
            input_tokens: Total de tokens de entrada acumulados
            output_tokens: Total de tokens de salida acumulados
        """
        # Actualizar los totales
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        
        # Formatear números con separadores de miles
        formatted_input = f"{input_tokens:,}".replace(",", ".")
        formatted_output = f"{output_tokens:,}".replace(",", ".")
        total_tokens = f"{(input_tokens + output_tokens):,}".replace(",", ".")
        
        # Actualizar el label con el formato: "Tokens totales: X.XXX (Entrada: Y.YYY | Salida: Z.ZZZ)"
        self.tokens_label.setText(
            f"Tokens totales: {total_tokens} (Entrada: {formatted_input} | Salida: {formatted_output})"
        )
