# QORE VPS CONTROL BRIDGE 001

Status: DESIGN + BOOTSTRAP IMPLEMENTATION. NO LIVE/PRODUCTION AUTHORITY. NO SECRETS IN QORE-CORE.

Owner: Sergio Meza
Source of truth: mezas3238-hue/qore-core

## Mission

Provide a persistent second administrative path into the authorized Windows VPS vps-vrix so ChatGPT can operate the VPS without a human copying commands between chat and RDP.

The bridge is an operations transport only. It does not grant trading authority, does not alter QORE certification rules, and must not be used to enable LIVE or real-capital execution.

## Architecture

ChatGPT GitHub connector -> PRIVATE GitHub control repository -> outbound HTTPS polling -> QORE VPS Control Bridge -> PowerShell, filesystem, processes, qore-core working tree and Trader Lab.

The private repository uses three transport folders: commands, results, and heartbeats.

There is no inbound listener and no public port exposed by this bridge.

## Repository separation

qore-core remains the canonical source of code and architecture.

The private control repository is NOT a source-code authority. It is only a command/result transport and must never contain trading secrets, account credentials, provider passwords, or long-lived infrastructure secrets.

The control repository must be PRIVATE and accessible only to the Owner and the ChatGPT GitHub connector/app that is intentionally authorized to use it.

## Security model

1. The control repository is private.
2. The VPS credential used by the bridge is a fine-grained GitHub token restricted to that one control repository.
3. Required token permission: repository Contents read/write only.
4. The token is encrypted on the VPS with Windows DPAPI using LocalMachine scope.
5. The encrypted token file ACL is restricted to SYSTEM and Administrators.
6. The bridge accepts only JSON command files under commands/.
7. Every command must target the exact configured device id.
8. Every command must carry an expiry timestamp; expired jobs are rejected.
9. Results include the source command blob SHA for replay/audit traceability.
10. Completed jobs are persisted locally and are not executed twice after restart.
11. Each result is written under results/JOB_ID.json.
12. A heartbeat is written under heartbeats/DEVICE_ID.json.
13. No GitHub Actions runner is installed on the VPS.
14. No command is accepted from pull requests, issues, comments, forks, or the public qore-core repository.

## Command schema

schema: qore-vps-job-v1
job_id: unique id
target_device: vps-vrix
created_at: UTC ISO timestamp
expires_at: UTC ISO timestamp
type: powershell
cwd: optional working directory
timeout_seconds: bounded timeout
command: PowerShell command text

PowerShell is intentionally the primitive capability because it already provides filesystem, process, service, Git, Python, replay, and Trader Lab control. Higher-level typed tools can be added later without changing the transport.

## Result schema

The bridge returns job id, source command SHA, device id, start/end timestamps, duration, exit code, timeout state, stdout, stderr, truncation markers and bridge version.

Output is capped in the transport to avoid oversized GitHub objects. Large evidence files remain on the VPS and can be fetched in a subsequent command.

## Heartbeat

The bridge updates heartbeats/vps-vrix.json with UTC timestamp, hostname, bridge version, PowerShell version and process id. This provides an independently observable ONLINE/OFFLINE signal without Desktop Commander.

## Installation model

The bridge installs under C:\ProgramData\QORE\VPSBridge and runs as Scheduled Task QORE VPS Control Bridge under NT AUTHORITY\SYSTEM, starting at Windows boot.

The task is independent of the user's RDP session and should continue after RDP disconnects.

## One-time bootstrap prerequisites

The Owner performs only the initial bootstrap because Desktop Commander quota can no longer execute remote commands:

1. Create a new PRIVATE GitHub repository, recommended name qore-vps-control.
2. Initialize it with a README so main exists.
3. Grant the ChatGPT GitHub connector access to that private repository.
4. Create a fine-grained GitHub token scoped only to qore-vps-control, with Contents read/write and no Actions/admin permission.
5. On vps-vrix, obtain this qore-core branch and run tools/vps_bridge/Install-QoreVpsBridge.ps1 once as Administrator.
6. Enter the private repository name and token when prompted.

After bootstrap, normal command execution and result retrieval require no RDP intermediary.

## Operational boundary

Administrative VPS access is separate from trading authorization.

Existing Owner rules remain in force: DEMO/research only unless explicitly changed under QORE governance; no automatic LIVE/real-capital activation; no certification shortcuts; GitHub remains the code source of truth; VPS is a test/runtime bank, not the canonical code authority.

## Failure behavior

The bridge fails closed if config is missing, token cannot be decrypted, control repo is inaccessible, target device mismatches, command is expired, schema is unknown, result for the job already exists, or execution timeout is exceeded.

Network failure does not delete jobs. The agent retries polling and heartbeat publication with bounded delay.

## Future extension

Once ChatGPT full custom MCP write actions are available for the account, this agent can be fronted by Secure MCP Tunnel and the GitHub queue can become a backup transport. The local execution layer does not need to be rewritten.
