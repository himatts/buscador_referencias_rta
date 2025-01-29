"""
Nombre del Archivo: webScrapingManager.py
Descripción: Gestor que maneja la automatización web con Selenium para la descarga
             de hojas de diseño desde la página web de RTA.

Autor: RTA Muebles - Área Soluciones IA
Fecha de Última Modificación: 2024
Versión: 1.0
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    ElementNotInteractableException
)
from webdriver_manager.chrome import ChromeDriverManager
from utils.helpers import extract_reference  # Importar la función extract_reference
import logging
import time
import csv
import os
import re
from typing import List, Dict, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_scraping.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WebScrapingManager:
    """
    Gestor que maneja la automatización web con Selenium.
    """
    
    def __init__(self, config):
        """
        Inicializa el gestor de web scraping.
        
        Args:
            config: Objeto de configuración con credenciales
        """
        self.config = config
        self.driver = None
        self._is_running = False

    def initialize_driver(self):
        """Inicializa el driver de Chrome con las opciones necesarias."""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-extensions")
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            self.driver.implicitly_wait(0)  # Establecer espera implícita a 0
            logger.info("Driver de Chrome inicializado correctamente")
            return True
        except Exception as e:
            logger.error(f"Error al inicializar el driver: {str(e)}")
            return False

    def login(self) -> bool:
        """
        Realiza el inicio de sesión en la página web.
        
        Returns:
            bool: True si el login fue exitoso, False en caso contrario
        """
        try:
            self.driver.get("https://app.rta.com.co/diseno/#/login")
            logger.info("Página de login abierta")

            # Esperar y llenar campo de usuario
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'login-username'))
            )
            username_field.clear()
            username_field.send_keys(self.config.get_web_email())
            logger.info("Email ingresado")

            # Llenar campo de contraseña
            password_field = self.driver.find_element(By.ID, 'login-password')
            password_field.clear()
            password_field.send_keys(self.config.get_web_password())
            logger.info("Contraseña ingresada")

            # Click en botón de login
            login_button = self.driver.find_element(By.XPATH, '//button[@ng-click="login(credentials)"]')
            login_button.click()
            logger.info("Botón de login clickeado")

            # Esperar a que se cargue el elemento que indica login exitoso
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//a[@href="#/historicoDisenos"]'))
            )
            logger.info("Login exitoso")
            return True

        except Exception as e:
            logger.error(f"Error en el login: {str(e)}")
            return False

    def navigate_to_historico(self) -> bool:
        """
        Navega a la sección de histórico de diseños.
        
        Returns:
            bool: True si la navegación fue exitosa, False en caso contrario
        """
        try:
            historico_button = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, '//a[@href="#/historicoDisenos"]'))
            )
            historico_button.click()
            logger.info("Navegado a 'Histórico de Diseños'")

            # Esperar a que se cargue el campo de búsqueda
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//input[@ng-model="objRefenciaMueble.nombreProyectoDiseno"]'))
            )
            logger.info("Página de histórico cargada correctamente")
            return True

        except Exception as e:
            logger.error(f"Error al navegar al histórico: {str(e)}")
            return False

    def search_reference(self, reference: str) -> bool:
        """
        Busca una referencia en el histórico.
        
        Args:
            reference: Referencia a buscar (formato: letras + número)
            
        Returns:
            bool: True si la búsqueda fue exitosa, False en caso contrario
        """
        try:
            # Utilizar la función extract_reference para obtener la referencia en formato correcto
            search_term = extract_reference(reference)
            if not search_term:
                search_term = reference
                
            logger.info(f"Buscando con el término: {search_term}")

            # Esperar y llenar campo de búsqueda
            search_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//input[@ng-model="objRefenciaMueble.nombreProyectoDiseno"]'))
            )
            search_field.clear()
            time.sleep(1)  # Esperar a que se limpie el campo
            search_field.send_keys(search_term)
            logger.info(f"Referencia '{search_term}' ingresada en el campo de búsqueda")

            # Click en botón de búsqueda
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@ng-click="buscarMueblebyDiseno()"]'))
            )
            search_button.click()
            logger.info(f"Búsqueda iniciada para referencia '{search_term}'")

            # Esperar resultados o mensaje de no resultados
            try:
                WebDriverWait(self.driver, 2).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, '//button[@ng-click="verHojaDiseno(item)"]')),
                        EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "No se encontraron resultados")]'))
                    )
                )
                logger.info(f"[{search_term}] Una de las condiciones ha sido cumplida")
            except TimeoutException:
                logger.warning(f"[{search_term}] TimeoutException: No se encontraron condiciones")
                return False

            # Determinar cuál condición se cumplió
            try:
                # Verificar si el mensaje de 'No se encontraron resultados' está presente
                self.driver.find_element(By.XPATH, '//div[contains(text(), "No se encontraron resultados")]')
                logger.info(f"[{search_term}] Confirmado: No se encontraron resultados")
                return False
            except NoSuchElementException:
                # Si no se encontró el mensaje, verificar si el botón de resultados está presente
                logger.info(f"[{search_term}] Confirmado: Se encontraron resultados")
                return True

        except Exception as e:
            logger.error(f"Error en la búsqueda de referencia '{reference}': {str(e)}")
            return False

    def process_design_sheet(self, reference: str, target_folder: str) -> bool:
        """
        Procesa la hoja de diseño de una referencia y extrae los datos a un archivo CSV.
        Extrae tanto la tabla de Piezas Mueble como la de Componentes.
        
        Args:
            reference: Referencia a procesar
            target_folder: Carpeta donde guardar el archivo CSV
            
        Returns:
            bool: True si el procesamiento fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"[{reference}] Procesando hoja de diseño")
            inicio_procesamiento = time.time()

            # Encontrar y hacer clic en el primer botón de hoja de diseño
            botones_hoja_diseno = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//button[@ng-click="verHojaDiseno(item)"]'))
            )
            if not botones_hoja_diseno:
                logger.warning(f"[{reference}] No se encontraron hojas de diseño")
                return False

            # Hacer clic en el primer botón
            self.driver.execute_script("arguments[0].scrollIntoView();", botones_hoja_diseno[0])
            botones_hoja_diseno[0].click()
            logger.info(f"[{reference}] Botón 'Ver Hoja de Diseño' clickeado")

            # Esperar a que el modal esté presente y visible
            try:
                modal = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "modal-dialog"))
                )
                # Esperar a que el modal sea visible y esté completamente cargado
                WebDriverWait(self.driver, 10).until(
                    EC.visibility_of(modal)
                )
                logger.info(f"[{reference}] Modal de hoja de diseño cargado")
            except TimeoutException:
                logger.error(f"[{reference}] Tiempo de espera excedido al cargar el modal")
                raise Exception("No se pudo cargar el modal de la hoja de diseño")

            # Primero expandir específicamente la sección de Piezas mueble
            try:
                # Usar el XPath específico para la sección de Piezas mueble
                piezas_header = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "/html/body/div[2]/div/div/div[3]/div[2]/div[1]/div/div[2]/div/div[3]/div/div[1]/h3"
                    ))
                )
                
                # Hacer scroll hasta el elemento
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", piezas_header)
                time.sleep(1)  # Esperar a que termine el scroll
                
                # Verificar si la sección ya está expandida
                aria_expanded = piezas_header.get_attribute('aria-expanded')
                if aria_expanded != 'true':
                    # Intentar click con JavaScript si el click normal falla
                    try:
                        piezas_header.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", piezas_header)
                    time.sleep(1)  # Esperar a que se expanda
                    logger.info(f"[{reference}] Sección de Piezas mueble expandida")
                else:
                    logger.info(f"[{reference}] Sección de Piezas mueble ya estaba expandida")
                
                # Verificar que la sección se expandió correctamente
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//div[contains(@class, 'collapse in')]//table[contains(@class, 'table-bordered')]"
                    ))
                )
                
            except Exception as e:
                logger.error(f"[{reference}] Error al expandir sección de Piezas mueble: {str(e)}")
                raise Exception("No se pudo expandir la sección de Piezas mueble")

            # Luego expandir las demás secciones necesarias
            otras_secciones = [
                ('collapseTabla1', '//h3[contains(@aria-controls, "collapseTabla1")]'),
                ('collapseTabla2', '//h3[contains(@aria-controls, "collapseTabla2")]'),
                ('collapseComponentes', '//h3[contains(@aria-controls, "collapseComponentes")]')
            ]

            for seccion_id, xpath in otras_secciones:
                try:
                    menu = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", menu)
                    time.sleep(1)
                    
                    aria_expanded = menu.get_attribute('aria-expanded')
                    if aria_expanded != 'true':
                        try:
                            menu.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", menu)
                        time.sleep(1)
                        logger.info(f"[{reference}] Menú '{seccion_id}' expandido")
                    else:
                        logger.info(f"[{reference}] Menú '{seccion_id}' ya estaba expandido")
                        
                except Exception as e:
                    logger.warning(f"[{reference}] No se pudo expandir el menú '{seccion_id}': {str(e)}")

            # 1. Procesar tabla de Piezas Mueble
            piezas_data = []
            headers = []
            try:
                logger.info(f"[{reference}] Intentando localizar la tabla de Piezas Mueble...")
                
                # Intentar encontrar la tabla usando el XPath específico
                piezas_table = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//div[contains(@class, 'collapse in')]//table[contains(@class, 'table-bordered')]"
                    ))
                )
                
                if not piezas_table:
                    # Intentar selectores alternativos si el principal falla
                    tabla_selectors = [
                        '//div[@id="collapsePiezas"]//table',
                        '//table[contains(@class, "table-hover") and contains(@class, "table-condensed")]',
                        '//div[contains(@id, "collapse")]//table[contains(@class, "table-bordered")]'
                    ]
                    
                    for selector in tabla_selectors:
                        try:
                            piezas_table = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, selector))
                            )
                            if piezas_table:
                                logger.info(f"[{reference}] Tabla encontrada con selector alternativo: {selector}")
                                break
                        except:
                            continue

                if not piezas_table:
                    raise Exception("No se pudo encontrar la tabla de Piezas Mueble")

                logger.info(f"[{reference}] Tabla de Piezas Mueble encontrada, procediendo a extraer datos...")

                # Obtener encabezados
                header_cells = piezas_table.find_elements(By.TAG_NAME, 'th')
                if header_cells:
                    # Procesar encabezados de la tabla principal como en el plugin
                    raw_headers = [cell.text.strip() for cell in header_cells]
                    logger.info(f"[{reference}] Encabezados encontrados: {raw_headers}")
                    
                    # Mapear encabezados exactamente como en el plugin
                    headers = []
                    for i, header in enumerate(raw_headers):
                        if i == 9:
                            headers.append('Canto Largo 1')
                        elif i == 10:
                            headers.append('Canto Largo 2')
                        elif i == 11:
                            headers.append('Canto Corto 1')
                        elif i == 12:
                            headers.append('Canto Corto 2')
                        else:
                            headers.append(header)
                    
                    # Filtrar encabezados no deseados
                    headers = [h for h in headers if h not in ['', 'Pre', 'Opciones']]
                    logger.info(f"[{reference}] Encabezados procesados: {headers}")
                    
                    # Obtener índices importantes
                    pieza_index = headers.index('Pieza') if 'Pieza' in headers else -1
                    letra_index = headers.index('Letra') if 'Letra' in headers else -1
                    
                    if pieza_index == -1 or letra_index == -1:
                        logger.error(f"[{reference}] No se encontraron las columnas 'Pieza' y/o 'Letra'")
                        return False

                # Procesar filas de datos de la tabla principal
                rows = piezas_table.find_elements(By.TAG_NAME, 'tr')[1:]  # Excluir fila de encabezados
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 13:
                        # Mapear datos como en el plugin
                        row_data = []
                        for i, cell in enumerate(cells):
                            if i in [0, 1, 13, 14]:
                                continue
                            text = cell.text.strip()
                            # Eliminar paréntesis vacíos y espacios
                            text = re.sub(r'\s*\(\s*\)\s*$', '', text).strip()
                            row_data.append(text)
                        
                        # Filtrar datos nulos
                        row_data = [x for x in row_data if x is not None]
                        
                        # Verificar precorte
                        pieza_text = row_data[pieza_index].lower() if len(row_data) > pieza_index else ''
                        if any(x in pieza_text for x in ['precorte', 'pre-corte', 'pre corte']):
                            continue
                        
                        # Limpiar formato de Letra
                        if len(row_data) > letra_index:
                            row_data[letra_index] = re.sub(r'\s*\(P-\d+\)', '', row_data[letra_index]).strip()
                        
                        # Agregar los datos sin comillas adicionales
                        piezas_data.append(row_data)
                
                logger.info(f"[{reference}] Datos de Piezas Mueble extraídos exitosamente: {len(piezas_data)} filas")
            except Exception as e:
                logger.error(f"[{reference}] Error al procesar tabla de Piezas Mueble: {str(e)}")
                logger.error(f"[{reference}] Detalles del error: {type(e).__name__}")

            # 2. Procesar tabla de Componentes
            componentes_data = []
            try:
                componentes_table = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="collapseComponentes"]//table'))
                )
                
                if componentes_table:
                    componentes_rows = componentes_table.find_elements(By.TAG_NAME, 'tr')
                    
                    if len(componentes_rows) > 0:
                        # Procesar encabezados de componentes como en el plugin
                        componentes_headers = ['Referencia', 'Descripcion', 'Cantidad']
                        
                        # Procesar filas de datos
                        for row in componentes_rows[1:]:  # Saltar la fila de encabezados
                            cells = row.find_elements(By.TAG_NAME, 'td')
                            if len(cells) >= 4:
                                row_data = [
                                    cells[1].text.strip(),  # Referencia
                                    cells[2].text.strip(),  # Descripcion
                                    cells[3].text.strip()   # Cantidad
                                ]
                                componentes_data.append(row_data)
                
                logger.info(f"[{reference}] Datos de Componentes extraídos exitosamente: {len(componentes_data)} filas")
            except Exception as e:
                logger.error(f"[{reference}] Error al procesar tabla de Componentes: {str(e)}")

            # 3. Combinar y guardar datos en CSV
            if piezas_data or componentes_data:
                nombre_archivo = os.path.join(target_folder, f'hoja_diseno_{reference}.csv')
                with open(nombre_archivo, 'w', newline='', encoding='utf-8') as archivo_csv:
                    escritor_csv = csv.writer(archivo_csv)
                    
                    # Escribir sección de Piezas Mueble
                    if headers and piezas_data:
                        escritor_csv.writerow(headers)
                        escritor_csv.writerows(piezas_data)
                        logger.info(f"[{reference}] Datos de Piezas Mueble escritos en CSV")
                    
                    # Agregar separación entre tablas
                    escritor_csv.writerow([])
                    escritor_csv.writerow(['Componentes'])
                    
                    # Escribir sección de Componentes
                    if componentes_data:
                        escritor_csv.writerow(componentes_headers)
                        escritor_csv.writerows(componentes_data)
                        logger.info(f"[{reference}] Datos de Componentes escritos en CSV")
                
                logger.info(f"[{reference}] Datos exportados a '{nombre_archivo}'")
            else:
                logger.warning(f"[{reference}] No se encontraron datos para exportar")

            # Cerrar la ventana emergente y restablecer estado
            self.close_popup()
            self.reset_estado()

            fin_procesamiento = time.time()
            tiempo_total = fin_procesamiento - inicio_procesamiento
            logger.info(f"[{reference}] Procesamiento completado en {tiempo_total:.2f} segundos")

            return True

        except Exception as e:
            logger.error(f"[{reference}] Error al procesar hoja de diseño: {str(e)}")
            self.close_popup()
            self.reset_estado()
            return False

    def close_popup(self):
        """Cierra la ventana emergente de la hoja de diseño."""
        try:
            boton_cerrar = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//span[@aria-hidden="true"]'))
            )
            boton_cerrar.click()
            logger.info("Ventana emergente cerrada")
        except Exception as e:
            logger.error(f"Error al cerrar ventana emergente: {str(e)}")

    def clear_search(self):
        """Limpia el campo de búsqueda."""
        try:
            boton_limpiar = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@ng-click="limpiar()"]'))
            )
            boton_limpiar.click()
            logger.info("Botón limpiar clickeado")

            # Esperar a que se limpie el campo de búsqueda
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.find_element(By.XPATH, '//input[@ng-model="objRefenciaMueble.nombreProyectoDiseno"]').get_attribute('value') == ''
            )
            logger.info("Búsqueda limpiada")
            
        except Exception as e:
            logger.error(f"Error al limpiar búsqueda: {str(e)}")
            self.reset_estado()

    def reset_estado(self):
        """
        Restablece el estado de la página navegando de nuevo a 'Histórico de Diseños'.
        Esto asegura que la página esté en un estado limpio para la siguiente búsqueda.
        """
        try:
            logger.info("Restableciendo el estado de la página para la siguiente búsqueda")
            self.navigate_to_historico()
        except Exception as e:
            logger.error(f"Error al restablecer el estado de la página: {str(e)}")

    def stop(self):
        """Detiene la ejecución del web scraping."""
        self._is_running = False
        if self.driver:
            self.driver.quit()
            self.driver = None 