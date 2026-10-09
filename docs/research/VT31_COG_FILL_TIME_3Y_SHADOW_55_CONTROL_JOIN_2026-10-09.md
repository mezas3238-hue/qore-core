# VT31 COG — 3Y Prospective Fill Revalidation / Frozen 55-Control Join (2026-10-09)

**STATUS: CAUSAL DEVELOPMENT RESEARCH — NO TRADE POLICY PROMOTION.**
Fresh Holdout sealed. NY and London NOT CERTIFIED. LIVE/FUNDED operation not authorized.

## Canonical identity

- COG branch: `agent/vt31-architect-cognition-sensors-20261009`.
- Owner-consumed 3Y NAS100 evidence `VT31_NAS100_OWNER_3Y_BASE_001`; window 2023-10-01 (inclusive) to 2026-10-01 (exclusive).
- Evidence artifact `11459859004`, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` (reused unchanged).
- Original OPS-frozen 55-admitted replay artifact `11459439466`.
- COG prospective fill shadow: [RUN 37993553650](https://github.com/mezas3238-hue/qore-core/actions/runs/37993553650), SUCCESS; measured code `d9fa6ecc0507b5e090d286b8c4c5630a4fdac209`; artifact `11645867877`.
- Frozen control arithmetic + shadow-55 join: [RUN 37994052776](https://github.com/mezas3238-hue/qore-core/actions/runs/37994052776), SUCCESS; measured code `14d77462d59a4afec06fe6303977db40f9ccc399`; artifact `11645828567`.
- Frozen control has **exact matching** PF, mean R, maximum drawdown, total R, win/loss counts in a completely separate deterministic chronological `Decimal` recomputation. The join **fails closed** if any metric drifts.

## 1. What was actually implemented

### Canonical prospective fill at M1-open T

`src/qore/infrastructure/traders/vt31_nas100_fill_time_causal_sensor.py` builds a fresh situation from **only closed NAS100 M1 bars with close <= prospective pending bar OPEN T**. It preserves the original source selection and structural target. It causally updates M15/H1 when available, session-reference reclaim, structure sequence, multi-sided sweep, entry-evidence age/freshness, current range, path efficiency/overlap, and structure/liquidity event count. It explicitly carries frozen prior-day/H4/structural source where no new observable source is available.

`revalidate_prospective_fill()` calls **the existing canonical `reason()`**, never another policy engine. It runs variants with or without the existing COMP008 admission contradiction audit. Mandatory entry intelligence blockers are distinguished from later post-entry calibration blockers. `current_open_r` is unavailable before entry and deliberately rejected. It has **no fill cancel/execution/sizing authority**.

Important source limitation: the legacy backtest `_fill_index` detects whether the future fill candle eventually touched the entry using that candle's high/low. Our shadow may use that retrospective index to select the *labelled* prospective opportunity T for scientific pairing. It **must not** and **does not** pass candle high/low/close to cognition at T. This alone does not make executable MT5 fill-time behavior proven: an actual pending order would need a pre-open or tick-before-fill action route in OPS implementation, followed by a full changed-trade replay with possible later fills.

Unit proof: adding/mutating a future/fill candle leaves the `PostEntryCausalObservation` identical; clock mismatch, unknown session, impossible pre-entry M1 and post-fill R are fail-closed. No London assumptions are introduced by this **NY-only** adapter.

## 2. Truthful 3Y funnel: unchanged structural control

| Measure | Count |
|---|---:|
| Source executable setups | **124** |
| No-fill | 29 |
| Prospective fill opportunities | **95** |
| Censored fill-bar ambiguity | 16 |
| Structural terminal paths | **79** |
| Admitted in frozen COMP009 55-trade control | **55** |
| Terminal structural zero post-fill M1 | 11 |
| Of those zero post-fill M1, admitted in 55 control | **6** |

No entry, fill, stop, target, execution, or terminal economics was modified to obtain these measurements.

### All 95 retrospective prospective fill opportunities

| Outcome from canonical NY shadow | Count |
|---|---:|
| Fresh full canonical pre-fill cognition calls | **95** |
| `EXECUTE` → would accept | **62** |
| `WAIT` → would reject at T | 18 |
| `ABSTAIN` → would reject at T | 15 |
| Total proposed reject at T | **33** |
| Additional entry-mandatory unavailable blockers | 1 (volatility) |
| COMP008-additional variant accept | 43 |
| COMP008-additional variant reject | 52 |
| Diff between two variants across the 95 | 19 |

On the **79 structural terminal paths**, basic fill-time shadow rejects **23 nonwinners and 3 winners**, retains **44 nonwinners and 9 winners**. These are *not* the finalized admission populations and cannot be described as the trading results of the proposed variant.

Of the 11 structural zero-call paths, **4** would have been rejected at prospective fill open T by base reasoning. These counts cannot be interpreted as successful prevented losses without an actually rerouted replay; no terminal result was used to make the decision.

## 3. Exact match against owner frozen admitted 55-trade control

The join uses signal timestamp identity and immutable artifact digests. All 55 admitted trades map one-to-one to 55 of the 95 prospective fill opportunity records. Frozen control arithmetic reproduces the reported Core 3Y numbers exactly:

| Metric (0.05R/trade friction) | Original frozen 55 CONTROL | **Naive conditional deletion of basic shadow rejects** |
|---|---:|---:|
| Trades | **55** | **35** |
| Winning trades | 11 | 9 |
| Nonwinning trades | 44 | 26 |
| PF | **1.6326693583** | **1.9671042231** |
| Stressed mean R | **+0.4635572948R** | **+0.6499851722R** |
| Total stressed R | **+25.4956512133R** | **+22.7494810286R** |
| Chronological observed DD | **21.3585957183R** | **12.4218745037R** |
| Consecutive stressed losses | **23** | **13** |

**What the second column is:** a *mathematical filter on already realized outcomes*, not a new replay. It naively assumes that every would-be-rejected trade vanishes and the remainder stay identical in timing and R. It does not implement order cancellation, re-entry, alternative future fills, changed overlapping exposure, intrabar spread/commissions, position-route actuation or actual changed execution. Its PF/DD are **non-certifying diagnostics**, not a proven trading improvement. As a diagnostic the deletion would also reduce total stressed R by **2.7461701848R**. Critical edge ceiling could degrade.

On these admitted 55, base prospective fill decision would **retain 35 / reject 20**; **18 of the rejected trades are losses/nonwinners, 2 are winners**. Six of the admitted trades had no postfill causal M1; base fill revalidation would reject **3 of those 6**.

The stricter COMP008-entry-revalidation view is **identical on the admitted 55**: 35 would remain, 20 rejected (18 nonwinners/2 winners); all 19 cross-variant differences from the overall 95 happen *outside the frozen admitted 55*. No second improvement has been inferred.

## 4. Hard certification conclusion

- At no point did a **real modified economic replay** show DD <=6R, Sharpe >=1.50, density >=400 trades per three years, stable half-year results, genuine WIN/LOSS preservation, or full actual routing. The naive deletion's DD **12.42R** itself remains over the **6R** gate. Its **35** retained trades are drastically below Core density.
- Even under the naive upper-bound calculation, net cumulative R is lower than control; increased PF does not prove the true edge remains.
- **Do not promote** automatic fill rejection from these exploratory results. No live authority.
- The old frozen source derives from VT31 R2.2 with mandatory 09-10 New York reference raid and Breaker/OB evidence. OPS is independently auditing **ICT 2023 original Silver Bullet FVG formation / session fidelity**. This artifact is **not** proof that the source replicates ICT verbatim. Any source correction must get its own fresh shadow baseline on the same consumed development population, without retrofitting results from obsolete source assumptions.
- London requires a separate clock/causal observation builder from the OPS-authenticated ICT 03:00-04:00 NY lesson; this NY 10:00-11:00 research path must **never** be reused as a silent London authority.

## 5. Required next coordinated experiment

OPS owner to own a distinct **actual changed-execution** control-vs-prospective-fill-revalidation replay, with unchanged evidence SHA, same original certified-source methodology, proper order lifecycle including pending order cancellation/re-offer and intrabar timing. No change to baseline/control branch should be hidden. Return:
- CONTROL exact source SHA, selected/admitted/traded/filled identities, rejected 2 winners' original R vs prevented 18 nonwinners;
- cash-clock prospective pending fill T as-of proofs with all required blockers, plus route -> execution acknowledgement;
- 6 admitted zero-call rows and which three candidate would intercept; censor unresolvable fill-bar paths;
- actual changed trade sample, PF, expectancy, continuous DD, Sharpe, Sortino, half-year robustness, stress/Monte Carlo and full Core gating (NY and London independently);
- freeze only after all Core gates pass and original ICT-source fidelity is independently verified.

New working files in COG branch:
- `src/qore/infrastructure/traders/vt31_nas100_fill_time_causal_sensor.py`
- `src/qore/infrastructure/traders/vt31_nas100_post_entry_cognitive_runtime.py` (optional fresh evidence age/multisweep fields)
- `scripts/vt31_nas100_cognitive_3y_fill_shadow_fast_v1.py`
- `scripts/vt31_nas100_cognitive_fill_shadow_control_join_v1.py`
- `.github/workflows/vt31-cognitive-fill-shadow-fast-v1.yml`
- `.github/workflows/vt31-cognitive-fill-shadow-control-join-fast-v1.yml`
- `tests/infrastructure/test_vt31_nas100_fill_time_causal_sensor.py`
- `tests/infrastructure/test_vt31_nas100_cognitive_fill_shadow_control_join.py`

**Governance:** Fresh Holdout SEALED, no sizing/leverage/capital, no signal preselection by realized trade outcome, NY/London independently uncertified, no production/funded authority.
