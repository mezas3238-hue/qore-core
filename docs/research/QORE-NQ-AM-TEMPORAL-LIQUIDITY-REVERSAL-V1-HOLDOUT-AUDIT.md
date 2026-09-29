# QORE NQ AM TEMPORAL LIQUIDITY REVERSAL V1 — 1Y EVIDENCE SELECTION NOTE

Tracker: #653  
Status: CONSUMED 1Y METHODOLOGY REPLAY AUTHORIZED

## Owner adjudication

For the immediate objective — determine whether the reviewed methodology works —
already-consumed evidence is explicitly acceptable.

Consumption history is therefore NOT an exclusion criterion for the 1Y
methodology replay.

It remains relevant only to the later question of independent fresh
certification.

## Known NAS100 consumed evidence

Repository evidence includes:
- CIBO Market Atlas NAS100/USTEC research spanning the 2016-09-17 to
  2026-09-17 primary corpus;
- VT31 M1 Silver Bullet / New York reversal evidence across earlier consumed
  windows;
- VT08 index evidence over later consumed windows.

These data are valid for methodology falsification/feasibility because the new
candidate will be scored mechanically on them without claiming that the market
interval itself was unseen by QORE.

## Preferred 1Y source family

Use retained/recoverable VT31 NAS100 M1 evidence where possible, because:
- the candidate requires M1 timing;
- evidence provenance and cTrader identity already exist;
- it avoids degrading IFVG/reclaim logic to M5;
- it provides a direct one-year chronological replay.

A practical first target is a one-year slice inside a known VT31 M1 acquisition
window. Exact boundaries are frozen only after artifact recovery confirms
coverage. Window selection is based on data availability, never on this
candidate's PnL.

## Result semantics

The run will be labeled:
`CONSUMED_1Y_METHODOLOGY_REPLAY`

A positive result means the mechanics deserve further validation.
A negative result falsifies or weakens the current V1 mechanics.
Neither outcome is relabeled fresh OOS.
