# QORE CIBO — H21 MASTER CONTINUITY / BANK FLOOR ZERO / DD 34.35372258% / 3368 TRADES

**2026-10-08. RESEARCH ONLY. Original CIBO method preserved. NOT CERTIFIED / NO VPS LIVE AUTHORITY.**

## Owner binding orders
1. CIBO itself manages all **3368** Trader-executed entries; no admission filtering, rejections or signal deletion.
2. Keep original CIBO cognitive, BANK, MEDIUM, ATTACK, Sizing, Leverage, CIBO Compound, Portfolio Compound and causal M5 management. Only adjust monetary allocation and native risk/stop parameters.
3. Stop-loss risk nominal **5% of current capital**, $60→$3 if physically executable. Exact per-trade risk may bind at mandatory 1x, historical prior, margin and source caps; don't claim every entry exactly $3.
4. Repair sovereign floor and drive max DD **≤25% acceptable / ≤20% ideal**, ideally without reducing profit ceiling. Never pretend $60 backtest is real funded $2000 Stellar Instant or use $14/lot FundedNext pricing silently.
5. No certified gains until full solvency, intratrade MTM / broker execution and independent sealed OOS.

## Empirical master evidence: runner H21 SUCCESS

[Run 37781108417](https://github.com/mezas3238-hue/qore-core/actions/runs/37781108417).
Full H21 JSON in `docs/research/CIBO_H21_ZERO_BANK_BREACH_DD_34P35372_VERIFIED_REPLAY_RESULTS.json` commit `3149d65043524bae964ba440b6916f8675d338ad`.

Research carrier: `h21-share50-cut020`
- Source: Original CIBO from source snapshot on `agent/cibo-causal-expectation-leakage-fix-001`, exactly same provider model and 3368 original Trader signals.
- Nominal entry risk: MEDIUM effective fraction 0.05 + ATTACK single-trade fraction 0.05; old physical source/min-lot guard behavior is NOT altered in canonical source.
- `--economic-group-bootstrap-cushion-share 0.50`: finance BANK with **50% of real distributable MEDIUM net profits** (no fake cash; the other half to portfolio).
- `--lifecycle-adverse-loss-cut-r -0.20`: *existing causal post-entry partial-loss-reduction* mechanism (earlier −0.40); no future outcome flags or new method.
- 3368/3368 original trades, 2520 MEDIUM + 848 ATTACK, 0 BANK trade entries.
- $60 starting → **$3589.260487255495** ending, **+$3529.260487255495** net modeled.
- **Max DD = 34.35372258175%**; improvement vs $60->$3180.250244 DD36.910539%. The DD target 25% remains a strict unresolved P0 blocker; do not classify as certified.
- **Sovereign floor breach 0** exact. Sovereign bank end **$276.552438505152**, minimum **$42.480087114338** (floor dynamically varies with sovereign bank peak). Ending sovereign protection floor 208.571672729969.
- Gross modeled losses **$13339.48786619**, not strict Pareto relative H16 gross $12368.98058479; risk/profit tradeoff requires disclosure.
- Native model provider costs total ~$1621.18849, NOT user FundedNext $14/lot.
- Reconciliation precision: total net = final minus $60, difference < 1e-20.

## Ablation & failed rescues — preserve evidence
- **H18** bank-only profit split 0.50 at −0.40R → USD3304.54715, DD36.910539%, bank breach0. Combined 0.50 at −0.25R → USD3571.79859, DD34.696185%, bank breach0. [Run 37780120854](https://github.com/mezas3238-hue/qore-core/actions/runs/37780120854), artifact 11552980035, JSON `docs/research/CIBO_H18_BANK_FLOOR_ZERO_BREACH_DD_34P696_REAL_REPLAY_RESULTS.json`.
- **H21** fine tuning −0.25 / −0.20 / −0.10 / −0.05 with 50% MEDIUM-to-BANK: **−0.20R is current local DD and capital frontier** among tested; −0.10R DD34.991%, −0.05R DD34.740%. All floor zero. No ≤25% yet.
- **H22** stronger globally applied 1x MEDIUM stop thresholds + 1-trade loss streak: **REJECT ALL** because DD47.185% to 73.099%, floor breaches $11.61–$17.71, terminal profit lower (USD1076–1617 total capital). [Run 37781404186](https://github.com/mezas3238-hue/qore-core/actions/runs/37781404186), JSON on H22 branch. Tight stops hurt winning recoveries and regime composition, so tighter is not automatically safer.
- **H19** distinct experimental module tried zero-sum cushion→bank transfers. It eventually completed [run 37781691734](https://github.com/mezas3238-hue/qore-core/actions/runs/37781691734): 73 transfers totaling USD163.71584 in full-cushion case, no material new capital, gross bank breach residual ~5e−27 from Decimal rounding and DD unchanged36.910539%. 50% profit split H19 resulted **0 transfers and byte-identical H18 34.696%**. **DO NOT merge H19 code**; native profit routing H21 is simpler, tested and already yields exactly zero floor breach.
- **H23** separate hypothesis to activate existing 1x protection only when portfolio drawdown ≥10–20% (causal) rather than globally; workflow `.github/workflows/cibo-trader-lab-dd-conditional-medium-defense-h23.yml`, branch `agent/cibo-h23-drawdown-conditional-medium-1x-defense-001`, outcome pending at H21 handoff publication. Treat as new hypothesis, no forecast.

## What specifically caused DD
Worst baseline episode peak `2019-07-19T06:45Z` capital $79.76393861 to trough `2019-08-12T11:25Z` (modeled) capital $50.32263874: DD36.910539% and negative PnL −$29.44129986, **MEDIUM only**, most losses at mandated 1x. Bank treasury reallocation cannot directly lower total DD (zero-sum). To reach 25%, gross peak-to-trough decline would need to shrink to $19.94098465, i.e. **~$9.50 losses avoided** under fixed peak assumption. Suppressing all 2x losing contribution (~$4.058) is insufficient. Need better causal post-entry losses at 1x, balanced against profitable trades; do not invent a past hindsight blacklist.

## Certification action items
- Inspect H23 outcome. If robust, rank on zero bank floor + DD + profit + gross losses, never promote if new DD worse or negative bank.
- If H23 fails, study specific 2019 regime M5 closed-bar contexts and portfolio risk pressure *at entry* and causal exit; tune real existing CIBO cognition/postentry only with independent future holdout. No cherry-picked 2019 dates, symbol/trader blacklists, or outcome leakage.
- H8 physical funded minimum fallback P0 **still open**: mandatory Trader 1x may be unfinanceable with actual broker symbol margin and start USD60. Broker intratrade equity/stopout not simulated in H21. Do not confuse zero internal sovereign floor breach with fully certified cash liquidity.
- Retest FundedNext Stellar Instant **USD2000** separately, strict 6% trailing max loss, internal USD60 daily and concurrent budget, user 7 USD/lot open + 7 USD/lot close model, actual broker contract leverage, min lot and commission reality, floating MTM, spread, swaps and stressed slippage.
- Full science: sealed 3yr OOS, walk forward, bootstrap/Monte Carlo drawdown, robustness to costs, cognition ablations, audit records and integration with certified Traders/Shared. Existing 2019-22 reused data are not blind OOS certification.
- Do not touch other architect's source branch; this is isolated forensics, and owner approval of 5% micro risk is nominal budget rather than broker feasibility guarantee.

**NO CERTIFICATION CLAIMS. CURRENT RESEARCH FRONTIER H21: $3589.26 / DD34.3537% / sovereign breach0 / 3368 entries.**

## IMPORTANT: DISTINCT GLOBAL PERFORMANCE CEILING NOT REPLACED BY MICRO 5% RESULT
The historic CIBO maximum-return sovereign economic floor **$582,440.03** (discovered with different 10,000x ATTACK compounding and DD ~65%) belongs to a *different unconstrained capital/execution experimental regime*. This branch H21 is a **new, owner-demanded $60 micro-capital 5% nominal-risk study**, so its $3,589.26 is not a superior replacement for that historical ceiling. Treat each as independent unsolved certification programs. None of these old model dollar outcomes demonstrates real broker-fundable gross capital; deployment must satisfy physical minimum lots, liquidity and intratrade margin. H21 zero internal sovereign breach is required but never sufficient proof.

## H23 result (not pending anymore) — independent 3,368 replay success
[H23 run 37782194937](https://github.com/mezas3238-hue/qore-core/actions/runs/37782194937) completed SUCCESS. Variant `h23-def010-dd020` conditioned an existing MEDIUM 1x protection stop at −0.10R only when *already observed* realized portfolio DD >=20%, native trader loss streak>=1, 1x risk>=1.5%, with bank profit split50% and adverse partial cut−0.20R. It recorded **final $3574.18138, max DD33.81212445%, bank floor breach0, 3368 entries**. DD is 0.5416pp better than H21 but final capital ~$15.079 lower, so *not strict Pareto over H21*. Other H23 combinations DD38.37% and DD46.06%, reject. See H23 branch JSON `docs/research/CIBO_H23_DD_CONDITIONAL_MEDIUM_33P812_VERIFIED_RESULTS.json` commit `b20888d9c64f561f04f43bf3eeb8c3cf48f13815`. H24 is follow-up targeting only large MEDIUM risks when account DD >=20–25%, **not yet verified** at this update.

## H24 final verified results — historical DD minimum reduced but not yet certified
H24 run [37782797158](https://github.com/mezas3238-hue/qore-core/actions/runs/37782797158) **SUCCESS** and 3,368/3,368 entries, native no-source-change risk/stop parameter tuning.
- Best zero-bank-breach *raw DD floor*: `h24-def005-min030-dd020`, bank share50%; existing MEDIUM defensive initial stop −0.05R, only after predecision live portfolio DD>=20%, prior same-trader losing streak>=1 and entry baseline stop risk >=3.0% of current capital; native adverse partial cut−0.20R. **DD33.5413253866%, capital $3304.366913, bank breach0, sovereign bank end $182.348698**. 846 ATTACK + 2522 MEDIUM, 0 BANK trades. Gross losses $12,779.126513.
- `h24-def010-min025-dd020`: DD33.812124%, cap $3304.419775, bank breach0; lower net than H23 without DD benefit. Reject.
- `h24-def005-min025-dd025`: DD33.541325%, cap $3304.584830, **sovereign breach $3.454510**. Reject.
- H24 33.5413% is better DD than H23 33.8121%, but $269.814 less capital, so **NOT strict Pareto H23**. Neither meets <=25% requirement. Persisted H24 machine-results JSON `docs/research/CIBO_H24_LARGE_RISK_CAUSAL_DD_33P541_RESULTS.json` commit `6e87aa22bfc767e75ffb53b9cde0b83ae181d9ce` on H24 branch.
- The previous “frozen” $582,440.03 historical extreme-leverage ceiling is a separate regime; neither H21/H23/H24 can claim matching that floor with nominal 5% micro-capital risk.

**CURRENT VERIFIED MULTI-OBJECTIVE FRONTIER (NO WINNER UNDER BOTH TARGETS)**:
H21 maximum capital $3589.26 / DD34.3537% / bank breach0;
H23 better DD33.8121% / cap $3574.18 / bank breach0;
H24 minimum DD33.5413% / cap $3304.37 / bank breach0.
No candidate achieves DD<=25% nor historical broker-fundable viability. Never promote an overfitted 2019-only signature to certified without blind fresh OOS.
