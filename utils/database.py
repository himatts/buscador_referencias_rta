"""
Módulo de gestión de base de datos para el buscador de referencias.

Este módulo proporciona la interfaz para interactuar con la base de datos SQLite
que almacena información sobre las carpetas y referencias del sistema. Implementa
funcionalidades para la creación, actualización y consulta de registros, así como
la normalización de datos para optimizar las búsquedas.

La base de datos utiliza dos tablas principales:
1. folder_references: Almacena información sobre las carpetas y sus referencias
2. folder_changes: Registra el historial de cambios en las carpetas

Attributes:
    DB_NAME (str): Ruta absoluta al archivo de base de datos SQLite.
"""

import datetime
from datetime import datetime
import sqlite3
from contextlib import closing
import os
from utils.helpers import normalize_text, get_significant_terms

DB_NAME = r"\\192.168.200.250\rtadiseño\SOLUCIONES IA\BASES DE DATOS\buscador_de_referencias\folder_references.db"

def initialize_db():
    """
    Inicializa la estructura de la base de datos.
    
    Crea las tablas necesarias si no existen y establece los índices
    para optimizar las consultas. Las tablas creadas son:
    
    1. folder_references:
       - id: Identificador único
       - folder_name: Nombre normalizado de la carpeta
       - path: Ruta única de la carpeta
       - hash: Hash para verificación de cambios
       - created_at: Fecha de creación
       - last_updated: Última actualización
       - is_deleted: Indicador de eliminación
       - parent_path: Ruta del directorio padre
       - total_items: Número total de elementos
       
    2. folder_changes:
       - id: Identificador único
       - folder_id: Referencia a folder_references
       - change_type: Tipo de cambio
       - old_path: Ruta anterior
       - new_path: Nueva ruta
       - changed_at: Fecha del cambio
    """
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with closing(conn.cursor()) as cur:
            # Tabla principal de carpetas
            cur.execute('''
            CREATE TABLE IF NOT EXISTS folder_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT NOT NULL,
                path TEXT UNIQUE NOT NULL,
                hash TEXT,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                is_deleted INTEGER DEFAULT 0,
                parent_path TEXT,
                total_items INTEGER
            )
            ''')
            
            # Tabla para el historial de cambios
            cur.execute('''
            CREATE TABLE IF NOT EXISTS folder_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER,
                change_type TEXT NOT NULL,
                old_path TEXT,
                new_path TEXT,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (folder_id) REFERENCES folder_references (id)
            )
            ''')
            
            # Índices para mejorar el rendimiento
            cur.execute('CREATE INDEX IF NOT EXISTS idx_folder_path ON folder_references(path)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_folder_hash ON folder_references(hash)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_parent_path ON folder_references(parent_path)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_folder_name ON folder_references(folder_name)')
            
            conn.commit()

def insert_folder(folder_name: str, path: str, hash_value: str, parent_path: str, total_items: int):
    """
    Inserta una nueva carpeta en la base de datos.
    
    Args:
        folder_name (str): Nombre de la carpeta a insertar.
        path (str): Ruta completa de la carpeta.
        hash_value (str): Hash calculado para la carpeta.
        parent_path (str): Ruta del directorio padre.
        total_items (int): Número total de elementos en la carpeta.
    
    Note:
        El nombre de la carpeta se normaliza antes de la inserción para
        facilitar las búsquedas posteriores.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    normalized_folder_name = normalize_text(folder_name)
    
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute('''
                INSERT INTO folder_references 
                (folder_name, path, hash, created_at, last_updated, parent_path, total_items)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (normalized_folder_name, path, hash_value, now, now, parent_path, total_items))
            
            folder_id = cur.lastrowid
            cur.execute('''
                INSERT INTO folder_changes (folder_id, change_type, changed_at)
                VALUES (?, 'CREATED', ?)
            ''', (folder_id, now))
            
            conn.commit()

def get_folder(folder_name: str, selected_paths: list, limit: int = 100):
    """
    Busca carpetas por nombre en las rutas seleccionadas.
    
    La búsqueda se realiza utilizando términos normalizados y significativos
    extraídos del nombre de la carpeta. Se aplican filtros adicionales basados
    en las rutas seleccionadas.
    
    Args:
        folder_name (str): Nombre o referencia a buscar.
        selected_paths (list): Lista de rutas donde realizar la búsqueda.
        limit (int, optional): Límite de resultados a retornar. Por defecto 100.
    
    Returns:
        list: Lista de diccionarios con la información de las carpetas encontradas.
              Cada diccionario contiene: folder_name, path, hash, last_updated, total_items.
    
    Example:
        >>> get_folder("BLZ 6472", ["/ruta/principal"], 10)
        [{'folder_name': 'blz 6472', 'path': '/ruta/principal/BLZ 6472', ...}]
    """
    normalized_selected_paths = [os.path.normpath(path).lower() for path in selected_paths]
    normalized_folder_name = normalize_text(folder_name)
    query_terms = get_significant_terms(normalized_folder_name)
    
    if not query_terms:
        return []
    
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with closing(conn.cursor()) as cur:
            like_clauses = " AND ".join(["folder_name LIKE ?"] * len(query_terms))
            search_values = [f"%{term}%" for term in query_terms]
            search_values.append(limit)
            
            query = f'''
                SELECT folder_name, path, hash, last_updated, total_items 
                FROM folder_references 
                WHERE {like_clauses}
                AND is_deleted = 0
                LIMIT ?
            '''
            
            cur.execute(query, tuple(search_values))
            results = cur.fetchall()
            
            filtered_results = []
            for folder_name, path, hash_value, last_updated, total_items in results:
                normalized_path = os.path.normpath(path).lower()
                if any(normalized_path.startswith(selected_path) for selected_path in normalized_selected_paths):
                    filtered_results.append({
                        'folder_name': folder_name,
                        'path': path,
                        'hash': hash_value,
                        'last_updated': last_updated,
                        'total_items': total_items
                    })
            
            return filtered_results
            
def get_db_connection():
    """
    Obtiene una conexión a la base de datos con timeout configurado.
    
    Returns:
        sqlite3.Connection: Objeto de conexión a la base de datos.
    
    Note:
        La conexión se configura con un timeout de 20 segundos para
        manejar situaciones de concurrencia.
    """
    return sqlite3.connect(DB_NAME, timeout=20)

def normalize_existing_folders():
    """
    Normaliza los nombres de todas las carpetas existentes en la base de datos.
    
    Esta función se utiliza para actualizar registros antiguos y asegurar
    que todos los nombres de carpetas estén normalizados según los criterios
    actuales de búsqueda.
    
    Note:
        Esta función debe ejecutarse solo una vez cuando se necesite actualizar
        el formato de los datos existentes.
    """
    conn = get_db_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute('SELECT id, folder_name FROM folder_references')
            rows = cur.fetchall()
            for row in rows:
                id_, folder_name = row
                normalized_folder_name = normalize_text(folder_name)
                cur.execute('UPDATE folder_references SET folder_name = ? WHERE id = ?', 
                            (normalized_folder_name, id_))
        conn.commit()
    except Exception as e:
        print(f"Error al normalizar carpetas: {e}")
        conn.rollback()
    finally:
        conn.close()

# Llama a esta función una vez para normalizar todos los datos existentes
# normalize_existing_folders()