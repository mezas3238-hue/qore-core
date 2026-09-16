# VT-31 Multi-Index Behavior Observatory

## Purpose

This observatory is a consumed-only research system for studying VT-31 across NAS100, SP500 and US30 before any new candidate is created. It is designed to answer how VT-31 behaves across assets, directions, time, structural geometry and cross-index context without turning retrospective labels into trading rules.

## Immutable evidence boundary

The observatory consumes the definitive 780-root tick-corrected ledger and its pre-entry deep-forensics matrix. It never opens a fresh holdout. The current candidate state remains `NO_R9_NOT_CERTIFIED`, `LIVE_AUTHORIZED=FALSE`, `PRODUCTION_AUTHORIZED=FALSE`.

## Analytical layers

### 1. Evidence coverage and censoring

The system measures terminal/no-trade/censored roots by market, side and historical partition. This prevents apparent performance differences from being confused with different data-resolution rates.

### 2. Market and side behavior

For NAS100, SP500 and US30 the system computes sample size, win/loss counts, stressed expectancy at 0.10R friction, profit factor, drawdown, losing streak, return quantiles and terminal-status composition. It repeats the same analysis for LONG/SHORT and market-by-side interactions.

### 3. Structural geometry

The observatory retains the pre-entry geometry already reconstructed from frozen R8/gap05 semantics: signal minute, risk/reference, raid body, confirmation body, raid/reference depth, final-extreme depth, confirmation/extreme latency, displacement beyond anchor, entry location, protected-swing-like state, opposing-series length and distance to opposite 09:00 liquidity.

Distributions are reported separately for each index so that differences in NAS100, SP500 and US30 can be observed without forcing one market's scale onto another.

### 4. Interaction atlas

Predeclared interaction tables include market × side, market × entry family, market × 5-minute signal bucket, market × risk/reference bucket, market × protected-swing-like state, market × prior-day alignment and market × terminal family.

These tables are descriptive only. A positive retrospective cell is not a candidate rule.

### 5. Temporal stability

Quarterly and half-year behavior is produced overall and independently for each market. Periods with at least 10 observations are counted for sign stability. This exposes regime drift, collapses and recoveries instead of hiding them in aggregate statistics.

### 6. Block-bootstrap uncertainty

Each market and market-side group receives a deterministic 2,000-path moving-block bootstrap using block size 5. The output contains p05/p50/p95 mean stressed R and the fraction of bootstrap paths with positive mean. The bootstrap is diagnostic and is not a promotion gate.

### 7. Cross-index behavior

Trades are grouped by NY date to study breadth and synchronization. The observatory records how VT-31 behaves when one, two or three indices signal on the same day, whether directions agree or conflict, pairwise same-day stressed-R correlations and side-agreement fractions for NAS100/SP500, NAS100/US30 and SP500/US30.

### 8. Failure anatomy

Every terminal result is normalized into target, initial-stop, protected-stop or other. Counts are reported overall, by market and by side. This isolates whether an asset fails at initial geometry or later lifecycle management.

### 9. Unsupervised pre-entry regimes

Six deterministic regimes are built with robust-scaled k-means using only pre-entry variables. Terminal R, win/loss, terminal status and all post-entry information are prohibited from clustering.

The regime features are:

- signal minute;
- risk/reference;
- raid body fraction;
- confirmation body fraction;
- raid depth to reference;
- final-extreme depth to reference;
- raid-to-extreme latency;
- raid-to-confirmation latency;
- displacement beyond anchor;
- entry location within reference;
- protected-swing opposing-series length;
- opposite-liquidity distance in R.

After clusters are frozen, outcome statistics and half-year stability are attached only as labels. This permits behavioral discovery without supervised hindsight selection.

## Outputs

The GitHub Actions artifact contains:

- `vt31-behavior-observatory.json`: complete machine-readable atlas;
- `vt31-behavior-trade-matrix.csv`: one terminal trade per row with pre-entry context and outcome label;
- `vt31-behavior-dossier.md`: concise human-readable market summary;
- `git-sha.txt`, source artifact identity/digest and `SHA256SUMS`.

## Governance

This observatory is research infrastructure, not a candidate generator. No bucket, regime, market, side or interaction may be promoted directly into R9. Any hypothesis that emerges from this consumed evidence must be converted into a finite predeclared family and subjected to leakage-free walk-forward before any candidate freeze. Fresh evidence remains sealed until that process is complete.
