# QORE CORE — VT31 ICT original clean-room reset (P0, 2026-10-09)

## Owner directive
**ABANDON all old VT31 behavior. Restart from first principles.** No TTrades-r2.2/r2.4, older COMP008/COMP009 cognition, r5/r8 or legacy adaptive-confluence assumptions may be silently imported into the new trader.

### Branches
- **New clean branch:** `agent/vt31-ict-cleanroom-rebuild-20261009`.
- **Sealed old-code trace / Git rollback only:** `archive/vt31-legacy-before-cleanroom-20261009` at original SHA `27b25309fce470fc53095794e630ba9193334975`.
- **COG coordination:** GitHub Issue #727, with explicit request for a new COG implementation. Legacy cognitive branch `agent/vt31-architect-cognition-sensors-20261009` is **not** a valid implementation baseline and must not be merged blindly.
- Git history and historical artifacts are audit-only; none is a new trader signal producer or executable execution authority.

## Pre-deletion inventory
Using GitHub full recursive tree from `27b25309...`, **668** VT31-referenced blobs:
- **21** old trader source files in `src/qore/infrastructure/traders`;
- **8** old Trader Lab source files;
- **217** scripts including historical backtests;
- **232** workflows, including old CIBO/VT31 research workflows;
- **29** named tests;
- **158** docs including older handoffs / analytical notebooks;
- **3** other nested paths (some counted indirectly in the groups above).
These are *reference-path counts* (matching `vt31`, `vt_31`, `vt-31`), not all possible indirect import references to the old modules.

**Deletion boundary:** remove ONLY the audited 668 originally-present legacy matching paths on the new rebuild branch, with one atomic Git tree commit. Original `main`, deployed environments and other traders must not be changed. Archive branch retains original files for audit/recovery. Fresh evidence artifacts from earlier 3Y tests remain on GitHub Actions, but historical metrics are NOT the new Silver Bullet baseline.

## NEW clean architecture
- **`src/qore/infrastructure/traders/vt31_ict_cleanroom/contracts.py`**: shared pure-standard-library `CognitiveDecision`, `M1Bar`, `FvgCandidate`, session clock.
- **`src/qore/infrastructure/traders/vt31_ict_cleanroom/operations.py`**: clean NY/DST Silver Bullet source clock; accepts independent cognitive draw+MSS; first eligible directional FVG with causal M1; demonstrates only CE research observation without broker fill; no sizing, order routing, old imports or LIVE.
- **`cognition.py`**: RESERVED FOR ARCHITECT 1. Must produce real independent DOL from completed M15/H1/H4/session evidence, MSS/displacement with objective provenance, as-of source times; cognitive ownership, not OPS dummy producer.
- **`tests/infrastructure/test_vt31_ict_cleanroom_ops.py`** and **`.github/workflows/vt31-ict-cleanroom-bootstrap-v1.yml`**: verify the new clean code without loading old VT31.

## Mandatory migration gates
1. **No-old-code/no-old-workflows test** for committed clean branch. Import references from *non-VT31 filenames* in Core/CIBO must be discovered and retired safely before integration to main. A run failing due to deletion is a blocker to be fixed, not a reason to restore old VT31.
2. **COG/OPS shared DTO contract** must be approved on Issue #727. COG provides causally timestamped market provenance rather than old reason()/COMP00x copy. OPS integrates independently.
3. **Original ICT source fidelity**: 03–04,10–11,14–15 New York; no mandatory 09–10 TTrades sweep; authoritative real DOL + first suitable FVG in source hour; CE/stop/structural MSS strictness are audited as formalization where primary video does not specify universality.
4. **Event->pending->actual broker fill lifecycle** bid/ask/tick and chronological M1 with ambiguity fail-closed. No artificial fills/capacity.
5. **Independent NY and London actual 3Y economic replay** with fees, real trade counts, PF/expectancy/DD/Sharpe/Sortino/MonteCarlo, 6R DD gate, full cognition, test of source/production parity. NY PM subwindow remains within NY internal model.
6. **No LIVE** or deployment until old runtime registry no longer routes to a deleted legacy class and safety/economic gates pass. Fresh holdout sealed.

**Status: reset on isolated branch, certification intentionally revoked.** The operational old code is not restored by the audit archive.

## VERIFIED execution checkpoint — 2026-10-09 (post-reset)

- **Exact atomic 668-file deletion commit:** `01b0ccd598e75170912d63ede9b769538e3250b2` on new cleanroom branch.
- **Post-delete Git tree:** 1,329 total paths; only 6 files containing `vt31` survived, and **all 6 are newly created cleanroom assets** (the cleanroom package 3 Python modules, 1 test, 1 new workflow and this document). Additional *new* audit workflow is added subsequently, never an old runtime file.
- **Standalone new OPS and architect shared COG DTO test run:** [38011922245 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38011922245), tests after deletion verify no old trader sources or old workflows, NY original DST clock and read-only CE price touch, no fabricated fills.
- **Direct Python import dependency audit:** [38011979440 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38011979440); *zero direct Python imports* from surviving `src` modules into the deleted `vt31_nas100_*` and `vt31_silver_bullet*` families. Dynamic string-based registries and full regression still need audit: a count of zero direct imports alone is not production-ready certification.
- **Draft PR #750:** https://github.com/mezas3238-hue/qore-core/pull/750 — deliberately **not merged** while both architects build new COG and OPS execution and pass integration.
- **Coordination request to ARCH1:** https://github.com/mezas3238-hue/qore-core/issues/727#issuecomment-6092006566 — new independent cognitive producer required, no recycling old COG code.
- **Historical archive:** `archive/vt31-legacy-before-cleanroom-20261009` contains old files for audit only. Its existence does not give the new trader any execution or import authority.

**Old VT31 operational state:** removed on rebuild branch, not yet retired from `main` or VPS. Deploying unfinished cleanroom would be unsafe; the PR is draft until complete substitution and certification.

