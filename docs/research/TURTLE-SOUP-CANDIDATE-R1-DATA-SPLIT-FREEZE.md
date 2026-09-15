# Turtle Soup Candidate R1 — Data Split & Development Replay Freeze

Status: FROZEN BEFORE ANY ECONOMIC REPLAY RESULT.

Research identity: `turtle-soup-candidate-r1`
Canonical trader code: `CODE_UNASSIGNED`

## Acquisition universe

Initial development acquisition is predeclared for these seven prop-relevant Forex instruments:

- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCAD
- GBPJPY
- AUDJPY

The R1 development candidate is evaluated on the complete seven-market universe. No market may be removed or added in R1 because of its development P&L.

The acquisition source is read-only cTrader historical market data. Acquisition is evidence collection only; it is not account trading and grants no execution authority.

## Time span

Request up to 1095 calendar days of provider-native D1 and native M15 history ending at collection time.

## Development / fresh-OOS boundary

`FRESH_OOS_EMBARGO_START = 2026-03-01T00:00:00Z`

Development characterization may consume only bars whose `opened_at` is strictly earlier than the embargo start.

Bars on or after the embargo start are **acquired but embargoed**. Merely acquiring and hashing them does not authorize reading their price path for candidate selection.

The loader must remove embargoed D1 and M15 bars before setup detection, execution-path construction, management replay, P&L calculation, metrics, policy selection or market/variant decisions. A setup whose required execution or management evidence crosses the embargo boundary is censored rather than completed with post-embargo data.

No code that computes setups, trades, P&L, metrics, rankings, policy selection or market selection during development may receive embargoed bars.

## Provider-native D1 session boundary

The provider-native D1 opening timestamps are the authoritative boundaries for the daily source stream. Around session/DST transitions the interval between consecutive native D1 opens can differ from exactly 24 hours.

For causal M15 execution slicing, source day `i` is therefore:

`D1[i].opened_at <= M15.opened_at < D1[i+1].opened_at`

The nominal `opened_at + 24h` endpoint carried by the raw D1 evidence must not truncate or extend a native provider session for execution-path purposes.

Consequences:

1. a D1 bar without a subsequent native D1 open cannot initiate a new replay setup;
2. Classic uses the M15 slice belonging to its current native D1 source day;
3. Plus One uses the M15 slice belonging to the next native D1 source day;
4. management bar 1 is the first complete native D1 bar after the fill/source-entry day, preserving the already-frozen management contract;
5. every required M15 execution slice must be chronological and exactly contiguous at 15-minute cadence across the provider-native D1 interval;
6. a missing, duplicated, overlapping or noncontiguous required M15 slice is explicit invalid/censored evidence; it is never interpolated or patched.

This is an execution-evidence interpretation of the provider-native D1 stream, not a new Turtle Soup trading rule.

## Tick/increment operationalization

The retained raw evidence includes `symbol_digits` but does not claim a separate exchange tick-size field. R1 freezes the provider price increment used by the detector as:

`tick_size = Decimal(10) ** (-symbol_digits)`

This is an explicit QORE/provider-precision execution input, not a claim that Connors/Raschke defined modern spot-FX tick metadata.

Classic keeps the source-authorized entry-offset choice already frozen in code before results:

`classic_entry_offset_ticks = 5`

The 5–10 source band will not be optimized after development results are observed.

## Development execution and transaction-cost model freeze

Execution model identity:

`TURTLE_SOUP_R1_D1_NATIVE_M15_CAUSAL_V1`

Execution semantics are the source detector already implemented in `turtle_soup_candidate_r1.py`, including M15 causal ordering, fail-closed same-bar ambiguity and QORE conservative observed-open gap-through fills.

Development transaction-cost model identity:

`TURTLE_SOUP_R1_ALL_IN_ROUND_TRIP_BPS_V1`

The cost model is deliberately broker-agnostic and is used for development robustness only. It does not claim to reproduce FTMO or FundedNext live execution. For each closed trade:

`cost_R = (entry_price * round_trip_bps / 10000) / initial_risk_price`

`net_R = gross_R - cost_R`

The all-in round-trip charge is applied once to the full starting notional even when an experimental Plus-One policy exits partially. This avoids giving partial-exit policies a favorable cost exemption.

Predeclared cost schedule:

- 0.0 bp — gross diagnostic;
- 0.5 bp — low-cost sensitivity;
- **1.0 bp — primary development selection cost**;
- 2.0 bp — adverse-cost stress.

No cost point may be chosen after results to make a policy pass. Prop-firm-specific spread, commission and slippage assumptions must be verified separately before final FTMO/FundedNext approval.

## Development robustness gates and deterministic policy selection

Classic and Plus One are judged separately. A frozen management policy can advance from development only when all of these conditions hold on the complete seven-market R1 universe:

1. at least 50 closed, non-censored trades;
2. positive total and positive mean net R at the primary 1.0 bp cost;
3. primary-cost profit factor strictly greater than 1.00;
4. positive total net R at the 2.0 bp adverse-cost stress;
5. primary-cost total-net-R / max-drawdown-R ratio at least 1.00 when drawdown is nonzero;
6. no single market, calendar year or side contributes more than 65% of total positive primary-cost R contribution;
7. removing any one market must not make the remaining six-market primary-cost total R negative.

Ambiguous source/execution cases and insufficient management evidence are reported separately and never converted to favorable trades.

If multiple policies for the same variant pass every gate, selection is deterministic and lexicographic:

1. highest 2.0 bp stress total net R;
2. lower primary-cost max drawdown R;
3. higher primary-cost profit factor;
4. lexicographically smaller policy ID as final deterministic tie-break.

If no policy for a variant passes, that variant is rejected for R1. R1 is not retuned against the fresh holdout. Any subsequent research iteration must receive a new research/config identity and may use development evidence only until it is independently frozen.

## Required development report

For every variant/policy report at minimum:

- evaluated signal opportunities and decision/reason census;
- setup/fill count;
- ambiguous count;
- censored management count;
- closed trade count;
- gross and each predeclared net-cost total/mean/median R;
- win rate;
- profit factor;
- max drawdown R;
- worst trade;
- longest losing sequence;
- holding bars;
- result concentration by market/year/side;
- leave-one-market-out primary-cost total R;
- exact source-config fingerprint;
- management-policy fingerprint;
- raw D1/M15 evidence digests and collector SHAs;
- exact replay software SHA;
- execution-model and transaction-cost-model identities.

## Holdout release condition

The embargo may be released exactly once only after:

1. development replay is complete;
2. one Classic policy/config and one Plus-One policy/config are either frozen or explicitly rejected;
3. the seven-market universe is frozen without holdout outcome knowledge;
4. source configuration is frozen;
5. execution model is frozen;
6. transaction-cost model is frozen;
7. candidate fingerprints and the development adjudication are recorded in GitHub.

After release there is no parameter retuning, management-grid change, entry-offset change, market deletion/addition based on holdout results, or second use of the same OOS as an independent holdout.

## Data semantics

The initial campaign uses provider-native D1 bars rather than D1 fabricated from H4 aggregation.

For Forex this is a source-authorized market transfer. The historical futures-specific `night data ignored / day-session only` source rule is not silently projected onto 24-hour spot-FX bar construction. Any later futures campaign requires an explicit exchange day-session calendar and separate dataset fingerprint.

## Governance

This split, causal session interpretation, cost schedule and development selection rule were frozen before any Turtle Soup R1 economic replay result was inspected.

No DEMO/LIVE/Production/real-capital authority is granted.
