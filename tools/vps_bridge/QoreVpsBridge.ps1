param(
    [string]$ConfigPath = "$env:ProgramData\QORE\VPSBridge\config.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Security

$BridgeVersion = "0.2.0"
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

function Get-PropertyValue {
    param([object]$Object,[string]$Name,$Default = $null)
    if ($null -eq $Object) { return $Default }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $Default }
    return $prop.Value
}

function Read-ProtectedToken {
    if (-not (Test-Path -LiteralPath $TokenPath)) { throw "Encrypted token file not found: $TokenPath" }
    $protected = [IO.File]::ReadAllBytes($TokenPath)
    $bytes = [System.Security.Cryptography.ProtectedData]::Unprotect(
        $protected,$null,[System.Security.Cryptography.DataProtectionScope]::LocalMachine
    )
    return [Text.Encoding]::UTF8.GetString($bytes)
}

function Load-State {
    if (-not (Test-Path -LiteralPath $StatePath)) { return @{ completed = @{} } }
    try {
        $obj = (Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8) | ConvertFrom-Json
        $completed = @{}
        $completedObject = Get-PropertyValue -Object $obj -Name "completed"
        if ($completedObject) {
            foreach ($p in $completedObject.PSObject.Properties) { $completed[$p.Name] = [string]$p.Value }
        }
        return @{ completed = $completed }
    } catch {
        Write-BridgeLog "state_read_failed: $($_.Exception.Message)"
        return @{ completed = @{} }
    }
}

function Save-State {
    param([hashtable]$State)
    $tmp = "$StatePath.tmp"
    $payload = @{ completed = $State.completed } | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText($tmp,$payload,[Text.UTF8Encoding]::new($false))
    Move-Item -Force -LiteralPath $tmp -Destination $StatePath
}

if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Bridge config not found: $ConfigPath" }
$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($required in @("control_repo","branch","device_id","poll_seconds")) {
    if ($null -eq $config.PSObject.Properties[$required]) { throw "Missing config property: $required" }
}

$repoParts = [string]$config.control_repo -split "/",2
if ($repoParts.Count -ne 2) { throw "control_repo must be owner/repo" }
$Owner = $repoParts[0]
$Repo = $repoParts[1]
$Branch = [string]$config.branch
$DeviceId = [string]$config.device_id
$PollSeconds = [Math]::Max(3,[int]$config.poll_seconds)
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
    param([ValidateSet("GET","PUT")][string]$Method,[string]$Uri,[object]$Body=$null,[switch]$AllowNotFound)
    try {
        if ($Method -eq "GET") { return Invoke-RestMethod -Method Get -Uri $Uri -Headers $Headers -TimeoutSec 30 }
        $json = $Body | ConvertTo-Json -Depth 20 -Compress
        return Invoke-RestMethod -Method Put -Uri $Uri -Headers $Headers -Body $json -ContentType "application/json" -TimeoutSec 30
    } catch {
        $status = $null
        try { $status = [int]$_.Exception.Response.StatusCode } catch {}
        if ($AllowNotFound -and $status -eq 404) { return $null }
        throw
    }
}

function Get-RepoContent {
    param([string]$Path)
    $escapedPath = ($Path -split "/" | ForEach-Object { [Uri]::EscapeDataString($_) }) -join "/"
    $branchEncoded = [Uri]::EscapeDataString($Branch)
    $uri = "$ApiBase/contents/${escapedPath}?ref=$branchEncoded"
    return Invoke-GitHub -Method GET -Uri $uri -AllowNotFound
}

function Put-RepoText {
    param([string]$Path,[string]$Text,[string]$Message)
    $existing = Get-RepoContent -Path $Path
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $body = @{ message=$Message; content=[Convert]::ToBase64String($bytes); branch=$Branch }
    $existingSha = Get-PropertyValue -Object $existing -Name "sha"
    if ($existingSha) { $body.sha = [string]$existingSha }
    $escapedPath = ($Path -split "/" | ForEach-Object { [Uri]::EscapeDataString($_) }) -join "/"
    return Invoke-GitHub -Method PUT -Uri "$ApiBase/contents/$escapedPath" -Body $body
}

function Decode-RepoFile {
    param($Item)
    $content = Get-PropertyValue -Object $Item -Name "content"
    if (-not $content) {
        $path = [string](Get-PropertyValue -Object $Item -Name "path")
        if ([string]::IsNullOrWhiteSpace($path)) { throw "Repository item has no path" }
        $Item = Get-RepoContent -Path $path
        $content = Get-PropertyValue -Object $Item -Name "content"
    }
    if (-not $content) { throw "Repository item has no content" }
    $clean = ([string]$content) -replace "\s",""
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($clean))
}

function Truncate-Text {
    param([AllowNull()][string]$Text,[int]$MaxChars=262144)
    if ($null -eq $Text) { return @{text="";truncated=$false} }
    if ($Text.Length -le $MaxChars) { return @{text=$Text;truncated=$false} }
    return @{text=$Text.Substring(0,$MaxChars);truncated=$true}
}

function Invoke-Program {
    param([string]$FileName,[string]$Arguments,[string]$WorkingDirectory,[int]$TimeoutSeconds=300)
    if (-not (Test-Path -LiteralPath $WorkingDirectory -PathType Container)) { throw "working directory does not exist: $WorkingDirectory" }
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName=$FileName; $psi.Arguments=$Arguments; $psi.WorkingDirectory=$WorkingDirectory
    $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true; $psi.UseShellExecute=$false; $psi.CreateNoWindow=$true
    $proc = New-Object Diagnostics.Process
    $proc.StartInfo=$psi
    $start=[DateTime]::UtcNow
    [void]$proc.Start()
    $stdoutTask=$proc.StandardOutput.ReadToEndAsync()
    $stderrTask=$proc.StandardError.ReadToEndAsync()
    $exited=$proc.WaitForExit(([Math]::Max(1,[Math]::Min(86400,$TimeoutSeconds)))*1000)
    $timedOut=-not $exited
    if ($timedOut) { try{$proc.Kill()}catch{}; try{$proc.WaitForExit(5000)}catch{} }
    $stdout=$stdoutTask.GetAwaiter().GetResult()
    $stderr=$stderrTask.GetAwaiter().GetResult()
    $end=[DateTime]::UtcNow
    $exitCode=$null
    if (-not $timedOut) { $exitCode=$proc.ExitCode }
    $out=Truncate-Text -Text $stdout
    $err=Truncate-Text -Text $stderr
    return @{started_at=$start.ToString("o");finished_at=$end.ToString("o");duration_ms=[int64]($end-$start).TotalMilliseconds;exit_code=$exitCode;timed_out=$timedOut;stdout=$out.text;stderr=$err.text;stdout_truncated=$out.truncated;stderr_truncated=$err.truncated}
}

function Require-Path {
    param([object]$Job,[string]$Property="path",[switch]$Directory)
    $value=[string](Get-PropertyValue -Object $Job -Name $Property)
    if ([string]::IsNullOrWhiteSpace($value)) { throw "$Property is required" }
    if ($Directory) {
        if (-not (Test-Path -LiteralPath $value -PathType Container)) { throw "directory does not exist: $value" }
    } else {
        if (-not (Test-Path -LiteralPath $value)) { throw "path does not exist: $value" }
    }
    return $value
}

function Invoke-TypedJob {
    param($Job)
    $type=[string](Get-PropertyValue -Object $Job -Name "type")
    switch ($type) {
        "noop" { return @{ok=$true;operation="noop";utc=[DateTime]::UtcNow.ToString("o")} }
        "system_info" {
            $os=Get-CimInstance Win32_OperatingSystem
            $cs=Get-CimInstance Win32_ComputerSystem
            return @{ok=$true;operation="system_info";hostname=$env:COMPUTERNAME;user=[Security.Principal.WindowsIdentity]::GetCurrent().Name;powershell_version=$PSVersionTable.PSVersion.ToString();os_caption=$os.Caption;os_version=$os.Version;last_boot_utc=$os.LastBootUpTime.ToUniversalTime().ToString("o");total_memory_gb=[Math]::Round($cs.TotalPhysicalMemory/1GB,2);utc=[DateTime]::UtcNow.ToString("o")}
        }
        "list_directory" {
            $path=Require-Path -Job $Job -Directory
            $maxItems=[Math]::Max(1,[Math]::Min(1000,[int](Get-PropertyValue -Object $Job -Name "max_items" -Default 200)))
            $recurse=[bool](Get-PropertyValue -Object $Job -Name "recurse" -Default $false)
            $items=if($recurse){Get-ChildItem -LiteralPath $path -Force -Recurse -ErrorAction Stop|Select-Object -First $maxItems}else{Get-ChildItem -LiteralPath $path -Force -ErrorAction Stop|Select-Object -First $maxItems}
            $rows=@()
            foreach($item in $items){$rows+=@{name=$item.Name;full_name=$item.FullName;type=if($item.PSIsContainer){"directory"}else{"file"};length=if($item.PSIsContainer){$null}else{$item.Length};last_write_utc=$item.LastWriteTimeUtc.ToString("o")}}
            return @{ok=$true;operation="list_directory";path=$path;items=$rows}
        }
        "file_info" {
            $path=Require-Path -Job $Job
            $item=Get-Item -LiteralPath $path -Force
            return @{ok=$true;operation="file_info";full_name=$item.FullName;type=if($item.PSIsContainer){"directory"}else{"file"};length=if($item.PSIsContainer){$null}else{$item.Length};creation_utc=$item.CreationTimeUtc.ToString("o");last_write_utc=$item.LastWriteTimeUtc.ToString("o");attributes=[string]$item.Attributes}
        }
        "read_text" {
            $path=Require-Path -Job $Job
            if((Get-Item -LiteralPath $path).PSIsContainer){throw "read_text requires a file"}
            $maxChars=[Math]::Max(1,[Math]::Min(1048576,[int](Get-PropertyValue -Object $Job -Name "max_chars" -Default 262144)))
            $view=Truncate-Text -Text (Get-Content -LiteralPath $path -Raw -Encoding UTF8) -MaxChars $maxChars
            return @{ok=$true;operation="read_text";path=$path;text=$view.text;truncated=$view.truncated}
        }
        "tail_text" {
            $path=Require-Path -Job $Job
            if((Get-Item -LiteralPath $path).PSIsContainer){throw "tail_text requires a file"}
            $lines=[Math]::Max(1,[Math]::Min(2000,[int](Get-PropertyValue -Object $Job -Name "lines" -Default 200)))
            $view=Truncate-Text -Text ((Get-Content -LiteralPath $path -Tail $lines -Encoding UTF8)-join [Environment]::NewLine)
            return @{ok=$true;operation="tail_text";path=$path;lines=$lines;text=$view.text;truncated=$view.truncated}
        }
        "list_processes" {
            $name=[string](Get-PropertyValue -Object $Job -Name "name" -Default "")
            $procs=if([string]::IsNullOrWhiteSpace($name)){Get-Process|Sort-Object ProcessName,Id}else{Get-Process -Name $name -ErrorAction SilentlyContinue|Sort-Object ProcessName,Id}
            $rows=@()
            foreach($p in ($procs|Select-Object -First 500)){$rows+=@{name=$p.ProcessName;id=$p.Id;cpu_seconds=if($null -eq $p.CPU){$null}else{[Math]::Round($p.CPU,3)};working_set_mb=[Math]::Round($p.WorkingSet64/1MB,2)}}
            return @{ok=$true;operation="list_processes";processes=$rows}
        }
        "service_status" {
            $name=[string](Get-PropertyValue -Object $Job -Name "name")
            if([string]::IsNullOrWhiteSpace($name)){throw "name is required"}
            $svc=Get-Service -Name $name -ErrorAction Stop
            return @{ok=$true;operation="service_status";name=$svc.Name;display_name=$svc.DisplayName;status=[string]$svc.Status;start_type=[string]$svc.StartType}
        }
        "git_status" {
            $repoPath=Require-Path -Job $Job -Property "repo_path" -Directory
            return @{ok=$true;operation="git_status";process=Invoke-Program -FileName "git.exe" -Arguments "status --short --branch" -WorkingDirectory $repoPath -TimeoutSeconds 60}
        }
        "git_head" {
            $repoPath=Require-Path -Job $Job -Property "repo_path" -Directory
            return @{ok=$true;operation="git_head";process=Invoke-Program -FileName "git.exe" -Arguments "rev-parse HEAD" -WorkingDirectory $repoPath -TimeoutSeconds 60}
        }
        "git_diff_names" {
            $repoPath=Require-Path -Job $Job -Property "repo_path" -Directory
            return @{ok=$true;operation="git_diff_names";process=Invoke-Program -FileName "git.exe" -Arguments "diff --name-status" -WorkingDirectory $repoPath -TimeoutSeconds 60}
        }
        "pytest_target" {
            $repoPath=Require-Path -Job $Job -Property "repo_path" -Directory
            $target=[string](Get-PropertyValue -Object $Job -Name "target")
            if([string]::IsNullOrWhiteSpace($target)){throw "target is required"}
            if($target -notmatch '^[A-Za-z0-9_\-./\\:]+$'){throw "target contains unsupported characters"}
            $timeoutSeconds=[int](Get-PropertyValue -Object $Job -Name "timeout_seconds" -Default 1800)
            return @{ok=$true;operation="pytest_target";target=$target;process=Invoke-Program -FileName "python.exe" -Arguments "-m pytest $target -q" -WorkingDirectory $repoPath -TimeoutSeconds $timeoutSeconds}
        }
        default { throw "unsupported typed job: $type" }
    }
}

function Publish-Heartbeat {
    $payload=@{schema="qore-vps-heartbeat-v1";device_id=$DeviceId;hostname=$env:COMPUTERNAME;utc=[DateTime]::UtcNow.ToString("o");bridge_version=$BridgeVersion;powershell_version=$PSVersionTable.PSVersion.ToString();pid=$PID;typed_operations=@("noop","system_info","list_directory","file_info","read_text","tail_text","list_processes","service_status","git_status","git_head","git_diff_names","pytest_target")}|ConvertTo-Json -Depth 8
    [void](Put-RepoText -Path "heartbeats/$DeviceId.json" -Text $payload -Message "bridge($DeviceId): heartbeat $BridgeVersion")
}

function Publish-Result {
    param($Job,[string]$CommandSha,[object]$Payload,[AllowNull()][string]$BridgeError)
    $jobId=[string](Get-PropertyValue -Object $Job -Name "job_id")
    $result=@{schema="qore-vps-result-v2";job_id=$jobId;target_device=$DeviceId;source_command_sha=$CommandSha;bridge_version=$BridgeVersion;bridge_error=$BridgeError;payload=$Payload;completed_at=[DateTime]::UtcNow.ToString("o")}|ConvertTo-Json -Depth 30
    [void](Put-RepoText -Path "results/$jobId.json" -Text $result -Message "bridge($DeviceId): result $jobId")
}

Write-BridgeLog "bridge_start version=$BridgeVersion repo=$Owner/$Repo branch=$Branch device=$DeviceId poll_seconds=$PollSeconds"
$lastHeartbeat=[DateTime]::MinValue

while($true){
    try{
        if(([DateTime]::UtcNow-$lastHeartbeat).TotalSeconds -ge 600){Publish-Heartbeat;$lastHeartbeat=[DateTime]::UtcNow}
        $items=Get-RepoContent -Path "commands"
        if($items){
            foreach($item in @($items|Sort-Object name)){
                $itemType=[string](Get-PropertyValue -Object $item -Name "type")
                $itemName=[string](Get-PropertyValue -Object $item -Name "name")
                if($itemType -ne "file"){continue}
                if(-not $itemName.EndsWith(".json",[StringComparison]::OrdinalIgnoreCase)){continue}
                $job=(Decode-RepoFile -Item $item)|ConvertFrom-Json
                $jobId=[string](Get-PropertyValue -Object $job -Name "job_id")
                if([string]::IsNullOrWhiteSpace($jobId)){continue}
                $itemSha=[string](Get-PropertyValue -Object $item -Name "sha")
                if($State.completed.ContainsKey($jobId)){continue}
                if(Get-RepoContent -Path "results/$jobId.json"){$State.completed[$jobId]=$itemSha;Save-State -State $State;continue}
                $errorText=$null;$payload=$null
                try{
                    if([string](Get-PropertyValue -Object $job -Name "schema") -ne "qore-vps-job-v2"){throw "unsupported schema"}
                    if([string](Get-PropertyValue -Object $job -Name "target_device") -ne $DeviceId){throw "target_device mismatch"}
                    $expiresText=[string](Get-PropertyValue -Object $job -Name "expires_at")
                    if([string]::IsNullOrWhiteSpace($expiresText)){throw "expires_at required"}
                    if([DateTime]::UtcNow -gt [DateTime]::Parse($expiresText).ToUniversalTime()){throw "job expired"}
                    Write-BridgeLog "job_start id=$jobId type=$([string](Get-PropertyValue -Object $job -Name "type")) sha=$itemSha"
                    $payload=Invoke-TypedJob -Job $job
                    Write-BridgeLog "job_finish id=$jobId"
                }catch{
                    $errorText=$_.Exception.Message
                    Write-BridgeLog "job_error id=$jobId error=$errorText"
                    $payload=@{ok=$false;operation=[string](Get-PropertyValue -Object $job -Name "type")}
                }
                try{
                    Publish-Result -Job $job -CommandSha $itemSha -Payload $payload -BridgeError $errorText
                    $State.completed[$jobId]=$itemSha
                    Save-State -State $State
                    Publish-Heartbeat
                    $lastHeartbeat=[DateTime]::UtcNow
                }catch{Write-BridgeLog "result_publish_failed id=$jobId error=$($_.Exception.Message)"}
            }
        }
    }catch{Write-BridgeLog "poll_error: $($_.Exception.Message)"}
    Start-Sleep -Seconds $PollSeconds
}
