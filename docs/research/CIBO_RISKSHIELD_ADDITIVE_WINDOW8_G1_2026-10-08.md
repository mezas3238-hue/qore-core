# CIBO — additive eighth causal drawdown window G1 (scientific experiment)

Date: 2026-10-08. Status: in-research on **reused** three-year benchmark; not certification. Isolated branch `agent/cibo-riskshield-additive-window8-g1-001`, canonical source commit `ebbfacc6d28c26c32e76fb3bb6043e9d55f32dec`.

## Sovereign goal and baseline
Target future milestone **<=22% historical max DD** without degrading CIBO's economic ceiling. Certified status requires subsequent frozen external fresh 3-year holdout and scientific tests. Current exact research carrier **37.77211161548658% max DD**, terminal capital **USD 668,910.439682713**, total gross loss **USD 957,225.911831171**, ATTACK gross loss **USD 955,665.772155971**, PF **1.698738334823389**, 3,368 of 3,368 Trader entries maintained. Frozen capital floor **USD 582,440.0252953678696769360345**; the stronger growth-preserving comparison seeks **>=USD 668,910.439682713**.

**Accounting:** ATTACK sovereign breach = 0, but `sovereign_floor_breach_usd=84.617235934...` exists in the reused control. Keep separate. Do not present accounting certification until investigated.

## Why this experiment is different

B1, C1, D1, E1 and F1 failed to produce a STRICT PARETO carrier improvement. F1 trial of ATTACK post-entry adverse partials [run 37737706543](https://github.com/mezas3238-hue/qore-core/actions/runs/37737706543), 8 cases SUCCESS, all rejected; even mild 5% partial at 10% projected-risk threshold worsened DD to ~49.795% while capital fell to ~USD 664,843. Broad lifecycle changes caused far larger capital collapse. Never promote such rules.

- The incumbent window7 is a small-capital causal guard (100x–170x, capital USD 1,000–1,300) with just 3 binds but crucial compounding protection. C1 repurposed window7 for high multiplier risk; this destroyed low-capital protection, contaminating the DD outcome.
- D1 widened pre-existing window4 too broadly (4,800x–up to 9,000x), resulting in severe economic damage.
- G1 therefore **adds window8 as an independent optional gate**, leaving windows 1–7 unchanged.
- W8 depends only on causal *predecision* maximum allowed multiplier, current realized drawdown, current total capital and configured bounds. No Trader identity, no future outcomes, no entry rejection. The experiment is not a genuine predictive neural model; its efficacy must be established by replay.

## Observed 2021 causal research question

Reproduced original control artifact `11525552745` from E1. For **calendar dates** 2021-02-09 through 2021-02-26 (inclusive), ATTACK had 28 realized settlements; positive ATTACK realized net ~USD **7,943.44**, negative ~USD **24,942.39**. Among high-multiplier settlements (>=4,000x), 4 trades: 1 positive ~USD **6,314.91** and 3 negative totaling ~USD **19,407.94**. ATTACK settlements >=5,000x were exactly 3 negatives in this sample (not a forward-looking predictor). This demonstrates why a blanket high-multiplier ban risks cutting significant winners and must not be justified by in-sample winner labels.

The largest negative episode settlements include 8,106x / -USD 9,565.08 and two 5,000x settlements / -USD 5,980.56 and -USD 3,862.30. These are **observed outcomes**, not information available at the entry moment.

## Source changes G1

1. `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py` — window8 parameters, validation, independent bind counter, optional post-window7 attenuation, full telemetry. Original windows 1–7 untouched.
2. `scripts/cibo_trader_lab_three_mode_ceiling.py` — seven matching CLI options mapped into the research engine.
3. `.github/workflows/cibo-riskshield-additive-window8-g1.yml` — exact baseline plus 8 experimental variants, SHA/digest-checked input artifacts and multiple numeric gates.

[GitHub Actions run G1](https://github.com/mezas3238-hue/qore-core/actions/runs/37738207384) and all nine JSON artifacts, when complete.

## Control versus candidate schedule

Control: window8 disabled, all seven original guards retained.

Window8 bounds proposed: multiplier 5,000–10,000x at live capital USD 35,000–65,000 and realized DD 0–45%, with attenuation fractions **0.995, 0.99, 0.98, 0.95, 0.90**. Two additional 7,000–10,000x or 5,000–8,200x variations, and one narrower capital band USD 45,000–65,000.

Ranking validates 3,368 trades, zero MEDIUM reject/defer, zero ATTACK sovereign breach, control parity to exact baseline capital/DD/loss, both window7 and window8 bind counters, terminal capital, DD, GL, ATTACK GL, profit factor and a strict Pareto pass condition.

**STRICT PARETO** requires capital >=USD 582,440.025295 and DD strictly below 37.772111615%, total/ATTACK gross loss no worse, all 3,368 entries, no rejection/breach; *full economic dominance* additionally requires capital >=USD 668,910.44. If a candidate worsens GL or economic quality, mark as diagnostic only, not promoted.

## Lessons for next iteration

- Confirm actual window8 binds before interpreting no-change results. A configured gate with zero binds has not been tested economically.
- Track top 10 historical DD episodes, including 2019 MEDIUM at ~37.666%, 2020 Sep ~37.017%, 2020 Apr ~36.406%; dropping just one episode cannot achieve 22%.
- If W8 finds a favorable narrow band, prefer a *causal projected-risk and confidence guard* instead of memorizing these calendar dates/Trader IDs.
- Preserve sealed future 3-year OOS and never call reused replays certification.
