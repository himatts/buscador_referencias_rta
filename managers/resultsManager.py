"""
Nombre del Archivo: resultsManager.py
Descripción: Manejador de la tabla de resultados.
             Gestiona todas las operaciones relacionadas con la visualización y
             actualización de los resultados de búsqueda.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

import os
import re
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import QTreeWidgetItem, QHeaderView, QApplication

class ResultsManager:
    """
    Manejador de la tabla de resultados.
    
    Esta clase se encarga de gestionar la visualización y actualización de los
    resultados en la tabla QTreeWidget, incluyendo el formato, coloreado y
    organización de los resultados.
    
    Attributes:
        main_controller: Referencia al controlador principal
    """
    
    def __init__(self, main_controller):
        """
        Inicializa el manejador de resultados.
        
        Args:
            main_controller: Referencia al controlador principal
        """
        self.main_controller = main_controller
        
    def add_result_item(self, idx, path, file_type, search_reference):
        """
        Añade un ítem a la tabla de resultados.
        
        Args:
            idx (int): Índice del resultado
            path (str): Ruta del archivo o carpeta
            file_type (str): Tipo de archivo
            search_reference (str): Referencia de búsqueda
        """
        main_window = self.main_controller.main_window
        
        if main_window.search_type == 'Referencia':
            self._add_reference_result(idx, path, file_type, search_reference)
        else:  # Nombre de Archivo
            self._add_filename_result(idx, path, file_type)
            
        self.recolor_results()
        self._update_ref_info_label()
        
    def _add_reference_result(self, idx, path, file_type, search_reference):
        """
        Añade un resultado de búsqueda por referencia.
        
        Args:
            idx (int): Índice del resultado
            path (str): Ruta del archivo o carpeta
            file_type (str): Tipo de archivo
            search_reference (str): Referencia de búsqueda
        """
        main_window = self.main_controller.main_window
        results = main_window.results
        
        # Verificar duplicados
        for i in range(results.topLevelItemCount()):
            existing_item = results.topLevelItem(i)
            if (existing_item.text(6) == path and 
                existing_item.text(2) + existing_item.text(3) == search_reference):
                return
                
        folder_name = os.path.split(path)[1]
        match = re.match(r"([A-Z]+)\s*(\d+)", search_reference)
        component1 = match.group(1) if match else ''
        component2 = match.group(2) if match else ''
        
        item = QTreeWidgetItem([
            '',  # Seleccionar
            str(idx + 1),  # ID
            component1,  # REF
            component2,  # ###
            file_type,  # TIPO
            folder_name,  # NOMBRE DE ARCHIVO
            path  # RUTA
        ])
        
        self._configure_item(item, path)
        self._insert_item_sorted(item, idx)
        
    def _add_filename_result(self, idx, path, file_type):
        """
        Añade un resultado de búsqueda por nombre de archivo.
        
        Args:
            idx (int): Índice del resultado
            path (str): Ruta del archivo o carpeta
            file_type (str): Tipo de archivo
        """
        main_window = self.main_controller.main_window
        results = main_window.results
        
        # Verificar duplicados
        for i in range(results.topLevelItemCount()):
            existing_item = results.topLevelItem(i)
            if existing_item.text(4) == path:
                return
                
        folder_name = os.path.split(path)[1]
        
        item = QTreeWidgetItem([
            '',  # Seleccionar
            str(idx + 1),  # ID
            file_type,  # TIPO
            folder_name,  # NOMBRE DE ARCHIVO
            path  # RUTA
        ])
        
        self._configure_item(item, path)
        self._insert_item_sorted(item, idx)
        
    def _configure_item(self, item, path):
        """
        Configura las propiedades de un ítem de resultado.
        
        Args:
            item (QTreeWidgetItem): Ítem a configurar
            path (str): Ruta del archivo o carpeta
        """
        # Alineación
        for i in range(item.columnCount()):
            if i in [5, 6]:  # Nombre de archivo y ruta
                item.setTextAlignment(i, Qt.AlignLeft)
            else:
                item.setTextAlignment(i, Qt.AlignCenter)
                
        # Configuración adicional
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Unchecked)
        item.setData(6 if self.main_controller.main_window.search_type == 'Referencia' else 4,
                    Qt.UserRole, path)
                    
    def _insert_item_sorted(self, item, idx):
        """
        Inserta un ítem en la posición correcta según su índice.
        
        Args:
            item (QTreeWidgetItem): Ítem a insertar
            idx (int): Índice del ítem
        """
        results = self.main_controller.main_window.results
        inserted = False
        
        for i in range(results.topLevelItemCount()):
            existing_item = results.topLevelItem(i)
            existing_idx = int(existing_item.text(1)) - 1
            if idx < existing_idx:
                results.insertTopLevelItem(i, item)
                inserted = True
                break
                
        if not inserted:
            results.addTopLevelItem(item)
            
    def _update_ref_info_label(self):
        """Actualiza la etiqueta de información de referencias."""
        main_window = self.main_controller.main_window
        found_refs = set()
        
        for i in range(main_window.results.topLevelItemCount()):
            item = main_window.results.topLevelItem(i)
            if main_window.search_type == 'Referencia':
                ref = f"{item.text(2)}{item.text(3)}"
            else:
                ref = item.text(3)
            found_refs.add(ref)
            
        found_count = len(found_refs)
        searched_count = len(self.main_controller.searched_refs)
        
        if self.main_controller.is_searching:
            main_window.ref_info_label.setText(
                f"Búsqueda en Progreso:\n"
                f"se ha encontrado información para {found_count} de {searched_count} "
                f"referencias buscadas"
            )
            
    def recolor_results(self):
        """Recolorea las filas de la tabla de resultados para mejorar la legibilidad."""
        main_window = self.main_controller.main_window
        last_ref = None
        color = QColor("lightgray")
        
        for i in range(main_window.results.topLevelItemCount()):
            item = main_window.results.topLevelItem(i)
            if main_window.search_type == 'Referencia':
                current_ref = item.text(3)  # Columna '###'
            else:
                current_ref = item.text(2)  # Columna 'TIPO'
                
            if last_ref != current_ref:
                color = QColor("white") if color == QColor("lightgray") else QColor("lightgray")
                
            for j in range(item.columnCount()):
                item.setBackground(j, QBrush(color))
                
            last_ref = current_ref
            
    def update_results_headers(self):
        """Actualiza los encabezados de la tabla de resultados según el tipo de búsqueda."""
        main_window = self.main_controller.main_window
        results = main_window.results
        
        results.clear()
        results.setHeaderHidden(False)
        
        if main_window.search_type == 'Referencia':
            results.setColumnCount(7)
            results.setHeaderLabels(['', 'ID', 'REF', '###', 'TIPO', 'NOMBRE DE ARCHIVO', 'RUTA'])
            results.setColumnWidth(0, 40)
            results.setColumnWidth(1, 15)
            results.setColumnWidth(2, 50)
            results.setColumnWidth(3, 50)
            results.setColumnWidth(4, 90)
            results.setColumnWidth(5, 250)
            results.setColumnWidth(6, 200)
            results.header().setSectionResizeMode(6, QHeaderView.Stretch)
        else:  # Nombre de Archivo o Imagen
            results.setColumnCount(5)
            results.setHeaderLabels(['', 'ID', 'TIPO', 'NOMBRE DE ARCHIVO', 'RUTA'])
            results.setColumnWidth(0, 40)
            results.setColumnWidth(1, 15)
            results.setColumnWidth(2, 90)
            results.setColumnWidth(3, 250)
            results.setColumnWidth(4, 200)
            results.header().setSectionResizeMode(4, QHeaderView.Stretch)
            
    def process_final_results(self, results_dict):
        """
        Procesa los resultados finales de la búsqueda.
        
        Args:
            results_dict (dict): Diccionario con los resultados de la búsqueda
        """
        main_window = self.main_controller.main_window
        
        # Acumular resultados por referencia
        accumulated_results = {}
        for idx, results in results_dict.items():
            reference = results[0][2] if results else ""
            if reference not in accumulated_results:
                accumulated_results[reference] = []
            accumulated_results[reference].extend(results)
            
        # Procesar resultados acumulados
        found_refs = set()
        detailed_results = {}
        
        for idx, (reference, all_results) in enumerate(accumulated_results.items()):
            folders = sum(1 for result in all_results if result[1] == "Carpeta")
            videos = sum(1 for result in all_results if result[1] == "Video")
            images = sum(1 for result in all_results if result[1] == "Imagen")
            tech_sheets = sum(1 for result in all_results if result[1] == "Ficha Técnica")
            
            detailed_results[idx] = {
                "reference": reference,
                "folders": folders,
                "videos": videos,
                "images": images,
                "tech_sheets": tech_sheets,
                "results": all_results
            }
            
            for _, _, search_reference in all_results:
                found_refs.add(search_reference)
                
        # Actualizar interfaz
        self.main_controller.found_refs = found_refs
        self._highlight_entry_rows(found_refs)
        
        found_count = len(found_refs)
        searched_count = len(self.main_controller.searched_refs)
        main_window.ref_info_label.setText(
            f"Búsqueda Finalizada:\n"
            f"se ha encontrado información para {found_count} de {searched_count} "
            f"referencias buscadas"
        )
        
        main_window.results.resizeColumnToContents(6)
        self.recolor_results()
        main_window.detailed_results = detailed_results
        
    def _highlight_entry_rows(self, found_references):
        """
        Resalta las filas de la tabla de entrada según las referencias encontradas.
        
        Args:
            found_references (set): Conjunto de referencias encontradas
        """
        main_window = self.main_controller.main_window
        for row in range(main_window.entry.rowCount()):
            item = main_window.entry.item(row, 0)
            if item:
                text_line = item.text().strip()
                found = any(ref in text_line for ref in found_references)
                item.setBackground(
                    QColor(255, 255, 255) if found else QColor(255, 200, 200)
                )
                
    def on_select_all_state_changed(self, state):
        """
        Maneja el cambio de estado del checkbox 'Seleccionar todos'.
        
        Args:
            state: Estado del checkbox (Qt.Checked, Qt.Unchecked, Qt.PartiallyChecked)
        """
        main_window = self.main_controller.main_window
        results = main_window.results
        
        for i in range(results.topLevelItemCount()):
            item = results.topLevelItem(i)
            item.setCheckState(0, state)
            
        self.update_selected_count()
        
    def update_selected_count(self):
        """Actualiza el contador de elementos seleccionados."""
        main_window = self.main_controller.main_window
        results = main_window.results
        count = 0
        
        for i in range(results.topLevelItemCount()):
            item = results.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                count += 1
                
        main_window.selectedCountLabel.setText(f"Elementos seleccionados: {count}")
        
    def copy_found(self):
        """Copia al portapapeles las referencias encontradas."""
        main_window = self.main_controller.main_window
        found_refs = []
        
        for i in range(main_window.results.topLevelItemCount()):
            item = main_window.results.topLevelItem(i)
            if main_window.search_type == 'Referencia':
                ref = f"{item.text(2)}{item.text(3)}"
            else:
                ref = item.text(3)
            found_refs.append(ref)
            
        if found_refs:
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(found_refs))
            main_window.status_label.setText("Referencias encontradas copiadas al portapapeles")
        else:
            main_window.status_label.setText("No hay referencias para copiar")
            
    def copy_not_found(self):
        """Copia al portapapeles las referencias no encontradas."""
        main_window = self.main_controller.main_window
        found_refs = set()
        
        for i in range(main_window.results.topLevelItemCount()):
            item = main_window.results.topLevelItem(i)
            if main_window.search_type == 'Referencia':
                ref = f"{item.text(2)}{item.text(3)}"
            else:
                ref = item.text(3)
            found_refs.add(ref)
            
        not_found_refs = self.main_controller.searched_refs - found_refs
        
        if not_found_refs:
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(sorted(not_found_refs)))
            main_window.status_label.setText("Referencias no encontradas copiadas al portapapeles")
        else:
            main_window.status_label.setText("No hay referencias no encontradas para copiar")
