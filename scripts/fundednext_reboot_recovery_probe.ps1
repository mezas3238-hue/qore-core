[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [string]$StateDir = "C:\QORE\state",
    [string]$TaskName = "QORE FundedNext Runtime"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path $RepoRoot).Path
$GitSha = (& git -C $RepoRoot rev-parse HEAD).Trim().ToLowerInvariant()
if ($GitSha -notmatch '^[0-9a-f]{40}$') {
    throw "Repository HEAD is not a full Git SHA"
}

$HeartbeatPath = Join-Path $StateDir "heartbeat.json"
$GuardPath = Join-Path $StateDir "guard.json"
if (-not (Test-Path $HeartbeatPath)) { throw "heartbeat.json missing" }
if (-not (Test-Path $GuardPath)) { throw "guard.json missing" }

$Heartbeat = Get-Content -Raw $HeartbeatPath | ConvertFrom-Json
$Guard = Get-Content -Raw $GuardPath | ConvertFrom-Json
$BootTime = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()
$HeartbeatTime = [DateTimeOffset]::Parse([string]$Heartbeat.timestamp_utc).UtcDateTime
$GuardTime = [DateTimeOffset]::Parse([string]$Guard.timestamp_utc).UtcDateTime
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop

$HeartbeatShaOk = ([string]$Heartbeat.git_sha -eq $GitSha)
$GuardShaOk = ([string]$Guard.git_sha -eq $GitSha)
$HeartbeatAfterBoot = ($HeartbeatTime -gt $BootTime)
$GuardAfterBoot = ($GuardTime -gt $BootTime)
$HeartbeatRunning = ([string]$Heartbeat.state -eq "RUNNING")
$GuardConnected = ([bool]$Guard.connected)
$TaskHealthy = ([string]$Task.State -eq "Running")
$Passed = $HeartbeatShaOk -and $GuardShaOk -and $HeartbeatAfterBoot -and `
    $GuardAfterBoot -and $HeartbeatRunning -and $GuardConnected -and $TaskHealthy

$Evidence = [ordered]@{
    schema = "qore.fundednext.reboot-recovery.v1"
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    git_sha = $GitSha
    passed = $Passed
    boot_time_utc = $BootTime.ToString("o")
    heartbeat_timestamp_utc = $HeartbeatTime.ToString("o")
    guard_timestamp_utc = $GuardTime.ToString("o")
    heartbeat_sha_matches = $HeartbeatShaOk
    guard_sha_matches = $GuardShaOk
    heartbeat_after_boot = $HeartbeatAfterBoot
    guard_after_boot = $GuardAfterBoot
    heartbeat_running = $HeartbeatRunning
    guard_connected = $GuardConnected
    task_name = $TaskName
    task_state = [string]$Task.State
    task_last_result = $TaskInfo.LastTaskResult
    task_healthy = $TaskHealthy
}

$StateEvidence = Join-Path $StateDir "reboot-recovery.json"
$Evidence | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $StateEvidence
$ArtifactDir = Join-Path $RepoRoot "artifacts"
New-Item -ItemType Directory -Force -Path $ArtifactDir | Out-Null
$ArtifactEvidence = Join-Path $ArtifactDir "fundednext_reboot_recovery.json"
$Evidence | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ArtifactEvidence
$Evidence | ConvertTo-Json -Depth 5
Write-Host "ARTIFACT=$ArtifactEvidence"
if (-not $Passed) { exit 2 }
