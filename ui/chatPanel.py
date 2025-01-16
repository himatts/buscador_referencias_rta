"""
Panel de chat integrado en la ventana principal.
Este módulo implementa la interfaz visual del chat que se mostrará
cuando se active el modo 'Referencias con creación de carpeta'.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QKeyEvent

class ChatPanel(QWidget):
    """Panel de chat que permite la interacción entre el usuario y el LLM."""
    
    # Señales para comunicación con otros componentes
    message_sent = pyqtSignal(str)  # Emitida cuando el usuario envía un mensaje
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Definir el estilo de botón consistente con mainWindow
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
        self.init_ui()
        
    def init_ui(self):
        """Inicializa la interfaz de usuario del panel."""
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Título del chat
        title_label = QLabel("Asistente RTA")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
        layout.addWidget(title_label)
        
        # Área de mensajes
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 8px;
                background-color: white;
                font-family: "Sans Serif";
                font-size: 12px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Indicador de "escribiendo..."
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

        # Layout para botones de acción
        self.action_buttons_layout = QHBoxLayout()
        layout.addLayout(self.action_buttons_layout)
        
        # Área de entrada de texto
        self.message_input = QTextEdit()
        self.message_input.setFixedHeight(60)
        self.message_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
                background-color: white;
                font-family: "Sans Serif";
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #007bff;
            }
        """)
        layout.addWidget(self.message_input)
        
        # Botón de enviar
        self.send_button = QPushButton("Enviar")
        self.send_button.setFixedHeight(30)
        self.send_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.send_button.setStyleSheet(self.button_style)
        layout.addWidget(self.send_button)
        
        # Label para mostrar el costo
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

        # Conectar señales
        self.send_button.clicked.connect(self.send_message)
        self.message_input.textChanged.connect(self.adjust_input_height)
        self.message_input.installEventFilter(self)
        
        # Estilo general del panel
        self.setStyleSheet("""
            ChatPanel {
                background-color: #f5f6fa;
                border-right: 1px solid #dcdde1;
            }
        """)

    def show_action_buttons(self, actions):
        """
        Muestra botones de acción en el panel.
        
        Args:
            actions: Lista de diccionarios con las acciones.
                    Cada diccionario debe tener:
                    - text: Texto del botón
                    - callback: Función a llamar cuando se presione
        """
        # Limpiar botones anteriores
        while self.action_buttons_layout.count():
            item = self.action_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Crear nuevos botones
        for action in actions:
            btn = QPushButton(action['text'])
            btn.setStyleSheet(self.button_style)
            btn.clicked.connect(action['callback'])
            self.action_buttons_layout.addWidget(btn)
            
    def clear_action_buttons(self):
        """Elimina todos los botones de acción."""
        while self.action_buttons_layout.count():
            item = self.action_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
    def eventFilter(self, obj, event):
        """Maneja eventos personalizados."""
        if obj == self.message_input and event.type() == QKeyEvent.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
        
    def send_message(self):
        """Envía el mensaje actual y limpia el campo de entrada."""
        message = self.message_input.toPlainText().strip()
        if message:
            self.append_message("Usuario", message)
            self.message_sent.emit(message)
            self.message_input.clear()
            
    def append_message(self, sender: str, message: str, is_error: bool = False):
        """
        Añade un mensaje al área de chat.
        
        Args:
            sender: Nombre del remitente ("Sistema", "Usuario", "LLM")
            message: Contenido del mensaje
            is_error: Si es True, el mensaje se muestra como error
        """
        # Preparar estilos CSS para cada tipo de mensaje
        styles = {
            "error": """
                background-color: #ffe6e6;
                color: #cc0000;
                border: 1px solid #ffcccc;
                border-radius: 3px;
                padding: 8px;
                margin: 5px 0;
            """,
            "Sistema": """
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 8px;
                margin: 5px 0;
            """,
            "Usuario": """
                background-color: #e6f3ff;
                color: #0056b3;
                border: 1px solid #cce5ff;
                border-radius: 3px;
                padding: 8px;
                margin: 5px 0;
                text-align: right;
            """,
            "LLM": """
                background-color: #f8f9fa;
                color: #333333;
                border: 1px solid #e9ecef;
                border-radius: 3px;
                padding: 8px;
                margin: 5px 0;
            """
        }
        
        # Seleccionar el estilo apropiado
        style = styles["error"] if is_error else styles.get(sender, styles["LLM"])
        
        # Formatear y añadir el mensaje
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)
        
        # Insertar un div con el estilo correspondiente
        self.chat_display.insertHtml(
            f'<div style="{style}">'
            f'<b>{sender}:</b><br>'
            f'{message.replace(chr(10), "<br>")}'
            '</div><br>'
        )
        
        # Asegurar que el último mensaje sea visible
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
        
    def set_typing_status(self, is_typing: bool):
        """
        Actualiza el indicador de 'escribiendo...'.
        
        Args:
            is_typing: True si el LLM está procesando, False en caso contrario
        """
        self.typing_label.setText(
            "El asistente está escribiendo..." if is_typing else ""
        )
        
    def adjust_input_height(self):
        """Ajusta la altura del campo de entrada según el contenido."""
        document_height = self.message_input.document().size().height()
        if document_height <= 60:  # Altura máxima permitida
            self.message_input.setFixedHeight(max(60, document_height + 10))
            
    def clear_chat(self):
        """Limpia el historial del chat."""
        self.chat_display.clear()
        self.message_input.clear()
        self.typing_label.clear()
        self.cost_label.setText("Costo de la interacción: $0.00")
        
    def update_cost(self, cost: float):
        """
        Actualiza el costo mostrado de la interacción.
        
        Args:
            cost: Costo en dólares de la interacción
        """
        self.cost_label.setText(f"Costo de la interacción: ${cost:.4f}") 