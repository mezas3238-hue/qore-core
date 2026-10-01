# CIBO B — T16 Post-Declaration Market Structure V1

This evidence lane consumes only cTrader DEMO M1 trendbars whose return windows
start after the frozen T16 declaration.

It may establish:

- post-declaration sample count;
- correlation sign/stability;
- hedge beta;
- basis residual.

It explicitly does **not** reconstruct historical bid/ask, spread, slippage,
commission or hedge execution cost. Those fields remain unknown until observed
evidence exists. Therefore structural return evidence cannot by itself make
T16 policy-ready.

Pairs are fixed before outcomes:

- NAS100 / USTEC -> US30;
- NAS100 / USTEC -> US500.

No 2017H1 holdout data, broker mutation, LIVE authority or real-capital
authority is used.
