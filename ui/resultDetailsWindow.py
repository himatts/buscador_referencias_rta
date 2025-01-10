# BUSCADOR_REFERENCIAS_RTA/ui/resultDetailsWindow.py
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QHeaderView

class ResultDetailsWindow(QDialog):
    def __init__(self, results, parent=None):
        super(ResultDetailsWindow, self).__init__(parent)
        self.setWindowTitle("Detalles de Resultados")
        self.setGeometry(100, 100, 1080, 600)  # Incrementa el tamaño de la ventana

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["ID", "Referencia", "Carpetas", "Videos", "Imágenes", "Fichas Técnicas"])
        self.result_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.result_tree.header().setStretchLastSection(False)  # Permite la personalización de las columnas
        self.result_tree.setColumnWidth(1, 300)  # Incrementa el tamaño de la columna de referencia
        layout.addWidget(self.result_tree)

        self.load_results(results)

        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def load_results(self, results):
        print("\n=== DEBUGGING VENTANA DE DETALLES ===")
        print("Resultados recibidos en la ventana de detalles:")
        print(results)
        
        for idx, details in results.items():
            print(f"\nCargando ítem {idx}:")
            print(f"Detalles completos: {details}")
            
            ref_item = QTreeWidgetItem([
                str(idx + 1),
                details['reference'],
                str(details['folders']),
                str(details['videos']),
                str(details['images']),
                str(details['tech_sheets'])
            ])
            self.result_tree.addTopLevelItem(ref_item)

            for result in details['results']:
                path, file_type, search_reference = result
                result_item = QTreeWidgetItem([
                    '',  # Puedes dejarlo en blanco o asignar un identificador
                    '',  # Opcional
                    file_type,
                    os.path.basename(path),
                    path
                ])
                ref_item.addChild(result_item)
