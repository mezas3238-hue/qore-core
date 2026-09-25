$ErrorActionPreference='Stop'
$Root='C:\QORE_CTRADER_DEMO_FREE'
. "$Root\scripts\load_ctrader_demo_credentials.ps1"
$env:PYTHONPATH="$Root\src;$Root\scripts"
Set-Location $Root
python "$Root\scripts\ctrader_demo_live_settlement_watcher.py" --root $Root --interval-seconds 30
exit $LASTEXITCODE
