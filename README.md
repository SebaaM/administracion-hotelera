# Administración hotelera · Nido PMS

PMS local configurable para pequeños hoteles y hostels. Backend Django y PostgreSQL, frontend React con TypeScript. Cada establecimiento mantiene una instalación independiente en su red local.

## Alcance de la primera versión

Reservas por habitación privada o cama de dormitorio, check-in y check-out, cargos y cobros con comprobantes internos, limpieza, mantenimiento y personalización de marca y secciones. Sin sincronización con canales externos ni emisión fiscal.

## Puesta en marcha en Windows

Requisitos: Docker Desktop instalado y ejecutándose, con contenedores Linux. Internet se necesita para descargar y construir las imágenes por primera vez; la operación posterior funciona sin Internet. Los navegadores no cargan fuentes, scripts ni imágenes desde servicios externos.

Desde una terminal PowerShell en esta carpeta:

```powershell
# Usá la IP fija o el nombre del equipo servidor que verá el resto del hotel.
.\configurar.ps1 -DireccionHotel 192.168.1.50
docker compose up -d --build
docker compose exec backend python manage.py createsuperuser
```

Abrí `http://localhost:8080` en el servidor o `http://192.168.1.50:8080` desde otro equipo de la misma red. La IP es un ejemplo: reemplazala por la del servidor. Si Windows solicita acceso de red, habilitalo únicamente en la red privada del hotel; no abras puertos del router hacia Internet. La primera comprobación de red entre dos equipos debe hacerse en la instalación de cada hotel.

Entrá con la cuenta que creaste. En **Configuración → Habitaciones y camas**, creá el inventario real; en **Marca y secciones**, cargá logos, imágenes y los tres colores base. Las cuentas adicionales se crean en `/admin/`: una cuenta activa puede operar el PMS; una cuenta con permiso de personal (`is_staff`) también puede cambiar la configuración. Esta versión tiene dos niveles de acceso; los permisos detallados por área quedan pendientes de definición.

El script genera contraseñas y clave de Django aleatorias en `.env` y no sobrescribe un archivo existente. Para cambiar la dirección del servidor, editá `DJANGO_ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` en `.env` y ejecutá `docker compose up -d`. La moneda inicial es ARS y la zona horaria inicial es `America/Buenos_Aires`; `HOTEL_TIME_ZONE` se cambia en `.env`. La configuración regional completa es una ampliación pendiente.

En Linux o macOS se puede copiar `.env.example` a `.env`, reemplazar los dos valores `GENERAR_CON_CONFIGURAR` por secretos aleatorios independientes y completar las direcciones del hotel antes de ejecutar Docker Compose.

## Operación

- **Vista general:** calendario de siete días por habitación privada o cama, ocupación por unidad reservable y movimientos del día.
- **Reservas:** una reserva puede incluir varias unidades; se valida capacidad, fechas y disponibilidad antes de guardarla. Las fechas son intervalos `[llegada, salida)`: el día de salida puede coincidir con la próxima llegada.
- **Check-in:** solo en las fechas de la estadía, con la unidad limpia y sin otro huésped alojado. **Check-out:** libera la disponibilidad y genera limpieza pendiente. Un saldo pendiente no se borra al registrar la salida.
- **Cargos y cobros:** alojamiento calculado por noche y unidad, cargos adicionales, anticipos y cobros manuales. Los cobros no pueden superar el saldo. El medio “Tarjeta” registra un cobro ya realizado; no procesa pagos.
- **Comprobante interno:** desde la cuenta de la reserva, “Imprimir comprobante interno” permite imprimir o guardar como PDF con el navegador. Se imprime la cuenta completa; no es una factura fiscal ni un recibo numerado por cada cobro.
- **Limpieza:** pendiente → en curso → lista. También admite tareas manuales para unidades desocupadas.
- **Mantenimiento:** incidencia por habitación o cama, con período y bloqueo opcional. No se puede bloquear un espacio que ya tiene reservas en ese período. Al resolver la incidencia se libera el bloqueo.
- **Configuración:** marca, tres colores, logo, imagen de acceso, imágenes de habitaciones y secciones visibles. Los textos principales se escriben en español. Se pueden agregar camas y editar sus nombres, tarifas y activación; las tarifas nuevas no cambian reservas existentes.

Los puestos consultan al servidor cada cinco segundos cuando la pestaña está visible, y también al volver a ella. Todos escriben en la misma base PostgreSQL; los cambios de reserva usan transacciones y bloqueos por habitación, además de una restricción PostgreSQL contra solapamientos por unidad. La sincronización puede tardar hasta cinco segundos; no es una conexión permanente de eventos.

La configuración de secciones modifica la navegación y conserva los datos y permisos. Cada hotel tiene su propia instalación y base: no es un servicio compartido con varios hoteles dentro de la misma base.

## Datos ficticios de demostración

La demostración preparada en esta computadora contiene huéspedes e importes ficticios. Cuenta de prueba: `recepcion`, contraseña `Nido-Prueba-2026!`. Se carga mediante `seed_demo`, exclusivamente en una base sin habitaciones ni reservas y con `DJANGO_DEBUG=1`.

```powershell
docker compose exec -e DJANGO_DEBUG=1 backend python manage.py seed_demo
```

No cargues la demostración en un hotel en operación. Para una instalación real usá una base nueva, `DJANGO_DEBUG=0` y cuentas propias creadas con `createsuperuser`; la cuenta demo no se crea durante el arranque normal.

## Persistencia y copias de seguridad

Docker conserva PostgreSQL, las imágenes cargadas y los archivos estáticos en volúmenes separados. `docker compose down` detiene la instalación y conserva los datos. No uses `docker compose down -v`: elimina los volúmenes.

Para una copia consistente, pausá las escrituras del equipo y detené temporalmente el backend y la web. Desde la carpeta del proyecto, con Docker en marcha:

```powershell
New-Item -ItemType Directory -Force backups | Out-Null
docker compose stop backend web
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/pms.dump'
docker compose cp db:/tmp/pms.dump ./backups/pms.dump
docker compose run --rm --no-deps --user root -v "${PWD}/backups:/backup" backend tar -cf /backup/media.tar -C /app/media .
docker compose up -d backend web
```

Guardá también una copia privada de `.env` en un lugar seguro y copiá los archivos de `backups/` fuera del disco del servidor. Nunca subas estos archivos a GitHub. Para restaurar, primero detené el backend, restaurá el archivo con `pg_restore` en una base vacía y extraé `media.tar` en el volumen de imágenes. La restauración debe probarse con una copia, antes de usar datos reales; esta entrega no configura backups automáticos.

## Desarrollo y verificaciones

La estructura se generó con `django-admin startproject`, `startapp` y `create-vite --template react-ts`. Las migraciones se generan con `python manage.py makemigrations`; no se mantiene una base SQLite de producción.

```powershell
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test pms --noinput
```

La construcción del contenedor web ejecuta `tsc -b` y `vite build`. El frontend conserva `package-lock.json` y las dependencias de backend están fijadas a las versiones verificadas.

Las pruebas cubren habitaciones y camas, fechas contiguas, restricciones en PostgreSQL, reservas simultáneas, capacidad, cargos y cobros, limpieza, mantenimiento, cancelación, acceso, CSRF y configuración. GitHub Actions vuelve a construir la instalación y ejecutar las verificaciones en cada PR hacia `main` y cada actualización de `main`.

Para desarrollo sin contenedores de aplicación, iniciá solo PostgreSQL (`docker compose up -d db`), creá un entorno Python, instalá `backend/requirements.txt`, cargá las variables de `.env` y usá `DJANGO_DEBUG=1`, `python backend/manage.py runserver 127.0.0.1:8000`. En otra terminal, dentro de `frontend`, ejecutá `npm ci` y `npm run dev`. Vite deriva `/api` y `/media` a Django.

El navegador puede ofrecer herramientas WebMCP para consultar disponibilidad y abrir el formulario de reserva. Se registran solo en navegadores compatibles y en sesiones autenticadas; no permiten guardar reservas automáticamente. Los navegadores habituales funcionan con la interfaz completa aunque no soporten WebMCP.

## Límites de esta versión

No incluye canales externos, reservas públicas, facturación fiscal, devoluciones, cambio de fechas o traslado de unidades de una reserva existente, tarifas de temporada, monedas múltiples ni permisos detallados por área. La cancelación de reservas con cobros está bloqueada hasta disponer de un flujo de devolución. Los cargos y cobros no se borran ni se editan: un flujo contable de correcciones y devoluciones requiere una próxima integración.

Se puede editar el huésped, contacto, documento y notas. La cantidad de huéspedes y las fechas/unidades quedan fijadas al crear la reserva. Una habitación se define como privada o compartida; vender temporalmente un dormitorio como habitación completa queda pendiente.

El servicio se entrega para una red local de confianza, con HTTP en el puerto 8080. Para Wi-Fi compartida con huéspedes o redes no confiables, la puesta en producción necesita HTTPS local y aislamiento de red. No está preparado para exponerse públicamente en Internet. Antes de usarlo con datos reales, validar los procedimientos del hotel, la conexión desde otro puesto y la restauración de backups.

## GitHub Flow

Consultá `CONTRIBUTING.md`. Las integraciones se desarrollan en ramas y se revisan con PR; los mensajes se escriben en español. El repositorio es público y contiene únicamente código y ejemplos ficticios.
