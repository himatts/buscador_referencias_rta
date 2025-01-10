# BUSCADOR_REFERENCIAS_RTA/utils/helpers.py

import os
import re
from difflib import SequenceMatcher
import unicodedata

# Lista de palabras de enlace comunes que se ignorarán en la búsqueda
STOPWORDS = {'de', 'la', 'el', 'y', 'en', 'a', 'por', 'para', 'con', 'sin', 'sobre'}

def extract_reference(text):
    # Extrae las primeras tres letras y los números siguientes, ignorando el resto del texto
    match = re.search(r'([A-Z]{3})\s*(\d{3,5})', text, re.IGNORECASE)
    if match:
        return f"{match.group(1).upper()} {match.group(2)}"
    return None


def normalize_text(text):
    """
    Normaliza el texto eliminando acentos, caracteres especiales y convirtiéndolo a minúsculas.
    
    Args:
        text (str): Texto a normalizar.
    
    Returns:
        str: Texto normalizado.
    """
    # Convertir a minúsculas primero
    text = text.lower()
    
    # Normalizar caracteres Unicode (eliminar acentos)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    
    # Reemplazar caracteres especiales con espacios
    text = re.sub(r'[+_\-.]', ' ', text)
    
    # Eliminar otros caracteres especiales
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Normalizar espacios múltiples
    text = ' '.join(text.split())
    
    return text.strip()
    
def get_significant_terms(query):
    """
    Obtiene los términos significativos de una consulta, ignorando las stopwords.
    Los términos se normalizan y se filtran para eliminar términos vacíos.
    
    Args:
        query (str): Consulta de búsqueda.
    
    Returns:
        list: Lista de términos significativos.
    """
    normalized_query = normalize_text(query)
    # Dividir por espacios y filtrar stopwords y términos vacíos
    terms = [term.strip() for term in normalized_query.split() if term.strip()]
    return [term for term in terms if term not in STOPWORDS and len(term) > 1]


def is_exact_match(search_reference, text):
    """
    Verifica si hay una coincidencia exacta entre la referencia de búsqueda y el texto.
    Ahora maneja tanto referencias como nombres de archivo.
    """
    # Primero intentamos extraer y comparar referencias
    extracted_search_ref = extract_reference(search_reference)
    extracted_text_ref = extract_reference(text)
    
    if extracted_search_ref and extracted_text_ref:
        # Si ambos textos contienen referencias, las comparamos
        normalized_search_ref = normalize_text(extracted_search_ref)
        normalized_text_ref = normalize_text(extracted_text_ref)
        if normalized_search_ref == normalized_text_ref:
            print(f"Coincidencia exacta de referencia encontrada: {normalized_search_ref} == {normalized_text_ref}")
            return True
    
    # Si no hay coincidencia por referencia o no son referencias,
    # comparamos los textos normalizados completos
    normalized_search = normalize_text(search_reference)
    normalized_text = normalize_text(text)
    
    # Verificar si el texto normalizado de búsqueda está contenido en el texto normalizado
    if normalized_search in normalized_text:
        print(f"Coincidencia exacta de texto encontrada: {normalized_search} en {normalized_text}")
        return True
    
    return False

def is_ficha_tecnica(search_reference, text):
    ref = extract_reference(search_reference)
    if not ref:
        return False
    ficha_tecnica_pattern = re.compile(r'ficha\s*t[eé]cnica', re.IGNORECASE)
    if ficha_tecnica_pattern.search(text):
        if ref in text:
            return True
        ref_parts = ref.split()
        for part in ref_parts:
            if part in text:
                return True
        return any(SequenceMatcher(None, part, text).ratio() > 0.8 for part in ref_parts)
    return False

def search_references(reference, results, selected_paths):
    normalized_selected_paths = [os.path.normpath(path).lower() for path in selected_paths]
    filtered_results = []
    for result in results:
        db_reference, file_name, path, last_updated = result
        print(f"Comparando base de datos referencia: {db_reference}, ruta: {path} con referencia buscada: {reference}")
        if any(os.path.normpath(path).lower().startswith(selected_path) for selected_path in normalized_selected_paths) and is_exact_match(reference, db_reference):
            filtered_results.append(result)
    return filtered_results