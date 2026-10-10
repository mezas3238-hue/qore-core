# SCALPER A2 — Paired nine-market historical replay, matched source, winner preservation

**Owner:** Architect B, methodology PR #759 / issue #757; cognition cross-review A1 PR #758 / issue #756. Parent #623.  
**Date:** 2026-10-10. All work GitHub Actions, no VPS, LIVE, merge or production. This report tracks genuine research execution and does not certify Scalper.

## Provenance (verified, not synthesized)

Source of historical provider-native M1 is official GitHub Actions [run 35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), at source SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. All nine raw-M1 artifacts were confirmed by GitHub API as `expired=false`, each ~92–105 MB compressed. The market jobs independently check `canonical_symbol`, `provider_native_m1=true`, `synthetic_m1=false`, `interpolated_m1=false`, `contradictory_m1=0`, and `read_only=true`; no M5-to-M1 fabrication.

**Frozen market/session map:** USDJPY/AUDJPY/AUDUSD/GBPJPY (Asia), EURUSD/GBPUSD (London), XAUUSD/USDCAD/NAS100 (NY). QORE generic H1→M15→M1 across these sessions is not a claim of literal Asia/London TTrades source model replication. MAX3 remains a shared ceiling per (session, operating_date).

## Two independently preregistered, real-market research pipelines

| Arm | Workflow / run | Source & logic | Output | Current evidence |
|---|---|---|---|---|
| A — structural frozen V49 control | [V49 CONTROL #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695) | Branch B V49 with causal H1-target repair; original frozen V49 structural stop/target economics | Nine V49 opportunity files + nine V49 economic reports/trade ledgers + global V49 MAX3 / PF/DD matrix | Contract CI passed; 9/9 market outputs and aggregate require explicit run evidence before claiming |
| B — legacy V50-G cognitive geometry | [V50-G TRACE #38053723674](https://github.com/mezas3238-hue/qore-core/actions/runs/38053723674) | Same V49 B causal census + pinned A1 cognitive modules SHA `4ab7c1ad72876f15e2f24923927d9140406d85a3` | Nine V49 source ledgers + nine V50-G market reports/trades + one A1 cognitive trace per source + nine-market waterfall + PF/DD/cost-stress matrix | Contract CI passed; 9/9 and economics require aggregate PASS. V50-G is **PARTIAL BRIDGE**, not nine-market Master Frame cognition |

GitHub workflow commits: A2 B trace `cb897be93821fcb238c4a16a419dfff2814ec0f4` and V49 frozen control latest workflow `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`. Both automatically ran on their research branches. Different workflow commit SHAs do **not** change the frozen V49 census implementation; validate exact source opportunity manifests and signatures before combining.

**Preregistration before outcomes:** methodology issue #757 comments [6097729624](https://github.com/mezas3238-hue/qore-core/issues/757#issuecomment-6097729624) and [6097752092](https://github.com/mezas3238-hue/qore-core/issues/757#issuecomment-6097752092), source provenance, loss reasons, no optimizer/promotion and same-population assumptions.

## Independent source-to-execution and winner preservation audit

The branch B now includes:

- `capitalizer_scalper_v49_v50_g_waterfall_v1.py`: verifies source-ID join to A1 cognitive trace, geometry READY, conditional cognitive allowance, per-source executed policy trade legitimacy, no duplicated/foreign/ambiguous fills, missing session M1 and global MAX3.
- `capitalizer_scalper_winner_retention_v1.py`: **post hoc only**, joins selected V49 and V50-G trades to the identical V49 source universe, requires all nine markets with matching source rows, calculates original winning-ID preservation and R mass before considering any new wins. Refuses absent or ambiguous parents.
- `test_capitalizer_scalper_v49_v50_g_waterfall_v1.py` and `test_capitalizer_scalper_winner_retention_v1.py`: fail-closed tests using **synthetic fixture data only**, not economic replay.
- [Methodology CI #38054299022](https://github.com/mezas3238-hue/qore-core/actions/runs/38054299022): **both methodology_quality and full_quality PASS**, Ruff entire repo, Mypy src/tests, tests method, V53/V54. Commit `85e5545c76a11fc5826f9ab1ac3ba8adb4284f2a`.

### Winner mass: do not mistake unmatched new wins for preserved winners

Baseline positive winners are those actually selected by V49 global MAX3. For each arm B policy (`GEOMETRY_ONLY`, `COGNITIVE_GEOMETRY`), match exact original `source_opportunity_id`, then count baseline positive winners that **remain profitable**. Compute:

- `winner_count_preservation_ratio = |baseline winning IDs still positive under candidate| / |baseline winning IDs|`.
- `original_winner_mass_preservation_ratio = Σ baseline realized R of those IDs / Σ baseline positive R`.
- `candidate_realized_winner_mass_ratio = Σ candidate positive R of those same IDs / Σ baseline positive R`.

Do not confuse the last two: a larger candidate reward does not erase how many originally profitable signals were suppressed. New candidate winners not in V49-selected baseline are reported separately. 80%/90% Owner thresholds are a screening contract, **not** a claim of source-fidelity to TTrades or guarantee of performance. The tools do not choose new policies on historical outcomes.

## Blocking caveats

1. Tests passing and a run being started do **not** mean nine-market replay completed; do not invent PF/DD, Sharpe, Sortino or recovered trade counts before checking all market jobs, aggregate job and exact artifacts.
2. Economic models have different stop/target decisions, so an equal-market comparison is **not** a controlled single-variable attribution to cognition. V50-G static `WELL_SUPPORTED` and per-candidate empty memory are known limitations. A1's true full nine-market Master Frame and prequential causal loss memory require independent 9/9 observed-barrier replay and ablations.
3. `COST_STRESS_R` 0, 0.01, 0.025, 0.05 are simplified per-trade R deductions, **not** broker-native BID/ASK spreads, financing, slippage or commissions. Gross PF/DD is not certifiable net PF/DD.
4. If a runner fails on missing data, duplicated V49 keys, ambiguous trade/source parent, unknown provenance or timing leak, stop claims; do not reduce the opportunity population or silently assign a winner to make the aggregate pass.
5. Follow-up scientific gate after proper nine-market results: maintain density above rejected 90 trades, winner_count≥80% and original positive winner R≥90%, net PF target, max-DD Owner≤6R, independent OOS and Monte Carlo. No live/funded account permission.

**Status:** historical replay code and method verifiers in GitHub, preregistered. Results only after verifying successful artifacts on their exact run SHA.
