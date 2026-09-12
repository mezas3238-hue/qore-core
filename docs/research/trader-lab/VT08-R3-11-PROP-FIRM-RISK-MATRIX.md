# VT-08 R3.11 — Prop-Firm Risk Matrix (Consumed Evidence Only)

Checkpoint: 2026-09-12

## Authority

Research-only. This document does not grant DEMO_ELIGIBLE, LIVE, funded-account, merge, or ready authority. It does not access the reserved 2020-2022 candidate holdout.

Canonical economic structure remains frozen as:

- **A = CORE** = AUDJPY SHORT + GBPUSD SHORT
- **GBPJPY = RETURN ENHANCER** = GBPJPY LONG + GBPJPY SHORT
- **B = PORTFOLIO** = A + GBPJPY enhancer

The seven-market universe remains open for research. This matrix does not permanently exclude the other market×direction capabilities.

## Evidence used

Only already-consumed R3.10/R3.8 evidence was used:

- fresh window: 2022-08-13 through 2024-08-12
- baseline window: 2024-08-13 through 2026-09-11
- total B portfolio trades: 229
- A trades: 117
- GBPJPY enhancer trades: 112

No pre-2022-08-13 evidence was opened.

## Research account and constraints

- normalized starting equity: USD 100,000
- A fixed-risk sweep: 20 / 25 / 30 / 35 bps of current equity per trade
- GBPJPY fixed-risk sweep: 10 / 15 / 20 / 25 bps per trade
- portfolio open-risk heat cap: 90 bps of current equity
- broker min/max/step volume constraints retained from consumed cTrader evidence
- protective-stop loss used as bounded open risk
- prop-firm external envelope evaluated against 5% maximum daily loss and 10% maximum loss
- internal sustainability reference: <= 2% daily loss and <= 5% account drawdown
- cost stress is a completed-trade price-bps proxy, not a claim about realized broker spread/commission/slippage

For adverse intraday equity, consumed M15 high/low evidence was used and each position's adverse loss was capped at its modeled protective-stop loss. Daily reset was evaluated on a CE(S)T calendar for the FTMO-like 2-Step envelope.

## Full zero-cost risk matrix

| A risk | GBPJPY risk | Return | Max equity DD | Worst daily loss | Max heat |
|---:|---:|---:|---:|---:|---:|
| 0.20% | 0.10% | +6.09% | 2.16% | 0.47% | 0.50% |
| 0.20% | 0.15% | +7.04% | 2.25% | 0.56% | 0.55% |
| 0.20% | 0.20% | +8.04% | 2.38% | 0.61% | 0.60% |
| 0.20% | 0.25% | +9.02% | 2.56% | 0.66% | 0.64% |
| 0.25% | 0.10% | +7.15% | 2.69% | 0.61% | 0.60% |
| 0.25% | 0.15% | +8.13% | 2.78% | 0.66% | 0.65% |
| 0.25% | 0.20% | +9.12% | 2.90% | 0.71% | 0.70% |
| 0.25% | 0.25% | +10.11% | 3.04% | 0.76% | 0.75% |
| 0.30% | 0.10% | +8.22% | 3.25% | 0.71% | 0.70% |
| 0.30% | 0.15% | +9.22% | 3.31% | 0.76% | 0.75% |
| 0.30% | 0.20% | +10.23% | 3.45% | 0.81% | 0.80% |
| 0.30% | 0.25% | +11.23% | 3.59% | 0.87% | 0.85% |
| 0.35% | 0.10% | +9.32% | 3.83% | 0.81% | 0.80% |
| 0.35% | 0.15% | +10.30% | 3.86% | 0.86% | 0.85% |
| 0.35% | 0.20% | +11.32% | 4.00% | 0.92% | 0.90% |
| 0.35% | 0.25% | +12.40% | 4.15% | 0.92% | 0.90% |

No zero-cost matrix point breached the external 5% daily-loss or 10% maximum-loss envelope on consumed evidence.

## Cost-stress findings

The decisive weakness is not gross drawdown; it is cost fragility in the 2024-2026 baseline.

Representative **A 0.25% / GBPJPY 0.20%** portfolio:

- zero-cost combined: **+9.12%**
- 0.25 bp stress combined: **+7.31%**
- 0.50 bp stress combined: **+5.52%**
- 1.00 bp stress combined: **+2.05%**
- fresh 2022-2024 at 0.50 bp: **+5.33%**
- baseline 2024-2026 at 0.50 bp: **+0.17%**
- baseline break-even price-cost proxy: approximately **0.545 bp/trade**
- combined break-even price-cost proxy: approximately **1.299 bp/trade**

Representative **A 0.20% / GBPJPY 0.25%** portfolio:

- zero-cost combined: **+9.02%**
- max equity DD: **2.56%**
- worst daily loss: **0.66%**
- 0.50 bp stress combined: **+5.49%**
- fresh 2022-2024 at 0.50 bp: **+5.05%**
- baseline 2024-2026 at 0.50 bp: **+0.40%**
- baseline break-even price-cost proxy: approximately **0.606 bp/trade**

The latter has the best observed return/DD among the tested grid, but it must **not** be promoted as an optimized production allocation because the grid itself used consumed evidence.

## Sleeve decomposition at the conservative reference point

At **A 0.25% / GBPJPY 0.20%**:

- A CORE alone: 117 trades, **+5.18%**, PF ~1.364, max equity DD ~2.41%, worst daily loss ~0.51%
- GBPJPY enhancer alone: 112 trades, **+3.76%**, PF ~1.341, max equity DD ~1.39%, worst daily loss ~0.21%
- B combined: 229 trades, **+9.12%**, PF ~1.351, max equity DD ~2.90%, worst daily loss ~0.71%

This supports the frozen architecture: A remains a valid core and GBPJPY adds meaningful return without causing a disproportionate drawdown increase on consumed evidence.

## Adjudication

**Do not choose the single highest-return cell.** The consumed grid shows a broad sustainable plateau rather than one unique optimum.

Current research zone:

- A: roughly **0.20%-0.30%** risk per trade
- GBPJPY enhancer: roughly **0.20%-0.25%** risk per trade
- portfolio heat: **<= 0.90%**
- internal daily-loss operating ceiling for future Monte Carlo: **2.0%**
- internal hard drawdown research ceiling for future Monte Carlo: **5.0%**

A conservative reference policy for the next engineering stage is **A 0.25% / GBPJPY 0.20%**, not because it maximizes historical profit, but because it preserves the CORE > enhancer risk hierarchy, keeps historical drawdown below 3%, keeps worst modeled daily loss below 1%, and remains positive in both consumed windows at the 0.50 bp proxy stress.

This reference allocation is **not yet frozen as the final prop-firm policy**. Actual cTrader all-in costs, provider-specific reset semantics, Monte Carlo breach probabilities, and fresh holdout evidence remain required.

## Next gate

Before opening the June-2020 through June-2022 candidate holdout:

1. freeze the provider-parameterized prop-firm Risk contract;
2. freeze actual/preregistered cost treatment;
3. run Monte Carlo and block-resampled path stress under daily-loss / maximum-loss rules;
4. require sufficiently low breach probability under the internal envelope;
5. only then certify a genuinely fresh holdout interval and execute it once.
