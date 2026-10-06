# CIBO Generation Current Control V1 — Freeze Candidate

Status: **PRE-C8 AS-IS CONTROL IDENTITY SEALED / ECONOMIC BASELINE POPULATION STILL PENDING**

Control identity:

`CIBO_GENERATION_CURRENT_CONTROL_V1`

Exact candidate Git SHA:

`87d98ced8d56b275823c4472392923ba6a11d769`

This SHA is intentionally **pre-GEN-C8**. GEN-C8 and later work are N+1
research and must not be absorbed retrospectively into their own control.

## Included AS-IS generation

The candidate contains the then-current:

- frozen Phase20 V3 current-CIBO candidate;
- GEN-C1 compound accounting;
- GEN-C2 protected capital floor;
- GEN-C3 Core Compound Portfolio;
- GEN-C4 marginal capital utility evidence;
- frozen GEN-C5 V1 sequential-compounding shadow;
- frozen GEN-C6 V1 Internal Capital Market shadow;
- frozen GEN-C7 V1 profit-preservation/giveback shadow;
- authoritative T20 release/returned-capacity provenance;
- provider instrument-capability registry;
- World Cup sovereign-capital-amplification governing mission;
- requirement→CE2I/GEN-C gap matrix.

## CI evidence at candidate selection

At the time this candidate was selected, all completed required checks on the
exact SHA were SUCCESS, including:

- CIBO Capital Management Authority CE2I;
- GEN-C1;
- GEN-C2;
- GEN-C3;
- GEN-C4;
- GEN-C5;
- GEN-C6;
- GEN-C7;
- Provider Instrument Capability;
- Phase20 Provider Uncertainty;
- Pre-Holdout Checkpoint;
- Phase18 Trader replays that had completed;
- Phase19 Integrated / K / L / N and burned-calibration gates.

The Phase19M workflow's `quality` job was SUCCESS while its downstream
`audit` job remained queued. Therefore:

```text
all_required_ci_green = NOT YET PROVEN
control_sealed        = FALSE
```

The exact-SHA CI evidence is now complete and green: 26/26 required workflows
are recorded as SUCCESS in
`CIBO-GENERATION-CURRENT-CONTROL-CI-EVIDENCE-V1.json`.

The immutable control identity is therefore sealed. This closes control
selection/freeze only; it does **not** fabricate the still-missing fresh
economic baseline population.

## Holdout and policy protection

```text
Phase20 V3 mutated                  = FALSE
2017H1 holdout consumed             = FALSE
outcome data used to select control = FALSE
GEN-C5 V1 modified                  = FALSE
GEN-C6 V1 modified                  = FALSE
GEN-C7 V1 modified                  = FALSE
```

## Economic baseline measurement

The policy/control identity is selected pre-outcome.

Economic measurements must later be bound to the same causal comparison
population. They must not be used to change which SHA became the control.

Required AS-IS measurement families include:

- current Trader opportunity surface;
- current CIBO policy behavior;
- compound state;
- allocation/competition behavior;
- capital utilization and idle-capital state;
- provider-normalized constraints;
- stressed plausible loss;
- return / capital-at-risk / capital-minute;
- drawdown/tail/underwater/recovery;
- profit retention and protected-floor growth.

If a real fresh utilization population is unavailable, the economic baseline
remains explicitly pending; synthetic utilization must not be invented.

## N+1 quarantine

GEN-C8 and later generations may be engineered in shadow, but:

```text
NO C8+ ECONOMIC VALUE CLAIM
NO C8+ PROMOTION
NO C8+ WORLD CUP ATTRIBUTION
```

until this AS-IS control is cryptographically sealed and the comparison
population is bound.

This preserves:

```text
TODAY'S BEST CIBO
IS TOMORROW'S CONTROL.
```


## Machine-seal closure

The N+1 branch now contains a dedicated machine-seal workflow:

`.github/workflows/cibo-generation-current-control.yml`

Verified successful run:

`36725688605`

The workflow materializes the immutable pre-C8 control manifest and reasserts
the exact baseline Git SHA, all-green exact-SHA CI, untouched 2017H1 holdout,
no V3 mutation and no outcome-based control selection.

The following remain deliberately separate:

`AS_IS_CONTROL = COMPLETED_AND_PROVEN`

`AS_IS_ECONOMIC_BASELINE = OPEN`

The second cannot close until a fresh causal population exists. Synthetic
utilization or retrospective invented USD economics are forbidden.
