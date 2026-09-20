param(
    [Parameter(Mandatory=$true)][switch]$ConfirmLiveCapital,
    [Parameter(Mandatory=$true)][switch]$EaEntitlementVerified,
    [Parameter(Mandatory=$true)][switch]$VpsEntitlementVerified
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$RuntimeTaskName = "QORE-FundedNext-Runtime"
$WatchdogTaskName = "QORE-FundedNext-Watchdog"
$StateDir = "$Root\var\fundednext"
$ActivationPath = "$StateDir\live-activation.json"
$StatePath = "$StateDir\runtime-state.json"
$CloseoutPath = "$Root\artifacts\fundednext_runtime_closeout.json"
$RecoveryPath = "$Root\artifacts\fundednext_restart_recovery.json"
$SafetyPath = "$StateDir\live-safety.json"
$OwnerArtifactPath = "$Root\artifacts\fundednext_owner_live_activation.json"
$FailureArtifactPath = "$Root\artifacts\fundednext_live_activation_failed.json"
$RuntimeScript = "$Root\scripts\qore_fundednext_runtime.py"
$RulesRefreshScript = "$Root\scripts\qore_fundednext_rules_refresh.py"
$RulesRefreshPath = "$StateDir\provider-rules-refresh.json"
$RulesRefreshTaskName = "QORE-FundedNext-Rules-Refresh"

function Write-JsonAtomic([object]$Value, [string]$Path) {
    $Temp = "$Path.tmp.$PID"
    $Json = $Value | ConvertTo-Json -Depth 10
    [IO.File]::WriteAllText(
        $Temp,
        $Json + [Environment]::NewLine,
        [Text.UTF8Encoding]::new($false)
    )
    Move-Item -Force $Temp $Path
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

function Wait-QoreRuntimeStopped([int]$TimeoutSeconds = 30) {
    $Deadline = [DateTimeOffset]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        $Processes = @(Get-QoreRuntimeProcesses)
        if ($Processes.Count -eq 0) { return }
        Start-Sleep -Milliseconds 500
    } while ([DateTimeOffset]::UtcNow -lt $Deadline)
    throw "previous QORE runtime did not terminate before LIVE transition"
}

function Assert-NewLiveRuntime(
    [DateTimeOffset]$AttemptStartedAt,
    [string]$GitSha,
    [int]$TimeoutSeconds = 60
) {
    $Deadline = [DateTimeOffset]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        $Processes = @(Get-QoreRuntimeProcesses)
        if ($Processes.Count -gt 1) {
            throw "multiple QORE runtime processes detected during LIVE activation"
        }
        if ($Processes.Count -eq 1 -and
            [string]$Processes[0].CommandLine -match "--mode\s+live(?:\s|$)" -and
            (Test-Path $StatePath)) {
            try {
                $State = Get-Content -Raw $StatePath | ConvertFrom-Json
                $ServiceStarted = [DateTimeOffset]::Parse([string]$State.service_started_at)
                $Heartbeat = [DateTimeOffset]::Parse([string]$State.heartbeat_at)
                $Reconciled = [DateTimeOffset]::Parse([string]$State.last_reconciliation_at)
                $Task = Get-ScheduledTask -TaskName $RuntimeTaskName
                if (
                    [string]$State.git_sha -eq $GitSha -and
                    $ServiceStarted -ge $AttemptStartedAt -and
                    $Heartbeat -ge $ServiceStarted -and
                    $Reconciled -ge $ServiceStarted -and
                    ([DateTimeOffset]::UtcNow - $Heartbeat).TotalSeconds -le 30 -and
                    [string]$Task.State -eq "Running"
                ) {
                    return [pscustomobject]@{
                        Process = $Processes[0]
                        State = $State
                        Task = $Task
                    }
                }
            } catch {
                # Runtime may still be starting; continue polling until timeout.
            }
        }
        Start-Sleep -Seconds 2
    } while ([DateTimeOffset]::UtcNow -lt $Deadline)
    throw "LIVE runtime did not produce a new verified process/state after activation"
}

function Restore-ShadowFailClosed(
    [object]$Activation,
    [string]$Python
) {
    $Activation.order_submission_authorized = $false
    Write-JsonAtomic $Activation $ActivationPath
    Remove-Item $OwnerArtifactPath -Force -ErrorAction SilentlyContinue
    Disable-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue | Out-Null
    Stop-ScheduledTask -TaskName $RuntimeTaskName -ErrorAction SilentlyContinue
    try {
        Wait-QoreRuntimeStopped 15
    } catch {
        @(Get-QoreRuntimeProcesses) | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 1
    }
    Remove-Item "$StateDir\runtime.lock" -Force -ErrorAction SilentlyContinue
    $ShadowAction = New-ScheduledTaskAction `
        -Execute $Python `
        -Argument "`"$RuntimeScript`" --mode shadow --activation var/fundednext/live-activation.json" `
        -WorkingDirectory $Root
    Set-ScheduledTask -TaskName $RuntimeTaskName -Action $ShadowAction | Out-Null
    Enable-ScheduledTask -TaskName $RuntimeTaskName | Out-Null
    Enable-ScheduledTask -TaskName $WatchdogTaskName | Out-Null
    Start-ScheduledTask -TaskName $RuntimeTaskName
}

if (-not $ConfirmLiveCapital -or -not $EaEntitlementVerified -or -not $VpsEntitlementVerified) {
    throw "Explicit Owner confirmation plus EA and VPS entitlement verification are required"
}
$AttemptStartedAt = [DateTimeOffset]::UtcNow

$GitSha = (git rev-parse HEAD).Trim()
if ($GitSha.Length -ne 40) { throw "QORE exact git SHA unavailable" }
$TrackedDirty = @(git status --porcelain --untracked-files=no)
if ($TrackedDirty.Count -ne 0) { throw "Tracked QORE working tree is not clean" }

foreach ($required in @($ActivationPath, $CloseoutPath, $RecoveryPath, $SafetyPath)) {
    if (-not (Test-Path $required)) {
        throw "Required live activation evidence missing: $required"
    }
}

$Activation = Get-Content -Raw $ActivationPath | ConvertFrom-Json
$Closeout = Get-Content -Raw $CloseoutPath | ConvertFrom-Json
$Recovery = Get-Content -Raw $RecoveryPath | ConvertFrom-Json
$Safety = Get-Content -Raw $SafetyPath | ConvertFrom-Json
if (
    [string]$Activation.git_sha -ne $GitSha -or
    [string]$Closeout.git_sha -ne $GitSha -or
    [string]$Recovery.git_sha -ne $GitSha
) {
    throw "Activation/closeout/recovery evidence is not bound to current exact SHA"
}
if (
    -not [bool]$Closeout.service_24_7_verified -or
    -not [bool]$Closeout.restart_recovery_passed -or
    -not [bool]$Closeout.shadow_mode_verified
) {
    throw "SHADOW 24/7 and restart closeout is incomplete"
}
if ([bool]$Closeout.live_mode_enabled -or [bool]$Closeout.order_submission_authorized) {
    throw "Closeout artifact must remain pre-LIVE evidence"
}
if (-not [bool]$Safety.account_enabled -or -not [bool]$Safety.gateway_enabled) {
    throw "Account/gateway kill switch must be explicitly enabled before activation"
}

$Python = (Get-Command python).Source
if (-not (Get-ScheduledTask -TaskName $RulesRefreshTaskName -ErrorAction SilentlyContinue)) {
    throw "Provider-rule auto-refresh task is not installed"
}
& $Python $RulesRefreshScript --root $Root
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $RulesRefreshPath)) {
    throw "Automated provider-rule verification failed"
}
$RulesRefresh = Get-Content -Raw $RulesRefreshPath | ConvertFrom-Json
if ([string]$RulesRefresh.schema -ne "qore.fundednext.provider-rules-refresh.v3") {
    throw "Provider-rule verification schema mismatch"
}
if ([string]$RulesRefresh.provider_rules_fingerprint -ne [string]$Activation.provider_rules_fingerprint) {
    throw "Provider-rule verification fingerprint mismatch"
}
if (
    -not [bool]$RulesRefresh.facts.no_daily_loss_limit -or
    [string]$RulesRefresh.facts.maximum_loss_fraction -ne "0.06" -or
    -not [bool]$RulesRefresh.facts.trailing_maximum_loss -or
    -not [bool]$RulesRefresh.facts.ea_allowed_mt5 -or
    [string]$RulesRefresh.facts.cumulative_open_risk_fraction -ne "0.03" -or
    [string]$RulesRefresh.facts.reclassified_open_risk_fraction -ne "0.01" -or
    -not [bool]$RulesRefresh.facts.cumulative_open_risk_applies -or
    -not [bool]$RulesRefresh.facts.stop_loss_required -or
    [int]$RulesRefresh.facts.quick_strike_seconds -ne 30 -or
    [string]$RulesRefresh.facts.news_profit_attribution_fraction -ne "0.40" -or
    [int]$RulesRefresh.facts.inactivity_calendar_days -ne 30 -or
    [bool]$RulesRefresh.facts.account_merging_allowed
) {
    throw "Provider-rule verification facts do not match the frozen Stellar Instant contract"
}
Remove-Item $OwnerArtifactPath -Force -ErrorAction SilentlyContinue
Disable-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue | Out-Null
Stop-ScheduledTask -TaskName $RuntimeTaskName -ErrorAction SilentlyContinue
Wait-QoreRuntimeStopped 30
Remove-Item "$StateDir\runtime.lock" -Force -ErrorAction SilentlyContinue

$LiveAction = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$RuntimeScript`" --mode live --activation var/fundednext/live-activation.json" `
    -WorkingDirectory $Root
Set-ScheduledTask -TaskName $RuntimeTaskName -Action $LiveAction | Out-Null

$Activation.ea_entitlement_verified = $true
$Activation.vps_entitlement_verified = $true
$Activation.provider_rules_current = $true
$Activation.no_send_passed = $true
$Activation.shadow_passed = $true
$Activation.service_24_7_verified = $true
$Activation.restart_recovery_passed = $true
$Activation.activation_timestamp = $AttemptStartedAt.ToString("o")
$Activation.order_submission_authorized = $true
Write-JsonAtomic $Activation $ActivationPath

try {
    Enable-ScheduledTask -TaskName $RuntimeTaskName | Out-Null
    Start-ScheduledTask -TaskName $RuntimeTaskName
    $Verified = Assert-NewLiveRuntime $AttemptStartedAt $GitSha 60

    Enable-ScheduledTask -TaskName $WatchdogTaskName | Out-Null
    Start-ScheduledTask -TaskName $WatchdogTaskName
    Start-Sleep -Seconds 3
    $WatchdogInfo = Get-ScheduledTaskInfo -TaskName $WatchdogTaskName
    if ([int]$WatchdogInfo.LastTaskResult -ne 0) {
        throw "LIVE watchdog self-check failed"
    }

    $State = $Verified.State
    $Process = $Verified.Process
    $Armed = [ordered]@{
        schema = "qore.fundednext.owner-live-activation.v3"
        git_sha = $GitSha
        account_identity_fingerprint = [string]$Activation.account_identity_fingerprint
        ea_entitlement_verified = $true
        vps_entitlement_verified = $true
        provider_rules_current = $true
        rules_refresh_mode = "AUTOMATIC_JIT_BEFORE_ORDER_SEND_PLUS_6H_PREWARM"
        manual_rule_expiry_required = $false
        provider_maximum_loss_fraction = "0.06"
        provider_cumulative_open_risk_fraction = "0.03"
        provider_reclassified_open_risk_fraction = "0.01"
        provider_stop_loss_required = $true
        certified_policy_schema = "qore.fundednext.provider-rules-refresh.v3"
        resident_runtime_mode = "LIVE_ARMED_WAITING_FOR_GENUINE_VT08_SIGNAL"
        runtime_pid = [int]$Process.ProcessId
        service_started_at = [string]$State.service_started_at
        heartbeat_at = [string]$State.heartbeat_at
        reconciliation_at = [string]$State.last_reconciliation_at
        scheduled_task_state = "Running"
        watchdog_last_result = [int]$WatchdogInfo.LastTaskResult
        synthetic_or_manual_test_order_authorized = $false
        activated_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    Write-JsonAtomic $Armed $OwnerArtifactPath
    Remove-Item $FailureArtifactPath -Force -ErrorAction SilentlyContinue
    Write-Host "QORE LIVE runtime armed and independently verified."
    Write-Host "No order was created by this activation step."
    Write-Host "Runtime remains idle until a genuine certified VT-08 opportunity passes all gates."
} catch {
    $Reason = $_.Exception.Message
    try {
        Restore-ShadowFailClosed $Activation $Python
    } catch {
        $Activation.order_submission_authorized = $false
        Write-JsonAtomic $Activation $ActivationPath
        Disable-ScheduledTask -TaskName $RuntimeTaskName -ErrorAction SilentlyContinue | Out-Null
        Disable-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue | Out-Null
    }
    $Failure = [ordered]@{
        schema = "qore.fundednext.live-activation-attempt-failed.v2"
        git_sha = $GitSha
        reason = $Reason
        failed_closed = $true
        recorded_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    Write-JsonAtomic $Failure $FailureArtifactPath
    throw "LIVE activation failed closed: $Reason"
}
