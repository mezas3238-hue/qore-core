# QORE CORE — CIBO DD Causal Atlas: 2020 ATTACK and GL rebound
## Evidence checkpoint — 2026-10-08 (reused research holdout; NOT certification)

Canonical handoff: `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`.

**Policy invariant:** initial USD 60, capital floor USD 582,440.0252953678696769360345, 3,368/3,368 entries, zero rejects/deferrals/sovereign breaches, identity-free causal execution. Target DD <=25%, aspirational <=20%. Neither this report nor its replays are fresh sealed OOS.

## 1. Sources and reproducibility

- Global STRICT PARETO: `f-m2850-h0060`, run [37762989521](https://github.com/mezas3238-hue/qore-core/actions/runs/37762989521), artifact `11542893252`.
- Lower physical DD frontier: `m1-0700`, run [37763827843](https://github.com/mezas3238-hue/qore-core/actions/runs/37763827843), artifact `11543178956`.
- New authoritative receipt-level forensic workflow: `.github/workflows/cibo-dd-causal-atlas-2020.yml`, run [37764884178](https://github.com/mezas3238-hue/qore-core/actions/runs/37764884178): SUCCESS; generated JSON artifact with per-receipt GL differences and max-DD window.
- Context join: `.github/workflows/cibo-dd-preentry-context-2020.yml`, run [37765061391](https://github.com/mezas3238-hue/qore-core/actions/runs/37765061391): SUCCESS, using frozen manifest artifact `11451743578` verified against SHA256 `d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`.
- A distinct previously launched run [37764486057](https://github.com/mezas3238-hue/qore-core/actions/runs/37764486057) established a slightly improved floor-valid physical frontier `w6-f9490`: DD **35.227092840837%**, capital **USD 670,925.72076899**, total gross loss **USD 959,321.26449968**, ATTACK gross loss **USD 957,755.19206415**. This is **local** STRICT versus `m1-0700`, **not global** STRICT versus `f-m2850-h0060`.
- Ultra Fast finer W6 near-cliff sweep: `.github/workflows/cibo-trader-lab-carrier35227-w6-fine-boundary-ridge.yml`, launched as run [37765229488](https://github.com/mezas3238-hue/qore-core/actions/runs/37765229488). Its status/outcome must be read from the run; this research note makes no unverified claim of improvement.

## 2. Comparator distinction is non-negotiable

| Metric | Global STRICT `f-m2850-h0060` | Physical `m1-0700` | Local W6 `w6-f9490` |
|---|---:|---:|---:|
| Capital final USD | 670,974.10018485 | 670,926.00746256 | 670,925.72076899 |
| Max DD % | 36.40871216 | 35.24018943 | **35.22709284** |
| Gross loss total USD | 957,685.06716806 | 959,362.05715998 | 959,321.26449968 |
| Gross loss ATTACK USD | 956,129.11271151 | 957,795.98472445 | 957,755.19206415 |

Against global STRICT, `m1-0700` raises total gross losses **USD 1,676.98999193** and ATTACK gross losses **USD 1,666.87201294**. `w6-f9490` reduces the rebound to approximately USD 1,636.20 total and USD 1,626.08 ATTACK but still does **not** satisfy global STRICT. A physical DD improvement is not a global promotion.

## 3. Max-DD episode forensic evidence (the 35.24019% frontier)

- Official peak: **2020-04-03 03:05 UTC**.
- Official trough: **2020-05-13 06:15 UTC**.
- Official peak-to-trough net by mode: ATTACK **-USD 253.899416392496**; MEDIUM **+USD 5.412013474518**.
- **118** terminal trade receipts have their final settlement inside that window.
- Across the wider replay there are **855 ATTACK trades**; in this max-DD episode, **22 ATTACK losing terminal receipts**.
- The two categories differ: the authoritative episode simulator may include *intermediate lifecycle partial settlements* absent from reconstructed final-receipt cash-flow timing. Do not claim the final-receipt net is the exact peak-to-trough ledger.
- Official GL difference between the two carriers reconciled against the **3,368 per-trade terminal receipts** to decimal residual approximately zero (total `1.51E-22`, ATTACK `0E-22`). This confirms the terminal GL delta explains the officially reported *gross-loss gap*, without claiming that terminal receipts alone reconstruct intratrade DD chronology.

## 4. The GL-rebound concentration that must be explained before changing controls

The largest individual GL worsening between the two configs is **USD 1,456.036**, corresponding to a losing ATTACK trade whose multiplier changes from **308** (global) to **856** (frontier); final gross loss changes from **USD 818.356** to **USD 2,274.392**. Next GL increases observed in the matched trade receipts are approximately **USD 418.86**, **USD 368.73**, **USD 283.56**, and **USD 280.71**.

The first trade by itself accounts for most of the *net* GL rebound; there are also offsetting savings elsewhere. This is a causal **diagnostic of policy-state/multiplier-path differences**, not evidence that all 856x exposures should be capped, or that the same trade can be safely suppressed. Avoid identity hardcoding, future outcome dependence and global multiplier cuts.

## 5. Frozen pre-entry context cohort results — hypothesis killer

The context join retrospectively screened **621** one-, two- and three-predicate pre-entry combinations among eligible market context attributes. A leading example of apparent selectivity matches **two** peak-to-trough losses totaling about **USD 112.43** but also **one historical winner worth USD 72,500**. The two episode losses in that example are from just one Trader (reported solely for diagnostic cohort breadth, *never* as an allowed runtime predicate).

Consequently:
- A context signature that catches historical losers **must not be promoted** if it also targets valuable winners without a documented safe lifecycle path.
- Select for trade-preserving, context-only management; compute winner harm, full GL, full capital, DD migration and long-horizon compound effects before promotion.
- Require M5 closed-bar chronology and negative matched controls. A context match alone is NOT evidence that a tighter stop was reachable before a favorable move or that saving one losing trade helps the final account.
- Report how many *independent traders, years, temporal folds and market regimes* support each candidate. Retrospective "zero winners" after screening many signatures is not independent evidence.

## 6. W6 fine-boundary replay scope and safeguards

New run `37765229488` varies only the existing W6 taper fraction, holding other control flags unchanged. Tests 16 values in **0.9480–0.9500** including a `0.9490` comparator. Ranks vs the already observed `35.22709284%` local result and separately emits a **global STRICT** flag per case.

Prior W6 experiment already shows a sharp cliff: `0.9490` retained approximately USD 670.9k, while `0.9475` fell to approximately USD 526.9k, below the frozen floor. Any new reduction in DD gained by collapsing capital is invalid.

## 7. Engineering conclusions / next controls

1. Preserve both comparator definitions (global STRICT, lowest physical DD), plus local W6 status.
2. Recompute multi-bottleneck atlas after every physical DD improvement, because max DD migrates between ATTACK April–May 2020 and MEDIUM July–August 2019.
3. Diagnose W6 compounding discontinuities and ATTACK GL rebound separately; broad leverage changes threaten the true ceiling.
4. Before proposing a context stop, **veto high-winner-exposure signatures**, verify matching winners/losers, closed-bar M5 chronology, and record exact delta for all 3,368 trades.
5. Prioritize loss-negative, winner-safe context-only lifecycle interventions that bridge the ~USD 1.6k strict GL gap without losing DD compression.
6. Run independent temporal ablations, fresh sealed OOS and all original scientific certification gates only after reaching DD <=25%. No current research run is certification evidence.

## 8. Promotion checklist

Promote **only** if terminal capital >= USD 582,440.0252953678696769360345, all 3,368 entries conserved, no defer/reject/breach, deterministic provenance and no future leakage. Classify separately: (a) DD physical frontier, (b) local Pareto, (c) global STRICT Pareto requiring total and ATTACK GL non-worsening versus `f-m2850-h0060`. Any parameter crossing the capital cliff is **REJECTED**.

The ideal DD remains <=20%, maximum tolerable <=25%. Above 25% remains **NOT CERTIFIED**.
