# CIBO COMPOUND — ADVERSARIAL STRESS MATRIX V1

Status: PREREGISTERED / RESEARCH-ONLY / NO MARKET-PROBABILITY CLAIM

Policy:

`CIBO_COMPOUND_ADVERSARIAL_STRESS_MATRIX_V1`

Digest:

`sha256:99ef9dbf2f6c98b161ee5d04568ba0b89bd6dc5d5f8b11cda2f10ef2f64ac46d`

The stress matrix is frozen before evaluation on the real Compound population.

Required stress families:

- LOSSES_FIRST;
- WINNER_DROUGHT;
- CORRELATION_CONVERGENCE;
- MARGIN_HIKE;
- CAPITAL_LOCKUP;
- GAP_AND_SLIPPAGE;
- GEN_N_LOSSES_EARLY.

Every transformed surface is replayed through the unchanged dependency-aware
Compound Monte Carlo adapter.

A stress path may intentionally become impossible. Missing GEN-N capital,
risk/margin exhaustion or rejected episodes are evidence of fragility and must
remain visible.

Stress frequencies are not market probabilities.

Stress success alone is not certification; fresh OOS and temporal replication
remain independent non-compensatory gates.
