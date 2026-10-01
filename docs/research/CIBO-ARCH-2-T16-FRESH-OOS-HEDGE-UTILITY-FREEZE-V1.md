# CIBO Architect 2 — T16 Fresh-OOS Hedge Utility Freeze V1

Status: **FROZEN BEFORE UTILITY POPULATION**

The pre-registered candidates remain exactly:

- NAS100 / USTEC -> US30
- NAS100 / USTEC -> US500

The earlier post-declaration market-structure artifact (run 36817089026,
artifact 11141752922) is calibration evidence only. It is not reused as the
fresh-OOS economic-utility population.

Frozen hedge betas from that immutable calibration:

- US30: 0.9870327967452153507332036422
- US500: 2.124695637073923294021473707

Fresh-OOS rules:

- observations must be strictly later than 2026-10-01T22:20:00Z;
- minimum 32 observations per candidate;
- exactly four contiguous folds;
- no pooled rescue;
- no post-outcome beta refit;
- no candidate-universe expansion;
- each fold charges the conservative maximum observed round-trip execution cost
  from the bounded T16 DEMO execution receipt;
- treatment is target return minus frozen beta times hedge return;
- net protection is control downside semideviation minus treatment downside
  semideviation minus the round-trip cost fraction;
- every one of the four folds must have net protection > 0.

A candidate that fails any fold is not certified. If neither pre-registered
candidate passes, T16 is eligible for `FALSIFIED_AND_CLOSED` rather than
retuning or expanding the universe.

This protocol has no sizing, Risk, execution, LIVE or productive authority and
does not consume Phase22 V2.
