"""
Módulo para manejar las interacciones con el LLM a través de OpenRouter.ai
"""

import os
import logging
from typing import Optional, List, Tuple, Dict
from dotenv import load_dotenv
import openai
import json
from time import sleep
import requests
import tiktoken

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMError(Exception):
    """Clase base para errores del LLM."""
    pass

class APIError(LLMError):
    """Error en la comunicación con la API."""
    def __init__(self, operation: str, status_code: int, message: str):
        self.operation = operation
        self.status_code = status_code
        super().__init__(f"Error en API ({status_code}) durante '{operation}': {message}")

class PromptError(LLMError):
    """Error en la construcción o validación del prompt."""
    pass

class ResponseError(LLMError):
    """Error en el procesamiento de la respuesta del LLM."""
    pass

class LLMManager:
    """
    Gestor para interacciones con el LLM a través de OpenRouter.ai.
    Utiliza el modelo Llama 3.3 70B Instruct para procesar texto y tomar decisiones.
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # segundos
    
    # Costos por token para el modelo (en dólares)
    MODEL_COSTS = {
        "meta-llama/llama-3.3-70b-instruct": {
            "input": 0.00012,    # $0.12 por 1M tokens de entrada
            "output": 0.0003     # $0.30 por 1M tokens de salida
        }
    }
    
    def __init__(self):
        """Inicializa el gestor de LLM cargando la API key desde .env"""
        load_dotenv()
        self.api_key = os.getenv('API_KEY_OPENROUTER')
        if not self.api_key:
            raise ValueError("No se encontró API_KEY_OPENROUTER en el archivo .env")
            
        # Configurar OpenAI para usar OpenRouter
        openai.api_base = "https://openrouter.ai/api/v1"
        openai.api_key = self.api_key
        
        self.model = "meta-llama/llama-3.3-70b-instruct"
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Usamos este tokenizer como aproximación
        self.session_cost = 0.0
        logger.info("LLMManager inicializado correctamente")
        
    def get_api_usage(self) -> Dict:
        """
        Obtiene información sobre el uso y límites de la API.
        
        Returns:
            Dict: Información de uso y límites de la API
        """
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error al obtener información de uso de API: {str(e)}")
            return {}
            
    def calculate_cost(self, input_text: str, output_text: str) -> float:
        """
        Calcula el costo de una interacción basado en los tokens de entrada y salida.
        
        Args:
            input_text: Texto de entrada enviado al modelo
            output_text: Texto de respuesta recibido del modelo
            
        Returns:
            float: Costo total de la interacción en dólares
        """
        try:
            # Contar tokens
            input_tokens = len(self.tokenizer.encode(input_text))
            output_tokens = len(self.tokenizer.encode(output_text))
            
            # Obtener costos del modelo actual
            model_costs = self.MODEL_COSTS.get(self.model, {
                "input": 0.0000015,
                "output": 0.0000020
            })
            
            # Calcular costo total
            input_cost = input_tokens * model_costs["input"]
            output_cost = output_tokens * model_costs["output"]
            total_cost = input_cost + output_cost
            
            # Actualizar costo de la sesión
            self.session_cost += total_cost
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Error al calcular costo: {str(e)}")
            return 0.0
            
    def get_session_cost(self) -> float:
        """
        Obtiene el costo total acumulado de la sesión.
        
        Returns:
            float: Costo total en dólares
        """
        return self.session_cost
        
    def _make_api_call(self, 
                      operation: str,
                      messages: List[Dict],
                      temperature: float = 0.7,
                      max_tokens: Optional[int] = None) -> Tuple[str, float]:
        """
        Realiza una llamada a la API con reintentos.
        
        Args:
            operation: Nombre de la operación
            messages: Lista de mensajes para el LLM
            temperature: Temperatura para la generación
            max_tokens: Límite de tokens (opcional)
            
        Returns:
            Tuple[str, float]: (Respuesta del LLM, costo de la interacción)
            
        Raises:
            APIError: Si hay un error en la comunicación
            ResponseError: Si hay un error en la respuesta
        """
        attempts = 0
        last_error = None
        
        while attempts < self.MAX_RETRIES:
            try:
                # Preparar parámetros
                params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature
                }
                if max_tokens:
                    params["max_tokens"] = max_tokens
                    
                # Realizar llamada
                response = openai.ChatCompletion.create(**params)
                
                # Validar respuesta
                if not response.choices:
                    raise ResponseError("No se recibió respuesta del LLM")
                    
                # Obtener texto de respuesta
                response_text = response.choices[0].message.content.strip()
                
                # Calcular costo
                input_text = " ".join([m["content"] for m in messages])
                cost = self.calculate_cost(input_text, response_text)
                
                return response_text, cost
                
            except openai.error.APIError as e:
                last_error = APIError(operation, getattr(e, 'status_code', 500), str(e))
            except openai.error.Timeout:
                last_error = APIError(operation, 408, "Timeout en la conexión")
            except openai.error.RateLimitError:
                last_error = APIError(operation, 429, "Límite de rate excedido")
            except Exception as e:
                last_error = ResponseError(f"Error inesperado: {str(e)}")
                
            attempts += 1
            if attempts < self.MAX_RETRIES:
                sleep(self.RETRY_DELAY * attempts)  # Backoff exponencial
                
        raise last_error
        
    def _validate_prompt(self, prompt: str) -> None:
        """
        Valida que un prompt sea adecuado.
        
        Args:
            prompt: Prompt a validar
            
        Raises:
            PromptError: Si el prompt no es válido
        """
        if not prompt or not isinstance(prompt, str):
            raise PromptError("El prompt no puede estar vacío")
            
        if len(prompt) > 4000:  # Límite arbitrario
            raise PromptError("El prompt es demasiado largo")
            
    def process_folder_creation_decision(self, 
                                      step: str,
                                      context: Dict,
                                      user_input: Optional[str] = None) -> Tuple[str, float]:
        """
        Procesa decisiones específicas para la creación de carpetas.
        
        Args:
            step: Paso actual del proceso
            context: Diccionario con información contextual
            user_input: Entrada opcional del usuario
            
        Returns:
            Tuple[str, float]: (Respuesta del LLM, costo de la interacción)
            
        Raises:
            PromptError: Si hay un error en la construcción del prompt
            APIError: Si hay un error en la comunicación con la API
            ResponseError: Si hay un error en la respuesta
        """
        try:
            messages = []
            
            # Prompt base del sistema
            system_prompt = (
                "Eres un asistente experto en el proceso de creación de carpetas para referencias de muebles RTA. "
                "Tu objetivo es tomar decisiones informadas basadas en el contexto proporcionado y guiar al usuario. "
                "Debes ser preciso, claro y siempre priorizar la integridad de los datos."
            )
            
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
            # Agregar contexto específico según el paso
            if step == "verificar_referencias":
                prompt = self._build_reference_verification_prompt(context)
            elif step == "confirmar_nombres":
                prompt = self._build_name_confirmation_prompt(context)
            elif step == "crear_carpetas":
                prompt = self._build_folder_creation_prompt(context)
            else:
                prompt = self._build_general_decision_prompt(step, context)
                
            self._validate_prompt(prompt)
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Si hay entrada del usuario, validarla y agregarla
            if user_input:
                self._validate_prompt(user_input)
                messages.append({
                    "role": "user",
                    "content": user_input
                })
            
            # Realizar llamada a la API
            return self._make_api_call(
                f"decision_{step}",
                messages,
                temperature=0.3
            )
            
        except Exception as e:
            if isinstance(e, (APIError, PromptError, ResponseError)):
                raise
            raise ResponseError(f"Error inesperado: {str(e)}")

    def process_message(self, message: str, conversation_history: List[Tuple[str, str]]) -> Tuple[str, float]:
        """
        Procesa un mensaje del usuario en el contexto de la conversación.
        
        Args:
            message: Mensaje del usuario
            conversation_history: Lista de tuplas (rol, mensaje) del historial
            
        Returns:
            Tuple[str, float]: (Respuesta del LLM, costo de la interacción)
        """
        try:
            # Construir el historial de mensajes para el LLM
            messages = []
            
            # Agregar el contexto inicial
            messages.append({
                "role": "system",
                "content": (
                    "Eres un asistente experto en el proceso de creación de carpetas "
                    "para referencias de muebles. Tu objetivo es guiar al usuario "
                    "a través del proceso, explicando cada paso y respondiendo sus dudas. "
                    "Debes ser claro, conciso y profesional en tus respuestas."
                )
            })
            
            # Agregar el historial de la conversación
            for role, content in conversation_history:
                messages.append({
                    "role": "user" if role == "usuario" else "assistant",
                    "content": content
                })
            
            # Agregar el mensaje actual
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Obtener respuesta del LLM y calcular costo
            return self._make_api_call(
                "process_message",
                messages,
                temperature=0.7  # Más creativo para el chat
            )
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje con LLM: {str(e)}")
            raise ValueError(f"Error en el procesamiento del mensaje: {str(e)}")
            
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
            str: Nombre formateado
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
            logger.info(f"Formateando referencia: {code} {number}")
            
            messages = [{
                "role": "user",
                "content": prompt
            }]
            
            response_text, cost = self._make_api_call(
                "format_reference",
                messages,
                temperature=0.1  # Bajo para mantener consistencia
            )
            
            # Validar el formato de la respuesta
            if not response_text or len(response_text.split()) < 3:
                raise ResponseError("La respuesta del LLM está vacía o es demasiado corta")
                
            # Verificar formato básico (CÓDIGO NÚMERO - RESTO)
            parts = response_text.split(' - ', 1)
            if len(parts) != 2 or ' ' not in parts[0]:
                raise ResponseError("El formato de la respuesta no es válido")
                
            logger.info(f"Referencia formateada exitosamente: {response_text}")
            return response_text  # Solo devolver el texto formateado, no la tupla con el costo
            
        except (APIError, ResponseError) as e:
            logger.error(f"Error específico al formatear con LLM: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al formatear con LLM: {str(e)}")
            raise ResponseError(f"Error al formatear referencia: {str(e)}")

    def suggest_file_selection(self, 
                             files: list, 
                             reference: str,
                             file_type: str) -> Tuple[str, float]:
        """
        Sugiere qué archivo seleccionar cuando hay múltiples opciones.
        
        Args:
            files: Lista de rutas de archivos
            reference: Referencia del mueble
            file_type: Tipo de archivo (PDF, Rhino, etc.)

        Returns:
            Tuple[str, float]: (Ruta del archivo sugerido, costo de la interacción)
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
            return self._make_api_call(
                "suggest_file",
                [{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1
            )
            
        except Exception as e:
            logger.error(f"Error al sugerir archivo: {str(e)}")
            raise ValueError(f"Error en la sugerencia de archivo: {str(e)}")

    def suggest_rhino_file(self, 
                         files: list,
                         reference: str,
                         source_folder: str) -> Tuple[str, float]:
        """
        Analiza y sugiere qué archivo Rhino seleccionar basado en criterios específicos.
        
        Args:
            files: Lista de rutas de archivos Rhino encontrados
            reference: Nombre de la referencia
            source_folder: Carpeta origen de la búsqueda

        Returns:
            Tuple[str, float]: (Ruta del archivo sugerido, costo de la interacción)
        """
        files_info = "\n".join([f"- {f}" for f in files])
        
        prompt = f"""Como experto en la selección de archivos Rhino para muebles RTA, necesito que analices estas rutas:

Referencia del mueble: {reference}
Carpeta origen: {source_folder}

Archivos Rhino encontrados:
{files_info}

Por favor, analiza siguiendo estos criterios en orden de prioridad:

1. VERSIÓN DE RHINO:
   - Prioridad: Rhino 5 > Rhino 4 > Rhino 6 > Rhino 7
   - Busca en el nombre: 'R5', 'Rhino5', 'R4', 'Rhino4', etc.

2. UBICACIÓN:
   - Prioriza archivos en carpetas que contengan 'EDITABLE' o 'EDITABLES'
   - Considera la profundidad en la estructura de carpetas (más cercano a la raíz es mejor)

3. NOMBRE DEL ARCHIVO:
   - Prioriza archivos que coincidan mejor con el nombre de la referencia
   - Busca palabras clave como 'FINAL', 'DEFINITIVO', 'APROBADO'
   - Evita archivos con 'OLD', 'BACKUP', 'ANTERIOR'

4. FECHA DE MODIFICACIÓN:
   - Si está en el nombre del archivo, considera versiones más recientes

Responde SOLAMENTE con la ruta completa del archivo que recomiendas usar.
Si hay empate en prioridades, selecciona el que esté en la carpeta más cercana a la raíz."""

        try:
            return self._make_api_call(
                "suggest_rhino_file",
                [{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1  # Bajo para mantener consistencia
            )
            
        except Exception as e:
            logger.error(f"Error al sugerir archivo Rhino: {str(e)}")
            raise ValueError(f"Error en la sugerencia de archivo Rhino: {str(e)}")

    def _build_reference_verification_prompt(self, context: Dict) -> str:
        """Construye el prompt para verificación de referencias."""
        found_refs = context.get('found_refs', [])
        not_found_refs = context.get('not_found_refs', [])
        
        prompt = (
            "Analiza los resultados de la verificación de referencias:\n\n"
            f"Referencias encontradas ({len(found_refs)}):\n"
        )
        
        for ref in found_refs:
            prompt += f"✓ {ref}\n"
            
        prompt += f"\nReferencias no encontradas ({len(not_found_refs)}):\n"
        for ref in not_found_refs:
            prompt += f"✗ {ref}\n"
            
        prompt += "\nConsidera:\n"
        prompt += "1. ¿Las referencias no encontradas son críticas?\n"
        prompt += "2. ¿Hay patrones en los errores?\n"
        prompt += "3. ¿Se debe continuar o solicitar correcciones?\n\n"
        prompt += "Proporciona una recomendación clara y las razones."
        
        return prompt
        
    def _build_name_confirmation_prompt(self, context: Dict) -> str:
        """Construye el prompt para confirmación de nombres formateados."""
        formatted_names = context.get('formatted_names', [])
        
        prompt = (
            "Revisa los nombres formateados para las referencias:\n\n"
        )
        
        for original, formatted in formatted_names:
            prompt += f"Original: {original}\n"
            prompt += f"Formateado: {formatted}\n\n"
            
        prompt += "Verifica:\n"
        prompt += "1. ¿Los nombres siguen el formato correcto?\n"
        prompt += "2. ¿Se mantiene toda la información importante?\n"
        prompt += "3. ¿Hay inconsistencias o errores?\n\n"
        prompt += "Proporciona una evaluación detallada y recomendación."
        
        return prompt
        
    def _build_folder_creation_prompt(self, context: Dict) -> str:
        """Construye el prompt para decisiones de creación de carpetas."""
        folders = context.get('folders', [])
        errors = context.get('errors', [])
        
        prompt = (
            "Analiza el resultado de la creación de carpetas:\n\n"
            f"Carpetas creadas ({len(folders)}):\n"
        )
        
        for folder in folders:
            prompt += f"✓ {folder}\n"
            
        if errors:
            prompt += f"\nErrores encontrados ({len(errors)}):\n"
            for error in errors:
                prompt += f"✗ {error}\n"
                
        prompt += "\nEvalúa:\n"
        prompt += "1. ¿Los errores son recuperables?\n"
        prompt += "2. ¿Se necesitan acciones correctivas?\n"
        prompt += "3. ¿El proceso fue exitoso en general?\n\n"
        prompt += "Proporciona un análisis y recomendaciones específicas."
        
        return prompt
        
    def _build_general_decision_prompt(self, step: str, context: Dict) -> str:
        """Construye un prompt general para otros tipos de decisiones."""
        prompt = (
            f"Analiza la siguiente situación en el paso '{step}':\n\n"
            "Contexto proporcionado:\n"
        )
        
        for key, value in context.items():
            prompt += f"{key}: {value}\n"
            
        prompt += "\nConsidera:\n"
        prompt += "1. ¿Qué riesgos hay en este paso?\n"
        prompt += "2. ¿Cuál es la mejor acción a seguir?\n"
        prompt += "3. ¿Se necesita información adicional?\n\n"
        prompt += "Proporciona una recomendación clara y justificada."
        
        return prompt 

    def determine_rhino_search_strategy(self, 
                                    source_folder: str,
                                    reference: str,
                                    available_paths: List[Dict[str, str]]) -> Tuple[str, float]:
        """
        Determina la estrategia de búsqueda para encontrar el archivo Rhino.
        
        Args:
            source_folder: Ruta origen desde donde se inicia la búsqueda
            reference: Referencia del mueble
            available_paths: Lista de diccionarios con información de rutas disponibles

        Returns:
            Tuple[str, float]: (Ruta donde buscar, costo de la interacción)
        """
        # Formatear la información de las rutas de manera jerárquica
        paths_info = ""
        for path in available_paths:
            depth_indent = "  " * path['depth']
            paths_info += f"{depth_indent}- {path['name']}\n"
            paths_info += f"{depth_indent}  Ruta completa: {path['path']}\n"
            paths_info += f"{depth_indent}  Es EDITABLE: {path['is_editable']}\n"
            paths_info += f"{depth_indent}  Es NUBE: {path['is_nube']}\n"
            paths_info += f"{depth_indent}  Ruta relativa: {path['relative_to_start']}\n\n"
        
        prompt = f"""Como experto en la estructura de archivos de muebles RTA, necesito que analices estas rutas y determines dónde buscar el archivo Rhino:

Referencia del mueble: {reference}
Ruta actual: {source_folder}

ESTRUCTURA DE CARPETAS DISPONIBLE:
{paths_info}

REGLAS DE BÚSQUEDA Y ANÁLISIS:

1. REGLA PRINCIPAL - CARPETA EDITABLES:
   - SIEMPRE buscar primero la carpeta llamada 'EDITABLE' o 'EDITABLES'
   - DETENERSE en la carpeta EDITABLES, NO entrar en sus subcarpetas
   - Si hay varias carpetas EDITABLES, elegir la más cercana a la referencia

2. ANÁLISIS DEL NOMBRE DE LA REFERENCIA:
   - La referencia "{reference}" debe guiar la búsqueda
   - Identifica palabras clave en la referencia (ej: "NIGHTSTAND" vs "MESA DE NOCHE")
   - Considera variaciones de nombres (ej: "Eter" puede estar como "ETER" o "Éter")

3. ESTRUCTURA JERÁRQUICA:
   - Prioriza la carpeta EDITABLES que esté en la misma rama que coincida con el nombre de la referencia
   - NO entrar en subcarpetas dentro de EDITABLES (como 'VERSION 1', 'OLD', etc.)
   - Si hay múltiples rutas, elegir la que mejor coincida con el nombre de la referencia

4. IMPORTANTE:
   - DEBES elegir una ruta que exista en la lista proporcionada
   - SIEMPRE detenerse en la carpeta EDITABLES, no explorar más profundo
   - Si hay varias opciones, elegir la que esté en la rama más relevante para la referencia

Analiza cuidadosamente y responde SOLAMENTE con la ruta completa de la carpeta EDITABLES donde deberíamos buscar el archivo Rhino.
NO INCLUIR subcarpetas dentro de EDITABLES en tu respuesta."""

        try:
            return self._make_api_call(
                "determine_rhino_search",
                [{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1
            )
            
        except Exception as e:
            logger.error(f"Error al determinar estrategia de búsqueda: {str(e)}")
            raise ValueError(f"Error al determinar estrategia de búsqueda: {str(e)}") 