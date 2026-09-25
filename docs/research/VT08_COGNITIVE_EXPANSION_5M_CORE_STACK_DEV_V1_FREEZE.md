# VT08 Cognitive Expansion 5M — Core Stack DEV V1 Freeze

Status: **DEVELOPMENT CANDIDATE FREEZE / SELECTED FROM CONSUMED EVIDENCE**

This is not a fresh-holdout freeze. The component choices below are explicitly
informed by consumed development evidence and therefore require a later sealed
validation on bars earlier than the currently consumed boundary.

## Consumed evidence boundary

Current 760-day corpus begins approximately:
`2024-08-25T21:00:00Z`

All evidence from that boundary through 2026-09-23 is consumed.

## Development finding that motivates the stack

On the consumed temporal segment, EURJPY with the pre-existing VT08 CIBO
`aggressive` stop family produced:

- baseline PF: 0.9076728591
- protected PF: 1.7692650047
- baseline DD: 7.3917R
- protected DD: 3.0000R
- protected total: +3.9803R
- trade count unchanged: 20

This does **not** authorize the policy. It only justifies a development
composition test.

## Frozen Core Stack DEV V1

Apply the same architecture to all five research markets:

1. Frozen VT08 signal admission / entry / initial stop / original 2R target.
2. VT08-native reference-H4 midpoint as structural equilibrium.
3. Bank 50% when that equilibrium is reached.
4. VT08-native opposite reference-H4 extreme as structural destination.
5. Bank the remaining 50% when that destination is reached later.
6. While exposure remains open, apply the already-existing VT08 CIBO
   `aggressive` ratchet family:
   - +0.50R observed -> stop 0.00R from next M15;
   - +1.00R observed -> stop +0.50R from next M15;
   - +1.50R observed -> stop +1.00R from next M15.
7. Active stop is evaluated before target/banking on each M15.
8. Ratchets observed on one M15 become active only on the next M15.
9. No selective runner in DEV V1; the consumed runner experiment did not
   demonstrate material capacity.
10. Stop may improve or hold, never widen.
11. No market/anchor/side deletion.

## Fresh validation requirement

If this composite creates a viable development candidate, the next evidence
must extend backward before the consumed boundary. The intended first fresh
window is the newly acquired portion of a 1095-day corpus strictly earlier
than `2024-08-25T21:00:00Z`.

No bar at or after the consumed boundary may be counted as fresh.

## Authority

- research_only=true
- selected_from_consumed_evidence=true
- fresh_holdout_passed=false
- demo_eligible=false
- live_authorized=false
- production_authorized=false
- real_capital_authorized=false
