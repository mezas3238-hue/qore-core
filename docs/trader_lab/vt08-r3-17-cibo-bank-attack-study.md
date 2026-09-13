# VT-08 R3.17 — CIBO BANK → ATTACK exploratory study

Checkpoint: 2026-09-13

Status: RESEARCH / CONSUMED-EVIDENCE EXPLORATION ONLY

## Purpose

Measure whether CIBO can improve VT-08 challenge speed and retained long-horizon economics by operating only after VT-08 has generated an unchanged entry:

1. protect the trade/capital;
2. bank a deterministic fraction of accumulated profit;
3. allow CIBO to request an aggressive Risk mode only against unprotected free cushion;
4. keep Risk sovereign over actual exposure;
5. fail closed before daily drawdown can reach 5%.

CIBO MUST NOT generate, filter, cancel, redirect or reverse VT-08 entries. It MUST NOT increase executed risk above Risk authority. It MUST NOT widen a Trader stop.

## Frozen portfolios inherited from R3.11

- A CORE = AUDJPY SHORT + GBPUSD SHORT.
- GBPJPY RETURN ENHANCER = GBPJPY LONG + GBPJPY SHORT.
- B COMBINED = A CORE + GBPJPY RETURN ENHANCER.

## Evidence windows

- Challenge study: retained R3.15 evidence `[2020-07-01, 2022-07-01)`, already consumed by official run `34759027136`. It is NOT a fresh holdout in R3.17.
- Long study: retained R3.8 2024–2026 evidence from run `34693803930`. It is consumed research evidence.

## Challenge contract

- Phase 1: +10% in <=30 trading days; +11% sensitivity.
- Phase 2: reset evaluation state, +5% in <=30 trading days; +6% sensitivity.
- Internal daily loss ceiling: 4.75%, deliberately below the provider-style 5% limit.
- Capital drawdown ceiling: 4.95%, deliberately below 5%.
- Same VT-08 generated-entry identities across controls and CIBO arms.
- Search and final-evaluation random seeds are distinct.

## BANK → ATTACK semantics

A bank policy has a profit trigger, bank fraction and minimum free-cushion threshold. Once peak equity passes the trigger, part of peak profit becomes protected capital. ATTACK may activate only while equity remains above the protected floor by the required free cushion.

At every decision Risk computes worst-case loss including modeled cost. Exposure is reduced or rejected if the proposed risk could touch either:

- the protected-capital floor;
- the 4.75% internal daily floor;
- the 4.95% capital drawdown floor;
- the Risk heat ceiling.

## Exploratory result observed before this document

These results are disclosed as already observed and therefore are not independent confirmation.

### 10,000-path final re-evaluation on a seed distinct from search

B COMBINED, stop unchanged, BANK25 at +2%, base Risk r125 (A 1.25%, GBPJPY 1.00%), ATTACK r250 (A 2.50%, GBPJPY 1.90%):

- Phase-1 +10% probability: 4.71%.
- Two-phase +10% then +5% probability: 0.70%.
- Same-base Risk-only two-phase probability: 0.24%.
- Absolute CIBO BANK→ATTACK delta: +0.46 percentage points.
- Relative two-phase improvement vs same-base Risk-only: ~191.7%.
- +11% then +6% sensitivity: 0.44%.
- Worst observed daily drawdown: 4.75%, never 5.00%.
- Worst observed capital drawdown: 4.95%, never 5.00%.

### 2024–2026 chronological decomposition for B

Using base r100 (A 1.00%, GBPJPY 0.80%), ATTACK r200 (A 2.00%, GBPJPY 1.50%) and BANK25 at +2%:

- Risk-only: -4.95%; ATTACK never activates.
- BANK→ATTACK without post-entry stop protection: -4.95%; ATTACK never activates.
- Post-entry protection (`+0.5R -> BE`, `+1.0R -> +0.5R`) + BANK→ATTACK: +15.5792%.
- Delta versus same-base Risk-only: +20.5292 percentage points.
- Max daily drawdown: ~2.1032%.
- Max capital drawdown: 4.95%.
- 111 VT-08 generated signals preserved; 58 executed, 53 Risk lockouts, 27 ATTACK trades, 26 protected exits.

The causal interpretation is therefore not "aggression alone works". On the chronological 2024–2026 path, CIBO first needs to protect enough trade outcomes to create the +2% bank trigger; only then does the aggressive Risk state become available.

## Authority

Research only. No LIVE, no real capital, no merge, no READY and no production authorization. A future unseen interval is required to validate any selected BANK→ATTACK policy independently.
