"""
Nombre del Archivo: configDialog.py
Descripción: Diálogo para configurar credenciales y hoja de Google Sheets.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from utils.config import Config

class ConfigDialog(QDialog):
    """
    Diálogo para configurar las credenciales de Google Sheets y otras opciones.
    """
    
    def __init__(self, parent=None):
        """Inicializa el diálogo de configuración."""
        super().__init__(parent)
        self.config = Config()
        self.init_ui()
        
    def init_ui(self):
        """Configura la interfaz del diálogo."""
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # 1. Grupo de Credenciales de Google
        credentials_group = QGroupBox("Credenciales de Google")
        credentials_layout = QVBoxLayout()
        
        # Botón para seleccionar archivo de credenciales
        cred_button_layout = QHBoxLayout()
        self.credentials_label = QLabel("No hay credenciales configuradas")
        if self.config.get_google_credentials_path():
            self.credentials_label.setText("Credenciales configuradas ✓")
        
        self.select_credentials_button = QPushButton("Seleccionar archivo...")
        self.select_credentials_button.clicked.connect(self.select_credentials_file)
        
        cred_button_layout.addWidget(self.credentials_label)
        cred_button_layout.addWidget(self.select_credentials_button)
        credentials_layout.addLayout(cred_button_layout)
        
        # Información sobre la hoja de cálculo
        sheet_info = QLabel(f"Hoja de cálculo: {self.config.GOOGLE_SHEET_KEY}")
        sheet_info.setWordWrap(True)
        credentials_layout.addWidget(sheet_info)
        
        credentials_group.setLayout(credentials_layout)
        layout.addWidget(credentials_group)
        
        # 2. Grupo de Configuración General
        general_group = QGroupBox("Configuración General")
        general_layout = QVBoxLayout()
        
        # Nombre de la carpeta en el escritorio
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Nombre de carpeta en escritorio:"))
        self.folder_name_input = QLineEdit()
        self.folder_name_input.setText(self.config.get_desktop_folder_name())
        folder_layout.addWidget(self.folder_name_input)
        general_layout.addLayout(folder_layout)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # 3. Grupo de credenciales web
        web_group = QGroupBox("Credenciales Web")
        web_layout = QVBoxLayout()
        
        # Campo para email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setText(self.config.get_web_email())
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        web_layout.addLayout(email_layout)
        
        # Campo para contraseña
        password_layout = QHBoxLayout()
        password_label = QLabel("Contraseña:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText(self.config.get_web_password())
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        web_layout.addLayout(password_layout)
        
        web_group.setLayout(web_layout)
        layout.addWidget(web_group)
        
        # 4. Botones de acción
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def select_credentials_file(self):
        """Maneja la selección del archivo de credenciales."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de credenciales",
            "",
            "Archivos JSON (*.json)"
        )
        
        if file_path:
            try:
                # Leer y validar el archivo JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    credentials = json.load(f)
                
                # Verificar que tenga los campos necesarios
                required_fields = [
                    'type',
                    'project_id',
                    'private_key_id',
                    'private_key',
                    'client_email'
                ]
                
                if all(field in credentials for field in required_fields):
                    # Guardar credenciales
                    self.config.save_google_credentials(credentials)
                    self.credentials_label.setText("Credenciales configuradas ✓")
                    QMessageBox.information(
                        self,
                        "Éxito",
                        "Credenciales guardadas correctamente."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "El archivo no parece ser un archivo válido de credenciales de Google."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error al procesar el archivo de credenciales:\n{str(e)}"
                )
    
    def accept(self):
        """Guarda la configuración y cierra el diálogo."""
        # Guardar nombre de carpeta de escritorio
        desktop_folder_name = self.folder_name_input.text().strip()
        if desktop_folder_name:
            self.config.set_desktop_folder_name(desktop_folder_name)

        # Guardar credenciales web
        email = self.email_input.text().strip()
        password = self.password_input.text()
        if email and password:
            self.config.set_web_credentials(email, password)

        super().accept() 