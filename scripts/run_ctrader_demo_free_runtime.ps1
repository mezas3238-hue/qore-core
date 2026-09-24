$ErrorActionPreference='Stop'
$Root='C:\QORE_CTRADER_DEMO_FREE'
. "$Root\scripts\load_ctrader_demo_credentials.ps1"
$env:PYTHONPATH="$Root\src;$Root\scripts"
Set-Location $Root
python "$Root\scripts\qore_ctrader_demo_free_runtime.py" --mode demo
$Code=$LASTEXITCODE
if($Code -ne 0){ exit $Code }
exit 0
