# Importación de reservas: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar reservas desde Excel o CSV con notas y colores, vista previa corregible y aplicación atómica sin duplicados.

**Architecture:** Una aplicación Django llamada `imports` separa lectores, normalización, borradores y aplicación. PostgreSQL guarda perfiles, procedencia y decisiones; React presenta un asistente administrativo. La escritura valida nuevamente la disponibilidad y las versiones antes de aplicar el lote.

**Tech Stack:** Django 5.2.18, DRF 3.16.1, PostgreSQL 17, React 19, TypeScript y Vite existentes; openpyxl 3.1.5 y defusedxml 0.7.1 para lectura de Excel; biblioteca csv de Python.

**Spec:** `docs/superpowers/specs/2026-10-09-importacion-reservas-design.md`.

## Global Constraints

- El flujo aprobado es: cargar → vincular camas → revisar → aplicar.
- Subir o analizar un archivo no cambia las reservas del PMS.
- Funcionará dentro de la red del hotel, sin servicios externos.
- El usuario confirmó que una celda con el huésped representa una noche: ocupación del 10 al 12 implica llegada el 10 y salida el 13.
- Las observaciones importadas se conservan por separado de las manuales.
- No se borran ni cancelan reservas porque falten en una nueva planilla.
- Los datos y archivos de huéspedes se mantienen fuera del repositorio público.
- Se genera la estructura con `manage.py startapp` y las migraciones con `manage.py makemigrations`.
- La entrega queda en la rama aparte, con commits y PR en español.
- Aplicar la planilla real requiere confirmar inventario y filas dentro del módulo; no se fusiona automáticamente.

## Review Focus

1. Un Excel que declara dimensiones enormes no debe agotar memoria ni dejar un borrador incompleto: prueba de límites en tarea 2.
2. Un huésped homónimo o una fecha corregida no debe vincularse a una reserva equivocada: prueba de asociación ambigua en tarea 4.
3. Una reserva ya editada o con cobros nuevos no debe recibir una actualización basada en una vista previa antigua: prueba de versión en tarea 5.
4. Un texto que empieza con =, +, - o @ debe conservarse sin ejecutar fórmulas al exportar y reimportar: prueba de ida y vuelta en tarea 3.
5. Una cuenta migrada sin importes no debe aparecer como una estadía gratuita o pagada: pruebas de API y revisión visual en tareas 1 y 7.

## Archivos y contratos compartidos

- `backend/imports/contracts.py`: dataclasses serializables `SourceCell`, `SheetConfig`, `WorkbookSource`, `Candidate`, `NoteDecision`, `RowDecision`, `PreviewRow` y `Preview`.
- `SourceCell`: hoja, coordenada, valor de texto, nota completa, color hexadecimal o null y tipo original.
- `SheetConfig`: hoja, año, mes, columna de etiquetas, filas de encabezado de días y filas de unidades; nombres de hoja únicos.
- `Candidate`: clave temporal, id_origen opcional, unidad_origen, huésped, llegada, salida, notas, colores, referencias y advertencias.
- `NoteDecision`: hoja/celda, acción ASSIGN/EXCLUDE, clave candidata destino o motivo de exclusión.
- `RowDecision`: clave, seleccionada, exclusión explícita, cambios de huésped/fechas/estado/unidad, reserva destino opcional, versión esperada y confirmaciones de advertencias.
- `PreviewRow`: candidato resuelto, acción CREATE/UPDATE/UNCHANGED/CONFLICT/REVIEW, errores y comparación antes/después.
- `Preview`: filas, notas pendientes, token de versión del borrador y resumen.
- `backend/imports/readers.py`: lectura limitada de Excel y detección de estructura.
- `backend/imports/csv_io.py`: contrato CSV reversible.
- `backend/imports/normalize.py`: calendario → candidatos; no escribe en la base.
- `backend/imports/preview.py`: vinculación, diferencias y validación.
- `backend/imports/apply.py`: única entrada para modificar reservas desde un lote.
- `frontend/src/imports/`: types.ts, api.ts, ImportPage.tsx, SourceStep.tsx, MappingStep.tsx y ReviewStep.tsx.
- Se conserva `pms/views.py` como serializador del PMS; no se reorganiza código ajeno al módulo.

## Preparación para ejecutar

La rama local ya contiene la especificación del commit `3f2515b`.
Antes de implementar, confirmar árbol limpio, leer especificación y plan,
y ejecutar la verificación base sin aplicar datos reales.
Usar el prefijo Git de directorio seguro que requiere esta computadora.

Los comandos Docker se ejecutan en la raíz del repositorio.
Los comandos `manage.py` locales se ejecutan desde `backend/`, con el Python
de `work/venv/Scripts/python.exe` y variables privadas de `.env` cargadas
sin imprimirlas. La construcción Docker permite probar con PostgreSQL real.

Las pruebas se ejecutan con `docker compose exec -T backend python manage.py test <etiquetas> --noinput`.
Cada tarea indica las etiquetas; su ciclo empieza con fallo por funcionalidad
ausente y termina con todas las pruebas de esas etiquetas pasando.
Reconstruir backend con `docker compose build backend` y recrearlo antes de
probar archivos nuevos; no ejecutar tests contra una imagen anterior.
Crear `imports/tests/__init__.py` y fixtures.py al generar los primeros tests.

Casos mínimos identificados para el ciclo de pruebas:

| Tarea | Prueba | Aserción principal |
| --- | --- | --- |
| 1 | test_unknown_rate_is_not_free_stay | rate is None; financial_review_required is True; ledger.count() == 0 |
| 2 | test_comments_and_theme_colors_survive | note == texto original; theme resuelto == hexadecimal esperado |
| 3 | test_nights_use_exclusive_checkout | start == 2026-08-10; end == 2026-08-13 |
| 3 | test_csv_roundtrip_preserves_formula_like_text | read_csv(write_csv(rows)) == rows normalizadas |
| 4 | test_ambiguous_binding_requires_decision | action == REVIEW; Reservation.count() no cambia |
| 5 | test_last_row_failure_rolls_back_batch | no existen reservas, vínculos ni lote nuevos |
| 5 | test_new_payment_invalidates_preview | se rechaza apply; cobro conservado; datos de huésped intactos |
| 6 | test_non_admin_cannot_download_csv | status_code == 403 |
| 7 | test_empty_account_requires_explicit_zero | rechazo sin confirmed_zero; revisión guarda usuario al confirmarlo |

### Tarea 1: persistencia de importación y cuentas por revisar

**Archivos:** generar `backend/imports/` con startapp; crear contracts.py;
modificar imports/models.py, config/settings.py, pms/models.py, pms/views.py;
generar migraciones; crear imports/tests/test_models.py.

**Interfaces:** ImportProfile guarda nombre, configuración y mapa de unidades;
ImportDraft guarda usuario, perfil, huella SHA-256, fuente normalizada JSON,
decisiones, revisión entera y estado DRAFT/APPLIED/DISCARDED.
ImportBinding vincula (perfil, id_origen UUID) con Reservation y último contenido; también es único por perfil y reserva.
ImportBatch registra acciones aplicadas y usuario, con vínculo único a borrador.
Reservation incorpora financial_review_required, account_reviewed_at y
account_reviewed_by. Allocation.rate acepta null para tarifa desconocida.
El DTO agrega import_notes: str, import_colors: list[dict], financial_review_required: bool;
las notas manuales siguen en notes y la tarifa normal continúa siendo decimal.

- [ ] Generar la app con `python manage.py startapp imports`; escribir test_models con unicidad de vínculo y lote, tarifa null y DTO sin cargos inventados.
- [ ] Ejecutar `docker compose exec -T backend python manage.py test imports.tests.test_models --noinput` tras construir la imagen con los tests; debe fallar por los campos o modelos ausentes.
- [ ] Implementar modelos y contratos; generar migraciones, reconstruir backend y ejecutarlas. Mantener el método normal create_reservation y su comportamiento anterior.
- [ ] Ejecutar test_models y las pruebas pms: ambos deben pasar; ninguna reserva normal queda marcada para revisión.
- [ ] Commit: `feat: registrar perfiles y borradores de importación`.

### Tarea 2: lector Excel y preservación de metadatos

**Archivos:** readers.py, imports/tests/test_excel.py y fixtures.py;
backend/requirements.txt.

**Interfaces:** `read_xlsx(content: bytes) -> WorkbookSource`;
`suggest_configuration(source: WorkbookSource) -> list[SheetConfig]`.
WorkbookSource contiene celdas dispersas, títulos y advertencias; no archivo público.

- [ ] Escribir tests: comentario completo conservado; tema/tint convertido a hexadecimal; etiquetas numéricas 10 y 10.0 normalizadas a 10; dos hojas detectadas; fórmulas y formatos ambiguos señalados.
- [ ] Agregar tests para ZIP corrupto, macros, tamaño y dimensiones excesivas; ejecutar test_excel y comprobar fallo antes de implementar.
- [ ] Implementar prevalidación ZIP y lector openpyxl con read_only=False, data_only=False y keep_links=False. Límite 5 MiB de archivo, 32 MiB descomprimidos, 20 hojas, 100.000 celdas, 5.000 filas y 400 columnas por hoja. Rechazar XML con DTD/entidades, entradas duplicadas y contenido macro. Usar defusedxml.
- [ ] Resolver RGB, tema y tint; preservar notas y celdas vacías relevantes. Formato condicional o celdas fusionadas que afecten unidades/días producen revisión explícita y configuración manual; no se inventa su color efectivo. No evaluar fórmulas.
- [ ] Ejecutar test_excel; todas las entradas inválidas se rechazan sin persistencia parcial. Commit: `feat: leer calendarios Excel con notas y colores`.

Documentación de las dependencias: [defusedxml en PyPI](https://pypi.org/project/defusedxml/), [openpyxl en PyPI](https://pypi.org/project/openpyxl/) y [lectura de comentarios](https://openpyxl.readthedocs.io/en/stable/comments.html).
Se conserva texto, autor y referencia; el formato visual del globo de comentario no forma parte de la migración.

### Tarea 3: normalización mensual y CSV reversible

**Archivos:** normalize.py, csv_io.py, imports/tests/test_normalize.py y test_csv.py.

**Interfaces:** `normalize_calendar(source: WorkbookSource, sheets: list[SheetConfig], legend: dict[str, str]) -> list[Candidate]`;
`read_csv(content: bytes) -> list[Candidate]`;
`write_csv(candidates: list[Candidate]) -> bytes`.

- [ ] Escribir tests: nombre del 10 al 12 → [10,13); cambio de color conserva una estadía; rojo de salida no suma noche; 31 de agosto y 1 de septiembre requieren confirmación de continuidad; cambio de cama no une por nombre.
- [ ] Escribir tests para días inválidos, etiquetas repetidas, notas en etiquetas/vacíos, nombre idéntico en estadías separadas y extremos de mes incompletos; ejecutar test_normalize y comprobar fallo.
- [ ] Implementar agrupación por unidad y días consecutivos. Configuración explícita identifica mes/año y filas; se excluyen encabezados y leyenda. Las uniones entre hojas son decisiones guardadas con todas las referencias, no deducciones silenciosas.
- [ ] Escribir tests CSV con encabezados de la especificación, Unicode, saltos de línea, JSON inválido e id_origen duplicado; incluir textos =1+1, +texto, -texto, @texto y apóstrofo original. Ejecutar test_csv y comprobar fallo.
- [ ] Implementar CSV UTF-8 con BOM aceptado, separador coma y columnas exactas; listas JSON para colores y referencias. Proteger texto de fórmula con apóstrofo y registrar qué campos fueron protegidos dentro de referencias; al reimportar retirar solo la protección registrada, conservando el apóstrofo original.
- [ ] Ejecutar test_normalize y test_csv; comprobar igualdad de datos en ida y vuelta. Commit: `feat: convertir calendarios a reservas y CSV normalizado`.

### Tarea 4: borradores, vinculación y vista previa validada

**Archivos:** preview.py, imports/services.py, imports/tests/test_preview.py.

**Interfaces:** `create_draft(content: bytes, filename: str, profile: ImportProfile, user: User) -> ImportDraft`;
`build_preview(draft: ImportDraft, decisions: list[RowDecision], note_decisions: list[NoteDecision]) -> Preview`;
`save_decisions(draft_id: int, expected_revision: int, decisions: dict, user: User) -> Preview`.

- [ ] Escribir tests: subir archivo no crea reservas; mapa sin confirmar exige revisión; cama desactivada impide aplicar; nombre homónimo no vincula automáticamente; dos filas que pretenden actualizar la misma reserva se bloquean; corrección de fecha o nombre ambiguo exige asociación explícita.
- [ ] Escribir tests para conservar notas completas, resolver notas sueltas mediante asociación o exclusión, diferencias antes/después, exclusión de filas y confirmación de advertencias; ejecutar test_preview y comprobar fallo.
- [ ] Implementar perfiles reutilizables y sugerencias sin confirmación automática. id_origen se asigna al confirmar una nueva fila; cargas futuras usan vínculos de perfil y firma previa. Solo coincidencias exactas inequívocas reutilizan un vínculo; otros casos muestran sugerencia para confirmar.
- [ ] Implementar comparación de ocupación, mantenimiento y disponibilidad; guardar en decisiones los tokens de Reservation.updated_at y la firma de asignaciones/cuenta. Mostrar revisión para tarifas desconocidas y todos los estados elegidos explícitamente.
- [ ] Ejecutar test_preview; el borrador guarda decisiones y versión pero ninguna modificación al PMS. Commit: `feat: revisar y vincular reservas antes de migrar`.

### Tarea 5: aplicación atómica, repetición y concurrencia

**Archivos:** apply.py, imports/tests/test_apply.py y test_concurrency.py.

**Interfaces:** `apply_draft(draft_id: int, expected_revision: int, user: User) -> ImportBatch`.
ImportBatch devuelve resumen de reservas creadas/actualizadas/sin cambios.

- [ ] Escribir test_apply para un lote válido, repetir su confirmación, volver a subir el mismo archivo, omitir una reserva existente y actualizar notas importadas sin borrar notes ni ledger.
- [ ] Escribir pruebas de rollback total: segundo candidato conflictivo, nota sin resolver, unidad inactiva y bloqueo de mantenimiento; ejecutar test_apply y comprobar fallo.
- [ ] Implementar transacción: bloquear borrador, luego reservas existentes por PK y habitaciones por PK, conforme al orden del PMS. Releer unidades y datos, validar versiones y disponibilidad antes de escribir; reutilizar exclusión PostgreSQL y lock_rooms.
- [ ] Crear reservas con una unidad y tarifa null, sin LedgerEntry automático; allocations activas solo para CONFIRMED/IN_HOUSE. Exigir fechas vigentes y cama limpia para IN_HOUSE. Preservar timestamps históricos desconocidos como null y no generar limpieza al importar finalizadas.
- [ ] Actualizar datos permitidos con snapshot vigente. Para reservas IN_HOUSE, CHECKED_OUT o CANCELLED existentes bloquear cambio de fechas/unidad/estado; permitir observaciones importadas sin alterar operación ni cuentas. No mover reservas con múltiples unidades desde una fila individual.
- [ ] Escribir test_concurrency con TransactionTestCase y dos conexiones: dos lotes disputan misma cama; editar reserva o agregar cobro tras preview invalida lote; confirmar simultáneamente el mismo borrador produce un único lote.
- [ ] Ejecutar test_apply y test_concurrency: sin duplicados ni cambios parciales; trasladar IntegrityError a conflicto visible fuera de la transacción fallida. Commit: `feat: aplicar migraciones con control de disponibilidad`.

### Tarea 6: API administrativa y exportación

**Archivos:** imports/views.py, urls.py, serializers.py y tests/test_api.py;
backend/config/urls.py.

**Interfaces:** endpoints bajo /api/imports/: profiles/ (GET/POST/PATCH por id);
drafts/ (GET/POST multipart); drafts/<id>/ (GET/PATCH decisiones);
drafts/<id>/preview/ (POST); drafts/<id>/apply/ (POST);
drafts/<id>/discard/ (POST); drafts/<id>/csv/ (GET).
PATCH, preview y apply exigen expected_revision. Toda ruta exige sesión activa
y is_staff; respuesta CSV usa Content-Disposition de descarga.

- [ ] Escribir test_api para anónimo, usuario operativo sin is_staff y administrador; CSRF obligatorio, archivo inválido, decisiones inválidas y versión obsoleta. Ejecutar test_api y comprobar fallo.
- [ ] Implementar rutas y serializers que rechacen campos desconocidos y decisiones fuera del borrador; reutilizar autenticación actual. Aplicar validación del servidor, no confiar en acciones enviadas por el navegador.
- [ ] La descarga exporta filas seleccionadas/resueltas con id_origen persistente. Un borrador descartado elimina su fuente con datos personales y conserva solo auditoría no personal; un lote aplicado mantiene procedencia protegida en PostgreSQL.
- [ ] Ejecutar test_api y pruebas de acceso directo a exportación por usuario sin permisos. Commit: `feat: exponer la revisión administrativa de importaciones`.

### Tarea 7: asistente React y cuentas pendientes

**Archivos:** frontend/src/imports/{types.ts,api.ts,ImportPage.tsx,SourceStep.tsx,MappingStep.tsx,ReviewStep.tsx};
App.tsx, types.ts, Configuration.tsx, App.css, ReservationDetail.tsx y Operations.tsx;
pms/views.py, config/urls.py e imports/tests/test_account_review.py.

**Interfaces:** `ImportPage({data, onApplied}: {data: State; onApplied: () => Promise<void>})`.
El cliente consume los DTO definidos en tareas 1, 4 y 6.
`POST /api/reservations/<id>/account-review/` acepta expected_updated_at,
firma de ledger y confirmed_zero; requiere sesión activa y confirmación humana.

- [ ] Escribir test_account_review: cargo o cobro nuevo invalida snapshot; cuenta vacía necesita confirmed_zero; completar revisión guarda usuario/fecha sin crear movimientos. Ejecutar y comprobar fallo.
- [ ] Implementar revisión de cuenta y mostrar «Cuenta pendiente de revisión» en detalle, lista de cuentas y comprobante. Mostrar importes como movimientos registrados, no total final de estadía cuando falta conciliación. La tarifa null se muestra «Sin tarifa importada».
- [ ] Implementar entrada «Importar reservas», visible solo para administradores y configurable entre secciones. Asistente: archivo/perfil → período y filas → mapa de unidades → revisión/nota suelta → resumen y confirmación HTML.
- [ ] Mantener las ediciones en el borrador mediante guardado explícito y revisión esperada; sondeos de state no renuevan los snapshots de revisión. Al aplicar, recargar el PMS y mostrar resumen y lote.
- [ ] Descarga CSV mediante fetch con sesión; no ejecutar JSON api() para una respuesta CSV. Mostrar errores al lado de filas y preservar trabajo ante un conflicto.
- [ ] Ejecutar test_account_review y `npm run build` desde frontend; ambos deben pasar. Revisar asistente a ancho de escritorio y móvil, teclado y leyenda con texto además de color.
- [ ] Commit: `feat: incorporar el asistente de migración al PMS`.

### Tarea 8: verificación integral, documentación y PR de revisión

**Archivos:** README.md; .github/workflows/verificar.yml; datos ficticios solo en tests.

- [ ] Cambiar CI para ejecutar `python manage.py test pms imports --noinput`. El PR inicial ya está fusionado en main (9dc6a63); abrir el nuevo PR contra main y conservar el trigger actual.
- [ ] Documentar formato soportado, límites, CSV protegido, fechas históricas, cuentas por conciliar y reimportación; incluir ejemplo con datos ficticios y procedimiento de vista previa.
- [ ] Ejecutar `docker compose up -d --build`; luego check, makemigrations --check --dry-run y test pms imports --noinput. Ejecutar `npm run build` desde frontend. Exigir cero errores y árbol sin migraciones pendientes.
- [ ] Verificar visualmente carga, vinculación, corrección, notas sueltas, conflicto, exclusión, aplicación ficticia, repetición del lote y descarga/reimportación CSV; usar una base de prueba para escrituras y conservar la instalación del hotel.
- [ ] Analizar la copia local del Excel real en vista previa; revisar que se conserven las 151 notas y los colores sin subir nombres, notas ni el archivo a GitHub. No aplicar esas reservas durante pruebas.
- [ ] Pedir revisión independiente de la rama según requesting-code-review, resolver hallazgos con pruebas dirigidas y repetir solo los controles afectados.
- [ ] Commit: `docs: documentar y verificar la migración de reservas`. Push de la rama; crear PR en borrador en español, adjuntarlo al chat y verificar CI. Mostrar la aplicación al usuario antes de finalizar o fusionar.

## Revisión del plan y ejecución

Cobertura: fechas e inventario (2–4), notas/colores (2–4,7), cuentas (1,5,7),
idempotencia y concurrencia (4–6), permisos/CSV (3,6), interfaz/entrega (7–8).
Los cinco puntos de Review Focus tienen pruebas asignadas.

Recomendación: ejecución nativa en este chat, con una revisión independiente
de toda la rama al terminar. Las tareas comparten contratos de borrador y
disponibilidad; implementarlas aquí evita contextos nuevos por cada tarea.
Alternativa: subagentes por tarea con revisión antes de avanzar.

Antes de ejecutar se necesita la revisión de este plan y la selección de
método. Esta documentación no implementa el módulo ni aplica reservas.
