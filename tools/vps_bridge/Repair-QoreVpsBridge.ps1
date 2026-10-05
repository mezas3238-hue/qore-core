Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TaskName = "QORE VPS Control Bridge"
$AgentPath = "C:\ProgramData\QORE\VPSBridge\QoreVpsBridge.ps1"

if (-not (Test-Path -LiteralPath $AgentPath)) {
    throw "Installed bridge agent not found: $AgentPath"
}

Write-Host "Stopping $TaskName ..."
try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 1

$text = Get-Content -LiteralPath $AgentPath -Raw -Encoding UTF8
$text = $text.Replace("[Security.Cryptography.ProtectedData]", "[System.Security.Cryptography.ProtectedData]")
$text = $text.Replace("[Security.Cryptography.DataProtectionScope]", "[System.Security.Cryptography.DataProtectionScope]")
$text = $text.Replace('$uri = "$ApiBase/contents/$escapedPath?ref=$branchEncoded"', '$uri = "$ApiBase/contents/${escapedPath}?ref=$branchEncoded"')

if ($text -notmatch "Add-Type -AssemblyName System.Security") {
    $text = $text.Replace('$ErrorActionPreference = "Stop"', '$ErrorActionPreference = "Stop"' + [Environment]::NewLine + 'Add-Type -AssemblyName System.Security')
}

[IO.File]::WriteAllText($AgentPath, $text, [Text.UTF8Encoding]::new($false))

Write-Host "Starting $TaskName ..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host ""
Write-Host "Bridge repair applied."
Write-Host "State      : $($task.State)"
Write-Host "LastResult : $($info.LastTaskResult)"
Write-Host "Agent      : $AgentPath"