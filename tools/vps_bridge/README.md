# QORE VPS Control Bridge

This directory contains the Windows-side bootstrap for QORE VPS Control Bridge.

Files:
- QoreVpsBridge.ps1: long-running Windows agent.
- Install-QoreVpsBridge.ps1: one-time elevated installer.
- Architecture and security contract: docs/architecture/QORE-VPS-CONTROL-BRIDGE-001.md.

Important:
- Do not put GitHub tokens, provider credentials, trading credentials, account passwords, or private control-repository contents into qore-core.
- The private repository is transport only.
- qore-core remains the code source of truth.
