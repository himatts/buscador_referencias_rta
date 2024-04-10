"""
Nombre del Archivo: helpers.py
"""
import re

def extract_reference(text):
    # Ajustada para manejar caracteres especiales y estructuras variadas
    match = re.search(r'([A-Z]{2,3})\s*\(?(\d{4,5})\)?\s*[-+]?[^\d]*([A-Z]*\s*\d*)?', text, re.IGNORECASE)
    if match:
        # Devuelve la referencia normalizada, incluyendo caracteres especiales
        return f"{match.group(1).upper()} {int(match.group(2))} - {match.group(3).strip()}" if match.group(3) else f"{match.group(1).upper()} {int(match.group(2))}"
    return None

def is_exact_match(search_reference, text):
    # Extrae las referencias completas de ambos textos
    extracted_search_ref = extract_reference(search_reference)
    extracted_text_ref = extract_reference(text)
    
    # Primero, verifica coincidencia exacta entre las referencias extraídas
    if extracted_search_ref == extracted_text_ref:
        return True
    
    # Si no hay coincidencia exacta, verifica si la referencia buscada está contenida en el texto extraído
    if extracted_search_ref and extracted_text_ref:
        # Convierte las referencias en patrones regex escapando caracteres especiales
        search_ref_pattern = re.escape(extracted_search_ref)
        text_ref_pattern = re.escape(extracted_text_ref)
        
        # Verifica si uno contiene al otro en cualquier dirección
        if re.search(search_ref_pattern, extracted_text_ref) or re.search(text_ref_pattern, extracted_search_ref):
            return True
    
    # Adicionalmente, verifica si la referencia buscada está contenida en el texto original
    # para manejar casos donde la extracción de la referencia no refleja la inclusión
    if extracted_search_ref and re.search(re.escape(extracted_search_ref), text, re.IGNORECASE):
        return True
    
    return False

def split_alphanumeric(text):
    # Divide un texto en componentes alfanuméricos
    return re.findall(r'\d+|\D+', text)

def has_matching_numbers(search_parts, text_parts):
    # Comprueba si hay coincidencias numéricas en los componentes
    return any(part for part in search_parts if part.isdigit() and part in text_parts)

def is_ficha_tecnica(search_reference, text):
    """
    Comprueba si el texto dado corresponde a una ficha técnica relacionada con la referencia buscada.
    
    Args:
        search_reference (str): La referencia buscada.
        text (str): El nombre del archivo a comprobar.
        
    Returns:
        bool: True si el archivo corresponde a una ficha técnica de la referencia, False en caso contrario.
    """
    # Esta función asume que extract_reference ya normaliza el formato de la referencia extraída
    ref = extract_reference(search_reference)
    if not ref:
        return False

    # Comprobar si el texto contiene términos relacionados con "Ficha Técnica"
    ficha_tecnica_pattern = re.compile(r'ficha\s*t[eé]cnica', re.IGNORECASE)
    if ficha_tecnica_pattern.search(text) and ref in text:
        return True

    return False