# CE2I ADR-002 — CIBO Capital Management Authority

Status: **OWNER-DIRECTED / CANONICAL / SUPERSEDES ADR-001**

PR: #651

## 1. Decision

The target architecture changes from "CIBO owns sizing" to:

> **CIBO owns the complete capital-management lifecycle of every Trader opportunity.**

The Trader supplies market opportunity and methodology facts. CIBO decides how capital is deployed,
protected, released, recycled, reserved and expanded around that opportunity.

CE2I is the intelligence/toolbox used by the CIBO Capital Management Authority.

Canonical names:

- **CMA** — CIBO Capital Management Authority
- **CE2I** — Capital Efficiency & Exposure Intelligence toolbox

## 2. Authority split

### Trader owns market methodology

The Trader owns:

- setup validity;
- market/timeframe/session logic;
- side;
- technical entry geometry;
- structural invalidation;
- target/technical objective;
- methodology facts and state;
- signal expiry/cancellation;
- technical facts required by its certification.

The Trader does **not** own capital size.

The Trader does **not** own the final capital allocation.

Legacy Trader risk multipliers/sizing formulas become evidence, not authority.

## 2.1 Owner sizing-authority ratification — 26-SEP-2026

The Owner ratified the following binding architecture law:

> **All active Trader sizing authority is retired. CIBO CMA is the sole runtime authority that may
> determine requested volume for every Trader opportunity.**

Consequences:

- Trader sizing/risk formulas may remain only as `LEGACY_SIZING_BASELINE` evidence for replay,
  reconstruction and certification comparison;
- active Trader runtime paths must emit a volume-free `TraderOpportunityEnvelope`;
- a Trader-provided monetary risk budget must never reach execution as sizing authority;
- execution boundaries must fail closed if a request still carries
  `strategy_requested_risk_usd`;
- QORE Risk may reduce or reject a CIBO request for survival constraints, but it does not restore
  Trader sizing authority;
- removing sizing authority does not remove Trader ownership of technical stop/invalidation,
  target, side or setup validity.

## 2.2 Account-aware capital mission intelligence

CIBO must know **what kind of account it is managing from authoritative account/provider context**.
The capital mission is derived from the account binding and environment; it is never selected by a
GitHub issue, per-trade switch, Trader preference or manual sizing flag.

Canonical examples:

```text
FundedNext + PRODUCTION + Stellar Instant
-> FUNDED_SURVIVAL_COMPOUND

cTrader + DEMO
-> DEMO_CAPABILITY_DISCOVERY
```

The same CIBO brain therefore changes its capital objective by account context while preserving the
same Trader methodology sovereignty and the same anti-cheating/accounting laws.

### FUNDED_SURVIVAL_COMPOUND

External funded capital prioritizes:

- account survival;
- provider rule compliance;
- minimum viable seed;
- preservation of optionality;
- capital competition;
- robust compounding;
- advanced CE2I execution only after sufficient validation.

Research-only capital tools must not become LIVE authority merely because they exist in the registry.

### DEMO_CAPABILITY_DISCOVERY

DEMO exists to measure the maximum causal capability of CIBO.

CIBO may exercise every **implemented, executable and non-rejected** CE2I tool so that QORE can
measure:

- capital productivity;
- cross-Trader allocation;
- multi-tool composition;
- expansion/de-risk behavior;
- capital velocity;
- optionality;
- portfolio interactions;
- failure/rollback behavior.

DEMO capability discovery is **not an absence of controls**. Provider constraints, QORE Risk,
durable capital accounting, reconciliation, no-double-spend, no martingale, causal evidence and
execution economics remain mandatory.

### Architecture consequence

Account context becomes an input to capital intelligence:

```text
ACCOUNT / PROVIDER BINDING
        |
        v
CIBO ACCOUNT CAPITAL IDENTITY
        |
        v
CIBO CAPITAL MISSION
        |
        +--> objective function
        +--> CE2I activation scope
        +--> reserve/optionality priority
        +--> experimentation eligibility
        +--> capital deployment posture
        |
        v
CIBO CMA DECISIONS
        |
        v
QORE RISK HARD GOVERNOR
```

This mission layer may change **how CIBO uses capital**. It never changes the Trader's setup,
technical stop, target or signal validity.

### CIBO CMA owns capital management

CIBO owns every capital decision inside the Risk-authorized envelope:

- initial exposure;
- minimum viable seed;
- size;
- margin usage;
- scaling;
- de-scaling;
- profit protection from a capital perspective;
- capital recovery accounting;
- capital recycling;
- realized-profit redeployment;
- protected-profit redeployment when economically reconciled;
- reserve policy;
- opportunity competition;
- portfolio capital allocation;
- concentration-aware allocation;
- timing of capital expansion;
- capital velocity optimization;
- exposure optionality;
- capital-preserving exit/de-risk requests when compatible with market methodology;
- selection of CE2I tools appropriate to the current market/account state.

### QORE Risk owns hard survivability constraints

Risk is not the sizing strategist.

Risk is the independent hard governor over:

- maximum monetary loss;
- margin headroom;
- provider/funded-account constraints;
- account survival;
- aggregate risk ceiling;
- reservation integrity;
- non-double-spend;
- emergency hard-stop constraints.

CIBO proposes capital actions. Risk may ALLOW, REDUCE or REJECT them when hard constraints require it.

Risk does not decide which CE2I tool is economically best.

### Execution owns broker mutation

Execution only applies a CIBO capital action after Risk authorization.

## 3. Core operating doctrine

Every valid Trader opportunity begins with the **lowest executable capital exposure compatible with
the opportunity and provider**.

The initial objective is not to maximize profit.

The initial objective is:

```text
ENTER THE OPPORTUNITY
WITH THE MINIMUM NEW CAPITAL AT RISK
```

After entry, CIBO continuously evaluates whether the position has created economic capacity that can
be used to increase return without re-exposing the original base capital unnecessarily.

CIBO's target is:

```text
MINIMIZE BASE CAPITAL AT RISK
MAXIMIZE ROBUST ECONOMIC OUTPUT
MAXIMIZE REUSABLE CAPITAL
MAXIMIZE FUTURE OPPORTUNITY CAPACITY
```

No deterministic guarantee of profit is implied. The engineering objective is to improve capital
productivity while preserving survivability.

## 4. Canonical capital lifecycle

### STATE 1 — MINIMAL_SEED

CIBO creates the smallest executable seed.

```text
SEED_VOLUME =
smallest step-aligned volume
that satisfies broker/provider execution constraints
and any indivisible methodology execution constraints
```

Legacy Trader risk scale is ignored as sizing authority.

### STATE 2 — OBSERVE

CIBO observes:

- market path;
- position path;
- realized PnL;
- protected PnL;
- current worst-case loss;
- margin;
- spread/slippage;
- liquidity;
- regime;
- correlation;
- other portfolio opportunities.

CIBO may choose to do nothing.

### STATE 3 — PROTECT_BASE

CIBO prioritizes reducing the amount of original capital that can still be lost.

It may use certified/validated capital tools such as:

- partial realization;
- exposure reduction;
- protected stop state supplied by the Trader methodology;
- hedge/risk-transfer tools if separately certified;
- margin reduction;
- risk reservation release.

### STATE 4 — BASE_RECOVERED

Base capital is considered recovered only from reconciled economic evidence.

CIBO must distinguish:

- floating profit;
- protected floating economic floor;
- realized net profit;
- reserved expansion risk;
- execution/cost reserve.

### STATE 5 — CAPITALIZE

Once capital conditions permit, CIBO may deploy one or more CE2I tools:

- Structural Leverage;
- Margin Efficiency;
- Risk Efficiency;
- Capital Recycling;
- Profit-Funded Expansion;
- Portfolio Netting;
- Opportunity Competition;
- Capital Velocity;
- Execution-Efficient Exposure;
- Regime-Adaptive Capitalization;
- Drawdown Reserve;
- Dynamic De-risking;
- Capital Optionality;
- Hedged Exposure / Risk Transfer;
- Convex / Limited-Downside Exposure when separately supported/certified.

CIBO chooses tools based on the actual market/account/portfolio condition.

### STATE 6 — COMPOUND_OR_RESERVE

Profits/capacity are not automatically redeployed.

CIBO compares:

- redeploy now;
- hold reserve;
- capitalize another Trader;
- reduce exposure;
- preserve optionality.

### STATE 7 — RELEASE

When an opportunity closes or capital is no longer required, CIBO releases/reconciles all associated
capital reservations.

## 5. Capital source accounting

Every capital increase must identify a source.

Canonical source types:

- ORIGINAL_BASE_CAPITAL;
- REALIZED_PROFIT;
- PROTECTED_ECONOMIC_FLOOR;
- RELEASED_RISK_CAPACITY;
- RELEASED_MARGIN_CAPACITY;
- TRUE_PORTFOLIO_NETTING;
- REDUCED_OTHER_EXPOSURE;
- CERTIFIED_LIMITED_DOWNSIDE_CAPACITY.

No source may be counted twice.

## 6. CIBO toolbox law

CIBO must not have one universal leverage multiplier.

It must have multiple capital tools and choose among them.

Every tool must declare:

- eligibility conditions;
- required evidence;
- expected capital effect;
- worst-case loss effect;
- margin effect;
- execution cost;
- portfolio interaction;
- rollback/de-risk condition;
- validation status.

## 7. Prohibitions

CIBO CMA V1 prohibits:

- martingale;
- doubling down to recover a loss;
- adding merely because price moved adversely;
- outcome-aware sizing;
- future leakage;
- counting floating PnL as realized cash;
- double-spending released risk or margin;
- silently increasing the account loss ceiling;
- manufacturing leverage by arbitrarily tightening a structural stop;
- widening a structural stop to support more size;
- hiding risk in correlated positions;
- overriding a Trader's technical signal/structure without a separately validated methodology change.

## 8. Migration of existing Traders

Existing per-Trader sizing becomes **LEGACY_SIZING_BASELINE**.

Examples:

- VT08 symbol BPS sizing;
- R34 governor scale;
- R38 EURUSD cognitive/fragility scale;
- R43 structural/side/rank/DD scale;
- R38 GBPJPY policy/fragility scale;
- R42 AUDJPY two-layer risk scale;
- VT31 certified-risk resolution.

They remain valuable for:

- historical reconstruction;
- baseline comparison;
- evidence about past economics.

They are not the future source of final volume.

Target flow:

```text
TRADER OPPORTUNITY
      |
      v
TRADER OPPORTUNITY ENVELOPE
(no volume authority)
      |
      v
CIBO CAPITAL MANAGEMENT AUTHORITY
      |
      +--> minimum seed
      +--> protect base
      +--> recycle
      +--> expand
      +--> reserve
      +--> compete opportunities
      +--> portfolio capital allocation
      |
      v
CIBO CAPITAL ACTION REQUEST
      |
      v
QORE RISK HARD GOVERNOR
      |
      v
EXECUTION
```

## 9. Certification consequence

Changing capital management can change realized economics even when the Trader signal is unchanged.

Therefore:

- Trader methodology certification remains evidence for the opportunity;
- CIBO capital-management policy requires its own certification;
- CIBO certification must be performed per Trader and portfolio-wide;
- reduced seed and every expansion/de-risk tool must be replayed chronologically;
- no CE2I tool is promoted solely because it improves one metric.

## 10. Immediate engineering order

PR #651 must now prioritize:

1. convert all current Trader sizing into legacy baseline adapters;
2. define a volume-free `TraderOpportunityEnvelope`;
3. implement CIBO minimum-seed sizing;
4. implement capital-source ledger / non-double-spend;
5. implement capital-state machine;
6. bind CE2I tools to explicit eligibility/evidence contracts;
7. replay each Trader with CIBO-owned capital management;
8. compare against legacy Trader sizing;
9. validate portfolio-wide capital efficiency;
10. only then enter shadow/DEMO execution studies.

ADR-001 is retained only as historical context and is superseded by this ADR.
