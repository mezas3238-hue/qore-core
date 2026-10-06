Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TaskName = "QORE VPS Control Bridge"
$InstallDir = "C:\ProgramData\QORE\VPSBridge"
$AgentPath = Join-Path $InstallDir "QoreVpsBridge.ps1"
$SourceCommit = "c92bbe14274206c9e01c72767049919417c8b9de"
$SourceUrl = "https://raw.githubusercontent.com/mezas3238-hue/qore-core/$SourceCommit/tools/vps_bridge/QoreVpsBridgeV040Clean.ps1"
$TempPath = Join-Path $env:TEMP "QoreVpsBridge-v040.ps1"

Write-Host "Downloading QORE VPS Control Bridge v0.4.0 ..."
Invoke-WebRequest -UseBasicParsing -Uri $SourceUrl -OutFile $TempPath

if ((Get-Item -LiteralPath $TempPath).Length -lt 7000) {
    throw "Downloaded bridge payload is unexpectedly small."
}

Write-Host "Stopping $TaskName ..."
try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 1

$PreviousPath = Join-Path $InstallDir "QoreVpsBridge.previous.ps1"
if (Test-Path -LiteralPath $AgentPath) {
    Copy-Item -Force -LiteralPath $AgentPath -Destination $PreviousPath
}
Copy-Item -Force -LiteralPath $TempPath -Destination $AgentPath

Write-Host "Starting $TaskName ..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 4

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

if ([string]$task.State -ne "Running") {
    Write-Host "Bridge did not enter Running state; rolling back ..."
    try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue } catch {}
    if (Test-Path -LiteralPath $PreviousPath) {
        Copy-Item -Force -LiteralPath $PreviousPath -Destination $AgentPath
        Start-ScheduledTask -TaskName $TaskName
    }
    throw "QORE VPS Control Bridge v0.4.0 failed to start; previous version restored."
}

Write-Host ""
Write-Host "QORE VPS Control Bridge upgraded."
Write-Host "Target version : 0.4.0"
Write-Host "State          : $($task.State)"
Write-Host "LastResult     : $($info.LastTaskResult)"
Write-Host "Agent          : $AgentPath"
Write-Host ""
Write-Host "Self-update is now enabled for future bridge versions."
Write-Host "Existing encrypted token and configuration were preserved."
