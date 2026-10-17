# VT08 P0-B — 495 FVG/CISD source receipts verified, intracycle C3 EQ future-leak prevented

**Date:** 2026-10-10 America/Asuncion. **Owner:** independent cognitive Architect B, branch `agent/vt08-5m-cognition-replay-20261010`, [PR #764](https://github.com/mezas3238-hue/qore-core/pull/764). Methodology A [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765). All work RESEARCH-ONLY ON GITHUB. No VPS, no live/demo, no sealed seven-year holdout.

## 1. Primary observed evidence and literal scope

**A frozen producer:** [GitHub Actions run 38098839670](https://github.com/mezas3238-hue/qore-core/actions/runs/38098839670), exact code SHA `5ea7d4ff2104200e99328bf57f6ee1aed447e028`. Five original `*-three-families-full.json` artifacts (do not follow mutable A branch). **Original market M15:** [run 35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907), source-capture SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`. Five files `market-evidence-1095d.json`.

**Independent B full receipt verification:** [GitHub Actions run 38103539460](https://github.com/mezas3238-hue/qore-core/actions/runs/38103539460) **SUCCESS**, code+tests SHA `0d596111e2005e02a9176f0a2ab743a0d6c2ebd5`, Ruff PASS, Mypy PASS and **9/9 adversarial tests** PASS. Report [artifact #11688891924](https://github.com/mezas3238-hue/qore-core/actions/runs/38103539460/artifacts/11688891924). B isolated verifier [source file](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/src/qore/infrastructure/trader_lab/vt08_5m_b_independent_three_family_receipt_audit_v1.py), [tests](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/tests/infrastructure/trader_lab/test_vt08_5m_b_independent_three_family_receipt_audit_v1.py), [workflow](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/.github/workflows/vt08-b-independent-three-family-fvg-m15-receipts.yml).

B read the **frozen A full receipts**, independently loaded the **physical M15 raw series**, reconstituted for every actual receipt:
- C1/C2 H4 windows, C2 *single* sweep and close-inside C1, and chosen side (no both-sides sweep admitted);
- exactly **one** surviving triple-M15 FVG at the end of parent H4 (C1 for C2 model, C2 for intracycle C3), formation time = third M15 bar CLOSED; transparent QORE distal invalidation, **not** TTrades POI significance;
- first M15 overlap/touch strictly after FVG formation; opposing-series start, extreme, CISD crossing first opposite candle OPEN on a CLOSED M15; no future M15 and no multiple competing PS within evaluated prefix;
- event-level `origin_id`, `source_event_id`, `snapshot_sha256`, close times `evaluated_at`, `htf_closure_known_at` and `swing_point_confirmed_at = max(actual relevant H4 close, actual CISD close)`, anchored per NY Owner source;
- for intracycle C3 **only** M15 prefix until the actual source decision, no future final C3 H4 OHLC;
- research authority flags, source POI priority **NOT verified**, 0 economic entries/fills/PnL.

## 2. Independently verified receipt-level totals (NOT trade counts)

| Market | C2 source FVG/CISD receipt matches | C3 intracycle source FVG/CISD matches |
|---|---:|---:|
| EURJPY | 48 | 49 |
| USDCHF | 52 | 44 |
| NZDUSD | 48 | 49 |
| CADJPY | 42 | 63 |
| USDCAD | 47 | 53 |
| **TOTAL** | **237** | **258** |

**495/495** frozen producer structural receipts matched independently reconstructed M15 source. `C3_CLOSURE_TO_C4` narrow unique-FVG receipts = **0**, which **does not falsify** the C3→C4 source family. This study validates each *reported receipt*, **not an exhaustive independent search for false-negative source events in the entire M15 universe**, nor the TTrades relevance/priority of each historical POI. Never add these 495 to the previous 488 narrow B01 or 294 C3 shape populations. Different, partially overlapping research detection definitions, no approved cohort for paired economic comparison.

**Critical missing distinction:** A's `swing_point_confirmed_at` is genuinely at/after HTF+CISD close. That is a **new model-swing confirmation**. It is NOT an independently attested **prior reference swing** knowable **before `C2.opened_at`** for the choice of intra-C2 WITH/AGAINST EQ. A's prior C1 FVG provenance is NOT, by itself, the identity of an author-valid reference swing. The B report deliberately shows `prior_reference_swing_eq_attested=0` (meaning *not independently attested in the evidence package*, **not** 0 valid swings in actual markets). EQ against-swing cannot be promoted without primary-source rule and original pre-C2 candle proof.

## 3. NEW independently found + repaired B P0: intra-C3 future EQ

While extending the B textual-rule acceptance contract, B found that the prior `verify_causal_event` had an unsafe branch: **both** `C3_CONTINUATION_FROM_C2` (entry during C3) **and** `C3_CLOSURE_TO_C4` were allowed to declare `C3_FULL_WICK_TO_WICK_AFTER_CLOSURE`. For intracycle C3, final `C3.high`/`C3.low` is NOT causally known until H4 C3 closes; using that EQ for an intra-C3 entry would be a full-bar lookahead regardless of a perfectly as-of M15 CISD.

**Fix B:** [text-only independent source boundary](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/src/qore/infrastructure/trader_lab/vt08_5m_b_methodology_spec_boundary_v1.py) explicitly requires `C3_CONTINUATION_FROM_C2` decision and hypothetical entry strictly before C3 H4 complete, prohibits completed C3 H4 candle payload, rejects `C3_FULL_WICK_TO_WICK_AFTER_CLOSURE`, and only accepts the explicitly non-consumed `EQ_NOT_CONSUMED_INTRAC3_H4_UNCLOSED` placeholder, which preserves `B_SOURCE:C3_INTRACYCLE_EQ_SOURCE_UNADJUDICATED`. A *previous C2* EQ could be added only after a separately frozen/source-verified rule and as-of evidence, **not** inferred by reusing future C3. C3 Closure→C4 continues to use *completed* C3 full-range EQ (different family). No research signal or live authority is unlocked by the repair.

**Proof:** [GitHub Actions #38103628679](https://github.com/mezas3238-hue/qore-core/actions/runs/38103628679) **SUCCESS** on SHA `fc043fad59498b179bd5184d452cc8292ce66205`: **19/19 adversarial tests**, Ruff PASS, Mypy PASS, B-only textual specification gate (no A code checkout/import). The tests explicitly reject future C3 EQ, complete C3 H4 object in intracycle and entries at/after H4 final close. Source-rule report [artifact #11687919631](https://github.com/mezas3238-hue/qore-core/actions/runs/38103628679/artifacts/11687919631). Existing `APPROVED_A_B_MANIFEST_SHA256=None` **unchanged**.

## 4. No premature D → A rule promotions

**Still D (source fidelity):** reference swing for EQ pre C2, applicable POI type and author-priority per family; FVG significance HTF vs mechanically surviving M15 triple; source-mapped PS logic and multiple-PS selection; double C2 sweep 105 earlier C3 shapes; quantitative wick threshold/timeout; C3 intracycle appropriate EQ or no EQ rule; exact source entry/SL/TP/lifecycle and evidence cutoffs for ALL Cognitive Situation fields. This is why `source_complete=0`, `cognitive_ready=0`, `fills=0`, `PF/DD=NOT_MEASURED`.

**Previous distinct source attestations still valid at their exact scope:** B [488 B01 source-lineage run #38095654032](https://github.com/mezas3238-hue/qore-core/actions/runs/38095654032); B [294 C3/C4 two-clock shapes #38098119759](https://github.com/mezas3238-hue/qore-core/actions/runs/38098119759); B [A/B/C/D policy #38098820220](https://github.com/mezas3238-hue/qore-core/actions/runs/38098820220). None constitutes a fully blind methodology-certifying replay; B has previously inspected A implementation. All code/tests kept separate and data physically cross-compared, but only a source-text-first frozen acceptance with independent quoted-primary-author adjudication can promote D to A.

**Action requested from A #762/#765:** deliver frozen **TEXT-ONLY** A/B/C/D spec by C2/C3-continuation/C3-closure family (REFERENCE_SWING, POI, EQ, CISD, PS, FAMILY_BOUNDARY), URL+date+brief exact quote for every A, raw bars/timestamps for pre-C2 reference swing, and source-supported choice of prior C2 EQ vs no EQ for an intracycle C3. Publish counts for source-confirmed CISD/PS separately from 129 proxies, 36 full-body QORE C, 105 double sweeps D. B will write independently spec-driven acceptance and revisit 488/495, NOT authorize via count.

**Prohibited:** VPS, DEMO/LIVE, sealed 7Y, mock broker orders, signed manifest invention, fictional profitability, retrospective trade conversions. Priority is rules D→A, not greater unverified density.


## 5. P0 corrective addendum: PRE-C2 reference is NOT a universal C3 prerequisite

**Verifier blind spot found and corrected after the 495 receipt result:** the initial B textual rule guard applied `reference_swing.identified_at<C2.open` equally to `C2_COMPLETED`, `C3_CONTINUATION_FROM_C2`, and `C3_CLOSURE_TO_C4`. The auditor's pre-C2 requirement specifically addresses selecting the *intra-C2 WITH-vs-AGAINST EQ regime*, not all C3 methods. Extending it unconditionally would be an unreferenced QORE rule that can veto valid C3 situations and destroy density without author support.

**Now in B code:**
- **C2_COMPLETED with EQ:** pre-C2 reference swing and source POI must be available before C2 opens. For against-swing EQ, an A-supplied boolean is still not independent proof; raw historical reconstruction and primary-source adjudication remain blockers.
- **C3_CONTINUATION_FROM_C2:** no artificial pre-C2 reference; instead `prior_c2_model_swing_proof` must show a real predecessor C2 confirmation with `source_bar_id+hash+closed_at+available_at <= C2.closed_at`, and must be independently audited. Missing proof creates `B_SOURCE:C3_PRIOR_C2_SWING_ASOF_UNATTESTED`; a producer-supplied shaped proof still leaves `B_SOURCE:C3_PRIOR_C2_SWING_PRIMARY_REVIEW_PENDING`. C3 final H4 full EQ remains invalid for intracycle entry.
- **C3_CLOSURE_TO_C4:** confirmation belongs to completed C3 H4 and its causal M15 CISD/PS; pre-C2 reference is NOT a universal source prerequisite; `B_SOURCE:C3_CLOSURE_POI_AND_SWING_PRIMARY_REVIEW_PENDING` until independent source validation. C3 EQ full can be observed only at/after C3 close.

**Exact CI:** [GitHub Actions #38103823100](https://github.com/mezas3238-hue/qore-core/actions/runs/38103823100) **SUCCESS**, code+tests SHA `6b331930d9a90d4e72c82c8174cc19c3cb40355d`; **21/21 adversarial tests PASS**, Ruff PASS, Mypy PASS; [artifact #11688154606](https://github.com/mezas3238-hue/qore-core/actions/runs/38103823100/artifacts/11688154606). Positive/negative tests distinguish pre-C2 regime reference from preceding completed C2 swing vs completed C3 closure; reject future or retro-confirmed C2 previous swing. **Not a new source A-promotion.** All orders/fills/cognitive approvals stay zero.
