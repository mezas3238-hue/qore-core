[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [string]$StateDir = "C:\QORE\state",
    [string]$TaskName = "QORE FundedNext Runtime"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path $RepoRoot).Path
$Python = (Get-Command python -ErrorAction Stop).Source
$GitSha = (& git -C $RepoRoot rev-parse HEAD).Trim().ToLowerInvariant()
if ($GitSha -notmatch '^[0-9a-f]{40}$') {
    throw "Repository HEAD is not a full Git SHA"
}

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
$StopFile = Join-Path $StateDir "STOP"
if (Test-Path $StopFile) {
    Remove-Item -Force $StopFile
}

$Guard = Join-Path $RepoRoot "scripts\fundednext_runtime_guard.py"
if (-not (Test-Path $Guard)) {
    throw "Runtime guard not found: $Guard"
}

$SupervisorArgs = @(
    "-m", "qore.infrastructure.fundednext_runtime_supervisor",
    "--state-dir", ('"{0}"' -f $StateDir),
    "--git-sha", $GitSha,
    "--",
    ('"{0}"' -f $Python),
    ('"{0}"' -f $Guard),
    "--state-dir", ('"{0}"' -f $StateDir),
    "--interval-seconds", "10"
) -join " "

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument $SupervisorArgs `
    -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "QORE FundedNext MT5 runtime supervisor; fail-closed, no provider mutation in guard mode." `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3
$Task = Get-ScheduledTask -TaskName $TaskName
$Info = Get-ScheduledTaskInfo -TaskName $TaskName

$Evidence = [ordered]@{
    schema = "qore.fundednext.windows-autostart.v1"
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    git_sha = $GitSha
    task_name = $TaskName
    task_state = [string]$Task.State
    last_task_result = $Info.LastTaskResult
    current_user = $env:USERNAME
    repo_root = $RepoRoot
    state_dir = $StateDir
    restart_count = 999
    restart_interval_seconds = 60
    multiple_instances = "IgnoreNew"
    startup_mode = "AtLogOnCurrentInteractiveUser"
}
$EvidencePath = Join-Path $StateDir "autostart.json"
$Evidence | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $EvidencePath
$Evidence | ConvertTo-Json -Depth 5
Write-Host "EVIDENCE=$EvidencePath"
