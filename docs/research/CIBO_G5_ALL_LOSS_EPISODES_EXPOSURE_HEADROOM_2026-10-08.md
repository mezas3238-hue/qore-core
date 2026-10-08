# CIBO G5 — full drawdown loss headroom and causal ATTACK exposure-gated replay

2026-10-08 · QORE CIBO historical 3-year REUSED research, not sealed certification holdout. Independent branch `agent/cibo-loss-tail-causal-exposure-g5-001` isolated from `agent/cibo-causal-expectation-leakage-fix-001`.

## Frozen source and exact repeatability

- Winner verified `em-s06745` in GitHub [run 37759974174](https://github.com/mezas3238-hue/qore-core/actions/runs/37759974174); output archive/artifact **11542321736**. Source SHA `44d368c1d4e439eb15a6f8282bcb5b89a1f79497`. Received 3,368/3,368 complete trades, all entries preserved and zero ATTACK sovereign breach.
- Verified carrier final **USD 673,146.5254539803718539973234**, total GL **USD 940,435.7630554367602465029838**, ATTACK GL **USD 938,872.8495404670959553183518**, max DD **36.91053924475215947767935340%**, PF **1.71571770438**.
- Frozen floor USD 582,440.0252953678696769360345. Important **separate `sovereign_floor_breach_usd = 85.41649567391081325466487569`** (NOT zero!) on this carrier. Requires accounting forensic and repair before clean certification, independent of `attack_sovereign_breach_usd=0`.
- The user explicitly prioritized exhaustive big-loss analysis **before** tuning, and asked all 3,368 decisions be preserved. Prior master report: `agent/cibo-complete-loss-forensics-3368-h1-001/docs/research/CIBO_MASTER_LOSS_FORENSICS_3368_2026-10-08.md`, commit `d99ea36776aca53279a962713216ddd80d385343`.

## Present carrier: all top ten loss/DD episodes

Data directly parsed from `em-s06745.json.drawdown_forensics.top_10_episodes` (G5 frozen parent); no hindsight values may enter decision policies. Fourth column is required loss improvement **only if peak remains fixed and no gains/path changes**, a diagnostic not a proven attainable counterfactual:

| Episode | Peak UTC → trough UTC | Peak-to-trough DD | Observed peak USD | Loss USD | Reduction needed to attain 22% with fixed peak USD | Principal mode |
|---:|---|---:|---:|---:|---:|---|
| 1 | 2019-07-19 → 2019-08-12 | 36.911% | 79.76 | 29.44 | **11.89** | MEDIUM |
| 2 | 2020-04-03 → 2020-05-13 | 36.693% | 720.98 | 264.55 | **105.93** | ATTACK |
| 3 | 2020-06-24 → 2020-06-30 | 36.413% | 4,288.72 | 1,561.64 | **618.12** | ATTACK |
| 4 | 2020-08-19 → 2020-09-28 | 34.737% | 12,541.29 | 4,356.47 | **1,597.39** | ATTACK |
| 5 | 2021-02-09 → 2021-03-03 | 33.151% | 62,653.34 | 20,770.08 | **6,986.35** | ATTACK |
| 6 | 2020-01-31 → 2020-03-06 | 33.150% | 119.38 | 39.57 | 13.31 | ATTACK |
| 7 | 2020-03-23 → 2020-03-26 | 32.185% | 577.82 | 185.97 | 58.85 | ATTACK |
| 8 | 2020-05-21 → 2020-06-08 | 30.818% | 1,225.67 | 377.73 | 108.08 | ATTACK |
| 9 | 2019-11-04 → 2019-12-11 | 30.153% | 96.25 | 29.02 | 7.85 | ATTACK |
| 10 | 2019-09-24 → 2019-10-14 | 25.639% | 83.51 | 21.41 | 3.04 | ATTACK |

**Scientific deduction:** fixing only the 2019 MEDIUM bootstrap episode is insufficient. All ten episodes exceed 25% and nine exceed 30%; at least nine are dominated by ATTACK or ATTACK-mixed outcomes. Loss USD and DD percent are distinct rankings. Target multi-epoch exposure compression without hindsight optimization or wealth destruction.

## G5 causal test: expose risk, not winner/loser outcome

- New isolated workflow: `.github/workflows/cibo-trader-lab-loss-tail-causal-exposure-g5.yml`, GitHub [run 37761586870](https://github.com/mezas3238-hue/qore-core/actions/runs/37761586870) triggered from commit `5f3b4baf1f6452f540d11604bba5b0f331cfdde4`.
- Replays 9 full portfolios in parallel: exact `em-s06745` control and 8 hypotheses on **`--lifecycle-attack-override-projected-open-stop-risk-fraction-trigger`** thresholds (0.03,0.04,0.05,0.06,0.08,0.10,0.12,0.15). Control keeps all already established 7 windows, MEDIUM `-0.6745` causal context stop, ATTACK guarded context stop `-0.50` and economic compounds. No Trader-specific whitelists, date filters, future PnL or decision veto.
- This gate observes already-estimated entry-time portfolio projected stop-risk fraction and determines whether to apply **ATTACK lifecycle management after Trader entry**. Eligibility also retains frozen 6-way decision-time market context. It does **not** cap the live stop risk/guarantee the DD bound. It will expose how many controls bind and how many were blocked by risk floor.
- Ranker enforces **exact baseline parity** at 100-digit DD and full capital/loss precision, **3368/3368 decisions**, zero ATTACK sovereign breach, zero MEDIUM reject/defer, checks total and ATTACK gross losses, capital floor and stronger >= incumbent, drawdown, PF and bottleneck attribution. Trials fail/reject if preserving wins is not proven.
- Expected results may be NO-OP or worsen risk; never claim progress until SUCCESS logs, result JSON and gate validations.

## Next engineering logic conditional on G5

If G5 has NO full Pareto improvements: **reject** and do not interpolate hindsight; move to distinct causal stop-risk **occupancy** or closed-M5 intratrade adverse signal. Specifically inspect pre-entry risk occupancy and lost-trade clustering in 2020, then identify gain-preserving post-entry economic interventions at a portfolio episode level. Maintain an explicit matched winner cohort when studying ex-post outcomes; avoid restricting Trader entry. When a test reduces one DD and increases another, re-rank entire top-ten. Rerun independent 3-year sealed holdout only when frozen and ready for certification.

**Current milestone not reached**: ≤22% DD required; no “Trabajo cumplido” without successful replay meeting ALL gates.
