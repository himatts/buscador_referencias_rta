"""
Módulo para manejar las interacciones con el LLM a través de OpenRouter.ai
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
import openai

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMManager:
    """
    Gestor para interacciones con el LLM a través de OpenRouter.ai.
    Utiliza el modelo Llama 3.3 70B Instruct para procesar texto y tomar decisiones.
    """
    
    def __init__(self):
        """Inicializa el gestor de LLM cargando la API key desde .env"""
        load_dotenv()
        api_key = os.getenv('API_KEY_OPENROUTER')
        if not api_key:
            raise ValueError("No se encontró API_KEY_OPENROUTER en el archivo .env")
            
        # Configurar OpenAI para usar OpenRouter
        openai.api_base = "https://openrouter.ai/api/v1"
        openai.api_key = api_key
        
        self.model = "meta-llama/llama-3.3-70b-instruct"
        logger.info("LLMManager inicializado correctamente")
        
    def format_reference_name(self, 
                            code: str, 
                            number: str, 
                            description: str) -> str:
        """
        Formatea el nombre de una referencia usando el LLM.
        
        Args:
            code: Código de 3 letras (ej: 'CDB')
            number: Número consecutivo (ej: '9493')
            description: Descripción original del mueble

        Returns:
            str: Nombre formateado según las reglas establecidas
        """
        prompt = f"""Formatea este nombre de referencia siguiendo EXACTAMENTE estas reglas:

1. Formato final OBLIGATORIO: "CÓDIGO NÚMERO - NOMBRE (COLORES)"
   Ejemplo: "CDB 9493 - CLOSET BARILOCHE ECO 150 (DUNA-BLANCO + BLANCO MQZ)"

2. Reglas de formateo:
   - Mantener el nombre del mueble exactamente como está
   - Poner TODOS los colores/materiales entre paréntesis al final
   - Usar "+" con espacios alrededor para separar colores: "COLOR1 + COLOR2"
   - Mantener guiones en nombres compuestos: "DUNA-BLANCO"
   - Cambiar "MARQUEZ" o "MARQUÉZ" por "MQZ"
   - Eliminar dimensiones como "71,5X210X34 CM"
   - Eliminar "(1C)", "(2C)", etc.
   - Eliminar "_CAJA N/N"
   - Eliminar "HD", "IMAGEN", "DIMENSIONES"
   - Reemplazar "mas" por "+"

3. IMPORTANTE:
   - SIEMPRE usar paréntesis para los colores/materiales
   - NUNCA perder información de colores/materiales
   - SIEMPRE mantener el espacio entre código y número

Información a formatear:
Código: {code}
Número: {number}
Descripción: {description}

Devuelve SOLO el texto formateado, sin explicaciones."""

        try:
            logger.debug(f"Enviando prompt al LLM para formatear: {code} {number}")
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1  # Bajo para mantener consistencia
            )
            
            formatted_name = response.choices[0].message.content.strip()
            logger.info(f"Nombre formateado por LLM: {formatted_name}")
            return formatted_name
            
        except Exception as e:
            logger.error(f"Error al formatear con LLM: {str(e)}")
            raise ValueError(f"Error en el formateo LLM: {str(e)}")
            
    def suggest_file_selection(self, 
                             files: list, 
                             reference: str,
                             file_type: str) -> str:
        """
        Sugiere qué archivo seleccionar cuando hay múltiples opciones.
        
        Args:
            files: Lista de rutas de archivos
            reference: Referencia del mueble
            file_type: Tipo de archivo (PDF, Rhino, etc.)

        Returns:
            str: Ruta del archivo sugerido
        """
        files_info = "\n".join([f"- {f}" for f in files])
        
        prompt = f"""Como asistente experto en selección de archivos, necesito que analices estas rutas de archivos {file_type} para la referencia {reference}:

{files_info}

Por favor:
1. Analiza los nombres y rutas
2. Prioriza archivos que contengan 'instructivo' si es PDF
3. Prioriza versiones más recientes de Rhino (R5 > R4 > R6 > R7)
4. Considera la estructura de carpetas (ej: 'EDITABLE' es relevante)

Responde SOLAMENTE con la ruta completa del archivo que recomiendas usar."""

        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1
            )
            
            suggested_file = response.choices[0].message.content.strip()
            logger.info(f"Archivo sugerido por LLM: {suggested_file}")
            return suggested_file
            
        except Exception as e:
            logger.error(f"Error al sugerir archivo: {str(e)}")
            raise ValueError(f"Error en la sugerencia de archivo: {str(e)}") 