$ErrorActionPreference = "Stop"
$Root = "C:\QORE_CTRADER_DEMO_FREE"
$SecretDir = Join-Path $env:LOCALAPPDATA "QORE\cTraderDemo"
$Desktop = [Environment]::GetFolderPath("Desktop")
$OkFile = Join-Path $Desktop "CTRADER_DEMO_CREDENCIALES_OK.txt"
$FailFile = Join-Path $Desktop "CTRADER_DEMO_CREDENCIALES_FALLO.txt"

function Save-DpapiSecret([string]$Name, [string]$Prompt) {
    $value = Read-Host $Prompt -AsSecureString
    $encrypted = ConvertFrom-SecureString $value
    [IO.File]::WriteAllText(
        (Join-Path $SecretDir "$Name.dpapi"),
        $encrypted,
        [Text.UTF8Encoding]::new($false)
    )
}

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

try {
    New-Item -ItemType Directory -Force -Path $SecretDir | Out-Null
    $principal = "$env:USERDOMAIN\$env:USERNAME"
    & icacls.exe $SecretDir /inheritance:r /grant:r "${principal}:(OI)(CI)F" | Out-Null

    Write-Host ""
    Write-Host "QORE - cTrader DEMO"
    Write-Host "Carga local cifrada de credenciales Open API."
    Write-Host "Nada de esto se guarda en el repositorio ni se imprime."
    Write-Host ""

    Save-DpapiSecret "client_id" "Client ID"
    Save-DpapiSecret "client_secret" "Client Secret"
    Save-DpapiSecret "access_token" "Access Token con scope TRADING"
    Save-DpapiSecret "refresh_token" "Refresh Token"
    $env:QORE_CTRADER_CLIENT_ID = Read-DpapiPlain "client_id"
    $env:QORE_CTRADER_CLIENT_SECRET = Read-DpapiPlain "client_secret"
    $env:QORE_CTRADER_ACCESS_TOKEN = Read-DpapiPlain "access_token"
    $env:QORE_CTRADER_REFRESH_TOKEN = Read-DpapiPlain "refresh_token"
    $env:PYTHONPATH = "$Root\src"
    Set-Location $Root

    Write-Host ""
    Write-Host "Validando autenticacion y descubriendo una sola cuenta DEMO..."
    $account = (& python -m qore.infrastructure.ctrader_demo_account_discovery 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $account -notmatch "^[0-9]+$") {
        throw "cTrader DEMO no pudo autenticar o el token no autoriza exactamente una cuenta DEMO."
    }

    [IO.File]::WriteAllText(
        (Join-Path $SecretDir "account_id.txt"),
        $account,
        [Text.UTF8Encoding]::new($false)
    )
    $body = @(
        "QORE cTrader DEMO: CREDENCIALES OK",
        "Cuenta DEMO descubierta y vinculada.",
        "Scope requerido: trading.",
        "Fecha UTC: $([DateTimeOffset]::UtcNow.ToString('o'))"
    ) -join [Environment]::NewLine
    [IO.File]::WriteAllText($OkFile, $body, [Text.UTF8Encoding]::new($false))
    Remove-Item $FailFile -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "CREDENCIALES CTRADER DEMO VALIDADAS."
    Write-Host "Cuenta DEMO descubierta y vinculada sin exponer su identificador."
}
catch {
    $message = $_.Exception.Message
    $failureBody = "QORE cTrader DEMO: FAIL-CLOSED" + [Environment]::NewLine + "Motivo: " + $message
    [IO.File]::WriteAllText(
        $FailFile,
        $failureBody,
        [Text.UTF8Encoding]::new($false)
    )
    Remove-Item $OkFile -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "CONFIGURACION CTRADER DEMO FALLIDA / FAIL-CLOSED"
    Write-Host $message
    Read-Host "Presiona ENTER para cerrar"
    exit 1
}

Read-Host "Presiona ENTER para cerrar"
