# QORE Capitalizer Cognitive Scalper V1 — Certification Standard V2

Status: FROZEN OWNER STANDARD  
Trader: `QORE_CAPITALIZER_COGNITIVE_SCALPER_V1`  
PR: #623  
Source of truth: GitHub  
Effective date: 2026-09-28

## 1. Governing principle

The certification objective is no longer trade-count density.

The priority order is:

```
ROBUST EDGE
→ WINNER / LOSER ECONOMICS
→ EXPECTANCY
→ PROFIT FACTOR
→ SHARPE / SORTINO
→ DRAWDOWN
→ LOSS CLUSTERING
→ TEMPORAL / OOS STABILITY
→ DENSITY
```

Law:

> We do not optimize density of trades. We optimize density of edge.

Density may be expanded only after edge is demonstrated and only when the expansion does not materially degrade PF, expectancy, Sharpe, Sortino, drawdown, tail risk, temporal stability, or winner preservation.

## 2. Governance

- GitHub is the source of truth.
- PR #623 remains DRAFT until explicit Owner authority changes that status.
- No merge, VPS, demo, live, production, funded, or real-capital authority is implied by laboratory certification.
- Development may generate hypotheses and falsify them; Development never certifies generalization.
- Any period inspected and then used to change the system is consumed for future tuning.
- A consumed period may be used for diagnosis and regression evidence, but cannot be relabelled as fresh OOS.
- Owner research-data amendment (30-Sep-2026): historical holdouts, including pre-2016, may be opened for diagnosis/repair. Any opened period is consumed research evidence and cannot later satisfy final fresh certification evidence.
- No outcome-aware entry, sizing, filtering, protection, or routing logic is allowed.
- No martingale or loss-recovery sizing is allowed.
- Every decision feature must exist at or before the relevant decision timestamp.

## 3. Current reference evidence

Latest exact V2 distributed evidence at the time this standard was frozen:

### Development 2024–2026

- trades: 948
- winners: 544
- win rate: 57.38%
- PF: 2.2673840596398114
- Total-R: +258.6758664923R
- observed max DD: 5.9989275442R
- losing streak: 5
- density retention: 1
- entrant identities unchanged
- V2 consumed-data full gate: PASSED

This is a quality reference, not certification.

### Validation 2022–2024

Latest distributed checkpoint before exact resume:

- trades: 1,034
- winners: 459
- win rate: 44.39%
- PF: 1.7891731031931322
- Total-R: +112.8803815218R
- observed max DD: 6.6355967471R
- losing streak: 6
- exact resume required from checkpoint

GitHub evidence after this document supersedes these values.

### Reserved 2020–2022

Latest complete greedy V2 result:

- trades: 1,088
- winners: 456
- win rate: 41.91%
- PF: 1.4267360084596239
- Total-R: +56.6233657195R
- observed max DD: 7.2628349947R
- losing streak: 6
- greedy Reserve/Relief path exhausted
- richer episode-sequence search/world-model required

Reserved is consumed and cannot become a fresh holdout again.

## 4. Mandatory acceptance gates

### 4.1 OOS Profit Factor

For every designated OOS era:

```
PF >= 1.50
```

Combined OOS:

```
PF >= 1.70
```

Preferred:

```
PF >= 2.00
```

A strong era cannot compensate for another OOS era that fails a mandatory gate.

### 4.2 Expectancy

Every OOS era must have:

```
expectancy > 0R / trade
```

Target:

```
expectancy >= +0.15R / trade
```

### 4.3 Observed drawdown

Acceptance:

```
observed max DD <= 10R
```

Preferred:

```
<= 6–8R
```

Intervention band:

```
>10R and <=15R
```

Rejection-level tail evidence:

```
>15R
```

### 4.4 Sharpe

Required OOS:

```
annualized Sharpe >= 1.50
```

Preferred:

```
>= 2.00
```

Every report must bind:
- return interval;
- frequency;
- annualization factor and method;
- risk-free assumption;
- zero-trade-period treatment;
- cost basis;
- exact population.

No annualization may be silently inferred.

### 4.5 Sortino

Required OOS:

```
annualized Sortino >= 2.00
```

The MAR, downside-deviation denominator, frequency, zero-trade handling, and annualization method must be explicit.

### 4.6 Win rate and payoff

Win rate is descriptive, not an isolated certification gate.

Preferred:

```
WR >= 50%
```

Mandatory payoff target unless an explicitly reviewed statistical-compensation exception exists:

```
Average Winner / Average Loser >= 1.20
```

Preferred:

```
>= 1.50
```

Never optimize WR by destroying right-tail winners.

### 4.7 Monte Carlo and sequence survival

Required:

```
MC positive probability >= 90%
MC p95 DD <= 15R
```

Preferred:

```
MC positive probability >= 95%
MC p95 DD <= 10–12R
```

Required stress families:
- reshuffling;
- dependence-aware sequence stress;
- losing-cluster stress;
- cost stress when provider/broker cost evidence exists.

The resampling frame, seed, block semantics, sample count, chronology semantics, and cost assumptions must be frozen before results.

### 4.8 Loss clustering

Measure at minimum:
- cluster count;
- run length;
- cumulative cluster R;
- duration;
- concentration by session/market/regime/direction/setup subtype;
- volatility/liquidity/correlation context;
- MAE/MFE state.

A candidate cannot be ACCEPTED if loss clustering creates account-survival risk before expectancy can manifest.

### 4.9 Winner preservation

Any intelligence that removes, abstains from, exits, or protects trades must report:

- Loss Recall
- Winner Count Preservation
- Winner-R Preservation
- PF delta
- expectancy delta
- Sharpe delta
- DD delta
- density delta

Minimum research targets:

```
Winner Count Preservation >= 80%
Winner-R Preservation >= 90%
```

Preferred:

```
Winner Count Preservation >= 90%
Winner-R Preservation >= 95%
```

A loss filter that removes comparable winner mass is not evidence of improved edge.

### 4.10 MAE / MFE

Required forensic coverage:

- MAE winners
- MAE losers
- MFE winners
- MFE losers
- MAE-before-MFE
- MFE-before-MAE
- time-to-MAE
- time-to-MFE
- time-to-stop
- time-to-target

Future MFE/MAE is a label for research only and can never be a decision-time input.

### 4.11 Loser anatomy

Full-stop losers must be studied using causal facts available at or before the decision/observation timestamp, including where available:

- market regime
- session
- time-of-day / day-of-week
- volatility
- liquidity / spread
- correlation / cross-market context
- HTF structure
- sweep quality
- MSS / CISD / displacement
- FVG / OB quality
- entry location
- distance to invalidation
- pre-entry path
- causal post-entry journey
- opposing structural evidence

The research question is HIGH-QUALITY WINNERS vs AVOIDABLE FULL-STOP LOSERS, not retrospective label memorization.

### 4.12 Temporal stability

Report, when evidence exists:

```
PF
WR
expectancy
Sharpe
Sortino
DD
trades
Avg Win
Avg Loss
payoff
longest losing streak
```

across relevant:
- eras
- folds
- years
- sessions
- symbols
- regimes
- directions
- volatility states.

A favorable global average cannot mask a structurally weak era.

### 4.13 Cost stress

Minimum gate:

```
POST-COST EXPECTANCY > 0
POST-COST PF > 1
```

Preferred:

```
POST-COST PF >= 1.50
```

Stress spread, commission, slippage, and latency only from explicit evidence. Missing provider economics must be reported as missing evidence; costs may not be invented.

### 4.14 Density

Density is secondary. No fixed 250–300-trade target is a certification requirement.

A lower-density strategy with materially stronger edge is preferable to a higher-density strategy with weak PF, poor risk-adjusted return, or destructive tail risk.

The final candidate still requires enough observations for meaningful OOS/tail evaluation, but no trade-count expansion may damage quality.

## 5. Final independent / prospective OOS

Owner research-data amendment (30-Sep-2026):

Historical holdouts may be used to diagnose and repair the Trader, including the provider-native pre-2016 window. Once outcomes from any historical period are used to change methodology, cognition, admission, execution geometry, lifecycle, or policy, that period is consumed and has zero authority as final fresh certification evidence.

The mandatory final fresh-evidence gates therefore require one of:

1. a genuinely independent governed provider/source whose outcomes were not used for tuning; or
2. a prospective frozen evaluation period beginning after the immutable candidate fingerprint is frozen.

The final OOS object must be frozen before its outcomes are read and may be evaluated exactly once for that immutable candidate.

If final independent/prospective OOS falsifies the candidate, that candidate is rejected and the observed OOS evidence becomes consumed. Retuning requires a new independent/prospective validation object.

Historical evidence may still contribute to temporal robustness, regression, falsification, MAE/MFE, loss-cluster, winner-preservation and multi-era research, but it may not be relabelled as fresh certification evidence.

## 6. Shared / CIBO authority boundary

Shared may provide facts, context, regime, liquidity, volatility, correlation, cross-market observations, journey evidence, uncertainty, and anomaly evidence. Shared does not take Scalper sovereignty.

Scalper owns its edge-producing methodology.

CIBO later owns capital, sizing, allocation, reserve, expansion, recycling, and de-risking. Scalper entries may not be modified merely to make CIBO easier to satisfy.

## 7. Classification

### ACCEPTED

All mandatory evidence must be present and pass simultaneously:

- OOS PF >=1.50 per era;
- combined OOS PF >=1.70;
- OOS expectancy >0;
- OOS Sharpe >=1.50;
- OOS Sortino >=2.00;
- observed DD <=10R;
- MC positive >=90%;
- MC p95 DD <=15R;
- payoff >=1.20 or independently reviewed statistical-compensation evidence;
- temporal stability;
- cost robustness;
- anti-leakage audit;
- no outcome-aware runtime logic;
- no catastrophic loss clustering;
- MAE/MFE and loser-anatomy coverage;
- winner-preservation evidence when intelligence changes outcomes/admission;
- sufficient post-quality density;
- fresh-holdout integrity;
- required Risk, CIBO, and independent validation reviews.

### INTERVENTION — CONTINUE WORK

Use when meaningful edge exists but one or more mandatory gates are missing or fail without definitive falsification.

### REJECTED

Use only when evidence supports a terminal falsification such as:
- OOS expectancy collapses;
- fresh holdout falsifies the frozen candidate;
- edge is structurally absent;
- tail/account-survival risk is unacceptable;
- generalization fails decisively;
- success requires leakage, outcome-aware logic, or prohibited overfitting.

## 8. Current classification at freeze

```
INTERVENTION — CONTINUE WORK
```

Reasons:
- Development is strong but cannot certify;
- Validation exact resume is still active at freeze time;
- Reserved greedy V2 remains below the new per-era PF gate of 1.50;
- Sharpe, Sortino, MC, full loss-cluster audit, final cost stress, and final fresh-holdout evidence are not yet complete for the candidate;
- no immutable final candidate has been frozen.

## 9. Engineering loop

Do not stop at the first failed hypothesis:

```
diagnose
→ identify causal failure
→ state mechanism
→ predeclare hypothesis
→ implement
→ test
→ falsify or advance
```

No post-result threshold hunting on consumed Reserved. No density-first optimization.

Priority:

> Reduce avoidable losers without destroying winners, while preserving causal validity and temporal generalization.
