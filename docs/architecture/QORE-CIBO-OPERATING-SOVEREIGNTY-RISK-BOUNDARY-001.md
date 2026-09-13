# QORE-CIBO-OPERATING-SOVEREIGNTY-RISK-BOUNDARY-001

Checkpoint: 2026-09-13

Status: APPROVED R3.17 ARCHITECTURAL CONTRACT — RESEARCH / DEMO ONLY

## Purpose

Formalize the operating boundary requested for CIBO inside QORE:

```text
CIBO OWNS OPERATING MANAGEMENT.
RISK OWNS CAPITAL-EXPOSURE AUTHORIZATION.
CIBO MAY NOT BYPASS RISK.
```

This contract does not grant LIVE or production authority. It defines how CIBO
may manage Traders while preserving Risk sovereignty.

## CIBO operating sovereignty

Within the Trader-management domain CIBO may decide, using governed evidence and
its cognitive/executive state, whether a managed Trader should operate under any
of these postures:

- `BUILD`
- `PROTECT`
- `BANK`
- `ATTACK`
- `LOCK`
- `REDUCE`
- `SUSPEND`

These are CIBO decisions. Risk does not choose the strategic posture.

CIBO may use the Trader Capability Profile, certified performance evidence,
market/regime evidence, account state, protected profit, free cushion,
correlation/concentration evidence, challenge progress, operating limitations,
freshness and uncertainty when choosing the posture.

The contract is intentionally not limited to BANK -> ATTACK. Those states are
one concrete use of the wider Trader Manager authority.

## Risk sovereignty

Every CIBO posture that can expose capital emits a `CiboRiskRequest`.

```text
CIBO RISK REQUEST != RISK AUTHORIZATION
```

Risk remains the only authority that may convert the request into executable
capital exposure. Risk may:

- `ALLOW`;
- `REDUCE`;
- `REJECT`.

Risk may never be bypassed by CIBO, a Trader, Portfolio, Execution or an
experiment.

CIBO may set a stricter capital ceiling than Risk would otherwise allow. Risk
may always reduce that ceiling further. CIBO may never force Risk to authorize
more exposure.

## Capital protection

CIBO may decide that realized/retained profit becomes protected capital. A BANK
decision is monotonic: previously banked capital cannot be silently unbanked.

CIBO may request ATTACK only when:

- protected profit exists above starting equity;
- unprotected free cushion remains positive;
- the request is bound to Risk-envelope evidence.

Risk still checks the full worst-case exposure against all applicable limits,
including daily loss, total drawdown, heat, correlation, broker constraints and
other account policy.

## Trader authority

The Trader remains authoritative for its own frozen methodology and setup.

CIBO does not become the Trader merely because it manages the Trader.

For VT-08 R3.17 specifically:

```text
VT-08 -> generates the setup/entry identity
CIBO  -> chooses operating posture
Risk  -> authorizes/reduces/rejects exposure
Execution -> executes only authorized intent
```

R3.17 does not permit CIBO to invent, redirect or reverse VT-08 entries.

## Execution boundary

CIBO operating decisions contain no provider-native order fields and no
`RiskAuthorization`. They do not submit an order.

```text
CIBO MANAGEMENT != EXECUTION AUTHORITY
CIBO POSTURE != BROKER ORDER
```

Execution remains downstream of the formal Risk authorization path.

## Research binding

R3.17 uses an explicitly `research_only` CIBO operating authority because its
2020-2022 and 2024-2026 evidence windows are already consumed.

Research authority cannot be confused with DEMO/LIVE execution authority.

The production/DEMO form of this contract must bind to an exact prior
`CiboManagementDecision` in `SELECTED` state with
`CIBO_MANAGED_TRADERS_RISK`.

## R3.17 safety contract

The current experiment additionally enforces:

- internal daily drawdown ceiling: 4.75%;
- internal capital drawdown ceiling: 4.95%;
- provider-style 5.00% daily drawdown must never be touched;
- 5.00% capital drawdown must never be touched;
- Risk sizes or rejects exposure after CIBO chooses the posture;
- no LIVE, real-capital, merge or READY authority.

## Constitutional summary

```text
CIBO DECIDES WHAT OPERATING POSTURE QORE SHOULD TAKE.
RISK DECIDES HOW MUCH CAPITAL MAY ACTUALLY BE EXPOSED.
RISK HAS VETO.
CIBO CANNOT BYPASS RISK.
EXECUTION CANNOT BYPASS EITHER.
```
