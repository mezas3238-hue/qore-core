# QORE NQ AM TEMPORAL LIQUIDITY REVERSAL V1 — PRE-HOLDOUT FREEZE CONTRACT

Identity: `QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V1`  
Tracker: #653  
Parent research foundation: #590 / PR #601  
Source video: `UVVmS0de0g0`  
Status: DEVELOPMENT ON CONSUMED EVIDENCE / FRESH 1Y HOLDOUT SEALED

## 1. Mission

Mechanize the NQ AM-session long reversal reviewed in the source video without
using the final low of day or any other post-outcome label. V1 is an independent
candidate and does not alter VT31.

The implementation uses QORE's cTrader DEMO `USTEC` feed as the provider
instrument for canonical `NAS100`. This is a CFD proxy and is **not** exchange
NQ futures. A positive result therefore validates only this exact evidence
identity until a separate futures replication exists.

## 2. Causal V1 chain

All timestamps are `America/New_York`, DST-aware.

1. Build completed RTH sessions from the exact `09:30` M1 open and the `16:14`
   M1 final RTH settlement bar.
2. Require previous completed RTH session to close in its upper half.
3. Require current `09:30` open below previous `16:14` settlement.
4. Define `gap = previous_settlement - current_09:30_open`.
5. Define lowest octant = `open + gap/8`.
6. Define lower quadrant = `open + gap/4`.
7. During `09:30 <= t < 09:35`, require:
   - no high reaches the lower quadrant;
   - no M1 close reaches the lowest octant.
8. Select the nearest still-untouched completed RTH low below the current
   `09:30` open from the prior five eligible RTH sessions. "Untouched" means no
   later provider M1 low at or below that reference from the minute after its
   `16:14` settlement through the current `09:30` open.
9. Define the frozen downside opening-gap extension as
   `extension_2 = current_09:30_open - 2 * gap`.
10. Require the selected sell-side reference to lie within one gap octant
    (`gap/8`) of `extension_2`.
11. FULL V1 rejects a day if that sell-side reference is swept before `10:50`.
12. Require first sell-side penetration during `10:50 <= t < 11:00`.
13. From first penetration through `11:00`, require every M1 close to remain
    above `max(reference_low, extension_2)`. Wicks may penetrate; body acceptance
    below the confluence invalidates FULL V1.
14. Search the preceding 60 minutes for a mechanically defined bearish M1 FVG:
    `third.high < first.low`.
15. After the sweep, that bearish FVG becomes an inversion candidate only after
    an M1 close above the FVG upper boundary.
16. Entry is causal at the close of the first M1 bar, no later than `11:10`,
    that overlaps the inverted FVG and closes at/above its midpoint.
17. One trade maximum per NY RTH day.
18. Structural stop = first-half macro sweep extreme minus one provider tick.
19. V1 economic target = the pre-known `09:30` RTH open.
20. Unresolved positions exit at the last admissible path by `12:00`.
21. Same-M1 stop/target ambiguity is resolved **stop first**.
22. Primary friction = `0.05R`; stress friction = `0.10R`.

The target policy is QORE's frozen V1 economic formalization for falsification;
it is not a claim that the source author universally exits every such setup at
the 09:30 open.

## 3. No-hindsight laws

At entry V1 must not know:
- final low/high of day;
- later target reach;
- later MAE/MFE;
- later macro behavior;
- final session close;
- any outcome label.

Appending bars after the frozen AM lifecycle must not change the entry or
already-resolved trade.

`LOW_OF_DAY` is evaluation language only and is never an input feature.

## 4. Development evidence

Development/debugging interval:

`2024-08-13 NY -> 2025-08-13 NY` (end exclusive)

This interval is already consumed by broader NAS100 research and is deliberately
used only for implementation/debugging/ablation. It cannot be fresh evidence for
this candidate.

Provider: cTrader DEMO  
Canonical market: `NAS100`  
Provider symbol: `USTEC`  
Required resolution: M1

## 5. Development go/no-go gate

Before risking the sealed holdout, exact FULL V1 must satisfy on consumed
development evidence:

- `trade_count >= 12`;
- `primary_total_r > 0`;
- `primary_pf > 1.0`;
- no data/provenance failure;
- all focused/static tests green.

This is a preregistered holdout-opening gate, not a tuning target. If FULL V1
fails it, the result is retained as `FALSIFIED_BEFORE_HOLDOUT`, the holdout
remains sealed, and any mechanic change requires a new candidate identity.

## 6. Frozen explanatory ablations

The following ablations run only on consumed development evidence:

- `FULL`
- `NO_MACRO`
- `NO_GAP_EXTENSION`
- `NO_IFVG`
- `NO_ACCEPTANCE_TEST`
- `NO_RTH_GAP_CONTEXT`

Ablations have **zero selection authority**. The only identity eligible for the
future fresh holdout is `FULL`. No ablation result may be used to mutate FULL
before opening the already-preregistered holdout unless a new candidate identity
is created and a different fresh holdout is sealed.

## 7. Fresh 1Y holdout

The candidate holdout is separately audited in
`QORE-NQ-AM-TLR-V1-HOLDOUT-AUDIT.md`.

It remains `SEALED` until:
- focused tests are green;
- Ruff and mypy are green;
- development replay completes on consumed evidence;
- exact FULL config fingerprint is emitted;
- provider M1 availability for the holdout boundaries is verified without
  exposing holdout economics;
- a final pre-open freeze commit exists.

The holdout is opened once. After opening it is permanently consumed.

## 8. Holdout measurements

The one-year run must report at minimum:
- evaluated and eligible sessions;
- opportunity/setup/trade counts;
- wins/losses/breakeven;
- gross/primary/stress R;
- PF and expectancy;
- max DD and losing streak;
- monthly/quarterly stability;
- MFE/MAE;
- exit-reason attribution;
- false-bottom count/rate;
- conservative collision count;
- deterministic bootstrap confidence interval;
- exact evidence identity/hash and git SHA.

## 9. Governance

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
