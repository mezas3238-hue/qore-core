param(
    [string]$ConfigPath = "$env:ProgramData\QORE\VPSBridge\config.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BridgeVersion = "0.1.0"
$InstallDir = Split-Path -Parent $ConfigPath
$LogDir = Join-Path $InstallDir "logs"
$StatePath = Join-Path $InstallDir "state.json"
$TokenPath = Join-Path $InstallDir "token.bin"

New-Item -ItemType Directory -Force -Path $InstallDir, $LogDir | Out-Null
$LogPath = Join-Path $LogDir ("bridge-" + (Get-Date -Format "yyyyMMdd") + ".log")

function Write-BridgeLog {
    param([string]$Message)
    $line = "{0} {1}" -f ([DateTime]::UtcNow.ToString("o")), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Read-ProtectedToken {
    if (-not (Test-Path -LiteralPath $TokenPath)) {
        throw "Encrypted token file not found: $TokenPath"
    }
    $protected = [IO.File]::ReadAllBytes($TokenPath)
    $bytes = [Security.Cryptography.ProtectedData]::Unprotect(
        $protected,
        $null,
        [Security.Cryptography.DataProtectionScope]::LocalMachine
    )
    return [Text.Encoding]::UTF8.GetString($bytes)
}

function Load-State {
    if (-not (Test-Path -LiteralPath $StatePath)) {
        return @{ completed = @{} }
    }
    try {
        $raw = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8
        $obj = $raw | ConvertFrom-Json
        $completed = @{}
        if ($obj.completed) {
            foreach ($p in $obj.completed.PSObject.Properties) {
                $completed[$p.Name] = [string]$p.Value
            }
        }
        return @{ completed = $completed }
    }
    catch {
        Write-BridgeLog "state_read_failed: $($_.Exception.Message)"
        return @{ completed = @{} }
    }
}

function Save-State {
    param([hashtable]$State)
    $tmp = "$StatePath.tmp"
    $payload = @{ completed = $State.completed } | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText($tmp, $payload, [Text.UTF8Encoding]::new($false))
    Move-Item -Force -LiteralPath $tmp -Destination $StatePath
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Bridge config not found: $ConfigPath"
}

$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($required in @("control_repo", "branch", "device_id", "poll_seconds")) {
    if (-not $config.PSObject.Properties.Name.Contains($required)) {
        throw "Missing config property: $required"
    }
}

$repoParts = [string]$config.control_repo -split "/", 2
if ($repoParts.Count -ne 2) {
    throw "control_repo must be owner/repo"
}
$Owner = $repoParts[0]
$Repo = $repoParts[1]
$Branch = [string]$config.branch
$DeviceId = [string]$config.device_id
$PollSeconds = [Math]::Max(2, [int]$config.poll_seconds)
$Token = Read-ProtectedToken
$Headers = @{
    Authorization = "Bearer $Token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "QORE-VPS-Control-Bridge/$BridgeVersion"
}
$ApiBase = "https://api.github.com/repos/$Owner/$Repo"
$State = Load-State

function Invoke-GitHub {
    param(
        [ValidateSet("GET", "PUT")][string]$Method,
        [string]$Uri,
        [object]$Body = $null,
        [switch]$AllowNotFound
    )
    try {
        if ($Method -eq "GET") {
            return Invoke-RestMethod -Method Get -Uri $Uri -Headers $Headers -TimeoutSec 30
        }
        $json = $Body | ConvertTo-Json -Depth 12 -Compress
        return Invoke-RestMethod -Method Put -Uri $Uri -Headers $Headers -Body $json -ContentType "application/json" -TimeoutSec 30
    }
    catch {
        $status = $null
        try { $status = [int]$_.Exception.Response.StatusCode } catch {}
        if ($AllowNotFound -and $status -eq 404) {
            return $null
        }
        throw
    }
}

function Get-RepoContent {
    param([string]$Path)
    $escapedPath = ($Path -split "/" | ForEach-Object { [Uri]::EscapeDataString($_) }) -join "/"
    $branchEncoded = [Uri]::EscapeDataString($Branch)
    $uri = "$ApiBase/contents/$escapedPath?ref=$branchEncoded"
    return Invoke-GitHub -Method GET -Uri $uri -AllowNotFound
}

function Put-RepoText {
    param(
        [string]$Path,
        [string]$Text,
        [string]$Message
    )
    $existing = Get-RepoContent -Path $Path
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $body = @{
        message = $Message
        content = [Convert]::ToBase64String($bytes)
        branch = $Branch
    }
    if ($existing -and $existing.sha) {
        $body.sha = [string]$existing.sha
    }
    $escapedPath = ($Path -split "/" | ForEach-Object { [Uri]::EscapeDataString($_) }) -join "/"
    return Invoke-GitHub -Method PUT -Uri "$ApiBase/contents/$escapedPath" -Body $body
}

function Decode-RepoFile {
    param($Item)
    if (-not $Item.content) {
        $Item = Get-RepoContent -Path ([string]$Item.path)
    }
    $clean = ([string]$Item.content) -replace "\s", ""
    $bytes = [Convert]::FromBase64String($clean)
    return [Text.Encoding]::UTF8.GetString($bytes)
}

function Truncate-Text {
    param(
        [AllowNull()][string]$Text,
        [int]$MaxChars = 524288
    )
    if ($null -eq $Text) {
        return @{ text = ""; truncated = $false }
    }
    if ($Text.Length -le $MaxChars) {
        return @{ text = $Text; truncated = $false }
    }
    return @{ text = $Text.Substring(0, $MaxChars); truncated = $true }
}

function Run-PowerShellJob {
    param($Job)

    if (-not $Job.command) {
        throw "powershell job missing command"
    }

    $timeoutSeconds = 900
    if ($Job.timeout_seconds) {
        $timeoutSeconds = [Math]::Max(1, [Math]::Min(86400, [int]$Job.timeout_seconds))
    }

    $cwd = $InstallDir
    if ($Job.cwd) {
        $requested = [string]$Job.cwd
        if (-not (Test-Path -LiteralPath $requested -PathType Container)) {
            throw "cwd does not exist: $requested"
        }
        $cwd = $requested
    }

    $command = [string]$Job.command
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))

    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = "powershell.exe"
    $psi.Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded"
    $psi.WorkingDirectory = $cwd
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    if ($Job.env) {
        foreach ($p in $Job.env.PSObject.Properties) {
            $psi.EnvironmentVariables[$p.Name] = [string]$p.Value
        }
    }

    $proc = [Diagnostics.Process]::new()
    $proc.StartInfo = $psi
    $start = [DateTime]::UtcNow
    [void]$proc.Start()

    $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
    $stderrTask = $proc.StandardError.ReadToEndAsync()
    $exited = $proc.WaitForExit($timeoutSeconds * 1000)
    $timedOut = -not $exited

    if ($timedOut) {
        try { $proc.Kill() } catch {}
        try { $proc.WaitForExit(5000) } catch {}
    }

    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $end = [DateTime]::UtcNow
    $exitCode = $null
    if (-not $timedOut) {
        $exitCode = $proc.ExitCode
    }

    $out = Truncate-Text -Text $stdout
    $err = Truncate-Text -Text $stderr

    return @{
        started_at = $start.ToString("o")
        finished_at = $end.ToString("o")
        duration_ms = [int64]($end - $start).TotalMilliseconds
        exit_code = $exitCode
        timed_out = $timedOut
        stdout = $out.text
        stderr = $err.text
        stdout_truncated = $out.truncated
        stderr_truncated = $err.truncated
    }
}

function Publish-Heartbeat {
    $payload = @{
        schema = "qore-vps-heartbeat-v1"
        device_id = $DeviceId
        hostname = $env:COMPUTERNAME
        utc = [DateTime]::UtcNow.ToString("o")
        bridge_version = $BridgeVersion
        powershell_version = $PSVersionTable.PSVersion.ToString()
        pid = $PID
    } | ConvertTo-Json -Depth 5
    [void](Put-RepoText -Path "heartbeats/$DeviceId.json" -Text $payload -Message "bridge($DeviceId): heartbeat")
}

function Publish-Result {
    param(
        $Job,
        [string]$CommandSha,
        [hashtable]$Execution,
        [AllowNull()][string]$BridgeError
    )

    $result = @{
        schema = "qore-vps-result-v1"
        job_id = [string]$Job.job_id
        target_device = $DeviceId
        source_command_sha = $CommandSha
        bridge_version = $BridgeVersion
        bridge_error = $BridgeError
        execution = $Execution
    } | ConvertTo-Json -Depth 12

    [void](Put-RepoText -Path "results/$($Job.job_id).json" -Text $result -Message "bridge($DeviceId): result $($Job.job_id)")
}

Write-BridgeLog "bridge_start version=$BridgeVersion repo=$Owner/$Repo branch=$Branch device=$DeviceId poll_seconds=$PollSeconds"

$lastHeartbeat = [DateTime]::MinValue

while ($true) {
    try {
        if (([DateTime]::UtcNow - $lastHeartbeat).TotalSeconds -ge 30) {
            Publish-Heartbeat
            $lastHeartbeat = [DateTime]::UtcNow
        }

        $items = Get-RepoContent -Path "commands"
        if ($items) {
            foreach ($item in @($items | Sort-Object name)) {
                if ([string]$item.type -ne "file") { continue }
                if (-not ([string]$item.name).EndsWith(".json", [StringComparison]::OrdinalIgnoreCase)) { continue }

                $raw = Decode-RepoFile -Item $item
                $job = $raw | ConvertFrom-Json

                if (-not $job.job_id) { continue }
                $jobId = [string]$job.job_id

                if ($State.completed.ContainsKey($jobId)) { continue }
                if (Get-RepoContent -Path "results/$jobId.json") {
                    $State.completed[$jobId] = [string]$item.sha
                    Save-State -State $State
                    continue
                }

                $errorText = $null
                $execution = $null

                try {
                    if ([string]$job.schema -ne "qore-vps-job-v1") {
                        throw "unsupported schema"
                    }
                    if ([string]$job.target_device -ne $DeviceId) {
                        throw "target_device mismatch"
                    }
                    if (-not $job.expires_at) {
                        throw "expires_at required"
                    }
                    $expires = [DateTime]::Parse([string]$job.expires_at).ToUniversalTime()
                    if ([DateTime]::UtcNow -gt $expires) {
                        throw "job expired"
                    }
                    if ([string]$job.type -ne "powershell") {
                        throw "unsupported job type: $($job.type)"
                    }

                    Write-BridgeLog "job_start id=$jobId sha=$($item.sha)"
                    $execution = Run-PowerShellJob -Job $job
                    Write-BridgeLog "job_finish id=$jobId exit=$($execution.exit_code) timeout=$($execution.timed_out)"
                }
                catch {
                    $errorText = $_.Exception.Message
                    Write-BridgeLog "job_error id=$jobId error=$errorText"
                    $now = [DateTime]::UtcNow.ToString("o")
                    $execution = @{
                        started_at = $now
                        finished_at = $now
                        duration_ms = 0
                        exit_code = $null
                        timed_out = $false
                        stdout = ""
                        stderr = ""
                        stdout_truncated = $false
                        stderr_truncated = $false
                    }
                }

                try {
                    Publish-Result -Job $job -CommandSha ([string]$item.sha) -Execution $execution -BridgeError $errorText
                    $State.completed[$jobId] = [string]$item.sha
                    Save-State -State $State
                }
                catch {
                    Write-BridgeLog "result_publish_failed id=$jobId error=$($_.Exception.Message)"
                }
            }
        }
    }
    catch {
        Write-BridgeLog "poll_error: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds $PollSeconds
}
