# QORE UNIVERSAL TRADER CERTIFICATION STANDARD — UTC-001

**Status:** CEO-directed universal certification rule  
**Scope:** every Specialized Trader, current or future, before ACCEPTED / certified promotion  
**Authority:** Core Governance + Certification & Integration Gate  
**Applies to:** research promotion, trader rebuilds, replacement versions and new trader construction  
**Non-goal:** this standard does not grant LIVE authority or override QORE Risk / Execution / provider constraints

---

## 1. Constitutional rule

A Trader is not accepted because it produces many trades.

A Trader is accepted only when it demonstrates robust edge, controlled downside,
temporal stability, independent out-of-sample generalization and reproducible evidence.

```text
EDGE ROBUSTO
    -> WINNER / LOSER ECONOMICS
    -> EXPECTANCY
    -> PROFIT FACTOR
    -> SHARPE / SORTINO
    -> DRAWDOWN / TAIL SURVIVAL
    -> LOSS CLUSTERING
    -> TEMPORAL / OOS STABILITY
    -> COST ROBUSTNESS
    -> DENSITY
```

**Density is secondary. It may amplify proven edge; it may never substitute for edge.**

```text
NO EDGE -> NO CERTIFICATION
NO OOS GENERALIZATION -> NO CERTIFICATION
NO FRESH HOLDOUT INTEGRITY -> NO CERTIFICATION
NO REPRODUCIBILITY -> NO CERTIFICATION
DENSITY != EDGE
DEVELOPMENT != CERTIFICATION
CI GREEN != TRADER ACCEPTED
```

---

## 2. Universal ACCEPTED gates

Every gate below is mandatory unless the metric is mathematically undefined for the
strategy; any such exception must be justified in retained evidence and approved by
the Certification & Integration Gate. An exception may not be used to hide adverse
performance.

### 2.1 Profit Factor

- every independent OOS era/fold: **PF >= 1.50**
- combined OOS: **PF >= 1.70**
- preferred operating quality: **PF >= 2.00**

A strong Development PF cannot compensate for a broken OOS era.

### 2.2 Expectancy

- every independent OOS era/fold: **expectancy > 0R/trade**
- combined OOS certification floor: **expectancy >= +0.15R/trade**

A high trade count with marginal expectancy is not a certification argument.

### 2.3 Drawdown

- observed Max DD: **<= 6R**
- **6R is the universal Core hard acceptance ceiling**
- >6R requires intervention and blocks ACCEPTED
- >15R is a structural rejection condition unless a newer Core governance standard explicitly supersedes UTC-001

### 2.4 Sharpe

- OOS Sharpe: **>= 1.50**
- preferred: **>= 2.00**

Every report must state return frequency, annualization convention, treatment of
no-trade periods, costs and exact population.

### 2.5 Sortino

- OOS Sortino: **>= 2.00**

Sharpe and Sortino must be interpreted together; upside variability must not be
penalized as if it were downside damage.

### 2.6 Monte Carlo / sequence survival

- probability of positive result: **>= 90%**
- p95 Max DD: **<= 15R**
- preferred positive probability: **>= 95%**
- preferred p95 Max DD: **<= 10–12R**

At minimum, retained evidence must include sequence/reshuffle stress and losing-cluster
stress. Cost stress is required whenever provider economics are available.

### 2.7 Payoff economics

- Average Winner / Average Loser: **>= 1.20**
- preferred: **>= 1.50**

Win rate is never interpreted without payoff and expectancy.

### 2.8 Cost robustness

After realistic retained costs:

- post-cost expectancy **> 0**
- post-cost PF **> 1.00**
- preferred post-cost PF **>= 1.50**

Historical provider costs may not be fabricated. If exact economics are unavailable,
the limitation must be explicit and the affected certification claim remains blocked.

### 2.9 Temporal stability

No global average may hide a broken era.

Each material era/fold must report at least:

- trades;
- wins/losses/breakeven;
- win rate;
- PF;
- expectancy;
- Sharpe;
- Sortino;
- Max DD;
- Average Winner;
- Average Loser;
- payoff ratio;
- longest losing streak.

All independent OOS eras used for certification must remain economically positive.

### 2.10 Loss clustering

The Trader must pass an explicit loss-cluster / tail-survival gate.

Required investigation includes, where applicable:

- loss-cluster frequency and duration;
- longest losing streak;
- session/time-of-day/day-of-week;
- symbol / direction / setup subtype;
- volatility / liquidity / spread;
- market/cross-market regime;
- MAE/MFE and time-to-MAE/MFE;
- structural failure state.

A Trader that can suffer a plausible loss cluster large enough to destroy its intended
capital envelope is not ACCEPTED merely because its aggregate PF is positive.

### 2.11 Winner preservation for loser-rejection intelligence

Any filter, perception model, Shared fact or other intelligence introduced to reject
losers must report:

- Loss Recall;
- Winner Count Preservation;
- Winner-R Preservation;
- PF delta;
- expectancy delta;
- Sharpe delta;
- DD delta;
- density delta.

Minimum preservation gates:

- Winner Count Preservation **>= 80%**
- Winner-R Preservation **>= 90%**

Preferred:

- Winner Count Preservation **>= 90%**
- Winner-R Preservation **>= 95%**

Reducing losses by destroying the winner population is not improvement.

### 2.12 Fresh holdout integrity

If Validation, Reserved or any holdout has already been inspected and then used to
design, tune, select or reject a new policy, that evidence is **burned for future
certification of the modified policy**.

```text
OBSERVED HOLDOUT
-> MODIFICATION INFORMED BY THAT HOLDOUT
-> HOLDOUT BURNED
-> FRESH INDEPENDENT EVIDENCE REQUIRED
```

No repeated threshold tuning against the same Reserved population.

### 2.13 Anti-leakage / causal decision integrity

Forbidden:

- future outcome used at decision time;
- post-entry MAE/MFE used as entry input;
- future labels leaked into features;
- repeated holdout mining;
- outcome-aware sizing;
- martingale;
- loss-recovery sizing;
- hidden future-dependent filtering.

Every productive decision feature must exist at or before the decision timestamp.

### 2.14 Density

There is **no universal minimum trade count that can compensate for weak edge**.

Density is evaluated only after the quality gates above pass.

Per-Trader minimum sample sufficiency must be declared before final OOS evaluation,
based on the methodology and opportunity frequency, not chosen after seeing outcomes.

```text
QUALITY FIRST
-> THEN DENSITY
```

A lower-density robust Trader is preferred over a high-density marginal Trader.

---

## 3. Win rate law

Win rate is mandatory to report but is **not a universal standalone acceptance threshold**.

Reference preference:

- WR >= 50% is desirable when compatible with the strategy's payoff structure.

A lower WR can be accepted only if payoff, expectancy, PF, Sharpe/Sortino, drawdown
and OOS stability all satisfy the universal gates.

A high WR cannot rescue poor payoff economics.

```text
WIN RATE x PAYOFF x EXPECTANCY x TAIL RISK
```

must be evaluated jointly.

---

## 4. Development, Validation and Reserved

### Development

Development may be used for hypothesis generation, training and engineering.

It never certifies the Trader.

### Validation

Validation tests hypotheses frozen before validation consumption.

### Reserved / final holdout

Reserved must remain independent of the modification being certified.

If it has been used to guide a subsequent redesign, a new fresh holdout is required.

---

## 5. Universal dispositions

### ACCEPTED

All mandatory gates pass with reproducible evidence.

### INTERVENTION — CONTINUE WORK

There is evidence of edge, but one or more acceptance gates remain below standard.
Engineering continues. Density must not be used to disguise the deficiency.

### REJECTED

Use when evidence shows a structural failure such as:

- OOS expectancy materially disappears;
- PF is structurally insufficient;
- unacceptable tail/DD behavior;
- no temporal generalization;
- fresh holdout falsification;
- unavoidable leakage/overfit dependency;
- strategy economics become negative after required costs.

Rejected means the tested architecture/policy is rejected. It does not prohibit a
new causal hypothesis with genuinely fresh evidence.

---

## 6. Required certification evidence pack

No Trader may be marked ACCEPTED without a retained, reproducible pack containing:

```text
git HEAD / strategy version
workflow run IDs
artifact IDs / hashes
dataset provenance
exact train/development window
exact validation/OOS windows
fresh holdout window
trade population
PF
win rate
expectancy
Sharpe
Sortino
Max DD
Monte Carlo positive probability
Monte Carlo p95 DD
Average Winner
Average Loser
payoff ratio
longest losing streak
loss-cluster analysis
MAE/MFE analysis
cost stress
per-era / per-fold results
winner-preservation evidence for any loser-rejection layer
density / sample sufficiency
anti-leakage audit
final disposition
```

Missing evidence means the corresponding claim is not certified.

---

## 7. Relationship to Shared, CIBO, Risk and Execution

### Trader

Owns methodology, setup, direction, entry, structural invalidation/stop, target and exit methodology.

### Shared

May provide facts, context, regime, uncertainty and cross-market observations.
It may not silently become the Trader's sovereign decision authority.

### CIBO

Owns capital management/sizing/allocation according to its separate authority.
CIBO must not be used to disguise a weak Trader edge.

### QORE Risk

Remains independent hard survivability governor.

### Execution

Mutates the provider only after all required authorities pass.

```text
GOOD CAPITAL MANAGEMENT != GOOD TRADER
GOOD TRADER != LIVE AUTHORITY
TRADER CERTIFICATION != RISK BYPASS
```

---

## 8. Construction rule for every future Trader

Every new Trader work order and every material rebuild must reference **UTC-001**.

The development sequence is:

```text
METHODOLOGY
-> CAUSAL IMPLEMENTATION
-> DEVELOPMENT
-> FREEZE
-> INDEPENDENT OOS
-> LOSS / WINNER ECONOMICS
-> SHARPE / SORTINO / DD / MC
-> COST STRESS
-> FRESH HOLDOUT
-> UTC-001 GATE
-> ACCEPTED | INTERVENTION | REJECTED
```

The builder may not redefine these universal acceptance gates inside an individual
Trader PR merely to make that Trader pass.

Any future change to UTC-001 is a Core governance change and requires explicit,
versioned review; it cannot drift through a Trader-specific commit.

---

## 9. Final law

```text
EDGE BEFORE DENSITY.
OOS BEFORE PROMOTION.
SURVIVAL BEFORE SCALE.
NO WINNER DESTRUCTION TO MANUFACTURE WIN RATE.
NO HOLDOUT MINING.
NO LEAKAGE.
NO TRADER ACCEPTED UNTIL UTC-001 PASSES.
```
