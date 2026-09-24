$ErrorActionPreference='Continue'
$Root='C:\QORE_CTRADER_DEMO_FREE'
$Task='QORE-cTrader-DEMO-Free'
$Log="$Root\artifacts\ctrader_demo_free_watchdog.log"
$StatePath="$Root\var\ctrader_demo_signal_runtime\runtime-state.json"
$LockPath="$Root\var\ctrader_demo_signal_runtime\runtime.lock"
while($true){
  $Now=[DateTime]::UtcNow
  $Proc=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -match 'qore_ctrader_demo_free_runtime.py'} | Select-Object -First 1
  $Healthy=$false
  if($Proc){
    $Age=($Now-[DateTime]$Proc.CreationDate).TotalSeconds
    if($Age -lt 180){ $Healthy=$true }
    elseif(Test-Path $StatePath){
      try{
        $State=Get-Content $StatePath -Raw | ConvertFrom-Json
        $Heartbeat=[DateTimeOffset]::Parse($State.heartbeat_at).UtcDateTime
        $Healthy=(($Now-$Heartbeat).TotalSeconds -le 120)
      }catch{$Healthy=$false}
    }
  }
  if(-not $Healthy){
    Add-Content $Log "$([DateTimeOffset]::UtcNow.ToString('o')) recover process=$([bool]$Proc)"
    if($Proc){ Stop-Process -Id $Proc.ProcessId -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2 }
    Stop-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
    $Left=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -match 'qore_ctrader_demo_free_runtime.py'}
    if(-not $Left){ Remove-Item $LockPath -Force -ErrorAction SilentlyContinue }
    Start-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
  }
  Start-Sleep -Seconds 60
}
