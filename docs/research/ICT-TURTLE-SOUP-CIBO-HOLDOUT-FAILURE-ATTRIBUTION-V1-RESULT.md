# QORE CORE — ICT TURTLE SOUP × CIBO HOLDOUT FAILURE ATTRIBUTION V1 — RESULT

**Identity:** `ICT_TS_CIBO_HOLDOUT_FAILURE_ATTRIBUTION_V1`  
**Evidence status:** `CONSUMED_DIAGNOSTIC_ONLY`  
**Workflow run:** `35135524688`  
**Workflow HEAD:** `ab37e70ae0a98d491637a5b93b30889ad5ca0617`  
**Artifact:** `10462263686`  
**Artifact digest:** `sha256:4b32df662cfe1e9ccfc9961baf640b7d464b14051aa1b47e4d8ee7354c4f90b6`

## 1. Reconstruction result

CIBO reconstructed the 12 consumed R5 trades against the original seven read-only M5 market artifacts plus the frozen Behavior Lab ledger.

- Entry contract correct: **12/12**.
- Protected-swing / stop contract correct: **12/12**.
- Daily DOL target contract correct: **12/12**.
- No fuzzy linkage or alternate market history was used.

Therefore the R5 economic failure is not explained by an implementation mismatch in entry price/time, the one-native-tick PS stop rule, or the nearest untouched completed three-candle Daily swing target rule.

## 2. Hard-stop attribution

R5 produced three hard stop exits. CIBO reconstructed their post-stop trajectory through the frozen Daily C3 close:

- hard stops: **3**;
- recovered original entry after stop: **0/3**;
- reached original target after stop: **0/3**;
- `POST_STOP_NO_ENTRY_RECOVERY`: **3/3**.

This consumed evidence does **not** support the simple explanation that the one-tick-beyond-PS stop was merely too tight. In all three cases price continued sufficiently against the position that the original entry was not recovered before the Daily C3 lifecycle ended.

The stop itself was contract-correct in all three cases. The observed failure therefore lies upstream of stop execution more than in stop-buffer width.

## 3. Entry-state attribution

CIBO found an E1 pre-entry association already present in the frozen Behavior Lab:

- the three hard stops all lacked D1 full-C1 opposite-side traversal before entry;
- the previously established consumed split was 5/5 gross winners, 3/7 gross losers, and 0/3 hard stops with D1 full-C1 traversal before entry.

In the deep attribution:

- `ENTRY_STATE`: **4 trades**;
- three are the GBPJPY LONG hard stops;
- one is a small GBPJPY SHORT Daily-C3-close loss.

This is **E1_ASSOCIATION**, not a causal operating rule. It suggests that an authentic Ideal C2 can satisfy the R5 candle contract while the broader Daily repricing/delivery transition is still incomplete.

The current evidence supports the research hypothesis that R5 confirms candle structure more strongly than it confirms persistent market delivery.

## 4. Target / DOL attribution

Every recorded target reconstructed correctly under the frozen R5 rule:

- valid/untouched at entry: **12/12**;
- nearest valid completed three-candle Daily swing in direction: **12/12**;
- target contract invalid: **0/12**.

However:

- **10/12** trades had more than one valid R5 Daily DOL candidate at entry;
- both target exits (**2/2**) showed additional favorable delivery after the selected target.

Therefore the target was not *wrong under the R5 contract*, but the R5 rule `nearest valid Daily swing = primary DOL` does not prove that the selected level was the dominant market draw. Multiple valid DOLs are the normal condition in this sample, not the exception.

This generates a DOL-hierarchy research question, not permission to select farther targets retrospectively.

## 5. Trade-level failure zones

CIBO output:

- `ENTRY_STATE`: **4**;
- `UNRESOLVED`: **3**;
- `NO_FAILURE_PROFITABLE_EXIT`: **3**;
- `NO_FAILURE_TARGET_EXIT`: **2**;
- `STOP_INVALIDATION`: **0**;
- `TARGET_SELECTION`: **0**.

The three unresolved losses were:

- EURUSD LONG, Daily-C3-close, `-0.4461538462R`;
- GBPJPY SHORT, Daily-C3-close, `-0.2321428571R`;
- USDCAD SHORT, Daily-C3-close, `-0.4888178914R`.

They had correct contracts and no current E1 entry contradiction strong enough for attribution, so CIBO correctly leaves them unresolved rather than inventing a cause.

## 6. CIBO diagnosis

### Entry
**Mechanically correct: 12/12.**  
**Market-state suitability: not fully established.** Four losing trades, including all three hard stops, carry the current E1 incomplete-D1-repricing warning.

### Stop
**Mechanically correct: 12/12.**  
The three hard stops did not recover entry or target after stop. Current evidence therefore favors genuine thesis/delivery failure over a generic “stop too tight” explanation. No wider-stop rule is authorized.

### Target
**Mechanically correct: 12/12.**  
But 10/12 trades had multiple valid DOL candidates and 2/2 target winners continued beyond the nearest selected DOL. The unresolved problem is DOL dominance/hierarchy, not implementation correctness. No farther-target rule is authorized.

## 7. Current research priorities

1. Promote the D1 full-C1 traversal observation only to a preregistered **E2 causal hypothesis** after defining the mechanism and falsifier; do not hard-code it.
2. Build a source-bound / causal `PRIMARY_DOL_STATE` that distinguishes nearest valid DOL from dominant expected draw when multiple Daily pools coexist.
3. Diagnose the three `UNRESOLVED` losses using pre-entry delivery persistence, H1/H4 state transitions, and cross-market context without consulting post-entry P&L for rule selection.
4. Replicate any E2 mechanism on independent diagnostic evidence before any trader identity can use it.

## 8. Governance

```text
DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
```

CIBO authority ceiling remains `OPINION`. No merge and no operating-policy promotion is authorized by this result.