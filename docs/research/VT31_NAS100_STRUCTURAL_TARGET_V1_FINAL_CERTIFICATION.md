# VT31 NAS100 Structural Target V1 — Final Certification Record

Status: **TRADER_CERTIFIED / NOT LIVE / NOT PRODUCTION**

Checkpoint: 2026-09-20  
Repository: `mezas3238-hue/qore-core`  
Branch: `agent/vt31-nas100-hypothesis-lifecycle-v1`

## Identity

- Candidate: `VT31_NAS100_STRUCTURAL_TARGET_V1`
- Selected variant: `EQ50_COMPRESSED_ACCEPT_RUN25`
- Contract fingerprint:
  `089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08`
- Market: NAS100
- Methodology: frozen VT31 AM Silver Bullet
- Timezone: America/New_York
- Decision source: closed M1 only
- Silver Bullet source remains unchanged.

## Frozen structural target architecture

The certified target architecture is frozen as follows:

1. When the frozen 09:00–10:00 NY reference equilibrium is a forward
   structural level and is touched on a closed M1 strictly before terminal,
   bank 50%.
2. If DOL1 is not reached, the remaining 50% preserves the original terminal.
3. If DOL1 is reached, default behavior is to realize the remaining 50% at
   DOL1.
4. Runner exception:
   - reference volatility was `compressed` at entry; and
   - the DOL1-touch M1 closes beyond DOL1.
5. Under that exception:
   - bank 25% at DOL1;
   - leave 25% runner;
   - runner destination = DOL2, defined as +0.25 frozen reference width;
   - runner protection = second confirmed M1 protective swing (PS2), effective
     from the next M1.
6. Stop can improve or hold, never widen.
7. Same-M1 runner stop/target ambiguity is `STOP_FIRST`.
8. Future journey labels, terminal PnL, fold identity and calendar-date edge
   rules are forbidden runtime inputs.

No parameter selection, scan or retuning is authorized after freeze.

## Freeze binding

Candidate freeze:

- Run: `35513305170`
- Freeze artifact: `10605623133`
- Artifact digest:
  `sha256:46f157d912551bf4f75954df907d810f1e58705622d8c782161a53699ddb21f9`
- Freeze result: SUCCESS
- Development folds: R5 / R6 / R8 / consumed all passed their declared gates.

## Five-year consumed validation

Five-year run:

- Run: `35513474108`
- Artifact: `10605433453`
- Artifact digest:
  `sha256:9630a64496b3bdb9eafd29cde0d9a33d463cfb451bd56ba6a117188736e43502`
- Window: `[2017-07-01, 2022-07-01)`
- Evidence status: `CONSUMED_EXTENDED_VALIDATION`
- Fresh: FALSE
- Parameters retuned inside 5Y: FALSE

5Y result:

- Trades: **806**
- Wins: **241**
- Losses: **565**
- PF: **3.736184576983536**
- Total: **+68.4017921123R**
- Mean: **+0.0848657470R/trade**
- Observed max DD: **3.7089849073R**
- Max losing streak: **11**
- MC positive terminal: **99.98%**
- MC p95 DD: **6.3348648310R**
- MC p99 DD: **8.1518108457R**

All declared 5Y gates passed.

## Five annual blocks

Every year block is positive:

| Block | Window | Trades | PF | Total R | Max DD |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 2017-07-01 → 2018-07-01 | 156 | 1.6027 | +3.7530R | 2.6177R |
| 2 | 2018-07-01 → 2019-07-01 | 165 | 4.3047 | +17.6399R | 1.7185R |
| 3 | 2019-07-01 → 2020-07-01 | 153 | 2.8009 | +9.8027R | 1.6025R |
| 4 | 2020-07-01 → 2021-07-01 | 171 | 2.6539 | +8.5829R | 2.7646R |
| 5 | 2021-07-01 → 2022-07-01 | 161 | 11.2163 | +28.6234R | 0.7605R |

Annual stability: **5/5 positive**.

## Rolling 2Y temporal / WFO-style stability

All four frozen-policy rolling 2Y windows passed density, PF, positive total and
DD gates:

| Window | Trades | PF | Total R | Max DD |
| --- | ---: | ---: | ---: | ---: |
| 2017-07-01 → 2019-07-01 | 321 | 2.8499 | +21.3928R | 2.6177R |
| 2018-07-01 → 2020-07-01 | 318 | 3.5454 | +27.4426R | 2.5549R |
| 2019-07-01 → 2021-07-01 | 324 | 2.7292 | +18.3856R | 3.7090R |
| 2020-07-01 → 2022-07-01 | 332 | 5.6559 | +37.2063R | 2.7646R |

Rolling temporal stability: **4/4 PASS**.

## Execution / slippage stress

The exact frozen candidate was stressed with additional source-R execution
cost. No policy parameter was changed.

| Extra cost | PF | Total R | Max DD | MC positive |
| --- | ---: | ---: | ---: | ---: |
| +0.01R | 3.6900 | +67.9520R | 3.7688R | 99.96% |
| +0.02R | 3.6448 | +67.5023R | 3.8287R | 100.00% |
| +0.05R | 3.5146 | +66.1530R | 4.0082R | 99.95% |

All execution-stress gates passed.

## Extreme-trade dependence

The candidate remains profitable after removing its largest winners:

- Remove largest 1 winner:
  - 805 trades
  - PF **3.1837**
  - Total **+54.5913R**
  - DD **3.7090R**
- Remove largest 5 winners:
  - 801 trades
  - PF **1.8218**
  - Total **+20.5435R**
  - DD **3.9898R**

The edge is not dependent on one or five extreme winning trades.

## Directional diagnostics

Both directions remain positive over the certification window:

- LONG:
  - 372 trades
  - PF **3.0706**
  - Total **+22.5110R**
  - DD **1.9089R**
- SHORT:
  - 434 trades
  - PF **4.2484**
  - Total **+45.8908R**
  - DD **3.3140R**

## Final certification suite

Final suite:

- Run: `35519882906`
- HEAD: `75719aef3c625f387d726ff519fdd0f059414f67`
- Artifact: `10607439608`
- Artifact digest:
  `sha256:a08eb5ab18833e8112002a2ab908460c152b7b39b3314c879df6b2c499858568`
- Conclusion: SUCCESS

All final gates are TRUE:

- frozen identity exact;
- 800–900 trades;
- PF >= 1.50;
- total positive;
- observed DD <= 6R;
- 5/5 annual blocks positive;
- 4/4 rolling 2Y windows pass;
- MC positive terminal >= 0.90;
- MC p95 DD <= 15R;
- +0.01R stress gate;
- +0.02R stress gate;
- +0.05R severe stress remains positive;
- remove-top-1 robustness;
- remove-top-5 robustness.

Final decision:

`VT31_NAS100_STRUCTURAL_TARGET_V1 = TRADER_CERTIFIED`

## Evidence qualification

The final certification suite uses consumed extended validation evidence. It
does **not** claim a new fresh holdout. The candidate was frozen before its 5Y
validation and was not retuned inside the 5Y or final robustness suite.

## Authority

Certification does not authorize execution.

Until a separate Owner order for runtime integration / activation:

- `LIVE_AUTHORIZED = FALSE`
- `REAL_CAPITAL_AUTHORIZED = FALSE`
- `PRODUCTION_AUTHORIZED = FALSE`
- `ORDER_SUBMISSION_AUTHORIZED = FALSE`

No merge is authorized by this record.
