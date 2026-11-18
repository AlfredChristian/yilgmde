<#
Lance Yilgmdé pour les tests et la démo, sur Windows (D64).

    powershell -ExecutionPolicy Bypass -File scripts\lancer_demo.ps1
    powershell -ExecutionPolicy Bypass -File scripts\lancer_demo.ps1 -Reinitialiser

1. Prépare la base de démo (comptes, plan, historique) si elle n'existe pas, ou la refait
   à neuf avec -Reinitialiser.
2. Ouvre deux fenêtres : l'API (port 8000) et l'interface en https (port 5173), pour que la
   caméra et le micro marchent aussi sur les téléphones du même Wi-Fi.
3. Affiche les adresses à ouvrir et les comptes de test.

Fermer les deux fenêtres arrête l'application.
#>
param([switch]$Reinitialiser)
$ErrorActionPreference = "Stop"

$racine = Split-Path -Parent $PSScriptRoot
Set-Location $racine
$python = "python"
if (Test-Path ".venv\Scripts\python.exe") { $python = (Resolve-Path ".venv\Scripts\python.exe").Path }

$env:YILGMDE_ADMIN_EMAIL = "admin@ouaga.bf"
$env:YILGMDE_ADMIN_PASSWORD = "admin12345"
$base = "data\processed\yilgmde.sqlite3"

if ($Reinitialiser -and (Test-Path $base)) {
    Remove-Item $base
    Write-Host "Ancienne base supprimée."
}
if (-not (Test-Path $base)) {
    Write-Host "Préparation de la base de démo (1 à 2 minutes)..."
    & $python scripts/charger_exemples.py --ouaga --demo
    if ($LASTEXITCODE -ne 0) { throw "La préparation de la base a échoué : voir le message ci-dessus." }
}

$api = "Set-Location '$racine'; `$env:YILGMDE_ADMIN_EMAIL='admin@ouaga.bf'; `$env:YILGMDE_ADMIN_PASSWORD='admin12345'; & '$python' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $api
$front = "Set-Location '$racine\frontend'; npm run dev:telephone"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $front

$adresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.InterfaceAlias -notmatch "vEthernet|VMware|VirtualBox|Loopback" } |
    Select-Object -ExpandProperty IPAddress

Write-Host ""
Write-Host "Yilgmdé démarre dans deux nouvelles fenêtres (attendre une dizaine de secondes)."
Write-Host "  Sur ce PC        : https://localhost:5173"
foreach ($ip in $adresses) { Write-Host "  Sur le téléphone : https://${ip}:5173   (même Wi-Fi que ce PC)" }
Write-Host "  Documentation API: http://localhost:8000/docs"
Write-Host ""
Write-Host "Avertissement de sécurité du navigateur : c'est normal (certificat local)."
Write-Host "  Chrome : Paramètres avancés, puis Continuer vers le site."
Write-Host "  Safari : Afficher les détails, puis visiter ce site web."
Write-Host ""
Write-Host "Comptes : admin@ouaga.bf / admin12345 ; chauffeur@ouaga.bf / chauffeur123 ; laabal@ouaga.bf / laabal1234"
