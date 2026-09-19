# VT31_NAS100_R5 — Final Certification Contract

Status: **FROZEN CANDIDATE / FINAL HOLDOUT SEALED / NOT LIVE**

## Identity

- Candidate: `VT31_NAS100_R5`
- Market: NAS100
- Methodology: VT31 AM Silver Bullet intelligent hybrid + structural rearm
- Timezone: America/New_York
- Decision source: closed M1 only
- Base variant: `WAIT_1025_B060`
- Rearm profile: `ACTIVITY_L`
- Rearm management: `SCORE_PROTECT`
- Global risk scalar: `0.60`

No runtime or certification step may alter this configuration after the final
holdout is opened.

## Frozen economics

First-position pre-scalar risk:

- CORE: 1.00R
- SECONDARY: 0.05R
- SCOUT: 0.02R
- monthly alternate budget: 0.60R

Structural rearm:

- maximum one genuine rearm per day;
- new raid + new confirmation + new decision are mandatory after the first
  terminal exit;
- causal pre-entry quality score only;
- HIGH/MID/LOW pre-scalar rearm risk: 0.10R / 0.05R / 0.02R;
- ACTIVITY_L monthly rearm budgets are determined only from the previous
  month's base trade count:
  - <=8: 0.30R
  - <=10: 0.17R
  - >10: 0.04R
- final global risk scalar: 0.60.

The engine is locked to this one activity profile and this one scalar for final
certification. No alternative variant is scanned on holdout evidence.

## Development binding

5Y consumed validation:

- Run: 35358805202
- Artifact: 10554091357
- Artifact ZIP SHA-256:
  `38359f743b86a23be1d8294d9f4e03d2613261bd7b6cff63c4ef54ffc16ec0b3`
- Window: [2017-07-01, 2022-07-01)
- Trades: 806
- PF: 2.147751559984496546692193737
- Max DD: 5.76313027394994178900211746R
- Total: +53.97656884532812305172257968R
- Annual blocks: 5/5 positive.

This evidence is consumed development evidence and is not the final fresh
certification holdout.

## Final sealed holdout

- ID: `VT31_NAS100_R5_FINAL_HOLDOUT_001`
- Window: [2022-07-18T00:00:00Z, 2024-07-18T00:00:00Z)
- Calendar span: 731 days
- Selected before acquisition
- No overlap with consumed VT31/CIBO evidence ending 2022-07-15
- Canonical M1 collector requires >=730 actual days
- After first successful acquisition this interval is permanently consumed and
  can never be called fresh again.
- No retuning against this interval is allowed.

## Final certification gates

The single frozen candidate must satisfy all of the following on the sealed
holdout:

- 300–350 terminal trades;
- PF >= 1.50;
- mean R > 0;
- total R > 0;
- observed max DD <= 6R;
- 2/2 annual blocks positive;
- Monte Carlo positive-terminal probability >= 0.90;
- Monte Carlo p95 max DD <= 15R;
- +0.01 source-R extra-cost stress remains positive with PF >=1.40 and DD <=6.5R;
- +0.02 source-R extra-cost stress remains positive with PF >=1.30 and DD <=7R;
- +0.05 source-R severe extra-cost stress remains positive with PF >1.0.

If any gate fails:

`VT31_NAS100_R5 = REJECTED_FINAL_HOLDOUT`

The same holdout may not be used for retuning.

If every gate passes:

`VT31_NAS100_R5 = TRADER_CERTIFIED`

Certification does **not** itself enable live execution.

## Authority

Until separate runtime integration and Owner activation:

- `LIVE_AUTHORIZED = FALSE`
- `REAL_CAPITAL_AUTHORIZED = FALSE`
- `PRODUCTION_AUTHORIZED = FALSE`
- `ORDER_SUBMISSION_AUTHORIZED = FALSE`

No merge is authorized by this contract.
