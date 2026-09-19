# QORE CAPITALIZER — COGNITIVE ARCHITECTURE FREEZE V1

**Identity:** `QORE_CAPITALIZER_COGNITIVE_SCALPER_V1`  
**Status:** ARCHITECTURE_FROZEN / IMPLEMENTATION_IN_PROGRESS / NOT_CERTIFIED  
**Date:** 2026-09-19  
**Branch:** `agent/qore-capitalizer-cognitive-v1-001`

## Mission

Build a new multi-session scalper whose economic mission is to capitalize QORE Core through
frequent, low-risk, independently justified intraday opportunities. The trader is not Turtle
Soup, VT08, AMD, CRT, or VT31. Existing QORE intelligence may be reused only as engineering
patterns and governed infrastructure.

The trader MUST NOT be used in DEMO, LIVE, or real capital until it completes the normal QORE
certification chain. Production destination is explicitly outside this freeze.

## Frozen market/session research universe

- ASIA: USDJPY, AUDJPY, AUDUSD; GBPJPY is an additional research candidate.
- LONDON: EURUSD, GBPUSD.
- NEW_YORK: XAUUSD, USDCAD; NAS100 is an additional research candidate.

A market earns inclusion through evidence. Session assignment is a research prior, not proof of
edge.

## Opportunity budget

- Maximum executed opportunities per session: 2.
- Maximum theoretical daily executions: 6.
- The maximum is never a quota.
- Zero executions is valid.
- A second trade in the same session requires a genuinely new causal opportunity.
- Revenge, same-source retry, and unchanged-thesis re-entry are forbidden.

## Strategy identity

The frozen research identity is a **microstructure transition scalper**.

Core causal sequence:

```text
BALANCE / COMPRESSION
        |
LIQUIDITY / BREAK EVENT
        |
ACCEPTANCE or REJECTION
        |
DISPLACEMENT
        |
MICRO PULLBACK / RETEST
        |
ENTRY OPPORTUNITY
        |
STRUCTURAL MICRO-DOL
```

The engine may resolve continuation or reversal from the same market-state grammar. The
cognitive layer must never invent a new strategy at runtime.

## Cognitive architecture

```text
                     CAPITALIZER MASTER BRAIN
                              |
                     STRATEGY IDENTITY
                              |
       +----------------------+----------------------+
       |                      |                      |
   MARKET BRAIN          SESSION BRAIN        EXECUTION BRAIN
       |                      |                      |
       +----------------------+----------------------+
                              |
                    MICROSTRUCTURE ENGINE
                              |
                       SITUATION MODEL
                              |
       +----------------------+----------------------+
       |                      |                      |
 EXPERIENCE MEMORY      DAILY JOURNEY          LOSS-CAUSE MEMORY
       |                      |                      |
       +----------------------+----------------------+
                              |
                       EXPOSURE GRAPH
                              |
                       DOL / JOURNEY
                              |
                    OPPORTUNITY REASONER
                              |
                     ADVERSARIAL CHECKER
                              |
                    CONFIDENCE CALIBRATOR
                              |
                 +------------+------------+
                 |            |            |
              EXECUTE        WAIT       ABSTAIN
                 |
          POSITION INTELLIGENCE
                 |
                CIBO
                 |
             QORE RISK
                 |
             EXECUTION
```

## Frozen cognitive invariants

1. Strategy Identity is immutable at runtime.
2. Market Memory, Session Memory, Experience Memory, Daily Journey and PnL cannot rewrite
   strategy identity.
3. Situation Model is causal and decision-time only.
4. Decisions are EXECUTE, WAIT, or ABSTAIN.
5. ABSTAIN kills the current hypothesis.
6. No secondary/fallback route may override ABSTAIN.
7. Re-entry after ABSTAIN requires a new causal event and rebuilt Situation Model.
8. Losses are stored with causal state, not only PnL.
9. A new trade may be blocked when it repeats the same unresolved failure state.
10. Exposure is modeled by underlying currency/asset factor, not merely ticket count.
11. Three JPY trades are not automatically three independent risks.
12. Execution quality is part of scalping cognition: spread, commission, quote freshness,
    slippage and latency may convert EXECUTE into WAIT/ABSTAIN.
13. Confidence must be evidence-calibrated; unsupported numeric confidence is forbidden.
14. Unknown/low-evidence states fail toward WAIT/ABSTAIN.
15. A deterministic adversarial check must try to falsify each EXECUTE thesis.
16. Session cognition retains causal handoff from Asia -> London -> New York.
17. Daily Journey retains consumed liquidity, failed hypotheses, current exposure and remaining
    destinations.
18. Maximum two executions per session is a hard opportunity-budget ceiling, not a target.
19. Capitalization Governor may recommend NORMAL, CAUTIOUS, HIGH_SELECTIVITY, STOP_SESSION or
    STOP_DAY, but cannot bypass QORE RISK.
20. QORE RISK remains final capital authority.
21. External/deep CIBO reasoning is off the boundary-critical execution path.
22. Boundary-critical reasoning is local, deterministic, auditable and latency-bounded.
23. No LIVE/PRODUCTION authority is created by this architecture.
24. No real-capital testing is allowed before full QORE certification.

## Fast brain vs deep brain

### Fast brain
- market/session state
- microstructure state
- causal Situation Model
- exposure state
- execution-quality state
- opportunity reasoner
- adversarial check
- EXECUTE/WAIT/ABSTAIN

### Deep brain
- session review
- causal loss forensics
- memory consolidation
- hypothesis research
- regime discovery
- adversarial research/council

The deep brain may propose research. It may not mutate certified rules in production.

## Certification obligations

Before any use:
- exact source/strategy contract freeze;
- deterministic implementation tests;
- no-lookahead proof;
- session-by-session replay;
- market-by-market replay;
- spread/commission/slippage stress;
- chronological portfolio replay;
- losing-streak and drawdown forensics;
- walk-forward / temporal stability;
- Monte Carlo;
- genuinely unseen holdout;
- QORE Trader Lab promotion evidence;
- runtime/shadow verification after certification;
- explicit Owner deployment authorization.

## Authority state

- ARCHITECTURE_FROZEN = TRUE
- IMPLEMENTATION_STARTED = TRUE
- STRATEGY_SOURCE_CONTRACT_COMPLETE = FALSE
- ECONOMIC_EDGE_PROVEN = FALSE
- TRADER_LAB_CERTIFIED = FALSE
- DEMO_AUTHORIZED = FALSE
- LIVE_AUTHORIZED = FALSE
- REAL_CAPITAL_AUTHORIZED = FALSE
- PRODUCTION_AUTHORIZED = FALSE
- VPS_MUTATED = FALSE


## Universal execution portability requirement

The Owner requires the Capitalizer to be certifiable for use across the intended operating
domains, not only one low-cost RAW broker.

Mandatory execution environments for the initial certification program:

- IC Markets RAW;
- FTMO;
- FundedNext;
- an adverse provider-neutral portability envelope whose frozen spread/commission/slippage/
  latency assumptions are at least as demanding as the approved research specification.

The same frozen strategy/cognitive candidate must survive every mandatory environment. Passing
IC Markets RAW while failing FTMO or FundedNext is **not** full Capitalizer certification.

Provider profiles are execution evidence, not strategy variants. They may change:

- spread cost;
- commission;
- slippage;
- latency;
- fill-quality assumptions;
- provider/account restrictions.

They may **not** change:

- Strategy Identity;
- entry methodology;
- causal reasoning semantics;
- the two-opportunity session ceiling;
- loss/rearm sovereignty;
- market/session cognition rules selected by the frozen candidate.

No provider may receive a retrospectively optimized strategy variant merely to obtain a pass.

The fail-closed portability law is:

```text
IC_MARKETS_RAW QUALIFIED
AND FTMO QUALIFIED
AND FUNDEDNEXT QUALIFIED
AND ADVERSE_PORTABILITY_ENVELOPE QUALIFIED
    -> EXECUTION_PORTABILITY_QUALIFIED

otherwise
    -> CAPITALIZER_FULL_CERTIFICATION_BLOCKED
```

Additional brokers/funding programs may later be added as new execution profiles without
changing the strategy identity, but each requires its own evidence before use.
