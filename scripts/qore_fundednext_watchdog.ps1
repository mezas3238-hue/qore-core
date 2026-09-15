param()

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StatePath = "$Root\var\fundednext\runtime-state.json"
$Restart = $false
if (-not (Test-Path $StatePath)) {
    $Restart = $true
} else {
    try {
        $State = Get-Content -Raw $StatePath | ConvertFrom-Json
        $Heartbeat = [DateTimeOffset]::Parse([string]$State.heartbeat_at)
        if (([DateTimeOffset]::UtcNow - $Heartbeat).TotalSeconds -gt 120) {
            $Restart = $true
        }
    } catch {
        $Restart = $true
    }
}

if ($Restart) {
    Stop-ScheduledTask -TaskName "QORE-FundedNext-Runtime" -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName "QORE-FundedNext-Runtime"
    $Event = [ordered]@{
        event = "WATCHDOG_RESTART"
        at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    New-Item -ItemType Directory -Force -Path "$Root\artifacts" | Out-Null
    $Event | ConvertTo-Json -Compress | Add-Content -Encoding UTF8 "$Root\artifacts\fundednext_watchdog.jsonl"
}
