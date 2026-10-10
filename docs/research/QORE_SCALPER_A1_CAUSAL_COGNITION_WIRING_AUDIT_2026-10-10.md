# SCALPER A1 — Causal Cognition Wiring Audit, Evidence Contract, and Repair Plan

**Date:** 2026-10-10. **Owner:** Architect A / Cognitive track, issue #756, draft PR #758. **Cross-review:** Architect B, issue #757, draft PR #759. **Parent:** draft PR #623. **Scope:** GitHub research ONLY; no VPS, execution, production, merge or certification.

## Verified root cause and scientific boundary

The V50-G market replay (`capitalizer_v50_cognitive_geometry_economics.py::build_market`) passes a new `CapitalizerExperienceMemory()` on every opportunity and a static `CapitalizerEpistemicReadiness.WELL_SUPPORTED`. It invokes `build_v50_cognitive_snapshot` and `propose_v50_geometry`, but **does not invoke** `build_master_cognitive_frame` in this path. The source-complete V49 H1/M15/M1 opportunities still govern candidate generation. Do NOT infer full Master Brain / nine-market causal reasoning, persistent memory, portfolio competition, or verified metacognition from V50-G profit-factor results or the presence of those modules in the repository.

The existing `capitalizer_v50_prequential_cognitive_memory.py` is a distinct laboratory and cannot be substituted for V50-G memory without a frozen population, explicit source identifiers, timestamp ordering, and ablation. `CapitalizerExperienceMemory` is intentionally runtime-immutable; persistence must be provided via a causally versioned history view, never automatic in-place training or a current/future outcome lookup.

## Implemented now — lossless observational instrumentation

- `src/qore/infrastructure/trader_lab/capitalizer_v50_g_causal_decision_trace.py`: immutable trace per **source opportunity** with deterministic source ID, H1/M15/M1 observation times, V50 bridge state family, knowledge/disposition and WHY, geometry decision/WHY, eligible-policy flags, absence of Master Frame/World Model/9-market competition, and the static readiness and empty-memory provenance.
- Trace constructor rejects out-of-order or timezone-naive observations, false full-Master integration/readiness claims, nonzero observations in empty baseline memory, terminal-outcome visibility, and capital authority.
- V50-G `build_market` now writes a separate `capitalizer-v50-g-cognitive-trace.jsonl` in CLI output; one line per V49 opportunity, **including rejected geometry**. The market report records trace count and explicit incomplete-cognition metadata.
- `tests/infrastructure/trader_lab/test_capitalizer_v50_g_causal_decision_trace.py` checks fail-closed invariants and stable source identity.
- Critically this is **instrumentation, not a strategy fix**: the previous input assumptions and V50-G 90-trade economic calculation remain untouched. No automatic winner pruning, retune, timing change, MAX3 change, or source modification is authorized.

## Required integrated causal wiring (P0, NOT YET IMPLEMENTED)

1. **Nine-market time barrier:** for every globally ordered M1 close, construct a coherent `CapitalizerGlobalWorldModel` with exactly nine Market Brains, actual prior market/session state, current Session Brain, carried Daily Journey, closed-only Loss Memory, positions and exposure graph. Every component must have observation time <= decision time. Use true synchronized market coverage and enforce DST; do not fabricate `KNOWN`/good perceptions for missing feeds.
2. **Pre-strategy cognition:** obtain nine-market perception snapshots, regime hypotheses and cross-market causality; derive pressure from *known* session/position/loss events; call `build_master_cognitive_frame` with only currently active DECISION contexts. Record exact caller, input-fingerprint, frame evaluated, metacognitive reasons, adversarial reasons, sovereign gate, competition result and any WAIT/ABSTAIN. Do not infer that `adapt_v50_to_master_context` itself builds a frame.
3. **Experience memory:** use a single chronological evidence store for the replay, with per-decision *immutable as-of* views. An experience becomes visible **only after actual selected trade settlement** and never before its exit timestamp; blocked/counterfactual candidates cannot teach the runtime. A snapshot with no eligible profile must say `UNKNOWN`, never `WELL_SUPPORTED` by constant. Reevaluate simultaneous timestamps under a deterministic tie rule.
4. **Decision contract:** `source_opportunity_id -> source rule/family -> decision_at -> inputs -> invoked modules -> WHY -> strategy eligibility -> frame gate -> competition -> execution/no-execution -> eventual closed-only update`. Do not allow the final P&L or the exit label in the pre-entry trace.
5. **No silent filtering:** introduce the full-frame path as a separate preregistered A/B research variant, NOT a replacement for legacy baseline. Compare identical source opportunities and time windows, all nine markets, and record eligible/WAIT/ABSTAIN denominators. Stop admission if sources/evidence absent; do not claim performance gains from synthetic defaults.
6. **Fidelity contract with B:** any source/route/HTF/FVG/CISD/stop/target gate change requires exact TTrades/ICT source passage, obligatoriness, route and independent methodological sign-off from B. A owns cognitive timing/economy only.

## Required falsification and acceptance evidence

- A baseline-vs-trace differential test must demonstrate unchanged V50-G opportunity count, READY count, policy admissions, selected trade identities, gross R, PF and DD (the trace may not change economics).
- A full-frame integration test must fail when any of the nine market snapshots is missing, any observation is future-dated, provenance is incomplete, source IDs collide, or a memory event settles after the decision.
- Prequential memory replay must show `exit_at <= decision_at` for *accepted settled* positions only, no hindsight learning from rejected candidates and no cross-era leakage.
- Blind outcomes before decisions; remove each cognitive layer separately and compare *same population*: Master Frame, perception, metacognition, experience memory, adversarial, competition, position/exposure, pressure. Report true effect, not merely call counts.
- Revalidate Ruff, Mypy, pytest and the five corrected-core workflows V50-R/V51/V53/V54-A/V54-B. Exact run ID, HEAD, 9/9 market jobs, artifact IDs and aggregate status are mandatory before calling a gate GREEN.
- Preservation gate: >=80% baseline winning trade count and >=90% baseline winner R, plus real HF opportunity density. Reject the previously Owner-rejected 90-trade V50-G as promotion candidate. Report PF, Sharpe, Sortino, DD <=6R acceptance, expectancy, losses, stress, and era-specific coverage; the 3-5R drawdown target remains separate.

**Status:** Observability hardening implemented, regression validation pending. **FULL MASTER COGNITION NOT DEMONSTRATED; SCALPER NOT CERTIFIED.** No holdout, VPS or production use.
