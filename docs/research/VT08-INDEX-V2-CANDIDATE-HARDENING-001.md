# VT-08 Index V2 — candidate hardening before fresh validation

## Authority boundary

This record transfers exactly one development hypothesis from PR #543 into a single-candidate replay. It does not reopen the 512-contract search and does not claim that the QORE-selected mechanics are universal TTrades source rules.

Frozen development selection: `V-32e621c9282c`.

- closure: `c2-or-c3-body-close`
- protected swing: `farthest-structural`
- stop: `protected-swing-extreme`
- target: `1.5r`
- lifecycle: `next-h4-boundary`
- daily cardinality: `unique-only`
- universe: NAS100 / SP500 / US30
- New-York anchors: 02:00 / 06:00 / 10:00

Development evidence remains consumed: `[2024-08-13, 2026-09-12)` New-York dates. The selecting ambiguity-lab run is `34789861277`; artifact `10327652038`; artifact ZIP digest `sha256:4a43aed58fa43374855ad906d26719e955a03e790398feb329132fd0d786b39b`.

## Replay defect repaired before any holdout

The ambiguity-lab replay required an exact stop/target level to be contained inside a later M15 high-low range. A bar that opened completely beyond an exit level could therefore survive the level even though the market had already gapped through it.

The transferred candidate closes that historical-execution defect before any fresh holdout is opened:

- adverse stop gap: exit at the observed M15 open;
- favorable target gap: conservatively credit only the frozen target;
- otherwise apply the existing same-M15-bar STOP-first ordering;
- missing lifecycle bars still fail closed;
- no signal-selection rule changes.

This correction is an execution-semantic repair, not an economic optimization. It must be replayed on the already-consumed development evidence. If the fixed candidate no longer satisfies the frozen development adjudication, the candidate is rejected and no fresh holdout is opened.

## Governance

`DEMO_ELIGIBLE=false`.

`LIVE_AUTHORIZED=false`.

`PRODUCTION_AUTHORIZED=false`.

CIBO is not used to generate or select signals. Risk authority is not bypassed. The next permitted step after a green consumed-evidence hardening replay is a separate pre-holdout freeze on an exact immutable candidate SHA, followed by one-time validation strictly before 2024-08-13.
