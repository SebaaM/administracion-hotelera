# Flujo de desarrollo

Trabajamos con GitHub Flow. `main` recibe cambios mediante pull requests; cada integración se desarrolla en una rama corta, como `feature/reservas` o `fix/disponibilidad`.

Los mensajes de commit, títulos y descripciones de PR se escriben en español. Usamos prefijos `feat:`, `fix:`, `test:`, `docs:` o `chore:` seguidos de una descripción concreta.

Antes de pedir revisión: ejecutar las pruebas de Django con PostgreSQL, comprobar las migraciones y compilar el frontend. Las integraciones grandes comienzan como PR en borrador y pasan a revisión cuando la verificación termina. No fusionar con pruebas fallidas.

No subir `.env`, datos de huéspedes, comprobantes reales, copias de seguridad ni imágenes cargadas por un hotel. Los datos de ejemplo deben ser ficticios.
