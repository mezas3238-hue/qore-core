# VT08 Cognitive Expansion 5M — CIBO Stop Protection Transfer V1 Freeze

Status: **PRE-ECONOMIC FREEZE / CONSUMED DEVELOPMENT ONLY**

This freeze is committed before observing the five-market economic result of
the stop-protection transfer.

## Source technology

Reuse the pre-existing VT08 CIBO R3.16 stop-protection families already
source-controlled in:

`src/qore/infrastructure/trader_lab/vt08_index_c2_r1_cibo_stop_protection.py`

No new stop threshold is invented for the five-market expansion.

Frozen arms:

- `off`
- `soft`
  - +0.75R observed -> next-bar stop -0.50R
  - +1.25R observed -> next-bar stop 0.00R
  - +1.60R observed -> next-bar stop +0.50R
- `be050-lock050-at100`
  - +0.50R observed -> next-bar stop 0.00R
  - +1.00R observed -> next-bar stop +0.50R
- `aggressive`
  - +0.50R observed -> next-bar stop 0.00R
  - +1.00R observed -> next-bar stop +0.50R
  - +1.50R observed -> next-bar stop +1.00R

## Replay invariants

- exact VT08 5M trade identity is unchanged;
- entry is unchanged;
- initial structural stop is unchanged;
- original 2R target is unchanged;
- H4 lifecycle is unchanged;
- active stop is checked before target on the same M15;
- a ratchet observed on one M15 becomes effective only on the next M15;
- stop can improve or hold, never widen;
- `off` must reconcile baseline exactly;
- no market/anchor/side may be deleted;
- no policy may be promoted from this consumed result.

## Evidence status

The current 760-day five-market evidence, including its temporal subdivisions,
has already been inspected in earlier stages. It is
`CONSUMED_DEVELOPMENT_EVIDENCE`.

Any selected policy must later traverse a separately sealed temporal validation.

## Authority

- DEMO_ELIGIBLE=false
- LIVE_AUTHORIZED=false
- PRODUCTION_AUTHORIZED=false
- REAL_CAPITAL_AUTHORIZED=false
