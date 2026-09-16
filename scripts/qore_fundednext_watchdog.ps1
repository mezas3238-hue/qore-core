param()

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StatePath = "$Root\var\fundednext\runtime-state.json"
$RuntimeTaskName = "QORE-FundedNext-Runtime"
$EventPath = "$Root\artifacts\fundednext_watchdog.jsonl"

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
            $State = Get-Content -Raw $StatePath | ConvertFrom-Json
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
}
