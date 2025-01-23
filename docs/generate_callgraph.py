from pycallgraph2 import PyCallGraph
from pycallgraph2.output import GraphvizOutput
from pycallgraph2.config import Config
from pycallgraph2.globbing_filter import GlobbingFilter
import os

def main():
    # Configurar el grafo
    config = Config()
    config.trace_filter = GlobbingFilter(
        exclude=[
            'pycallgraph.*',
            'PyQt5.*',
            '_*',
            'os.*',
            'sys.*'
        ]
    )
    
    # Crear ruta en el escritorio
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    output_path = os.path.join(desktop_path, 'call_graph.png')
    print(f"El archivo se guardará en: {output_path}")
    
    graphviz = GraphvizOutput(
        output_file=output_path,
        tool='C:\\Program Files\\Graphviz\\bin\\dot.exe'
    )
    
    with PyCallGraph(output=graphviz, config=config):
        print("Generando diagrama de llamadas...")
        # Importar los módulos principales del proyecto
        import main
        from ui import mainWindow, mainWindowController, chatPanel, configDialog
        from managers import (
            referenceFolderCreationManager,
            chatManager,
            fileManager,
            pathsManager,
            searchController
        )
        from utils import llm_manager
        
        # Esperar un momento para asegurar que se registren las importaciones
        import time
        time.sleep(1)
    
    print(f"Diagrama generado en: {output_path}")

if __name__ == '__main__':
    main() 