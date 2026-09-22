param(
    [Parameter(Mandatory=$true)][ValidateSet("account", "gateway", "market", "trader")][string]$Scope,
    [Parameter(Mandatory=$true)][ValidateSet("enable", "disable")][string]$Action,
    [string]$Name
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Path = "$Root\var\fundednext\live-safety.json"
if (-not (Test-Path $Path)) { throw "Live safety state does not exist" }
$State = Get-Content -Raw $Path | ConvertFrom-Json
$Enabled = $Action -eq "enable"

if ($Scope -eq "account") {
    $State.account_enabled = $Enabled
} elseif ($Scope -eq "gateway") {
    $State.gateway_enabled = $Enabled
} elseif ($Scope -eq "market") {
    if ($Name -notin @("AUDJPY", "GBPUSD", "GBPJPY")) { throw "Unknown live market" }
    $Values = @($State.disabled_markets)
    if ($Enabled) { $Values = @($Values | Where-Object { $_ -ne $Name }) }
    elseif ($Name -notin $Values) { $Values += $Name }
    $State.disabled_markets = @($Values | Sort-Object -Unique)
} else {
    if ([string]::IsNullOrWhiteSpace($Name)) { throw "Trader name is required" }
    $Values = @($State.disabled_traders)
    if ($Enabled) { $Values = @($Values | Where-Object { $_ -ne $Name }) }
    elseif ($Name -notin $Values) { $Values += $Name }
    $State.disabled_traders = @($Values | Sort-Object -Unique)
}

$Temp = "$Path.tmp"
$State | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $Temp
Move-Item -Force $Temp $Path
Write-Host "FundedNext kill switch updated: $Scope $Action $Name"
