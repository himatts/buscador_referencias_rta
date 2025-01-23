"""
Módulo de funciones auxiliares para el buscador de referencias.

Este módulo proporciona un conjunto de funciones utilitarias para el procesamiento
de texto, normalización, extracción de referencias y comparación de cadenas.
Las funciones aquí implementadas son utilizadas por los módulos principales
para realizar búsquedas precisas y manejar diferentes formatos de texto.
"""

import os
import re
from difflib import SequenceMatcher
import unicodedata

# Lista de palabras de enlace comunes que se ignorarán en la búsqueda
STOPWORDS = {'de', 'la', 'el', 'y', 'en', 'a', 'por', 'para', 'con', 'sin', 'sobre'}

def extract_reference(text):
    """
    Extrae el código de referencia de un texto dado.
    
    Busca un patrón que consiste en tres letras seguidas de 3-5 números,
    ignorando espacios y el resto del texto.
    
    Args:
        text (str): Texto del cual extraer la referencia.
    
    Returns:
        str or None: Referencia extraída en formato 'XXX YYYYY' o None si no se encuentra.
    
    Example:
        >>> extract_reference("BLZ 6472 - Ejemplo")
        'BLZ 6472'
    """
    match = re.search(r'([A-Z]{3})\s*(\d{3,5})', text, re.IGNORECASE) # Busca el patrón en el texto
    if match:
        return f"{match.group(1).upper()} {match.group(2)}" # Devuelve la referencia en formato 'XXX YYYYY'
    return None

def normalize_text(text):
    """
    Normaliza el texto eliminando acentos, caracteres especiales y convirtiéndolo a minúsculas.
    
    El proceso de normalización incluye:
    1. Conversión a minúsculas
    2. Eliminación de acentos y diacríticos
    3. Reemplazo de caracteres especiales por espacios
    4. Eliminación de otros caracteres no alfanuméricos
    5. Normalización de espacios múltiples
    
    Args:
        text (str): Texto a normalizar.
    
    Returns:
        str: Texto normalizado.
    
    Example:
        >>> normalize_text("BLZ-6472_Ejemplo")
        'blz 6472 ejemplo'
    """
    text = text.lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    text = re.sub(r'[+_\-.]', ' ', text)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = ' '.join(text.split())
    return text.strip()
    
def get_significant_terms(query):
    """
    Obtiene los términos significativos de una consulta, ignorando las stopwords.
    
    Los términos se normalizan y se filtran para eliminar términos vacíos y palabras comunes
    que no aportan significado a la búsqueda.
    
    Args:
        query (str): Consulta de búsqueda.
    
    Returns:
        list: Lista de términos significativos normalizados.
    
    Example:
        >>> get_significant_terms("Mesa de Comedor")
        ['mesa', 'comedor']
    """
    normalized_query = normalize_text(query)
    terms = [term.strip() for term in normalized_query.split() if term.strip()]
    return [term for term in terms if term not in STOPWORDS and len(term) > 1]

def is_exact_match(search_reference, text):
    """
    Verifica si hay una coincidencia exacta entre la referencia de búsqueda y el texto.
    
    La función realiza dos tipos de comparación:
    1. Comparación de referencias extraídas (si existen)
    2. Comparación de textos normalizados completos
    
    Args:
        search_reference (str): Referencia o texto de búsqueda.
        text (str): Texto con el que comparar.
    
    Returns:
        bool: True si hay coincidencia exacta, False en caso contrario.
    
    Example:
        >>> is_exact_match("BLZ 6472", "BLZ-6472-ejemplo")
        True
    """
    extracted_search_ref = extract_reference(search_reference)
    extracted_text_ref = extract_reference(text)
    
    if extracted_search_ref and extracted_text_ref:
        normalized_search_ref = normalize_text(extracted_search_ref)
        normalized_text_ref = normalize_text(extracted_text_ref)
        if normalized_search_ref == normalized_text_ref:
            print(f"Coincidencia exacta de referencia encontrada: {normalized_search_ref} == {normalized_text_ref}")
            return True
    
    normalized_search = normalize_text(search_reference)
    normalized_text = normalize_text(text)
    
    if normalized_search in normalized_text:
        print(f"Coincidencia exacta de texto encontrada: {normalized_search} en {normalized_text}")
        return True
    
    return False

def is_ficha_tecnica(search_reference, text):
    """
    Verifica si un texto corresponde a una ficha técnica de una referencia específica.
    
    La función busca coincidencias entre la referencia y el texto, considerando:
    1. La presencia de "ficha técnica" en el texto
    2. La coincidencia de la referencia completa o sus partes
    3. Similitud aproximada usando SequenceMatcher
    
    Args:
        search_reference (str): Referencia a buscar.
        text (str): Texto a analizar.
    
    Returns:
        bool: True si el texto corresponde a una ficha técnica de la referencia, False en caso contrario.
    """
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
    """
    Busca referencias en los resultados que coincidan con las rutas seleccionadas.
    
    Args:
        reference (str): Referencia a buscar.
        results (list): Lista de resultados de la base de datos.
        selected_paths (list): Lista de rutas seleccionadas para la búsqueda.
    
    Returns:
        list: Lista filtrada de resultados que coinciden con la referencia y las rutas.
    """
    normalized_selected_paths = [os.path.normpath(path).lower() for path in selected_paths]
    filtered_results = []
    for result in results:
        db_reference, file_name, path, last_updated = result
        print(f"Comparando base de datos referencia: {db_reference}, ruta: {path} con referencia buscada: {reference}")
        if any(os.path.normpath(path).lower().startswith(selected_path) for selected_path in normalized_selected_paths) and is_exact_match(reference, db_reference):
            filtered_results.append(result)
    return filtered_results