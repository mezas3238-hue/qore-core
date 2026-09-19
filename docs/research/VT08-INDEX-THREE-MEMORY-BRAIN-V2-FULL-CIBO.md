# VT08 Index — Three-Memory Brain V2 / Full CIBO

## Status

Research-only memory architecture.

V2 upgrades the Market Memory domain from the compact 12-market Matrix view to
the official full CIBO index dossiers. It does not change the frozen VT08 V7
strategy and does not change the VT08-specific Trader Experience evidence.

## Three independent memory domains

### 1. Strategy Identity Memory

Frozen source of truth:

- candidate: `VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001`
- economic freeze SHA: `c37412c877f2fda8b32bda652b6bc74663159761`
- fingerprint:
  `a7f3b7afa3a98bfcb4daad1595762ce3925000fb256e2cbd2db84b8ec80b1308`

CIBO may reason around this strategy identity. It may not rewrite it
retrospectively.

### 2. Full CIBO Market Memory

Official package:

- identity: `CIBO_INDEX_MARKET_INTELLIGENCE_DOSSIER_V1`
- run: `35300432246`
- git SHA: `3ee6b4786ce42bbfcdbd3a3f3572d3f485cd7165`
- artifact: `10529467508`
- digest:
  `sha256:604a7d324842b46874179a39567b2cc982e03564ac18bfb3046f8e511dfe6a72`

The package is independent of VT08 outcomes.

Combined index evidence:

- 2,095,377 retained M5 bars;
- 322,675 behavior episodes;
- 108,558 resolved departures.

Per market:

- NAS100: 701,457 M5 / 110,471 episodes / 39,060 departures;
- SP500: 693,064 M5 / 102,863 episodes / 31,445 departures;
- US30: 700,856 M5 / 109,341 episodes / 38,053 departures.

Each Market Memory contains:

- Matrix behavior dimensions;
- Market Journey;
- Structure Touch;
- Departure Timing;
- Pre-Departure Sequence;
- Daily Path;
- Target Destination V1;
- Target Destination V2;
- cross-index associations;
- explicit knowledge gaps;
- source runs, artifacts and hashes.

Evidence remains `E1_ASSOCIATION_ONLY`.

### 3. VT08 Trader Experience Memory

Official VT08-specific experience package:

- run: `35288271920`;
- artifact: `10526040777`;
- 2,294 VT08-market interactions.

Per market:

- NAS100: 761;
- SP500: 747;
- US30: 786.

This memory contains the history of VT08 applying its own methodology to each
market. It is stored separately from general market knowledge.

## Governed memory layout

The V2 store contains:

- 1 Strategy Identity `SEMANTIC` memory;
- 3 full per-index `MARKET` memories;
- 1 full cross-index `MARKET` memory;
- 3 per-index VT08 `TRADER` memories;
- 1 cross-index VT08 `TRADER` memory;
- 2 immutable `LONG_TERM_ARCHIVE` records;
- 1 `RESEARCH` limitations record.

General market facts are explicitly tagged as not conditioned on VT08 outcomes.

## Situation Model V2

The Situation Model is assembled before any future trading decision.

It has direct access to:

- frozen strategy identity;
- full market dossier for the selected symbol;
- full cross-index market context;
- VT08-specific market experience;
- VT08-specific cross-index experience.

Supported pre-decision lookups include the existing causal/context dimensions
where retained evidence exists, including:

- side;
- session;
- weekday;
- previous-body alignment;
- FVG-after-raid state;
- H4 anchor;
- VT08 model family;
- VT08 POI family;
- prior-H4 range regime.

Unknown dimensions remain unknown.

## Not implemented by V2

V2 does not yet select:

- ENTER / WAIT / ABSTAIN reasoning policy;
- target depth;
- position-management state;
- contextual trailing;
- structural rearm;
- specialist admission;
- fresh holdout candidate.

Those require separate Trader Experience forensics and structural capacity
research.

## Governance

```text
FULL_CIBO_MARKET_MEMORY=true
MARKET_MEMORY_EVIDENCE_TIER=E1_ASSOCIATION_ONLY

REASONING_POLICY_SELECTED=false
TARGET_DEPTH_POLICY_SELECTED=false
POSITION_POLICY_SELECTED=false
CONTEXTUAL_TRAILING_POLICY_SELECTED=false
STRUCTURAL_REARM_POLICY_SELECTED=false

SPECIALISTS_FROZEN=false
FRESH_HOLDOUT_OPENED=false

DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
```

No statistic in the full market dossier automatically becomes a VT08 trading
rule.
