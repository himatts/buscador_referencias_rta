"""
Módulo para manejar la validación y formateo de colores en referencias RTA.
"""

import json
import os
from typing import List, Set

class ColorManager:
    """
    Clase para manejar la validación y formateo de colores en referencias RTA.
    Implementa reglas específicas para el formateo de colores y mantiene una lista
    de colores válidos.
    """
    
    def __init__(self):
        """Inicializa el gestor de colores cargando la lista de colores válidos."""
        self.colores_validos: Set[str] = set()
        self._cargar_colores()
        
    def _cargar_colores(self) -> None:
        """Carga la lista de colores válidos desde el archivo JSON."""
        try:
            # Ruta al archivo de colores relativa a este módulo
            ruta_colores = os.path.join(os.path.dirname(__file__), 'colores.json')
            
            with open(ruta_colores, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.colores_validos = set(data.get('materiales_unicos', []))
                
        except Exception as e:
            raise ValueError(f"Error al cargar colores: {str(e)}")
    
    def formatear_color(self, color: str) -> str:
        """
        Formatea un color según las reglas establecidas.
        
        Args:
            color: Color a formatear
            
        Returns:
            str: Color formateado según las reglas
        """
        if not color:
            return ""
            
        # Convertir a mayúsculas y eliminar espacios extras
        color = color.upper().strip()
        
        # Reglas especiales de formateo
        if color in ['BLANCO NEVADO', 'BLANCO MARQUEZ', 'BLANCO KRONOSPAN']:
            return 'BLANCO'
            
        # Excepción para BLANCO HIGH GLOSS
        if color == 'BLANCO HIGH GLOSS':
            return color
            
        # Validar que sea un color válido
        if color not in self.colores_validos:
            raise ValueError(f"Color no válido: {color}")
            
        return color
        
    def es_color_valido(self, color: str) -> bool:
        """
        Verifica si un color es válido.
        
        Args:
            color: Color a verificar
            
        Returns:
            bool: True si el color es válido, False en caso contrario
        """
        try:
            color_formateado = self.formatear_color(color)
            return color_formateado in self.colores_validos
        except:
            return False
            
    def obtener_colores_validos(self) -> List[str]:
        """
        Obtiene la lista de colores válidos.
        
        Returns:
            List[str]: Lista de colores válidos
        """
        return sorted(list(self.colores_validos)) 