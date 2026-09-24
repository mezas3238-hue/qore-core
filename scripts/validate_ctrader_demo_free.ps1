$ErrorActionPreference = "Stop"
$Root = "C:\QORE_CTRADER_DEMO_FREE"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Ok = Join-Path $Desktop "CTRADER_DEMO_FREE_OK.txt"
$Fail = Join-Path $Desktop "CTRADER_DEMO_FREE_FALLO.txt"

try {
    . "$Root\scripts\load_ctrader_demo_credentials.ps1"
    $env:PYTHONPATH = "$Root\src"
    Set-Location $Root
    & python "$Root\scripts\bootstrap_ctrader_demo_free.py"
    if ($LASTEXITCODE -ne 0) {
        throw "bootstrap cTrader DEMO devolvio codigo $LASTEXITCODE"
    }
    $binding = Get-Content -Raw "$Root\var\ctrader_demo_free\binding.json" | ConvertFrom-Json
    $body = @(
        "QORE cTrader DEMO FREE: OK",
        "Entorno: DEMO",
        "Risk: CAPITAL_ALLOCATOR_ONLY",
        "CIBO: SIZING_AND_POSITION_INTELLIGENCE_SOVEREIGN",
        "Balance DEMO: $($binding.balance)",
        "Traders asignados: $($binding.allocations.PSObject.Properties.Count)",
        "Simbolos vinculados: $($binding.contracts.Count)",
        "Fecha UTC: $([DateTimeOffset]::UtcNow.ToString('o'))"
    ) -join [Environment]::NewLine
    [IO.File]::WriteAllText($Ok, $body, [Text.UTF8Encoding]::new($false))
    Remove-Item $Fail -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "CTRADER DEMO FREE VALIDADO."
}
catch {
    $message = $_.Exception.Message
    $failureBody = "QORE cTrader DEMO FREE: FAIL-CLOSED" + [Environment]::NewLine + "Motivo: " + $message
    [IO.File]::WriteAllText(
        $Fail,
        $failureBody,
        [Text.UTF8Encoding]::new($false)
    )
    Remove-Item $Ok -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "CTRADER DEMO FREE FALLIDO / FAIL-CLOSED"
    Write-Host $message
    Read-Host "Presiona ENTER para cerrar"
    exit 1
}

Read-Host "Presiona ENTER para cerrar"
