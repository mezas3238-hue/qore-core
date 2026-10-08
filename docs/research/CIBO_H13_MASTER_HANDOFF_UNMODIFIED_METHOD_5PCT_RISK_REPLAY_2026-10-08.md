# QORE CIBO H13 | Original method / only risk dollars: 5% on MEDIUM and ATTACK

**2026-10-08. Research only, not certified.**

## Unambiguous order from owner

**DO NOT CHANGE CIBO'S METHODOLOGY.** Keep exactly original:
- The same 3,368 Trader entry decisions (2019–2022).
- The same CIBO cognitive judgments, bank/cushion handling, Leverage, Sizing, CIBO Compound and Portfolio Compound.
- The same mode assignment ATTACK/MEDIUM, full lifecycle rules, protective exit R, commissions/provider costs as originally modeled, context routing, profit-taking, loss mitigation and input artifacts.

**ONLY change the financial risk sizing amount to a nominal 5% of current capital per entry.** At $60 this means the target is **$3 stop exposure**, *not* a fixed $10 stop. Nominal budget does not override the CIBO method's 1x mandatory baseline, original portfolio/margin/seed native-cap constraints, nor its ability to assign a smaller physical stop amount; verify actual entry receipts before claiming every signal used exactly $3.

This is **not** the FundedNext $2k/$14-per-lot replay. It is the original $60 CIBO experiment with original provider cost assumptions, so cost and broker viability remain uncertified. The user explicitly ordered same original method; reintroducing $14/lot here would change an additional input and defeat clean causality.

## Changes: monetary sizing only

- Source branch `agent/cibo-original-method-all-modes-5pct-sizing-h13-001` FROM `agent/cibo-loss-tail-causal-exposure-g5-001`, isolated from sovereign architect branches.
- Capital module `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py` commit `d5a8cbc48d59a73e6c25970127921cf27bb4f998`: new optional MEDIUM fraction override. `None` exactly preserves canonical original logic. `0.05` replaces only MEDIUM nominal monetary stop sizing fraction after canonical cognitive classification. No other CIBO behavior changed.
- Runner `scripts/cibo_trader_lab_three_mode_ceiling.py` commit `f66d64190f96f9deabb762c2253f2ac8f1ca2449`: CLI `--medium-entry-risk-fraction`.
- Existing ATTACK monetary sizing knob `--ceiling-attack-single-trade-risk-fraction`: original **0.20**, variant **0.05**, both rely on same canonical underlying CIBO computation (including native taper when applicable).
- Workflow `.github/workflows/cibo-trader-lab-original-method-all-mode-risk-5pct-h13.yml` commit `8e3052251412f5ba292ab99af772a38beb43d66e`, trigger push/dispatch.
- Exactly two full replay cases, same inputs:
   - `h13-original-risk-020` original ATTACK 20%, MEDIUM no override (historical baseline parity).
   - `h13-original-risk-005` ATTACK 5%, MEDIUM nominal 5%.
- Frozen control checks initial USD60 → USD673,146.525454 and max DD 36.91053924475%, plus 3,368 full accepted Trader entries. Any drift aborts run.
- Prints capital, max DD, gross losses, ATTACK losses, PF, full entry count and **bank sovereign floor-breach**, with hard statement NOT CERTIFIED if breach. Writes `docs/research/CIBO_H13_ORIGINAL_METHOD_RISK_5PCT_VS_20PCT_REPLAY_RESULTS.json` on successful completion.

## Already completed companion H12 ATTACK-only scientific AB (NOT all-mode)

GitHub run [37772285754](https://github.com/mezas3238-hue/qore-core/actions/runs/37772285754), success, complete 3,368 entries.
Control: USD673,146.525454, DD36.910539%, gross loss USD940,435.763055, sovereign floor breach USD85.416496.
ATTACK at 5%, MEDIUM unchanged: **USD3,180.250244** final, DD36.910539%, gross loss USD12,368.980585, sovereign floor breach USD77.103604. This is not a verified account profit, because sovereign protection fails.
H12 results [JSON](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-original-method-only-5pct-risk-h12-001/docs/research/CIBO_H12_ORIGINAL_METHOD_RISK_5PCT_VS_20PCT_REPLAY_RESULTS.json).

## H13 replay verification and certification

GitHub Actions run **37772543921**, link https://github.com/mezas3238-hue/qore-core/actions/runs/37772543921. It passed checkout/compile/pinned source acquisition and entered the actual two full replay subprocesses. **H13 economic results pending verification**, never infer from H12, and never substitute unvalidated H11 structural Trader R.
Scientific gates: 3,368/3,368, no rejected/deferred Trader entries, stable control parity, transparent gross losses + DD + sovereign breaches, physical-account limitations still open.

After valid output, compare actual stop risk fraction distributions (first trade baseline 1x $0.295, not guaranteed $3), and determine whether nominal 5% allocation is achieved under CIBO's untouched constraints. If owner demands *exactly* $3 spent in first trade against original 1x, that may be physically incompatible with unchanged native sizing and must be reported, not faked.

**Never promote old $673k or new variant capital figures to real or certified profit with bank negative or unmodeled broker margin / MTM.**
