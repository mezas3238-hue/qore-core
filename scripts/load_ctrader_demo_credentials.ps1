$ErrorActionPreference = "Stop"
$SecretDir = Join-Path $env:LOCALAPPDATA "QORE\cTraderDemo"

function Read-DpapiPlain([string]$Name) {
    $encrypted = [IO.File]::ReadAllText((Join-Path $SecretDir "$Name.dpapi"))
    $secure = ConvertTo-SecureString $encrypted
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

foreach ($required in @("client_id.dpapi","client_secret.dpapi","access_token.dpapi","refresh_token.dpapi","account_id.txt")) {
    if (-not (Test-Path (Join-Path $SecretDir $required))) {
        throw "cTrader DEMO credentials are not configured"
    }
}$env:QORE_CTRADER_CLIENT_ID = Read-DpapiPlain "client_id"
$env:QORE_CTRADER_CLIENT_SECRET = Read-DpapiPlain "client_secret"
$env:QORE_CTRADER_ACCESS_TOKEN = Read-DpapiPlain "access_token"
$env:QORE_CTRADER_REFRESH_TOKEN = Read-DpapiPlain "refresh_token"
$env:QORE_CTRADER_DEMO_ACCOUNT_ID = [IO.File]::ReadAllText((Join-Path $SecretDir "account_id.txt")).Trim()
if ($env:QORE_CTRADER_DEMO_ACCOUNT_ID -notmatch "^[0-9]+$") {
    throw "cTrader DEMO account id is invalid"
}