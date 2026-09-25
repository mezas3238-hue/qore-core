# VT08 CRT PURE — Cognitive Experience WFO Freeze 001

**PR:** #626  
**Status:** preregistered before R2-BY / R2-BZ economic result inspection  
**Markets:** AUDUSD, USDJPY  
**Governance:** research only

## Purpose

Use the already-frozen CRT PURE cognitive architecture as an actual decision
layer instead of continuing to add static selection filters.

The experiment does not alter CRT methodology.

## Immutable cognitive authority

Final action is generated only by:

`qore.infrastructure.traders.crt_pure_cognitive_state.reason()`

Permitted actions:

- EXECUTE
- WAIT
- ABSTAIN

The cognitive layer cannot:

- rewrite Strategy Identity;
- see future labels at decision time;
- change target or stop;
- create a new CRT signal;
- bypass confirmation;
- grant capital authority;
- resurrect a killed hypothesis;
- bypass ABSTAIN with fallback on the same source event.

## Market-specific Experience Memory

Each market learns only from its own preceding 4Y window.

### AUDUSD — R2-BY

State:

`REF_DELAY_DIRECTION`

Labels learned in training:

1. shrunken Expected-R;
2. shrunken dead-on-arrival rate.

### USDJPY — R2-BZ

State:

`REF_DELAY_OVERLAP`

Labels learned in training:

1. shrunken Expected-R;
2. shrunken dead-on-arrival rate.

No AUDUSD state/outcome is transferred to USDJPY and vice versa.

## Frozen epistemic mapping

For a supported cell:

### KNOWN

- Expected-R > 0;
- DOA rate < training baseline DOA.

Cognition receives no contradiction or uncertainty.

### CONFLICTED

- Expected-R <= 0;
- DOA rate >= training baseline DOA.

Cognition receives hard contradiction:

`EXPERIENCE_NEGATIVE_R_AND_HIGH_DOA`

### PARTIAL

One of the two axes is favorable and the other is not.

Cognition receives uncertainty:

`EXPERIENCE_MIXED_R_DOA_EVIDENCE`

### UNKNOWN

Cell support below the existing minimum support.

Cognition receives uncertainty:

`EXPERIENCE_CELL_UNRESOLVED`

No numeric confidence is invented.

## Frozen learning parameters

- prior training window: 4 years;
- OOS window: next 1 year;
- minimum cell support: 30;
- empirical-Bayes prior strength: 100;
- no threshold search after results.

## Decision mapping

The experiment does not directly map memory to a trade.

It creates a causal `CrtPureSituationModel` and calls the frozen cognitive
reasoner.

Expected behavior from the frozen reasoner:

- KNOWN + complete source-valid evidence -> EXECUTE;
- PARTIAL / UNKNOWN -> WAIT;
- CONFLICTED -> ABSTAIN.

## Evaluation

Report separately:

- action counts;
- EXECUTE trades/year;
- PF;
- Total-R;
- max DD;
- DOA rate;
- 0.02R and 0.05R cost stress;
- positive OOS-year fraction.

A reduction in stop/DOA is not sufficient if density or post-cost economics
collapse.

No automatic promotion.

No merge / VPS / DEMO / LIVE / production / real capital.
