# CIBO T08 Factor / Correlation Lineage V1

Status: **A1 CAUSAL LINEAGE CONTRACT / NO NETTING AUTHORITY**

Identity:

`CIBO_T08_FACTOR_CORRELATION_LINEAGE_V1`

## Purpose

T08 asks whether apparent diversification represents distinct economic factor
risk or correlated exposure disguised as diversification.

This A1 contract joins two already-existing causal surfaces:

- the pre-decision T08 correlation audit;
- the structural-stop T08 factor-risk mapping.

It then computes deterministic overlap/concentration facts without granting any
runtime netting credit.

## Required invariants

The lineage requires:

- exactly four temporal correlation folds;
- minimum sample coverage already met;
- correlation matrix identified;
- directional stability observed;
- one unique factor-risk mapping per signal;
- exact decision-time equality between correlation state and mapping;
- identical correlation sample lineage;
- structural stop risk conserved exactly;
- no mapping already marked as certified;
- no netting credit already authorized.

## Reported facts

For every active factor the report exposes:

- gross factor risk;
- signed net factor risk;
- cancellation implied by opposing exposures;
- fraction of total gross factor risk;
- number of mapped opportunities using that factor.

This allows later scientific gates to distinguish genuine factor diversity from
hidden concentration or cancellation.

## Scientific boundary

A complete lineage is **not** a T08 scientific PASS.

T08 still requires:

```text
T08_FRESH_OOS_NETTING_UTILITY_REQUIRED
T08_STRESS_AND_WF1_WF4_REPLICATION_REQUIRED
```

The lineage grants no productive, LIVE, real-capital, PRE_EXAM, integration or
certification authority.

It is a sidecar scientific artifact for later consumption by the Integrator.
