# VT08 CRT PURE — R2-E SOURCE MULTIPLICITY CENSUS 001

**Identity:** `VT08_CRT_PURE_R2E_SOURCE_MULTIPLICITY_CENSUS_001`  
**Workflow run:** `35808707583`  
**Evidence HEAD:** `91f4de134bbfe22f445bdc1ed600d24aa0a215ca`  
**Status:** CHARACTERIZATION COMPLETE / NO ENTRY PROMOTION  
**Methodology mutated:** FALSE  
**Trades created:** 0  
**PnL evaluated:** FALSE

## 1. Question

R2-C imposed an engineering control:

`single_source_event_per_parent = true`

When the first direction-aligned close-unmitigated Model #1 source did not obtain
body-close confirmation, the parent stayed WAIT and no later source was considered.

R2-E asks only:

> Do those WAIT parents contain later, independently emitted direction-aligned
> Model #1 source events, and do any of those later events confirm causally?

It does not trade them.

## 2. Causal safeguards

R2-E reuses the frozen R2-C close-unmitigated breach builder.

A later event therefore:

- exists only after its own source candle appears;
- comes from the already-causal old-level ledger;
- is direction-aligned with the parent CRT;
- is measured separately from the first source;
- is checked for body-close confirmation;
- is checked for a next contiguous M15 bar;
- is not automatically treated as rearm or entry;
- does not alter R1/R2-A/R2-B/R2-C.

No PnL is computed.

## 3. Quality

Run `35808707583`:

- quality: SUCCESS
- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- AUDUSD census: SUCCESS
- USDJPY census: SUCCESS
- BTCUSD census: SUCCESS

The Cognitive Gate on the implementation HEAD also completed SUCCESS.

## 4. AUDUSD

R2-C WAIT parents: **128**

- with later aligned source: **96**
- without later aligned source: **32**
- with two or more later sources: **66**
- total later source events: **217**
- with at least one later body confirmation: **55**
- with at least one later executable confirmation: **46**

Later event states:

- executable confirmations: **67**
- body-confirmed but no next bar: **10**
- no body confirmation: **140**

Temporal split:

- Year 1: 72 WAIT; 54 with later source; 26 with later executable confirmation
- Year 2: 56 WAIT; 42 with later source; 20 with later executable confirmation

## 5. USDJPY

R2-C WAIT parents: **121**

- with later aligned source: **91**
- without later aligned source: **30**
- with two or more later sources: **60**
- total later source events: **213**
- with at least one later body confirmation: **41**
- with at least one later executable confirmation: **37**

Later event states:

- executable confirmations: **48**
- body-confirmed but no next bar: **10**
- no body confirmation: **155**

Temporal split:

- Year 1: 64 WAIT; 52 with later source; 22 with later executable confirmation
- Year 2: 57 WAIT; 39 with later source; 15 with later executable confirmation

## 6. BTCUSD

R2-C WAIT parents: **181**

- with later aligned source: **152**
- without later aligned source: **29**
- with two or more later sources: **107**
- total later source events: **359**
- with at least one later body confirmation: **90**
- with at least one later executable confirmation: **82**

Later event states:

- executable confirmations: **109**
- body-confirmed but no next bar: **11**
- no body confirmation: **239**

Temporal split:

- Year 1: 90 WAIT; 77 with later source; 41 with later executable confirmation
- Year 2: 91 WAIT; 75 with later source; 41 with later executable confirmation

## 7. Combined interpretation

Combined R2-C WAIT parents: **430**

- parents with later aligned source: **339 / 430 = 78.8%**
- parents with two or more later sources: **233 / 430 = 54.2%**
- parents with at least one later executable confirmation:
  **165 / 430 = 38.4%**
- total later aligned source events: **789**
- total later executable confirmation events: **224**

No exact first-reference evidence reuse was observed in the census counters. The later
events are therefore not explained by simply replaying the exact same source reference.

## 8. Adjudication

R2-E falsifies the engineering assumption that the first aligned source is an adequate
proxy for all Model #1 opportunity structure inside C3.

It does **not** prove:

- that every later source should be traded;
- that the first source should be discarded;
- that later sources are automatically valid rearm;
- that multiple entries per parent are authorized;
- that a profitable result will follow.

The correct next question is hypothesis identity and lifecycle:

1. Can a later source event create a genuinely separate Model #1 hypothesis while the
   earlier source remains unresolved?
2. If yes, does cognition run those hypotheses concurrently through WAIT / CONFIRMED /
   ABSTAIN rather than treating the later source as a fallback?
3. What source or structural event kills the earlier hypothesis?
4. If one hypothesis confirms, what happens to competing hypotheses from the same parent?

Until that contract is explicitly frozen, R2-E remains census evidence only.

## 9. Next research identity

The next allowed experiment should not be another arbitrary technical trigger.

A valid next identity is a multi-hypothesis Model #1 characterization that:

- assigns a unique source_event_id to every independent later source;
- never revives the first hypothesis;
- never reuses the same reference evidence;
- preserves source-body confirmation;
- caps execution according to a predeclared competition rule;
- labels the competition rule as engineering unless RomeoTPT closes it;
- changes no target/stop/expiry dimension in the same experiment.

Economic evaluation must come only after the hypothesis-lifecycle contract is frozen.

## 10. Governance

- PR remains DRAFT / UNMERGED.
- No VPS mutation.
- No runtime registration.
- No DEMO activation.
- No LIVE activation.
- No production authority.
- No real-capital authority.
