param(
    [Parameter(Mandatory = $true)]
    [string]$ControlRepo,

    [string]$Branch = "main",

    [string]$DeviceId = "vps-vrix",

    [int]$PollSeconds = 3,

    [string]$InstallDir = "$env:ProgramData\QORE\VPSBridge"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this installer from an elevated Administrator PowerShell."
    }
}

Assert-Administrator

$parts = $ControlRepo -split "/", 2
if ($parts.Count -ne 2) {
    throw "ControlRepo must be owner/repo, for example mezas3238-hue/qore-vps-control"
}

$SourceAgent = Join-Path $PSScriptRoot "QoreVpsBridge.ps1"
if (-not (Test-Path -LiteralPath $SourceAgent)) {
    throw "Agent script not found beside installer: $SourceAgent"
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$AgentPath = Join-Path $InstallDir "QoreVpsBridge.ps1"
$ConfigPath = Join-Path $InstallDir "config.json"
$TokenPath = Join-Path $InstallDir "token.bin"

Copy-Item -Force -LiteralPath $SourceAgent -Destination $AgentPath

$config = @{
    schema = "qore-vps-bridge-config-v1"
    control_repo = $ControlRepo
    branch = $Branch
    device_id = $DeviceId
    poll_seconds = [Math]::Max(2, $PollSeconds)
}
$config | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

Write-Host ""
Write-Host "Enter a fine-grained GitHub token restricted ONLY to $ControlRepo."
Write-Host "Required repository permission: Contents = Read and write."
$secureToken = Read-Host "GitHub token" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ([string]::IsNullOrWhiteSpace($plain)) {
        throw "Token cannot be empty."
    }

    $bytes = [Text.Encoding]::UTF8.GetBytes($plain)
    $protected = [Security.Cryptography.ProtectedData]::Protect(
        $bytes,
        $null,
        [Security.Cryptography.DataProtectionScope]::LocalMachine
    )
    [IO.File]::WriteAllBytes($TokenPath, $protected)

    [Array]::Clear($bytes, 0, $bytes.Length)
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $plain = $null
}

$acl = Get-Acl -LiteralPath $InstallDir
$acl.SetAccessRuleProtection($true, $false)
$systemRule = [Security.AccessControl.FileSystemAccessRule]::new(
    "SYSTEM",
    "FullControl",
    "ContainerInherit,ObjectInherit",
    "None",
    "Allow"
)
$adminRule = [Security.AccessControl.FileSystemAccessRule]::new(
    "BUILTIN\Administrators",
    "FullControl",
    "ContainerInherit,ObjectInherit",
    "None",
    "Allow"
)
$acl.SetAccessRule($systemRule)
$acl.AddAccessRule($adminRule)
Set-Acl -LiteralPath $InstallDir -AclObject $acl

$taskName = "QORE VPS Control Bridge"
$arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -ConfigPath "{1}"' -f $AgentPath, $ConfigPath
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Start-Sleep -Seconds 2
$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName

Write-Host ""
Write-Host "QORE VPS Control Bridge installed."
Write-Host "InstallDir : $InstallDir"
Write-Host "Task       : $taskName"
Write-Host "State      : $($task.State)"
Write-Host "LastResult : $($info.LastTaskResult)"
Write-Host ""
Write-Host "Within about 30 seconds the private control repository should contain:"
Write-Host "  heartbeats/$DeviceId.json"
