# VT08 Cognitive Expansion 5M — Adaptive Protection V2 Hypothesis Freeze

Status: **POST-FORENSICS HYPOTHESIS / PRE-FRESH-ECONOMICS / NO AUTHORITY**

This freeze is produced from consumed 1095-day mechanism forensics. It creates
two falsifiable position-management hypotheses. It does not promote either one.

## Why a V2 hypothesis exists

The Core Stack robustness failures were decomposed against the exact
structural-bank-only arm. This isolates the incremental effect of the inherited
CIBO `aggressive` stop ratchets.

Consumed attribution:

### CADJPY

- overall aggressive-protection delta vs bank-only: +1.9416R
- anchor 01: +1.6955R
- anchor 05: +1.9191R
- anchor 09: **-1.6731R**

Hypothesis: CADJPY 09 NY has a distinct journey shape where the same aggressive
ratchet is premature. Keep the trade and the structural banking unchanged, but
use BANK-ONLY stop behavior at anchor 09. Anchors 01/05 retain the pre-existing
aggressive policy.

### NZDUSD

- overall aggressive-protection delta vs bank-only: -2.5026R
- risk/reference HIGH: +1.4829R
- risk/reference MID: +1.4116R
- risk/reference LOW: **-5.3971R**

Mechanistic hypothesis: when initial VT08 risk is <25% of the reference-H4
range, a fixed +0.50R ratchet is reached too early in the larger H4 journey and
clips continuation. Keep trade admission and structural banking unchanged, but
use BANK-ONLY stop behavior for the already-frozen LOW risk/reference state.
MID/HIGH retain the pre-existing aggressive policy.

The LOW threshold (<0.25 reference-H4 range) is not newly fitted here; it is the
pre-existing causal geometry band already frozen in Core Capital Intelligence.

## Candidate identities

- `VT08_CADJPY_ADAPTIVE_PROTECTION_V2_A9_BANK_ONLY`
- `VT08_NZDUSD_ADAPTIVE_PROTECTION_V2_LOW_RISKREF_BANK_ONLY`

## Invariants

For both candidates:

- no entry is removed;
- no market/side/anchor is filtered;
- initial stop is unchanged;
- fixed 2R target is unchanged;
- H4 lifecycle is unchanged;
- EQ50 bank and structural destination are unchanged;
- the stop may improve or hold, never widen;
- OFF means no ratchet, not no stop;
- no runtime PnL, terminal label, fold identity or calendar-date edge feature;
- trade count must reconcile exactly with Core Stack V1.

## Fresh validation boundary

All evidence beginning at or after:

`2023-09-24T23:45:00Z`

is consumed for these hypotheses.

Any fresh validation must use signals **and exits** strictly before that
boundary. The candidate cannot be retuned from the fresh result.

## First fresh gates

Per market:

- fresh sample >= 30 trades;
- adaptive PF > 1.20;
- adaptive total R > 0;
- adaptive PF > frozen Core Stack V1 PF on identical fresh trades;
- adaptive DD <= frozen Core Stack V1 DD on identical fresh trades;
- trade count identical.

A pass is only `FRESH_MECHANISM_SCREEN_PASS`, not certification.

## Authority

- research_only=true
- demo_eligible=false
- live_authorized=false
- production_authorized=false
- real_capital_authorized=false
