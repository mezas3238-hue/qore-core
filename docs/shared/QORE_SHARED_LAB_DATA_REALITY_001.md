# QORE SHARED LAB — Data Reality & Sensor Laboratory 001

Status: **ARQUITECTO 2 LANE FUNCTIONALLY COMPLETE / READY FOR CROSS-INTEGRATION REVIEW**

No trading, sizing, risk, production, certification or protected-holdout authority is granted by this lane.

## Boundary

`PROVIDER -> RAW RECEIVED EVIDENCE -> PROVENANCE -> CANONICAL IDENTITY -> MARKET HOURS ->
TIMESTAMP/CHRONOLOGY -> FRESHNESS -> QUALITY -> COMPLETENESS -> SENSOR OUTPUT -> LAB RECEIPT ->
EXACT NEXT-CONSUMER FINGERPRINT`

This lane consumes, but does not rewrite, the Shared Lab core/tool contracts owned by Arquitecto 1.

## Evidence laws

- A valid timestamp alone never proves market reality.
- Provider lineage identifies the exact source, raw SHA-256, decoder and mapping revision.
- Canonical identity is economic identity; provider symbol spelling is not.
- Predecision evidence must satisfy `observed_at <= available_at <= decision_at <= consumed_at`.
- Any future evidence before decision is an automatic laboratory failure.
- Quality is per required capability; pooled rescue is forbidden.
- Critical sensor loss requires block/abstention; unrelated healthy sensors cannot rescue it.
- Noncritical degradation must raise uncertainty and report affected dependencies.
- Golden traces are engineering fixtures only and never the final fresh 7-trader x 2-year holdout.
- Fault families are parameterized through Arquitecto 1's `SharedLabToolRegistry`.
- The data lane has no imports/calls that grant productive authority or consume future P/L outcomes.

## Functional surface

Implemented and tested:

1. deterministic Golden Trace Library;
2. raw provider evidence and exact decode lineage;
3. provider degradation and reconnect receipts;
4. canonical identity and explicit provider alias mappings;
5. futures maturity/contract-month/venue/multiplier identity;
6. instrument-aware market calendar;
7. timezone/provider-local -> UTC normalization;
8. DST, epoch and session-rollover reality;
9. chronology/leakage firewall;
10. freshness, continuity, quality and completeness metrics;
11. cross-provider disagreement;
12. partial-universe detection;
13. structured sensor fault receipts;
14. redundancy/resilience dependency receipts;
15. fail-degraded and abstention behavior;
16. deterministic sensor replay;
17. exact validated-output -> next-consumer lineage;
18. L10 Lab-of-the-Lab known-failure detection;
19. authority/outcome-aware static firewall;
20. executable 14-gate end-of-lane engineering exam.

## Parameterized failure matrix

The lane consumes these official registry families without modifying the registry:

- `TIMESTAMP_PERTURBATION`
- `SENSOR_FAILURE_INJECTOR`
- `PROVIDER_DEGRADATION`
- `IDENTITY_MUTATION`

The matrix covers multiple sensors, assets, regimes, offsets, durations, missing fractions,
provider modes and identity mutations rather than generating one-off scripts.

## Sensor/provider adversarial coverage

Covered families include missing/duplicated/out-of-order/stale/future evidence, timestamp drift,
partial history, provider disconnect/reconnect gaps, spread anomaly, malformed/zero-negative values,
wrong asset class, alias collision, starvation, delay, intermittency, partial provider, conflicting
provider, changed symbol/mapping, different decimals, corrupted payload, duplicate/drop and sequence gap.

## Temporal coverage

Explicit cases include:

- +1 ms
- +10 ms
- +1 s
- +30 s
- +5 min
- negative offset
- duplicate timestamp
- missing timestamp
- future timestamp
- out-of-order sequence
- DST transition/fold
- timezone mismatch
- clock drift
- epoch conversion
- provider-local vs UTC mismatch
- session-boundary rollover

## Market-hours coverage

Instrument-aware calendar tests include:

- open
- closed
- holiday
- partial/open-compatible state
- early close
- weekend
- DST
- futures session break
- overnight session
- rollover contract
- provider reporting during closure

## Strict 14-gate exam

The executable exam requires independent evidence for every gate:

1. GOLDEN_TRACE
2. SENSOR_FAILURE_INJECTION
3. TIMESTAMP_CHRONOLOGY
4. PROVIDER_INTEGRITY
5. CANONICAL_IDENTITY
6. MARKET_HOURS
7. DATA_COMPLETENESS
8. DATA_QUALITY
9. PROVENANCE
10. REDUNDANCY_RESILIENCE
11. FAIL_DEGRADED
12. LEAKAGE_FIREWALL
13. DETERMINISTIC_REPLAY
14. L10_KNOWN_FAILURE_DETECTION

One failed or missing gate makes `functional_complete=false`. No pooled rescue exists.

## Latest reproducible evidence

Validated head before this documentation-only update:

`9b2e3fd853e0f106ee697b8fa66026a26d768613`

Dedicated workflow:

`QORE Shared Lab Data Reality`

Run:

`37217372572`

Result:

`SUCCESS`

Test result:

`137 passed`

Exam fingerprint:

`d18ed2245e0990126a85fab7e1e795b945c9fb6c6f027dcf91dc0c36551eb1b6`

Artifact:

`qore-shared-lab-data-reality-exam`

Artifact ID:

`11308908053`

Artifact archive digest:

`sha256:b2d08edf238848ae650470dc5f798b353b013ca3276e798126b92acd9ee9f987`

## Cross-architect status

At final lane revalidation:

- Arquitecto 1 / #716 HEAD: `f58549f505109c0f24ed631add3f6597cca48796`
- Arquitecto 2 / #717 tested HEAD: `9b2e3fd853e0f106ee697b8fa66026a26d768613`
- overlapping changed files: **0**
- #717 state: **DRAFT / MERGEABLE**
- merge performed: **NO**

Arquitecto 1 remains responsible for cross-integration into #716.

## Authority

This lane cannot open/close/modify orders or positions, change sizing, grant risk, operate an account,
open the protected final holdout, certify Shared, or promote production.

Its receipts are scientific/functional evidence only.
