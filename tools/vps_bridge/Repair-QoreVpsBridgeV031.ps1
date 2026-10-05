Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TaskName = "QORE VPS Control Bridge"
$InstallDir = "C:\ProgramData\QORE\VPSBridge"
$AgentPath = Join-Path $InstallDir "QoreVpsBridge.ps1"
$SourceCommit = "d6259b00b61d07a94286e6cf5425e6d30c933e3b"
$SourceUrl = "https://raw.githubusercontent.com/mezas3238-hue/qore-core/$SourceCommit/tools/vps_bridge/QoreVpsBridgeV031.ps1"
$TempPath = Join-Path $env:TEMP "QoreVpsBridge-v031.ps1"

Write-Host "Downloading clean QORE VPS Control Bridge v0.3.1 ..."
Invoke-WebRequest -UseBasicParsing -Uri $SourceUrl -OutFile $TempPath

if ((Get-Item -LiteralPath $TempPath).Length -lt 7000) {
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
Write-Host "QORE VPS Control Bridge repaired/upgraded."
Write-Host "Target version : 0.3.1"
Write-Host "State          : $($task.State)"
Write-Host "LastResult     : $($info.LastTaskResult)"
Write-Host "Agent          : $AgentPath"
Write-Host ""
Write-Host "Encrypted token and configuration preserved."
