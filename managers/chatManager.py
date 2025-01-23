"""
Nombre del Archivo: chatManager.py
Descripción: Gestor de chat que maneja la interacción entre el usuario y el LLM
             durante el proceso de creación de carpetas.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2 de Marzo de 2024
Versión: 1.0
"""

from PyQt5.QtCore import QObject, pyqtSignal
from utils.llm_manager import LLMManager
from typing import Dict, List, Optional
import os
import logging
import json
from datetime import datetime
import shutil

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_prompts.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChatError(Exception):
    """Clase base para errores del chat."""
    pass

class ProcessStepError(ChatError):
    """Error durante el procesamiento de un paso específico."""
    def __init__(self, step: str, message: str, context: Optional[Dict] = None):
        self.step = step
        self.context = context or {}
        super().__init__(f"Error en paso '{step}': {message}")

class LLMCommunicationError(ChatError):
    """Error en la comunicación con el LLM."""
    def __init__(self, operation: str, message: str):
        self.operation = operation
        super().__init__(f"Error en operación LLM '{operation}': {message}")

class ChatManager(QObject):
    """
    Gestor de chat que maneja la interacción entre el usuario y el LLM.
    
    Esta clase coordina la comunicación entre la interfaz de usuario y el LLM,
    manteniendo el estado de la conversación y gestionando el flujo del proceso
    de creación de carpetas.
    """
    
    # Estados del proceso
    ESTADO_INICIAL = "inicial"
    ESTADO_VERIFICAR_REFERENCIAS = "verificar_referencias"
    ESTADO_BUSCAR_SHEETS = "buscar_sheets"
    ESTADO_CONFIRMAR_NOMBRES = "confirmar_nombres"
    ESTADO_CREAR_CARPETAS = "crear_carpetas"
    ESTADO_SELECCIONAR_RHINO = "seleccionar_rhino"
    ESTADO_ERROR = "error"
    ESTADO_FINALIZADO = "finalizado"
    
    # Señales para comunicación con la interfaz
    llm_response = pyqtSignal(str, str, bool)  # sender, message, is_error
    typing_status_changed = pyqtSignal(bool)  # is_typing
    error_occurred = pyqtSignal(str, str)  # error_type, error_message
    
    def __init__(self, controller):
        """
        Inicializa el gestor de chat.
        
        Args:
            controller: Referencia al controlador principal
        """
        super().__init__()
        self.controller = controller
        self.llm_manager = LLMManager()
        self.current_references = []
        self.conversation_history = []
        self.current_step = self.ESTADO_INICIAL
        self.step_context = {}
        self.error_recovery_attempts = {}
        self.pending_rhino_selection = None  # Para almacenar la referencia pendiente de selección de Rhino
        
    def _handle_error(self, error: Exception) -> str:
        """
        Maneja un error y genera un mensaje apropiado para el usuario.
        
        Args:
            error: Excepción a manejar
            
        Returns:
            str: Mensaje de error formateado para el usuario
        """
        if isinstance(error, ProcessStepError):
            # Incrementar contador de intentos de recuperación
            self.error_recovery_attempts[error.step] = self.error_recovery_attempts.get(error.step, 0) + 1
            
            # Si hay demasiados intentos, sugerir reiniciar
            if self.error_recovery_attempts[error.step] >= 3:
                return (
                    "Ha habido varios errores en este paso. "
                    "Te sugiero reiniciar el proceso o contactar al soporte técnico."
                )
            
            # Generar mensaje según el paso
            if error.step == "verificar_referencias":
                return (
                    "Hubo un problema al verificar las referencias en la base de datos. "
                    "Por favor, verifica que las referencias estén correctamente escritas."
                )
            elif error.step == "buscar_sheets":
                return (
                    "Error al buscar información en Google Sheets. "
                    "Verifica que las credenciales sean válidas y que haya conexión."
                )
            elif error.step == "crear_carpetas":
                return (
                    "Ocurrió un error al crear las carpetas. "
                    "Verifica los permisos y que las rutas sean accesibles."
                )
            else:
                return f"Error en el paso '{error.step}': {str(error)}"
                
        elif isinstance(error, LLMCommunicationError):
            return (
                "Hubo un problema al comunicarse con el asistente. "
                f"Detalles: {str(error)}"
            )
        else:
            return f"Error inesperado: {str(error)}"
        
    def _validate_step_transition(self, current_step: str, next_step: str) -> bool:
        """
        Valida si la transición entre pasos es válida.
        
        Args:
            current_step: Paso actual
            next_step: Paso siguiente
            
        Returns:
            bool: True si la transición es válida
        """
        valid_transitions = {
            self.ESTADO_INICIAL: [self.ESTADO_VERIFICAR_REFERENCIAS, self.ESTADO_ERROR],
            self.ESTADO_VERIFICAR_REFERENCIAS: [self.ESTADO_BUSCAR_SHEETS, self.ESTADO_ERROR, self.ESTADO_FINALIZADO],
            self.ESTADO_BUSCAR_SHEETS: [self.ESTADO_CREAR_CARPETAS, self.ESTADO_ERROR, self.ESTADO_FINALIZADO],
            self.ESTADO_CREAR_CARPETAS: [self.ESTADO_SELECCIONAR_RHINO, self.ESTADO_FINALIZADO, self.ESTADO_ERROR],
            self.ESTADO_SELECCIONAR_RHINO: [self.ESTADO_CREAR_CARPETAS, self.ESTADO_FINALIZADO, self.ESTADO_ERROR],
            self.ESTADO_ERROR: [
                self.ESTADO_VERIFICAR_REFERENCIAS,
                self.ESTADO_BUSCAR_SHEETS,
                self.ESTADO_CREAR_CARPETAS,
                self.ESTADO_SELECCIONAR_RHINO,
                self.ESTADO_FINALIZADO
            ],
            self.ESTADO_FINALIZADO: []
        }
        
        return next_step in valid_transitions.get(current_step, [])
        
    def _transition_to_step(self, next_step: str):
        """
        Realiza la transición a un nuevo paso, validando y preparando el contexto.
        
        Args:
            next_step: Paso al que se quiere transicionar
        
        Raises:
            ProcessStepError: Si la transición no es válida
        """
        if not self._validate_step_transition(self.current_step, next_step):
            raise ProcessStepError(
                self.current_step,
                f"Transición inválida de '{self.current_step}' a '{next_step}'"
            )
            
        self.current_step = next_step
        
    def start_folder_creation_process(self, references: List[str], db_results: Optional[Dict[str, List[str]]] = None):
        """
        Inicia el proceso de creación de carpetas.
        
        Args:
            references: Lista de referencias a procesar
            db_results: Diccionario opcional con los resultados de la búsqueda en BD.
                       Las claves son las referencias y los valores son listas de rutas.
        """
        try:
            if not references:
                raise ProcessStepError(self.ESTADO_INICIAL, "No se proporcionaron referencias")
                
            self.current_references = references
            self.conversation_history = []
            self.error_recovery_attempts = {}
            self.current_step = self.ESTADO_INICIAL
            
            # Reiniciar contadores de tokens
            self.llm_manager.total_input_tokens = 0
            self.llm_manager.total_output_tokens = 0
            self.controller.main_window.chat_panel.update_tokens(0, 0)
            
            # Mensaje inicial del sistema
            welcome_message = (
                "¡Hola! Soy el asistente de RTA y te ayudaré en el proceso de "
                "creación de carpetas para las referencias."
            )
            self.llm_response.emit("Sistema", welcome_message, False)
            
            # Si ya tenemos resultados de la BD, guardarlos en el contexto
            if db_results:
                # Clasificar referencias encontradas y no encontradas
                found_refs = []
                not_found_refs = []
                
                for ref in references:
                    paths = db_results.get(ref, [])
                    if paths:
                        found_refs.append(ref)
                    else:
                        not_found_refs.append(ref)
                
                self.step_context = {
                    'db_results': db_results,
                    'found_refs': found_refs,
                    'not_found_refs': not_found_refs,
                    'total_refs': len(references)
                }
            
            # Siempre empezar por verificar referencias
            self._transition_to_step(self.ESTADO_VERIFICAR_REFERENCIAS)
            
            # Iniciar el proceso
            self.process_next_step()
            
        except Exception as e:
            error_msg = self._handle_error(e)
            self.llm_response.emit("Sistema", error_msg, True)
            self.error_occurred.emit("inicio", str(e))
        
    def _update_tokens_display(self):
        """Actualiza la visualización de tokens en la interfaz."""
        input_tokens, output_tokens = self.llm_manager.get_token_counts()
        self.controller.main_window.chat_panel.update_tokens(input_tokens, output_tokens)
        logger.info(f"Tokens actualizados - Entrada: {input_tokens}, Salida: {output_tokens}")

    def handle_user_message(self, message: str):
        """
        Maneja los mensajes del usuario, incluyendo la selección de archivos Rhino alternativos.
        """
        try:
            # Si el mensaje es un botón de archivo
            if message.startswith("<file_button>"):
                button_info = message[len("<file_button>"):-len("</file_button>")]
                button_data = eval(button_info)
                
                # Si es una selección de archivo Rhino alternativo
                if button_data.get("type") == "choose_rhino":
                    chosen_path = button_data.get("path")
                    if chosen_path and os.path.exists(chosen_path):
                        # Obtener la carpeta destino del contexto actual
                        target_folder = self.step_context.get("target_folder")
                        if target_folder:
                            # Copiar el archivo Rhino seleccionado
                            rhino_name = os.path.basename(chosen_path).upper()
                            rhino_target = os.path.join(target_folder, rhino_name)
                            shutil.copy2(chosen_path, rhino_target)
                            
                            # Actualizar el resultado en el contexto
                            if "copy_results" in self.step_context:
                                self.step_context["copy_results"]["rhino"] = rhino_name
                                # Eliminar el error de "No se encontraron archivos Rhino" si existe
                                if "errors" in self.step_context["copy_results"]:
                                    self.step_context["copy_results"]["errors"] = [
                                        err for err in self.step_context["copy_results"]["errors"]
                                        if "No se encontraron archivos Rhino" not in err
                                    ]
                            
                            # Marcar que ya no estamos esperando selección
                            self.step_context["waiting_for_rhino"] = False
                        
                        # Notificar al usuario
                        self.llm_response.emit(
                            "Sistema",
                            f"✅ Archivo Rhino {rhino_name} copiado exitosamente a la carpeta destino.",
                            False
                        )
                        
                        # Continuar con el siguiente paso
                        self.process_next_step()
                    else:
                        self.llm_response.emit(
                            "Sistema",
                            "❌ Error: No se pudo copiar el archivo porque no se encontró la carpeta destino.",
                            True
                        )
                else:
                    self.llm_response.emit(
                        "Sistema",
                        "❌ Error: El archivo seleccionado no existe o no es accesible.",
                        True
                    )
                return

            # Guardar el mensaje en el historial
            self.conversation_history.append(("usuario", message))
            
            # Indicar que el LLM está procesando
            self.typing_status_changed.emit(True)
            
            try:
                # Procesar el mensaje según el paso actual
                response, cost = self.llm_manager.process_folder_creation_decision(
                    self.current_step,
                    self.step_context,
                    message
                )
                
                # Actualizar tokens y costo en la UI
                self._update_tokens_display()
                self.controller.main_window.chat_panel.update_cost(
                    self.llm_manager.get_session_cost()
                )
                
                # Analizar la respuesta y tomar acción
                if "continuar" in response.lower():
                    if self.current_step == "verificar_referencias":
                        self._transition_to_step("buscar_sheets")
                        self.llm_response.emit(
                            "Sistema",
                            "Excelente. Procederé a buscar la información en Google Sheets.",
                            False
                        )
                        self.process_next_step()
                    elif self.current_step == "confirmar_nombres":
                        self._transition_to_step("crear_carpetas")
                        self.llm_response.emit(
                            "Sistema",
                            "Perfecto. Comenzaré a crear las carpetas y copiar los archivos.",
                            False
                        )
                        self.process_next_step()
                else:
                    # Si no se debe continuar, mostrar la respuesta del LLM
                    self.llm_response.emit("LLM", response, False)
                    
            except Exception as e:
                error_msg = self._handle_error(e)
                self.llm_response.emit("Sistema", error_msg, True)
                self.error_occurred.emit("mensaje_usuario", str(e))
                
            finally:
                # Indicar que el LLM terminó de procesar
                self.typing_status_changed.emit(False)
                
        except Exception as e:
            error_msg = self._handle_error(e)
            self.llm_response.emit("Sistema", error_msg, True)
            self.error_occurred.emit(self.current_step, str(e))
            self._transition_to_step(self.ESTADO_ERROR)

    def process_single_reference(self):
        """
        Procesa una única referencia de forma secuencial, manejando los mensajes en el orden correcto.
        """
        try:
            # Verificar si hay referencias pendientes
            if not self.pending_rhino_selection or not self.pending_rhino_selection.get("pending_files"):
                logger.warning("No hay referencias pendientes para procesar")
                return

            # Obtener la referencia actual
            current_ref = self.pending_rhino_selection["original"]
            ref_data = self.pending_rhino_selection["pending_files"][current_ref]

            # 1. Mostrar mensaje solicitando la selección del archivo Rhino
            message = f"\nPor favor, selecciona el archivo Rhino para la referencia: {current_ref}"
            
            # Obtener las alternativas de archivos Rhino
            rhino_alternatives = []
            if ref_data.get("files_info", {}).get("rhino_alternatives"):
                rhino_alternatives = ref_data["files_info"]["rhino_alternatives"]
            
            if rhino_alternatives:
                # 2. Si hay múltiples archivos, mostrar la lista
                message += "\nSe han encontrado los siguientes archivos Rhino:\n"
                
                for i, path in enumerate(rhino_alternatives):
                    if i > 0:
                        message += "\n---\n"  # Divisor entre archivos
                        
                    file_name = os.path.basename(path)
                    # Botón para abrir carpeta
                    folder_button = {
                        'text': "📁 Abrir carpeta",
                        'path': os.path.dirname(path),
                        'type': 'folder'
                    }
                    # Botón para abrir archivo
                    file_button = {
                        'text': "📄 Abrir archivo",
                        'path': path,
                        'type': 'rhino'
                    }
                    # Botón para elegir archivo
                    choose_button = {
                        'text': "✅ Elegir este archivo",
                        'path': path,
                        'type': 'choose_rhino'
                    }
                    
                    message += f"\n<b>{file_name}</b>\n"
                    message += f"<file_button>{folder_button}</file_button> "
                    message += f"<file_button>{file_button}</file_button> "
                    message += f"<file_button>{choose_button}</file_button>"
                
                # Botón para omitir al final, después de un divisor
                message += "\n\n---\n\n"
                skip_button = {
                    'text': "❌ Omitir archivo Rhino",
                    'path': '',
                    'type': 'skip_rhino'
                }
                message += f"<file_button>{skip_button}</file_button>"

            self.llm_response.emit("Sistema", message, False)

        except Exception as e:
            logger.error(f"Error al procesar referencia: {str(e)}")
            error_msg = self._handle_error(e)
            self.llm_response.emit("Sistema", error_msg, True)
            self._transition_to_step(self.ESTADO_ERROR)

    def handle_file_selection(self, file_path: str, selection_type: str):
        """
        Maneja la selección de archivos desde los botones del chat.
        """
        try:
            logger.info(f"ChatManager: Recibida selección - Path: {file_path}, Type: {selection_type}")
            
            if self.current_step != self.ESTADO_SELECCIONAR_RHINO:
                logger.warning(f"Selección recibida en estado inválido: {self.current_step}")
                return
                
            if not self.pending_rhino_selection:
                logger.warning("No hay selección de Rhino pendiente")
                return

            ref_data = self.pending_rhino_selection
            original_ref = ref_data.get('original')
            pending_files = ref_data.get('pending_files', {})
            
            # Procesar la selección actual
            if selection_type in ['choose_rhino', 'skip_rhino']:
                selected_rhino = file_path if selection_type == 'choose_rhino' else None
                results = self.controller.folder_creation_manager.complete_folder_creation(
                    ref_key=original_ref,
                    selected_rhino=selected_rhino
                )
                
                # 4. Mostrar mensaje de éxito para la referencia actual
                if not results.get("errors"):
                    self.llm_response.emit(
                        "Sistema",
                        f"✅ Carpeta creada exitosamente para {original_ref}",
                        False
                    )
                else:
                    error_msg = "\n".join(error.replace('**', '') for error in results["errors"])
                    self.llm_response.emit(
                        "Sistema",
                        f"❌ Error al crear carpeta para {original_ref}: {error_msg}",
                        True
                    )
                
                # Eliminar la referencia actual de pendientes
                if original_ref in pending_files:
                    del pending_files[original_ref]
                
                # 5. Pequeña pausa antes de continuar (implementada a través del tiempo de procesamiento)
                
                # 6. Procesar siguiente referencia si hay pendientes
                if pending_files:
                    next_ref = next(iter(pending_files))
                    self.pending_rhino_selection = {
                        "original": next_ref,
                        "pending_files": pending_files,
                        **pending_files[next_ref]
                    }
                    # Procesar la siguiente referencia
                    self.process_single_reference()
                else:
                    # No hay más referencias pendientes, mostrar resumen final
                    self._show_final_summary(results)
                    self.pending_rhino_selection = None
                    self._transition_to_step(self.ESTADO_FINALIZADO)

        except Exception as e:
            logger.error(f"Error al manejar selección de archivo: {str(e)}")
            error_msg = self._handle_error(e)
            self.llm_response.emit("Sistema", error_msg, True)
            self.error_occurred.emit("seleccion_archivo", str(e))
            self._transition_to_step(self.ESTADO_ERROR)

    def process_next_step(self):
        """
        Procesa el siguiente paso en el flujo de creación de carpetas.
        """
        try:
            # Si estamos esperando la selección de un archivo Rhino, no continuar
            if self.current_step == self.ESTADO_SELECCIONAR_RHINO and self.pending_rhino_selection:
                logger.info("Esperando selección de archivo Rhino")
                return

            if self.current_step == self.ESTADO_VERIFICAR_REFERENCIAS:
                # Solo buscar en la base de datos si no tenemos resultados previos
                if 'db_results' not in self.step_context:
                    logger.warning("No hay resultados de búsqueda previos. Se requiere ejecutar SearchThread primero.")
                    self.llm_response.emit(
                        "Sistema",
                        "Error: No se encontraron resultados de búsqueda. Por favor, inicia la búsqueda primero.",
                        True
                    )
                    return
                
                # Generar mensaje informativo para el chat
                found_refs = self.step_context['found_refs']
                not_found_refs = self.step_context['not_found_refs']
                
                message = f"He encontrado {len(found_refs)} referencias en la base de datos"
                if not_found_refs:
                    message += f" y {len(not_found_refs)} no fueron encontradas"
                message += ".\n\n"
                
                if found_refs:
                    message += "Referencias encontradas:\n"
                    for ref in found_refs:
                        message += f"- {ref}\n"
                    message += "\n"
                
                if not_found_refs:
                    message += "Referencias no encontradas:\n"
                    for ref in not_found_refs:
                        message += f"- {ref}\n"
                    message += "\n¿Deseas reformatear y crear las carpetas para los datos encontrados?"
                else:
                    message += "¿Deseas reformatear y crear las carpetas para los datos encontrados?"
                
                self.llm_response.emit("Sistema", message, False)
                
                # Mostrar botones de acción
                actions = [
                    {
                        'text': 'Sí',
                        'callback': lambda: self._handle_verification_response(True)
                    },
                    {
                        'text': 'No',
                        'callback': lambda: self._handle_verification_response(False)
                    }
                ]
                self.controller.main_window.chat_panel.show_action_buttons(actions)
                
                # Actualizar tokens después de la operación
                input_tokens, output_tokens = self.llm_manager.get_token_counts()
                self.controller.main_window.chat_panel.update_tokens(input_tokens, output_tokens)
                
            elif self.current_step == self.ESTADO_BUSCAR_SHEETS:
                # Buscar en Google Sheets y formatear nombres
                try:
                    # Capturar y registrar el inicio del proceso
                    logger.info("Iniciando búsqueda en Google Sheets y formateo de nombres")
                    
                    formatted_refs = self.controller.folder_creation_manager.fetch_and_format_with_sheets(
                        self.current_references
                    )
                    
                    logger.info(f"Referencias formateadas recibidas: {formatted_refs}")
                    
                    # Verificar si hay errores en las referencias formateadas
                    refs_with_errors = [ref for ref in formatted_refs if 'error' in ref]
                    refs_without_errors = [ref for ref in formatted_refs if 'error' not in ref]
                    
                    logger.info(f"Referencias con errores: {len(refs_with_errors)}")
                    logger.info(f"Referencias sin errores: {len(refs_without_errors)}")
                    
                    if refs_without_errors:
                        # Actualizar tabla de contenido con nombres formateados
                        entry = self.controller.main_window.entry
                        for ref_data in refs_without_errors:
                            # Buscar la referencia original en la tabla y actualizarla
                            for row in range(entry.rowCount()):
                                item = entry.item(row, 0)
                                if item and item.text().strip() == ref_data['original']:
                                    # Extraer solo el nombre formateado de la tupla (nombre, costo)
                                    nombre_formateado = ref_data['nombre_formateado'][0] if isinstance(ref_data['nombre_formateado'], tuple) else ref_data['nombre_formateado']
                                    item.setText(nombre_formateado)
                                    break
                        
                        # Actualizar contexto - asegurarnos de guardar solo los campos necesarios
                        self.step_context.update({
                            'formatted_refs': [{
                                'original': ref['original'],
                                'nombre_formateado': ref['nombre_formateado'][0] if isinstance(ref['nombre_formateado'], tuple) else ref['nombre_formateado']
                            } for ref in refs_without_errors]
                        })
                        
                        logger.info(f"Contexto actualizado: {self.step_context}")
                        
                        # Generar mensaje con los nombres formateados
                        message = "He obtenido los siguientes nombres formateados:<br><br>"
                        
                        # Primero mostrar las referencias exitosas
                        for ref in refs_without_errors:
                            nombre_formateado = ref['nombre_formateado'][0] if isinstance(ref['nombre_formateado'], tuple) else ref['nombre_formateado']
                            message += f'• <b>Original:</b> {ref["original"]}<br>'
                            message += f'• <b>Formateado:</b> {nombre_formateado}<br><br>'
                        
                        # Luego mostrar las referencias con error
                        if refs_with_errors:
                            message += "Referencias con problemas:<br>"
                            for ref in refs_with_errors:
                                message += f'• {ref["original"]}: {ref["error"]}<br>'
                            message += "<br>"
                        
                        message += "¿Deseas continuar con la creación de carpetas?"
                        
                        self.llm_response.emit("Sistema", message, False)
                        
                        # Mostrar botones de acción
                        actions = [
                            {
                                'text': 'Sí',
                                'callback': lambda: self._handle_sheets_response(True)
                            },
                            {
                                'text': 'No',
                                'callback': lambda: self._handle_sheets_response(False)
                            }
                        ]
                        self.controller.main_window.chat_panel.show_action_buttons(actions)
                        
                        # Actualizar tokens después de la operación
                        input_tokens, output_tokens = self.llm_manager.get_token_counts()
                        self.controller.main_window.chat_panel.update_tokens(input_tokens, output_tokens)
                        
                    else:
                        error_message = "No se pudo formatear ninguna referencia correctamente.<br><br>"
                        if refs_with_errors:
                            error_message += "Errores encontrados:<br>"
                            for ref in refs_with_errors:
                                error_message += f'• {ref["original"]}: {ref["error"]}<br>'
                        raise ProcessStepError("buscar_sheets", error_message)
                    
                except ProcessStepError as e:
                    logger.error(f"Error en el proceso: {str(e)}")
                    raise
                except Exception as e:
                    logger.error(f"Error inesperado: {str(e)}")
                    raise ProcessStepError(
                        "buscar_sheets",
                        f"Error al obtener información de Google Sheets: {str(e)}"
                    )
                    
            elif self.current_step == self.ESTADO_CREAR_CARPETAS:
                try:
                    # Preparar las referencias en el formato correcto
                    formatted_refs_for_creation = []
                    for ref in self.step_context['formatted_refs']:
                        formatted_refs_for_creation.append({
                            'original': ref['original'],
                            'nombre_formateado': ref['nombre_formateado']
                        })
                    
                    results = self.controller.folder_creation_manager.create_folders_and_copy_files(
                        formatted_refs_for_creation,
                        self.step_context.get('db_results', {})
                    )
                    
                    # Si hay archivos pendientes de selección
                    if results.get("pending_files"):
                        # Guardar información en el contexto
                        self.step_context["pending_files"] = results["pending_files"]
                        
                        # Tomar la primera referencia pendiente
                        ref_key = next(iter(results["pending_files"]))
                        self.pending_rhino_selection = {
                            "original": ref_key,
                            "pending_files": results["pending_files"],
                            **results["pending_files"][ref_key]
                        }
                        
                        self._transition_to_step(self.ESTADO_SELECCIONAR_RHINO)
                        # Iniciar el proceso secuencial para la primera referencia
                        self.process_single_reference()
                        return
                    
                    # Si no hay archivos pendientes, mostrar el resumen final
                    if results["processed"]:
                        self._show_final_summary(results)
                        self._transition_to_step(self.ESTADO_FINALIZADO)
                    else:
                        self.llm_response.emit(
                            "Sistema",
                            "No se pudo procesar ninguna referencia correctamente.",
                            True
                        )
                        self._transition_to_step(self.ESTADO_ERROR)

                except Exception as e:
                    logger.error(f"Error al crear carpetas: {str(e)}")
                    raise ProcessStepError(
                        "crear_carpetas",
                        f"Error al crear carpetas: {str(e)}"
                    )
                    
        except Exception as e:
            error_msg = self._handle_error(e)
            self.llm_response.emit("Sistema", error_msg, True)
            self.error_occurred.emit(self.current_step, str(e))
            self._transition_to_step(self.ESTADO_ERROR)

    def _handle_verification_response(self, accepted: bool):
        """Maneja la respuesta del usuario a la verificación de referencias."""
        self.controller.main_window.chat_panel.clear_action_buttons()
        if accepted:
            self._transition_to_step(self.ESTADO_BUSCAR_SHEETS)
            self.process_next_step()
        else:
            self.llm_response.emit("Sistema", "Proceso cancelado.", False)
            self._transition_to_step(self.ESTADO_FINALIZADO)

    def _handle_sheets_response(self, accepted: bool):
        """Maneja la respuesta del usuario a la confirmación de nombres formateados."""
        self.controller.main_window.chat_panel.clear_action_buttons()
        if accepted:
            self._transition_to_step(self.ESTADO_CREAR_CARPETAS)
            self.process_next_step()
        else:
            self.llm_response.emit("Sistema", "Proceso cancelado.", False)
            self._transition_to_step(self.ESTADO_FINALIZADO)

    def _open_result_folder(self, folder_path: str):
        """Abre la carpeta de resultados en el explorador."""
        try:
            import os
            os.startfile(folder_path)
        except Exception as e:
            self.llm_response.emit("Sistema", f"Error al abrir la carpeta: {str(e)}", True) 

    def _show_final_summary(self, results: Dict):
        """
        Muestra el resumen final del proceso de creación de carpetas.
        
        Args:
            results: Diccionario con los resultados del proceso
        """
        message = "Se han creado las carpetas y se han copiado los archivos:"
        
        if results["processed"]:
            for i, ref in enumerate(results["processed"]):
                message += "\n\n"  # Separación entre referencias
                
                if i > 0:
                    message += "---\n\n"  # Divisor entre referencias
                
                # Crear botón de carpeta
                folder_button = {
                    'text': f"📁 {ref['original']}",
                    'path': ref['target_folder'],
                    'type': 'folder'
                }
                message += f"<file_button>{folder_button}</file_button>"
                
                if ref['copied_files'].get('pdf'):
                    pdf_path = os.path.join(ref["target_folder"], ref['copied_files']["pdf"])
                    pdf_button = {
                        'text': f"📄 {ref['copied_files']['pdf']}",
                        'path': pdf_path,
                        'type': 'pdf',
                        'indent': True
                    }
                    message += f"\n<file_button>{pdf_button}</file_button>"
                    
                if ref['copied_files'].get('rhino'):
                    rhino_path = os.path.join(ref["target_folder"], ref['copied_files']["rhino"])
                    rhino_button = {
                        'text': f"🔧 {ref['copied_files']['rhino']}",
                        'path': rhino_path,
                        'type': 'rhino',
                        'indent': True
                    }
                    message += f"\n<file_button>{rhino_button}</file_button>"
        
        if results["errors"]:
            message += "\n\nErrores encontrados:\n"
            for error in results["errors"]:
                message += f'• {error}\n'
        
        self.llm_response.emit("Sistema", message, False)
        
        # Mostrar botón para abrir carpeta
        if results["processed"]:
            # Obtener la carpeta padre (2 niveles arriba)
            parent_folder = os.path.dirname(os.path.dirname(results["processed"][0]['target_folder']))
            actions = [
                {
                    'text': 'Abrir Carpeta',
                    'callback': lambda: self._open_result_folder(parent_folder)
                }
            ]
            self.controller.main_window.chat_panel.show_action_buttons(actions) 