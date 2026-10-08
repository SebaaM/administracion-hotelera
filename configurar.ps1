param([string]$DireccionHotel = 'localhost')
$ErrorActionPreference = 'Stop'
$rutaProyecto = $PSScriptRoot
$rutaEnv = Join-Path $rutaProyecto '.env'
if (Test-Path -LiteralPath $rutaEnv) { Write-Host 'La configuración ya existe. Editá .env para cambiar la dirección del servidor.'; exit 0 }
function Nuevo-Secreto {
    $bytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $rng.Dispose()
    return [Convert]::ToBase64String($bytes)
}
if ($DireccionHotel -notmatch '^[a-zA-Z0-9.\-]+$') { throw 'Ingresá una IP o un nombre de equipo válido, sin puerto.' }
$textoEnv = Get-Content -LiteralPath (Join-Path $rutaProyecto '.env.example') -Raw
$textoEnv = $textoEnv.Replace('POSTGRES_PASSWORD=GENERAR_CON_CONFIGURAR', ('POSTGRES_PASSWORD=' + (Nuevo-Secreto)))
$textoEnv = $textoEnv.Replace('DJANGO_SECRET_KEY=GENERAR_CON_CONFIGURAR', ('DJANGO_SECRET_KEY=' + (Nuevo-Secreto)))
$textoEnv = $textoEnv.Replace('DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend', "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend,$DireccionHotel")
$textoEnv = $textoEnv.Replace('CSRF_TRUSTED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080', "CSRF_TRUSTED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://${DireccionHotel}:8080")
Set-Content -LiteralPath $rutaEnv -Value $textoEnv -Encoding utf8
Write-Host 'Configuración creada. Ejecutá docker compose up -d --build y luego docker compose exec backend python manage.py createsuperuser.'
