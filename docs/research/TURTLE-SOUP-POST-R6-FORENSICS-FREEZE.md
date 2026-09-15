# QORE CORE — Turtle Soup Post-R6 Diagnostic Forensics Freeze

Status: `FORENSICS_ONLY`

Root research identity: `turtle-soup-candidate-r1`
Source rejected round: `turtle-soup-candidate-r6-reentry-exp1`
Canonical trader code: `CODE_UNASSIGNED`

## Purpose

Diagnose why Turtle Soup failed after R5/R6 without reopening candidate selection, changing rules, or consuming fresh OOS.

## Immutable input

Only the exact R6 authoritative artifact from run `35023272848`, HEAD `2423f1f72005388fb14d916099bef9a1dac96c3b`, artifact `10418706760` may be used.

The artifact contains the already-consumed R6 report and trades. No new market data may be acquired by this forensics round.

## Questions frozen before diagnostics

1. Is the failure present gross-before-cost, or created mainly by transaction costs?
2. Does Attempt 2 repair Attempt 1 economically, or only improve it while remaining negative?
3. Are losses mostly immediate adverse continuation, or failed reversals after meaningful favorable excursion?
4. Is apparent profitability dependent on rare right-tail winners?
5. Does the payoff distribution deteriorate from pre-Walk-Forward to Walk-Forward even if win frequency does not?
6. Are positive-looking market/side pockets broad and stable, or concentrated/non-stationary?
7. Does any frozen policy escape these structural failure modes?

## Prohibited actions

- no fresh OOS access;
- no market or side deletion;
- no stop/entry/offset retuning;
- no management grid expansion;
- no R7 candidate construction;
- no promotion of a diagnostic segment;
- no Monte Carlo / Risk / CIBO / prop-firm qualification;
- no canonical trader identity assignment.

## Interpretation rule

Forensics may identify a causal failure mechanism and may motivate a future materially new preregistered research identity. It may not convert consumed diagnostics into an approved filter or candidate.
