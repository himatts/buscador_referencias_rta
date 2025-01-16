"""
Nombre del Archivo: config.py
Descripción: Maneja la configuración global de la aplicación.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

import os
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Config:
    """
    Clase para manejar la configuración global de la aplicación.
    Incluye manejo de credenciales y configuraciones generales.
    """
    
    # Constantes de configuración
    GOOGLE_SHEET_KEY = "1E-mHqi17tHtga1sTcPRlq6FxaXKe4Nr3Sn5ssPqx5EE"
    
    def __init__(self):
        """Inicializa la configuración."""
        self.config_dir = Path.home() / '.rta_buscador'
        self.config_file = self.config_dir / 'config.json'
        self.credentials_file = self.config_dir / 'google_credentials.json'
        
        # Valores por defecto
        self.default_config = {
            'desktop_folder_name': 'PEDIDOS MERCADEO'
        }
        
        # Asegurar que existe el directorio de configuración
        self._ensure_config_dir()
        
        # Cargar configuración
        self.config = self._load_config()
    
    def _ensure_config_dir(self):
        """Asegura que existe el directorio de configuración."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directorio de configuración asegurado: {self.config_dir}")
        except Exception as e:
            logger.error(f"Error creando directorio de configuración: {e}")
            raise
    
    def _load_config(self):
        """
        Carga la configuración del archivo JSON.
        Si no existe, crea uno con valores por defecto.
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("Configuración cargada exitosamente")
                return {**self.default_config, **config}
            else:
                self._save_config(self.default_config)
                logger.info("Creada configuración por defecto")
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return self.default_config.copy()
    
    def _save_config(self, config):
        """Guarda la configuración en el archivo JSON."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            logger.info("Configuración guardada exitosamente")
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            raise
    
    def save_google_credentials(self, credentials_json):
        """
        Guarda las credenciales de Google en un archivo seguro.
        
        Args:
            credentials_json: Contenido JSON de las credenciales
        """
        try:
            with open(self.credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials_json, f, indent=4)
            logger.info("Credenciales de Google guardadas exitosamente")
        except Exception as e:
            logger.error(f"Error guardando credenciales: {e}")
            raise
    
    def get_google_credentials_path(self):
        """
        Retorna la ruta al archivo de credenciales de Google.
        
        Returns:
            Path al archivo de credenciales o None si no existe
        """
        return str(self.credentials_file) if self.credentials_file.exists() else None
    
    def get_google_sheet_key(self):
        """
        Retorna la clave de la hoja de Google Sheets.
        
        Returns:
            str: Clave de la hoja
        """
        return self.GOOGLE_SHEET_KEY
    
    def set_google_sheet_key(self, key):
        """Este método ya no se utiliza ya que el ID de la hoja es constante."""
        logger.warning("Intento de modificar el ID de la hoja de cálculo, que ahora es constante.")
    
    def get_desktop_folder_name(self):
        """
        Retorna el nombre de la carpeta a crear en el escritorio.
        
        Returns:
            str: Nombre de la carpeta
        """
        return self.config.get('desktop_folder_name', 'PEDIDOS MERCADEO')
    
    def set_desktop_folder_name(self, name):
        """
        Establece el nombre de la carpeta a crear en el escritorio.
        
        Args:
            name: Nuevo nombre de la carpeta
        """
        self.config['desktop_folder_name'] = name
        self._save_config(self.config)
        logger.info("Nombre de carpeta de escritorio actualizado") 