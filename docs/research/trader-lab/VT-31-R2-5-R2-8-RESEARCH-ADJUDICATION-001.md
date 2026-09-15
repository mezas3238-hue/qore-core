# VT-31 R2.5–R2.8 — Multi-Index Research Adjudication 001

Checkpoint: 2026-09-14

Status: **REJECTED FOR CANDIDATE FREEZE — NO DEMO/LIVE/REAL-CAPITAL AUTHORITY**

## Source boundary

Primary authority remains TTrades `youtube:o0v4KQxZbpU`,
`1000856441.mp4`, SHA-256
`bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf`.

The source demonstrates NAS100/NQ, the 09:00–10:00 New-York reference,
10:00–11:00 M1 entry window, strict range raid, post-raid reversal structure,
Breaker/FVG/Order-Block entry families, raid-extreme stop, opposite-range
target, pending expiry at 11:00 and 3R-to-breakeven management. SP500 and US30
remain Human-Owner-authorized transfer research, not new source authority.

## Acquisition correction

The initial R2.5 evidence at `06b93fb...` was invalidated before acceptance:
fourteen-day M1 windows could exceed cTrader's 5,000-bar page while
`hasMore` was not reliable. The corrected collector uses three-day windows
(maximum 4,321 inclusive M1 openings) and serialized markets.

Official corrected run: `34847475943`

Validated code SHA: `81466402548f2c6343d0a038a2558a3a83dc0795`

Full QORE Gate: PASS.

Corrected evidence:

| Market | Bars | First | Last | Provider | Evidence fingerprint |
|---|---:|---|---|---|---|
| NAS100 | 733,653 | 2024-08-15 13:22Z | 2026-09-14 13:21Z | USTEC | `83fadfd2e17f53f681bf78aa562fa66a55b94536acbd73bd3f629fd608c363b9` |
| SP500 | 729,127 | 2024-08-15 13:33Z | 2026-09-14 13:32Z | US500 | `c7f1752c43d9d68b595c6c36108c6bfc6510a0e7d77d72b9f23be868526aa16c` |
| US30 | 733,157 | 2024-08-15 13:40Z | 2026-09-14 13:39Z | US30 | `1d271a26e95a543cdb5143285742ec7210e3450e17de476059c2efc9c72bda07` |

Artifact IDs and ZIP digests:

- NAS100 `10350575547` — `sha256:1a16adc1485ce7f77666fde2261a36dd62beea8cfea1f3a5abcea176a3902cea`
- SP500 `10351435307` — `sha256:bcdc7a346cb3a618b277934d21e9ed30583f814c0645862dd48cd8ca3a5a1fc1`
- US30 `10350622506` — `sha256:bdfc75724433162bd4d079f581543c09aad75f35406a7a3d2985cd205c89b96c`
- adjudication `10350477574` — `sha256:591cdb1e99bbd0e592c64c61e0e8aa9780cde657ff1933c4d6162431e2afcc09`

Artifact inspection run `34861281681` verified all four ZIP digests, embedded
Git SHAs and adjudication digest
`73a5e21657cf8a63228bdbb92ebc3cc7321b95f327cd1724c8e2031b85d6cd57`.

## Hypothesis ledger

Fifteen hypotheses were registered and retained:

1. R2.5: Breaker, FVG and Order Block × near-stop, midpoint and near-target
   (nine hypotheses).
2. R2.6: all demonstrated entry families with nearest still-valid retracement
   × the same three zone locations (three hypotheses).
3. R2.7: R2.6 near-stop plus source-anchored minimum planned 3R
   (one hypothesis).
4. R2.8: structural close plus directionally aligned confirmation body, with
   and without the 3R containment (two hypotheses).

No market-specific, direction-specific or outcome-derived rescue was accepted.

## Best research result and falsification

R2.6 near-stop was the strongest aggregate result:

- sample: 443;
- raw total: +85.6013R;
- raw mean: +0.19323R/trade;
- raw PF: 1.27525;
- stressed total at 0.05R/trade: +63.4513R;
- stressed mean: +0.14323R/trade;
- stressed PF: 1.19172;
- stressed max DD: 46.5033R;
- LONG stressed mean: +0.26022R/trade;
- SHORT stressed mean: +0.02571R/trade;
- positive quartiles: 3/4;
- NAS100 stressed mean: -0.16108R/trade;
- SP500 stressed mean: +0.24754R/trade;
- US30 stressed mean: +0.35545R/trade.

It failed the predeclared maximum-DD and every-market-positive gates.

R2.7 retained 423 observations and +64.7802R stressed with PF 1.20416, but
NAS100 remained -0.17157R/trade and stressed DD remained 46.5815R.

R2.8 directional displacement retained 397 observations and +49.1061R
stressed with PF 1.16640, but NAS100 remained -0.15175R/trade and stressed DD
was 55.3949R. Adding the 3R containment retained 379 observations and
+51.9426R stressed with PF 1.18455, but NAS100 remained -0.15353R/trade and
stressed DD was 53.3449R.

R2.6 official run: `34862087159`, validated code SHA
`d198e28fb757ab800bd7e3a60b83f131d2d2903b`; Ruff PASS, Mypy PASS,
7,332 tests PASS. Artifact `10355074492`, ZIP digest
`sha256:f7c8d5d539623371b861569dbf859d86d8225a81effe0add4017e3db28f6d37a`.

R2.7 run: `34864010227`; artifact `10355707880`, ZIP digest
`sha256:2370717f83c039e58e8384a1aa1279a1759de4a892d88d0c9d8572b885232806`.

R2.8 run: `34864294132`; artifact `10355867996`, ZIP digest
`sha256:6c46c5e189fd04e280cd6adc163fbf4b899ab78929ea934662e0f95674d6d38d`.

## Root-cause adjudication

The zero-trade R2.4 outcome was caused by source overconstraint, while the
original non-reproducible R2.5 evidence was caused by M1 request truncation.
Both engineering faults are corrected.

After correction, the remaining failure is economic generalization. Alternative
entry-family selection, exact zone location, a source-anchored 3R floor and
directional-body confirmation do not produce acceptable NAS100 expectancy or
drawdown. Positive aggregate results are carried by SP500/US30 and sparse large
winners. Removing NAS100, using LONG only or selecting a market-specific family
would be retrospective rescue and contradict the common-contract objective.

The qualitative source ambiguities still lacking numerical authority are sweep
depth, displacement magnitude, premium/discount distance and minimum R:R. No
additional threshold may be selected from these consumed outcomes and called a
TTrades rule.

## Decision

`VT31_R2_5 = REJECTED`

`VT31_R2_6 = REJECTED`

`VT31_R2_7 = REJECTED`

`VT31_R2_8 = REJECTED`

`VT31_CANDIDATE_FROZEN = FALSE`

`VT31_DEMO_ELIGIBLE = FALSE`

`LIVE_AUTHORIZED = FALSE`

`REAL_CAPITAL_AUTHORIZED = FALSE`

`PRODUCTION_AUTHORIZED = FALSE`

No fresh evidence was opened because no candidate passed consumed-evidence
research gates. The historical period before 2024-08-15 remains preserved for
a genuinely new, pre-frozen methodology contract.
