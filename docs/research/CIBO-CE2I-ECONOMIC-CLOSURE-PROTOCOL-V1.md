# CIBO CE2I Economic Closure Protocol V1

Status: **PREREGISTERED BEFORE QUALIFYING FORWARD ECONOMIC OUTCOMES**

Identity:

`CIBO_CE2I_ECONOMIC_CLOSURE_PROTOCOL_V1`

Scope owned by Architect A:

`T04 / T06 / T07 / T08 / T09 / T10 / T12 / T13 / T14 / T15 / T18`

T05 and T19 are already terminal mechanical contracts and are not reopened.
Provider/execution tools owned by Architect B are outside this protocol.

## Universal causal comparison law

Every economic claim in this protocol requires:

1. the same frozen decision population for control and treatment;
2. the same Trader setup/side/entry/stop/target/thesis;
3. the same provider-valid execution/economic facts;
4. the same QORE Risk boundary;
5. the same CMA/account-capital truth;
6. the same chronological horizon;
7. identical outcome-coverage requirements;
8. no pre-freeze decisions;
9. no synthetic replacement for missing provider economics;
10. no treatment selection after outcome inspection.

If population equality cannot be proven, the comparison is invalid.

The sealed 2017H1 holdout is excluded from development.

## Universal economic gate

All tools use the same non-compensatory principle already frozen in GEN-C9:

`CIBO_GENC9_NONCOMPENSATORY_ECONOMIC_GATE_V1`

No CE2I tool may pay for worse safety with higher return.

Mandatory safety dimensions include, where applicable:

- ruin / insolvency incidence;
- capital-capacity or conservation breaches;
- maximum and tail drawdown;
- peak plausible loss;
- minimum realized capital;
- underwater duration and recovery;
- margin fragility;
- provider failures;
- concentration / starvation failures;
- loss of required optionality;
- violation of Risk or CMA authority.

Only after safety is non-worse may a treatment claim strict economic
improvement.

No weighted score can rescue a failed safety dimension.

## Universal replication law

A treatment that appears useful in aggregate is still not replicated.

Required temporal verdict:

```text
WF1 PASS
WF2 PASS
WF3 PASS
WF4 PASS
---------
REPLICATED
```

Anything below 4/4 remains unreplicated/falsified under the preregistered
criterion.

## T04 — Risk Efficiency

Research question:

Does the marginal capital decision improve robust economic output per true
monetary stop-risk dollar without worsening safety?

Required evidence:

- true monetary stop risk;
- provider-valid economics;
- realized outcomes;
- incremental portfolio risk;
- tail/drawdown evidence.

Forbidden:

- nominal lot as risk proxy;
- margin as risk proxy;
- leverage as the objective;
- future expectancy.

Primary economic signals:

- realized economic output / plausible-loss burden;
- realized economic output / true stop-risk;
- capital productivity.

## T06 — Profit-Funded Expansion

Research question:

Does deploying already-realized net profit as bounded expansion produce
strictly better robust economic value than leaving that profit unexpanded?

The treatment may use only reconciled realized profit after costs.

Forbidden:

- floating PnL as funding;
- loss-triggered expansion;
- base-capital relabeling;
- martingale/recovery behavior.

Safety cannot worsen merely because expansion is "profit funded."

## T07 — Protected-Capacity Expansion

Research question:

Does a separately frozen protected-capacity policy add robust value without
misrepresenting accounting protection as provider guarantee?

Required:

- reconciled protected-capital evidence;
- exact protection class;
- policy evidence;
- explicit provider guarantee evidence if and only if a broker guarantee is
  claimed.

Missing provider guarantee evidence can never be inferred.

## T08 — Portfolio Netting

Research question:

Does using proven current factor/net exposure reduce duplicated portfolio risk
or improve capital efficiency without hiding true gross/plausible loss?

Required:

- causal factor map;
- current position exposures;
- contemporaneous correlation/factor state;
- provider/account economics.

Forbidden:

- fabricated covariance;
- synthetic hedge credit;
- synthetic netting credit;
- assuming historical correlation stability without evidence.

The economic treatment is allocation based on proven incremental exposure, not
a bookkeeping reduction of risk.

## T09 — Opportunity Competition

Research question:

Under real scarcity, does allocating scarce capital among simultaneously valid
opportunities improve portfolio economic value relative to the frozen control?

Required:

- same opportunity set at decision time;
- same capital source truth;
- same Risk/provider constraints;
- simultaneous/scarce capital condition.

Abundance-only evidence cannot prove a scarcity allocator.

Starvation and concentration are mandatory safety dimensions.

## T10 — Capital Velocity

Research question:

Does releasing/reusing capital sooner improve realized economic output per
unit of capital-at-risk time without degrading expectancy or safety?

Required:

- authoritative deployment timestamp;
- authoritative terminal/release timestamp;
- realized output;
- capital-minutes;
- provider-valid costs.

A shorter holding time alone is not economic value.

Primary signal:

`realized economic output / risk-capital time`

subject to non-worse safety and expectancy.

## T12 — Regime-Adaptive Capitalization

Research question:

Does selecting which capital tool is eligible from a **causal current regime**
improve economic results relative to fixed eligibility?

T12 may change tool eligibility only.

Forbidden:

- regime score -> lot size;
- future regime labels;
- post-outcome regime relabeling;
- using T12 to bypass another tool's own failed gate.

The selected downstream tool must still pass its own contract.

## T13 — Drawdown Reserve

Research question:

Does reserving capital during preregistered drawdown/loss-cluster states
preserve survival/optionality and improve robust economic value versus continued
deployment?

Forbidden:

- future opportunity identities;
- outcome-aware reserve activation;
- declaring reserve valuable solely because later losses happened.

Opportunity-density evidence must be decision-time causal evidence.

## T14 — Dynamic De-risking

Research question:

Can current plausible loss / capital consumption be reduced while retaining
economically useful participation?

Required:

- causal current position path;
- current protection state;
- provider execution cost of de-risking;
- post-action realized economics.

A reduction in nominal exposure is not sufficient.

The treatment fails if lower risk is achieved only by destroying economic value
beyond the non-compensatory gate.

## T15 — Capital Optionality

Research question:

Does preserving capacity for later valid opportunities add robust economic
value compared with spending that capacity now?

Forbidden:

- knowledge of future opportunity identity/outcome;
- oracle future-arrival schedules;
- retrospective "we should have waited" labels.

Permitted:

- causal current capacity;
- already-known scheduled opportunities;
- preregistered decision-time opportunity-arrival evidence.

Optionality must be measured through later usable capacity and realized
opportunity value, not through an invented shadow price.

## T18 — Cross-Trader Capital Allocation

Research question:

Does account-level allocation across simultaneously valid Trader opportunities
improve robust portfolio value while preserving Trader sovereignty?

T18 may allocate capital only.

It may not alter:

- Trader methodology;
- side;
- entry;
- structural stop;
- target;
- thesis;
- validity/expiry.

Required safety dimensions:

- portfolio tail risk;
- Trader starvation;
- concentration;
- provider/Risk/CMA feasibility.

## Stress law

Each tool must face the stress family relevant to its economic mechanism,
including as applicable:

- losses-first;
- winner drought;
- correlation convergence;
- margin hike;
- capital lockup;
- gap/slippage;
- early-generation losses.

A tool cannot pass only because the unstressed path is favorable.

## Terminal disposition law

After valid fresh evidence, each tool must receive exactly one terminal
scientific disposition:

- `COMPLETED_AND_PROVEN` if its preregistered economic claim is proven;
- `FALSIFIED_AND_CLOSED` if the claim fails;
- `SUPERSEDED_WITH_PROVEN_LINEAGE` only with explicit proven successor lineage;
- `EXTERNAL_DEPENDENCY_BLOCKED` only when required external evidence is
  genuinely unavailable.

No tool remains indefinitely "implemented" merely because its economic result
is inconvenient.

## Non-claims

This protocol does not claim any of the eleven tools has passed.

It freezes the economic question and evidence law before Architect A receives
the qualifying provider-valid forward population from Architect B.
