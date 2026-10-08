# CIBO H8 — PHYSICAL SOLVENCY FIRST, UNFUNDED BASELINE FAIL-CLOSED
**2026-10-08 / CRITICAL P0 / RESEARCH ONLY / NOT CERTIFIED**

This branch is a deliberately isolated proof/repair branch from `agent/cibo-loss-tail-causal-exposure-g5-001`. It does not overwrite the other architect's work.

## Evidence that changes the economic interpretation
The frozen `em-s06745` research case (run 37759974174, artifact 11542321736, sha256 `0e14d059be5053f453861ef02d119a7290d803d01ca3c74735a94e3a0f127d52`) has:
- 3,368/3,368 terminal trade receipts; modeled USD60 → USD673,146.52545.
- **Sovereign bank minimum −USD55.41649567**, end **−USD46.72669880**, sovereign floor breach **USD85.41649567**, ATTACK sovereign spill metric 0.
- Entire-account **terminal-settlement-only** balance proxy remained **positive**, minimum USD50.32263874497 on 2019-08-12 11:25 UTC. Thus **no evidence of entire-account zero at settlement timestamps**, but this is NOT an intratrade margin/liquidation survival test.
- Reported modeled final PnL **is not certified, not proven broker executable, not transferable as real-world cash profit**. Historical risk research *must not* imply availability for withdrawal.
- See the [H6 forensic corrective report](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-sovereign-dd-rootcause-h6-001/docs/research/CIBO_H6_SOVEREIGN_LEDGER_AND_MULTI_EPISODE_CAUSAL_ATLAS_2026-10-08.md) commit `69d886986181859d659029f07cef5a78dd658934`.

## Exact code-level P0 identified
In `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`, the original code lines around 5933–5978 evaluated capacity, but on over-budget ATTACK demotion to MEDIUM 1x, it **did not recheck funding, total risk and margin** before appending the executed Trader position. Additionally, positive bootstrap MEDIUM PnL was directed to the cushion after repaying deficit, while MEDIUM losses debit the bank, permitting sovereign bank floor violation. A successful ledger arithmetic check is not proof of physical financing.

## Isolated H8 fail-closed patch
Commit `a17683e659c9e985db52706554fcb0d4b769a9d0` inserts a physical capacity assertion **after** any ATTACK→MEDIUM fallback and **before** `selected.append`, including:
- `stop_risk <= risk_left`
- `margin <= margin_left`
- `source_reserved (stop-risk + provider fees) <= source_left`
- MEDIUM source capacity additionally bounded by **sovereign available less protected floor**. Never book liabilities from reserve below floor, even if combined cushion is positive.

If already-executed Trader entry physically cannot be managed at the mandatory 1x under these constraints, **fail the entire research simulation with a named `CIBO_H8_UNFUNDED_EXECUTED_TRADER_BASELINE` error**. Never silently reject/delete the Trader entry and continue fabricating a 3,368/3,368 good-looking curve. This represents an *unsolved pre-trade funding architecture conflict*, not permission for CIBO to select trades.

**Workflow** `.github/workflows/cibo-trader-lab-physical-solvency-h8.yml`: one exact frozen `em-s06745` full replay, pinned historic artifacts and atlas input digests; prints first capacity exception; scientific success only if it catches expected unfunded mandatory baseline, otherwise fail. Workflow result/artifact is pending verification and no result is claimed here.

## Rebuild after honest capacity diagnostics
1. Read first fail-closed breach: capital at decision, sovereign floor, cushion, reserved stop-risk, margin, liquidity, 1x minimum required, provider fees, existing trades and clock.
2. **Trader executes all original entries** as sovereign design constraint, while the bank may lack even 1x funding. Cannot simultaneously promise 3,368 physically executable entries, zero floor breach and fixed USD60 start unless the *actual broker/financing model* can fund them. If infeasible, certify the impossibility, redesign funding/lot sizing/margin/capital seed or handle real bankrupt/stop-out behavior in the replay instead of pretending profitability.
3. Reconcile bank and cushion transfers with *actual available* money, not debt created by ledger arithmetic. Incorporate mark-to-market/open positions, broker stop-out rules, worst intrabar gap, realistic leverage and lot constraints.
4. Restart ceiling discovery on the newly physically valid simulation: **only then** attack DD to ≤25% max tolerable / ≤20% ideal and defend true economic returns. Preserve 3,368 receipt completeness as a scientific invariant and call out physically impossible cases as FAIL, not favorable lower DD.
5. Temporal holdout, Monte Carlo, Monte Carlo risk of ruin, execution stress, entry-by-entry 4-engine ablation, bank custody, CIBO+Traders+Shared integration, full scientific battery before LIVE/demo commercialization.

**NO CERTIFICATION CLAIMS. No PnL result from H8 has been verified.**
