# Especificación: migración de reservas desde planillas

Fecha: 9 de octubre de 2026  
Rama: `feature/importacion-reservas`  
Estado: diseño conversacional aprobado; especificación pendiente de revisión.

## Objetivo y alcance

Agregar al PMS local un módulo administrativo para cargar reservas desde Excel,
revisar la interpretación y aplicar un lote de altas y actualizaciones.
Funcionará dentro de la red del hotel, sin servicios externos.
Conservará observaciones y colores de origen y permitirá exportar un CSV
normalizado que mantenga esos datos como columnas explícitas.

La primera versión acepta archivos `.xlsx` con calendario mensual y CSV
normalizado. No acepta archivos `.xls`, macros ni CSV exportado directamente
de una cuadrícula mensual. Ese CSV carece de las notas y los formatos
necesarios para esta migración.

El flujo aprobado es: cargar → vincular camas → revisar → aplicar.
Subir o analizar un archivo no cambia las reservas del PMS.

## Formato conocido y fechas

La planilla examinada contiene dos hojas mensuales, AGO-26 y SEP-26,
días en columnas y unidades en filas. Hay etiquetas de camas, como
`2-a`, y etiquetas de habitaciones privadas. Los encabezados diarios se
repiten entre grupos de habitaciones. También existe una leyenda de colores.

El usuario confirmó que una celda con el huésped representa una noche:
ocupación del 10 al 12 implica llegada el 10 y salida el 13.

El administrador seleccionará las hojas a procesar y confirmará mes y año.
Se conservarán las fechas originales; no se trasladarán a la fecha actual.
Las hojas cuyo período no pueda identificarse requieren una selección
explícita antes de analizar reservas.

Se agrupan celdas consecutivas con el mismo nombre en una misma unidad.
Un cambio de color durante esa secuencia no crea por sí solo otra reserva.
Los casos ambiguos se marcan para revisión. Unir estadías entre hojas
contiguas exige confirmar la continuidad; no se unen personas entre camas
distintas solo por compartir un nombre. Los cambios de habitación se
presentan como tramos separados con su información de origen.

Las celdas rojas de salida no representan una noche adicional.
Si contienen un nombre o contradicen la continuidad de la estadía,
se pide corregir las fechas en la vista previa.
Las reservas que tocan el principio o fin del período disponible muestran
una advertencia de posible estadía incompleta.

## Inventario y configuración

Cada etiqueta de origen se vincula a una unidad existente del PMS.
Las sugerencias por nombre requieren confirmación.
Las unidades desactivadas y las filas sin vincular bloquean su importación.

El módulo no crea automáticamente habitaciones ni modifica sus tarifas.
Las unidades faltantes se cargan desde la configuración actual del PMS
y luego se vuelve a la vinculación.
La asociación confirmada se conserva en un perfil local reutilizable.
No se cambia el inventario de demostración para hacerlo coincidir
automáticamente con una planilla real.

El perfil permite configurar las hojas, sus períodos, las filas de unidades,
la fila de días y la leyenda. La detección inicial ofrece valores sugeridos;
la configuración permite adaptar el formato a otros hoteles.

## Notas, colores y procedencia

Se conserva el texto completo de las notas de celda.
Las observaciones importadas indican hoja y celda de origen.
Un mismo texto repetido dentro de una estadía se muestra una vez,
con todas sus referencias de procedencia.

Las notas de etiquetas y celdas vacías no se asignan silenciosamente
a un huésped. Se muestran en una lista de pendientes para vincularlas
manualmente a una reserva o excluirlas con una decisión registrada.
El lote no puede aplicarse mientras existan notas sin resolver.

Se conserva el color efectivo de cada celda relevante como hexadecimal
y su referencia original. La leyenda conocida incluye:

| Color | Significado original |
| --- | --- |
| #FF0000 | Check out |
| #0070C0 | Cambio de habitación: sale |
| #FF00FF | Cambio de habitación: entra |
| #C6EFCE | Pagado |
| #FFE598 | Falta pagar |
| #00FF00 | Llegó; falta entregar llave |
| #00FFFF | Pedido especial |
| #00B0F0 | Agencia |
| #FFFF00 | Llegó; no pagó y falta entregar llave |
| #6D9EEB | Liquidado Despegar |
| #9900FF | Pagado Despegar |

Otros colores quedan visibles como «sin significado confirmado».
Los colores y las notas son información de origen. No generan cobros,
cargos, check-in, tareas de limpieza ni cambios de estado automáticamente.
El administrador confirma el estado de cada reserva en la revisión.
Solo se permite «alojado» si la fecha actual cae dentro de la estadía.
Importar una reserva finalizada no inventa horas de check-in o check-out.

## Vista previa y actualización

Cada fila revisable muestra huésped, unidad, llegada, salida, noches,
estado propuesto, observaciones, colores y celdas de origen.
Permite corregir nombres, fechas, estado y asociación de unidad;
también excluir una fila antes de aplicar.

Las acciones visibles son «crear», «actualizar», «sin cambios»,
«conflicto» y «requiere revisión».
Se muestra el antes y después de cada actualización.

Cada reserva migrada recibe un identificador estable dentro de su perfil.
El archivo idéntico y la repetición del mismo lote no duplican reservas.
En futuras cargas se reutilizan las asociaciones ya confirmadas.
Si una modificación del calendario impide reconocer con certeza una
reserva, se exige una vinculación explícita; el nombre del huésped no es
una clave única. Las reservas creadas manualmente requieren selección
explícita para recibir datos importados.

No se borran ni cancelan reservas porque falten en una nueva planilla.
No se reemplazan cobros, cargos ni notas escritas manualmente.
Las observaciones importadas se conservan por separado de las manuales,
de modo que una actualización no las borre ni las duplique.

Cambios de fechas, unidades o estado incompatibles con una estadía operativa
se bloquean para resolverse desde el flujo normal del PMS.
Un conflicto de disponibilidad no se resuelve sobrescribiendo otra reserva.

## Cuentas y datos faltantes

No se convierten palabras como «pagado» ni importes encontrados en notas
en movimientos contables automáticos.
Las reservas migradas conservan esa información en sus observaciones.

La ausencia de tarifa o saldo no significa importe cero.
La reserva muestra «cuenta pendiente de revisión» hasta que recepción
confirme sus cargos y cobros mediante el flujo de facturación existente.
La importación de datos en una reserva existente conserva su cuenta actual.
Si cambian fechas o unidades, su cuenta queda pendiente de revisión
para que recepción concilie el alojamiento sin modificar movimientos existentes.

## Aplicación y concurrencia

El administrador elige las filas resueltas y ve un resumen final.
Aplicar exige una confirmación dentro del PMS.
Un lote con filas seleccionadas inválidas no puede aplicarse.

Antes de guardar se vuelven a validar las reservas, la disponibilidad,
los bloqueos de mantenimiento y las unidades activas.
Si otro usuario modificó una reserva desde la vista previa,
se invalida esa actualización y se solicita volver a revisar.

El lote se aplica en una única transacción de PostgreSQL.
Se reutilizan el orden de bloqueo y las restricciones de disponibilidad
del PMS. Un error revierte todos los cambios del lote seleccionado.
Repetir la confirmación no vuelve a aplicar un lote ya completado.

El registro del lote conserva usuario, fecha, perfil, huella del archivo,
acciones y reservas afectadas. Los borradores pueden descartarse.
Los datos y archivos de huéspedes se mantienen fuera del repositorio público.

## CSV normalizado

La exportación contiene una fila por reserva y encabezados en español:
`id_origen`, `huésped`, `unidad_origen`, `llegada`, `salida`,
`estado`, `observaciones`, `colores` y `referencias`.
Las fechas usan YYYY-MM-DD y el archivo usa UTF-8.
Colores y referencias admiten una lista JSON dentro de la celda CSV.

La importación CSV valida ese contrato e identifica filas mediante
`id_origen` dentro del perfil. No ejecuta fórmulas.
La exportación protege los campos de texto que pudieran interpretarse
como fórmulas al abrirlos en una hoja de cálculo y documenta esa protección.

## Componentes e integración

Una aplicación Django separada contiene lectores de Excel y CSV,
normalización, borradores, perfiles y aplicación de lotes.
Se genera su estructura con `manage.py startapp` y las migraciones con
`manage.py makemigrations`.

React incorpora una sección «Importar reservas» para administradores.
La API usa la autenticación de sesión y protección CSRF actuales.
El servidor realiza la interpretación y todas las validaciones;
la interfaz no determina por sí sola si una reserva es importable.

Se establecen límites de archivo y tamaño descomprimido para Excel.
Los formatos inválidos muestran un error claro sin alterar reservas.
No se evalúan fórmulas ni se consultan vínculos externos.

## Verificación y entrega

Las pruebas usarán archivos sintéticos con personas ficticias.
Cubrirán noches, salida, límites mensuales, notas, colores, vinculación,
duplicados, actualizaciones, conflictos, permisos, concurrencia y
reversión completa de un lote ante un error.

Se verificará la exportación/importación CSV, la conservación de cuentas
y notas manuales, y la protección contra aplicación repetida.
Se ejecutarán los controles de Django, las migraciones y el build de React.
Se revisará visualmente el flujo completo en la aplicación local.

La planilla real se utilizará para verificar el análisis y la vista previa.
Aplicar sus reservas exige confirmar inventario y filas dentro del módulo.
No se incorporará el archivo ni información personal a GitHub.

La entrega queda en la rama aparte, con commits y PR en español.
Se mostrará el módulo antes de darlo por finalizado y no se fusionará
automáticamente con la rama principal.
