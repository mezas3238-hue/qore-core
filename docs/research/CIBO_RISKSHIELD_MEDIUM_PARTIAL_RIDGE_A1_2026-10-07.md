# CIBO — RiskShield MEDIUM causal partial A1 — reproducible replay report

**Owner:** QORE CIBO research. **Date (America/Asuncion):** 2026-10-07.
**Status:** preliminary research-only, reused ~36-month holdout; NOT certification evidence.
**Isolated branch:** `agent/cibo-dd-riskshield-lifecycle-a1-001`.
**Source revision:** `d5c2ba1cc9f3b16316837875eff51c3b2a4c4278`.
**Experiment workflow:** `.github/workflows/cibo-trader-lab-riskshield-medium-partial-ridge-a1.yml`.
**Workflow commit:** `fbc425e302aa1136aa409575ea6c334fd0ca1209`.
**Run:** [37717084056](https://github.com/mezas3238-hue/qore-core/actions/runs/37717084056) — SUCCESS.
**Artifact ID:** `11524715346`.

## Scope and controls

Test the 38.11% research lineage *without editing the concurrently active canonical branch*, particularly its MEDIUM 1x/2x bootstrap loss episode (2019). Retain all ATTACK windows, four economic engines and causal expected-R gating. Vary only the post-entry bootstrap `ADVERSE_PARTIAL_REDUCTION` fraction (0.30/0.35/0.38/0.40/0.42/0.45), plus two narrowly scoped expected-R ceilings (0.08/0.12). Use frozen `fusion-c` 38.0308091811% as primary control; include an earlier sc-j control. No Trader rejection, hardcoded Trader blacklist, new data leakage or production changes.

Mandatory invariants in ranking: 3,368 decisions/trades, 3,368 final trades, all entries preserved, zero Sizing MEDIUM reject/defer, zero ATTACK sovereign breach. Reject results below the sovereign frozen capital floor **USD 582,440.025295...**. Strict relative to fusion-c requires DD improvement and no degradation of total/ATTACK gross loss, with floor intact; the stronger `dominates_current` also requires at least equal terminal capital.

## Results

| Case | Capital USD | DD | Total gross loss USD | Vs fusion-c |
|---|---:|---:|---:|---|
| fusionc-control, partial 0.40 | 668,669.925976 | 38.030809% | 957,251.518203 | baseline |
| **fusionc-partial42, partial 0.42** | **668,669.893061** | **37.902425%** | **957,251.194762** | **Strict relative to fusion-c; not full economic dominance** |
| fusionc-partial38, partial 0.38 | 668,669.717579 | 38.159193% | 957,252.082955 | rejected |
| fusionc-partial35, partial 0.35 | 550,659.431264 | 38.351769% | 951,824.986544 | below frozen floor |
| fusionc-partial30, partial 0.30 | 523,387.061511 | 40.614449% | 938,923.058163 | below floor, higher DD |
| fusionc-partial45, partial 0.45 | 117,886.357850 | 67.011983% | 677,458.013252 | catastrophic capital destruction |
| fusionc-exp08p40 | 550,575.395611 | 38.030809% | 951,499.429552 | below floor |
| fusionc-exp12p40 | 668,621.581145 | 46.014367% | 964,525.838613 | rejected |
| baseline38115 / sc-j prior control | 667,694.561190 | 38.232892% | 960,515.177353 | non-primary reference |

`fusionc-partial42` versus `fusionc-control`: DD improved **0.12838412 percentage points** (38.03080918% to 37.90242506%); total gross loss fell **USD 0.32344037**; ATTACK gross loss fell **USD 0.09484782**; PF approximately **1.69846859**; terminal capital fell only **USD 0.03291450**. 127 causal bootstrap overrides were observed in both. The max-DD period remains **2019-07-19T06:45Z to 2019-08-12T11:25Z**, MEDIUM mode. The micro-change is causal but has not removed the underlying bottleneck.

**Important global comparison:** In concurrent canonical research, the stronger carrier `carrier37772-p4150` was observed with **37.7721116% DD**, **USD 668,910.43968 capital**, and **USD 957,225.91183 gross loss** (GitHub Actions 37716702999 / 37716629160). The A1 37.902425% candidate is worse on those global metrics; **DO NOT PROMOTE OR REPLACE** the canonical carrier on the basis of this A1 result.

## Scientific interpretation

Small causal MEDIUM partial-fraction changes can compress one specific drawdown episode without materially reducing terminal capital. However outcomes are **strongly nonlinear**: 0.45 caused a very large drawdown and wealth collapse; 0.35 reduced loss but failed the frozen capital floor. This validates *narrow, context-aware post-entry management as a promising research direction*, not a universal stop/lifecycle adjustment.

The present A1 change is an **experiment only**. It is **not** an implemented predictive risk shield, not a proof that future holdout DD stays below 20%, and not a complete solution to cross-Trader correlation/aggregate downside exposure. It does not justify applying `0.42` globally.

## Next experiments (on the canonical latest strict-Pareto carrier only after source verification)

1. Refresh latest candidate and determine whether max DD is MEDIUM 2019, ATTACK 2021, or another episode.
2. Build causal aggregate open stop-risk + high-confidence correlated shock headroom diagnostics, measured before entry/exit decisions; do not reject Trader entries.
3. Test limited, targeted and reversible portfolio risk-budget taper when correlated projected stress exceeds budget; compare control and multiple mild settings.
4. Evaluate 2019 MEDIUM partial 0.42 as a local diagnostic only, but do not replace the better 37.772% global carrier without full STRICT PARETO improvement.
5. Keep holdout sealed; freeze parameters and use independent three-year data, walk-forward and stress tests only after research gates.

**Reproducibility:** exact script and input artifact digests are included in the workflow. Artifact and run logs preserve all 9 JSON replay outputs and acceptance assertions.
