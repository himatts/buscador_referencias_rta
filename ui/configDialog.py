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
    QPushButton, QFileDialog, QMessageBox, QGroupBox
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
        self.initUI()
        
    def initUI(self):
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
        
        # 3. Botones de acción
        button_layout = QHBoxLayout()
        save_button = QPushButton("Guardar")
        save_button.clicked.connect(self.save_config)
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
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
    
    def save_config(self):
        """Guarda la configuración."""
        try:
            # Validar y guardar nombre de carpeta
            folder_name = self.folder_name_input.text().strip()
            if folder_name:
                self.config.set_desktop_folder_name(folder_name)
            
            QMessageBox.information(
                self,
                "Éxito",
                "Configuración guardada correctamente."
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al guardar la configuración:\n{str(e)}"
            ) 