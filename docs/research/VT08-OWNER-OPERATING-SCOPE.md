# VT-08 V2 — Human Owner operating scope

Checkpoint: 2026-09-11

## Authority

This file records an explicit Human Owner operating constraint for VT-08 V2.
It is an operating-policy overlay on the source methodology, not a claim that the
primary teaching source contains only these H4 openings.

If source material shows additional repeating H4 openings, those source-cycle
openings remain useful for understanding the lesson but are **not authorized QORE
trading or Trader Lab candidate windows**.

## Authorized asset families and New York H4 openings

QORE may evaluate VT-08 V2 only in the following operating windows, interpreted
with the IANA timezone `America/New_York` so daylight-saving transitions are handled
by New York local time rather than by a fixed UTC offset.

### Forex

Authorized H4 opening hours:

- `01:00` New York
- `05:00` New York
- `09:00` New York

Authorized Core Forex research markets:

- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCAD
- GBPJPY
- AUDJPY

### Futures

Authorized H4 opening hours:

- `02:00` New York
- `06:00` New York
- `10:00` New York

Authorized Core futures research markets:

- NAS100
- SP500
- US30

## Explicit exclusions

- `13:00 / 17:00 / 21:00` Forex source-cycle openings are outside QORE's VT-08 operating scope.
- `14:00 / 18:00 / 22:00` futures source-cycle openings are outside QORE's VT-08 operating scope.
- XAUUSD is outside this VT-08 campaign because the Human Owner restricted the campaign to the listed Forex and futures families.
- No research result, optimization, candidate frequency, backtest result, or later source re-read may silently expand these windows.

## Governance consequence

The timing conclusion in `VT08-CRT-H4-AMD-V2-FIDELITY-REAUDIT-002.md` that treated
three-window scanning as incomplete is superseded **for QORE operating scope** by
this explicit Human Owner instruction.

The full source cycle may still be retained as source knowledge. The software must
nevertheless gate candidate generation to exactly:

- Forex: `(1, 5, 9)` New York;
- Futures: `(2, 6, 10)` New York.

This correction does **not** revive the old economic claims or automatically validate
the prior 16,351 candidate total. Subsequent POI, causal-context, wick-classification,
entry, target, and lifecycle findings still apply. A fresh owner-scoped audit is
required on the current methodology fingerprint.

## Campaign launch record

On 2026-09-11 the Human Owner ordered a fresh VT-08 V2 historical campaign under
this exact operating scope. The campaign must use the current methodology
fingerprint, at least 730 days of cTrader DEMO read-only evidence, only the ten
authorized markets above, and only the `01/05/09` Forex and `02/06/10` Futures
New York H4 openings. This record grants no economic, DEMO_ELIGIBLE, execution,
LIVE, Production, or real-capital authority.
