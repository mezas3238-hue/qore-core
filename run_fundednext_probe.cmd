@echo off
setlocal
cd /d "%~dp0"
echo QORE FundedNext MT5 NO-SEND probe
echo No orders will be submitted by this probe.
echo.
python scripts\fundednext_mt5_no_send_probe.py
set "QORE_PROBE_EXIT=%ERRORLEVEL%"
echo.
if "%QORE_PROBE_EXIT%"=="0" (
  echo QORE NO-SEND PROBE PASSED
  if exist "artifacts\fundednext_mt5_no_send_probe.json" (
    echo.
    echo SHA256 evidence:
    certutil -hashfile "artifacts\fundednext_mt5_no_send_probe.json" SHA256
  )
) else (
  echo QORE NO-SEND PROBE FAILED - exit code %QORE_PROBE_EXIT%
)
echo.
pause
exit /b %QORE_PROBE_EXIT%
