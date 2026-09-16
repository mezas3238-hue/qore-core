param(
    [Parameter(Mandatory=$true)][switch]$ConfirmLiveCapital,
    [Parameter(Mandatory=$true)][switch]$EaEntitlementVerified,
    [Parameter(Mandatory=$true)][switch]$VpsEntitlementVerified,
    [Parameter(Mandatory=$true)][DateTimeOffset]$RulesValidUntil
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

if (-not $ConfirmLiveCapital -or -not $EaEntitlementVerified -or -not $VpsEntitlementVerified) {
    throw "Explicit Owner confirmation plus EA and VPS entitlement verification are required"
}
$Now = [DateTimeOffset]::UtcNow
if ($RulesValidUntil -le $Now) {
    throw "RulesValidUntil must be an explicit future timestamp"
}

$GitSha = (git rev-parse HEAD).Trim()
if ($GitSha.Length -ne 40) { throw "QORE exact git SHA unavailable" }
$TrackedDirty = @(git status --porcelain --untracked-files=no)
if ($TrackedDirty.Count -ne 0) { throw "Tracked QORE working tree is not clean" }

$StateDir = "$Root\var\fundednext"
$ActivationPath = "$StateDir\live-activation.json"
$CloseoutPath = "$Root\artifacts\fundednext_runtime_closeout.json"
$RecoveryPath = "$Root\artifacts\fundednext_restart_recovery.json"
$SafetyPath = "$StateDir\live-safety.json"
foreach ($required in @($ActivationPath, $CloseoutPath, $RecoveryPath, $SafetyPath)) {
    if (-not (Test-Path $required)) { throw "Required live activation evidence missing: $required" }
}

$Activation = Get-Content -Raw $ActivationPath | ConvertFrom-Json
$Closeout = Get-Content -Raw $CloseoutPath | ConvertFrom-Json
$Recovery = Get-Content -Raw $RecoveryPath | ConvertFrom-Json
$Safety = Get-Content -Raw $SafetyPath | ConvertFrom-Json
if ([string]$Activation.git_sha -ne $GitSha -or [string]$Closeout.git_sha -ne $GitSha -or [string]$Recovery.git_sha -ne $GitSha) {
    throw "Activation/closeout/recovery evidence is not bound to current exact SHA"
}
if (-not [bool]$Closeout.service_24_7_verified -or -not [bool]$Closeout.restart_recovery_passed -or -not [bool]$Closeout.shadow_mode_verified) {
    throw "SHADOW 24/7 and restart closeout is incomplete"
}
if ([bool]$Closeout.live_mode_enabled -or [bool]$Closeout.order_submission_authorized) {
    throw "Closeout artifact must remain pre-LIVE evidence"
}
if (-not [bool]$Safety.account_enabled -or -not [bool]$Safety.gateway_enabled) {
    throw "Account/gateway kill switch must be explicitly enabled before activation"
}

$Activation.ea_entitlement_verified = $true
$Activation.vps_entitlement_verified = $true
$Activation.provider_rules_current = $true
$Activation.no_send_passed = $true
$Activation.shadow_passed = $true
$Activation.service_24_7_verified = $true
$Activation.restart_recovery_passed = $true
$Activation.rules_verified_at = $Now.ToString("o")
$Activation.rules_valid_until = $RulesValidUntil.ToUniversalTime().ToString("o")
$Activation.activation_timestamp = $Now.ToString("o")
$Activation.order_submission_authorized = $true
$Activation | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $ActivationPath

$Python = (Get-Command python).Source
$RuntimeScript = "$Root\scripts\qore_fundednext_runtime.py"
$LiveAction = New-ScheduledTaskAction -Execute $Python -Argument "`"$RuntimeScript`" --mode live --activation var/fundednext/live-activation.json" -WorkingDirectory $Root
Stop-ScheduledTask -TaskName "QORE-FundedNext-Runtime" -ErrorAction SilentlyContinue
Set-ScheduledTask -TaskName "QORE-FundedNext-Runtime" -Action $LiveAction | Out-Null
Start-ScheduledTask -TaskName "QORE-FundedNext-Runtime"
Start-Sleep -Seconds 20
$State = Get-Content -Raw "$StateDir\runtime-state.json" | ConvertFrom-Json
$Heartbeat = [DateTimeOffset]::Parse([string]$State.heartbeat_at)
if ([string]$State.git_sha -ne $GitSha) { throw "LIVE runtime SHA mismatch" }
if (($Now = [DateTimeOffset]::UtcNow) - $Heartbeat -gt [TimeSpan]::FromSeconds(120)) {
    throw "LIVE runtime heartbeat did not become fresh"
}

$Armed = [ordered]@{
    schema = "qore.fundednext.owner-live-activation.v1"
    git_sha = $GitSha
    account_identity_fingerprint = [string]$Activation.account_identity_fingerprint
    ea_entitlement_verified = $true
    vps_entitlement_verified = $true
    provider_rules_current = $true
    rules_valid_until = $RulesValidUntil.ToUniversalTime().ToString("o")
    resident_runtime_mode = "LIVE_ARMED_WAITING_FOR_GENUINE_VT08_SIGNAL"
    synthetic_or_manual_test_order_authorized = $false
    activated_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$Armed | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 "$Root\artifacts\fundednext_owner_live_activation.json"
Write-Host "QORE LIVE runtime armed. No order was created by this activation step."
Write-Host "Runtime remains idle until a genuine certified VT-08 opportunity passes all gates."
