# CIBO scientific continuity — causal DD experiments and provider margin realism
Date 2026-10-08 | Research only | branch `agent/cibo-dual-dd-context-defense-20261008-001`

## Sovereign unchanged
Initial USD 60; terminal floor >= USD 582440.0252953678696769360345; 3368/3368 Trader entries; zero rejection/defer; zero sovereign breach; generic causal features, no future outcomes, dates, Trader IDs or symbol blacklists. DD target <=25%, ideal 20–22%. Reused holdout research cannot certify live fundability or predictive returns.

## Baseline and new local DD frontier

1. Original canonical master `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`; local baseline `m1cliff-n00624` from [run 37765706712](https://github.com/mezas3238-hue/qore-core/actions/runs/37765706712): capital 670925.7614734999606339602478, DD 35.206607393045501467%, total GL 959321.223795176541180456, ATTACK GL 957755.192064147558231916. Local global STRICT Pareto status must be separately assessed.
2. [New independent ridge 37766565962](https://github.com/mezas3238-hue/qore-core/actions/runs/37766565962) on isolated branch: `m2-reclaim-060` DD **34.92401406329469%**, capital **USD 671185.0736747881**, total GL **USD 959500.2966357417**, ATTACK GL **USD 957941.0786191801**, PF 1.69945270056. Floor-valid and improves both DD and terminal capital against local baseline, but total GL +179.072840565 and ATTACK GL +185.886555033. **NOT local strict Pareto, NOT global strict Pareto; retain candidate for research only.**
3. Non-winning candidates in same ridge: `m2-wick-060` DD 34.96083775%, cap USD 670487.83, GL 961747.18; `m2-h4m5-060` DD 35.005551%, cap USD 670938.38, GL 959332.54; several other stop levels incur severe capital cliffs below the sovereign floor. Do not promote. Cases preserve entry count via replay assertions.
4. Next actual experimental sweep: [workflow `cibo-trader-lab-dual-dd-reclaim-cliff-ridge-20261008.yml`](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-dual-dd-context-defense-20261008-001/.github/workflows/cibo-trader-lab-dual-dd-reclaim-cliff-ridge-20261008.yml). Test stop-R local ridge and small W6 taper shifts; require exact metric evaluation before promotion. No live deployment.

## Ten-episode risk audit and margin feasibility red flag

[Successful GitHub forensic run 37766756802](https://github.com/mezas3238-hue/qore-core/actions/runs/37766756802), source artifact 11543738930 ZIP SHA256 `7643863b5d53ae762f2d63e956b20278132d0a9ec554235b28cabaca659f5be9`. Workflow: `.github/workflows/cibo-dualdd-top10-capital-risk-forensics-20261008.yml`. Source case `m1cliff-n00624`. DD snapshot top exposures:

| Episode DD rank | Date of peak | Observed DD | Peak simulated total capital USD | Open stop risk / capital | Open margin / capital |
|---:|---|---:|---:|---:|---:|
| 1 | 2019-07-19 | 35.2066% | 79.76394 | 8.16% | 41.76% |
| 2 | 2020-04-03 | ~35.01% | 705.17 | 1.03% | 0.38% |
| 3 | 2020-09-10 | ~34.60% | 12866.09 | ~0.01% | 0.12% |
| 4 | 2021-02-09 | ~33.38% | 61689.77 | ~0.0025% | 0.10% |
| 5 | 2020-03-23 | ~32.27% | 567.41 | **20.07%** | 4.97% |
| 6 | 2020-08-19 | ~31.90% | 12199.41 | ~0.01% | ~0.01% |
| 7 | 2020-05-21 | ~30.83% | 1227.49 | **18.45%** | **184.46%** |
| 8 | 2020-06-24 | ~30.82% | 4289.78 | 0.36% | 0.29% |
| 9 | 2020-01-31 | ~30.02% | 123.66 | **19.69%** | **34.39%** |
| 10 | 2019-11-04 | ~28.69% | 109.15 | 0.76% | 1.85% |

**Critical finding for broker-realism certification:** at 2020-05-21 peak the recorded open margin was approximately USD 2264.25 on a simulated capital snapshot of USD 1227.49, ratio 184.46%. The engine file `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py` contains `MARGIN_CAPACITY_MULTIPLE = Decimal("100")` and calculates `margin_capacity = total * MARGIN_CAPACITY_MULTIPLE`. Thus the replay allows synthetic risk/margin capacity materially above its capital in this lane. The snapshot does not prove executable broker collateral/margin-level admissibility: it is a scientific **red flag**, not an assertion about a specific provider.

### Independent certification and live deployment gates (NOT YET PASSED)
- State exact broker/account leverage, symbol-by-symbol margin requirements and volume min/step/max; reconcile simulated `margin_per_volume` and actual executable lot.
- Model free margin, margin level and broker stop-out / margin-call thresholds **using provider specifications**, including peak-to-trough mark-to-market open-position equity, hedged and correlated concurrency, slippage/gaps and spread spikes. Do not assume fixed stop-out percentages.
- Verify account total equity vs treasury `sovereign_bank+portfolio_cushion` and mark-to-market unrealized P&L, reservations, open stop risk, provider costs and stop-out liquidation path.
- Produce exact per-event feasibility exceptions, zero unsupported fills, unrealizable P&L quarantined, and risk-of-ruin under clustered losses.
- Until these gates pass, do NOT describe simulated USD 671k as realizable cash, deploy an aggressive 10000x exposure into a live or funded account, or assert full certification.
- Risk snapshots at drawdown peaks are explanatory ex-post forensics, NOT date-specific runtime policy triggers.

## Risk-engineering direction
Current DD cannot reach 25% by targeting one episode: 10 recorded episodes exceed ~28.69% on the baseline. Need causal **multi-episode** risk envelope, not date/identity targeting. Features to test on logged past-state: realized live DD and running peak; normalized open stop risk / mark-to-market equity; provider margin level; last observed closed-bar regime/expected-R; portfolio concurrence/loss clusters; protected profit-keeping lifecycle. Quantify winners lost and economic cliff for each. Promote only if global policy condition satisfied; all holdout-reused research remains uncertified.

## Current artifacts
- [Own post-entry context ridge](https://github.com/mezas3238-hue/qore-core/actions/runs/37766565962)
- [Top-ten margin risk forensic](https://github.com/mezas3238-hue/qore-core/actions/runs/37766756802)
- [Prior causal 2019 atlas](https://github.com/mezas3238-hue/qore-core/actions/runs/37765762713)
- [Prior ATTACK 2020 atlas](https://github.com/mezas3238-hue/qore-core/actions/runs/37765061391)
- [Next reclaim threshold experiment workflow](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-dual-dd-context-defense-20261008-001/.github/workflows/cibo-trader-lab-dual-dd-reclaim-cliff-ridge-20261008.yml)

This is an isolated technical supplement for the canonical master; never rewrite another active architect's handoff concurrently.