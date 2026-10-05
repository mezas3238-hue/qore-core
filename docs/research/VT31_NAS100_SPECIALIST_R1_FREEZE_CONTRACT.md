# VT31_NAS100_SPECIALIST_R1 — Freeze Contract

Status: SUPERSEDED FOR CERTIFICATION / HOLDOUT SEALED

This identity supersedes the old pre-intelligence `VT31_NAS100_R1` candidate
for the current NAS100 specialist research program. It does not inherit the old
candidate fingerprint.

## Governance

- Research branch / PR #610 only.
- No merge without Owner instruction.
- No live, production or real-capital authority.
- The sealed NAS100 interval `[2015-04-19, 2016-04-19)` remains unopened.
- The holdout may be opened exactly once only after the implementation,
  development WFO, focused validation, static validation, Full QORE and exact
  SHA/config fingerprint freeze are all green.
- Opening permanently consumes the interval.
- No post-open retuning may be evaluated against the same interval as fresh.

## Methodology retained

Silver Bullet / VT31 remains the trading methodology:

```text
09:00-10:00 NY frozen reference
→ strict first-side liquidity raid
→ both-sides-swept fail closed
→ post-raid structural close
→ source-valid FVG / Breaker / Order Block
→ versioned R2.2 execution translation
```

## NAS100 specialist intelligence

### Three persistent memories + causal Situation Model

VT31 does **not** consult CIBO at runtime.

The specialist carries exactly three persistent governed memories:

1. **Strategy / Identity Memory** — what VT31 is, what AM Silver Bullet looks
   for, source-valid setup families, methodological invalidation and lifecycle.
   Market statistics and PnL cannot rewrite this memory retrospectively.
2. **CIBO NAS100 Market Memory** — the governed NAS100 market dossier retained
   in `CiboMemoryStore`, including the full dossier as
   `LONG_TERM_ARCHIVE` plus MARKET/RESEARCH sections with provenance,
   evidence refs, freshness and association-only limitations.
3. **VT31_NAS100 Trader Experience / Lab Memory** — consumed lessons from
   VT31 interacting with NAS100: supported mechanisms, rejected hypotheses,
   loss/journey/capacity forensics and unresolved warnings.

The **Market Situation Model** is separate. It is ephemeral and rebuilt from
causal market evidence at every observation/reasoning timestamp.

Runtime architecture:

```text
STRATEGY / IDENTITY MEMORY
        +
CIBO NAS100 MARKET MEMORY
        +
VT31 NAS100 EXPERIENCE MEMORY
        +
CURRENT CAUSAL SITUATION MODEL
        ↓
REASONING ENGINE
        ↓
THESIS / SUPPORT / CONTRADICTIONS / UNCERTAINTY
        ↓
EXECUTE / WAIT / ABSTAIN
        ↓
STOP / DOL / TARGET-DEPTH / MANAGEMENT
        ↓
STRUCTURAL REARM
```

There is no CIBO API call, no date-level historical outcome lookup and no
mutable online rewriting of the three persistent memories. A memory revision
requires explicit research, revalidation and a new fingerprint.

The candidate reconstructs its intelligence from **closed NAS100 M1 bars only**.
It does not query a CIBO ledger by date and it does not require SP500/US30 data.

CIBO Atlas is the historical learning source that motivated and validated the
state representation. Runtime state is rebuilt causally.

The source-valid setup is executable only when all of these are true:

1. the most recent causally observable CIBO-equivalent structure event is a
   `reference-liquidity-sweep`;
2. the current NY path through the decision is compressed below `0.75x` the
   previous admitted NY day's 00:00-16:00 range;
3. the decision occurs before 10:30 NY **inside this specific compressed
   reference-sweep state**; this is not a global fixed entry time;
4. the first source-reference reclaim is not in the previously identified
   8-14 minute stale state.

Otherwise the candidate abstains.

## Stop intelligence

Initial invalidation remains the source-methodological swing extreme, with no
arbitrary point buffer and no retrospective widening.

```text
STOP = price where the source reversal hypothesis is structurally invalid
```

No M1 protected-swing trailing is allowed.

## Target / management intelligence — superseded rule

The former R-driven management policy in this contract is **not eligible for
certification** under the Owner's sovereign pure-edge rule.

The active certification boundary is:

```text
primary destination = opposite frozen 09:00 structural boundary
initial invalidation = source structural invalidation
runtime R target = prohibited
runtime R breakeven = prohibited
runtime R trailing = prohibited
runtime R partial exit = prohibited
```

Any future extension beyond the primary boundary must be derived from causal
market-native evidence such as:

- structural acceptance;
- liquidity continuation/failure;
- confirmed exhaustion;
- regime change;
- momentum deterioration;
- confirmed protective structure.

R may be calculated only as post-trade evaluation.

Canonical sovereign rule:

`docs/research/VT31_NAS100_SOVEREIGN_PURE_EDGE_CERTIFICATION_RULE.md`

This supersession does **not** open the holdout. A new exact pure-edge candidate
fingerprint must be frozen before any one-shot holdout is authorized.

## Causal firewall

Runtime-prohibited:

- future bars;
- date-level CIBO outcome lookup;
- final departure lookup;
- objective-reached lookup;
- post-boundary extension lookup;
- terminal result lookup;
- post-hoc winning-date selection.

The decision trace must explain:

```text
market state
sequence freshness
latest structure event
compression state
decision timing
entry / abstention
structural stop
reference-volatility state
target plan
management plan
```

## Development gates before freeze

Each consumed R8/R6/R5 fold must independently satisfy, under -0.05R/trade:

- terminal sample >= 30;
- mean R > 0;
- PF >= 1.15;
- max DD <= 20R;
- max losing streak <= 15;
- 10k moving-block Monte Carlo positive terminal probability >= 0.70;
- Monte Carlo p95 max DD <= 20R.

Cross-fold temporal stability must additionally be checked before freeze.

## Holdout

The holdout boundary remains:

```text
market: NAS100
start: 2015-04-19T00:00:00Z
end-exclusive: 2016-04-19T00:00:00Z
```

Until an immutable freeze artifact exists:

```text
VT31_NAS100_SPECIALIST_R1 = SUPERSEDED_FOR_CERTIFICATION
NAS100_1Y_FRESH_HOLDOUT = SEALED
LIVE_AUTHORIZED = FALSE
PRODUCTION_AUTHORIZED = FALSE
```
