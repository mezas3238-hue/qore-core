# VT-08 R3.16 — CIBO Capital Protection Study Freeze

Checkpoint: 2026-09-13

Status: RESEARCH / EXPLORATORY EVIDENCE ON ALREADY-CONSUMED WINDOWS.

## Parent and retained evidence

- Parent branch: `agent/vt08-r3-14-two-phase-funding-001`.
- Parent exact green HEAD: `266fa60df2654ffcbce3a89569295bb19f791022`.
- Challenge evidence source: R3.15 run `34759027136`, exact retained SHA `64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222`, window `[2020-07-01, 2022-07-01)`.
- Long-run evidence source: R3.8 run `34693803930`, retained artifact SHA `b65d32ea03d3b471997d7955db37cf9a2d41ddaa`, available two-year window beginning 2024-08-13 and ending 2026-09-12.
- Both windows are already consumed evidence. R3.16 MUST NOT claim a fresh independent holdout.
- R3.16 downloads retained artifacts only. It MUST NOT recollect cTrader history or reopen the R3.15 protected holdout.

## Frozen portfolio architecture

The R3.11 portfolio identities remain unchanged:

- `A_CORE` = AUDJPY SHORT + GBPUSD SHORT.
- `GBPJPY_RETURN_ENHANCER` = GBPJPY LONG + GBPJPY SHORT.
- `B_COMBINED_PORTFOLIO` = A CORE + GBPJPY RETURN ENHANCER.

No other VT-08 market or direction is admitted to R3.16.

## CIBO authority boundary

CIBO is explicitly prohibited from:

- generating an entry;
- suppressing or filtering a valid VT-08 generated entry;
- changing direction;
- changing the original target;
- widening the original stop;
- re-entering;
- increasing exposure above Risk authority;
- bypassing the 5% capital drawdown ceiling.

CIBO may only:

1. ratchet protection after an already-open VT-08 trade moves favorably; and
2. request lower future exposure from Risk as capital protection activates.

Risk remains sovereign. If capital headroom is exhausted, Risk may allocate zero exposure even though the Trader-generated signal remains present in the evidence. Such a zero allocation is recorded as a `risk_lockout`, not as CIBO deleting the Trader entry.

## Conservative post-entry execution rule

CIBO ratchets use retained M15 evidence. The stop effective at the opening of an M15 bar is evaluated before target touch. A favorable threshold reached inside that bar may change the stop only for later bars. This prevents R3.16 from inventing favorable intrabar ordering.

Frozen post-entry policies:

- `off`: original VT-08 stop and fixed 2R target.
- `soft`: +0.75R -> -0.50R; +1.25R -> 0R; +1.60R -> +0.50R.
- `be050-lock050-at100`: +0.50R -> break-even; +1.00R -> +0.50R.
- `aggressive`: +0.50R -> break-even; +1.00R -> +0.50R; +1.50R -> +1.00R.

The target remains the Trader's original fixed 2R target in every policy.

## Risk surface

R3.16 reuses the already-researched Challenge Risk surface rather than inventing a new larger-risk family:

- r075: A 0.75%, GBPJPY 0.60%, heat 2.00%.
- r100: A 1.00%, GBPJPY 0.80%, heat 2.50%.
- r125: A 1.25%, GBPJPY 1.00%, heat 3.00%.
- r150: A 1.50%, GBPJPY 1.20%, heat 3.50%.
- r200: A 2.00%, GBPJPY 1.50%, heat 4.50%.
- r225: A 2.25%, GBPJPY 1.70%, heat 5.00%.
- r250: A 2.50%, GBPJPY 1.90%, heat 5.50%.

The same selected Risk level is used in both 30-day phases. CIBO may only reduce effective exposure.

## Hard capital protection

Primary price-cost stress: 0.50 bp.

The hard capital contract is 5% maximum drawdown. Before each simultaneous entry group, Risk computes worst-case stop loss including the frozen cost proxy and scales or rejects exposure so that neither:

- equity below 95% of phase/long-run starting capital; nor
- peak-to-equity drawdown above 5%

is permitted by the modeled stop exposure.

Frozen account guards:

- `hard5-only`: only the hard 5% capital contract.
- `target-late`: at 70%, 85%, 95% progress toward the current phase target, cap requested future Risk to 85%, 60%, 30% of its otherwise-authorized amount.
- `bank50-late`: target-late plus preservation of 50% of accrued peak profit as capital headroom permits.
- `bank50-ddlate`: bank50-late plus drawdown scaling at 3.50% -> 75%, 4.25% -> 50%, 4.75% -> 25%.

## Study 1 — fixed 30 + 30 challenge

Evidence source is the already-consumed R3.15 2020-2022 window.

- Paired moving-block bootstrap with 5-trading-day blocks.
- Search paths: 2,500.
- Final selected-policy paths: 10,000.
- Seed: `2026091304`.
- Phase 1 uses exactly the first 30 modeled trading days.
- Phase 2 uses exactly the second 30 modeled trading days and starts from fresh evaluation equity/state.
- No unused days from one phase may be transferred to the other.
- Primary targets: Phase 1 +10%, Phase 2 +5%.
- Sensitivity targets: Phase 1 +11%, Phase 2 +6%.
- Primary selection: maximize paired probability of completing both phases, then Phase-1 pass probability, then fewer Risk lockouts, then lower base Risk.
- A, GBPJPY and B are scored separately.

## Study 2 — retained 2024-2026 chronology

The exact retained chronology is replayed over `[2024-08-13, 2026-09-12)` for A, GBPJPY and B.

R3.16 records:

- terminal return;
- maximum drawdown;
- generated Trader signals;
- executed trades after Risk sizing;
- Risk lockouts caused by capital protection;
- CIBO-protected exits;
- full stop losses;
- paired return and drawdown delta versus Risk-only at the same selected Risk level.

## Interpretation restrictions

R3.16 is allowed to answer only how much CIBO changes retained VT-08 economics under these frozen capital-protection policies.

R3.16 does NOT:

- change VT-08 B01 methodology;
- change A / GBPJPY / B membership;
- create new Trader entries;
- create a new independent validation claim;
- grant DEMO_ELIGIBLE by itself;
- grant LIVE or Production authority;
- authorize real capital;
- authorize merge or READY state.

Any policy chosen from R3.16 is exploratory/post-hoc with respect to these consumed windows and requires a genuinely unseen future validation interval before it can be treated as independently validated CIBO policy evidence.
