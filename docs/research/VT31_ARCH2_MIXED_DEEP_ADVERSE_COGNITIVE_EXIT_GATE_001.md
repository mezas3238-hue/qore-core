# VT31 NAS100 — Mixed Deep-Adverse Cognitive Exit Gate 001

**Owner:** Sergio Meza  
**Status:** PREDECLARED / CONSUMED-EVIDENCE DEVELOPMENT  
**Branch:** `agent/vt31-edge-position-cert-b-001`

## Fixed base

Use the clean admission survivor built on Comparator 005:

- `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
- Breaker SHORT + prior-day rotation + compressed-reference abstention,
  with the bullish recovery exception;
- FVG SHORT + compressed reference + FRESH_LT8M reclaim +
  FAST_LE5M confirmation abstention;
- additional clean entry exclusion:
  Breaker SHORT + prior-day bearish + compressed reference + H1 bullish.

B-side position logic remains Comparator 003.

This base non-degrades PF, mean-R, observed DD, density, winner preservation and
half-year stability 4/4. Recent consumed is approximately:

- PF 2.0171;
- mean +0.7082R/trade;
- observed DD 7.2398R;
- MC positive 90.76%;
- MC p95 DD 14.70R;
- winner count / winner-R 100% preserved.

## Observation-only live discovery

At the first causal material-adverse observation, the already-existing bucket:

`current_open_r <= -0.75R`

combined with management context `MIXED` contained:

- R5: 1 loss / 0 winners;
- recent: 4 losses / 0 winners.

Total: 5 losses / 0 winners.

The `-0.75R` boundary is not newly invented. It already existed in
`_bucket_open_r()` before this attribution.

## Predeclared variants

1. `COMP003_PLUS_MIXED_DEEP_ADVERSE`
   - keep all existing Comparator 003 exits;
   - additionally allow EXIT when:
     - maximum cognition verified;
     - current management context = MIXED;
     - current_open_r <= -0.75R.

2. `COMP003_PLUS_BREAKER_MIXED_DEEP_ADVERSE`
   - same;
   - additionally require entry family = Breaker.

## Causality

The signal is evaluated only on a fully closed causal M1.

If EXIT is authorized, execution occurs at the next M1 open.

No same-bar close execution is allowed.

The decision may not consume:

- future bars;
- terminal result;
- fold/date identity;
- volume;
- position sizing;
- leverage;
- compounding;
- portfolio/capital weighting.

## Frozen adjudication

Against the clean admission survivor require across R5/R6/R8/recent:

- PF non-degrade 4/4;
- mean-R non-degrade 4/4;
- observed DD non-degrade 4/4;
- density >=75%;
- winner count preservation >=80%;
- winner-R preservation >=90%;
- half-year mean/DD non-degrade.

Certification still requires observed DD <=6R.

Fresh holdout remains sealed. A consumed-evidence survivor is not candidate
freeze or certification.
