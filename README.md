## Buscador de Referencias - RTA

Este programa es una aplicación de escritorio que sirve como un "Buscador de Referencias" y permite buscar y visualizar archivos y carpetas basados en los códigos de referencia de los productos de RTA. Además, cuenta con una funcionalidad adicional para buscar imágenes similares a una imagen de referencia utilizando técnicas de procesamiento de imágenes.

<br>

![alt](.git\imgs\gui_buscador_referencias_rta.png)

## Características Principales

1. **Tabla de entrada de datos**: En esta tabla, puedes ingresar o pegar una lista de referencias que deseas buscar. Puedes hacerlo manualmente o copiar y pegar desde otras fuentes, como un chat o una hoja de cálculo.
2. **Selección múltiple de tipos de archivos**: Puedes seleccionar los tipos de archivos que deseas buscar, como carpetas, imágenes, videos o fichas técnicas.
3. **Selección múltiple de rutas de búsqueda**: Tienes la opción de especificar una o más rutas en las que se realizará la búsqueda, lo que te permite abarcar diferentes ubicaciones donde pueda encontrarse la información.
4. **Resultados organizados**: Los resultados de la búsqueda se muestran en una lista organizada, donde puedes ver la referencia, el tipo de archivo, el nombre completo del archivo o carpeta y la ruta de ubicación.
5. **Opciones de interacción con los resultados**: Puedes abrir directamente los archivos o carpetas encontrados, seleccionar múltiples resultados para copiarlos o compartir su información, y copiar las referencias encontradas o no encontradas al portapapeles.
6. **Búsqueda por imagen**: Además de buscar por referencias, el programa también te permite cargar una imagen de un mueble y buscar archivos o carpetas relacionados con esa imagen.

<br>

<aside>

📌 **Consideración Inicial:**
El programa es útil para encontrar múltiples archivos referencias específicas. **Para búsquedas de un solo archivo o nombre del mueble, es más conveniente usar el buscador del explorador de windows.**

</aside>

<br>

## Instrucciones de Uso

1. **Ingreso de referencias**:
    - Haz clic en el botón "`Pegar Información`" o presiona `Ctrl+V` para pegar una lista de referencias en la tabla de entrada de datos.
    
    <br>
    
    <aside>

        Es importante que la búsqueda incluya las LETRAS Y NÚMEROS al comienzo de la referencia. Recuerda que éste programa está orientado a encontrar referencias específicas y no los nombres generales del mueble.
    
    </aside>
    
    <br>
    
    **Ejemplo 1:** Copiar información de una **Lista**, y pegarla en el programa usando el botón “`Pegar Información`”.
    

    
    ![pegar_info_01.gif](.git/imgs/pegar_info_01.gif)
    
    <aside>

    <br>

    📌 Al pegar o escribir las referencias **no importará** si el nombre de la referencia que estamos buscando está escrito:
    
    1. Con un espacio, (e.g): BLZ 6472
    2. Todo junto, (e.g): BLZ6472
    3. Con guiones, (e.g): BLZ 6472- , BLZ6472 -, BLZ-6472
    4. Compartiendo el nombre de su archivo con otras referencias, (e.g): GLW 3201 - BLZ 6472 - GLB 4895 - INSTRUCTIVO
    
    El programa tendrá la capacidad de localizarlo.
    
    </aside>
    
    <br>

    **Ejemplo 2:** Copiar información de una **Tabla**, y pegarla en el programa usando `Control + V`.
    
    ![pegar_info_02.gif](.git/imgs/pegar_info_02.gif)

    <br>
    
    - También puedes escribir manualmente las referencias que deseas buscar.
    
    ![pegar_info_03.gif](.git/imgs/pegar_info_03.gif)
    
    - Si necesitas eliminar algunas referencias, selecciona las filas correspondientes y haz clic en "`Borrar Selección`" o presiona la tecla `Suprimir`.
    - Para borrar toda la información del programa, haz clic en "`Borrar Todo`".

    <br>
    
    ![pegar_info_04.gif](.git/imgs/pegar_info_04.gif)

<br>

2. **Selección de tipos de archivos**:
- Marca las casillas correspondientes a los tipos de archivos que deseas buscar, como carpetas, imágenes, videos o fichas técnicas.
    
<center>

<img src=".git/imgs/selection_01.png" alt="drawing" width="300"/> <img src=".git/imgs/selection_02.png" alt="drawing" width="300"/>

</center>

<br>
    
3. **Selección de rutas de búsqueda**:
    - Haz clic en el botón "`Seleccionar ruta de búsqueda`" para elegir una ruta en la que se realizará la búsqueda.
    - Puedes agregar más rutas haciendo clic en el botón "`+`".
    - Si deseas eliminar una ruta, haz clic en el botón "`-`" al lado de la ruta correspondiente.
    
    <center>

    <img src=".git/imgs/path_01.png" alt="drawing" width="300"/> <img src=".git/imgs/path_02.png" alt="drawing" width="300"/>

    </center>

<br>

4. **Iniciar la búsqueda**:
    - Una vez que hayas ingresado las referencias, seleccionado los tipos de archivos y las rutas de búsqueda, haz clic en el botón "`Buscar`" para iniciar el proceso.
    - Durante la búsqueda, se mostrará una barra de progreso y un indicador de estado.

    ![Untitled](.git/imgs/progress_bar.png)
    
    <br>

    ### La velocidad de búsqueda dependerá de 2 factores:
    
    <b>1.</b> Principalmente de la velocidad de la NAS. Si la NAS presenta intermitencia o baja velocidad, esto se verá reflejado en la cantidad de tiempo de búsqueda.
            
    No será lo mismo hacer la búsqueda con una conexión directa a las NAS (es decir, desde la oficina), que hacer la búsqueda con una conexión inalámbrica, como es el caso de la conexión a las NAS desde la casa. **Esto quiere decir, que la búsqueda desde casa será mucho más lenta, mientras que en la oficina será más rápida.** 

    <br>
            
    <b>2.</b> La cantidad de carpetas que el programa debe recorrer para encontrar las referencias. Esto lo podemos ver en la parte inferior del programa.

    <br>
        
        Se puede minimizar el programa mientras se realiza la búsqueda. Esto permite continuar trabajando en otras cosas sin afectar el funcionamiento del programa.
    
    - Si necesitas detener la búsqueda, puedes hacer clic nuevamente en el botón "`Detener búsqueda`" o presionar la tecla `Esc`.

<br>
    
### 5. **Visualización de resultados**:
   - Los resultados de la búsqueda se mostrarán en una lista organizada.
   - Las referencias para las cuales no se encontró ninguna información se resaltarán en rojo en la tabla superior.
   - Puedes hacer doble clic en un resultado para abrir la carpeta o archivo correspondiente.
   - Para seleccionar múltiples resultados, mantén presionada la tecla Ctrl y haz clic en los elementos deseados.
   - Usa el checkbox "`Seleccionar todos`" para marcar o desmarcar todos los resultados.
    
![Untitled](.git/imgs/resultados.png)


    
### 6. **Interacción con los resultados**:
   - Haz clic derecho sobre un resultado para abrir un menú contextual que te permitirá copiar la ruta de ubicación o la información completa del resultado.
   - Haz clic en "`Abrir Selección`" para abrir los archivos o carpetas seleccionados.
   - Haz clic en "`Crear Copia`" para copiar los elementos seleccionados en otra ubicación.
   - Haz clic en "`Copiar REF encontradas`" o "`Copiar REF no encontradas`" para copiar las referencias correspondientes al portapapeles.
    
## 7. **Búsqueda por imagen**:

   <center>

   <img src=".git/imgs/img_search_02.png" alt="drawing" width="600"/> 
    
   <img src=".git/imgs/img_search_02.png" alt="drawing" width="300"/> <img src=".git/imgs/img_search_03.png" alt="drawing" width="300"/>

   </center>
    
   - Haz clic en el botón "`Buscar con Imagen`" para abrir una ventana adicional.
   - Carga una imagen del mueble que deseas buscar.
   - Ajusta el umbral de reconocimiento para ajustar el algoritmo de búsqueda. Para:
        1. Imagen de normal o menor resolución == utilizar umbral de reconocimiento =1 aprox.
        2. Imagen recortada == utilizar umbral de reconocimiento =6-10 aprox.
        3. Fondos Blanco: se encuentra en desarrollo de un algoritmo diferente. 
        4. Fondos blanco decorados: mayor posibilidad de ser identificado =1-6 aprox.
        5. **Selector tipo de imagen: No tiene ningún impacto aún.**
   - El programa buscará archivos e imágenes relacionados con la imagen cargada.