import sqlite3
from PIL import Image
import imagehash

class ImageSearchEngine:
    def __init__(self, db_path):
        self.db_path = db_path
        self.hashes_precargados = self.cargar_hashes_desde_db()

    def cargar_hashes_desde_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT ruta_imagen, hash_imagen FROM hashes')
        hashes = {fila[0]: fila[1] for fila in cursor.fetchall()}
        conn.close()
        return hashes

    def buscar_imagenes_similares(self, imagen_referencia_o_ruta, umbral_similitud):
        if isinstance(imagen_referencia_o_ruta, Image.Image):
            imagen_referencia = imagen_referencia_o_ruta
        else:
            imagen_referencia = self.cargar_normalizar_imagen(imagen_referencia_o_ruta)
        
        hash_referencia = self.generar_hash_imagen(imagen_referencia)
        return self.buscar_imagenes_similares_con_db(hash_referencia, umbral_similitud)

    def cargar_normalizar_imagen(self, ruta_imagen):
        # Si ruta_imagen es ya un objeto Image, simplemente devuélvelo
        if isinstance(ruta_imagen, Image.Image):
            return ruta_imagen
        else:
            # De lo contrario, carga la imagen desde la ruta proporcionada
            imagen = Image.open(ruta_imagen)
            imagen = imagen.convert("RGB")
            return imagen

    def generar_hash_imagen(self, imagen):
        return imagehash.average_hash(imagen)

    def buscar_imagenes_similares_con_db(self, hash_referencia, umbral_similitud):
        imagenes_similares = []
        for ruta_imagen, hash_almacenado in self.hashes_precargados.items():
            hash_imagen = imagehash.hex_to_hash(hash_almacenado)
            diferencia_hash = hash_referencia - hash_imagen
            if diferencia_hash < umbral_similitud:
                imagenes_similares.append((ruta_imagen, diferencia_hash))
        return imagenes_similares