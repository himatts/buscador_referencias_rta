"""
Nombre del Archivo: updateDatabaseDialog.py
Descripción: Este módulo implementa una interfaz gráfica para la actualización
             de la base de datos del buscador de referencias. Permite ejecutar
             y monitorear el proceso de actualización de manera segura y controlada.

Características Principales:
- Interfaz de autenticación con contraseña
- Monitoreo en tiempo real del proceso de actualización
- Visualización detallada del progreso mediante logs
- Capacidad de cancelar la actualización en cualquier momento
- Manejo seguro de procesos en segundo plano

Clases Principales:
- DatabaseUpdateThread: Manejo asíncrono del proceso de actualización
- UpdateDatabaseDialog: Ventana de diálogo para la actualización

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QProgressBar, QTextEdit,
    QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import time
import sys
import os
import subprocess
from pathlib import Path

def resource_path(relative_path):
    """
    Obtiene la ruta absoluta al recurso, funciona tanto en desarrollo como en PyInstaller.

    Esta función maneja las diferencias de rutas entre el entorno de desarrollo
    y la aplicación empaquetada con PyInstaller.

    Args:
        relative_path (str): Ruta relativa al recurso deseado.

    Returns:
        str: Ruta absoluta al recurso.
    """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)

class DatabaseUpdateThread(QThread):
    """
    Hilo dedicado para ejecutar la actualización de la base de datos.

    Esta clase maneja la ejecución del script de actualización en segundo plano,
    permitiendo que la interfaz de usuario permanezca responsiva durante el proceso.

    Signals:
        progress_updated (str): Emitida cuando hay un nuevo mensaje de progreso.
        update_completed (bool, str): Emitida cuando la actualización finaliza.
        progress_value (int): Emitida cuando cambia el valor del progreso (0-100).

    Attributes:
        _is_cancelled (bool): Indica si el proceso ha sido cancelado.
        process (subprocess.Popen): Proceso del script de actualización.
    """
    
    progress_updated = pyqtSignal(str)
    update_completed = pyqtSignal(bool, str)
    progress_value = pyqtSignal(int)
    
    def __init__(self, parent=None):
        """
        Inicializa el hilo de actualización.

        Args:
            parent (QObject, optional): Objeto padre del hilo.
        """
        super().__init__(parent)
        self._is_cancelled = False
        self.process = None
        
    def run(self):
        """
        Ejecuta el proceso de actualización de la base de datos.

        Este método:
        1. Localiza y ejecuta el script de actualización
        2. Monitorea la salida del proceso
        3. Emite señales de progreso y finalización
        4. Maneja la cancelación del proceso
        """
        try:
            update_script = resource_path('update_db.py')
            print(f"[DEBUG] Iniciando actualización desde: {update_script}")
            
            if getattr(sys, 'frozen', False):
                python_exe = sys.executable
                cmd = [python_exe, '-c', f"import runpy; runpy.run_path('{update_script}')"]
            else:
                python_exe = sys.executable
                cmd = [python_exe, '-u', str(update_script)]
                
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                universal_newlines=True,
                env=env,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            while True:
                if self._is_cancelled:
                    if self.process:
                        self.progress_updated.emit("Cancelando actualización...")
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                        self.update_completed.emit(False, "Actualización cancelada por el usuario")
                    break
                    
                line = self.process.stdout.readline()
                if line:
                    if "[PROGRESS]" in line:
                        try:
                            progress = int(line.split("[PROGRESS]")[1])
                            self.progress_value.emit(progress)
                        except Exception as e:
                            print(f"[DEBUG] Error al procesar progreso: {str(e)}")
                    self.progress_updated.emit(line.strip())
                elif self.process.poll() is not None:
                    break
            
            if not self._is_cancelled:
                if self.process.returncode == 0:
                    self.update_completed.emit(True, "Base de datos actualizada exitosamente")
                else:
                    self.update_completed.emit(False, "Error durante la actualización")
                    
        except Exception as e:
            self.update_completed.emit(False, f"Error durante la actualización: {str(e)}")
    
    def cancel(self):
        """
        Marca el proceso para cancelación.
        
        La cancelación efectiva ocurrirá en el siguiente ciclo del bucle principal.
        """
        self._is_cancelled = True

class UpdateDatabaseDialog(QDialog):
    """
    Ventana de diálogo para la actualización de la base de datos.

    Esta clase proporciona una interfaz gráfica que permite:
    - Autenticar al usuario mediante contraseña
    - Iniciar y monitorear el proceso de actualización
    - Visualizar el progreso y los logs en tiempo real
    - Cancelar la actualización si es necesario

    Attributes:
        update_thread (DatabaseUpdateThread): Hilo de actualización.
        password_input (QLineEdit): Campo para ingresar la contraseña.
        progress_bar (QProgressBar): Barra de progreso de la actualización.
        log_text (QTextEdit): Área de texto para mostrar los logs.
        start_button (QPushButton): Botón para iniciar la actualización.
        cancel_button (QPushButton): Botón para cancelar la actualización.
        close_button (QPushButton): Botón para cerrar la ventana.
    """

    def __init__(self, parent=None):
        """
        Inicializa la ventana de diálogo.

        Args:
            parent (QWidget, optional): Widget padre de esta ventana.
        """
        super().__init__(parent)
        self.setWindowTitle("Actualización de Base de Datos")
        self.setMinimumWidth(600)
        self.setup_ui()
        self.update_thread = None
        
    def setup_ui(self):
        """
        Configura la interfaz gráfica de la ventana.

        Crea y organiza todos los widgets necesarios:
        - Etiqueta informativa
        - Campo de contraseña
        - Barra de progreso
        - Área de logs
        - Botones de control
        """
        layout = QVBoxLayout()
        
        info_label = QLabel("Este proceso actualizará la base de datos con los cambios en las carpetas monitoreadas.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        password_layout = QHBoxLayout()
        password_label = QLabel("Contraseña:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setAlignment(Qt.AlignCenter) 
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFormat("Progreso de Actualización: %p%")
        layout.addWidget(self.progress_bar)
        
        log_label = QLabel("Detalles del proceso:")
        layout.addWidget(log_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(300)
        layout.addWidget(self.log_text)
        
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Iniciar Actualización")
        self.cancel_button = QPushButton("Cancelar")
        self.close_button = QPushButton("Cerrar")
        
        self.cancel_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.start_button.clicked.connect(self.start_update)
        self.cancel_button.clicked.connect(self.cancel_update)
        self.close_button.clicked.connect(self.handle_close)
        
    def closeEvent(self, event):
        """
        Maneja el evento de cierre de la ventana.

        Si hay una actualización en curso, solicita confirmación antes de cerrar.

        Args:
            event (QCloseEvent): Evento de cierre de la ventana.
        """
        if self.update_thread and self.update_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Confirmar Cierre',
                '¿Está seguro de que desea cancelar la actualización y cerrar la ventana?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.cancel_update()
                self.update_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
            
    def handle_close(self):
        """Cierra la ventana de diálogo."""
        self.close()
        
    def start_update(self):
        """
        Inicia el proceso de actualización.

        Verifica la contraseña y, si es correcta:
        1. Deshabilita los controles apropiados
        2. Crea y configura el hilo de actualización
        3. Inicia el proceso de actualización
        """
        password = self.password_input.text()
        if not self.verify_password(password):
            QMessageBox.warning(self, "Error", "Contraseña incorrecta")
            return
            
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.password_input.setEnabled(False)
        self.start_button.setEnabled(False)
        self.close_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        
        self.update_thread = DatabaseUpdateThread(self)
        self.update_thread.progress_updated.connect(self.log_message)
        self.update_thread.progress_value.connect(self.progress_bar.setValue)
        self.update_thread.update_completed.connect(self.update_completed)
        self.update_thread.start()
        
        self.log_message("Iniciando actualización de la base de datos...")
            
    def cancel_update(self):
        """
        Cancela el proceso de actualización en curso.
        
        Deshabilita el botón de cancelación y solicita la cancelación
        al hilo de actualización.
        """
        if self.update_thread:
            self.cancel_button.setEnabled(False)
            self.log_message("Solicitando cancelación...")
            self.update_thread.cancel()
            
    def update_completed(self, success, message):
        """
        Maneja la finalización del proceso de actualización.

        Args:
            success (bool): True si la actualización fue exitosa, False en caso contrario.
            message (str): Mensaje describiendo el resultado de la actualización.
        """
        self.log_message(message)
        self.progress_bar.setValue(100 if success else 0)
        
        self.password_input.setEnabled(True)
        self.start_button.setEnabled(True)
        self.close_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "Éxito", message)
        else:
            QMessageBox.warning(self, "Error", message)
            
    def log_message(self, message):
        """
        Añade un mensaje al área de logs.

        Args:
            message (str): Mensaje a añadir al log.
        """
        self.log_text.append(f"{time.strftime('%H:%M:%S')} - {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def verify_password(self, password):
        """
        Verifica si la contraseña ingresada es correcta.

        Args:
            password (str): Contraseña ingresada por el usuario.

        Returns:
            bool: True si la contraseña es correcta, False en caso contrario.
        """
        correct_password = "RTA2024"
        return password == correct_password
