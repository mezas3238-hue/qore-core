# QORE Shared — Owner Proactive Shared↔Trader Intelligence Directive 007

**Status:** OWNER-FROZEN TRANSVERSAL EXTENSION  
**Primary PR:** #635  
**Program:** QORE Meta-Cognitive Scientific Intelligence  
**Source of truth:** GitHub  
**Relationship to Directives 004/005/006:** additive; this directive expands Shared's cognition/communication role without granting execution, capital, Risk or Trader-methodology authority.

## 1. Identity change

Shared is no longer limited to passive contextual description.

Shared evolves toward:

```text
QORE GLOBAL PROACTIVE SCIENTIFIC MARKET INTELLIGENCE
```

capable of:

```text
SEE
UNDERSTAND
RELATE
DISCOVER
ANTICIPATE
WARN
EXPLAIN
MONITOR
FALSIFY
MEASURE UNCERTAINTY
REDUCE IGNORANCE
```

Shared must detect when the world is changing, not only describe the current world.

## 2. Core authority law

Freeze:

```text
SHARED UNDERSTANDS.
SHARED DISCOVERS.
SHARED WARNS.
SHARED MONITORS.

TRADERS OPERATE.
CIBO CAPITALIZES.
RISK PROTECTS.
EXECUTION MATERIALIZES.
```

Shared may communicate a potential opportunity, regime-transition risk,
continuation support, thesis deterioration, relationship break, systemic-state
change, uncertainty spike or data-quality degradation.

None of those outputs is an order.

## 3. Sovereignty

Shared may never own or acquire:

```text
order_send
position_close
modify_stop
modify_tp
position_size
capital_allocate
risk_authorize
trade_block
trade_force
trader_methodology_mutation
```

Trader retains setup, direction, entry, entry timing, technical invalidation,
technical stop, technical target, trade thesis, re-entry, position management,
exit methodology and expiry unless a future explicit ADR transfers a bounded
authority.

CIBO owns capital deployment and sizing.

Risk retains hard survivability authority.

Execution alone mutates broker state.

## 4. Shared market hypotheses

Shared may produce cognition-only hypotheses:

```text
BULLISH_HYPOTHESIS
BEARISH_HYPOTHESIS
CONTINUATION_HYPOTHESIS
REVERSAL_HYPOTHESIS
RANGE_HYPOTHESIS
REGIME_TRANSITION_HYPOTHESIS
INSUFFICIENT
```

Binding law:

```text
MARKET HYPOTHESIS != TRADER ORDER
SHARED WORLD THESIS != TRADE THESIS
```

A Trader may reject or ignore a Shared hypothesis. Shared may contradict a
Trader setup. Neither side silently overrides the other's sovereign authority.

## 5. First-class Shared outputs

Shared shall support typed, evidence-bound forms of:

- `SHARED_OPPORTUNITY_ALERT`;
- `SHARED_REGIME_TRANSITION_ALERT`;
- `SHARED_CONTINUATION_SUPPORT`;
- `SHARED_WORLD_EXPLANATION`;
- `SHARED_POSITION_THREAT_ALERT`.

These are cognitive products, not broker instructions.

## 6. Shared→Trader intelligence contract

A canonical machine contract must exist for trader-facing Shared cognition.

Required semantic planes include:

- identity: snapshot/hypothesis/alert;
- causal time: observed-at and evidence-cutoff-at;
- canonical instrument identity;
- market family and trader horizon;
- world, market and macro state;
- rates/USD/liquidity/volatility/commodity/agricultural/cross-asset state;
- relationship coherence/stability/age;
- directional hypothesis;
- continuation/reversal/failure-hazard/positive-tail support;
- systemic stress and regime-transition state;
- contradictory and missing evidence;
- uncertainty and calibrated confidence;
- data quality/freshness;
- causal maturity;
- supporting, contradicting and provenance evidence references.

No human-readable explanation may substitute for the machine contract.

## 7. Opportunity discovery

Shared may identify a market as worthy of Trader attention.

Opportunity maturity may include:

```text
NO_OPPORTUNITY
EARLY
DEVELOPING
MATURE
DETERIORATING
EXPIRED
INSUFFICIENT
```

An opportunity board is an attention structure, not an order ranking.

The flow is:

```text
SHARED DISCOVERS
→ TRADER VALIDATES ITS OWN METHODOLOGY
→ EXECUTE / WAIT / ABSTAIN
```

Only a Trader-created valid opportunity may proceed toward CIBO.

## 8. Position intelligence

When a Trader owns an open-position thesis, Shared may retain a read-only
observation subscription and the world state that existed at entry.

Shared compares:

```text
WORLD_STATE_AT_ENTRY
vs
WORLD_STATE_NOW
```

and may emit typed deltas for:

- world state;
- regime;
- relationships;
- continuation;
- failure hazard;
- uncertainty;
- systemic stress.

Shared may say the supporting world is deteriorating or remains coherent.
It may not close, resize, protect or otherwise mutate the position.

## 9. Regime-transition and continuation intelligence

Shared shall research:

```text
TREND_CONTINUATION
TREND_EXHAUSTION
TRANSITION_DEVELOPING
REVERSAL_RISK
REGIME_BREAK
STRUCTURAL_DECOUPLING
```

Outputs must remain probabilistic/evidence-bound and preserve uncertainty.

Bad:

```text
trend will reverse
```

Required form:

```text
regime transition risk = ...
continuation support = ...
reversal evidence = ...
expected horizon = ...
uncertainty = ...
```

Continuation intelligence is equally required so Shared does not become only a
fear/warning system.

## 10. Competing worlds

Shared maintains competing explanations rather than forcing one story:

```text
CURRENT_WORLD
ALTERNATIVE_WORLD_A
ALTERNATIVE_WORLD_B
UNKNOWN_WORLD
```

Unknown and unresolved anomalies remain first-class.

## 11. Horizon law

Shared cognition is multi-horizon.

Every material claim shall preserve:

```text
observation horizon
expected validity horizon
decay horizon
```

A monthly macro condition may not directly control an M1 entry without a
scientifically validated causal bridge.

## 12. Event-driven architecture

Global cognition must not force every Trader to synchronously scan the full
world.

Required pattern:

```text
DEEP / NEARLINE WORLD COGNITION
→ CACHED CAUSAL SNAPSHOTS
→ MATERIAL STATE TRANSITIONS
→ SUBSCRIPTIONS / ROUTING
→ TRADER FAST-PATH CONSUMPTION
```

The current hard runtime SLA is not relaxed.

## 13. Alert governance

Alerts require identity, version, hypothesis identity, asset, created-at,
updated-at and evidence-cutoff.

Lifecycle may include:

```text
NEW
ACTIVE
STRENGTHENING
WEAKENING
RESOLVED
INVALIDATED
EXPIRED
```

Materiality, novelty, confidence change, world-state change and position
relevance must be researched before productive alerting.

Alert fatigue, duplication and repeated unchanged states are failures.

## 14. Causality and anti-leakage

For every Shared output:

```text
evidence_cutoff_at <= decision_time
```

Future price, report, weather, market close, roll state or position outcome may
never alter an earlier Shared output.

Data degradation must lower epistemic confidence or produce
`INSUFFICIENT`; it must not be interpreted as market behavior.

## 15. Epistemic discipline

Shared need not always have a directional view or opportunity.

Valid epistemic outputs include:

```text
KNOWN
PARTIALLY_KNOWN
UNCERTAIN
CONTRADICTORY
INSUFFICIENT
UNKNOWN
```

Every material output must preserve supporting evidence, contradicting
evidence and missing evidence.

Numerical confidence must not imply calibration unless empirical calibration
evidence exists.

## 16. Trader projection

Shared maintains one global world truth and may create trader-relevant
projections from it.

```text
GLOBAL_WORLD_STATE
!=
TRADER_RELEVANT_PROJECTION
```

A projection filters relevance; it may not rewrite global state or fabricate a
Trader-specific world.

Routing uses a read-only Trader capability registry describing markets,
horizons, supported intelligence classes and position-monitoring capability.

It may not expose Trader methodology as Shared authority.

## 17. Swing support

Shared shall prepare typed interfaces for future research families such as:

```text
QORE_GLOBAL_MACRO_SWING
QORE_COMMODITY_SWING
QORE_CROSS_ASSET_SWING
QORE_REGIME_TRANSITION_SWING
```

This directive does not create, activate or certify any Trader.

Swing Trader certification remains independent.

## 18. Agriculture / commodity integration

The agricultural and commodity world created under the Owner agricultural
directive becomes one possible input to Shared world cognition only after its
own identity, contract, roll, temporal, liquidity and causal gates are
satisfied.

No roll artifact may become a trend, divergence or regime-transition alert.

## 19. CIBO boundary

After a Trader independently validates a trade, certified Shared facts may
eventually be available to CIBO read-only.

```text
SHARED INFORMS.
CIBO DECIDES CAPITAL.
```

Shared cannot size or allocate.

CIBO cannot manufacture a Trader setup.

## 20. Risk boundary

Risk remains the final survivability governor.

A Shared crisis/stress state is evidence, not a global trade blocker.

```text
SHARED STRESS != REJECT ALL CORE
```

## 21. Causal value certification

Any claim that Shared improves a Trader requires control/treatment evidence.

Separate:

- opportunity-discovery value;
- entry-decision value;
- position-management value;
- continuation/positive-tail value;
- systemic awareness value.

Measure false alerts, missed alerts, lead time, winner damage, early-exit
regret and missed-opportunity regret without allowing future outcomes into the
historical decision.

If Trader behavior is unchanged, Shared receives no causal Trader-value credit
unless a separate measurable benefit is proven.

## 22. Learning governance

Runtime logs observations and outcomes but does not self-promote behavior.

```text
IDEA
→ SANDBOX
→ PREREGISTRATION
→ OOS
→ STRESS
→ REPLICATION
→ GOVERNANCE
→ PROMOTION
```

No online self-training into productive behavior.

## 23. Program

STI program:

```text
STI-0  Shared-Trader Gap Audit
STI-1  SharedTraderIntelligenceSnapshot
STI-2  Opportunity Discovery Engine
STI-3  Global Opportunity Board
STI-4  Opportunity Lifecycle / Watch State
STI-5  Regime Transition Intelligence
STI-6  Continuation / Positive-Tail Intelligence
STI-7  Position Observation Subscription
STI-8  Position Threat Intelligence
STI-9  World-at-Entry vs World-Now Delta
STI-10 Trader-Relevant Projection
STI-11 Alert Routing / Materiality / Deduplication
STI-12 Swing Trader Support Contract
STI-13 CIBO Read-Only Shared Facts Contract
STI-14 Control/Treatment Attribution
STI-15 Fresh OOS / Stress / Replication
STI-16 Governed Productive Admission
```

Dependency ordering may be tightened scientifically, but no later stage may
bypass temporal, causal, provenance, anti-leakage or sovereignty gates.

## 24. Final invariant

```text
SHARED MUST NOT ONLY DESCRIBE THE WORLD.
SHARED MUST DETECT WHEN THE WORLD IS CHANGING.

SHARED MAY SAY:
"THERE IS A POTENTIAL OPPORTUNITY HERE."

BUT THE TRADER MUST PROVE
THAT A TRADE EXISTS.

SHARED MAY SAY:
"THE WORLD THAT SUPPORTED THIS POSITION IS DETERIORATING."

BUT THE TRADER DECIDES
HOW THE POSITION IS MANAGED.

SHARED MAY SAY:
"THE WORLD STILL SUPPORTS THIS MOVE."

BUT THE TRADER DECIDES
WHETHER ITS METHODOLOGY JUSTIFIES HOLDING.
```

PR #635 remains DRAFT / UNMERGED. This directive creates no LIVE,
production, real-capital, merge, Risk, sizing, execution, broker-mutation or
Trader-methodology authority.
