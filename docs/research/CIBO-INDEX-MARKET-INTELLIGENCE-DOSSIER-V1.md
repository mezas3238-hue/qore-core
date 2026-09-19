# CIBO Index Market Intelligence Dossier V1

## Purpose

Build a full, market-first CIBO memory package for the three index markets used by
VT08:

- NAS100
- SP500
- US30

This package is intentionally independent of VT08 trade outcomes. It is the
general market-memory layer that complements, but must never be confused with,
the VT08-specific Trader Experience Memory.

## Canonical evidence

### CIBO 12-Market Intelligence Matrix V1

- run: `35235739642`
- git SHA: `0bb28ade6d66de32dfb5390b2c66d318159ad082`
- artifact: `10503960571`

### CIBO Market Atlas Journey 10Y V1

- run: `35175979474`
- git SHA: `9cc0f17a2f30846d61b242132547f39391909656`

Index Journey artifacts:

- NAS100: `10479150314`
- SP500: `10479255223`
- US30: `10478955724`

### CIBO Market Atlas Target Destination V2

- run: `35204892665`
- git SHA: `2f510461b3360e91d5ee70a72716a76cd6561f16`

Index Target V2 artifacts:

- NAS100: `10489955740`
- SP500: `10489343403`
- US30: `10489104194`

### CIBO Market Journey Summary V1

- run: `35200408430`
- git SHA: `2bdd2fb3e050322fea49b2030e6844e3c9a1f289`
- artifact: `10487577113`

## Market populations

| Market | Retained M5 | Behavior events | Resolved departures |
|---|---:|---:|---:|
| NAS100 | 701,457 | 110,471 | 39,060 |
| SP500 | 693,064 | 102,863 | 31,445 |
| US30 | 700,856 | 109,341 | 38,053 |

These are general CIBO market observations, not VT08 trades.

## Dossier sections

Each market dossier retains summaries derived from the immutable underlying
ledgers while preserving the source artifact references and hashes:

- full Matrix detail;
- Journey manifest and population;
- Market Journey;
- Structure Touch;
- Departure Timing;
- Pre-Departure Sequence;
- Daily Path;
- Target Destination V1;
- Target Destination V2;
- cross-index Journey associations;
- explicit knowledge gaps;
- provenance and governance.

The retained source ledgers remain authoritative for row-level evidence. The
dossier does not replace them.

## Epistemic constraints

Automatic evidence tier remains:

`E1_ASSOCIATION_ONLY`

The package does not:

- promote a market association to a VT08 rule;
- select a target;
- select a stop;
- select a session;
- select a side;
- select a specialist;
- establish a causal cross-index leader;
- claim Target V2 contains every possible DOL;
- use VT08 PnL to define general market behavior.

## Known gaps

The dossier preserves these limitations instead of filling them with guesses:

- universal Order Block / Breaker / FVG chronology is not complete;
- dedicated equal-liquidity chronology is not complete;
- generic regime thresholds are not frozen;
- Target Destination V2 is a supported reference universe, not all DOLs;
- nearest-departure cross-index matching is association, not causal leadership;
- the general Market Atlas contains no trader decision stream.

## Relationship to VT08 Three-Memory Brain

After this package is built and validated, the VT08 Three-Memory Brain must use
these full dossiers as its per-index `MARKET` memory.

VT08-specific dossiers remain separate `TRADER` memory.

Therefore:

```text
Strategy Identity Memory
        +
Full CIBO Market Intelligence Dossier
        +
VT08 Trader Experience Memory
        =
VT08 Situation Model input
```

The Situation Model still has no trading authority at this stage.

## Governance

```text
RULE_PROMOTION_ALLOWED=false
DEMO_ELIGIBLE=false
LIVE_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
FRESH_HOLDOUT_OPENED=false
```

The one-year fresh holdout remains sealed.
