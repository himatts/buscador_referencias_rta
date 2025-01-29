"""
Nombre del Archivo: webScrapingThread.py
Descripción: Hilo que maneja la ejecución asíncrona del web scraping.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2024
Versión: 1.0
"""

from PyQt5.QtCore import QThread, pyqtSignal
import logging
from typing import List, Dict, Optional
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_scraping.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WebScrapingThread(QThread):
    """
    Hilo que maneja la ejecución asíncrona del web scraping.
    """
    
    # Señales
    progress = pyqtSignal(str)  # Para mensajes de progreso
    error = pyqtSignal(str)     # Para mensajes de error
    finished = pyqtSignal()     # Cuando termina el proceso

    def __init__(self, manager, references: List[str], target_folders: Optional[Dict[str, str]] = None):
        """
        Inicializa el hilo de web scraping.
        
        Args:
            manager: Instancia de WebScrapingManager
            references: Lista de referencias a procesar
            target_folders: Diccionario opcional que mapea referencias a sus carpetas destino
        """
        super().__init__()
        self.manager = manager
        self.references = references
        self.target_folders = target_folders or {}
        self._is_running = True

    def run(self):
        """Ejecuta el proceso de web scraping."""
        try:
            # Inicializar el driver
            self.progress.emit("Iniciando navegador Chrome...")
            if not self.manager.initialize_driver():
                self.error.emit("Error al inicializar el navegador Chrome")
                return

            # Login
            self.progress.emit("Iniciando sesión en la página web...")
            if not self.manager.login():
                self.error.emit("Error al iniciar sesión")
                return

            # Navegar al histórico
            self.progress.emit("Navegando a la sección de histórico...")
            if not self.manager.navigate_to_historico():
                self.error.emit("Error al navegar a la sección de histórico")
                return

            # Procesar cada referencia
            total_refs = len(self.references)
            for i, ref in enumerate(self.references, 1):
                if not self._is_running:
                    self.progress.emit("Proceso cancelado por el usuario")
                    break

                self.progress.emit(f"Procesando referencia {i}/{total_refs}: {ref}")
                
                # Buscar la referencia
                if self.manager.search_reference(ref):
                    self.progress.emit(f"Búsqueda exitosa para referencia: {ref}")
                    
                    # Obtener la carpeta destino para esta referencia
                    target_folder = self.target_folders.get(ref)
                    if not target_folder:
                        self.error.emit(f"No se encontró la carpeta destino para: {ref}")
                        continue
                        
                    # Procesar la hoja de diseño y extraer datos
                    if self.manager.process_design_sheet(ref, target_folder):
                        self.progress.emit(f"Datos extraídos exitosamente para: {ref}")
                    else:
                        self.error.emit(f"Error al procesar la hoja de diseño para: {ref}")
                else:
                    self.error.emit(f"No se encontraron resultados para: {ref}")

            self.progress.emit("Proceso completado")

        except Exception as e:
            logger.error(f"Error en el hilo de web scraping: {str(e)}")
            self.error.emit(f"Error inesperado: {str(e)}")

        finally:
            self.manager.stop()
            self.finished.emit()

    def stop(self):
        """Detiene la ejecución del hilo."""
        self._is_running = False
        self.manager.stop() 