# VT08 Index — Three-Memory Intelligent Brain V1

## Status

Research-only architecture foundation.

This layer implements the three-memory model for VT08 Index without changing the
frozen V7 strategy and without copying Turtle Soup/XAUUSD parameters.

## 1. Strategy Identity Memory

Source of truth:

- candidate: `VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001`
- freeze SHA: `c37412c877f2fda8b32bda652b6bc74663159761`
- rule fingerprint:
  `a7f3b7afa3a98bfcb4daad1595762ce3925000fb256e2cbd2db84b8ec80b1308`

The exact frozen V7 rule material is stored as governed `SEMANTIC` memory.

CIBO Market Memory and Trader Experience Memory may inform later reasoning, but
they may not mutate this identity retrospectively.

## 2. CIBO Market Memory

This memory is deliberately independent of VT08 outcomes.

Primary sources:

### CIBO 12-Market Intelligence Matrix V1

- run: `35235739642`
- artifact: `10503960571`
- digest:
  `sha256:0a2ddcea40054c3724e0910a7437d823c38224093699dc5d630dd2a6619b01e8`

### CIBO Market Journey Summary V1

- run: `35200408430`
- artifact: `10487577113`
- digest:
  `sha256:0394ea6e64bddf3315f331d710084441868e50182341ff13511d13c6d95abe4d`

The general CIBO corpus includes:

- 8,726,985 retained M5 bars;
- 1,425,723 Journey episodes;
- 108,558 cross-index Journey rows.

Index-specific Journey populations:

- NAS100: 110,471 episodes;
- SP500: 102,863 episodes;
- US30: 109,341 episodes.

Per-index market memory retains general market behavior such as side, session,
weekday, prior-body relationship, FVG presence, CISD/reclaim behavior,
MFE/MAE, Protected Swing distance, raid depth, temporal stability and supported
Target Destination V2 summaries.

The cross-index market memory remains E1 association only. Nearest-departure
lead/lag is not causal leadership.

## 3. VT08 Trader Experience Memory

Source:

- workflow run: `35288271920`
- artifact: `10526040777`
- digest:
  `sha256:8dc34a84aee03480fc83e76b53c476200da72751edba6d904dd6be6440ea5394`

Parent evidence:

- Semantic V2 artifact: `10525006904`;
- Complete Ledgers V1 artifact: `10479912540`.

The experience population is 2,294 VT08-market interactions:

- NAS100: 761;
- SP500: 747;
- US30: 786.

This memory contains the interaction between VT08 and each market: temporal
stability, anchor/side/model/POI/regime behavior, stop rate, post-stop later-2R
behavior, causal departure timing and A-I diagnostic taxonomy.

It is stored as `TRADER` memory and is never presented as general market truth.

## 4. Governed CiboMemoryStore

The bridge records:

- one Strategy Identity `SEMANTIC` memory;
- three index-specific general `MARKET` memories;
- one general cross-index `MARKET` memory;
- three index-specific VT08 `TRADER` memories;
- one VT08 cross-index `TRADER` memory;
- three immutable `LONG_TERM_ARCHIVE` records;
- one `RESEARCH` limitations record.

Every retained item carries explicit provenance, evidence references, freshness
and limitations.

The general Market Memory is tagged:

- `association-only`;
- `consumed-research-evidence`;
- `no-rule-promotion`;
- `not-vt08-outcome-conditioned`.

The Trader Experience Memory is tagged:

- `consumed-research-evidence`;
- `vt08-specific`;
- `diagnostic-only`;
- `no-rule-promotion`.

## 5. Situation Model

`Vt08IndexSituationModel` assembles pre-decision context from all three memory
domains.

Current supported lookup dimensions include, where known:

### Market Memory

- side;
- session;
- weekday;
- previous-body alignment;
- FVG presence after raid.

### Trader Experience Memory

- H4 anchor;
- side;
- V7 model kind;
- V7 POI kind;
- weekday;
- previous-H4 range regime.

The Situation Model also exposes the general cross-index memory and the
VT08-specific cross-index experience memory.

Unknown dimensions remain explicitly unknown.

The Situation Model does **not** output ENTER/WAIT/ABSTAIN and does not alter
entry, stop or target.

## 6. What is intentionally not implemented yet

This V1 foundation does not select:

- reasoning policy;
- target-depth policy;
- contextual trailing policy;
- structural rearm policy;
- specialist admission rules.

Those require separate forensics and causal research using the new memory
architecture. No E1 association may become an operating rule merely because it
looks favorable historically.

## 7. Known CIBO Market Atlas limitations

The stored limitations explicitly preserve the current gaps:

- universal Order Block / Breaker / FVG chronology is not complete;
- dedicated equal-liquidity chronology is not complete;
- generic regime thresholds are not frozen;
- cross-index nearest-departure matching does not establish causal leadership.

These gaps are not filled with guesses.

## 8. Governance

```text
DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
SPECIALISTS_FROZEN=false
FRESH_HOLDOUT_OPENED=false
```

The fresh one-year holdout remains sealed.

This layer changes memory architecture only. It does not change V7 economic
mechanics or promote a new candidate.
