@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo QORE FundedNext FIRST-EXECUTION READINESS
echo This workflow uses NO-SEND and order_check only. It never calls order_send.
echo.

for /f %%S in ('git rev-parse HEAD') do set "QORE_GIT_SHA=%%S"
if "%QORE_GIT_SHA%"=="" (
  echo Unable to resolve repository HEAD.
  exit /b 2
)
echo Exact SHA: %QORE_GIT_SHA%

python scripts\fundednext_mt5_no_send_probe.py
if errorlevel 1 exit /b %ERRORLEVEL%

python scripts\fundednext_mt5_shadow_probe.py
if errorlevel 1 exit /b %ERRORLEVEL%

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_fundednext_runtime_task.ps1 -RepoRoot "%CD%" -StateDir "C:\QORE\state"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo Runtime supervisor installed and started.
echo Reboot-recovery evidence is intentionally fail-closed until a real reboot has occurred.
echo After reboot, run scripts\fundednext_reboot_recovery_probe.ps1 and rerun readiness.
echo.

if exist "C:\QORE\state\reboot-recovery.json" (
  python scripts\fundednext_runtime_readiness.py --git-sha "%QORE_GIT_SHA%" --state-dir "C:\QORE\state"
  exit /b %ERRORLEVEL%
)

echo PRE-REBOOT CHECKS COMPLETED. Reboot evidence is still required.
exit /b 3
