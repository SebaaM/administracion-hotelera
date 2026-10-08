from django.contrib import admin

# Operational data is edited through validated services. The Django admin is
# reserved for accounts; direct booking edits would bypass inventory locks.
admin.site.site_header = "Nido · Cuentas del hotel"
admin.site.site_title = "Administración de cuentas"
