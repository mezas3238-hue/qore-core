# VT31 — COG LANE — FAST RUNNER 3Y CAUSAL SENSOR TRUTH (2026-10-09)

**Status:** evidence-backed COG development checkpoint; **NOT** economic certification.  
**Repository:** `mezas3238-hue/qore-core`  
**Branch:** `agent/vt31-architect-cognition-sensors-20261009`  
**Final 3Y shadow workflow run:** [37991724073](https://github.com/mezas3238-hue/qore-core/actions/runs/37991724073) — SUCCESS.  
**Measured run SHA:** `d0d27bc0c1325d95d0412de32c29dab6d3624978`  
**Unit CI:** [37991691739](https://github.com/mezas3238-hue/qore-core/actions/runs/37991691739) — SUCCESS.  
**Fast-runner static + pytest:** ruff PASS; 32/32 tests PASS.  
**Canonical source:** `VT31_NAS100_OWNER_3Y_BASE_001`; NAS100 2023-10-01 (inclusive) to 2026-10-01 (exclusive).  
**Source artifact:** `11459859004`; canonical reused, not reacquired.  
**Evidence SHA256:** `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`.

## 1. What actually ran

The new `scripts/vt31_nas100_cognitive_3y_native_fact_fast_audit_v1.py` intercepts the **existing specialist's** selected setup lifecycle, feeds the immutable M1 evidence into read-only causal native-fact producers, and returns the **same** structural simulation. It does not change source selection, entry timing, fills, stops, targets, position outputs or trading policy. Expensive Monte Carlo is intentionally not computed for this observer-only job; no certification/economic claims are made from its placeholder.

**Proper denominator repair:** an earlier pilot incorrectly included 16 ambiguous fill-bar censures in post-entry observation counts and sampled terminal bars. That pilot's fact counts are rejected. Final run excludes those censures, the fill candle, and the terminal candle from the **post-entry cognitive decision denominator**; it reports only fully closed M1 facts that a *next-open* actuator could in principle consume. This is an actual accounting fix, not an economic improvement.

### Actual 3Y structural funnel

| Item | Final count |
|---|---:|
| Selected executable source setups | 124 |
| No fill | 29 |
| Prospective fills | 95 |
| Fill-bar censored / unresolvable | 16 |
| Valid structural-terminal paths | 79 |
| Valid preterminal closed-M1 observations | 1,866 |
| Structural paths with **zero** usable post-fill observations | **11** |
| Final Comparator-009 admitted control | **55 from prior reference** — NOT re-adjudicated in this shadow run |

Selected families: breaker 83; fair-value-gap 29; order-block 12. These sum to 124. The 11 zero-call paths are **within 79 structural terminal paths**, not a proven subset of the 55 later admitted trades.

### Native fact shadow truth (preterminal only)

| Producer | TRUE observations | FALSE observations | NA observations | Unique structural trades with TRUE | Decision status |
|---|---:|---:|---:|---:|---|
| `structure_invalidated` | 0 | 1,866 | 0 | 0 | No *early* thesis break evidenced by current stop-close boundary; cannot claim protection |
| `liquidity_failure_confirmed` | 1,047 | 819 | 0 | 50 | Exploratory frozen-reference recross criterion; **not an economically validated exit rule** |
| `regime_changed_against_thesis` | 57 | 1,809 | 0 | 4 | Real H1 frozen-regime to adverse-H1 transitions, causal M1/H1 |
| `next_structural_target` | 0 available | 1,866 `NOT_APPLICABLE` | 0 missing required | 0 | Current structural control never makes the post-target, already-accepted journey available before terminal; source chaining STILL required for EXTEND |

**Regime producer repair:** the initial version required the frozen H1 to be strictly direction-aligned, mistakenly marking a valid frozen `mixed` or `flat` regime as `NOT_EVALUABLE`. The first sound-denominator run therefore showed 1,798 NA observations. The corrected producer accepts known frozen regime states and records a TRUE transition only if closed current H1 has become opposite the thesis and the frozen H1 was not already opposite. The final run yields 0 NA, 57 true M1 observations over **4 distinct positions**. This is a cognition input proof, not proof those four trades should have exited.

**Interpretation:** Native event evidence exists, yet 3Y **production consumer/action/actuation parity is not tested** by the shadow Fast Runner. A recurring TRUE observation is not a new independent signal each minute.

### Eleven zero-observation structural signal identities (UTC)

```text
2023-10-04T14:25:00+00:00
2023-12-12T15:16:00+00:00
2023-12-18T15:16:00+00:00
2024-04-11T14:09:00+00:00
2024-05-21T14:06:00+00:00
2025-04-17T14:23:00+00:00
2025-04-29T14:21:00+00:00
2025-10-13T14:03:00+00:00
2025-11-21T15:19:00+00:00
2026-04-10T14:09:00+00:00
2026-04-15T14:08:00+00:00
```

These are causal timing audit identifiers, never a date-based entry blacklist or outcome oracle.

## 2. COG implementation in this lane

- New `vt31_nas100_causal_fact_producers.py`: as-of closed-M1 truth values and explicit `OBSERVED`, `NOT_EVALUABLE`, `NOT_APPLICABLE`, `MISSING_REQUIRED` with provenance.
- `vt31_nas100_cognitive_telemetry.py`: explicit UNWIRED status and producer-to-consumer as-of/value parity. Semantic parser now recognizes multiword `NOT_EVALUATED` without matching unrelated negative states such as `NO_CONFIRMED_EXHAUSTION`.
- `vt31_nas100_post_entry_cognitive_runtime.py`: `build_market_facts_from_causal_report()` refuses mandatory unavailable facts instead of turning them into false; real native TRUE can reach canonical full-cognition EXIT in fixture. `revalidate_prospective_fill()` is SHADOW-only, uses `reason()` from frozen entry situation and exact prospective M1-open timestamp; no post-fill R or execution authority.
- `scripts/vt31_nas100_cognitive_sensor_audit_v1.py`: detects required PositionActions with missing actuator sensors, and reports native status/value/source counts.
- Dedicated 3Y Fast Runner workflow `.github/workflows/vt31-cognitive-3y-fast-native-facts-v1.yml`: runs immutable three-year shadow, checks source hashes, fails closed on structural parity, uploads evidence-bound artifacts.
- Isolated CI workflow `.github/workflows/vt31-cognitive-native-facts-contract-v1.yml`: full causal unit/static tests.

All changes remain on COG branch. OPS ownership of entry/exit scripts and certification gates is respected.

## 3. Exact missing items before any scientific promotion

1. **Do not silently wire native read-only prototypes as live EXIT triggers.** Formalize a methodology-native early structure break and a confirmed liquidity failure with independently justified evidence. The current stop-close proxy cannot act ahead of terminal execution.
2. **Connect these producers in the actual OPS replay caller**, not merely the COG shadow. Build `PostEntryMarketFacts` from a timestamp-matching report; telemetry must see it; canonical `PositionAction` must route to next-open execution or fail the run.
3. **Zero-call:** insert prospective-fill revalidation at *actual fill open T* using exclusively market evidence closed no later than T. CONTROL vs FILL_REVALIDATE with the same frozen 3Y, no arbitrary delay. Include each of the 11 signal IDs as an audit row but DO NOT preselect/reject them based on final loss. Record rejected winners, rejected losers and risk/winner preservation.
4. **Regime parity:** prove that H1 entry/current facts in OPS are the same canonical, complete closed-H1 buckets used in this observer. Never mix M15 and H1 in one change detector or leak NY clock into London.
5. **Structural destination:** source a confirmed next DOL market structure, with provenance and formation timestamps; `NOT_APPLICABLE` before primary acceptance is valid. Never invent EXTEND from a constant sentinel or unseen future target.
6. **NY and London independent certification:** OPS still owns density >=400 genuine fills per 3Y, hard continuous DD <=6R, PF/Sharpe/Sortino/MC/costs and full gate matrix. COG sensing does not waive failed economic gates.
7. The canonical 3Y source is consumed development evidence; Fresh Holdout remains sealed. **No live/funded execution permission.**

## 4. Required next shared reproducibility package

Upon OPS integration, report CONTROL vs modified **on identical source SHA256**:
```text
3Y source hash / COG SHA / OPS SHA / session_model_id
candidate selected/fill/terminal/admitted counts
input TRUE/FALSE/NA by producer
full/maximum cognition REQUIRED + EVALUATED coverage
zero-call before/after fill-time revalidation
canonical HOLD/TRAIL/EXTEND/EXIT and routed/executed parity
rejected winners and losers / winner R preservation
PF / mean R / observed continuous DD R / Sharpe / Sortino / MC / cost stresses
pass/fail each frozen Core gate
```

No dual-session promotion until NY and London each independently pass all development gates.
