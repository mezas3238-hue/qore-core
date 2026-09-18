# QORE CORE — ICT TURTLE SOUP × CIBO HOLDOUT FAILURE ATTRIBUTION V1

**Status:** CONSUMED DIAGNOSTIC EVIDENCE ONLY  
**Identity:** `ICT_TS_CIBO_HOLDOUT_FAILURE_ATTRIBUTION_V1`  
**Parent:** `ICT_TS_CIBO_DIAGNOSTICS_V1`  
**Tracker:** Issue #600  
**Repository:** `mezas3238-hue/qore-core`

## 0. Purpose

Couple the authoritative R5 holdout outputs to the original R5 market evidence so CIBO can determine, trade by trade, where the observed failure occurred:

- entry timing/state;
- protected-swing / stop placement and subsequent behavior;
- primary DOL / target selection and subsequent behavior.

This is diagnostics, not optimization. No result from the consumed holdout may directly alter a trader.

## 1. Frozen evidence

### R5 holdout
- Run `35118222306`
- HEAD `9beb2f8147db2b9fb780bc4cc28e2cdb05b7851e`
- Holdout `ICT_TS_R5_FRESH_2016_2018`
- Aggregate trades: 12
- Seven per-market artifacts contain the original read-only `market-evidence.json` M5 histories.

### Behavior Lab
- Run `35125861002`
- HEAD `4d09a43aa5795624b4a7cb29bb2503ae586c5a4f`
- Population: 189,579 consumed FX liquidity-raid events.

### Existing exact linkage
- 12/12 exact D1 prior-candle C2 matches.
- 12/12 exact H4 prior-candle C2 matches.
- No fuzzy date/session matching.

## 2. Required output per trade

CIBO must emit all of the following separately:

```text
ENTRY_CONTRACT_ASSESSMENT
ENTRY_MARKET_STATE_ASSESSMENT
STOP_CONTRACT_ASSESSMENT
STOP_BEHAVIOR_ASSESSMENT
TARGET_CONTRACT_ASSESSMENT
TARGET_BEHAVIOR_ASSESSMENT
FAILURE_ZONE
EVIDENCE_TIER
DIAGNOSTIC_CODES
```

`FAILURE_ZONE` is diagnostic location, not an operating rule.

Allowed values:
- `ENTRY_STATE`
- `STOP_INVALIDATION`
- `TARGET_SELECTION`
- `MIXED`
- `UNRESOLVED`
- `NO_FAILURE_TARGET_EXIT`
- `NO_FAILURE_PROFITABLE_EXIT`

## 3. Entry audit

### Contract verification
For every trade, independently reconstruct from the market evidence:

1. Daily C2 is an authentic Ideal C2 under frozen R5 code.
2. H4 C2 is an authentic Ideal C2 under frozen R5 code.
3. entry timestamp is the next H4 candle open after H4 C2;
4. entry price equals that H4 C3 open;
5. H4 protected swing and one-native-tick stop exactly match the frozen R5 contract;
6. entry occurs inside the expected Daily C3.

If any contract fact does not reconstruct exactly, the diagnostic must fail closed.

### Market-state observations available before entry
Record without inventing filters:

- D1 full-C1 opposite-side traversal before entry;
- H4 full-C1 opposite-side traversal before entry;
- elapsed minutes from Daily C3 open to entry;
- favorable and adverse excursion already spent during Daily C3 before entry;
- those excursions normalized by initial risk and by target distance;
- final H4 C2 body/range geometry;
- M5 directional net movement during the final 15m, 30m and 60m before entry.

The previously observed D1 full-C1 traversal relationship remains `E1_ASSOCIATION`, not a rule.

## 4. Stop / protected-swing audit

### Contract verification
- LONG stop = H4 protected low minus exactly one native tick.
- SHORT stop = H4 protected high plus exactly one native tick.

No alternate buffer is tested.

### Behavioral classification for stopped trades
Use only the original price path after the recorded stop through the frozen Daily C3 close.

- `POST_STOP_TARGET_REACHED`: original entry and original target were both reached after stop. Strong evidence the stop fired before the thesis fully failed, but still diagnostic only.
- `POST_STOP_ENTRY_RECOVERED_ONLY`: entry was recovered after stop but target was not reached. Mixed/premature-stop evidence.
- `POST_STOP_NO_ENTRY_RECOVERY`: price did not recover original entry before Daily C3 close. Behavior supports structural invalidation more than a too-tight-stop explanation.

Also record:
- time from entry to stop;
- MFE before stop in R;
- maximum stop penetration;
- post-stop maximum favorable recovery;
- Daily C3 close relative to entry and stop.

No arbitrary ATR, pip or R threshold may be introduced.

## 5. Target / DOL audit

Independently enumerate every completed, untouched three-candle Daily swing in trade direction that existed at entry under the frozen R5 target family.

Verify:
- chosen target existed before entry;
- chosen target was untouched at entry;
- chosen target was the nearest valid R5 Daily swing in trade direction;
- `primary_dol_opened_at` matches the selected pivot;
- count of valid DOL candidates at entry;
- next farther valid DOL, if present.

Contract labels:
- `TARGET_CONTRACT_CORRECT_SINGLE_DOL`
- `TARGET_CONTRACT_CORRECT_NEAREST_OF_MULTIPLE`
- `TARGET_CONTRACT_INVALID`

The second label explicitly means *R5 selected correctly under its own contract, but dominance among multiple DOLs is not proven by source or outcome*.

### Target behavior
For target exits, record:
- additional favorable excursion after target through Daily C3 close;
- whether the next farther valid Daily DOL was reached after the first target.

For non-target exits, record:
- maximum favorable excursion as fraction of original target distance;
- whether target was reached only after the recorded exit.

No new target hierarchy may be created from these results.

## 6. Failure attribution logic

Failure attribution must separate contract correctness from market-state suitability.

### `ENTRY_STATE`
May be assigned only when:
- entry/stop/target contracts reconstruct correctly;
- stop behavior does not show the target being reached after stop; and
- consumed pre-entry observations show a market-state contradiction or incomplete delivery transition.

This remains at most E1 unless independently replicated.

### `STOP_INVALIDATION`
May be assigned only when:
- entry and target contracts reconstruct correctly; and
- post-stop trajectory recovers the entry and/or target, providing direct evidence that the protected-swing stop may have invalidated too early.

### `TARGET_SELECTION`
May be assigned only if the target contract itself fails reconstruction or the target was already consumed before entry. A target being missed is not enough.

### `MIXED`
Used when evidence supports more than one failure zone.

### `UNRESOLVED`
Required whenever evidence cannot distinguish the above.

### `NO_FAILURE_TARGET_EXIT` / `NO_FAILURE_PROFITABLE_EXIT`
Used when the recorded trade was not an economic failure. These labels do not certify entry quality; they only prevent profitable outcomes from being mislabeled as failure cases.

A losing trade must never receive a failure code merely because it lost.

## 7. Aggregate questions CIBO must answer

1. Were the 12 entries contract-correct?
2. Among the three hard stops, did price subsequently recover entry and/or target?
3. Does the stop evidence support “too tight”, “valid invalidation”, or mixed behavior?
4. Were all 12 R5 targets contract-correct and untouched at entry?
5. How often were multiple valid Daily DOLs present at entry?
6. For target winners, how often did delivery continue beyond the selected DOL?
7. Does evidence place the dominant observed problem before entry, at protected-swing invalidation, at target selection, or remain unresolved?

## 8. Anti-hindsight rules

Prohibited:
- changing the R5 entry after observing outcome;
- changing stop buffer;
- deleting GBPJPY or LONG;
- ranking DOLs by historical P&L;
- creating an entry threshold from the 12 trades;
- using post-entry observations as if they were known at entry;
- promoting any diagnostic finding directly into CIBO operating policy.

## 9. Evidence and authority

All outputs are `CONSUMED_DIAGNOSTIC_ONLY`.

```text
DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
```

Any mechanism promoted beyond E1 requires preregistration and independent evidence under a new identity.