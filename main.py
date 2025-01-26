# BUSCADOR_REFERENCIAS_RTA/main.py
import os
import sys
from PyQt5.QtWidgets import QApplication

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def reset_log_file():
    """Limpia el archivo de logs al inicio del programa."""
    log_file = 'llm_prompts.log'
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('')  # Sobrescribe el archivo con contenido vacío
    except Exception as e:
        print(f"Error al limpiar archivo de logs: {e}")

# Agregar los directorios al path
if getattr(sys, 'frozen', False):
    # Estamos ejecutando en modo PyInstaller
    sys.path.append(resource_path('ui'))
    sys.path.append(resource_path('utils'))
    sys.path.append(resource_path('core'))
else:
    # Estamos en modo desarrollo
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ui.mainWindow import App
from ui.mainWindow import SplashScreen
from utils.database import initialize_db

def main():
    """Función principal que inicia la aplicación."""
    reset_log_file()  # Limpiar logs al inicio
    initialize_db()
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()

    main_window = App()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()