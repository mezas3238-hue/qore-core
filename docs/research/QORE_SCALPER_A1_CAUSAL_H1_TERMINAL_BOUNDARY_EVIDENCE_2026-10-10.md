# Scalper A1 — Future H1 terminal metadata: cognitive causal boundary

**Date:** 2026-10-10 · **Branch:** `agent/scalper-architect-a-cognition-20261010` · **Issues/PRs:** cognitive #756/#758; source methodology #757/#759; parent #623. **Status:** research, draft, not certified, no VPS/LIVE/merge.

## Defect, observation and limits

`V49Opportunity.h1_state_until` is computed by a full-history source census. It may describe a later opposing H1 signal and is *not* guaranteed known at the M1 decision. The original `build_v50_cognitive_snapshot` did not explicitly use the field in its cognitive facts, but retained the unsanitized `V49Opportunity` as `source_opportunity`, making future metadata accessible to downstream cognitive consumers.

A1 commit `260bdd8f1634574c810e449b8d810c867ad368dc` changes only the V50 cognitive view: `_as_of_source_opportunity` copies the source candidate and **right-censors** `h1_state_until` at the actual M1 decision timestamp, without rewriting the source census or using the future terminal value. Right-censoring means **visibility ends here**, not “H1 ended here.” The original V49 opportunity still preserves its retrospective terminal value for offline audit. Do not convert the clipped timestamp into a source exit signal, state invalidation, or strategy filter.

A1 test commit `9960b2e2d7877668bf14ec9dcc39b580ac4aa28e` varies this future terminal by 40 days and asserts identical V50 cognitive snapshot, disposition and geometry, with the copied source's terminal clipped to the decision instant. Type annotation follow-up `15f64cf0a7d4bdec243ac61531085266ae9f530b`.

This fix does **not** establish full Master Frame invocation inside V50-G; that benchmark still uses a per-opportunity empty experience memory and hardcoded `WELL_SUPPORTED`. A1's separate `capitalizer_a1_full_frame_research_adapter.py` exercises actual nine-market frame invocation on externally supplied evidence but is not an integrated causal nine-market replay.

## Additional quality defects repaired

- `efa9e2d9915f27d86b4b458b9e27c087e9d6e8a0`: V51 test's escaped literal `\\n` had placed a winner-R preservation assertion *inside a comment*. This restores a real assertion expecting 5R/3R rather than 1R/1R. No production rule or economic parameter changed.
- `228f7a8185a5ce8d057137572f31378bf5a29ce8`: V54 test signature split into multiple lines to satisfy Ruff E501.
- `6fb52aa09ca05d34287a351ce8bfbae56e762812`: annotate the research adapter fixture return type so Mypy can check it.
- `.github/workflows/qore-scalper-cognition-audit.yml`: independent branch-only Ruff repo, Mypy repo and focused pytest. The workflow is a **quality test only**, never evidence of trading certification.

## Cross-architect caller facts

Direct inspected entry points (`capitalizer_high_frequency_capacity_census_v49.py`, `capitalizer_v50_cognitive_geometry_economics.py`, `capitalizer_v50_cognitive_opportunity.py`, `capitalizer_a1_full_frame_research_adapter.py`) do **not** call `assess_dual_source_entry`. V50-G calls `build_v50_cognitive_snapshot`, while only the A1 research adapter calls `build_master_cognitive_frame`. This is a scoped finding, **not** proof that dual-source is globally unused and not an explanation for V50-G's rejected 90 trades.

A2 methodology branch separately fixes `_untouched_h1_target_fast` so only M1 bars closed by `decision_at` may demonstrate a target touch; it is a *source-rule/target semantic fix*, **not** copied into A1 without methodology approval. A1 requested explicit cross-review in PR #759, comment 6096863912.

## Pending scientific falsification

1. Verify the exact HEAD of GitHub Actions runs and avoid assigning GREEN to canceled/obsolete SHAs.
2. Test unchanged V49 source population and V50-G market admissions, trades, PF/DD and winners when compared with its instrumented as-of version on identical nine-market inputs. Unit snapshot equality alone is insufficient.
3. Join B's H1 target repair only in an explicitly reviewed integration and rerun source parity.
4. Replace static V50-G readiness with evidence-derived metacognition **in an isolated A/B**, never by silent replacement of baseline; use a synchronized nine-market causal barrier and actual perception data.
5. Carry only **selected, actually settled** trade records into future immutable as-of memory; prove the memory affects actual gate outcomes by ablation. Same-timestamp settlement is not predecision knowledge.
6. Apply density and winner-preservation constraints (>=80% winning trade count, >=90% positive winner R), MAX3 ceiling and <=6R acceptance DD **only when validated on actual comparable replay**. 90-trade architecture remains rejected.

No QORE Risk authority, economic freeze, trader certification or production access is created by these changes.
