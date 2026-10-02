# CIBO PROFITABILITY LAB 001

Status: RESEARCH_ONLY / DIAGNOSTIC / NO_PRODUCTIVE_AUTHORITY  
Frozen source of truth: PR #670 `agent/cibo-integrator-ab-001` @ `5f8b9895dae3c851ce459e792e839bb994f8b5da`  
Observed capability run: `37075080556`  
Observed final artifact: `11256800358`  
Observed reused-batch artifact: `11256450732`  
Validation class: `NON_CERTIFYING_REUSED_HOLDOUT`

## Owner directive and mission

The seven Traders are **test population generators**, not the object of optimization and not candidates for post-hoc acceptance/rejection.

The laboratory question is:

> Can CIBO process the complete opportunity stream through all applicable cognitive, CE2I, CMA, Risk, capital-science, Compound and Portfolio capabilities, and can that full orchestration improve survival and portfolio economics without mutating Trader edge?

The primary laboratory hypothesis is **UNDER-UTILIZATION / UNDER-ORCHESTRATION OF CIBO CAPABILITIES**.

Run #28 proved that the end-to-end software path executes, but it did **not** prove that every applicable CIBO capability participated at every eligible decision epoch. The laboratory must therefore measure capability utilization before attributing negative economics to the Traders.

"Sacar a flote todos los trades" is defined operationally as:

- every emitted opportunity enters a complete CIBO decision pipeline;
- every applicable capability is either APPLIED or produces an explicit fail-closed/non-applicable reason;
- CIBO may reject, reduce, defer, protect, derisk, preserve, compound or allocate an opportunity, but it may not silently skip an applicable capability;
- the objective is positive portfolio economics plus survival, not forcing every individual trade to become a winner;
- no Trader methodology/edge is changed inside this laboratory.

This laboratory is causal diagnosis, not outcome-aware optimization. The observed 2014-10-19 -> 2015-04-19 reused holdout is evidence for hypotheses only. It is forbidden to select thresholds, weights, Trader inclusion, tool eligibility, sizing rules, compound speed, or treatments because they improve this observed outcome.

Any proposed CIBO mechanism/orchestration change must be preregistered and later evaluated on a separate development/forward population before any certification claim.

## Observed economics

- MINIMAL_SEED_ONLY: 241 executions, ending capital about USD 0.51, net P/L about -USD 59.49.
- FULL_CIBO_CORE: 107 executions, ending capital about USD 30.85, net P/L about -USD 29.15.
- FULL_CIBO_COMPOUND_PORTFOLIO: 183 total executions, ending capital about USD 4.20, net P/L about -USD 55.80.
- Core structural P/L before provider execution adjustment: about -USD 20.16.
- Core provider execution adjustment: about -USD 9.00.
- Compound incremental structural P/L before provider execution adjustment: about -USD 20.60.
- Compound incremental provider execution adjustment: about -USD 6.04.
- Therefore provider cost materially amplifies losses but is not the primary cause: the structural treatment is already negative before costs.

## Finding F01 — expectation input is a static Trader prior

For every opportunity inside a given Trader, the observed ratio

`expected_net_value_usd / stop_risk_usd`

is exactly constant.

Observed frozen prior expected return-on-stop-risk:

| Trader | Frozen prior expected R | Observed average gross R | Sign agreement |
| --- | ---: | ---: | --- |
| VT08_FOREX | -0.098214 | +0.270443 | NO |
| R34_XAUUSD | +0.011239 | +0.117574 | YES |
| R38_EURUSD | -0.074066 | +0.052739 | NO |
| R43_GBPUSD | +0.045402 | -0.138756 | NO |
| R38_GBPJPY | +0.277245 | -0.234500 | NO |
| R42_AUDJPY | +0.155581 | -0.316628 | NO |
| VT31_NAS100 | +0.298188 | +0.092618 | YES |

Five of seven Trader signs disagree on this observed window.

This does not authorize changing the prior from the observed outcome. It establishes a laboratory hypothesis: a static Trader-level prior may be too coarse to rank individual opportunities and may transfer poorly across market regimes.

## Finding F02 — zero-selection lanes are expectation-gated, not infrastructure-blocked

VT08_FOREX emitted 27 opportunities and R38_EURUSD emitted 109 opportunities.

Their representative STABLE decisions had ample deployable capital and QORE Risk was not the blocker. Allocation rows were rejected because `adjusted_net_value_usd` was non-positive under the frozen prior.

Observed MINIMAL_SEED_ONLY P/L:
- VT08_FOREX: about -USD 0.45.
- R38_EURUSD: about +USD 4.09.

The EURUSD result is a direct diagnostic miss: the prior excluded the complete lane even though the observed baseline population was net positive. This is evidence of expectation-transfer/calibration risk, not permission to include EURUSD post hoc.

## Finding F03 — selection quality is inconsistent

Observed gross R, selected versus excluded:

- R34_XAUUSD: selected average +0.2925R; excluded +0.0715R.
- R43_GBPUSD: selected average -0.3043R; excluded -0.0769R.
- R38_GBPJPY: selected average -0.2680R; excluded -0.2227R.
- R42_AUDJPY: selected average -0.1073R; excluded -0.3720R.
- VT31_NAS100: selected average -0.3439R; excluded +0.2410R.

The selector improved AUDJPY and XAUUSD on this observed window, but materially inverted VT31 and worsened GBPUSD/GBPJPY.

No threshold or feature may be retuned from these outcomes. The laboratory must determine whether predecision features contain enough information to rank setup-specific expectancy before future outcomes.

## Finding F04 — exposure geometry can invert positive unweighted R

R34_XAUUSD selected 15 opportunities with about +4.39R unweighted, but generated about -USD 3.10 structural P/L before provider costs.

Observed average initial stop risk:
- winning XAUUSD selections: about USD 1.91;
- losing XAUUSD selections: about USD 2.55.

Losses therefore carried about 1.33x the average initial stop risk of winners.

This is not evidence to normalize risk post hoc. It establishes a capital-efficiency question: broker minimum volume plus heterogeneous structural-stop distance can transform positive setup-level R expectancy into negative dollar expectancy.

## Finding F05 — Compound magnified a negative selected surface

Compound/Portfolio added 76 executions on the same Core selection surface and produced about -USD 26.64 incremental realized P/L.

Incremental compound P/L by Trader:
- R34_XAUUSD: about -USD 5.15.
- R43_GBPUSD: about -USD 1.39.
- R38_GBPJPY: about -USD 14.90.
- R42_AUDJPY: about -USD 5.21.

The overlay used realized-profit-only funding and QORE Risk remained sovereign. The mechanism failure is economic: additional exposure was applied to a selected surface whose realized structural expectancy was negative.

GEN-C1, GEN-C3 and GEN-C5 were applied. GEN-C6 was reported JUSTIFIED_NOT_APPLICABLE in this ablation. This laboratory must explicitly distinguish "compound accounting works" from "compound policy adds economic value."

## Finding F06 — provider costs are secondary, not primary

FULL_CIBO_CORE:
- structural before execution adjustment: about -USD 20.16;
- provider adjustment: about -USD 9.00;
- realized net: about -USD 29.15.

Compound increment:
- structural before execution adjustment: about -USD 20.60;
- provider adjustment: about -USD 6.04;
- realized increment: about -USD 26.64.

Removing provider costs would improve results but would not make either treatment positive.

## Finding F07 — the reused 2014-2015 profitability replay is temporally anachronistic for learned expectation

The active expectation prior is `CIBO_PHASE20_TRAIN_PRIOR_V1`.

Its code declares the TRAIN window:

- start: `2021-09-23T05:00:00+00:00`
- end: `2022-03-09T17:00:00+00:00`

The reused capability replay evaluates decisions in:

- `2014-10-19 -> 2015-04-19`.

Therefore the expectation model used by the allocator was learned more than six years after the historical decisions it is being asked to score.

The contract correctly prevents reading the 2014-2015 outcome during the decision itself, but setting `expectation.as_of` to the historical decision timestamp does not make a 2021-2022 learned parameter historically available in 2014.

Disposition:

- run #28 remains valid evidence that the software stack can execute end-to-end under a non-certifying backcast;
- run #28 is not valid evidence of causal economic profitability for the complete learned CIBO stack;
- no profitability treatment may be selected from its economic outcome;
- Profitability Lab must use chronological train -> forward validation order for every learned CIBO component.

The same temporal-availability audit must be applied to cognitive memory, regime models and any other learned/frozen artifact before economic conclusions are accepted.

## Full-infrastructure utilization requirement

The next laboratory replay must emit a per-opportunity utilization ledger covering the complete CIBO stack:

### Cognitive
- CF01..CF19.

### CE2I
- T01..T20.

### Capital science / Compound
- GEN-C1..GEN-C14.

### Capital and execution governance
- CIBO Cognitive routing;
- CE2I regime selection;
- CMA capital-source selection and sole sizing authority;
- QORE Risk ALLOW/REDUCE/REJECT;
- provider economics / T11;
- realized-profit release / T20;
- Compound capital;
- Compound Portfolio;
- Sequential Compounding;
- Internal Capital Market;
- Profit Preservation;
- Adaptive Compound Speed;
- Robust Growth/Ruin Capacity;
- Capital Digital Twin;
- Multi-Period MPC;
- Crisis Capital Intelligence;
- Meta-Capital Memory.

For every opportunity and every capability, one canonical disposition is required:

- APPLIED;
- REGIME_BLOCKED;
- FAIL_CLOSED;
- JUSTIFIED_NOT_APPLICABLE;
- NOT_INTEGRATED.

A capability that is implemented but never reached because the test harness bypassed its input path is a **LAB COVERAGE FAILURE**, not evidence that the capability is unnecessary.

The laboratory must distinguish three different questions:

1. **Implemented?** — code/contract exists.
2. **Eligible?** — predecision state says it can legally participate.
3. **Applied?** — it actually consumed the opportunity/state and affected or confirmed the decision.

Only (3) counts as runtime utilization.

## Laboratory workstreams

### L1 — Opportunity-specific expectation science

Goal: determine whether CIBO can produce a causal setup-specific expected value distribution instead of a constant Trader prior.

Required inputs must be available strictly before decision time. Candidate feature families may include already-frozen Trader context, regime state, cognitive outputs, target geometry, structural-stop geometry, provider economics, capital duration and portfolio state.

Forbidden:
- choosing features because they correlate with the observed run #28 outcome;
- training on the reused holdout;
- reading post-entry path;
- using realized P/L to decide the same opportunity.

Deliverable: preregistered estimator protocol and calibration diagnostics on development folds.

### L2 — Full-trade CIBO orchestration attribution

For every emitted opportunity, record:
- raw Trader opportunity;
- entry into CIBO Cognitive;
- CF01..CF19 eligibility/application;
- causal expectation surface;
- regime posture;
- T01..T20 eligibility/application;
- GEN-C1..GEN-C14 eligibility/application;
- CMA capital-source decision;
- CMA sizing/volume expression;
- QORE Risk disposition;
- provider-economics adjustment;
- protection/derisk/optionality actions;
- portfolio competition/netting/internal-capital-market actions;
- Compound/Portfolio actions;
- settlement and released-capital actions;
- explicit reason for every capability not applied.

The laboratory must not treat a Trader-level zero-selection result as sufficient explanation. It must explain the complete CIBO path for every opportunity.

Deliverable: a per-opportunity CIBO utilization matrix plus aggregate utilization rates for every capability.

### L3 — Dollar-expression / minimum-volume distortion

Measure, without changing Trader geometry:
- structural outcome in R;
- minimum executable volume;
- stop-risk USD at minimum volume;
- margin USD;
- provider cost;
- winner versus loser stop-risk distribution;
- exposure-per-risk and exposure-per-margin;
- cases where positive unweighted R becomes negative weighted dollar P/L.

Deliverable: capital-efficiency diagnostics, not a new sizing policy.

### L4 — Compound causal ablation

Use identical predeclared populations for N vs N+1 comparisons.

Ablate one mechanism at a time:
- profit graduation;
- sequential compounding;
- internal capital market;
- profit preservation;
- adaptive compound speed;
- robust growth/ruin capacity;
- digital twin usage;
- multi-period MPC;
- crisis intelligence;
- meta-capital memory.

The observed run #28 may not select a winner. New treatments require development/forward evidence under the existing CIBO_COMPOUND_CAUSAL_ABLATION_PROTOCOL_V1 rules.

### L5 — Provider economics sensitivity

Report structural P/L and provider-adjusted P/L separately.

Stress only predeclared provider-cost scenarios and current empirical provider terms. Do not tune the strategy to one cost realization.

### L6 — Cognitive/CE2I contribution accounting

Repair the CF01..CF19 reporting identity mismatch and produce a per-opportunity function ledger.

Every function must report one of:
- APPLIED;
- REGIME_BLOCKED;
- FAIL_CLOSED;
- JUSTIFIED_NOT_APPLICABLE;
- NOT_INTEGRATED.

Non-application always requires a reason.

## Exit criteria from laboratory

CIBO may leave this laboratory only when:

1. every emitted opportunity is accounted for through the complete CIBO pipeline;
2. CF01..CF19, T01..T20 and GEN-C1..GEN-C14 have explicit runtime utilization/accountability;
3. no implemented/applicable capability is silently bypassed by the exam harness;
4. the expectation mechanism is setup-specific or there is evidence that a static prior is sufficient;
5. calibration and ranking are evaluated on development/forward folds not chosen from run #28;
6. capital-expression distortion is quantified and bounded;
7. Compound/Portfolio mechanisms demonstrate incremental economic value under causal ablation, rather than merely functioning mechanically;
8. provider-adjusted portfolio economics are positive where certification requires it;
9. no outcome-aware tuning, leakage, LIVE, real capital, production or merge authority was used.

## Governance

- Research only.
- No LIVE.
- No real capital.
- No production.
- No broker mutation.
- No merge authority.
- No outcome-aware tuning.
- Run #28 is diagnostic evidence only.
