param()

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StatePath = "$Root\var\fundednext\runtime-state.json"
$RuntimeTaskName = "QORE-FundedNext-Runtime"
$EventPath = "$Root\artifacts\fundednext_watchdog.jsonl"
$MaintenancePath = "$Root\var\fundednext\maintenance.json"
$RestartGuardPath = "$Root\var\fundednext\watchdog-restart-guard.json"
$RestartWindowSeconds = 600
$MaximumRestartsPerWindow = 3

function Read-JsonShared([string]$Path) {
    $Share = [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
    $Stream = [System.IO.FileStream]::new(
        $Path,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        $Share
    )
    try {
        $Reader = [System.IO.StreamReader]::new($Stream)
        try { return ($Reader.ReadToEnd() | ConvertFrom-Json) }
        finally { $Reader.Dispose() }
    } finally {
        $Stream.Dispose()
    }
}

function Write-JsonAtomic([object]$Value, [string]$Path) {
    $Directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $Directory | Out-Null
    $Temporary = "$Path.$PID.tmp"
    $Value | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 $Temporary
    Move-Item -Force $Temporary $Path
}

function Get-QoreRuntimeProcesses {
    return @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -eq "python.exe" -and
                $_.CommandLine -match "qore_fundednext_runtime\.py"
            }
    )
}

function Log-Watchdog([string]$Event, [string]$Reason) {
    $Value = [ordered]@{
        event = $Event
        reason = $Reason
        at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    New-Item -ItemType Directory -Force -Path "$Root\artifacts" | Out-Null
    $Value | ConvertTo-Json -Compress | Add-Content -Encoding UTF8 $EventPath
}

if (Test-Path $MaintenancePath) {
    Log-Watchdog "WATCHDOG_MAINTENANCE" "owner-maintenance-fence-active"
    exit 0
}

$Task = Get-ScheduledTask -TaskName $RuntimeTaskName
$Arguments = [string]$Task.Actions[0].Arguments
$DesiredMode = if ($Arguments -match "--mode\s+live(?:\s|$)") { "live" } else { "shadow" }
$Processes = @(Get-QoreRuntimeProcesses)

if ($Processes.Count -gt 1) {
    Disable-ScheduledTask -TaskName $RuntimeTaskName | Out-Null
    Log-Watchdog "WATCHDOG_FAIL_CLOSED" "multiple-runtime-processes"
    exit 2
}

$Restart = $false
$Reason = ""
if ($Processes.Count -eq 0) {
    $Restart = $true
    $Reason = "runtime-process-missing"
} elseif ([string]$Processes[0].CommandLine -notmatch "--mode\s+$DesiredMode(?:\s|$)") {
    $Restart = $true
    $Reason = "runtime-mode-mismatch"
}

if (-not $Restart) {
    if (-not (Test-Path $StatePath)) {
        $Restart = $true
        $Reason = "runtime-state-missing"
    } else {
        try {
            $State = Read-JsonShared $StatePath
            $Heartbeat = [DateTimeOffset]::Parse([string]$State.heartbeat_at)
            if (([DateTimeOffset]::UtcNow - $Heartbeat).TotalSeconds -gt 120) {
                $Restart = $true
                $Reason = "runtime-heartbeat-stale"
            }
        } catch {
            $Restart = $true
            $Reason = "runtime-state-invalid"
        }
    }
}

if ($Restart) {
    $Now = [DateTimeOffset]::UtcNow
    $WindowStartedAt = $Now
    $RestartCount = 0
    if (Test-Path $RestartGuardPath) {
        try {
            $Guard = Read-JsonShared $RestartGuardPath
            $PriorWindow = [DateTimeOffset]::Parse([string]$Guard.window_started_at)
            if (($Now - $PriorWindow).TotalSeconds -le $RestartWindowSeconds) {
                $WindowStartedAt = $PriorWindow
                $RestartCount = [int]$Guard.restart_count
            }
        } catch {
            $RestartCount = $MaximumRestartsPerWindow
        }
    }
    if ($RestartCount -ge $MaximumRestartsPerWindow) {
        Disable-ScheduledTask -TaskName $RuntimeTaskName | Out-Null
        Log-Watchdog "WATCHDOG_FAIL_CLOSED" "restart-storm-fenced:$Reason"
        exit 4
    }
    $RestartCount += 1
    Write-JsonAtomic ([ordered]@{
        window_started_at = $WindowStartedAt.ToString("o")
        restart_count = $RestartCount
        last_reason = $Reason
        last_restart_at = $Now.ToString("o")
    }) $RestartGuardPath

    Stop-ScheduledTask -TaskName $RuntimeTaskName -ErrorAction SilentlyContinue
    $Deadline = [DateTimeOffset]::UtcNow.AddSeconds(20)
    do {
        $Processes = @(Get-QoreRuntimeProcesses)
        if ($Processes.Count -eq 0) { break }
        Start-Sleep -Milliseconds 500
    } while ([DateTimeOffset]::UtcNow -lt $Deadline)

    if ($Processes.Count -gt 0) {
        Log-Watchdog "WATCHDOG_FAIL_CLOSED" "runtime-stop-timeout:$Reason"
        Disable-ScheduledTask -TaskName $RuntimeTaskName | Out-Null
        exit 3
    }

    Remove-Item "$Root\var\fundednext\runtime.lock" -Force -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName $RuntimeTaskName
    Log-Watchdog "WATCHDOG_RESTART" $Reason
} elseif (Test-Path $RestartGuardPath) {
    Remove-Item $RestartGuardPath -Force -ErrorAction SilentlyContinue
}
