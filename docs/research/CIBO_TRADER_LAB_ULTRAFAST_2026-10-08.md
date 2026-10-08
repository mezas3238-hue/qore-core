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

## Exact-case memoization acceptance gates

1. First cold run computes all cases and writes digest-sealed result cache.
2. Second run changes a workflow comment without touching source data or CLI flags. Runner must report a cache hit for **every** identical case.
3. Compare all strict Pareto output row fields exactly to baseline, and verify same 3,368 decisions, no sovereign breach.
4. New case flags must produce a different digest and fresh calculation.
5. Do not merge staging branch until these checks pass.

## Critical limitations

New exploratory case configurations still need an actual replay; a cache cannot make novel research computationally free. Cold cache builds still require validating full source custody. End-to-end GitHub Actions includes host provisioning/checkout/artifact handling and therefore is not equivalent to the standalone ~3-second microbenchmark previously cited. A cache hit must not be counted as a new backtest or OOS.

## Implementation provenance

- Working branch: `agent/cibo-trader-lab-ultrafast-20261008-001`
- Main CIBO research branch remains `agent/cibo-causal-expectation-leakage-fix-001` pending verified merge.
- Only the two named current suites migrated in this unit. Migrate other active legacy suites with exact baseline parity checks, not global find/replace.
