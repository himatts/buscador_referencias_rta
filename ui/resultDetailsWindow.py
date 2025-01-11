"""
Nombre del Archivo: resultDetailsWindow.py
Descripción: Este módulo implementa una ventana de diálogo para mostrar detalles
             detallados de los resultados de búsqueda. Presenta una vista jerárquica
             de los resultados encontrados, organizados por referencia y tipo de archivo.

Características Principales:
- Vista en árbol para mostrar resultados jerárquicamente
- Columnas organizadas para diferentes tipos de archivos
- Conteo de archivos por categoría
- Vista detallada de rutas y nombres de archivo

Clases Principales:
- ResultDetailsWindow: Ventana de diálogo para mostrar detalles de resultados

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

import os
from PyQt5.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QLabel, 
    QPushButton, 
    QTreeWidget, 
    QTreeWidgetItem, 
    QHeaderView
)

class ResultDetailsWindow(QDialog):
    """
    Ventana de diálogo que muestra detalles detallados de los resultados de búsqueda.

    Esta clase proporciona una interfaz para visualizar los resultados de búsqueda
    de manera organizada y detallada. Los resultados se muestran en una estructura
    de árbol donde cada referencia es un nodo principal que contiene sus archivos
    asociados como nodos hijos.

    Attributes:
        result_tree (QTreeWidget): Widget de árbol para mostrar los resultados.
        
    La ventana muestra las siguientes columnas:
    - ID: Número identificador del resultado
    - Referencia: Código de referencia del producto
    - Carpetas: Cantidad de carpetas encontradas
    - Videos: Cantidad de archivos de video
    - Imágenes: Cantidad de archivos de imagen
    - Fichas Técnicas: Cantidad de fichas técnicas
    """

    def __init__(self, results, parent=None):
        """
        Inicializa la ventana de detalles de resultados.

        Args:
            results (dict): Diccionario con los resultados de la búsqueda.
                          Debe contener la siguiente estructura:
                          {
                              'reference': str,
                              'folders': int,
                              'videos': int,
                              'images': int,
                              'tech_sheets': int,
                              'results': list
                          }
            parent (QWidget, optional): Widget padre de esta ventana.
        """
        super(ResultDetailsWindow, self).__init__(parent)
        self.setWindowTitle("Detalles de Resultados")
        self.setGeometry(100, 100, 1080, 600)

        # Configuración del layout principal
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Configuración del árbol de resultados
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels([
            "ID", 
            "Referencia", 
            "Carpetas", 
            "Videos", 
            "Imágenes", 
            "Fichas Técnicas"
        ])
        
        # Configuración de las columnas
        self.result_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.result_tree.header().setStretchLastSection(False)
        self.result_tree.setColumnWidth(1, 300)
        layout.addWidget(self.result_tree)

        # Carga de resultados
        self.load_results(results)

        # Botón de cierre
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def load_results(self, results):
        """
        Carga y muestra los resultados en el árbol.

        Este método procesa el diccionario de resultados y crea la estructura
        jerárquica en el árbol de resultados. Para cada referencia, crea un
        nodo principal con sus estadísticas y nodos hijos para cada archivo
        encontrado.

        Args:
            results (dict): Diccionario con los resultados de la búsqueda.
                          Debe contener información sobre referencias y sus
                          archivos asociados.
        """
        print("\n=== DEBUGGING VENTANA DE DETALLES ===")
        print("Resultados recibidos en la ventana de detalles:")
        print(results)
        
        for idx, details in results.items():
            # Crear ítem principal para la referencia
            ref_item = QTreeWidgetItem([
                str(idx + 1),                    # ID
                details['reference'],            # Referencia
                str(details['folders']),         # Carpetas
                str(details['videos']),          # Videos
                str(details['images']),          # Imágenes
                str(details['tech_sheets'])      # Fichas Técnicas
            ])
            self.result_tree.addTopLevelItem(ref_item)

            # Añadir subitems para cada resultado
            for result in details['results']:
                path, file_type, search_reference = result
                result_item = QTreeWidgetItem([
                    '',                          # ID (vacío para subitems)
                    '',                          # Referencia (vacío para subitems)
                    file_type,                   # Tipo de archivo
                    os.path.basename(path),      # Nombre del archivo
                    path                         # Ruta completa
                ])
                ref_item.addChild(result_item)
