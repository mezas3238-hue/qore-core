$ErrorActionPreference='Continue'
$Root='C:\QORE_CTRADER_DEMO_FREE'
while($true){
  try{
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$Root\scripts\run_ctrader_demo_free_performance.ps1"
  }catch{
    $msg = $_.Exception.Message
    Add-Content -Path "$Root\artifacts\ctrader_demo_free_report_errors.log" -Value "$(Get-Date -Format o) $msg"
  }
  Start-Sleep -Seconds 300
}
