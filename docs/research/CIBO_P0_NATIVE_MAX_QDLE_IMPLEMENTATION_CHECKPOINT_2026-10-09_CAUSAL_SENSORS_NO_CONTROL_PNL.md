# QORE CIBO P0 — IMPLEMENTATION CHECKPOINT 2026-10-09
## Native MAX sensor-derived management → 4 motors → QDLE no-CONTROL NAV; real exit path integration still open

**STATUS:** partial code repair and first causality tests PASS; **P0 NOT CLOSED, NO LIVE, NOT CERTIFIED**.  
**CANONICAL HANDOFF:** [CIBO_P0_MASTER_EMERGENCY_HANDOFF_2026-10-09_NATIVE_MAX_COGNITION_QDLE_UNIVERSAL_NO_STRATEGIC_BLOCKS.md](CIBO_P0_MASTER_EMERGENCY_HANDOFF_2026-10-09_NATIVE_MAX_COGNITION_QDLE_UNIVERSAL_NO_STRATEGIC_BLOCKS.md)  
**BRANCH:** `agent/cibo-sovereign-integration-p0-20261008` • **PR:** #745 DRAFT.  
**CEILING DISCOVERY HISTORICAL RESULTS ARE NOT BROKER PHYSICAL MANAGED PNL.**

## 1. First pending audit resolved

The previous fresh Native MAX run **#37912035662** is **completed, SUCCESS**, on SHA `057707e687db8030d2a191a4d70fbb56130d1b0b`. Final job `native-max-3368-cibo-manager-qdle` reports all stages PASS, 3368 distinct source signals, Native MAX recomputed fresh, 3368 manager advisory receipts and both QDLE research arms. Output artifact **11609885185**, ZIP digest **sha256:aeb47d8a0e234c2c01d3406b11c5ded55ccc0a156caa84ce9e1344a3485c635f**.

**Interpretation:** old workflow PASS only meant 3368 receipts + static legacy disposition-to-mode translation, not 3368 economically managed positions. Its old financial figures use Trader historical structural R on one subset and are NOT CIBO-Native managed PnL. This was the P0 defect.

## 2. Code changes actually made

| File | Change |
|---|---|
| `src/qore/infrastructure/cibo_p0_native_cognitive_management.py` | New deterministic **research adapter** consuming authentic predecision Native MAX `CALIBRATION`, `REASONING_ROUTING`, `SCENARIO_ENGINE`, `METACOGNITION`, `CAUSAL_REASONING`, `EXECUTIVE_SYNTHESIS` sensor metrics; no original capital disposition as input to mode. |
| `scripts/cibo_p0_native_max_manager_advisory_3368.py` | Replaces `COGNITIVE_BLOCK→BANK`, `CAPITAL_BLOCK→MEDIUM`, `RISK_REVIEW_READY→ATTACK` static authority with new sensor-derived management policy. Retains legacy reason *solely* as diagnostic. Source remains research, not authorized native trade instruction. |
| `scripts/qdle_3368_dual_ledger_replay.py` | Validates 3368 joined cognitive receipts; passes sensor-derived risk request to actual QDLE physical quoting. Every Native quote is isolated in temporary no-fill QDLE, even if economic SL happens to equal Trader SL. Never consume `gross_structural_outcome_r` into Native-managed NAV. Prevents CONTROL cashflows from activating compound loss streak for manager. Shadow NAV remains untraded USD60; complete manager PnL/PF/DD marked null. Does NOT touch LIVE broker gate. |
| `scripts/cibo_p0_native_managed_exit_path_audit.py` | New optional historical executable **bid/ask** path adapter to `cibo_managed_exit_replay.py`; reconciles quote fingerprint+symbol+entry/stop/fees; implements stop-first, partial/BE/trailing/defensive research exits if evidence supplies complete path. Missing/nonterminal path remains UNKNOWN/no PnL. **No global NAV write**. |
| `tests/infrastructure/test_cibo_p0_native_cognitive_management.py` | Legacy disposition inert; perturbing confidence changes economic risk request and physical QDLE lot; abstention remains received; bad/missing/noncausal sensor fails. |
| `tests/infrastructure/test_cibo_p0_native_managed_exit_path_audit.py` | Synthetic bid/ask exit differs from CONTROL R; no false settlement on missing path; bars chronology, symbol and source checks. |
| `.github/workflows/cibo-p0-native-cognitive-management-fast.yml` | Fast compile, unit + physical QDLE regression and source-isolation guards. |
| `.github/workflows/cibo-p0-native-max-manager-qdle-3368.yml` | Full-run assertions now enforce no structural Trader settlements/fake PnL in Native manager, 3368 sensor risk intents, quote-only status, dynamic cap. |

**Important interim design limitation:** Native MAX currently emits rich cognitive observations but not a native broker-agnostic `CiboCognitiveManagementDecision` signed action stream. The mapper is now *causally dependent on real sensor values* rather than old research selection labels, **but policy thresholds are explicitly a temporary paper research hypothesis**, not the native brain's fully authenticated autonomous management stream. Do not declare the MAX cognitive integration finished.

**Temporary paper risk request rule:** if calibration abstains, audit evidence insufficient or confidence <34 => BANK requests 25% of the **5% NAV maximum** (=1.25% NAV). Confidence 34–66 => MEDIUM requests 50% of max (=2.5% NAV). Confidence >=67, nonabstaining sufficient evidence => ATTACK requests full 5% NAV. **Never guarantees a broker physical minimum lot**, risk is all-in stop+fees+buffer, margin and broker grid still constrain. `CIBO` receives all 3368 regardless of capacity.

## 3. Verified CI (do not confuse with full replay validation)

- `CIBO P0 Native Cognitive Management Fast Tests`, run **#37915730556**, SHA `6de3015dead3e1aa5d790bb6826fee7be928acf0`: SUCCESS, 43 tests.
- Fast run **#37916086175**, SHA `18332ffd1593e1ff445bd15413c8e24b68ed33a5`: SUCCESS, 47 tests including shadow bid/ask path.
- Fast run **#37916235608**, SHA `cbaf6f26c23015057f37eaec4df6e9b484805db5`: SUCCESS, **48 tests**, including changing solely Native MAX confidence and observing QDLE lots **0.00 / 0.01 / 0.02** under unchanged USD60 account, $14/lot fee, physical 0.01 grid. This is a causal synthetic contract test, not market returns.
- Full Native MAX 3368 two-arm updated workflow **#37915676547** triggered from SHA `5953a32c71607b5251992135ff0bc27bce0f2c31`; **in progress at checkpoint writing**. Recheck exact status/artifacts and any failed step before claiming replay PASS. That SHA contains the core Native sensor/QDLE/control-isolation changes, but precedes later exit-path adapter, tests and null-DD reporting amendment.
- Several unrelated older repo-wide GitHub jobs (e.g. Zero Open Work Gate) have FAILED in push activity. They are NOT green and must be reviewed independently, not cited as P0 approval.

## 4. Critical invariants

1. **3368/3368 received**, independent of the old CIBO capital/cognitive filters. This is a receipt count, not a fill count.
2. The native management **risk fraction reaches QDLE's actual risk intent and lot quote**, proven by unit integration.
3. All Native MAX quotes remain **SHADOW NONSETTLING**, no original-Trader `gross_structural_outcome_r` booked against CIBO NAV, no OPEN fees debited without hypothetical fill proof. This intentionally means **no meaningful Native manager cumulative PnL/PF/DD available yet**.
4. `THREE_SETTLED_LOSSES_HAIR_CUT` still exists as an optional generic compound policy for *genuinely reconciled* losses; the Native research arm must never inject three original-Trader CONTROL losses to activate it. Do not globally delete real solvency controls.
5. Bid/ask path adapter can compute **only source-covered independent trade exit counterfactuals**; a synthetic-path test does **not** constitute the 3368 realistic managed replay or portfolio returns.
6. Zero real MT5 fills, zero LIVE order_send, no proof of historical six-symbol broker fill/spread/stops, and no certification.

## 5. Remaining emergency P0 tasks in strict order

**P0-1:** Read full updated run #37915676547 and its artifact. Verify **3368 source IDs**, mode counts now from real Native sensors, 3368 native cognitive budget intents, 3368 received, funded=0 for Native, quote-only vs unfundable; no Trader CONTROL PnL; all-in <=5% NAV. Investigate any failure; run latest SHA if changes postdated that run.

**P0-2:** Replace interim deterministic sensor-to-policy mapper with native MAX management decision generation **inside the Native engine**: causal `CiboCognitiveManagementDecision` per Trader signal and across post-entry market events, optional signed economic/execution instruction with risk, SL, TP, partials, BE, trailing, defensive and safe invariants. Show full reasoning trace, version, source timestamp, uncertainty and digests, not fabricated labels.

**P0-3:** Obtain trusted complete historical bid/ask market paths, orderability and six symbol broker specs (or report missing exact coverage). Wire `cibo_p0_native_managed_exit_path_audit.py` only where source exists. A path's synthetic-test source may NEVER certify real financial results.

**P0-4:** Upgrade QDLE global scheduler for actual *causal* managed position lifecycle with entry OPEN fee debited once, partial deal timestamps/lot grid, STOP/BE/TRAIL/DEFENSE at executable side, CLOSE fees, swap, marks, broker margin held/released, recovered risk and CIBO-authored settlements. Feed ONLY those managed settlements to four economic votes/NAV and source Bank/Cushion. Until this works full PF/DD stay null.

**P0-5:** Compare control vs no-strategy-caps vs native manager with identical trusted data/costs/provider conditions; 3368 received and separately count quoteable, actually modelled fills/settled. Verify synthetic tests, leakage, 5% all-in, gap risk and holdout. Finally record broker MT5 specs *read-only*, no sends.

**P0-6:** Re-run nonlive exact HEAD CI, update PR #745 and this checkpoint, provide audit artifact SHA, result counts and acceptance recommendation. Keep PR DRAFT / NO LIVE until real evidence.

## 6. Links

- Earlier successful raw native recompute [#37912035662](https://github.com/mezas3238-hue/qore-core/actions/runs/37912035662)
- New fast cognitive/physical lot PASS [#37916235608](https://github.com/mezas3238-hue/qore-core/actions/runs/37916235608)
- Updated full 3368 run awaiting completion [#37915676547](https://github.com/mezas3238-hue/qore-core/actions/runs/37915676547)
- PR [#745](https://github.com/mezas3238-hue/qore-core/pull/745)

**DO NOT CLOSE THE P0** merely because this document and tests were published. No actual full CIBO position-management outcomes or full manager drawdown have been proven.
