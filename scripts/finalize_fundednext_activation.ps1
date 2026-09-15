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
$ServiceStarted = [DateTimeOffset]::Parse([string]$State.service_started_at)
$Task = Get-ScheduledTask -TaskName "QORE-FundedNext-Runtime"

if ([bool]$Pending.activate_live_after_reboot) {
    throw "reboot readiness proof must remain SHADOW; LIVE activation is separate"
}
if ([string]$State.git_sha -ne [string]$Pending.git_sha) { throw "post-reboot SHA mismatch" }
if ([string]$State.account_identity_fingerprint -ne [string]$Pending.account_identity_fingerprint) {
    throw "post-reboot account fingerprint mismatch"
}
if ($ServiceStarted -lt $Boot) { throw "runtime service was not restarted after this Windows boot" }
if ($Heartbeat -lt $Boot) { throw "runtime produced no heartbeat after this Windows boot" }
if ($Reconciled -lt $Boot) { throw "runtime produced no reconciliation after this Windows boot" }
if (([DateTimeOffset]::UtcNow - $Heartbeat).TotalSeconds -gt 120) {
    throw "post-reboot runtime heartbeat stale"
}
if ([string]$Task.State -ne "Running") { throw "QORE runtime task is not running" }
if (-not (Test-Path "$StateDir\capital-checkpoint.json") -or -not (Test-Path "$StateDir\capital-checkpoint.backup.json")) {
    throw "durable capital checkpoint copies missing after reboot"
}

$EvidencePath = "$Root\artifacts\fundednext_restart_recovery.json"
$Evidence = [ordered]@{
    schema = "qore.fundednext.restart-recovery.v2"
    ok = $true
    mode = "SHADOW_NO_SEND"
    git_sha = [string]$State.git_sha
    account_identity_fingerprint = [string]$State.account_identity_fingerprint
    windows_boot_at = $Boot.ToUniversalTime().ToString("o")
    service_started_at = $ServiceStarted.ToUniversalTime().ToString("o")
    heartbeat_at = $Heartbeat.ToUniversalTime().ToString("o")
    reconciliation_at = $Reconciled.ToUniversalTime().ToString("o")
    scheduled_task_state = [string]$Task.State
    capital_checkpoint_recovered = $true
    order_submission_authorized = $false
    verified_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$Evidence | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $EvidencePath
$RecoveryHash = (Get-FileHash -Algorithm SHA256 -Path $EvidencePath).Hash.ToLowerInvariant()

$Activation.restart_recovery_evidence_sha256 = $RecoveryHash
$Activation.restart_recovery_passed = $true
$Activation.service_24_7_verified = $true
$Activation.order_submission_authorized = $false
$Activation.activation_timestamp = [DateTimeOffset]::UtcNow.ToString("o")
$Activation | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ActivationPath

$Complete = [ordered]@{
    schema = "qore.fundednext.runtime-closeout.v2"
    git_sha = [string]$State.git_sha
    account_identity_fingerprint = [string]$State.account_identity_fingerprint
    service_24_7_verified = $true
    restart_recovery_passed = $true
    shadow_mode_verified = $true
    live_mode_enabled = $false
    order_submission_authorized = $false
    completed_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$Complete | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 "$Root\artifacts\fundednext_runtime_closeout.json"
Remove-Item $PendingPath -Force
Unregister-ScheduledTask -TaskName "QORE-FundedNext-PostReboot-Finalize" -Confirm:$false -ErrorAction SilentlyContinue
