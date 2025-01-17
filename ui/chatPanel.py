from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime

class MessageBubble(QFrame):
    """Widget personalizado para representar un mensaje en el chat."""
    def __init__(self, sender: str, message: str, timestamp: str,
                 is_error: bool = False, parent=None):
        super().__init__(parent)
        self.sender = sender
        self.is_user = (sender.lower() == "usuario")

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
            # Mensaje del usuario (alineado a la derecha)
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
            # Mensaje del asistente (alineado a la izquierda)
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

        # Etiqueta de remitente (Opcional, si deseas mostrar "Asistente"/"Usuario")
        sender_label = QLabel(sender)
        sender_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                font-weight: bold;
                color: {"#ffffff" if self.is_user else "#333333"};
            }}
        """)
        layout.addWidget(sender_label)

        # Texto del mensaje
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextFormat(Qt.RichText)  # Permitir formato HTML
        message_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {"#ffffff" if self.is_user else "#333333"};
            }}
        """)
        layout.addWidget(message_label)

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

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)


class ChatPanel(QWidget):
    """Panel de chat con interacción mediante botones."""
    # Si ya no usas mensajes de texto directo, puedes eliminar esta señal
    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

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
