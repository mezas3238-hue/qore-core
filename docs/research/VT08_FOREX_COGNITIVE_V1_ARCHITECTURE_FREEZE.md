# VT08 FOREX — Cognitive V1 Architecture Freeze

Status: **FROZEN ARCHITECTURE / PARALLEL RESEARCH-SHADOW LINE / NOT LIVE-WIRED**

Owner-approved direction: preserve the certified VT08 Forex methodology and build a trader-local cognitive layer that reasons about each valid VT08 hypothesis before execution.

## 1. Non-negotiable invariants

1. **VT08 methodology is immutable.** Cognitive V1 may interpret context but may not invent, delete, or rewrite VT08 source rules, anchors, entry definitions, stop definitions, target definitions, expiry, cardinality, or certified market/direction authority.
2. **Architecture may be borrowed; knowledge may not.** VT31 and Capitalizer are architectural references only. Their NAS100 rules, thresholds, memories, PnL-derived bins, and strategy-specific knowledge are prohibited inputs.
3. **No future leakage.** Every cognitive state is causal as-of the decision timestamp. Future bars, terminal PnL, post-outcome labels, fold identity, calendar-date edge lookup, and retrospective oracle fields are prohibited.
4. **QORE Risk remains sovereign.** Cognition never mints capital authority, order authority, position size, leverage, or account permission.
5. **Current VT08 runtime remains untouched.** This line is developed in parallel and may run only in research/shadow until separately validated and Owner-authorized.
6. **ABSTAIN sovereignty.** A killed/contradicted hypothesis cannot be resurrected from the same source event. Rearm requires a genuinely new structural event and a new cognitive decision.
7. **Position protection is monotonic.** A stop may improve or hold; it may never widen.
8. **No runtime self-training from realized PnL.** New learned knowledge must pass governed research and versioned evidence binding before entering memory.

## 2. Frozen cognitive components

### A. Strategy Identity Memory

Purpose: answer **"What is VT08 and what must be true?"**

Contains only immutable VT08 methodology identity and fingerprints:
- Forex authority;
- Owner operational anchors **01:00 / 05:00 / 09:00 New York**;
- H4/M15/LTF contracts and source semantics;
- bias / POI / protected-swing / CISD / entry / invalidation / target / expiry identity;
- market and direction authority;
- cardinality and lifecycle invariants.

It cannot contain retrospective performance statistics.

### B. CIBO Market Memory — market specialist

Purpose: answer **"How does this market normally behave?"**

Memory is isolated by market. GBPUSD learns GBPUSD, GBPJPY learns GBPJPY, AUDJPY learns AUDJPY, etc.

Permitted knowledge is governed causal/aggregate context: liquidity behavior, H4 delivery, displacement, range state, session/anchor behavior, continuation/reversal structure, journey/destination statistics and causal structural events.

Post-outcome aggregate research may inform research hypotheses but cannot become a date-level runtime oracle.

### C. Trader Experience Memory

Purpose: answer **"What has VT08 learned when its own methodology interacts with this market?"**

Stores:
- supported mechanisms;
- falsified hypotheses;
- unresolved hypotheses;
- consumed research bindings;
- Market × Anchor interaction lessons;
- causal failure modes;
- WAIT/ABSTAIN/EXECUTE diagnostics;
- position-management lessons.

It cannot rewrite Strategy Identity Memory and cannot self-train at runtime.

### D. Causal Situation Model

Ephemeral, non-persistent working state built only from evidence available at `as_of`.

Required domains:
- market / anchor / local time;
- H4 context and source-candle state;
- liquidity and sweep state;
- bias state;
- POI state;
- protected swing state;
- CISD / displacement / confirmation state;
- entry geometry and freshness;
- contradiction / uncertainty context;
- journey stage and structural destination state;
- position state if already filled.

Unknown information remains explicitly UNKNOWN; it is never guessed.

### E. Hypothesis Lifecycle

Frozen lifecycle:

`FORMING -> CONFIRMED -> WAITING -> EXECUTABLE`

or

`FORMING/CONFIRMED/WAITING -> CONTRADICTED -> KILLED`

A KILLED hypothesis is terminal for that source identity.

A new attempt requires:
- a genuinely new qualifying structural/source event;
- new causal evidence;
- rebuilt Situation Model;
- new reasoning decision.

### F. Sovereign Reasoning Engine

The cognitive decision vocabulary is exactly:

- **EXECUTE** — methodology-valid hypothesis is causally supported and has no material contradiction.
- **WAIT** — hypothesis remains alive, but required causal evidence or resolution is still incomplete.
- **ABSTAIN** — a material contradiction invalidates the current hypothesis.

Reasoning must emit:
- supporting evidence;
- contradictions;
- uncertainty;
- memory references used;
- Situation Model fingerprint;
- hypothesis/source fingerprint;
- deterministic reason codes.

### G. Adversarial Reasoning

Before EXECUTE, the trader must evaluate the inverse question:

**"What observable evidence says this trade should not be executed?"**

The adversarial pass cannot invent new strategy rules. It searches for contradiction, invalidation, stale evidence, causal inconsistency, geometry conflict, journey conflict, or unresolved ambiguity.

A material unresolved contradiction prevents EXECUTE.

### H. Metacognition

Knowledge-state vocabulary is frozen to:

- **KNOWN**
- **SUPPORTED**
- **AMBIGUOUS**
- **CONTRADICTED**
- **UNKNOWN**

No pseudo-probability or unsupported confidence percentage is allowed.

The metacognitive layer states what is known, what evidence supports it, what remains unknown, and whether that uncertainty is execution-material.

### I. Journey / Destination Intelligence

Purpose: reason beyond entry toward the expected structural path.

It may represent:
- current journey stage;
- expected structural destination / DOL;
- continuation evidence;
- failure-to-deliver evidence;
- exhaustion state;
- path efficiency / overlap / displacement only when causally observable.

Future journey labels are prohibited runtime inputs.

### J. Position Intelligence

After fill, cognition remains active.

Position action vocabulary:

- **HOLD**
- **PROTECT**
- **REDUCE**
- **EXIT**

Invariant: stop may only improve or hold; never widen.

Position Intelligence may not override QORE Risk or create extra exposure.

### K. Market × Anchor Specialist Experience

VT08 remains one methodology, but Experience Memory is allowed to learn distinct causal behavior for each certified cell:

`MARKET × {01:00, 05:00, 09:00 NY}`

This is specialization, not methodology mutation.

No cell may be promoted from performance alone. A cell-specific lesson requires causal mechanism, temporal robustness, and governed evidence.

## 3. Frozen orchestration

```text
VT08 SOURCE / SIGNAL
        |
        v
Strategy Identity validation
        |
        v
CIBO Market Memory + Trader Experience Memory
        |
        v
Causal Situation Model
        |
        v
Hypothesis Lifecycle
        |
        v
Primary Reasoning
        |
        v
Adversarial Reasoning
        |
        v
Metacognitive materiality check
        |
        +---- ABSTAIN -> kill current hypothesis
        |
        +---- WAIT ----> continue observing same live hypothesis
        |
        +---- EXECUTE --> CIBO operational posture
                             |
                             v
                         QORE Risk
                             |
                             v
                         Execution
                             |
                             v
                    Position Intelligence
```

## 4. Architecture provenance

Permitted architectural borrowing:
- VT31: Strategy Identity Memory, Market Memory separation, Trader Experience Memory, causal Situation Model, EXECUTE/WAIT/ABSTAIN sovereignty, Position Intelligence.
- Capitalizer: adversarial reasoning, metacognitive knowledge state, hypothesis lifecycle concepts.
- CIBO: governed market/journey context and memory provenance.

Prohibited borrowing:
- NAS100-specific rules;
- Silver Bullet conditions;
- Capitalizer entry logic;
- Turtle Soup rules;
- fixed thresholds copied from another trader;
- another trader's PnL-derived filters;
- another trader's market-specific memories.

## 5. Validation path

The architecture freeze does **not** certify the cognitive implementation.

Required sequence:
1. contract/invariant implementation;
2. market-specific memory construction from governed VT08 evidence;
3. causal Situation Model;
4. Reasoning + Adversarial + Metacognition;
5. Hypothesis Lifecycle;
6. Journey / Position Intelligence;
7. deterministic replay on consumed evidence;
8. compare baseline VT08 vs Cognitive V1 for density, PF, DD, streaks, false abstention, missed valid opportunities, and leakage;
9. freeze candidate;
10. sealed holdout / WFO / MC / stress as required;
11. SHADOW;
12. separate Owner authorization before any LIVE replacement.

## 6. Governance

- Branch is parallel to current operational VT08.
- No merge without Owner order.
- No VPS mutation from this architecture freeze.
- No LIVE registration.
- No real-capital authorization.
- No production authorization.
- Existing VT08 certification remains unchanged by this work.
