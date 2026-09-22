# VT-08 Cardinality Forensics

Baseline: PR #518, SHA `a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0`, GitHub Actions run `34661791159`.

## Verdict

The historical `mechanical_candidate_count = 16,179` is **not** a trade counter.

In the baseline backtester, each authorized New York H4 anchor is inspected. For each eligible anchor the code independently attempts:

- a long Candle-2 mechanical candidate;
- a short Candle-2 mechanical candidate;
- a Candle-3 continuation candidate when prior H4 context permits it.

Each non-`None` object is appended to `candidates`; the reported `mechanical_candidate_count` is exactly `len(candidates)`.

The ten-market run contained:

- 16,093 eligible H4 anchors;
- 12,152 C2 mechanical candidates;
- 4,027 C3 mechanical candidates;
- 16,179 total mechanical candidates;
- 16,177 requiring unresolved source judgment;
- 2 automatic setups;
- 2 fills;
- 0 wins;
- 2 losses;
- 0 censored outcomes.

The aggregate workflow sums candidates, setups and fills in separate fields. No evidence was found that the ten-market aggregate converted 16,179 candidates into trades.

However, the baseline **does not implement a daily cardinality authority layer**. There is no `MarketDayId`, `DayState`, daily selection, consumed daily budget, or invariant that caps selected setups/fills at one per market × New-York local date. The observed run happened to have zero daily fill violations only because it produced two sparse setups in different markets/dates. The architecture still permits a future day with multiple automatic candidates to be counted as multiple setups/fills.

## Why 16,179 is mathematically possible

Across all ten markets the candidate distribution by eligible H4 anchor was:

| candidates emitted by one eligible anchor | anchor count |
| ---: | ---: |
| 0 | 4,006 |
| 1 | 8,393 |
| 2 | 3,296 |
| 3 | 398 |

Therefore a three-window market-day can legitimately contain several **diagnostic candidates** before daily selection. Observed maximum was seven candidates on a single market-day.

There were 1,068 anchors with more than one C2 candidate and 1,101 `(signal_at, side)` keys represented by more than one C2/C3 scenario. These are not proven economic duplicates, but they demonstrate why scenario/candidate accounting cannot be used as trade accounting without a separate selection and deduplication layer.

## Dataset denominator

The collector requested `760` lookback days and required at least `730` days of coverage. That is a data-acquisition horizon, not a count of eligible trading days.

The resulting New-York-local calendar span was 761 inclusive dates. Under the **baseline forensic definition** "eligible market-day = at least one authorized anchor has exact current H4 plus prior-H4 M15 evidence":

- VT08_FOREX: 3,780 eligible market-days across seven markets (540 each).
- VT08_FUTURES: 1,614 eligible market-days across three markets (538 each).
- Combined: 5,394 eligible market-days.

If the final dataset contract instead requires **all three** authorized windows and their H4 references to be complete, the stricter count is:

- VT08_FOREX: 3,773 complete market-days.
- VT08_FUTURES: 1,548 complete market-days.
- Combined: 5,321 complete market-days.

Therefore neither 7,300 nor 730 is an observed denominator in this run. The daily ceiling must be derived from the final frozen eligibility contract.

## Per-market reconciliation

| market | family | observed dates | eligible days (any anchor) | all-3 complete days | eligible anchors | candidates | setups | fills | max candidates/day |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EURUSD | forex | 653 | 540 | 539 | 1618 | 1616 | 0 | 0 | 7 |
| GBPUSD | forex | 653 | 540 | 539 | 1618 | 1614 | 0 | 0 | 7 |
| USDJPY | forex | 653 | 540 | 539 | 1618 | 1583 | 1 | 1 | 7 |
| AUDUSD | forex | 653 | 540 | 539 | 1618 | 1576 | 0 | 0 | 7 |
| USDCAD | forex | 653 | 540 | 539 | 1618 | 1672 | 0 | 0 | 6 |
| GBPJPY | forex | 653 | 540 | 539 | 1618 | 1571 | 0 | 0 | 7 |
| AUDJPY | forex | 653 | 540 | 539 | 1618 | 1589 | 1 | 1 | 7 |
| NAS100 | futures | 652 | 538 | 516 | 1589 | 1631 | 0 | 0 | 7 |
| SP500 | futures | 652 | 538 | 516 | 1589 | 1639 | 0 | 0 | 7 |
| US30 | futures | 652 | 538 | 516 | 1589 | 1688 | 0 | 0 | 7 |

The two automatic fills occurred at:

- `USDJPY`, NY date 2025-10-27, 09:00 anchor, C3, stop.
- `AUDJPY`, NY date 2026-04-17, 05:00 anchor, C3, stop.

No market-day in this baseline had more than one automatic setup or fill, but that is an observation, not an enforced invariant.

## Forensic answers to the 20 required questions

1. `16,179` is incremented indirectly by appending non-`None` C2/C3 candidate objects and then reporting `len(candidates)`.
2. One mechanical-candidate unit is a mechanically observed C2-long, C2-short, or C3 scenario candidate inside one authorized H4 anchor.
3. Yes. One H4 anchor can emit up to three candidates in the current code; 398 anchors emitted three in the real run.
4. Yes. Each market-day examines three authorized anchors and candidates appeared across multiple anchors.
5. The inspected aggregate keeps candidates, setups, and fills separate. No candidate→trade coercion was found in the #518 aggregate path.
6. The observed artifacts contain no >1-fill day, but the code has no daily cap, so such a path is mechanically possible if multiple automatic candidates occur.
7. The runner iterates `local_day → anchor hour`, but execution state is not held at day scope. Each anchor is replayed independently.
8. No daily consumed-trade state exists in #518.
9. Yes at candidate-accounting level: 1,101 same `(signal_at, side)` keys appeared across more than one C2/C3 scenario. Economic equivalence still requires source adjudication.
10. The baseline stores one protected-swing confirmation per candidate object; repeated confirmations can still produce separate candidates across scenario/anchor evaluations. No day-level dedupe exists.
11. Authorized anchor hours themselves are distinct; exact M15 evidence rejects overlap/duplicates, but candidate semantics can overlap across C2/C3 and adjacent context.
12. No duplicate candidate identities were found. NY conversion produced stable dates across the evidence, but no dedicated DST cardinality ledger/test exists in #518.
13. Yes. Collection requested 760 days, not exactly 730, and the NY inclusive calendar span is 761 dates.
14. In #518, `730` is `required_coverage_days`; `760` is collection lookback. Neither means eligible market-days.
15. Weekend/holiday/gap dates are not represented as a canonical denominator in #518. The new ledger must expose them explicitly.
16. The inspected ten-market aggregate sums per-market candidate counts once; no artifact double-count was observed.
17. This run contains one frozen configuration per market. No configuration-level duplicate was observed here; the current schema lacks a universal candidate identity suitable for cross-replay dedupe.
18. Candidate ordering is deterministic, but #518 has no explicit candidate ID. The forensic ledger derives stable IDs from market+anchor+scenario+side+signal+geometry.
19. No. Candidate/setup payloads in #518 do not carry `market_day_id`.
20. No. One-trade-per-market-day is not mechanically enforceable/testable in #518 today; it must be introduced as a separate daily cardinality authority.

## Required architectural correction

The rebuild must split VT-08 into `VT08ForexTrader` and `VT08FuturesTrader`, sharing only source-proven methodology primitives. Daily authority must belong to `MarketDayId(trader_family, canonical_market, America/New_York local_date)`, not to an anchor or candidate.

For every market-day the executable layer must enforce:

`selected_setup_count <= 1`

`pending_selected_order_count <= 1`

`filled_trade_count <= 1`

`terminal_trade_count <= 1`

and CI must fail on any violation.

The source-methodology decision for choosing among multiple fully valid windows remains separate. If the source does not specify it, chronological first-valid consumption must be labeled `OWNER_EXECUTION_POLICY`, never `TTRADES_SOURCE_RULE`.
