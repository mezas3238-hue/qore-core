# VT08 Cognitive Expansion — M3 All Valid Owner Anchors Frontier V1

Status: **PRE-ECONOMIC CONSUMED-DEVELOPMENT FREEZE**

Purpose: test whether the current one-selected-candidate-per-market-per-NY-date
containment is suppressing valid density.

The primary VT08 source and Owner scope authorize independent Forex H4 opens at
01:00, 05:00 and 09:00 New York. The source does not impose a one-trade-per-day
rule. The current high-density M3 line discards *all* candidates on a date when
more than one owner anchor is valid.

This experiment changes only that cardinality containment:

- market universe remains EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD;
- profile remains M3_FRACTAL;
- daily bias remains unchanged;
- completed C2 reversal remains unchanged;
- latest causally confirmed Protected Swing remains unchanged;
- entry remains the new-H4 open;
- initial stop remains the selected Protected Swing;
- target remains fixed 2R;
- lifecycle remains the next H4 cycle;
- 01/05/09 New York anchors remain the only anchors;
- every source-valid owner anchor is retained, including two or more on one NY
  date;
- no PnL, market rank, anchor rank, side rank or future bar is used to admit a
  trade.

The experiment is evaluated first on already-consumed 1095D evidence. It does
not open the sealed 7Y archive and grants no runtime authority.

research_only=true
consumed_development=true
daily_cardinality_suppression_removed=true
fresh_validation=false
live_authorized=false
