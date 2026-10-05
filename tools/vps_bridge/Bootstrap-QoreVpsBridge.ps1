param(
    [string]$ControlRepo = "mezas3238-hue/qore-vps-control",
    [string]$DeviceId = "vps-vrix"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SourceCommit = "4f7afbdbada24d15e1a03fc5c5c71b71fc33206e"
$Base = "https://raw.githubusercontent.com/mezas3238-hue/qore-core/$SourceCommit/tools/vps_bridge"
$TempDir = Join-Path $env:TEMP "qore-vps-bridge-bootstrap"

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

$Agent = Join-Path $TempDir "QoreVpsBridge.ps1"
$Installer = Join-Path $TempDir "Install-QoreVpsBridge.ps1"

Write-Host "Downloading QORE VPS Control Bridge from immutable qore-core commit $SourceCommit ..."
Invoke-WebRequest -UseBasicParsing -Uri "$Base/QoreVpsBridge.ps1" -OutFile $Agent
Invoke-WebRequest -UseBasicParsing -Uri "$Base/Install-QoreVpsBridge.ps1" -OutFile $Installer

Write-Host "Verifying downloaded files ..."
if ((Get-Item -LiteralPath $Agent).Length -lt 1000) { throw "Agent download is unexpectedly small." }
if ((Get-Item -LiteralPath $Installer).Length -lt 1000) { throw "Installer download is unexpectedly small." }

Write-Host ""
Write-Host "Installing bridge for $ControlRepo on device $DeviceId ..."
& $Installer -ControlRepo $ControlRepo -DeviceId $DeviceId
