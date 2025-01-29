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
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_prompts.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
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

class LLMManager(QObject):
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
    
    tokens_updated = pyqtSignal(int, int)  # Nueva señal para tokens
    cost_updated = pyqtSignal(float)  # Nueva señal para costo
    
    def __init__(self):
        """Inicializa el gestor de LLM cargando la API key desde .env"""
        super().__init__()
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
        
        # Contadores de tokens
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        # Historial de conversación
        self.conversation_history = []
        
        logger.info("LLMManager inicializado correctamente")
        
    def count_tokens(self, text: str) -> int:
        """
        Cuenta la cantidad de tokens en un texto.
        
        Args:
            text: Texto a contar tokens
            
        Returns:
            int: Número de tokens
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.error(f"Error al contar tokens: {str(e)}")
            return 0

    def count_messages_tokens(self, messages: List[Dict]) -> int:
        """
        Cuenta los tokens en una lista de mensajes.
        
        Args:
            messages: Lista de mensajes en formato ChatCompletion
            
        Returns:
            int: Total de tokens en los mensajes
        """
        total = 0
        try:
            for message in messages:
                # Contar tokens del contenido
                content_tokens = self.count_tokens(message.get("content", ""))
                # Contar tokens del rol (aproximadamente 4 tokens por rol)
                role_tokens = 4
                total += content_tokens + role_tokens
            
            # Agregar tokens de formato (aproximadamente 3 tokens por mensaje)
            total += len(messages) * 3
            
            return total
        except Exception as e:
            logger.error(f"Error al contar tokens de mensajes: {str(e)}")
            return 0

    def get_token_counts(self) -> Tuple[int, int]:
        """
        Obtiene el conteo total de tokens de entrada y salida.
        
        Returns:
            Tuple[int, int]: (total_input_tokens, total_output_tokens)
        """
        return self.total_input_tokens, self.total_output_tokens

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
            
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calcula el costo basado en los tokens de entrada y salida.
        
        Args:
            input_tokens: Tokens de entrada para esta operación
            output_tokens: Tokens de salida para esta operación
            
        Returns:
            float: Costo calculado para esta operación
        """
        try:
            # Actualizar totales
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            
            # Calcular costo usando las tarifas por 1K tokens
            input_cost = (input_tokens / 1000) * 0.0015  # $0.0015 por 1K tokens
            output_cost = (output_tokens / 1000) * 0.002  # $0.002 por 1K tokens
            total_cost = input_cost + output_cost
            
            # Actualizar costo de la sesión
            self.session_cost += total_cost
            
            # Emitir señales de actualización
            logger.info(f"Calculando costos:")
            logger.info(f"  - Tokens entrada: {input_tokens} (${input_cost:.4f})")
            logger.info(f"  - Tokens salida: {output_tokens} (${output_cost:.4f})")
            logger.info(f"  - Costo total operación: ${total_cost:.4f}")
            logger.info(f"  - Costo acumulado sesión: ${self.session_cost:.4f}")
            
            # Emitir señales
            logger.debug("Emitiendo señal tokens_updated...")
            self.tokens_updated.emit(self.total_input_tokens, self.total_output_tokens)
            logger.debug("Emitiendo señal cost_updated...")
            self.cost_updated.emit(self.session_cost)
            logger.debug("Señales emitidas correctamente")
            
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
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Determinar el tipo de operación para el resumen
            operation_type = ""
            if "format_reference" in operation:
                operation_type = "Formateo de nombre de referencia"
            elif "verify_references" in operation:
                operation_type = "Verificación de referencias"
            elif "decision_verificar_referencias" in operation:
                operation_type = "Decisión sobre verificación de referencias"
            elif "decision_confirmar_nombres" in operation:
                operation_type = "Decisión sobre confirmación de nombres"
            elif "decision_crear_carpetas" in operation:
                operation_type = "Decisión sobre creación de carpetas"
            else:
                operation_type = "Operación general"
            
            logger.info(f"=== INICIO PROMPT [{operation}] ===")
            logger.info(f"Timestamp: {timestamp}")
            logger.info(f"Tipo de operación: {operation_type}")
            logger.info(f"Temperatura: {temperature}")
            if max_tokens:
                logger.info(f"Max tokens: {max_tokens}")
            logger.info("=== FIN PROMPT ===\n")
            
        except Exception as log_e:
            logger.error(f"Error al registrar prompt: {str(log_e)}")
        
        while attempts < self.MAX_RETRIES:
            try:
                # Contar tokens de entrada antes de la llamada
                input_tokens = self.count_messages_tokens(messages)
                logger.debug(f"Tokens de entrada contados: {input_tokens}")
                
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
                
                # Contar tokens de salida
                output_tokens = self.count_tokens(response_text)
                logger.debug(f"Tokens de salida contados: {output_tokens}")
                
                # Calcular costo (esto también emitirá las señales)
                cost = self.calculate_cost(input_tokens, output_tokens)
                
                # Registrar uso
                logger.info(f"=== RESULTADO LLAMADA [{operation}] ===")
                logger.info(f"Tokens entrada: {input_tokens}")
                logger.info(f"Tokens salida: {output_tokens}")
                logger.info(f"Tokens totales - Entrada: {self.total_input_tokens}, Salida: {self.total_output_tokens}")
                logger.info(f"Costo: ${cost:.4f}")
                logger.info("=== FIN RESULTADO ===\n")
                
                return response_text, cost
                
            except openai.error.APIError as e:
                last_error = APIError(operation, getattr(e, 'status_code', 500), str(e))
                logger.error(f"Error API en {operation}: {str(e)}")
            except openai.error.Timeout:
                last_error = APIError(operation, 408, "Timeout en la conexión")
                logger.error(f"Timeout en {operation}")
            except openai.error.RateLimitError:
                last_error = APIError(operation, 429, "Límite de rate excedido")
                logger.error(f"Rate limit excedido en {operation}")
            except Exception as e:
                last_error = ResponseError(f"Error inesperado: {str(e)}")
                logger.error(f"Error inesperado en {operation}: {str(e)}")
                
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
            
            # Realizar llamada a la API y obtener respuesta
            response_text, cost = self._make_api_call(
                f"decision_{step}",
                messages,
                temperature=0.3
            )
            
            # Registrar la respuesta en el log
            logger.info(f"=== RESPUESTA [{step}] ===")
            logger.info(f"Texto de respuesta: {response_text}")
            logger.info(f"Costo: ${cost:.4f}")
            logger.info(f"Tokens acumulados - Entrada: {self.total_input_tokens}, Salida: {self.total_output_tokens}")
            logger.info("=== FIN RESPUESTA ===\n")
            
            return response_text, cost
            
        except Exception as e:
            if isinstance(e, (APIError, PromptError, ResponseError)):
                raise
            raise ResponseError(f"Error inesperado: {str(e)}")

    def start_new_conversation(self):
        """Inicia una nueva conversación, limpiando el historial anterior."""
        self.conversation_history = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.session_cost = 0.0
        logger.info("Nueva conversación iniciada")

    def add_message_to_history(self, role: str, content: str):
        """
        Agrega un mensaje al historial de la conversación.
        
        Args:
            role: Rol del mensaje ('system', 'user', 'assistant')
            content: Contenido del mensaje
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def get_conversation_messages(self) -> List[Dict]:
        """
        Obtiene todos los mensajes de la conversación actual.
        
        Returns:
            List[Dict]: Lista de mensajes en formato ChatCompletion
        """
        return self.conversation_history.copy()

    def process_message(self, 
                       user_message: str,
                       system_message: Optional[str] = None,
                       temperature: float = 0.7) -> Tuple[str, float]:
        """
        Procesa un mensaje del usuario manteniendo el contexto de la conversación.
        
        Args:
            user_message: Mensaje del usuario
            system_message: Mensaje del sistema (opcional)
            temperature: Temperatura para la generación
            
        Returns:
            Tuple[str, float]: (Respuesta del LLM, costo de la interacción)
        """
        try:
            messages = []
            
            # Si hay un mensaje del sistema, agregarlo al inicio
            if system_message:
                messages.append({
                    "role": "system",
                    "content": system_message
                })
                self.add_message_to_history("system", system_message)
            
            # Agregar historial de conversación
            messages.extend(self.get_conversation_messages())
            
            # Agregar mensaje actual del usuario
            messages.append({
                "role": "user",
                "content": user_message
            })
            self.add_message_to_history("user", user_message)
            
            # Obtener respuesta
            response_text, cost = self._make_api_call(
                "process_message",
                messages,
                temperature=temperature
            )
            
            # Agregar respuesta al historial
            self.add_message_to_history("assistant", response_text)
            
            return response_text, cost
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            raise

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
        # Cargar lista de colores válidos
        try:
            ruta_colores = os.path.join(os.path.dirname(__file__), 'colores.json')
            with open(ruta_colores, 'r', encoding='utf-8') as f:
                data = json.load(f)
                colores_validos = data.get('materiales_unicos', [])
                lista_colores = ", ".join(colores_validos)
        except Exception as e:
            logger.error(f"Error al cargar colores: {str(e)}")
            lista_colores = "Error al cargar lista de colores"

        prompt = f"""Formatea este nombre de referencia siguiendo EXACTAMENTE estas reglas y pasos de razonamiento:

1. ANÁLISIS INICIAL:
   a) Identifica el nombre base del mueble sin colores ni especificaciones
   b) Identifica TODOS los colores/materiales mencionados
   c) Identifica si hay redundancias en los colores (mismos colores mencionados múltiples veces)
   d) Identifica si el nombre incluye "BI-COLOR" o términos similares que indiquen combinación de colores
   e) Identifica si hay colores simples y compuestos en la misma referencia
   f) IMPORTANTE: Identifica el orden original en que aparecen los colores

2. LIMPIEZA DE INFORMACIÓN:
   - Eliminar dimensiones como "71,5X210X34 CM"
   - Eliminar "(1C)", "(2C)", etc.
   - Eliminar "_CAJA"
   - Eliminar "HD", "IMAGEN", "DIMENSIONES"
   - Eliminar redundancias en nombres de colores
   - Si dice "BI-COLOR" y luego repite los colores, mantener solo una instancia

3. FORMATEO DE COLORES:
   a) LISTA DE COLORES VÁLIDOS:
      Los únicos colores válidos son: {lista_colores}
   
   b) REGLAS ESPECIALES DE FORMATEO:
      - "BLANCO NEVADO", "BLANCO MARQUEZ", "BLANCO KRONOSPAN", "BLANCO KRONOS" se formatean como "BLANCO"
      - "BLANCO HIGH GLOSS" siempre debe escribirse exactamente así
      - Para materiales Kronospan (excepto blanco):
        * "FRESNO KRONOS", "FRESNO EUROPEO KRONOS", "FRESNO KRONOSPAN", "FRESNO EUROPEO KRONOSPAN", "FRESNO EUROPEO KRONO" 
          se formatean como "FRESNO KRONOSPAN"
        * "NOGAL KRONOS", "NOGAL KRONOSPAN", "NOGAL EUROPEO KRONOS", "NOGAL EUROPEO KRONOSPAN"
          se formatean como "NOGAL KRONOSPAN"
        * Para cualquier otro material seguido de "KRONOS", "KRONOSPAN" o "KRONO", 
          usar el formato "MATERIAL KRONOSPAN"
      - Cualquier otro color debe estar en la lista de colores válidos
      
   c) ORDEN DE LOS COLORES:
      - SIEMPRE mantener el orden original de los colores como aparecen en la descripción
      - Para colores compuestos, el orden es crítico y define una variante diferente
        Ejemplo: "DUNA-BLANCO" es diferente de "BLANCO-DUNA"
      - Si el mismo color compuesto aparece múltiples veces, usar la primera aparición para determinar el orden
   
   d) COLORES SIMPLES vs COMPUESTOS:
      - Un color simple es un solo color: "DUNA", "BLANCO", "WENGUE"
      - Un color compuesto usa guión: "DUNA-BLANCO", "BLANCO-WENGUE"
   
   e) REGLAS DE SEPARACIÓN:
      - Usar "+" con espacios alrededor para separar colores diferentes: "COLOR1 + COLOR2"
      - Usar "-" sin espacios para unir colores compuestos: "COLOR1-COLOR2"
      - Cambiar "/" o "\" por "-" en nombres compuestos, manteniendo el orden original
   
   g) CASOS ESP ECIALES:
      - Si un color simple aparece junto con un color compuesto que lo incluye, mantener ambos:
        Ejemplo: "(DUNA + DUNA-BLANCO)" es correcto porque DUNA es un color y DUNA-BLANCO es otro
      - Si hay dos colores compuestos, mantenerlos separados:
        Ejemplo: "(DUNA-BLANCO + BLANCO-WENGUE)" es correcto

4. FORMATO FINAL OBLIGATORIO:
   "CÓDIGO NÚMERO - NOMBRE (COLORES)"
   
   EJEMPLOS CORRECTOS:
   - "MDB 7236 - MUEBLE BOTIQUIN BATH BI-COLOR (DUNA + BLANCO)"
   - "MBD 7237 - MUEBLE BOTIQUIN BATH BI-COLOR (BLANCO-DUNA)"
   - "CLB 9493 - CLOSET BARILOCHE (DUNA + DUNA-BLANCO)"
   - "CLB 9494 - CLOSET BARILOCHE (DUNA + BLANCO-WENGUE)"
   - "CDB 9495 - CLOSET BARILOCHE (BLANCO + DUNA)"
   

5. VALIDACIÓN DE REDUNDANCIAS:
   - ¿El nombre contiene los mismos colores múltiples veces?
   - ¿Los colores en el nombre base son los mismos que en el paréntesis?
   - Si es así, mantener los colores SOLO en el paréntesis final
   - Para muebles BI-COLOR, el nombre base NO debe incluir los colores
   - Verificar que los colores simples y compuestos estén correctamente separados
   - ¿Se mantiene el orden original de los colores?

6. EJEMPLOS DE MANEJO DE REDUNDANCIAS Y COLORES:
   Entrada: "MBD 7237 MUEBLE BOTIQUIN BATH BI-COLOR DUNA/BLANCO (1C) DUNA/BLANCO MARQUEZ 72.6X41.2X35.2 CM"
   Correcto: "MDB 7236 - MUEBLE BOTIQUIN BATH BI-COLOR (DUNA + BLANCO)"
   
   Entrada: "MBD 7237 MUEBLE BOTIQUIN BATH BI-COLOR BLANCO/DUNA (1C) DUNA/BLANCO MARQUÉZ 72.6X41.2X35.2 CM"
   Correcto: "MBD 7237 - MUEBLE BOTIQUIN BATH BI-COLOR (BLANCO-DUNA)"
   
   Entrada: "MBD 7237 CLOSET BARILOCHE DUNA BLANCO MARQUEZ"
   Correcto: "CLB 9493 - CLOSET BARILOCHE (DUNA + BLANCO)"

   Entrada: "CLB 9494 CLOSET BARILOCHE FRESNO EUROPEO KRONOS"
   Correcto: "CLB 9494 - CLOSET BARILOCHE (FRESNO KRONOSPAN)"

   Entrada: "CLB 9495 CLOSET BARILOCHE NOGAL KRONOSPAN + BLANCO KRONOS"
   Correcto: "CLB 9495 - CLOSET BARILOCHE (NOGAL KRONOSPAN + BLANCO)"

7. VALIDACIÓN FINAL:
   Antes de devolver el nombre, verifica:
   - ¿Se eliminaron todas las redundancias de colores?
   - ¿Los colores aparecen solo una vez y en el lugar correcto?
   - ¿Los colores simples y compuestos están correctamente separados?
   - ¿El formato cumple con el patrón "CÓDIGO NÚMERO - NOMBRE (COLORES)"?
   - ¿Se mantiene toda la información importante sin repeticiones?
   - ¿Se respeta el orden original de los colores?
   - ¿"MQZ" solo se usa con "BLANCO" y está correctamente formateado como "BLANCO MQZ"?
   - ¿Todos los colores usados están en la lista de colores válidos?

Información a formatear:
Código: {code}
Número: {number}
Descripción: {description}

Devuelve SOLO el texto formateado, sin explicaciones."""

        try:
            logger.info(f"Formateando referencia: {code} {number}\n")
            
            messages = [{
                "role": "user",
                "content": prompt
            }]
            
            response_text, cost = self._make_api_call(
                "format_reference",
                messages,
                temperature=0.3  # Bajo para mantener consistencia
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
                temperature=0.3
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
                temperature=0.3  # Bajo para mantener consistencia
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
                temperature=0.3
            )
            
        except Exception as e:
            logger.error(f"Error al determinar estrategia de búsqueda: {str(e)}")
            raise ValueError(f"Error al determinar estrategia de búsqueda: {str(e)}") 

    def determine_folder_structure(self, 
                                source_path: str,
                                reference_name: str,
                                category: str) -> Tuple[str, float]:
        """
        Determina la estructura de carpetas óptima basada en la ruta origen.
        
        Args:
            source_path: Ruta origen en la NAS
            reference_name: Nombre de la referencia
            category: Categoría del mueble

        Returns:
            Tuple[str, float]: (Estructura de carpetas sugerida, costo de la interacción)
        """
        prompt = f"""Como experto en organización de archivos de muebles RTA, necesito que determines la estructura de carpetas óptima y simplificada.

INFORMACIÓN:
Ruta origen: {source_path}
Referencia: {reference_name}
Categoría: {category}

ANÁLISIS DE CATEGORÍA:
1. Si la categoría NO está especificada, debes RAZONAR la categoría correcta siguiendo estas reglas:
   - Analiza el TIPO DE MUEBLE y su USO PRINCIPAL
   - Categorías válidas son: AMBIENTE, OFICINA, COCINA, BAÑO Y DORMITORIO
   - Ejemplos de razonamiento:
     * "Centro de Cómputo" -> OFICINA (porque es un escritorio para computadora)
     * "Biblioteca Lisa" -> OFICINA (porque es un estante para libros)
     * "Closet Austral" -> DORMITORIO (porque es un closet para guardar ropa)
   - NO crear nuevas categorías fuera de las listadas
   - NO usar el nombre del mueble como categoría

2. PRIORIDAD DE ASIGNACIÓN:
   a) Si viene especificada en el campo 'Categoría', usar esa
   b) Si no viene especificada, analizar la ruta origen buscando la categoría en las rutas predeterminadas
   c) Si aún no es clara, RAZONAR basado en el uso principal del mueble

REGLAS PARA LA ESTRUCTURA:

1. ESTRUCTURA BASE:
   - Debe comenzar con la categoría principal (AMBIENTE, OFICINA, COCINA, BAÑO Y DORMITORIO). La categoría siempre debe estar escrita en singular.
   - Debe terminar con la carpeta de la referencia específica
   - Mantener SOLO 5 niveles máximo en la estructura

2. ELIMINACIÓN DE CARPETAS:
   - Eliminar TODAS las carpetas intermedias que contengan múltiples códigos de referencia
     Ejemplo a eliminar: "CLW 928 - CLH 3534 - CLK 4870 - CBD 4976 - CLC 6509 - MAPA DE EMPAQUE"
   - Eliminar TODAS las carpetas técnicas como:
     * EDITABLE, EDITABLES
     * 16MM, 3DM
     * NUBE
     * RENDERS, PDF, DWG, JPG
   - Eliminar carpetas que solo contengan dimensiones o especificaciones técnicas

3. MANEJO DE DUPLICADOS:
   - Si una carpeta aparece repetida en la ruta, mantener SOLO UNA instancia
     Ejemplo: "CLOSET AUSTRAL 3 PUERTAS\CLOSET AUSTRAL 3 PUERTAS" -> "CLOSET AUSTRAL 3 PUERTAS"
   - Si el nombre del mueble aparece en múltiples niveles, mantener solo el más significativo

4. COHERENCIA CON RUTAS PREDETERMINADAS:
   - La primera carpeta después de las rutas predeterminadas debe coincidir exactamente con la carpeta correspondiente en las rutas de referencia proporcionadas.
   - Rutas predeterminadas:
    
     //192.168.200.250/ambientes
     //192.168.200.250/baño
     //192.168.200.250/cocina
     //192.168.200.250/dormitorio
     //192.168.200.250/mercadeo/ANIMACIÓN 3D
     //192.168.200.250/mercadeo/IMAGENES MUEBLES
     //192.168.200.250/rtadiseño/AMBIENTES.3
     //192.168.200.250/rtadiseño/BAÑO.3
     //192.182.200.250/rtadiseño/COCINA.3
     //192.168.200.250/rtadiseño/DORMITORIO.3
     //192.168.200.250/rtadiseño/MERCADEO.3/IMÁGENES MUEBLES
     //192.168.200.250/rtadiseño/MERCADEO.3/ANIMACIONES
     
   - Ejemplo:
     - Ruta origen: `//192.168.200.250/dormitorio/Zapatero Alto Basico Odesto/ODESTO HIGH BASIC SHOE RACK/NUBE/ZLB 10556 - ZLM 10557 - ZLW 10950 - ISOMETRICO`
     - Carpeta resultante debe comenzar con: `DORMITORIO/ZAPATERO ALTO BASICO ODESTO`
     - Si la referencia invesitgada fue 'ZLW 10950' entonces la ruta completa debería quedar como: `DORMITORIO/Zapatero Alto Basico ODESTO/ODESTO HIGH BASIC SHOE RACK/ZLW 10950 - ODESTO HIGH BASIC SHOE RACK (WENGUE)`
     - recuerda que la información es completada con la información recolectada en el paso anterior desde el google sheet.

5. ESTRUCTURA FINAL DESEADA:
   Debe seguir uno de estos dos patrones según el caso:

   CASO 1 - PRODUCTO SIMPLE:
   CATEGORÍA/TIPO DE MUEBLE/REFERENCIA FINAL
   Ejemplo: "BIBLIOTECA/BIBLIOTECA LISA EASY/BLB 7602 - BIBLIOTECA LISA EASY (BELLOTA)"

   CASO 2 - PRODUCTO CON SUBREFERENCIA:
   CATEGORÍA/TIPO DE MUEBLE BASE/NOMBRE ESPECÍFICO/REFERENCIA FINAL
   Ejemplo: "DORMITORIO/ZAPATERO ALTO BASICO ODESTO/ODESTO HIGH BASIC SHOE RACK/ZLW 10950 - ODESTO HIGH BASIC SHOE RACK (WENGUE)"

   REGLAS DE DECISIÓN:
   1. Si en la ruta origen existe una carpeta adicional que especifica una variante o nombre específico del producto (como 'ODESTO HIGH BASIC SHOE RACK'), mantenerla como nivel adicional
   2. Si la ruta origen solo muestra el nombre básico del producto, usar el CASO 1
   3. La referencia final (último nivel) SIEMPRE debe mantener el código y nombre completo con color/acabado

   IMPORTANTE:
   - La estructura nunca debe exceder 4 niveles
   - El último nivel SIEMPRE debe contener el código de referencia
   - Los niveles intermedios NUNCA deben contener códigos de referencia

6. VALIDACIÓN FINAL OBLIGATORIA:
   Antes de responder, verifica que la estructura propuesta cumpla con TODAS estas condiciones:
   1. ¿Tiene máximo 4 niveles separados por '/'?
   2. ¿El primer nivel es una CATEGORÍA VÁLIDA (AMBIENTE, OFICINA, COCINA, BAÑO Y DORMITORIO) en singular y mayúsculas?
   3. ¿La categoría fue determinada correctamente según el uso del mueble y no solo por su nombre?
   4. ¿El último nivel contiene el código de referencia y nombre completo?
   5. ¿Los niveles intermedios NO contienen códigos de referencia?
   6. ¿Se mantiene el nombre específico del producto si existía en la ruta origen?
   7. ¿Se eliminaron todas las carpetas técnicas (EDITABLE, NUBE, etc.)?
   8. ¿Se eliminaron las carpetas con múltiples referencias?
   
   Si alguna condición no se cumple, ajusta la estructura antes de responder.

Analiza la ruta origen y proporciona SOLO la estructura de carpetas sugerida, separando niveles con '/'.
Ejemplo correcto: "DORMITORIO/CLOSET AUSTRAL 3 PUERTAS/CLW 9365 - CLOSET AUSTRAL 3 PUERTAS (WENGUE)"
Ejemplo correcto 2: "COCINA/MODULO MICROONDAS BAJO KIT/MBB 7603 - MODULO MICROONDAS BAJO KIT (BLANCO MQZ + BELLOTA-BLANCO)"

NO incluyas explicaciones ni comentarios adicionales."""
    
        try:
            return self._make_api_call(
                "determine_folder_structure",
                [{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.2  # Bajo para mantener consistencia
            )
            
        except Exception as e:
            logger.error(f"Error al determinar estructura de carpetas: {str(e)}")
            raise ValueError(f"Error al determinar estructura de carpetas: {str(e)}") 