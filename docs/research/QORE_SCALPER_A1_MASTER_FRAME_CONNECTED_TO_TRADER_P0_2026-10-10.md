# QORE Scalper P0 — Master Frame wired to the real Trader intent boundary

Date: 2026-10-10 | Architect: A1 Cognition | Branch: `agent/scalper-architect-a-cognition-20261010` | PR #758 (DRAFT) | Methodology peer PR #759 | Master PR #623.

## Owner P0: "Master Frame must influence the Trader, not just be written in a sidecar"

**IMPLEMENTED AND TESTED ON GITHUB, RESEARCH ONLY.** This work fixes the previously verified functional disconnect: V49 used frozen structural H1→M15→M1 opportunity selection; V50-G independently used a static `WELL_SUPPORTED` and fresh empty memory per candidate. Neither represented the nine-market full Master Frame influencing admission.

There are now **two independently exercised economic/integration seams**, both preserving the legacy frozen V49 baseline:

### 1. The original Trader source-intent selection function now actually invokes the Master Frame

`src/qore/infrastructure/trader_lab/capitalizer_high_frequency_trader_v49.py`:

- Existing `select_portfolio_trade_intents(opportunities)` **unchanged in behavior** when called without the opt-in research flags.
- New explicit call: `select_portfolio_trade_intents(opportunities, master_frame_barriers=(...), settled_memory=...)`. This route requires **actual already observed nine-market `A1MultiHypothesisBarrier` evidence** and a chosen-settled causal memory ledger, otherwise fails closed.
- Internally `select_master_frame_trade_intents` invokes `prepare_trader_cognition_packet` → real `replay_multi_hypothesis_evidence` → real `evaluate_full_frame_research_batch` → **actual `build_master_cognitive_frame` for every originally sourced candidate**. Source ID uses frozen `source_opportunity_id(V49Opportunity)` (identical to V50-G causal trace/hash), preserving source ancestry.
- Verifies **the exact ID set across all original V49 opportunities**, no duplicate or unknown source; one barrier per original confirmed M1 timestamp, strict chronology; matches market ID and H1/M15/M1 clocks; does not accept unresolved `TTRADES_REVIEW_PENDING` source-rule evidence as adequate in this route.
- PASS means candidate competes for a **research-only V49TradeIntent**, WAIT/ABSTAIN do **not** produce an intent, all disposition/WHY rows remain accounted. Selection is the preexisting deterministic chronological-source policy, under the **as-of available session slots and MAX3 ceiling**. This is an **experimental cognitive A/B policy, not an author-certified global simultaneous arbitration algorithm**.
- New `A1MasterFrameTraderIntentReport` preserves every source-ID and full packet, PASS/WAIT/ABSTAIN, selected intent IDs, MAX3 capacity nonadmissions and invariants. No sizing, no QORE Risk grant, no broker order, no certification.
- Direct regression: same three observed source candidates, one remaining MAX3 slot. With memory ablated the frozen chronological candidate wins; with previously chosen and settled independent failure fingerprint `STATE-A`, the Master Frame **ABSTAINS on that candidate**, and a distinct same-market PASS candidate becomes the Trader intent. Its **original V49 price/stop/target** are unchanged. Baseline call remains three intentions; research call selects one due the actually observed as-of slot. This verifies a behavioral difference at the Trader boundary, not just a logging flag.
- Defensive regressions reject missing one original source, duplicated source, unresolved rule ID, future/barrier duplication, inaccurate session and memory metadata.

### 2. PAPER economic replay explicitly consumes full Master Frame cognition and causal settled memory

`src/qore/infrastructure/trader_lab/capitalizer_a1_master_frame_paper_trader_integration_v1.py`:

- `run_real_master_frame_paper_trader(barriers, original_sources, baseline_selected_source_ids, ...)` applies the actual computed Master Frame decision to **PAPER admissions** and records source-ID matched verdict, WHY, source census and differences vs frozen V49 historical fills.
- For each new decision, the prior PAPEr CHOSEN settlements enter cognitive memory **only when their exit has occurred AND the settlement is strictly confirmed before the decision**. No unexecuted/counterfactual loss feedback. Optional independently attested causal loss labels; no fabricated fingerprint for unknown losses.
- Records gross PF/R/DD on the chosen pre-existing V49 fill outcomes only **after** admission, for diagnostic comparison. The frozen fill book is *not* a newly recomputed native-M1 executable book. No physical BID/ASK/spread/commission/slippage claims, no LIVE or FundedNext authority. Nine-market world barriers and A2 sensory observations must be provided externally; this module does not fabricate them.
- Current PAPER tests use controlled, **synthetic nine-market fixtures** and intentionally supplied `SCALPER_SENSOR` / `SCALPER_NATIVE_M1_ASOF` tokens. These test *call integration*, not real native data provenance. Exact source identity and the full Master Frame are exercised. No 9/9 historical full-cognitive metric has been measured.
- NOTE: sensor tokens supplied by the caller are **claims**, not cryptographic or provider-attested feed verification. Before scientific replay or certification the ingestion layer must independently verify their native origin, as-of timestamps and closed-candle evidence.

### Frozen numeric controls — NOT full-cognition test outcomes

A2 baseline true native-M1 nine-market [run #38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695): 2,876 pre-MAX3 source trade rows, 2,020 V49 portfolio trades, gross PF ~0.66446, DD ~236.134R. Legacy 94-trade V50-G [run #38053723674](https://github.com/mezas3238-hue/qore-core/actions/runs/38053723674) is the rejected partial cognition branch. These figures **MUST NOT** be presented as the effect of the newly connected Master Frame.

Scientific preservation gate on the exact V49 selected denominator: >=934 originally winning source IDs, >=415.748485649R original winner R mass, and no silent loss of opportunity source IDs. DD target 3–5R, hard limit <=6R, gross/net PF, Sharpe/Sortino, stress, 9/9 eras and holdouts all pending measurement with the new integration.

## Verified CI of integrated code and regressions

**Code commit:** `db9b0e1a16bad982c68dea48301bdc25798108b7`.

- [Full source Cognition Audit #38078342854](https://github.com/mezas3238-hue/qore-core/actions/runs/38078342854) — **SUCCESS**, Ruff repository-wide, Mypy no issues in **1,629 source/test files**, **57/57 focused tests PASS**.
- [A1 Causal Research Quality #38078342859](https://github.com/mezas3238-hue/qore-core/actions/runs/38078342859) — **SUCCESS**, Ruff, Mypy focused module, **38/38 tests PASS**.

No repository merge, VPS deployment, live or broker action occurred.

## Remaining P0 for actual nine-market native-M1 cognition+economics

1. **A2 must provide the 9-market event-time source/sensor bridge**, including exact `source_opportunity_id`, source-rule identifier with independently reviewed author classification, H1 and M15 confirmed clocks, native M1 confirmed trigger, full nine-market perception integrity, supported market/regime hypotheses, cross-market causal graph and evidence provenance. Sensor strings alone are insufficient for history-based certification.
2. Freeze a complete chronological 9/9 historical barrier dataset at identical V49 baseline event IDs; no future H1 terminal labels, synthesized state/support, missing market fillers or approximate M5-to-M1.
3. Connect the PAPER evaluated-admission pipeline to **native M1 replay of all truly chosen trades** under independent QORE Risk, bid/ask and physical costs. The existing PAPER A/B reuses frozen precomputed trade outcomes and therefore CANNOT prove new entry/exit economics if the decision changes the fill timing or order footprint.
4. Complete source-author review of **same-market multiple hypotheses and cross-market joint arbitration** before changing frozen first-MAX3 policy. No hindsight ranking or arbitrary new universal veto.
5. Produce exact source-ID matched 9/9 A/B + memory and competition ablations, original positive winner mass, DD, PF, Sharpe, Sortino, OOS + stress. Do not promote based solely on unit CI or attractive 90-trade apparent PF.

**CURRENT STATE:** Master Frame → **actual Trader research intent routing: CONNECTED**; Master Frame → **PAPER admission and causal settlement: CONNECTED in executable tests**; **authentic historical 9/9 full-cognitive replay: NOT EXECUTED**; **live risk/order integration: NOT AUTHORIZED**; **Scalper certification: BLOCKED**. Preserve PR #758 / #759 / #623 OPEN DRAFT and without merge.
