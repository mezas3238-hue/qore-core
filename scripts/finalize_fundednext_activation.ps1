param()

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StateDir = "$Root\var\fundednext"
$PendingPath = "$StateDir\pending-reboot-readiness.json"
$ActivationPath = "$StateDir\live-activation.json"
$StatePath = "$StateDir\runtime-state.json"
if (-not (Test-Path $PendingPath)) { exit 0 }

Start-Sleep -Seconds 20
$Pending = Get-Content -Raw $PendingPath | ConvertFrom-Json
$Activation = Get-Content -Raw $ActivationPath | ConvertFrom-Json
$State = Get-Content -Raw $StatePath | ConvertFrom-Json
$Boot = [DateTimeOffset](Get-CimInstance Win32_OperatingSystem).LastBootUpTime
$Heartbeat = [DateTimeOffset]::Parse([string]$State.heartbeat_at)
$Reconciled = [DateTimeOffset]::Parse([string]$State.last_reconciliation_at)
$Task = Get-ScheduledTask -TaskName "QORE-FundedNext-Runtime"

if ([string]$State.git_sha -ne [string]$Pending.git_sha) { throw "post-reboot SHA mismatch" }
if ([string]$State.account_identity_fingerprint -ne [string]$Pending.account_identity_fingerprint) {
    throw "post-reboot account fingerprint mismatch"
}
if ($Heartbeat -lt $Boot) { throw "runtime produced no heartbeat after this Windows boot" }
if ($Reconciled -lt $Boot) { throw "runtime produced no reconciliation after this Windows boot" }
if (([DateTimeOffset]::UtcNow - $Heartbeat).TotalSeconds -gt 120) {
    throw "post-reboot runtime heartbeat stale"
}
if ([string]$Task.State -ne "Running") { throw "QORE runtime task is not running" }

$EvidencePath = "$Root\artifacts\fundednext_restart_recovery.json"
$Evidence = [ordered]@{
    schema = "qore.fundednext.restart-recovery.v1"
    ok = $true
    git_sha = [string]$State.git_sha
    account_identity_fingerprint = [string]$State.account_identity_fingerprint
    windows_boot_at = $Boot.ToUniversalTime().ToString("o")
    heartbeat_at = $Heartbeat.ToUniversalTime().ToString("o")
    reconciliation_at = $Reconciled.ToUniversalTime().ToString("o")
    scheduled_task_state = [string]$Task.State
    verified_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$Evidence | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $EvidencePath
$RecoveryHash = (Get-FileHash -Algorithm SHA256 -Path $EvidencePath).Hash.ToLowerInvariant()

$Activation.restart_recovery_evidence_sha256 = $RecoveryHash
$Activation.restart_recovery_passed = $true
$Activation.service_24_7_verified = $true
if ([bool]$Pending.activate_live_after_reboot) {
    $Activation.order_submission_authorized = $true
}
$Activation.activation_timestamp = [DateTimeOffset]::UtcNow.ToString("o")
$Activation | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ActivationPath

if ([bool]$Pending.activate_live_after_reboot) {
    $Python = (Get-Command python).Source
    $RuntimeScript = "$Root\scripts\qore_fundednext_runtime.py"
    $Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$RuntimeScript`" --mode live --activation var/fundednext/live-activation.json" -WorkingDirectory $Root
    Set-ScheduledTask -TaskName "QORE-FundedNext-Runtime" -Action $Action | Out-Null
    Stop-ScheduledTask -TaskName "QORE-FundedNext-Runtime" -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName "QORE-FundedNext-Runtime"
    Start-Sleep -Seconds 20
    $PostLiveState = Get-Content -Raw $StatePath | ConvertFrom-Json
    $PostLiveHeartbeat = [DateTimeOffset]::Parse([string]$PostLiveState.heartbeat_at)
    if (([DateTimeOffset]::UtcNow - $PostLiveHeartbeat).TotalSeconds -gt 120) {
        throw "live runtime heartbeat failed after activation"
    }
}

$Complete = [ordered]@{
    schema = "qore.fundednext.activation-complete.v1"
    git_sha = [string]$State.git_sha
    account_identity_fingerprint = [string]$State.account_identity_fingerprint
    service_24_7_verified = $true
    restart_recovery_passed = $true
    live_mode_enabled = [bool]$Pending.activate_live_after_reboot
    completed_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$Complete | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 "$Root\artifacts\fundednext_activation_complete.json"
Remove-Item $PendingPath -Force
Unregister-ScheduledTask -TaskName "QORE-FundedNext-PostReboot-Finalize" -Confirm:$false -ErrorAction SilentlyContinue
