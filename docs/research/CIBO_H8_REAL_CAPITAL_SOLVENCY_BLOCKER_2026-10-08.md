# CIBO — H8 ACTUAL ACCOUNT SOLVENCY: CRITICAL P0 / NO GO
## 2026-10-08 — Research evidence, not certification

**AUTHORITATIVE OVERRIDE of past claims that modeled USD 670k terminal capital proves a real funded return.** Previous 35–36% DD "physical frontiers" meant *final-capital-floor-valid within a permissive settlement ledger*, not broker/margin/funded-execution certified.

## First physically unfunded mandatory executed position

Independent H8 fail-closed branch: `agent/cibo-physical-solvency-failclosed-h8-001`, workflow [37766123403](https://github.com/mezas3238-hue/qore-core/actions/runs/37766123403), SUCCESS **only as a diagnostic**, NOT successful trading certification.

Confirmed failure:
`CIBO_H8_UNFUNDED_EXECUTED_TRADER_BASELINE`
- Mandatory 1x MEDIUM source required USD **4.520000**.
- Physically available sovereign source USD **4.215535347065321381962719165**.
- Deficit about USD **0.30446465**, even though overall ledger risk/margin capacity checks were green.
- H8 policy correctly fails the research simulation rather than silently booking an unfunded entry or rejecting the Trader. There is no permission to credit eventual model PnL.

Root issue: the old engine demoted over-capacity ATTACK to MEDIUM 1x without rechecking source availability, stop-risk and margin before `selected.append`; MEDIUM losses debit the sovereign bank while bootstrap wins could flow to the ATTACK cushion. The invariant `attack_sovereign_breach_usd == 0` did not detect sovereign bank insolvency.

## Quantified ledger losses across four modeled carriers

Read-only audit: [37767203071](https://github.com/mezas3238-hue/qore-core/actions/runs/37767203071), SUCCESS, frozen preexisting replay artifacts and exact 3,368-entry checks.

| Archived research carrier | Model capital final USD | Min sovereign bank USD | End bank USD | Sovereign bank protection floor | Violation |
|---|---:|---:|---:|---:|---|
| Global STRICT `f-m2850-h0060` | 670,974.1002 | **-54.6172** | **-45.9274** | 30 | YES |
| Physical 35.24019 `m1-0700` | 670,926.0075 | **-54.6172** | **-45.9274** | 30 | YES |
| Physical 35.20661 `m1cliff-n00624` | 670,925.7615 | **-54.6172** | **-45.9274** | 30 | YES |
| Research 34.95158 `ctx2-a-s50` | 670,718.4234 | **-55.3845** | **-46.6947** | 30 | YES |

The nominal global case's sovereign-floor breach is approximately **USD 84.6172**, in spite of `attack_sovereign_breach_usd == 0`. In the three first listed cases, terminal cushion exceeds the modeled total capital because a negative sovereign bank is offset against it. This **is not proof the whole combined account reached zero at a settlement timestamp**; the critical claim is precisely that a protected bank and mandatory entry were **not properly funded**. Intratrade mark-to-market, liquidation prices, minimum broker lots, costs and margin closeouts remain unproven.

## New reproducible modern H8 research branch

`agent/cibo-h8-modern-35206-hardgate-001` began from current canonical `62c053603fbb96af779c2632783270551bace8a4`, preserving the current CIBO model, not the outdated script in the original H8 branch. It adds the H8 physical funded-source/stop-risk/margin gate **before** any entry is booked.

- `.github/workflows/cibo-h8-modern-physical-capacity-35206.yml` / [run 37766889084](https://github.com/mezas3238-hue/qore-core/actions/runs/37766889084): exact 35.20661% candidate under modern hard-gated engine. Check final verdict; **do not assume pass**.
- `.github/workflows/cibo-h8-physical-bootstrap-share-ablation.yml` / [run 37767055543](https://github.com/mezas3238-hue/qore-core/actions/runs/37767055543): causally redirect bootstrap MEDIUM profit share between sovereign and cushion (0%,25%,50%,75%,100%) while demanding actually funded mandatory 1x. This is a **research ablation**; any floor miss or capacity breach is a rejection.
- `.github/workflows/cibo-h8-historical-carrier-ledger-audit.yml` / [run 37767203071](https://github.com/mezas3238-hue/qore-core/actions/runs/37767203071): read-only legacy negative-bank audit, finished SUCCESS.

## Binding decision / mandatory next work

1. **Block promotion, trading deployment, certification and claiming withdrawable profits** based on the four archived curves. Keep them as historical *hypothesis research*, not real economically viable carriers.
2. Prove every mandatory Trader entry is **broker-fundable at its actual minimum executable quantity** with the real cash ledger. CIBO remains responsible for post-execution management and may not veto a Trader's entry. If the original 3,368 positions cannot all fit USD60 initial available financing, document **infeasibility**; don't conjure new bank credits, suppress entries or use a 10,000x multiplier as a substitute.
3. A valid redesign may reallocate **already realized, unreserved** available profits across sovereign/cushion *atomically* under explicit Sovereign authorization; it must reconcile money conservation on each decision, never re-label borrowed reserve as cash, never borrow future profit. It must still pass the full replay and all broker margin conditions.
4. After true 1x funded execution, model **mark-to-market equity, intrabar worst adverse excursion, gap/slippage, stop-out margin and broker lot steps**, plus forced liquidation chronology. Terminal settlement PnL and DD alone are insufficient.
5. Rebuild the REAL economic ceiling and max-DD frontiers from USD60 with the corrected physical model. The old floor USD582,440.03 is a **historical comparison target only**, not evidence a surviving cash path exists.
6. Retain 3,368 required Trader entry intents/decisions for audit, but if an execution is physically impossible the test must emit **FAIL**, not log an imaginary executed trade. No claim that all 3,368 are fundable until proven.
7. Only if a physically funded policy actually survives without negative bank/margin liquidation can CIBO resume genuine <=25% (ideal <=20%) DD optimization, temporal OOS, Monte Carlo, realistic costs, accounting reconciliation, Worst-Trader Rescue and Final Integrated Certification.

**Current status: NOT CERTIFIED — REAL-CAPITAL-FUNDING BLOCKER (P0).**

Further research-only context-stop DD reductions on the old permissive ledger cannot override this decision.

---

## Addendum: modern replay proves 35.2066% carrier unfunded (2026-10-08)

Exact modern-engine H8 replay [37766889084](https://github.com/mezas3238-hue/qore-core/actions/runs/37766889084), **SUCCESS diagnostically / STRATEGY BLOCKED**. At decision 2019-08-07 06:55 UTC, epoch 102, mandatory MEDIUM 1x required **USD 6.020000** of stop-risk+provider-fee source vs **USD 3.380219937157485631395490315** legitimately available after sovereign floor. Sovereign bank USD 33.81755034706532138196271917; protected floor USD30; free portfolio cushion **USD 19.76393860806455076191180576**. The 35.20661% old DD curve **does not survive the original bank-only hard funding rule**. The workflow's GREEN diagnostic is NOT a GREEN strategy.

Independent first-breach causality [37767846850](https://github.com/mezas3238-hue/qore-core/actions/runs/37767846850): earliest marked bank-floor violation at bank **USD 26.50342695591958**, floor USD30, free cushion **USD 68.33166195542810**, required internal top-up **USD 3.49657304408042**. First negative sovereign bank later arose with free cushion approximately **USD 8,938.17**. This is clear evidence of disjoint treasury allocation even when the combined ledger has funds; it is not evidence those funds can always meet broker stop-out constraints.

Research-only physically conserved bank/cushion bridge branch: `agent/cibo-h8-fundable-cushion-transfer-prototype-001`, code gate patch commit `8f68c8d726d8d231e93629165506dcdc3d0a6999`. Prototypes (1) cash transfer only from available unreserved cushion, (2) instantaneous conservation of bank+cushion total, (3) sovereign reserve+floor protection after settlement, (4) FAIL if insufficient cash. Run [37767770097](https://github.com/mezas3238-hue/qore-core/actions/runs/37767770097) exercises 35.20661% under these conditions; its outcome must be checked from Actions before claiming improvement. Three cash-bridge unit tests PASS, [37767945929](https://github.com/mezas3238-hue/qore-core/actions/runs/37767945929), but no unit test is substitute for full replay.

Alternative profit routing (bootstrap cushion share constrained to **0.50–1.00** by current engine) is being probed separately at [37767843304](https://github.com/mezas3238-hue/qore-core/actions/runs/37767843304). The earlier 0/25% probe was invalid CLI configuration and the earlier raw-M5-warm-cache error was tooling, not an economic result. Do not report either as strategy failure or success.

**Promotion remains blocked until a completed H8 full replay demonstrates 3,368 funded entries and no bank floor breaches, and independent broker mark-to-market/margin stop-out tests pass.**


## Addendum: exact Decimal precision and scientific replay custody

The first prototype run [37767770097](https://github.com/mezas3238-hue/qore-core/actions/runs/37767770097) failed **as software engineering evidence**, raising `CIBO_H8_BRIDGE_MONEY_CONSERVATION_FAILURE` when using Python Decimal's default 28-digit context with longer receipt precision. This is **not** proof that real transfers invent money: the research implementation was not exact enough for the audited ledger.

Corrective commit [181e728b67505bf3a42036553ceeb31792d4cea0](https://github.com/mezas3238-hue/qore-core/commit/181e728b67505bf3a42036553ceeb31792d4cea0) places the entire atomic debit/credit and before/after reconciliation inside a local **100-digit Decimal** context, preserving invariants at original precision. Independent [unit run 37768247176](https://github.com/mezas3238-hue/qore-core/actions/runs/37768247176): **4/4 PASS**, including a high-precision regression using account balances from the first H8 capacity failure. Success of these tests **does not** establish a viable 3,368-trade strategy.

After also repairing raw-M5 input restoration for direct CLI replays, full bridge trial [37768291949](https://github.com/mezas3238-hue/qore-core/actions/runs/37768291949) was launched. It has no verified economic verdict in this addendum; inspect run results before reporting. On scientific success one must still verify all 3,368 entries, count/totals of actual cushion-to-bank transfers, min sovereign bank >= its protection floor, zero 1x unfunded errors, terminal floor, cost and broker margin.

Bootstrap share 0.00 and 0.25 are rejected by the existing parameter domain `[0.50,1.00]`; do not treat them as valid economic research results. Corrected separate share ablation `0.50/0.60/0.70/0.80/0.90/1.00` is [run 37767843304](https://github.com/mezas3238-hue/qore-core/actions/runs/37767843304) with raw M5 restored for the direct evaluator.


## Precision follow-up — genuine 1x funding must use 100-digit sovereign source ledger

The first full trial with the 100-digit atomic cash bridge was [37768291949](https://github.com/mezas3238-hue/qore-core/actions/runs/37768291949), **SUCCESS diagnostically**, but **strategy BLOCKED** at the same 2019-08-07 06:55 UTC mandatory MEDIUM 1x. The bridge moved real cushion cash and the bank became USD 36.457330409907835750567228855; however, the per-entry source gate saw `6.019999999999999999999999995` vs `6.020000`, a deficit **USD 0.000000000000000000000000005**. This is the 28-digit Decimal precision boundary, not a meaningful portfolio loss. Still it correctly FAILS rather than booking an underfunded position.

Research fix `561e8d0ffa2ba46ef8d13b223753d50039a1696e`: (a) protected source/needed transfer computed in local 100-digit Decimal context, (b) local sovereign/cushion/source counters moved with 100-digit exact values, and (c) H8 funded source computed from the actual post-transfer bank minus actual outstanding sovereign reservations and protected bank floor. Corrected **5/5** H8 invariant unit suite: [37768917841](https://github.com/mezas3238-hue/qore-core/actions/runs/37768917841), SUCCESS. Full v2 proof [37768938754](https://github.com/mezas3238-hue/qore-core/actions/runs/37768938754) must be read separately; this note **does not presume its result**.

A standalone alternate 50% MEDIUM-to-cushion profit share was launched as [37769014634](https://github.com/mezas3238-hue/qore-core/actions/runs/37769014634) without cash bridging; only an H8-capacity PASS could establish it helped. Do not infer a fix merely because it reduces model bankruptcies or DD.


## Next confirmed H8 results — 2026-10-08 11:20 UTC

- H8 cash-bridge v2 [37768938754](https://github.com/mezas3238-hue/qore-core/actions/runs/37768938754): **diagnostic SUCCESS but STRATEGY BLOCKED** at 2020-07-13 21:10 UTC, epoch 1129. Mandatory 1x MEDIUM required USD0.310000000 but the stale local per-epoch source counter reported USD0.3099999999999999999999999960 (4E-27 less), with bank USD35.50226919159809420651185873, dynamic floor USD35.1922691915980942065118587450, available cushion USD3,622.7187640329076. Do not credit the model.
- v3 patch `73846e8ea4484d739896b02b27381da7288649a5` tracks **pending same-epoch sovereign and cushion source commitments independently**, using 100-digit bank, reservations and current peak floor. Prevents both double-use of pending source and false underfunding from rounded 28-digit local counters. Settlement-floor replenishment also runs with 100-digit exact arithmetic. Full replay [37769446768](https://github.com/mezas3238-hue/qore-core/actions/runs/37769446768) is the decisive new H8 scientific gate; **its outcome must be verified** (not silently promoted).
- Alternative 50% fixed cushion profit share (without bridge) [37769014634](https://github.com/mezas3238-hue/qore-core/actions/runs/37769014634) **diagnostic SUCCESS / strategy BLOCKED**. On 2022-03-29 14:19 UTC epoch 3024, mandatory MEDIUM 1x required USD39.9000, protected available USD25.4097736353965, bank USD148.3164 vs dynamic sovereign floor USD122.9066, free cushion USD342,756.7393. Thus static `bootstrap_cushion_share=0.50` cannot by itself solve physical funding.
- Multi-case profit share run [37767843304](https://github.com/mezas3238-hue/qore-core/actions/runs/37767843304) was cancelled without complete scientific results; do not count its variants.
- H8 isolated cash bridge precise regression suite [37768917841](https://github.com/mezas3238-hue/qore-core/actions/runs/37768917841): **5/5 PASS**. Validates local money conservation and exact first H8 shortage in isolation only.

**No P0 clearance:** physically funded 3,368/3,368 positions, broker intratrade margin, liquidation and new valid DD/economic ceiling remain unproven.
