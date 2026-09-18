# ICT Turtle Soup R4 — fresh holdout result

Date: 2026-09-16

Identity: `ICT_TURTLE_SOUP_R4_D1_IDEAL_C2_H1_CISD__H4_IDEAL_C2_M15_CISD__POSITIONAL_DAILY_DOL`

Parent freeze: `docs/research/ICT-TURTLE-SOUP-R4-PRE-HOLDOUT-FREEZE.md`

Workflow: `QORE ICT Turtle Soup R4 Fresh Holdout 2018-2020`

Authoritative run: `35052152001`

Authoritative software SHA: `8c076a714098704237a97fe992e2e01bf9c69bf0`

Aggregate artifact: `10429651883`

Artifact digest: `sha256:f91ba72a73cd40b1ba3c13bfa42789b5a317efc2fa9023e7cd9cf0106c2d8d17`

Aggregate file SHA-256:

- `aggregate.json`: `add11523d66978fec70f6569e4a21e48b9dc728e578e9f467c9f3ea06dcaf511`
- `trades.json`: `ce80e8e4e08a37cfd16f16308dfe82c75a1dcd8cff0e8519391e5e5574d3a9a6`
- `git-sha.txt`: `24171a87a881a7b69172227f5f23d8308c53cf2c3d1d0e177053542a2185518c`

## Governance

The one-shot window `[2018-07-02T21:00:00Z, 2020-07-01T21:00:00Z)` is now consumed for R4. It cannot be called fresh again.

No mechanics may be changed under the R4 identity after this result. Any repair requires a new identity and different untouched evidence.

`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`

## Signal-count comparison on the exact same evidence

Legacy R3-like signal count: **2,424**

R4 executed trades: **298**

Difference: **-2,126**

Reduction relative to legacy R3-like count: **87.7063%**

The reconstruction therefore changed trade frequency materially and in the intended direction: the source-exact two-level Ideal-C2/CISD contract is far more selective than the R3-like local H4 model.

The comparator is diagnostic only. It is not an alternative candidate and cannot be used to select post-hoc mechanics.

## Aggregate R4 economics

- Trades: **298**
- Gross winners: **112**
- Gross losers: **186**
- Gross win rate: **37.5839%**
- Gross total: **-15.9010560985R**
- Gross mean: **-0.05335924865R/trade**
- Gross PF: **0.9005586880**
- Primary friction: `0.05R/trade`
- Primary total: **-30.8010560985R**
- Primary mean: **-0.10335924865R/trade**
- Primary PF: **0.8180089360**
- Primary max drawdown: **33.2165929643R**
- Stress friction: `0.10R/trade`
- Stress total: **-45.7010560985R**
- Stress PF: **0.7444084216**

Decision: `ICT_TURTLE_SOUP_R4... = REJECTED_FOR_ADVANCEMENT`.

The source reconstruction substantially reduced trade count, but it did not create positive aggregate expectancy on this fresh window.

## Per-symbol primary result

| Symbol | Trades | Gross PF | Primary PF | Primary total R |
|---|---:|---:|---:|---:|
| AUDJPY | 50 | 0.6898 | 0.6170 | -10.5472 |
| AUDUSD | 39 | 0.6269 | 0.5703 | -10.7000 |
| EURUSD | 50 | 1.1434 | 1.0417 | +1.1084 |
| GBPJPY | 49 | 1.0435 | 0.9577 | -1.2412 |
| GBPUSD | 39 | 1.2773 | 1.1728 | +3.7314 |
| USDCAD | 35 | 1.0367 | 0.9347 | -1.1450 |
| USDJPY | 36 | 0.5032 | 0.4479 | -12.0075 |

Per-symbol outcomes are diagnostics only. No symbol may be removed or selected from this consumed result.

## Immediate forensic direction

The fresh result changes the diagnosis relative to R3:

1. Selectivity improved dramatically: 298 R4 trades versus 2,424 legacy-R3-like signals on identical evidence.
2. Target locality is no longer the obvious dominant failure: the median projected geometry is materially larger than R3, yet aggregate expectancy remains negative.
3. The main next question is whether the two-level Ideal-C2/CISD contract still admits reversal confirmations that do not persist through Daily C3, or whether the Daily DOL/relevant-swing interpretation remains too permissive.
4. No conclusion may be converted into a new filter from this consumed holdout. Deep forensics may diagnose causal families only; a repaired candidate must be frozen as a new identity before different untouched evidence is opened.
