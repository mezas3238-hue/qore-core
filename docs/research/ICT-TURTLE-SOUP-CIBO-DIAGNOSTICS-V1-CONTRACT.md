# QORE CORE — ICT TURTLE SOUP × CIBO DIAGNOSTICS V1

## Causal market-state attribution, evidence tiers and promotion gates

**Status:** RESEARCH / FORENSICS ONLY  
**Identity:** `ICT_TS_CIBO_DIAGNOSTICS_V1`  
**Parent:** `ICT_TS_BEHAVIOR_LAB_V1`  
**Tracker:** GitHub Issue #600  
**Repository:** `mezas3238-hue/qore-core`

---

## 0. Purpose

CIBO is introduced here as a **market-state diagnostic reader**, not as a retrospective optimizer and not as an execution authority.

The objective is to answer:

> What market state was already observable before entry that the Turtle Soup trader did not explicitly model, and does that state explain subsequent behavior in a way that survives replication outside the 12-trade R5 sample?

A diagnosis is not accepted because it sounds plausible. Every conclusion must have:

1. a frozen source of evidence;
2. a machine-readable observation;
3. a declared evidence tier;
4. a falsifiable prediction if causal language is used;
5. stability analysis;
6. an explicit promotion gate before it can affect a trader.

---

## 1. Frozen evidence inputs

### Behavior Lab
- Identity: `ICT_TS_BEHAVIOR_LAB_V1`
- Authoritative run: `35125861002`
- HEAD: `4d09a43aa5795624b4a7cb29bb2503ae586c5a4f`
- FX event population: **189,579 liquidity-raid events**
- Evidence status: `CONSUMED_DIAGNOSTIC_ONLY`

### R5 holdout
- Identity: `ICT_TURTLE_SOUP_R5_D1_AUTHENTIC_IDEAL_C2__H4_AUTHENTIC_IDEAL_C2__POSITIONAL_DAILY_DOL`
- Holdout: `ICT_TS_R5_FRESH_2016_2018`
- Authoritative run: `35118222306`
- HEAD: `9beb2f8147db2b9fb780bc4cc28e2cdb05b7851e`
- Trades: **12**
- Evidence status: `CONSUMED`

### Exact attribution already established
- 12/12 R5 trades linked to exact D1 prior-candle C2 raid event.
- 12/12 R5 trades linked to exact H4 prior-candle C2 raid event.
- 24/24 exact core matches.
- Join key: symbol + side + exact C2 source timestamp + `reference_type=prior-candle`.
- No fuzzy date/session matching is permitted.

---

## 2. Evidence hierarchy

Every CIBO statement MUST carry exactly one of the following evidence tiers.

### `E0_OBSERVATION`
Directly measured fact from frozen evidence.

Examples:
- H4 C2 reclaimed the swept level.
- D1 opposing C1 extreme had already been touched before entry.
- protected swing was X source-range units away.

No causal language is allowed at E0.

### `E1_ASSOCIATION`
Measured relationship in consumed evidence.

Requirements:
- sample size;
- effect size or rate difference;
- uncertainty / confidence interval where applicable;
- market/time stability;
- explicit statement that association is not an operating rule.

### `E2_CAUSAL_HYPOTHESIS`
A market-structure explanation consistent with E0/E1 and the frozen methodology.

Requirements:
- causal mechanism stated in advance;
- falsifiable prediction;
- variables available at or before entry;
- explicit falsifier;
- independent evidence slice not yet inspected for the test.

### `E3_REPLICATED_DIAGNOSTIC_MECHANISM`
An E2 hypothesis that was preregistered and reproduced on independent diagnostic evidence.

Requirements:
- preregistration SHA;
- independent evidence identity;
- same sign/direction of effect;
- stability checks;
- failure cases documented.

E3 is still **not automatically a trading rule**.

### `E4_CANDIDATE_OPERATING_RULE`
May exist only under a NEW trader/candidate identity.

Requirements:
- owner approval;
- source/mechanism justification;
- pre-economic freeze;
- fresh economic validation;
- independent governance gates.

**No conclusion may jump directly from E0/E1 to E4.**

---

## 3. Required CIBO state vector

For every R5 trade and later for every Behavior Lab event where inputs exist, CIBO must emit a machine-readable state vector.

```text
SETUP_VALIDITY_STATE
MARKET_PHASE
DELIVERY_STATE
LIQUIDITY_STATE
PRIMARY_DOL_STATE
PROTECTED_SWING_STATE
BANK_STATE
LOCK_STATE
ATTACK_STATE
CROSS_MARKET_CONTEXT
PRE_ENTRY_CONTRADICTIONS
POST_ENTRY_STATE_TRANSITIONS
DIAGNOSTIC_CAUSE_CODES
CONFIDENCE_TIER
```

### Enumerations

#### `MARKET_PHASE`
- `EXPANSION`
- `RETRACEMENT`
- `CONSOLIDATION`
- `REVERSAL`
- `AMBIGUOUS`

#### `DELIVERY_STATE`
At minimum:
- `BULLISH_PERSISTENT`
- `BEARISH_PERSISTENT`
- `BULLISH_REACTION_ONLY`
- `BEARISH_REACTION_ONLY`
- `TRANSITIONAL`
- `CONFLICTED`
- `UNRESOLVED`

#### `PRIMARY_DOL_STATE`
At minimum:
- `INTACT_AND_DIRECTIONALLY_ALIGNED`
- `INTACT_BUT_CONFLICTED`
- `PARTIALLY_CONSUMED`
- `CONSUMED_BEFORE_ENTRY`
- `AMBIGUOUS_MULTIPLE_DOL`
- `UNRESOLVED`

#### `PROTECTED_SWING_STATE`
At minimum:
- `STRUCTURALLY_PROTECTED`
- `RETESTED_BUT_INTACT`
- `WEAKENED`
- `INVALIDATED_BEFORE_ENTRY`
- `AMBIGUOUS`

---

## 4. Frozen observation timestamps

For the 12-trade autopsy, CIBO must reconstruct market state at these exact decision points:

1. `D1_C2_START`
2. `D1_C2_CLOSE`
3. `H4_C2_START`
4. `H4_C2_CLOSE`
5. `ENTRY`
6. `FIRST_FAVORABLE_EXCURSION`
7. `FIRST_ADVERSE_EXCURSION`
8. `EXIT`

Only observations from timestamps 1–5 may be used when asking whether a state could have distinguished trades **before entry**.

Observations 6–8 are outcome/transition evidence only and cannot be back-projected into entry logic.

---

## 5. Mandatory failure archetypes

CIBO must be able to distinguish, or explicitly return `UNRESOLVED`, for:

1. `VALID_RAID_NO_DELIVERY_CHANGE`
2. `REACTION_WITHOUT_PERSISTENCE`
3. `CISD_WITHOUT_PERSISTENCE`
4. `DOL_ALREADY_CONSUMED_OR_WRONG`
5. `PROTECTED_SWING_NOT_STRUCTURALLY_PROTECTED`
6. `ENTRY_DURING_COUNTER_DELIVERY_RETRACEMENT`
7. `EXPANSION_ALREADY_SPENT_BEFORE_ENTRY`
8. `LIQUIDITY_ACCEPTANCE_NOT_REJECTION`
9. `HTF_LTF_DELIVERY_CONFLICT`
10. `AMBIGUOUS_MARKET_STATE`

No failure archetype may be assigned merely because the trade lost.

---

## 6. Anti-hindsight governance

The following are prohibited:

- deleting GBPJPY because the three hard stops occurred there;
- deleting LONG because the hard-stop cluster was LONG;
- making session/hour a binary filter from consumed results;
- selecting stop buffer from winner/loser medians;
- selecting reclaim depth, CISD latency, DOL rank, target R, or sweep depth from consumed P&L;
- treating CIBO BANK/LOCK/ATTACK labels as causal simply because one state had higher historical P&L;
- using post-entry state transitions to justify an entry-time rule;
- reusing R5 2016–2018 as fresh validation;
- treating the 189,579-event FX atlas as fresh economic evidence.

Any new mechanic requires a new identity and preregistration.

---

## 7. Current consumed clues — explicitly NOT rules

### Clue A — D1 full-C1 traversal before entry
In the exact R5 × Behavior Lab attribution:
- gross winners: 5/5;
- gross losers: 3/7;
- hard stops: 0/3.

Status: `E1_ASSOCIATION_EXPLORATORY`.

This must not be hard-coded. CIBO must explain what market-state transition this traversal represents and test a falsifiable prediction on independent evidence.

### Clue B — reclaim saturation
- D1 reclaim: 12/12.
- H4 reclaim: 12/12.

Therefore reclaim presence alone cannot explain winner/loss separation in R5.

### Clue C — H4 FVG saturation
- H4 FVG present: 12/12.

Therefore FVG presence alone cannot explain the R5 split.

### Clue D — hard-stop concentration
The three hard stops explain essentially all gross damage in the R5 holdout.

Status: forensic target only. No symbol/side deletion is authorized.

---

## 8. Statistical requirements

Any E1/E2/E3 analysis must include where feasible:

- sample count;
- event prevalence;
- rate/effect difference;
- block-bootstrap confidence interval by day;
- symbol stability;
- side stability;
- D1/H4/H1 stability;
- year/quarter stability;
- leave-one-symbol-out;
- leave-one-quarter-out;
- minimum-sample warning;
- normalized outcomes using source-range units, not raw ticks across asset classes.

Cross-asset comparisons must not use raw ticks directly.

---

## 9. Hypothesis registry contract

Every causal hypothesis must be entered into `HYPOTHESIS_REGISTRY.json` before independent testing.

Required fields:

```json
{
  "hypothesis_id": "CIBO_TS_H001",
  "title": "...",
  "evidence_tier": "E2_CAUSAL_HYPOTHESIS",
  "source_evidence_ids": ["..."],
  "mechanism": "...",
  "pre_entry_variables": ["..."],
  "prediction": "...",
  "falsifier": "...",
  "independent_test_evidence": null,
  "status": "PREREGISTERED"
}
```

A hypothesis without a falsifier cannot be promoted to E2.

---

## 10. Promotion gates

### E1 → E2
Requires:
- source/market mechanism;
- no post-entry variable dependence;
- explicit falsifier;
- preregistered independent test.

### E2 → E3
Requires:
- independent evidence;
- preregistration SHA;
- replicated directional effect;
- stability report;
- no silent parameter change.

### E3 → E4
Requires:
- separate candidate identity;
- owner approval;
- pre-economic freeze;
- fresh holdout;
- independent final validation.

---

## 11. Deliverables

1. Machine-readable CIBO diagnostic schema.
2. 12-trade CIBO state ledger.
3. Winner / loser / hard-stop comparison.
4. Population replication over Behavior Lab events.
5. Stability matrix.
6. `HYPOTHESIS_REGISTRY.json`.
7. Counterexample ledger.
8. Immutable hashes and git-SHA binding.
9. Final report separating E0/E1/E2/E3 findings.

---

## 12. Authority

This work cannot authorize execution.

```text
DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
```

No merge and no operating-policy promotion without explicit owner authorization.
