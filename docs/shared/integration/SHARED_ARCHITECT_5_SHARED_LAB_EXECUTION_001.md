# SHARED — Arquitecto B5 · Shared Lab Execution Evidence 001

## Exact code snapshot

- Branch: `agent/shared-architect-b5-relational-asset-world-001`
- B5 SHA: `7c62547b635c805f52e94b66bec185b1c9b0ac53`
- Shared base: `55144bb92abdc5135521f545667b94dcad555bb1`
- Shared Lab observed HEAD: `f9792cd95553b5663383b0b3474e5be2e2bda789`

## Engineering validation before Lab

The complete B5-owned/new suite is GREEN locally on the exact B5 worktree:

- pytest: **62 passed / 0 failed**
- Ruff: **PASS**
- Mypy: **PASS — 0 issues in 30 Python files**

This proves engineering execution only; it does **not** promote B-11/B-12/B-13 to empirical scientific closure.

## Shared Lab attempts

### Attempt 1

Run: `SL-1791144163665939700-7c62547b-f88bc719`

Artifact: `23ac7060241b5aec27045bec827d0131732fbe4337f6a3b6d01f10f281ebba53`

Disposition: `INCOMPLETE`.

Finding: invocation did not load the B5 plugin registry and the default Lab suites tried to hash `shared_lab*.py` inside the B5 snapshot.

### Attempt 2 — corrected B5 plugin registry + base SHA

Run: `SL-1791144191275289500-7c62547b-4a4d112a`

Artifact: `bd467f52c377e9431c3f5e875f53681816d09c441272731f56b5c445c1e9c8f9`

The Lab correctly selected:

- `b5-relational-science-functional`
- `b5-asset-worlds-functional`
- `b5-handoff-determinism`

The first two tasks were stopped **before pytest started** with:

`resource limits could not be applied; fail-closed`

Root cause is in the current Shared Lab runtime: `shared_lab_orchestrator._apply_limits()` returns `False` whenever `os.name != "posix"`. The authorized host is Windows and has no WSL distribution, Docker or Podman runtime installed. No system/runtime installation was attempted.

## Disposition

This is a **Shared Lab infrastructure dependency**, not a B5 functional failure.

B5 preserves fail-closed behavior. No Lab PASS is claimed.

Scientific truth remains:

- B-11/B-12/B-13: engines implemented, empirical population dependency-blocked until B-08 relational comparability authority exists.
- B-14: `KNOWN_BLINDSPOT`; no agricultural proxy fabricated.
- B-15: `GOVERNED_UNKNOWN`; no product/venue/front/roll/continuous inference.
- no outcomes, fresh holdout, LIVE, production, real capital, sizing, Risk, Execution or broker mutation.
