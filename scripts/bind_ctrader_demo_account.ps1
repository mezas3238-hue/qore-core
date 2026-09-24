$ErrorActionPreference = "Stop"
$Root = "C:\QORE_CTRADER_DEMO_FREE"
$SecretDir = Join-Path $env:LOCALAPPDATA "QORE\cTraderDemo"
$AccountPath = Join-Path $SecretDir "account_id.txt"
$HadAccount = Test-Path $AccountPath
$Backup = $null
if ($HadAccount) { $Backup = [IO.File]::ReadAllText($AccountPath) }
if (-not $HadAccount) { [IO.File]::WriteAllText($AccountPath, "1", [Text.UTF8Encoding]::new($false)) }
try {
    . "$Root\scripts\load_ctrader_demo_credentials.ps1"
    $env:PYTHONPATH = "$Root\src"
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = (Get-Command python).Source
    $psi.Arguments = "-m qore.infrastructure.ctrader_demo_account_discovery"
    $psi.WorkingDirectory = $Root
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $p = [Diagnostics.Process]::new()
    $p.StartInfo = $psi
    [void]$p.Start()
    $stdout = $p.StandardOutput.ReadToEnd().Trim()
    $stderr = $p.StandardError.ReadToEnd().Trim()
    $p.WaitForExit()
    if ($p.ExitCode -ne 0 -or $stdout -notmatch "^[0-9]+$") {
        throw "cTrader DEMO account discovery failed: $stderr"
    }
    [IO.File]::WriteAllText($AccountPath, $stdout, [Text.UTF8Encoding]::new($false))
    Write-Output "ACCOUNT_BIND_OK"
}
catch {
    if ($HadAccount) { [IO.File]::WriteAllText($AccountPath, $Backup, [Text.UTF8Encoding]::new($false)) }
    elseif (Test-Path $AccountPath) { Remove-Item $AccountPath -Force }
    throw
}