# CIBO H15 — TRUE SOURCE CLONE / $60 RISK-ONLY 5% REPLAY / MODE PROFITS

**2026-10-08 — P0 — RESEARCH ONLY — NOT CERTIFIED**

## Why H15 supersedes H11–H14 as a fidelity check
The user explicitly prohibited changing CIBO methodology, cognitive engine, post-entry management, economic compound or Trader decision list. H11 was only a structural Trader R calculation, and H14 employed intentional economic ablation comparisons. Neither may be advertised as original CIBO profitability. H15 is **an exact snapshot of the latest engineering CIBO branch** rather than the older G5 research branch.

- Canonical base: `agent/cibo-causal-expectation-leakage-fix-001`, unchanged source bits in H15 branch.
- Isolated clone: `agent/cibo-faithful-clone-fivepct-full-replay-h15-001`.
- GitHub compare against latest canonical base at creation: **exactly 1 added workflow YAML file, zero changes to any original CIBO source file**.
- Workflow `.github/workflows/cibo-trader-lab-faithful-original-5pct-h15.yml`, commit `c95dc60dcef18c63e2853a9829961f4b39c83d79`. Run [37776873181](https://github.com/mezas3238-hue/qore-core/actions/runs/37776873181).
- Pinned full 3368 historical manifest and frozen predecision cognitive evidence; all original mode routing, Bank treasury, MEDIUM, ATTACK, native CIBO Compound, Portfolio Compound, Leverage, lifecycle/post-entry protection intact.
- **Only modified financial input in temporary replay copy**: `MEDIUM_RECOMMEND_RISK_FRACTION` numeric 0.04 → 0.05, and pre-existing `--ceiling-attack-single-trade-risk-fraction` input 0.20 → 0.05. These are stop-risk budgets/ceilings, not forced exact fills. The variant code is created in runner tempfile, not committed over canonical source; one-line diff is automatically asserted and exported.
- Control case `h15-original`: bitwise exact canonical CIBO module code with original medium 4% and ATTACK 20% cap.
- Owner risk case `h15-5pct`: source bitwise identical except the single medium numeric value, and ATTACK CLI 5% cap.
- Separate **scientific counterfactuals only**, NEVER counted as the exact CIBO source, `h15-5pct-no-sizing` and `h15-5pct-no-portfolio`; these cannot be deployed or added as independent revenues.

## Required report
Strictly reconcile net trade receipts over all 3368 original signals to total final minus original USD60. Report **Bank direct trade PnL = USD0 and 0 trades** (treasury), MEDIUM net PnL and ATTACK net PnL, open stop dollars and fees; report **bank cash transfers** to Portfolio as treasury accounting, not independent economic gains. Report **Sizing** and **Portfolio Compound** marginal value as `full_profit - without_engine_profit` under separate counterfactual replays; explain attribution interactions and non-additivity. Show capital, max drawdown, gross losses, sovereign bank floor breach, all 3368 preserved.

**DO NOT CLAIM success merely because a workflow was triggered.** Verify GitHub run completion, scientific assertions, and archive. No USD60 economics is a USD2k FundedNext brokerage replica and provider fees here remain the original CIBO research inputs, not USD14/lot user broker commission scenario.

## Safety
A positive ledger terminal net profit cannot be certified if sovereign bank floor is breached, or broker margin / MTM / actual min lot / swap / spread / liquidation viability is unproven. Strict preserve Trader sovereignty: no hidden entry discards. Next architect may design separate physical/funded replay without changing original method, after reproducibility and clear source contract.

*Economic run result to be appended after verification; no fabricated or prospective numbers.*
