# CIBO CMA Phase 7 — Observed Economic-Floor Evidence — 2026-09-26

Status: **PASSIVE EVIDENCE / REAL VPS READ-ONLY / NO RUNTIME MUTATION**

## Source observed

Workspace:

`C:\QORE_CTRADER_DEMO_FREE`

Observed runtime identity:

- branch: `agent/ctrader-demo-free-cibo-lab-001`
- HEAD: `c83179b1f4a48d8af5a4370e63e397ab0f66eb39`

Behavior Lab source:

`artifacts\ctrader_demo_live_behavior_lab\case-report.json`

No VPS file, process, broker order, account configuration or runtime state was changed during this inspection.

## Coverage

Observed case-report rows: **875**

| Trader | Cases | Cases with realized PnL | Cases with remaining-stop estimate | Cases with economic-floor estimate | Cases with settlement |
|---|---:|---:|---:|---:|---:|
| VT08_FOREX | 0 identified in case-report trader field | 0 | 0 | 0 | 0 |
| R34_XAUUSD | 23 | 0 | 0 | 0 | 0 |
| R38_EURUSD | 17 | 0 | 0 | 0 | 0 |
| R43_GBPUSD | 18 | 0 | 0 | 0 | 0 |
| R38_GBPJPY | 20 | 0 | 0 | 0 | 0 |
| R42_AUDJPY | 18 | 0 | 0 | 0 | 0 |
| VT31_NAS100 | 4 | 2 | 1 | 1 | 2 |
| UNKNOWN / non-Trader-keyed cases | 775 | — | — | — | 1 |

This means the historical behavior evidence is **not yet sufficient to certify Phase 7 across the portfolio**.

The current complete economic evidence is concentrated in VT31.

## VT31 observed closed cases

### Case A — settled loss

Signal:

`004195ab46dc82573e0a22ed2e31a1de5ceeba01feb2425e7fd6a968e7506833`

Observed:

- requested volume: 0.04;
- requested stop risk: USD 10.2408;
- final settlement: `CTRADER_DEMO_EXIT_SETTLEMENT`;
- realized net PnL: **-USD 10.56**;
- no observed protection event;
- closed/reconciled exit observed.

This case demonstrates why positive-path assumptions cannot release capital.

For a closed settled losing position:

```text
BASE CAPITAL RECOVERED = FALSE
SELF-FINANCING CAPACITY = 0
```

until the final capital-source settlement consumes the corresponding deployed base capacity.

### Case B — partial + settled positive exit

Signal:

`67b10587bf793e37af3c6c64d86de155882729a9ede18b5f53e4f1e65c5f92e6`

Observed:

- initial requested volume: 0.04;
- later observed volume: 0.02;
- requested stop risk: USD 26.0712;
- partial settlement observed;
- final exit settlement observed;
- realized net PnL: **+USD 64.06**;
- estimated initial risk PnL: USD 25.44;
- final estimated remaining-stop PnL: USD 0;
- final estimated economic floor: **+USD 64.06**;
- estimated economic floor: approximately **+2.5181R** relative to the behavior-lab initial-risk estimate.

At final settlement the closed-position economic floor is unambiguous:

```text
remaining open loss = 0
realized net PnL = +64.06
=> base capital recovered
=> positive realized-capital source exists
```

This does **not** prove that expansion would have been correct earlier in the path.

The historical report does not contain enough reconciled protection evidence to determine exactly
when, before final exit, CIBO could safely have crossed from PROTECT_BASE to CAPITALIZE.

## Key finding

The existing Behavior Lab is already strong enough to prove final settlement economics, but not yet
strong enough to prove **real-time capital recovery for every open position**.

For CMA expansion decisions, the required real-time binding must include:

1. broker-confirmed current position volume;
2. broker-confirmed current stop/protection;
3. realized net settlement accumulated for the signal;
4. remaining worst-case stop PnL;
5. commissions/swaps/conversion/slippage reserve;
6. mutation reconciliation status;
7. exact signal/position identity;
8. timestamp/freshness of the reconciled state.

Without these, CIBO remains in:

```text
OBSERVE / PROTECT_BASE
```

and expansion is fail-closed.

## New PR #651 implementation

Phase 7 now contains:

`src/qore/infrastructure/cibo_cma_behavior_binding.py`

It binds Behavior Lab case reports into:

`ReconciledPositionEconomics -> EconomicFloorResult`

but only when reconciliation evidence is explicit.

The adapter refuses to infer protected capital merely from positive floating PnL.

## Historical-vs-new authority boundary

The observed VPS evidence above predates the PR #651 CMA runtime authority switch.

Therefore those historical cases retain their legacy sizing-path observations.

They are used only to validate the economic-floor accounting model.

They are **not** evidence that the new CIBO minimal-seed sizing policy has already executed on the VPS.

## Phase 7 next gate

Next required work:

- add a passive real-time CMA capital observation event to the research runtime;
- bind current broker position + stop + settlements;
- emit base-capital-at-risk / economic-floor / self-financing-capacity;
- do not mutate position sizing from that observation yet;
- collect new CMA-minimal-seed cases;
- compare the observed floor timeline against actual settlement.

Only after that evidence is stable can CE2I expansion tools be considered for shadow decisions.
