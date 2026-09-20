# QORE Capitalizer — Research / Freeze Chain

Status: DEVELOPMENT ONLY — CONSUMED RESEARCH EVIDENCE
Owner contract: MAX3 per session is a ceiling, never a quota. QORE Risk remains sovereign.

## Acceptance envelope

The Capitalizer is a multi-session scalper. Research does not count as acceptance unless the frozen candidate ultimately satisfies all independent gates.

- Strategy observed DD target: **3R–5R**.
- Strategy observed DD absolute ceiling: **6R**.
- Daily realized loss must be engineered materially below the global DD envelope; do not normalize a funded-account daily limit as an acceptable trading target.
- DD may not be cosmetically reduced by redefining R, arbitrary lot reduction, or suppressing density without causal justification.
- Positive session PnL alone is not a stop condition.
- Every position must finish inside its own session.
- No DEMO/LIVE/production/real-capital authority is created by any research freeze.

## Freeze discipline

Only one chain is opened at a time. A downstream chain may use an upstream item only after the upstream result is explicitly classified:

- **FROZEN_APT** — evidence supports keeping the contract unchanged for the next chain.
- **FALSIFIED** — the proposed mechanism does not solve the stated problem.
- **RESEARCH_ONLY** — interesting evidence, not stable enough to freeze.
- **REJECTED_FOR_ACCEPTANCE** — violates the Owner economic envelope.

A freeze is not Trader Lab certification. Consumed-development evidence is never relabeled as fresh holdout evidence.

---

## Chain 1 — Daily Loss / Cross-Session Path

Question: how much can the trader lose inside one operating date as ASIA -> LONDON -> NEW_YORK accumulates?

Required evidence:
- worst realized day in R;
- realized intraday peak-to-trough DD;
- frequency of days <= -1R, -2R, -3R, -4R, -5R, -6R;
- annual stability;
- contribution by session;
- contribution by market / side / ordinal;
- repeated-loss cause across session handoffs.

Do not convert R to funded-account percent until QORE Risk sizing is explicitly applied.

Current lab: QORE_CAPITALIZER_DAILY_LOSS_FORENSICS_V1

No daily stop rule is selected in this chain.

---

## Chain 2 — Stop Geometry / Loss Anatomy

Open only after Chain 1 has a stable baseline.

Questions:
- Is the initial structural stop in the right place?
- Which stop losses were correct invalidations versus noise/raid sweeps?
- How much adverse excursion existed before eventual winners?
- How much favorable excursion existed before stopped losers?
- Which stop families improve protection without future leakage?
- Does the stop remain structurally valid in range, trend, volatility expansion, and transition?

Required invariants:
- stop may improve or hold;
- stop may never widen;
- no future pivot or later structure can authorize an earlier stop change;
- same-bar stop/target ambiguity stays fail-conservative.

The session-flow ledger must retain entry/stop/target/risk/exit lifecycle fields before this chain is evaluated.

---

## Chain 3 — Target Geometry / Destination Intelligence

Questions:
- Was the chosen destination structurally available at decision time?
- Was a fixed target truncating genuine expansion?
- When is the nearest structural destination appropriate?
- When is a farther destination causally justified?
- When should the trader abstain because no destination has sufficient structural capacity?

Study target families and timeframes using decision-time Target Context only. Outcome fields are labels, never entry features.

No trailing target is allowed until base destination behavior is understood.

---

## Chain 4 — Position Protection

Test mechanisms separately, never bundled:

1. structural break-even;
2. structural stop improvement;
3. profitable-swing lock;
4. trailing stop;
5. structural early exit;
6. trailing target / target extension.

Each mechanism must report:
- changed outcomes;
- losing trades improved;
- winning trades degraded;
- PF/DD/streak effect;
- daily-loss effect;
- temporal stability;
- market/session/state dependency.

A mechanism is frozen only if its causal trigger is known at the action time.

---

## Chain 5 — Market-State / Nine-Family Taxonomy

Owner requirement: study the **nine market families** deeply.

The identities/names of the nine families are **not frozen yet**. They must be derived or bound to an existing authoritative QORE/CIBO contract before use; do not invent labels to satisfy the count.

The taxonomy must allow the trader to distinguish at minimum:
- directional expansion / trend;
- range / balance;
- volatility expansion/contraction;
- transition / regime change;
- structural conflict / chaos;
- confidence degradation.

Final nine-family definitions must be mutually testable, causal at decision time, and stable across markets/sessions.

---

## Chain 6 — Confidence / Opportunity Quality

The trader must distinguish:
- high-confidence executable opportunity;
- partial / cautious opportunity;
- doubtful opportunity;
- conflicted opportunity;
- unknown / abstain.

Confidence may not be a fitted score whose only justification is historical PnL.

Evidence may include:
- Situation Model agreement;
- source-event freshness;
- CISD/departure timing;
- structural destination availability;
- regime/family;
- execution quality;
- exposure compatibility;
- failure-repeat memory;
- Market Brain / Session Brain evidence.

The output remains EXECUTE / WAIT / ABSTAIN.

---

## Chain 7 — Cross-Market Balance / Session Portfolio Intelligence

Questions:
- which market/side combinations can coexist;
- which second/third slots reduce or increase tail loss;
- when a weak market should yield a slot to a stronger causal opportunity;
- whether confidence concentration reduces DD without destroying density;
- whether simultaneous positions are actually duplicated factor bets.

This layer may choose among valid candidates but must not manufacture validity.

QORE Risk remains final exposure/capital authority.

---

## Chain 8 — CIBO ZIG-ZIG / Capital Modulation

The Owner requested a deep study of when ZIG-ZIG may be used and whether its use can damage a funded account.

Before implementation, bind the exact existing CIBO ZIG-ZIG semantic contract. Do not assume that the name means martingale, pyramiding, or simple lot multiplication.

Required falsification:
- effect on daily loss;
- effect on total DD and tail DD;
- effect after wins versus after losses;
- concentration/correlation risk;
- interaction with confidence and market/session compatibility;
- provider daily-loss and total-loss envelopes;
- fail-closed behavior when QORE Risk denies capital.

ZIG-ZIG can never override QORE Risk and cannot be used to rescue a losing hypothesis.

---

## Chain 9 — Execution / Funding Portability

Only after strategy behavior is structurally frozen:
- spread;
- commission;
- slippage;
- latency;
- same-bar ambiguity;
- provider-specific loss accounting;
- IC Markets RAW;
- FTMO;
- FundedNext;
- provider-neutral adverse envelope.

Provider profiles may not create strategy variants.

---

## Chain 10 — Candidate Freeze and Certification

Only after Chains 1–9 have explicit dispositions:
- freeze one candidate;
- WFO;
- Monte Carlo;
- stress;
- robustness;
- slippage/cost portability;
- temporal stability;
- sealed fresh holdout;
- independent validation;
- normal QORE Trader Lab certification.

Until then:
CANDIDATE_FROZEN = FALSE
TRADER_CERTIFIED = FALSE
LIVE_AUTHORIZED = FALSE
PRODUCTION_AUTHORIZED = FALSE
