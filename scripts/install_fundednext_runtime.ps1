param(
    [switch]$ActivateLive,
    [switch]$RebootNow
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

# Deployment is fail-closed: quiesce the previous resident runtime and watchdog
# before validating or rebinding a new exact SHA. Existing tasks are recreated
# later in this installer. If closeout fails, they remain disabled rather than
# allowing a mixed-SHA process to restart.
$RuntimeTaskName = "QORE-FundedNext-Runtime"
$WatchdogTaskName = "QORE-FundedNext-Watchdog"
$RulesRefreshTaskName = "QORE-FundedNext-Rules-Refresh"
foreach ($TaskName in @($RuntimeTaskName, $WatchdogTaskName, $RulesRefreshTaskName)) {
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -ne $ExistingTask) {
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    }
}
$StopDeadline = [DateTimeOffset]::UtcNow.AddSeconds(30)
do {
    $RuntimeProcesses = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -eq "python.exe" -and
                $_.CommandLine -match "qore_fundednext_runtime\.py"
            }
    )
    if ($RuntimeProcesses.Count -eq 0) { break }
    Start-Sleep -Milliseconds 500
} while ([DateTimeOffset]::UtcNow -lt $StopDeadline)
if ($RuntimeProcesses.Count -ne 0) {
    throw "Prior QORE runtime could not be quiesced for exact-SHA deployment"
}
Remove-Item "$Root\var\fundednext\runtime.lock" -Force -ErrorAction SilentlyContinue

if ($ActivateLive) {
    throw "LIVE activation remains a separate Owner-governance event; installer is SHADOW only"
}

function Sha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

$GitSha = (git rev-parse HEAD).Trim()
if ($GitSha.Length -ne 40) { throw "QORE exact git SHA unavailable" }
$TrackedDirty = @(git status --porcelain --untracked-files=no)
if ($TrackedDirty.Count -ne 0) {
    throw "Tracked QORE working tree differs from exact Git SHA"
}

Write-Host "QORE exact SHA: $GitSha"
Write-Host "Using the existing QORE/MT5 VPS installation; no reinstall is performed."
Write-Host "Running fresh exact-SHA NO-SEND evidence probe..."
python "$Root\scripts\fundednext_mt5_no_send_probe.py"
if ($LASTEXITCODE -ne 0) { throw "NO-SEND probe failed" }

Write-Host "Running broker-native certified-direction order_check probe (still NO-SEND)..."
python "$Root\scripts\fundednext_mt5_order_check_probe.py"
if ($LASTEXITCODE -ne 0) { throw "MT5 order_check probe failed" }

$NoSendPath = "$Root\artifacts\fundednext_mt5_no_send_probe.json"
$ShadowPath = "$Root\artifacts\fundednext_mt5_order_check_probe.json"
$NoSend = Get-Content -Raw $NoSendPath | ConvertFrom-Json
$Shadow = Get-Content -Raw $ShadowPath | ConvertFrom-Json
if (-not $NoSend.ok -or [string]$NoSend.git_sha -ne $GitSha) {
    throw "NO-SEND evidence is not bound to the exact SHA"
}
if (-not [bool]$NoSend.startup_reconciliation.clean) {
    throw "Initial SHADOW closeout requires a clean broker reconciliation state"
}
if ([bool]$NoSend.safety.order_send_called) {
    throw "NO-SEND evidence reports order_send activity"
}
if (-not $Shadow.ok -or [string]$Shadow.git_sha -ne $GitSha -or $Shadow.order_send_called) {
    throw "Shadow evidence is not exact-SHA/no-send"
}
$NoSendFingerprint = [string]$NoSend.account.identity_fingerprint
$ShadowFingerprint = [string]$Shadow.account_identity_fingerprint
if ($NoSendFingerprint.Length -ne 64 -or $NoSendFingerprint -ne $ShadowFingerprint) {
    throw "NO-SEND and order_check account identity do not match"
}

$ProviderContract = "$Root\src\qore\infrastructure\fundednext_stellar_instant.py"
$Now = [DateTimeOffset]::UtcNow
$ActivationDir = "$Root\var\fundednext"
New-Item -ItemType Directory -Force -Path $ActivationDir | Out-Null
$ActivationPath = "$ActivationDir\live-activation.json"
$SafetyPath = "$ActivationDir\live-safety.json"
$ZeroHash = "0" * 64
$Activation = [ordered]@{
    git_sha = $GitSha
    account_identity_fingerprint = $ShadowFingerprint
    expected_server = "FundedNext-Server"
    provider_rules_fingerprint = (Sha256 $ProviderContract)
    no_send_evidence_sha256 = (Sha256 $NoSendPath)
    shadow_evidence_sha256 = (Sha256 $ShadowPath)
    restart_recovery_evidence_sha256 = $ZeroHash
    ea_entitlement_verified = $false
    vps_entitlement_verified = $false
    provider_rules_current = $false
    no_send_passed = $true
    shadow_passed = $true
    service_24_7_verified = $false
    restart_recovery_passed = $false
    activation_timestamp = $Now.ToString("o")
    order_submission_authorized = $false
}
$Activation | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ActivationPath

Write-Host "Rebinding retained capital/runtime state to the exact SHADOW SHA without changing economics..."
python "$Root\scripts\rebind_fundednext_shadow_state.py" --root "$Root"
if ($LASTEXITCODE -ne 0) { throw "retained SHADOW state SHA rebind failed" }

if (-not (Test-Path $SafetyPath)) {
    $Safety = [ordered]@{
        schema = "qore.fundednext.live-safety.v1"
        account_enabled = $true
        gateway_enabled = $true
        disabled_traders = @()
        disabled_markets = @()
    }
    $Safety | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $SafetyPath
}

$Python = (Get-Command python).Source
$RuntimeScript = "$Root\scripts\qore_fundednext_runtime.py"
$WatchdogScript = "$Root\scripts\qore_fundednext_watchdog.ps1"
$FinalizeScript = "$Root\scripts\finalize_fundednext_activation.ps1"
$RulesRefreshScript = "$Root\scripts\qore_fundednext_rules_refresh.py"

$RuntimeAction = New-ScheduledTaskAction -Execute $Python -Argument "`"$RuntimeScript`" --mode shadow --activation var/fundednext/live-activation.json" -WorkingDirectory $Root
$RuntimeTrigger = New-ScheduledTaskTrigger -AtStartup
$RuntimeTrigger.Delay = "PT30S"
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName "QORE-FundedNext-Runtime" -Action $RuntimeAction -Trigger $RuntimeTrigger -Principal $Principal -Settings $Settings -Force | Out-Null

$WatchdogAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WatchdogScript`"" -WorkingDirectory $Root
$WatchdogTrigger = New-ScheduledTaskTrigger -Once -At ([DateTime]::Now.AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "QORE-FundedNext-Watchdog" -Action $WatchdogAction -Trigger $WatchdogTrigger -Principal $Principal -Settings $Settings -Force | Out-Null

$RulesRefreshAction = New-ScheduledTaskAction -Execute $Python -Argument "`"$RulesRefreshScript`" --root `"$Root`"" -WorkingDirectory $Root
$RulesRefreshTrigger = New-ScheduledTaskTrigger -Once -At ([DateTime]::Now.AddMinutes(2)) -RepetitionInterval (New-TimeSpan -Hours 6)
$RulesRefreshStartupTrigger = New-ScheduledTaskTrigger -AtStartup
$RulesRefreshStartupTrigger.Delay = "PT120S"
Register-ScheduledTask -TaskName "QORE-FundedNext-Rules-Refresh" -Action $RulesRefreshAction -Trigger @($RulesRefreshTrigger, $RulesRefreshStartupTrigger) -Principal $Principal -Settings $Settings -Force | Out-Null

& $Python $RulesRefreshScript --root $Root
if ($LASTEXITCODE -ne 0) { throw "initial provider-rule refresh failed" }

Start-ScheduledTask -TaskName "QORE-FundedNext-Runtime"
Start-Sleep -Seconds 35
$StatePath = "$ActivationDir\runtime-state.json"
if (-not (Test-Path $StatePath)) { throw "runtime heartbeat/state was not created" }
$State = Get-Content -Raw $StatePath | ConvertFrom-Json
$Heartbeat = [DateTimeOffset]::Parse([string]$State.heartbeat_at)
if (([DateTimeOffset]::UtcNow - $Heartbeat).TotalSeconds -gt 120) {
    throw "runtime heartbeat is stale"
}
if ([string]$State.git_sha -ne $GitSha) { throw "runtime state SHA mismatch" }
if ([string]$State.account_identity_fingerprint -ne $ShadowFingerprint) {
    throw "runtime account fingerprint mismatch"
}
if (-not (Test-Path "$ActivationDir\capital-checkpoint.json") -or -not (Test-Path "$ActivationDir\capital-checkpoint.backup.json")) {
    throw "durable capital checkpoint copies were not created"
}

$Activation.service_24_7_verified = $true
$Activation | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ActivationPath

$PreReboot = [ordered]@{
    schema = "qore.fundednext.pre-reboot-readiness.v2"
    git_sha = $GitSha
    account_identity_fingerprint = $ShadowFingerprint
    heartbeat_at = [string]$State.heartbeat_at
    service_started_at = [string]$State.service_started_at
    no_send_sha256 = (Sha256 $NoSendPath)
    shadow_sha256 = (Sha256 $ShadowPath)
    activate_live_after_reboot = $false
    recorded_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$PendingPath = "$ActivationDir\pending-reboot-readiness.json"
$PreReboot | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $PendingPath

$FinalizeAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$FinalizeScript`"" -WorkingDirectory $Root
$FinalizeTrigger = New-ScheduledTaskTrigger -AtStartup
$FinalizeTrigger.Delay = "PT90S"
Register-ScheduledTask -TaskName "QORE-FundedNext-PostReboot-Finalize" -Action $FinalizeAction -Trigger $FinalizeTrigger -Principal $Principal -Settings $Settings -Force | Out-Null

Write-Host "QORE runtime bound in SHADOW to exact clean SHA with durable capital/safety state."
Write-Host "LIVE/order_send remains disabled; no provider-rule freshness was fabricated."
if ($RebootNow) {
    Write-Host "Rebooting VPS only to prove exact-SHA recovery, not to reinstall QORE."
    Restart-Computer -Force
} else {
    Write-Host "Reboot proof can be run when the final SHA is selected for physical closeout."
}
