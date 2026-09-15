# Turtle Soup Candidate R6 — Re-entry Causal Addendum

Status: **FROZEN BEFORE SUCCESSFUL ECONOMIC REPLAY**

Research round: `turtle-soup-candidate-r6-reentry-exp1`

The first R6 workflow attempt failed at Python syntax compilation before any evidence download or economic replay. No R6 P&L was observed before this addendum.

## Conservative stop-container rule

To remove an unnecessary causal degree of freedom, R6 adopts the following stricter convention:

- the M15 bar that contains Attempt-1 stop-out is never eligible to generate the experimental re-entry;
- the adverse extreme of that stop-containing M15 bar is incorporated into the re-entry protective-stop state;
- re-entry eligibility begins only at the next M15 bar;
- after that point, ordinary R5 hierarchy applies: M15 first, exact M1 refinement for an ambiguous prospective re-entry bar, and already-frozen provider-native BID ticks only when that exact M1 minute already has frozen tick evidence;
- no new tick acquisition may be triggered by R6 outcomes;
- if the prospective re-entry remains ambiguous at the highest already-acquired admissible resolution, it is censored.

This convention intentionally sacrifices possible same-M15 re-entry fills rather than inventing stop/re-entry ordering. It is `QORE_EXPERIMENTAL_REENTRY`, not source authority.

All other rules in `TURTLE-SOUP-CANDIDATE-R6-EXPERIMENTAL-REENTRY-FREEZE.md` remain unchanged.

Fresh OOS remains closed.
