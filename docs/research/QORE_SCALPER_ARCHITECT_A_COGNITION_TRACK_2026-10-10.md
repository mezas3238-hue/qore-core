# SCALPER — Arquitecto A: Cognición real y replay causal

**Parent:** #623; **task:** #756; **base:** `48525bb6dcc2ed5dd9862422ede6a272bfa3c13e`.  
**Status:** INITIALIZED, NOT CERTIFIED. Exclusive changes to cognition, integration/telemetry, memory, causal re-arm and V50-R/V51 quality repair.

## Working baseline findings
- V50-G isolates a subset: `build_market()` constructs a fresh `CapitalizerExperienceMemory()` for each V49 opportunity, and hardcodes `CapitalizerEpistemicReadiness.WELL_SUPPORTED`. See `src/qore/infrastructure/trader_lab/capitalizer_v50_cognitive_geometry_economics.py`.
- A separate `capitalizer_v50_master_cognitive_adapter.py` is present; inspected V50-G build path does not call `build_master_cognitive_frame`. The full Master Frame's economic efficacy is not established by V50-G.
- The rejected 90-trade V50-G outcome is **diagnostic only**, not a certified cognitive candidate.
- Quality blockers attributable to lane A: Mypy five-field vs two-field `key` collision in `capitalizer_v50_m1_rearm_capacity.py:599,601` and two Mypy errors `capitalizer_v51_multi_era_repair.py:129,580` (numbers per previous Actions; verify against new run).

## Immediate safe patches
1. Rename parent-key and session-day-key variables, no logic changes. Return `cast(dict[str, Any], json.loads(...))` or use explicitly typed validation; address V51 mixed trade typing as `V49EconomicTrade | V50GTrade` without `Any` or silent assumptions.
2. Add unit/regression tests for unchanged emitted rows and gate invariants; run CI/Actions on GitHub and record workflow IDs.
3. Instrument all cognitive paths with immutable `ScalperCausalDecisionTrace v1` signatures. Verify pre-state never sees future outcomes.
4. Predeclare two experiments: A1 actual long-lived temporally governed memory vs fresh-per-opportunity isolation; A2 full Master Frame vs isolated V50 bridge. A/B identical opportunities/costs/seeds/stop-target law, with per-layer WHY and causal coverage.
5. Submit PR review request to Architect B via #757, recording SHA + output and any source-route contract it needs.

## Interface shared with methodology lane
Input strictly causal source plan: `source_route, source_rule_ids, H1 parent, M15 setup, M1 trigger, timestamps, structural target, thesis & execution stops`. Output strictly advisory: `component_versions, state_pre_digest, WHY, PASS_TO_STRATEGY/WAIT/ABSTAIN`. No future R, no capital authority.

## Quality and acceptance
Do not certify until nine markets/three sessions, density recovered beyond 90, winner count >=80%, winner-R >=90%, end-to-end Master Frame traces, cost/MC/independent-prospective OOS and methodology gate pass. Never use VPS or production.
