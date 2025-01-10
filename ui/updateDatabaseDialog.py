from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QProgressBar, QTextEdit,
                             QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import time
import sys
import os
import subprocess
from pathlib import Path

class DatabaseUpdateThread(QThread):
    progress_updated = pyqtSignal(str)
    update_completed = pyqtSignal(bool, str)
    progress_value = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False
        self.process = None
        
    def run(self):
        try:
            current_dir = Path(__file__).parent.parent
            update_script = current_dir / 'update_db.py'
            print(f"[DEBUG] Iniciando actualización desde: {update_script}")
            print(f"[DEBUG] Python ejecutable: {sys.executable}")
            
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                [sys.executable, '-u', str(update_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            print(f"[DEBUG] Proceso iniciado con PID: {self.process.pid}")
            
            while True:
                if self._is_cancelled:
                    print("[DEBUG] Proceso cancelado por usuario")
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
                    print(f"[DEBUG] Salida del proceso: {line.strip()}")
                    if "[PROGRESS]" in line:
                        try:
                            progress = int(line.split("[PROGRESS]")[1])
                            self.progress_value.emit(progress)
                        except Exception as e:
                            print(f"[DEBUG] Error al procesar progreso: {str(e)}")
                    self.progress_updated.emit(line.strip())
                elif self.process.poll() is not None:
                    print(f"[DEBUG] Proceso terminado con código: {self.process.returncode}")
                    break
            
            if not self._is_cancelled:
                if self.process.returncode == 0:
                    self.update_completed.emit(True, "Base de datos actualizada exitosamente")
                else:
                    self.update_completed.emit(False, "Error durante la actualización")
                    
        except Exception as e:
            print(f"[DEBUG] Error durante la actualización: {str(e)}")
            self.update_completed.emit(False, f"Error durante la actualización: {str(e)}")
    
    def cancel(self):
        self._is_cancelled = True

class UpdateDatabaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Actualización de Base de Datos")
        self.setMinimumWidth(600)
        self.setup_ui()
        self.update_thread = None
        
    def setup_ui(self):
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
        if self.update_thread and self.update_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Confirmar Cierre',
                '¿Está seguro de que desea cancelar la actualización y cerrar la ventana?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.cancel_update()
                self.update_thread.wait()  # Espera a que el hilo termine
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

            
    def handle_close(self):
        self.close()
        
    def start_update(self):
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
        if self.update_thread:
            self.cancel_button.setEnabled(False)
            self.log_message("Solicitando cancelación...")
            self.update_thread.cancel()
            
    def update_completed(self, success, message):
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
        self.log_text.append(f"{time.strftime('%H:%M:%S')} - {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def verify_password(self, password):
        """Verifica si la contraseña ingresada es correcta."""
        correct_password = "RTA2024"
        return password == correct_password
