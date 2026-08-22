# QORE-UMI14-EVENT-CONTRACT-SEMANTICS-001

## Status

**PROGRAM D / UMI-14 — LANE 11 / UMI13-UNR-014 — PREPARATORY CORRECTION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracker: #396  
Parent audit: #363  
Starting certified baseline: `39e1598e91c912f473f9628c3aab30fe7b9cc034`

This artifact closes only the bounded static D04 event-contract definition and
resolution-terms gap. It does not observe or adjudicate an event, calculate a current
probability, execute orders, settle cash, determine legality, enable Production or
open real capital.

## 1. Evidence boundary

Exact QORE baseline evidence:

- UMI-13 architecture blob: `ec51c900c2701f885053141601a7792cdf74856e`;
- canonical unresolved entry:
  `UMI13-UNR-014 — event-resolution / outcome authority — binary payoff shape != authoritative resolution`.

Exact-baseline repository searches did not identify a dedicated static event-contract
resolution owner. That mechanical result was not treated as sufficient by itself.

Primary external evidence used for financial falsification is current CFTC event-contract
guidance and 2026 CFTC product-term filings. Those materials show that event contracts
require contractual payout terms plus rules for how settlement is determined, who
makes the determination, which source controls, and how corrections/source conflicts
are handled. CME prediction-market material independently confirms that terminal event
payout can be a fixed binary amount while rulebook/resolution semantics remain
separate.

## 2. Adjudication

`VERIFIED MATERIAL D04 GAP — BOUNDED CORRECTION REQUIRED`

Surviving material collisions:

1. identical binary payout shape with different event criterion/question;
2. identical criterion with different contracted resolution source;
3. primary source vs fallback source priority;
4. different correction policies;
5. different source-conflict policies;
6. binary yes/no vs another explicit outcome taxonomy;
7. outcome code != observed/resolved outcome;
8. scheduled resolution date != actual resolution timestamp;
9. contractual payout != settlement mutation.

## 3. Candidate inventory

The candidate adds:

- `EventContractTermsId`;
- `EventEvidenceRef`;
- `EventSubjectReferenceId`;
- `EventResolutionAuthorityRef`;
- `EventCriterionCode`;
- `EventOutcomeStructureCode`;
- `EventOutcomeCode`;
- `EventResolutionSourceCode`;
- `EventResolutionRuleCode`;
- `EventCorrectionPolicyCode`;
- `EventSourceConflictPolicyCode`;
- `EventCashPayout`;
- `EventOutcomeTerms`;
- `EventResolutionTerms`;
- `EventContractTerms`.

UMI-02 `EconomicIdentityId` is reused for the contract instrument and payout currency.
No economic identity is created or mutated here.

## 4. Event definition boundary

`EventContractTerms` retains only static product material:

- event-contract terms ID;
- instrument economic identity;
- opaque event-subject reference;
- event criterion/rule code;
- outcome-structure code;
- at least two explicit unique outcomes;
- optional expiration date;
- static resolution terms;
- evidence reference.

The subject reference is deliberately opaque. It is not a URL, provider symbol,
scraping key, API identifier or current-event-state source.

Different criteria with identical payouts remain different contracts.

## 5. Outcome and payout semantics

Each `EventOutcomeTerms` retains:

- an explicit typed outcome code;
- a non-negative finite contractual cash payout;
- payout currency economic identity.

Zero payout is valid. The owner does not impose a universal complementary-payout law,
a universal `$1/$0` law, or a universal same-currency rule across all possible event
contracts. Those would be stronger universal claims than the evidence supports.

At least two outcomes are required, but the owner is not restricted to binary
contracts. A three-or-more-outcome contract can preserve its explicit taxonomy without
being translated into multiple synthetic binaries.

`OUTCOME CODE != RESOLVED OUTCOME`

No field stores a current/resolved outcome, resolution timestamp, vote count, score,
weather measurement or other observed event state.

## 6. Resolution authority and source precedence

`EventResolutionTerms` retains:

- opaque contracted resolution-authority reference;
- ordered, non-empty primary resolution-source codes;
- ordered optional fallback source codes;
- resolution-rule code;
- correction-policy code;
- source-conflict-policy code;
- optional scheduled resolution date.

Primary and fallback collections are exact tuples. Duplicates are rejected and the two
sets must be disjoint. Order is preserved as contractual material because source
precedence can affect resolution.

The authority reference is contractual metadata only. It is not a legal-person registry,
credential, API connection or adjudication capability.

`SOURCE REFERENCE != DATA FETCH`

`RESOLUTION TERMS != RESOLVED OUTCOME`

D05 owns observed external evidence and any retained authoritative resolution
observation. This D04 owner merely preserves what the contract says should control.

## 7. Correction and source-conflict policies

Correction and source-conflict policy codes are explicit typed contract terms so that
contracts which use the same source but differ on post-publication corrections or
conflicting-source treatment do not collapse into one representation.

The codes do not execute those policies. There is no source fetch, polling, parser,
conflict adjudication, retry loop or scheduler in this owner.

## 8. Time boundary

Expiration and scheduled resolution are optional exact dates. When both are supplied,
scheduled resolution cannot precede expiration and may equal it.

No current clock is consulted. The scheduled date does not assert when the event was
actually resolved.

`SCHEDULED RESOLUTION DATE != ACTUAL RESOLUTION TIME`

D06 retains current clock/calendar/deadline authority.

## 9. Authority map

| Material | Authority |
|---|---|
| Instrument/economic identity | UMI-02 / D04 |
| Static event criterion, outcomes, payout and resolution terms | this bounded D04 owner |
| Observed event/source evidence and retained resolution observation | D05 |
| Current deadlines/calendars/time | D06 |
| Probability, market price, valuation methodology/results | D07 |
| Current positions/exposure | D08 / D09 |
| Order/execution | D10 |
| Cash/position settlement mutation | D11 |
| Legality/eligibility/regulatory determination | D22 |

## 10. Fail-closed invariants

- explicit UUID-backed owner IDs; no implicit identity generation;
- typed economic identity for instrument and payout currency;
- canonical bounded lowercase codes;
- payout amount must be finite and non-negative;
- outcomes are an exact tuple of at least two typed entries;
- outcome codes are unique;
- primary resolution sources are non-empty, ordered, typed and unique;
- fallback sources are ordered, typed and unique;
- primary/fallback source sets are disjoint;
- authority/rule/correction/conflict values are typed;
- expiration/scheduled resolution dates are exact `date` values;
- scheduled resolution does not precede expiration when both exist;
- frozen/slotted deterministic values;
- deterministic `logical_values()`;
- no wall clock, UUID generation, random state, secret/provider material or current
  outcome field.

## 11. Explicit exclusions

This candidate implements no:

- event scraping, feed or exchange/provider API;
- current event state;
- current probability or market price;
- vote/score/weather/election parser;
- event adjudication engine;
- source-conflict execution;
- source-correction execution;
- realized/resolved outcome state;
- order/execution;
- settlement/cash/position mutation;
- portfolio/risk calculation;
- legal/regulatory eligibility engine;
- UMI-12 conformance-harness mutation;
- productive Cloud or real-capital authority.

## 12. Gate discipline

This candidate is preparatory because Lane 3 / PR #376 remains the integration-order
gate.

Required eventual sequence:

`PREPARATORY CANDIDATE -> EXACT-HEAD CI -> FREEZE -> WAIT FOR PRECEDING LANES -> SYNC TO NEW CERTIFIED MAIN -> NEW EXACT SHA -> FULL CI -> INDEPENDENT REVIEW -> INTEGRATION GATE -> EXPECTED-HEAD MERGE -> POST-MERGE CERTIFICATION`

`BINARY PAYOFF SHAPE != AUTHORITATIVE RESOLUTION`

`CI GREEN != ENGINEERING APPROVAL`

`NO INDEPENDENT EXACT-HEAD REVIEW -> NO MERGE`

`NO LANE-ORDER BYPASS`
