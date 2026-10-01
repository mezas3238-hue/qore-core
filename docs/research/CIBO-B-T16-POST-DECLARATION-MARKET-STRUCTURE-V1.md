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


## Provider-native candidate economics

The same read-only lane now also records, point-in-time, for `USTEC`,
`US30` and `US500`:

- bid/ask and quoted spread in bps;
- min/max/step/lot volume terms;
- broker expected margin at minimum volume;
- native commission metadata.

These fields prove current provider contract/quote availability only. They do
not prove realized slippage, successful hedge execution, market impact or the
full hedge cost model. Those remain separate external evidence gates.

## Latest terminal evidence — 2026-10-01

Revalidated on Architect-B HEAD `aa412b3b7de0824c9b809edba7eeb617cf3571b5`.

Workflow `QORE CIBO T16 Post-Declaration Market Structure` run
`36817089026` completed **SUCCESS** and sealed artifact
`11141752922` (digest
`sha256:2c49af854547486de58c358289a7e2db5f8128be4421ad58eb04a0cd06ce90a8`).

Both preregistered pairs now have **48** non-overlapping M1 return observations,
exceeding the frozen minimum of **30**, with **4/4 folds** available.

- `NAS100/USTEC -> US30`: correlation
  `0.3954139569878453283170350549`, hedge beta
  `0.9870327967453971764500222111`, basis RMS
  `0.0001368025471723187710923904538`.
- `NAS100/USTEC -> US500`: correlation
  `0.8622051595292492167872639614`, hedge beta
  `2.124695637073769264771432974`, basis RMS
  `0.00007506302011012838714771786774`.

For both pairs:

- sample readiness = true;
- fold coverage = true;
- correlation stability = true;
- basis risk measured = true;
- provider contract + current quote coverage = true;
- realized hedge fills/slippage = **not observed**;
- full hedge cost model = **not ready**;
- fresh-OOS utility = **not proven**;
- T16 policy/runtime authority = false.

Therefore the structural population/correlation/basis blockers are closed. The
remaining T16 blockers are exactly:

1. `T16_HEDGE_COST_EVIDENCE_INCOMPLETE`;
2. `T16_PROVIDER_EXECUTION_SUPPORT_INCOMPLETE`;
3. `T16_NET_ECONOMIC_BENEFIT_NOT_PROVEN`;
4. `T16_FRESH_OOS_HEDGE_UTILITY_REQUIRED`.

The 2017H1 holdout was not read and no broker mutation was performed.
