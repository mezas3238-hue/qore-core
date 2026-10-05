Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TaskName = "QORE VPS Control Bridge"
$InstallDir = "C:\ProgramData\QORE\VPSBridge"
$AgentPath = Join-Path $InstallDir "QoreVpsBridge.ps1"
$SourceCommit = "934d1f22fa4ec467e40151a704302828523b1f12"
$SourceUrl = "https://raw.githubusercontent.com/mezas3238-hue/qore-core/$SourceCommit/tools/vps_bridge/QoreVpsBridge.ps1"
$TempPath = Join-Path $env:TEMP "QoreVpsBridge-v020.ps1"

Write-Host "Downloading typed QORE VPS Control Bridge v0.2.0 ..."
Invoke-WebRequest -UseBasicParsing -Uri $SourceUrl -OutFile $TempPath

if ((Get-Item -LiteralPath $TempPath).Length -lt 5000) {
    throw "Downloaded bridge payload is unexpectedly small."
}

Write-Host "Stopping $TaskName ..."
try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 1

Copy-Item -Force -LiteralPath $TempPath -Destination $AgentPath

Write-Host "Starting $TaskName ..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 4

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host ""
Write-Host "QORE VPS Control Bridge upgraded."
Write-Host "Target version : 0.2.0"
Write-Host "State          : $($task.State)"
Write-Host "LastResult     : $($info.LastTaskResult)"
Write-Host "Agent          : $AgentPath"
Write-Host ""
Write-Host "The existing encrypted token and config were preserved."
