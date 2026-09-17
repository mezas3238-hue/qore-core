# QORE-CIBO-ATLAS-VT31-MARKET-SPECIALISTS-001

## Status

**IMPLEMENTATION SLICE — RESEARCH ONLY — NO R9 / NO LIVE / NO PRODUCTION AUTHORITY**

This architecture separates VT-31 into three market-specialist research lines while giving CIBO Atlas an independent market-laboratory role.

Specialist identities under research:

- `VT31_NAS100_*` — NAS100 only;
- `VT31_SP500_*` — SP500 only;
- `VT31_US30_*` — US30 only.

They remain siblings of the same VT-31 / Silver Bullet methodology. Specialization may adapt market-specific implementation only when a causal hypothesis remains inside the methodology contract and survives the full evidence pipeline.

## Why this split exists

The tick-corrected consumed evidence shows material behavioral differences between NAS100, SP500 and US30. Forcing one exact risk/entry/lifecycle geometry across all three can hide market-specific failure modes and make aggregate drawdown alignment harder.

The solution is **not** to retrospectively drop a weak market. The solution is to give each index an independently versioned trader research line while preserving a common methodology and a common CIBO Atlas diagnostic system.

## Authority model

```text
RAW HISTORICAL MARKET DATA
        |
        v
CIBO ATLAS MARKET LAB
(independent market behavior map)
        |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
VT31 NAS100          VT31 SP500          VT31 US30
specialist           specialist           specialist
telemetry             telemetry             telemetry
        |                  |                  |
        +------------------+------------------+
                           |
                           v
              CIBO ATLAS GAP COMPARATOR
                           |
                           v
              RESEARCH HYPOTHESES ONLY
                           |
                           v
            consumed research / WFO / stress
                           |
                           v
              exact candidate freeze
                           |
                           v
                    FULL QORE GATE
                           |
                           v
               genuine one-shot holdout
                           |
                           v
              independent validation
                           |
                           v
                     QORE RISK
                           |
                           v
                       EXECUTION
```

`CIBO ATLAS != EXECUTION AUTHORITY`.

`CIBO ATLAS != PROMOTION AUTHORITY`.

`CIBO ATLAS != AUTOMATIC PARAMETER OPTIMIZER`.

## Independent market map

Atlas must not merely summarize the trades selected by a VT-31 candidate. That would reproduce the trader's selection bias.

For each index, Atlas must reconstruct as much consumed historical market behavior as the available evidence permits, using methodology-compatible primitives independently of trader acceptance/rejection:

- 09:00 reference / liquidity structure;
- raid occurrence, side, depth, wick/body composition and final extreme;
- displacement and confirmation geometry;
- Breaker / FVG / Order Block availability and location;
- protected-swing structure and confirmation latency;
- entry-zone depth and retracement path;
- MAE/MFE path at fixed normalized checkpoints;
- initial-stop interaction;
- post-stop recovery / continuation;
- opposite-liquidity reachability and time-to-reach;
- spread / BID-ASK executable path where tick evidence exists;
- volatility and range state;
- temporal state (minute, day, quarter, half-year, regime);
- same-day NAS100/SP500/US30 breadth, direction agreement and divergence.

Atlas records both:

1. `PRE_ENTRY` information that could be known causally before an entry; and
2. `POST_OUTCOME_RESEARCH` labels used only for laboratory diagnosis.

The two timing classes may never be silently mixed.

## Three trader telemetry maps

Each specialist trader produces the same metric vocabulary against its own accepted setups. Examples:

- signal density;
- fill density;
- no-fill rate;
- initial-stop rate;
- protected-stop rate;
- 1R / 1.5R / 2R reach rate;
- target rate;
- median MAE and MFE;
- MFE-before-stop;
- post-stop MFE;
- stop-then-target rate;
- time-to-positive-excursion;
- risk/reference;
- raid depth/reference;
- confirmation body/range;
- entry location;
- protected-swing latency;
- cross-index breadth/context.

The trader snapshot is bound to exact trader identity and configuration fingerprint.

## Atlas gap comparison

For a common metric:

```text
behavior_gap = specialist_trader_value - independent_market_baseline_value
```

The raw gap is descriptive. It cannot change the trader.

Examples of useful diagnostics:

- trader initial-stop rate materially above methodology-compatible market baseline;
- trader rejects many market formations that later produce clean displacement;
- trader entry occurs systematically deeper/shallower than the market's successful path family;
- protected stop is activated before the market's normal retracement envelope;
- post-stop recovery is frequent, implying invalidation geometry rather than signal-direction failure;
- three-index breadth correlates with adverse path behavior;
- one specialist depends on a regime absent in adjacent time blocks.

## Predeclared diagnostic rules

`CiboAtlasDiagnosticRule` converts a metric gap into a **research hypothesis only**.

Every rule binds:

- a stable rule code;
- one metric code;
- direction (`above`, `below`, `absolute`);
- a numeric threshold frozen before the comparison is interpreted;
- a gap family;
- a hypothesis code;
- a methodology-guard evidence reference.

Rules do not mutate a candidate, select a market, authorize capital, or open a fresh holdout.

## Required diagnostic families

The initial taxonomy is:

- `data-coverage`;
- `signal-timing`;
- `entry-geometry`;
- `initial-invalidation`;
- `lifecycle-management`;
- `market-regime`;
- `cross-index-context`;
- `execution-path`.

## Development loop per market

Each of NAS100, SP500 and US30 gets an independent loop:

1. Build the broadest honest consumed market Atlas available.
2. Replay the current specialist against the same historical boundary.
3. Compare Atlas market map vs specialist telemetry.
4. Localize the dominant gap and verify it across temporal blocks.
5. Form a causal hypothesis that remains inside VT-31 methodology.
6. Convert it into a finite, predeclared research family.
7. Test only on consumed/development evidence.
8. Run leakage-free walk-forward.
9. If unstable, reject the hypothesis and return to Atlas.
10. If stable, create a new exact specialist identity/config.
11. Run provider robustness, stress, Monte Carlo and account-risk qualification.
12. Freeze exact candidate + Full QORE.
13. Only then open that market specialist's genuine fresh holdout once.
14. A failed fresh holdout is consumed forever and cannot be retuned under the same identity.

## Drawdown model

The three traders do not need identical raw drawdown distributions. They need individually defendible economic and risk behavior.

CIBO Atlas diagnoses the market/trader mismatch. QORE Risk remains responsible for account-wide exposure, correlation and capital protection.

The system must therefore preserve two different questions:

- **Trader question:** does this exact market-specialist methodology have robust positive expectancy with acceptable intrinsic drawdown?
- **Portfolio/Risk question:** can the independently qualified specialists coexist within the account's allowed drawdown envelope?

A governor cannot manufacture expectancy for a negative specialist.

## Cross-index role

CIBO Atlas studies NAS100, SP500 and US30 jointly even though the traders are specialized independently.

Cross-index information may become a causal context feature only after consumed evidence supports a predeclared hypothesis and leakage-free WFO validates it. Same-day confirmation, divergence or breadth must never be assumed beneficial merely because multiple indices agree.

## Initial implementation contract

`src/qore/infrastructure/cibo_atlas_market_lab.py` provides:

- `CiboAtlasMarketSnapshot` — independent market baseline;
- `CiboAtlasTraderSnapshot` — exact market-specialist telemetry;
- `CiboAtlasMetric` with explicit causal timing;
- `CiboAtlasDiagnosticRule` — predeclared hypothesis rule;
- `CiboAtlasBehaviorGap` — market-vs-trader difference;
- `CiboAtlasResearchHypothesis` — non-authoritative research output;
- `CiboAtlasComparison` — fail-closed research-only result;
- `compare_cibo_atlas_market_to_trader` — deterministic comparison.

The comparison hard-codes:

- `research_only=True`;
- `selection_prohibited=True`;
- `opens_new_holdout=False`;
- `live_authorized=False`;
- `production_authorized=False`.

## Next implementation slices

The contracts are only the boundary. The next slices must build actual evidence producers:

1. **CIBO Atlas Historical Market Scanner** for NAS100/SP500/US30 from the oldest honest retained data;
2. **Path & Excursion Laboratory** for MAE/MFE, stop-before-continuation and time-to-liquidity;
3. **Cross-Index Context Matrix** independent of trader acceptance;
4. **Specialist Telemetry Adapters** for NAS100, SP500 and US30;
5. **Gap Diagnostic Pack** with predeclared rules and temporal stability;
6. **Specialist Research Harness** that produces finite candidate families without fresh leakage;
7. **Per-market WFO + provider robustness + prop-risk qualification**.

## Governance

No result from CIBO Atlas can be called a certified trader.

No retrospective favorable market/regime/bucket may be promoted directly.

No fresh holdout may be inspected until an exact specialist candidate is frozen and Full QORE is GREEN.

No specialist may bypass CIBO/QORE Risk or canonical execution authority.
