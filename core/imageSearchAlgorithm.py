"""
Módulo que implementa el algoritmo de búsqueda de imágenes similares utilizando hashing perceptual.

Este módulo proporciona la funcionalidad para buscar imágenes similares en una base de datos
utilizando técnicas de hashing perceptual. El algoritmo compara las imágenes basándose en sus
características visuales generales en lugar de una comparación pixel por pixel.
"""

import sqlite3
from PIL import Image
import imagehash

class ImageSearchEngine:
    """
    Motor de búsqueda de imágenes que utiliza hashing perceptual para encontrar imágenes similares.
    
    Esta clase implementa un sistema de búsqueda de imágenes basado en la similitud visual,
    utilizando hashes perceptuales para comparar imágenes de manera eficiente.
    
    Attributes:
        db_path (str): Ruta al archivo de base de datos SQLite que almacena los hashes de las imágenes.
        hashes_precargados (dict): Diccionario que mantiene en memoria los hashes de las imágenes.
    """

    def __init__(self, db_path):
        """
        Inicializa el motor de búsqueda de imágenes.
        
        Args:
            db_path (str): Ruta al archivo de base de datos SQLite.
        """
        self.db_path = db_path
        self.hashes_precargados = self.cargar_hashes_desde_db()

    def cargar_hashes_desde_db(self):
        """
        Carga los hashes de imágenes desde la base de datos.
        
        Returns:
            dict: Diccionario con las rutas de las imágenes como claves y sus hashes como valores.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT ruta_imagen, hash_imagen FROM hashes')
        hashes = {fila[0]: fila[1] for fila in cursor.fetchall()}
        conn.close()
        return hashes

    def buscar_imagenes_similares(self, imagen_referencia_o_ruta, umbral_similitud):
        """
        Busca imágenes similares a una imagen de referencia.
        
        Args:
            imagen_referencia_o_ruta: Puede ser un objeto Image de PIL o una ruta a la imagen.
            umbral_similitud (int): Umbral máximo de diferencia permitido entre hashes.
        
        Returns:
            list: Lista de tuplas (ruta_imagen, diferencia_hash) de las imágenes similares encontradas.
        """
        if isinstance(imagen_referencia_o_ruta, Image.Image):
            imagen_referencia = imagen_referencia_o_ruta
        else:
            imagen_referencia = self.cargar_normalizar_imagen(imagen_referencia_o_ruta)
        
        hash_referencia = self.generar_hash_imagen(imagen_referencia)
        return self.buscar_imagenes_similares_con_db(hash_referencia, umbral_similitud)

    def cargar_normalizar_imagen(self, ruta_imagen):
        """
        Carga y normaliza una imagen para su procesamiento.
        
        Args:
            ruta_imagen: Ruta a la imagen o objeto Image de PIL.
        
        Returns:
            Image: Objeto Image de PIL normalizado en formato RGB.
        """
        if isinstance(ruta_imagen, Image.Image):
            return ruta_imagen
        else:
            imagen = Image.open(ruta_imagen)
            imagen = imagen.convert("RGB")
            return imagen

    def generar_hash_imagen(self, imagen):
        """
        Genera un hash perceptual para una imagen.
        
        Args:
            imagen (Image): Objeto Image de PIL a procesar.
        
        Returns:
            ImageHash: Hash perceptual de la imagen.
        """
        return imagehash.average_hash(imagen)

    def buscar_imagenes_similares_con_db(self, hash_referencia, umbral_similitud):
        """
        Busca imágenes similares comparando hashes en la base de datos.
        
        Args:
            hash_referencia (ImageHash): Hash de la imagen de referencia.
            umbral_similitud (int): Umbral máximo de diferencia permitido entre hashes.
        
        Returns:
            list: Lista de tuplas (ruta_imagen, diferencia_hash) de las imágenes similares encontradas.
        """
        imagenes_similares = []
        for ruta_imagen, hash_almacenado in self.hashes_precargados.items():
            hash_imagen = imagehash.hex_to_hash(hash_almacenado)
            diferencia_hash = hash_referencia - hash_imagen
            if diferencia_hash < umbral_similitud:
                imagenes_similares.append((ruta_imagen, diferencia_hash))
        return imagenes_similares