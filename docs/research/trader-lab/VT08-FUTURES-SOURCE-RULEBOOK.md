# VT-08-FUTURES Revision 3.2 Source Rulebook

Status: source-first reconstruction; economics blocked until full correctness gates pass.

## Market authority

`NAS100`, `SP500`, `US30` only. Forex symbols and XAUUSD are outside this Trader authority.

## Timing profiles

Two profiles exist and must never be conflated:

- `SOURCE_COMPLETE`: 02:00 / 06:00 / 10:00 / 14:00 America/New_York.
- `OWNER_OPERATIONAL_SUBSET`: 02:00 / 06:00 / 10:00 America/New_York.

The Owner subset is an operational policy, not the complete TTrades source timing profile.

## LTF profiles

`M15` is the standard H4 pairing. `M5_FRACTAL` and `M3_FRACTAL` are independent alternative profiles. A research run binds exactly one LTF profile and must not use another profile as retrospective confirmation.

## Shared R3.2 semantics

This Trader consumes only shared primitives from `vt08_source_kernel_r3_2`: OLHC/OHLC delivery semantics, qualitative C2/C3 evidence, CISD, protected swing, EQ, six entry-family identities, five stop-family identities, contextual target families, source-coherent bundles, causality and current-H4 lifecycle.

The Trader does not invent a numerical shallow/large threshold and does not assign a universal priority among entry families, protected swings or targets.

## Daily execution contract

For each `VT08-FUTURES + market + New-York local date`:

- candidates may exceed one;
- qualified setups may exceed one before daily selection if methodology permits;
- `selected_setup_count <= 1`;
- `pending_selected_order_count <= 1`;
- `filled_count <= 1`;
- `terminal_count <= 1`.

The max-one rule is Human Owner execution policy. A deterministic winner among multiple complete opportunities remains unresolved unless a separately versioned Owner policy is frozen.

## HTF lifecycle

Any selected trade is valid no later than the close of the current H4 candle. Continuing in a new H4 requires a fresh evaluation and fresh source evidence.

## Research-only ambiguity

SMT, failure swings, T-spot and expansion-met-with-expansion remain non-mandatory research concepts until their executable algorithms are source-resolved.

No Risk, broker, `DEMO_ELIGIBLE`, LIVE, Production or real-capital authority is granted.
