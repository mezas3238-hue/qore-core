# VT-08 Index C2 R1 — CIBO Stop-Protection Transfer Freeze

Checkpoint: 2026-09-13

Status: RESEARCH ONLY / POST-R1 TRANSFER HYPOTHESIS / NO PROMOTION AUTHORITY

## Parent and immutable Trader stream

- Parent PR: #535.
- Frozen R1 replay HEAD: `5232540cdb444473ddf0bfae01beb2e672cea344`.
- R1 pre-economic methodology freeze: `31bee8643cb09659a66e9ed793c1cb2bf9ba6353`.
- R1 official run: `34772299203`.
- R1 official artifact: `10323025742`.
- R1 signal/trade sample: 152 modeled trades across NAS100, SP500 and US30.

This study MUST preserve the exact R1 signal identity, entry, original Protected-Swing stop, 2R target, 02/06/10 America/New_York anchors, market set, side, daily cardinality and H4 containment. CIBO is not allowed to generate, delete, filter, redirect or reverse an R1 signal.

## Why this study exists

CIBO is QORE's Trader-management brain. Historical VT-08 R3.16/R3.17 research already established a constitutional split in which VT-08 owns signal generation, CIBO owns management posture/protection requests, Risk remains sovereign over capital exposure, and Execution receives authority only from Risk.

The index R1 study therefore asks a narrower causal question first: can the already-existing CIBO intratrade stop-protection families reduce full-stop damage and drawdown on the exact frozen R1 signal stream without changing signal selection?

## Frozen transfer families

These policies are copied unchanged from VT-08 CIBO R3.16 and were defined before this index CIBO experiment. They are transfer hypotheses, not index-tuned parameters and not TTrades source rules.

1. `off`: no CIBO stop ratchet.
2. `soft`: favorable +0.75R -> stop -0.50R; +1.25R -> stop 0.00R; +1.60R -> stop +0.50R.
3. `be050-lock050-at100`: favorable +0.50R -> stop 0.00R; +1.00R -> stop +0.50R.
4. `aggressive`: favorable +0.50R -> stop 0.00R; +1.00R -> stop +0.50R; +1.50R -> stop +1.00R.

No new thresholds may be introduced after CIBO index outcomes are observed without a distinct candidate identity and new freeze.

## Conservative M15 execution semantics

For every exact R1 trade:

- the stop active at the OPEN of an M15 bar is evaluated before the target on that bar;
- then the 2R target is evaluated;
- only if neither exits does the bar's favorable excursion update the CIBO stop for later M15 bars;
- a threshold reached inside the current M15 bar cannot retroactively protect that same bar;
- the original Protected-Swing stop is the initial stop at -1R;
- the original R1 2R target remains unchanged;
- if neither stop nor target exits by the R1 four-hour lifecycle boundary, the position exits at the final retained M15 close exactly as R1 does.

This ordering is deliberately conservative and matches the earlier CIBO replay semantics.

## Exact retained inputs

The workflow must consume:

- exact R1 artifact `10323025742` to obtain immutable trade identity/geometry;
- exact retained source-run market evidence from run `34661791159` / software SHA `a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0` for NAS100, SP500 and US30 M15 paths.

Every policy must reconcile to exactly the same 152 R1 signal keys. Any missing/duplicate signal, market, bar or geometry mismatch fails closed.

## Required evidence

For control and each CIBO policy report, at minimum:

- signal count and exact identity hash;
- W/L/flat;
- full-stop count;
- CIBO-protected-stop count;
- target count;
- H4-containment count;
- total R;
- mean R;
- profit factor;
- maximum R drawdown;
- maximum losing streak;
- by market;
- by 02/06/10 anchor;
- by long/short;
- by calendar year;
- first/second chronological half.

Also report delta versus `off`: full stops avoided, protected exits added, total-R delta, mean-R delta and max-drawdown delta.

## Adjudication boundary

This is consumed-evidence exploratory research. A policy performing best here does NOT become an execution rule. The study may identify mechanisms and candidates only.

No selection of a policy based on these outcomes may grant:

- DEMO_ELIGIBLE;
- CIBO_REVIEW authority for promotion;
- RiskAuthorization;
- LIVE authorization;
- Production authorization;
- real-capital authority.

Any later promotion requires a separately frozen operating policy and genuinely fresh unseen validation.

## Constitutional split

`VT-08 R1 signal != CIBO decision != RiskAuthorization != ExecutionSubmission`

CIBO may protect/manage; it may not impersonate Trader, Risk or Execution.