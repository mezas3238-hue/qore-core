# QORE NATIVE — G0B P1 RUN EXECUTED — 12 ORIGINAL MARKETS, SOURCE CLOCK ONLY

**Date:** 2026-10-12 (GitHub UTC). **Outcome status:** `G0B_STRUCTURAL_OBSERVED_ONLY_P1_BROKER_CALENDAR_BLOCKED`, **not** an economic result.

## Frozen execution evidence

- **Draft PR:** https://github.com/mezas3238-hue/qore-core/pull/820
- **Research branch:** `research/qore-native-g0b-sessions-cost-gates-20261012`
- **Exactly executed head:** `b62053df37cd7e1301c9e8452fb57f6412d1e213`
- **GitHub Actions:** https://github.com/mezas3238-hue/qore-core/actions/runs/38201368296
- **CI:** 14/14 jobs **SUCCESS** = 1 offline contract/test + 12 original source symbol scans + 1 independent 12-symbol SHA aggregate. All matrix raw revalidation passed; no cTrader API, economic data, trading or production.
- **Final artifact:** https://github.com/mezas3238-hue/qore-core/actions/runs/38201368296/artifacts/11725486764, `qore-native-g0b-existing12-aggregate-b62053df37cd7e1301c9e8452fb57f6412d1e213`. Archive includes `qore-native-g0b-aggregate.json`, `code-head-sha.txt`, `OUTPUT_SHA256SUMS.txt`. All 12 individual witness artifacts are in the same workflow run.
- **Independent final job log:** `G0B_STRUCTURAL_OBSERVED_ONLY_P1_BROKER_CALENDAR_BLOCKED bars 8726985 markets 12`, with SHA witness checks for all symbol JSON files, fixed 12 symbol set, G0/source verification, no outcomes and G1 blocking.
- **Original upstream data:** [#816](https://github.com/mezas3238-hue/qore-core/pull/816), [source producer #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), 12×11 annual partitions native cTrader DEMO, raw SHA verified. Not equivalent to IC Markets broker account verification.

## Interpretation and unresolved ambiguity

The 8.726.985 M5 **timestamps** were recounted and profiled in New York wall clock with explicit UTC offset. Data discontinuities are labelled `UNKNOWN_CLOSURE_OR_FEED_GAP`. The output does **NOT** prove which gaps are expected closing periods, holidays, rollover, outages, broker pauses or DST-specific schedule changes. It does not build valid broker-native H4 or D1 candles, although UTC completeness descriptive counters are provided. **No returns, no volatility, no PnL, no signal selected.**

**Missing mandatory evidence:** exact broker/tier, historical session calendar & exceptions with effective timestamps, contract units and rollover; BID/ASK historical broker-native by slot, commission RT and financing, stop spread survivability, slippage/exits, high-impact news calendar known as-of and controls for positions open before releases. The fail-closed cost gate is `BLOCKED_MISSING_SOURCE_EVIDENCE`, even if self-asserted reference fields are supplied they stay `SOURCE_CLAIMS_NEED_INDEPENDENT_VERIFICATION`.

**G1 remains BLOCKED; 0/3 Native traders certified.** No holdout inspected, no OOS claim, no VPS/MT5/Shared/CIBO/QDLE/LIVE modifications, PR remains draft.

## Parallel 21 IC Markets DEMO capture

At the last verified check of https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541 there were **12/21 capture artifacts uploaded**: USDCHF, NZDUSD, GBPCAD, EURNZD, EURCHF, EURCAD, EURGBP, GBPCHF, EURJPY, EURAUD, GBPAUD, GBPNZD. AUDCAD in progress and other eight in queue. These are ARTIFACT PRESENCE ONLY: **NOT 12/21 individually SHA-validated 10Y sources**. The run continues independently; do not relaunch it or count 33 verified.

## Next scientific handoff to finish P1 and open P2

1. Capture official broker-verified historical sessions, zone, rollover and holiday exceptions; overlay as **separate** versioned as-of calendar and label expected closures vs missing feed. Prefer UNKNOWN to invented closures.
2. Obtain historical same-account bid/ask & complete roundtrip costs (spread + commission + slippage + swaps) with effective times and executable-side stop analysis. No zero friction substitution. Confirm as-of news archive, open-position pre-news rule and unplanned-shock governor.
3. **Only when quality, cost and sample/power gates permit**, preregister one H4/D1 normal-regime hypothesis with causal trigger, matched baseline, stop, full cost, dependence-effective N and true untouched OOS. No parameter grid or 12-way winner selection. Respect policy #814 not to execute at macro announcements.
4. Separately complete G0 for each new M5 capture once 11 annual RAW partitions per symbol + SHA + broker identity/coverage are verifiable; M1 missing 24 remains separate.

This report reflects completed GitHub execution, not automated acceptance of source provenance, session calendars or financial viability. GitHub Actions artifact retention may expire; preserve the run, code HEAD, hashes and ledgers.
