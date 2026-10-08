# CIBO — Ultra-fast GitHub Trader Lab runtime engineering

**Scope:** research-only CIBO 37772 medium H4M5 and floor seeking sweeps. Do not claim either suite certifies a fresh 3-year holdout.

## Confirmed root causes
1. Parallel Python interpreters each read/parsed six years-of-M5-source partitions; 8–11 processes oversubscribed the shared GitHub host.
2. Even after bounded workers reduced wall time from ~5–7m to ~1–2m, each new runner repeated ~26 s M5 parse.
3. GitHub downloaded and expanded the same three SHA256-custodied manifest/baseline/control ZIPs and six M5 ZIPs every time.

## Architecture

- `scripts/cibo_trader_lab_batch_runner.py`: capped fork workers, parent/shared M5 memory, exact CLI flags per case, fail closed on child error.
- **Window pruning:** retain exactly the union of M5 original slices selected by each of the manifest's trade entry/exit horizons, using the original `bisect_left(opened, entry)` and `bisect_right(closed, exit)` semantics. No lifecycle calculation is approximated. Full source corpus still required to produce the first cache.
- **Prepared source cache:** deterministic gzip+JSON (not pickle), six-symbol fingerprint bound to manifest SHA256, six immutable Atlas ZIP digests, and causal lifecycle Python source fingerprints. Payload chronology validated; mismatch fails closed.
- **Immutable input ZIP cache:** SHA256-check each restored source, historical-source and historical-control ZIP at every replay, never trust existence alone. Warm restores skip all raw Atlas downloads.
- **Exact-result memoization:** optional, per case. Hash full CLI flags, output name, manifest bytes, full source Python tree digest, all nine input artifact SHA256 digests. Only exact repeats may be reused; stored replay JSON carries independent SHA256 seal and core result schema check. Cache-hit and cache-built messages are explicit in logs. A repeat is **not new scientific evidence**. Changed configuration recomputes.
- GitHub Actions cache is a speed optimization only, never a new source of truth for data, logic, or certification.

## Proven cold/warm performance before exact-case memoization

| Benchmark | Original | Shared-fork | Prepared M5 cold | Prepared M5 warm |
| --- | ---: | ---: | ---: | ---: |
| H4M5, 8 cases | 298 s | 86 s | ~73 s | **40 s** (run 37757768601) |
| Floor, 11 cases | 394 s | 109 s | **66 s** (run 37757374482) | **51 s** (run 37757836252) |

Exact original-vs-prepared warm comparison: 8/8 and 11/11 case metric rows identical for all recorded comparison keys (0 differences). This checks capital, DD, gross losses, PF, and strict Pareto per case.

## Exact-case memoization acceptance results — PASSED

- Cold case-result cache creation: H4M5 run 37758132492 and Floor run 37758137909, each SUCCESS; all 19 original metrics rows match exactly (25 fields per row).
- True warm verification, changed YAML comment only: H4M5 run 37758353826, **15 s end-to-end**, 8/8 sealed exact-result cache hits, no result recomputes; Floor run 37758361576, **19 s end-to-end**, 11/11 exact-result cache hits, no result recomputes.
- Warm reports **19/19 cases, 25 comparison fields each, zero differences** versus the original unspecialized full-M5 research runs; 3,368 expected decisions and no sovereign breach inherited from bytewise output parity.
- Memoized replay case batch time: H4M5 0.811 s, Floor 0.712 s; end-to-end GitHub Actions remains 15–19 s due to Actions startup/cache/ZIP verification/artifact upload.
- Changed flags produce different case SHA256 identities and cannot reuse existing result. New cases still run the engine; the exact memoized result is not independent scientific evidence.
- Independent warm preparation cache (without exact result memoization) ran H4M5 37757768601 in 40 s and Floor 37757836252 in 51 s; exact row parity also confirmed.

## Critical limitations

New exploratory case configurations still need an actual replay; a cache cannot make novel research computationally free. Cold cache builds still require validating full source custody. End-to-end GitHub Actions includes host provisioning/checkout/artifact handling and therefore is not equivalent to the standalone ~3-second microbenchmark previously cited. A cache hit must not be counted as a new backtest or OOS.

## Implementation provenance

- Working branch: `agent/cibo-trader-lab-ultrafast-20261008-001`
- Main CIBO research branch remains `agent/cibo-causal-expectation-leakage-fix-001` pending verified merge.
- Only the two named current suites migrated in this unit. Migrate other active legacy suites with exact baseline parity checks, not global find/replace.
