# Buscador de Referencias - RTA

Este programa es una aplicación de escritorio que sirve como un "Buscador de Referencias" y permite buscar y visualizar archivos y carpetas basados en los códigos de referencia de los productos de RTA. Además, cuenta con una funcionalidad adicional para buscar imágenes similares a una imagen de referencia utilizando técnicas de procesamiento de imágenes.

## Características Principales

1. **Tabla de entrada de datos**: En esta tabla, puedes ingresar o pegar una lista de referencias que deseas buscar. Puedes hacerlo manualmente o copiar y pegar desde otras fuentes, como un chat o una hoja de cálculo. El programa procesa automáticamente las referencias ingresadas, normalizando su formato para garantizar resultados precisos.

2. **Selección múltiple de tipos de archivos**: Puedes seleccionar los tipos de archivos que deseas buscar:
   - Carpetas: Directorios que contienen información de productos
   - Imágenes: Archivos en formatos JPG, PNG, etc.
   - Videos: Archivos de video relacionados con los productos
   - Fichas Técnicas: Documentación técnica en PDF
   - Otros: Permite especificar extensiones personalizadas

3. **Selección múltiple de rutas de búsqueda**: 
   - Tienes la opción de especificar una o más rutas en las que se realizará la búsqueda
   - Rutas predefinidas por categorías (Ambientes, Baño, Cocina, etc.)
   - Capacidad de añadir rutas personalizadas
   - Optimización automática de rutas para evitar búsquedas redundantes

4. **Resultados organizados**: Los resultados de la búsqueda se muestran en una lista organizada, donde puedes ver:
   - Referencia del producto
   - Tipo de archivo encontrado
   - Nombre completo del archivo o carpeta
   - Ruta de ubicación
   - Estadísticas de archivos encontrados por tipo

5. **Opciones de interacción con los resultados**: 
   - Apertura directa de archivos o carpetas encontrados
   - Selección múltiple para operaciones en lote
   - Copiado de rutas o información completa
   - Exportación de resultados
   - Vista detallada con estadísticas por referencia
   - Filtrado y ordenamiento de resultados

6. **Búsqueda por imagen**: 
   - Carga de imágenes de referencia
   - Algoritmo de hash perceptual para encontrar similitudes
   - Ajuste de sensibilidad mediante umbral de reconocimiento
   - Optimización para diferentes tipos de imágenes
   - Visualización de porcentaje de similitud
   - Vista previa en tiempo real

7. **Actualización de Base de Datos**:
   - Interfaz dedicada para actualización de referencias
   - Proceso seguro mediante autenticación
   - Monitoreo en tiempo real del progreso
   - Registro detallado de cambios
   - Capacidad de cancelar el proceso

#### 📌 **Consideración Inicial:**
El programa es útil para encontrar múltiples archivos referencias específicas. **Para búsquedas de un solo archivo o nombre del mueble, es más conveniente usar el buscador del explorador de windows.**

## Instrucciones de Uso

### 1. **Ingreso de referencias**:
- Haz clic en el botón "`Pegar Información`" o presiona `Ctrl+V` para pegar una lista de referencias en la tabla de entrada de datos.

Es importante que la búsqueda incluya las LETRAS Y NÚMEROS al comienzo de la referencia. Recuerda que éste programa está orientado a encontrar referencias específicas y no los nombres generales del mueble.

Al pegar o escribir las referencias **no importará** si el nombre de la referencia que estamos buscando está escrito:

1. Con un espacio, (e.g): BLZ 6472
2. Todo junto, (e.g): BLZ6472
3. Con guiones, (e.g): BLZ 6472- , BLZ6472 -, BLZ-6472
4. Compartiendo el nombre de su archivo con otras referencias, (e.g): GLW 3201 - BLZ 6472 - GLB 4895 - INSTRUCTIVO

El programa tendrá la capacidad de localizarlo gracias a su algoritmo de normalización de texto y extracción de referencias.

- También puedes escribir manualmente las referencias que deseas buscar.
- Si necesitas eliminar algunas referencias, selecciona las filas correspondientes y haz clic en "`Borrar Selección`" o presiona la tecla `Suprimir`.
- Para borrar toda la información del programa, haz clic en "`Borrar Todo`".

### 2. **Selección de tipos de archivos**:
- Marca las casillas correspondientes a los tipos de archivos que deseas buscar:
  - **Carpetas**: Busca directorios que contengan la referencia
  - **Imágenes**: Incluye archivos JPG, PNG y otros formatos de imagen
  - **Videos**: Busca archivos de video relacionados
  - **Ficha Técnica**: Localiza documentación técnica en PDF
  - **Otro**: Permite especificar extensiones adicionales personalizadas

### 3. **Selección de rutas de búsqueda**:
- Haz clic en el botón "`Seleccionar ruta de búsqueda`" para elegir una ruta en la que se realizará la búsqueda.
- Puedes agregar más rutas haciendo clic en el botón "`+`".
- Si deseas eliminar una ruta, haz clic en el botón "`-`" al lado de la ruta correspondiente.
- El programa optimizará automáticamente las rutas para evitar búsquedas redundantes.

### 4. **Iniciar la búsqueda**:
- Una vez que hayas ingresado las referencias, seleccionado los tipos de archivos y las rutas de búsqueda, haz clic en el botón "`Buscar`" para iniciar el proceso.
- Durante la búsqueda, se mostrará:
  - Barra de progreso general
  - Progreso por ubicación (NAS/Base de datos)
  - Cantidad de archivos procesados
  - Tiempo estimado restante
  - Estado actual de la búsqueda

### La velocidad de búsqueda dependerá de 2 factores:

**1.** Principalmente de la velocidad de la NAS. Si la NAS presenta intermitencia o baja velocidad, esto se verá reflejado en la cantidad de tiempo de búsqueda.
        
No será lo mismo hacer la búsqueda con una conexión directa a las NAS (es decir, desde la oficina), que hacer la búsqueda con una conexión inalámbrica, como es el caso de la conexión a las NAS desde la casa. **Esto quiere decir, que la búsqueda desde casa será mucho más lenta, mientras que en la oficina será más rápida.** 

**2.** La cantidad de carpetas que el programa debe recorrer para encontrar las referencias. Esto lo podemos ver en la parte inferior del programa.

Se puede minimizar el programa mientras se realiza la búsqueda. Esto permite continuar trabajando en otras cosas sin afectar el funcionamiento del programa.

Si necesitas detener la búsqueda, puedes hacer clic nuevamente en el botón "`Detener búsqueda`" o presionar la tecla `Esc`.

### 5. **Visualización de resultados**:
- Los resultados de la búsqueda se mostrarán en una lista organizada con las siguientes características:
  - Agrupación por referencia
  - Conteo de archivos por tipo
  - Vista previa de imágenes
  - Indicadores de estado (encontrado/no encontrado)
  - Detalles de ubicación y tipo de archivo
- Las referencias para las cuales no se encontró ninguna información se resaltarán en rojo en la tabla superior.
- Puedes hacer doble clic en un resultado para abrir la carpeta o archivo correspondiente.
- Para seleccionar múltiples resultados, mantén presionada la tecla Ctrl y haz clic en los elementos deseados.
- Usa el checkbox "`Seleccionar todos`" para marcar o desmarcar todos los resultados.

### 6. **Interacción con los resultados**:
- Haz clic derecho sobre un resultado para acceder al menú contextual con opciones:
  - Copiar ruta de ubicación
  - Copiar información completa
  - Abrir ubicación del archivo
  - Ver detalles adicionales
- Haz clic en "`Abrir Selección`" para abrir los archivos o carpetas seleccionados.
- Haz clic en "`Crear Copia`" para copiar los elementos seleccionados en otra ubicación.
- Haz clic en "`Copiar REF encontradas`" o "`Copiar REF no encontradas`" para copiar las referencias correspondientes al portapapeles.
- Utiliza la ventana de detalles para ver estadísticas completas por referencia.

## 7. **Búsqueda por imagen**:
- Haz clic en el botón "`Buscar con Imagen`" para abrir una ventana adicional.
- Carga una imagen del mueble que deseas buscar.
- Ajusta el umbral de reconocimiento para ajustar el algoritmo de búsqueda. Para:
    1. Imagen de normal o menor resolución == utilizar umbral de reconocimiento =1 aprox.
    2. Imagen recortada == utilizar umbral de reconocimiento =6-10 aprox.
    3. Fondos Blanco: se encuentra en desarrollo de un algoritmo diferente. 
    4. Fondos blanco decorados: mayor posibilidad de ser identificado =1-6 aprox.
    5. **Selector tipo de imagen: No tiene ningún impacto aún.**
- El programa buscará archivos e imágenes relacionados con la imagen cargada.
- Los resultados se mostrarán con un porcentaje de similitud.
- Puedes previsualizar las imágenes encontradas en tiempo real.

## 8. **Actualización de la Base de Datos**:
- Accede a la función de actualización desde el menú principal
- Ingresa la contraseña de autorización
- Monitorea el proceso de actualización en tiempo real:
  - Progreso general
  - Archivos procesados
  - Cambios detectados
  - Logs detallados
- La actualización puede cancelarse en cualquier momento
- Se mantiene un registro de todas las actualizaciones realizadas

## Notas Adicionales:
- El programa utiliza una base de datos local para optimizar las búsquedas
- Se recomienda mantener la base de datos actualizada para mejores resultados
- Las búsquedas son independientes de mayúsculas/minúsculas
- El programa maneja automáticamente diferentes formatos de referencia
- Se incluye un sistema de caché para mejorar el rendimiento en búsquedas repetidas