# BUSCADOR_REFERENCIAS_RTA/utils/database.py

import datetime
import sqlite3
from contextlib import closing
import os
from utils.helpers import normalize_text, get_significant_terms

DB_NAME = r"\\192.168.200.250\rtadiseño\SOLUCIONES IA\BASES DE DATOS\buscador_de_referencias\folder_references.db"

def initialize_db():
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
    """Inserta una nueva carpeta en la base de datos."""
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
    """Busca carpetas por nombre."""
    normalized_selected_paths = [os.path.normpath(path).lower() for path in selected_paths]
    
    # Normalizar el texto de búsqueda
    normalized_folder_name = normalize_text(folder_name)
    query_terms = get_significant_terms(normalized_folder_name)
    
    if not query_terms:
        return []
    
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with closing(conn.cursor()) as cur:
            # Construir la cláusula WHERE con múltiples LIKE
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
    """Retorna una conexión a la base de datos con un timeout configurado."""
    return sqlite3.connect(DB_NAME, timeout=20)

def normalize_existing_folders():
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