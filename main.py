import sys
from PyQt5.QtWidgets import QApplication
from ui.mainWindow import App
from ui.mainWindow import SplashScreen

def main():
    """Función principal que inicia la aplicación."""
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()

    main_window = App()
    main_window.show()

    splash.finish(main_window)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()