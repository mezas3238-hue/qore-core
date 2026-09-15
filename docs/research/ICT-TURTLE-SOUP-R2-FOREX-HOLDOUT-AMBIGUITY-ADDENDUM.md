# ICT Turtle Soup R2 Forex Holdout — Simultaneous-Pool Addendum

Status: PRE-RESULT / immutable after holdout access

This addendum clarifies the pre-result execution freeze without changing the economic hypothesis.

If one native M5 bar first-sweeps more than one currently eligible qualified liquidity pool, regardless of whether those pools are on the same side or on opposite sides, the bar is classified `AMBIGUOUS_MULTI_POOL_SWEEP` and produces no entry. Every pool crossed by that bar is considered consumed for later target/event eligibility.

Rationale: the source adjudication does not provide a deterministic priority among simultaneous pools, and M5 OHLC cannot recover intrabar ordering. QORE therefore fails closed rather than selecting the retrospectively favorable pool.

No P&L had been opened for ICT Turtle Soup R2 when this addendum was committed.
