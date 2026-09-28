# QORE UNIVERSAL TRADER CERTIFICATION STANDARD — UTC-001

**Version:** 1.1 — strict temporal gates  
**Status:** CEO-directed universal certification rule  
**Scope:** every Specialized Trader, current or future, before ACCEPTED / certified promotion  
**Authority:** Core Governance + Certification & Integration Gate  
**Applies to:** research promotion, trader rebuilds, replacement versions and new Trader construction  
**Non-goal:** this standard does not grant LIVE authority or override QORE Risk / Execution / provider constraints

---

## 1. Constitutional rule

A Trader is not accepted because it produces many trades or because a global aggregate looks good.

A Trader is accepted only when it demonstrates robust edge, controlled downside,
temporal stability, independent out-of-sample generalization and reproducible evidence
**inside every mandatory certification period**.

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

```text
NO EDGE -> NO CERTIFICATION
NO OOS GENERALIZATION -> NO CERTIFICATION
NO FRESH HOLDOUT INTEGRITY -> NO CERTIFICATION
NO REPRODUCIBILITY -> NO CERTIFICATION
ONE FAILED REQUIRED PERIOD -> NO CERTIFICATION
GLOBAL / COMBINED METRIC != CERTIFICATION GATE
DENSITY != EDGE
DEVELOPMENT != CERTIFICATION
CI GREEN != TRADER ACCEPTED
```

---

## 2. Strict temporal certification law

### 2.1 No global averaging

**Global, combined, pooled or whole-holdout metrics have zero acceptance authority.**

They may be reported for descriptive context only.

They may not:

- rescue a failed year;
- rescue a failed OOS fold;
- average away a drawdown breach;
- compensate negative expectancy in one period with profits from another;
- convert a temporally unstable Trader into ACCEPTED.

Example:

```text
2022 PF 2.40
2023 PF 0.90
GLOBAL PF 1.70
```

Result:

```text
NOT ACCEPTED
2023 FAILED
```

The global 1.70 is irrelevant to certification.

### 2.2 Annual slices are mandatory

If a certification holdout spans multiple calendar/trading years, **every covered year must be
evaluated independently**.

For a two-year holdout:

```text
HOLDOUT 2Y
  -> YEAR 1: FULL UTC-001 GATE
  -> YEAR 2: FULL UTC-001 GATE
```

Both years must pass.

A strong Year 1 cannot compensate for a weak Year 2.

If a holdout covers a partial first or last calendar year, that partial year is still a mandatory
temporal slice unless the predeclared certification protocol uses a different fixed annualization
boundary. Boundaries must be frozen before outcomes are inspected.

### 2.3 Frozen OOS folds are also mandatory

When the certification protocol defines OOS folds, every frozen fold must independently pass
UTC-001.

Annual slices and folds answer different temporal questions and neither may replace the other.

```text
ACCEPTED
=
ALL REQUIRED YEARS PASS
AND
ALL REQUIRED OOS FOLDS PASS
AND
FRESH HOLDOUT INTEGRITY PASSES
AND
ANTI-LEAKAGE PASSES
```

---

## 3. Universal gates — applied to EACH mandatory year/fold

The following gates are evaluated independently inside every required certification period.

### 3.1 Profit Factor

- **PF >= 1.50**
- preferred operating quality: **PF >= 2.00**

### 3.2 Expectancy

- **expectancy >= +0.15R/trade**

Merely positive but marginal expectancy is insufficient for ACCEPTED.

### 3.3 Drawdown

- **Observed Max DD <= 6R**
- **6R is the universal Core hard acceptance ceiling**
- 6.00R passes;
- >6R blocks ACCEPTED for that period.

### 3.4 Sharpe

- **Sharpe >= 1.50**
- preferred: **>= 2.00**

Every report must state return frequency, annualization convention, treatment of no-trade periods,
costs and exact population.

### 3.5 Sortino

- **Sortino >= 2.00**

### 3.6 Monte Carlo / sequence survival

For every mandatory period:

- positive-result probability **>= 90%**
- p95 Max DD **<= 15R**
- preferred positive probability **>= 95%**
- preferred p95 Max DD **<= 10–12R**

At minimum: reshuffle/sequence stress and losing-cluster stress.

### 3.7 Payoff economics

Payoff ratio is a **hard universal certification gate**.

- Average Winner / Average Loser: **>= 1.50**
- the threshold applies independently to every required year and every required OOS fold;
- a global/combined payoff cannot rescue a failed period.

Rationale: UTC-001 is an excellence standard, not a minimum-viability standard. Requiring 1.50
forces the average winner to be materially larger than the average loser while Profit Factor,
expectancy, Sharpe/Sortino, drawdown and Monte Carlo remain independent hard gates.

A high payoff still cannot rescue weak PF, expectancy, Sharpe/Sortino, drawdown, costs or OOS
stability. All gates must pass simultaneously.

### 3.8 Cost robustness

After realistic retained costs, in every mandatory period:

- post-cost expectancy **> 0**
- post-cost PF **> 1.00**
- preferred post-cost PF **>= 1.50**

Historical provider economics may not be fabricated. Missing required cost evidence blocks the
affected certification claim.

### 3.9 Loss clustering / tail survival

Every mandatory period must pass an explicit loss-cluster gate.

Required investigation, where applicable:

- cluster frequency and duration;
- longest losing streak;
- session/time-of-day/day-of-week;
- symbol / direction / setup subtype;
- volatility / liquidity / spread;
- regime / cross-market state;
- MAE/MFE and time-to-MAE/MFE;
- structural failure state.

### 3.10 Density / sample sufficiency

Density is evaluated only after quality passes.

Each mandatory period must contain the predeclared sample sufficiency required by that Trader's
methodology. Sample sufficiency must be frozen before final OOS outcomes are inspected.

There is no trade-count target that can rescue a failed quality gate.

---

## 4. Win rate law

Win rate is mandatory to report for every year/fold but is **not a universal standalone threshold**.

WR >= 50% is desirable when compatible with the strategy's payoff structure.

A lower WR can pass only when the same period independently satisfies the payoff >= 1.50 gate,
expectancy, PF, Sharpe/Sortino, DD, Monte Carlo and cost gates.

A high WR cannot rescue poor payoff economics.

```text
WIN RATE x PAYOFF x EXPECTANCY x TAIL RISK
```

must be evaluated jointly within the same temporal slice.

---

## 5. Winner preservation for loser-rejection intelligence

Any filter, perception model, Shared fact or intelligence introduced to reject losers must report,
per relevant independent period:

- Loss Recall;
- Winner Count Preservation;
- Winner-R Preservation;
- PF delta;
- expectancy delta;
- Sharpe delta;
- DD delta;
- density delta.

Minimum gates:

- Winner Count Preservation **>= 80%**
- Winner-R Preservation **>= 90%**

Preferred:

- Winner Count Preservation **>= 90%**
- Winner-R Preservation **>= 95%**

Reducing losses by destroying the winner population is not improvement.

---

## 6. Fresh holdout integrity

If Validation, Reserved or any holdout has already been inspected and then used to design, tune,
select or reject a modified policy, that evidence is burned for certification of that modification.

```text
OBSERVED HOLDOUT
-> MODIFICATION INFORMED BY THAT HOLDOUT
-> HOLDOUT BURNED
-> FRESH INDEPENDENT EVIDENCE REQUIRED
```

No repeated threshold tuning against the same Reserved population.

---

## 7. Anti-leakage / causal decision integrity

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

---

## 8. Development, Validation and Reserved

### Development

Development may be used for hypothesis generation, training and engineering. It never certifies.

### Validation / OOS

Validation tests hypotheses frozen before consumption. Every required year and fold is independently
gated.

### Reserved / final holdout

Reserved must remain independent of the modification being certified. If used to guide redesign, a
new fresh holdout is required.

---

## 9. Universal dispositions

### ACCEPTED

Only when **every mandatory annual slice and every mandatory frozen OOS fold passes every applicable
UTC-001 gate**, plus holdout integrity and anti-leakage.

### INTERVENTION — CONTINUE WORK

Evidence of edge exists, but one or more mandatory periods fail at least one gate.

### REJECTED

Use when evidence shows structural failure such as persistent OOS degradation, unacceptable
tail/DD behavior, temporal non-generalization, fresh holdout falsification, unavoidable
leakage/overfit dependency or negative post-cost economics.

---

## 10. Required certification evidence pack

No Trader may be marked ACCEPTED without retained reproducible evidence containing:

```text
git HEAD / strategy version
workflow run IDs
artifact IDs / hashes
dataset provenance
exact Development window
exact Validation/OOS window
fresh holdout window
predeclared annual/fold boundaries

FOR EACH REQUIRED YEAR:
  trade population
  wins/losses/breakeven
  win rate
  PF
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
  cost stress
  sample sufficiency

FOR EACH REQUIRED OOS FOLD:
  the same full metric/gate set

winner-preservation evidence for any loser-rejection layer
MAE/MFE analysis
fresh-holdout integrity audit
anti-leakage audit
final disposition
```

Global/combined metrics may appear only in a descriptive appendix and may not influence ACCEPTED.

---

## 11. Relationship to Shared, CIBO, Risk and Execution

### Trader
Owns methodology, setup, direction, entry, structural invalidation/stop, target and exit methodology.

### Shared
May provide facts, context, regime, uncertainty and cross-market observations. It may not silently
become Trader sovereign authority.

### CIBO
Owns capital management/sizing/allocation under its separate authority. CIBO must not disguise weak
Trader edge.

### QORE Risk
Independent hard survivability governor.

### Execution
Mutates the provider only after required authorities pass.

```text
GOOD CAPITAL MANAGEMENT != GOOD TRADER
GOOD TRADER != LIVE AUTHORITY
TRADER CERTIFICATION != RISK BYPASS
```

---

## 12. Construction rule for every future Trader

Every new Trader work order and material rebuild must reference UTC-001.

```text
METHODOLOGY
-> CAUSAL IMPLEMENTATION
-> DEVELOPMENT
-> FREEZE
-> INDEPENDENT OOS
-> ANNUAL SLICES
-> FROZEN OOS FOLDS
-> FULL UTC-001 GATE PER PERIOD
-> FRESH HOLDOUT
-> ACCEPTED | INTERVENTION | REJECTED
```

A Trader-specific work order may tighten UTC-001 but may never weaken it.

Any future change to UTC-001 is a Core governance change requiring explicit versioned review.

---

## 13. Final law

```text
EDGE BEFORE DENSITY.
PER-YEAR / PER-FOLD GATES BEFORE GLOBAL SUMMARIES.
ONE FAILED REQUIRED PERIOD -> NO CERTIFICATION.
GLOBAL PERFORMANCE CANNOT RESCUE TEMPORAL FAILURE.
OOS BEFORE PROMOTION.
MAX DD <= 6R IN EVERY REQUIRED PERIOD.
NO HOLDOUT MINING.
NO LEAKAGE.
NO TRADER ACCEPTED UNTIL UTC-001 PASSES.
```
