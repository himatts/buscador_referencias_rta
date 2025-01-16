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

# Configurar logging
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
            self.ESTADO_CREAR_CARPETAS: [self.ESTADO_FINALIZADO, self.ESTADO_ERROR],
            self.ESTADO_ERROR: [
                self.ESTADO_VERIFICAR_REFERENCIAS,
                self.ESTADO_BUSCAR_SHEETS,
                self.ESTADO_CREAR_CARPETAS,
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
        
    def start_folder_creation_process(self, references: List[str]):
        """
        Inicia el proceso de creación de carpetas.
        
        Args:
            references: Lista de referencias a procesar
        """
        try:
            if not references:
                raise ProcessStepError(self.ESTADO_INICIAL, "No se proporcionaron referencias")
                
            self.current_references = references
            self.conversation_history = []
            self.error_recovery_attempts = {}
            self.current_step = self.ESTADO_INICIAL
            
            # Mensaje inicial del sistema
            welcome_message = (
                "¡Hola! Soy el asistente de RTA y te ayudaré en el proceso de "
                "creación de carpetas para las referencias. Primero, verificaré "
                "las referencias en la base de datos."
            )
            self.llm_response.emit("Sistema", welcome_message, False)
            
            # Transición al primer paso
            self._transition_to_step(self.ESTADO_VERIFICAR_REFERENCIAS)
            
            # Iniciar el proceso de verificación
            self.process_next_step()
            
        except Exception as e:
            error_msg = self._handle_error(e)
            self.llm_response.emit("Sistema", error_msg, True)
            self.error_occurred.emit("inicio", str(e))
        
    def handle_user_message(self, message: str):
        """
        Procesa un mensaje del usuario.
        
        Args:
            message: Contenido del mensaje del usuario
        """
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
                
            # Actualizar el costo en la interfaz
            self.controller.main_window.chat_panel.update_cost(
                self.llm_manager.get_session_cost()
            )
                
        except Exception as e:
            error_msg = self._handle_error(e)
            self.llm_response.emit("Sistema", error_msg, True)
            self.error_occurred.emit("mensaje_usuario", str(e))
            
        finally:
            # Indicar que el LLM terminó de procesar
            self.typing_status_changed.emit(False)
            
    def process_next_step(self):
        """
        Procesa el siguiente paso en el flujo de creación de carpetas.
        """
        try:
            if self.current_step == self.ESTADO_VERIFICAR_REFERENCIAS:
                # Obtener resultados de la búsqueda en base de datos
                db_results = self.controller.folder_creation_manager.search_in_database_only(self.current_references)
                
                # Clasificar referencias encontradas y no encontradas
                found_refs = []
                not_found_refs = []
                found_count = 0
                
                # Limpiar tabla de resultados y resultados anteriores
                self.controller.main_window.results.clear()
                self.controller.found_refs = set()
                self.controller.searched_refs = set(self.current_references)
                
                # Procesar y mostrar resultados en la tabla
                for ref in self.current_references:
                    paths = db_results.get(ref, [])
                    if paths:
                        found_refs.append(ref)
                        # Procesar cada ruta encontrada
                        for path in paths:
                            file_type = "Carpeta" if os.path.isdir(path) else "Archivo"
                            # Añadir a la tabla de resultados
                            self.controller.results_manager.add_result_item(
                                found_count,
                                path,
                                file_type,
                                ref
                            )
                        found_count += 1
                        self.controller.found_refs.add(ref)
                    else:
                        not_found_refs.append(ref)
                
                # Actualizar etiquetas y contadores
                self.controller.main_window.ref_info_label.setText(
                    f"Referencias encontradas: {len(found_refs)} | No encontradas: {len(not_found_refs)}"
                )
                
                # Actualizar contexto
                self.step_context = {
                    'found_refs': found_refs,
                    'not_found_refs': not_found_refs,
                    'total_refs': len(self.current_references),
                    'db_results': db_results
                }
                
                # Generar mensaje informativo para el chat
                message = f"He encontrado {len(found_refs)} referencias en la base de datos"
                if not_found_refs:
                    message += f" y {len(not_found_refs)} no fueron encontradas"
                message += ".\n\n"
                
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
                        self.step_context = {
                            'formatted_refs': [{
                                'original': ref['original'],
                                'nombre_formateado': ref['nombre_formateado'][0] if isinstance(ref['nombre_formateado'], tuple) else ref['nombre_formateado']
                            } for ref in refs_without_errors],
                            'db_results': self.step_context.get('db_results', {})
                        }
                        
                        logger.info(f"Contexto actualizado: {self.step_context}")
                        
                        # Generar mensaje con los nombres formateados
                        message = "He obtenido los siguientes nombres formateados:\n\n"
                        
                        # Primero mostrar las referencias exitosas
                        for ref in refs_without_errors:
                            nombre_formateado = ref['nombre_formateado'][0] if isinstance(ref['nombre_formateado'], tuple) else ref['nombre_formateado']
                            message += f"✓ Original: {ref['original']}\n"
                            message += f"  Formateado: {nombre_formateado}\n\n"
                        
                        # Luego mostrar las referencias con error
                        if refs_with_errors:
                            message += "Referencias con problemas:\n"
                            for ref in refs_with_errors:
                                message += f"⚠️ {ref['original']}: {ref['error']}\n"
                            message += "\n"
                        
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
                    else:
                        error_message = "No se pudo formatear ninguna referencia correctamente.\n\n"
                        if refs_with_errors:
                            error_message += "Errores encontrados:\n"
                            for ref in refs_with_errors:
                                error_message += f"⚠️ {ref['original']}: {ref['error']}\n"
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
                # Crear carpetas y copiar archivos
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
                    
                    # Generar mensaje de resumen
                    message = "Se han creado las carpetas y se han copiado los archivos:\n\n"
                    
                    if results["processed"]:
                        for ref in results["processed"]:
                            message += f"✓ {ref['original']}:\n"
                            message += f"  Carpeta: {ref['target_folder']}\n"
                            if ref['copied_files'].get('pdf'):
                                message += f"  PDF: {ref['copied_files']['pdf']}\n"
                            if ref['copied_files'].get('rhino'):
                                message += f"  Rhino: {ref['copied_files']['rhino']}\n"
                            message += "\n"
                    
                    if results["errors"]:
                        message += "\nErrores encontrados:\n"
                        for error in results["errors"]:
                            message += f"✗ {error}\n"
                    
                    self.llm_response.emit("Sistema", message, False)
                    
                    # Mostrar botón para abrir carpeta
                    if results["processed"]:
                        actions = [
                            {
                                'text': 'Abrir Carpeta',
                                'callback': lambda: self._open_result_folder(results["processed"][0]['target_folder'])
                            }
                        ]
                        self.controller.main_window.chat_panel.show_action_buttons(actions)
                    
                    self._transition_to_step(self.ESTADO_FINALIZADO)
                    
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