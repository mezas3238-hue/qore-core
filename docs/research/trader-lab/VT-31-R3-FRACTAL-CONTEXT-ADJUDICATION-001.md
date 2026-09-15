# VT-31 R3 FRACTAL CONTEXT — RESEARCH ADJUDICATION 001

Checkpoint: 2026-09-14

## Scope and source fidelity

This tranche continued VT-31 on `NAS100`, `SP500`, and `US30` with identical
execution semantics and without touching fresh evidence.  TTrades remains the
methodology authority.

Primary source chain used:

- Owner file `1000856441.mp4`, SHA-256
  `bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf`,
  YouTube `o0v4KQxZbpU`.
- TTrades Scalping Model:
  https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/
- TTrades Candle 2 Closures:
  https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/
- TTrades Candle 3 Closure:
  https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/
- TTrades Fractal Model Playbook:
  https://ttrades.com/fractal-model-playbook-aligning-daily-hourly-and-5-minute-charts/
- TTrades Relative Strength / SMT:
  https://ttrades.com/relative-strength-weakness-smt-divergence-full-guide/

The newer Fractal Model material is recorded as a new R3 methodology line.  It
does not retroactively rewrite the original Silver Bullet source.

## Evidence boundary

Only the corrected, already-consumed R2.5 M1 DEMO evidence was used:

- NAS100 artifact `10350575547`, digest
  `sha256:1a16adc1485ce7f77666fde2261a36dd62beea8cfea1f3a5abcea176a3902cea`
- SP500 artifact `10351435307`, digest
  `sha256:bcdc7a346cb3a618b277934d21e9ed30583f814c0645862dd48cd8ca3a5a1fc1`
- US30 artifact `10350622506`, digest
  `sha256:bdfc75724433162bd4d079f581543c09aad75f35406a7a3d2985cd205c89b96c`

The historical tranche before 2024-08-15 remains unopened for VT-31 fresh
validation.

## Executed research

| Version | Run | Artifact | ZIP digest | Result |
|---|---:|---:|---|---|
| R3 | 34869773365 | 10358685274 | `ce575e30f76705f76cfc926916897d3ec19e3824f5b864cf7c0da467c2416643` | no survivor |
| R3.1 | 34870000252 | 10358567117 | `f6feee2266ef50ab8cd2207a7ff5809411c7382b343d6b89672843678db2e647` | no survivor |
| R3.2 | 34870252873 | 10359070432 | `af54d76bda7061c65c4f4bedcf8e9d8f5541c14ffd824e15d08c09e16bee2377` | no survivor |
| R3.3 | 34870430346 | 10358961466 | `44cb26c58c9e61337f627d5b671901d29edda5e570f167750c96c708821006f8` | no survivor |
| R3.4 | 34870748776 | 10359245952 | `fc5b22700b1ed0954d0c83719e4b7882bbc9d7cb4b8a95b8789a050216783113` | no survivor |
| R3.5 | 34871020178 | 10358484728 | `5b22fba2e37b3798bf11f63f926748626cce412074d4f24ea03d6dd3ef27e3c8` | no survivor |
| R3.6 | 34871228628 | 10359042901 | `7311a45c4f67003dfaba7065a853f6f36aba724775f78f7319e156787fd233f7` | no survivor |
| R3.7 | 34871534445 | 10358697377 | `872f769762fbb9cb9105f376073d69a53f828f8fa752979e770dedcd54a2b4b4` | no survivor |

R3 added 17 predeclared hypotheses.  Together with R2.5–R2.8, the research
ledger now contains 32 tested hypotheses.  Failed hypotheses remain visible.

Tested families included exact daily/H1 C2, H1 C3/continuation closures, H1
closure-family unions, cross-index relative-strength ranking, first unique
cross-index confirmation, source-anchored exact 2R, M15 causal closure filters,
M15-then-M1 sequential replay, and persistent H1 closure state.

## Best non-candidate observation

`latest-daily-h1-directional-closure` in R3.7 was the strongest result:

- sample: 93
- raw total: +68.0770368685R
- raw mean: +0.7320111491R/trade
- raw PF: 2.0637037011
- raw max DD: 16.1455479452R
- stressed total at 0.05R/trade: +63.4270368685R
- stressed mean: +0.6820111491R/trade
- stressed PF: 1.9334368928
- stressed max DD: 17.6455479452R
- NAS100 stressed mean: +0.1373117973R/trade
- SP500 stressed mean: +0.5249519595R/trade
- US30 stressed mean: +1.3627970867R/trade
- LONG stressed mean: +0.6355108726R/trade
- SHORT stressed mean: +0.7295223012R/trade
- positive quartiles: 3/4

It failed the predeclared aggregate sample gate (`93 < 150`) and at least one
per-market minimum (`< 30`).  Those gates are not lowered after observing the
result.  Therefore this observation is not frozen and is not allowed to consume
fresh evidence.

Other apparently promising small-sample H1 and M15 results were also rejected.
Relative-strength ranking, fixed 2R, first-confirmation containment, and the
sequential M15 replay did not repair the full cross-market failure.

## Artifact audit

Run `34871769718` at SHA
`634d7677e1b2f3adf981a532ff56aa1096a5ecd4` downloaded, digest-verified,
unpacked, SHA256SUMS-verified, parsed, and adjudicated all eight R3 artifacts.

Audit artifact: `10359721271`

Audit ZIP digest:
`sha256:e1de96de0a4e4dfd0ae429f11ef457888a276fb9ed3f6595b4ee89570f250f95`

Audit result:

- `artifacts_read=8`
- `zip_digest_verification=PASS`
- `embedded_sha256sums=PASS`
- every artifact remained research-only
- no fresh evidence was opened
- no candidate was frozen
- no artifact declared DEMO eligibility

## Adjudication

`VT31_R3_CANDIDATE_NOT_JUSTIFIED`

`VT31_CANDIDATE_FROZEN=false`

`VT31_DEMO_ELIGIBLE=false`

`LIVE_AUTHORIZED=false`

`REAL_CAPITAL_AUTHORIZED=false`

`PRODUCTION_AUTHORIZED=false`

PR #550 remains DRAFT and unmerged.  No candidate branch or fresh one-shot
workflow is created because the freeze preconditions were not met.
