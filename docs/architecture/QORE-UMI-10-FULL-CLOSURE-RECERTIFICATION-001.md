# QORE-UMI-10 — Full Closure Recertification Ledger

Status: GATE B OWNER-LOCAL CORRECTION CANDIDATE — NOT FULL-CLOSURE SEALED  
Program: #301 — Full Closure serial por UMI  
Historical tracker: #355  
Historical implementation PR: #356  
Retrospective oracle audit: #405  
Predecessor: UMI-09 FULL CLOSURE — SEALED/CLOSED  
Gate B base: `5ca117970091528cbef4202d0d87bf7f1bce52d0`  
Gate B branch: `agent/qore-umi10-full-closure-001`

## 1. Purpose

This ledger records the owner-local UMI-10 correction prepared under explicit Full Closure
Gate B authorization. It is not a seal, merge authorization, Ready authorization, or
production authorization.

The current owner production contract remains:

`src/qore/infrastructure/universal_valuation_observation.py`

with blob:

`daa67c2903e9a5c95b55313b5d3c2667a4c180ae`

Gate B does not modify that production owner. The correction is test/documentation only
unless an independent oracle first falsifies current production semantics.

Canonical lifecycle law remains:

```text
HISTORICAL CERTIFIED != CURRENT FULL-CLOSURE SEALED
CI GREEN != FULL-CLOSURE PASS
MERGED != SEALED
NO FINAL #301 EVIDENCE -> NO FULL-CLOSURE SEAL
```

## 2. Gate A reconstruction carried into Gate B

Historical UMI-10 implementation was integrated through #355 / PR #356. The historical
owner set was six paths:

1. `src/qore/infrastructure/universal_valuation_observation.py`
2. `tests/infrastructure/test_universal_valuation_observation.py`
3. `tests/infrastructure/test_universal_valuation_observation_critical_paths.py`
4. `tests/infrastructure/test_universal_valuation_observation_guards.py`
5. `tests/infrastructure/test_universal_valuation_observation_ohlc_identity.py`
6. `docs/architecture/QORE-UMI-10-UNIVERSAL-VALUATION-OBSERVATION-001.md`

The production blob remained unchanged at the Gate B base. No current production
semantic/projection defect was established by Gate A.

The retrospective #405 classification is authoritative for this correction:

```text
UMI10-LI-01 = CONFIRMED ORACLE GAP / MEDIUM
NO CURRENT PRODUCTION SEMANTIC/PROJECTION DEFECT ESTABLISHED
SOURCE NOT REOPENED
```

## 3. Gate A finding ledger

```text
FC10-01 HISTORICAL_STALE / NONCODE                    LOW     NON-BLOCKING
FC10-02 TEST_ORACLE — UMI10-LI-01                    MEDIUM  BLOCKING
FC10-03 TEST_COVERAGE / FAIL-CLOSED ORACLE           MEDIUM  BLOCKING
FC10-04 FULL-CLOSURE RECERTIFICATION LEDGER           MEDIUM  BLOCKING
FC10-05 LIFECYCLE INCOMPLETE BY DESIGN               INFO    EXPECTED
FC10-06 HISTORICAL OWNER RECONCILIATION              LOW     CLOSED
FC10-07 OPEN-PR OWNER OVERLAP                        MEDIUM  CLOSED / ZERO
FC10-08 CROSS-OWNER RECONCILIATION                   LOW     CLOSED
```

Gate B is permitted to correct FC10-02, FC10-03, and FC10-04 only within the verified
UMI-10 owner boundary. It does not authorize Gate C, D, E, or F.

## 4. FC10-02 — independent logical-materiality oracle correction

Gate B adds:

`tests/infrastructure/test_universal_valuation_observation_full_closure.py`

The correction does not use a parent object's current `logical_values()` as the expected
oracle for that same parent. Expected material is manually reconstructed from literals,
explicit UUID seeds, canonical timestamp strings, canonical decimal strings, and typed
contract facts.

For computed-input fingerprints, the expected SHA-256 is derived only from independently
reconstructed expected input tuples using standard-library JSON/SHA-256. The production
fingerprint helper and current SUT `logical_values()` are not used to build the expected
fingerprint.

### 4.1 Local identity and temporal material

The new suite directly protects:

- all four local UUID wrappers with exact literal material;
- rejection of a malicious `UUID` subclass carrying forged string material;
- `ValuationAsOfInstant` UTC/microsecond canonicalization;
- `ValuationAsOfInterval` UTC/microsecond canonicalization;
- strict date-only `ValuationAsOfDate` material;
- same-instant/different-offset equivalence without converting date-only facts to midnight.

### 4.2 Complete measure-family projections

The suite reconstructs independent expected projections for all UMI-10 measure families:

- exact D05 market price;
- fixed-income price;
- fixed-income yield + convention;
- fixed-income spread + reference identity;
- standalone zero rate;
- standalone par rate;
- standalone forward rate + structural forward period;
- discount factor + structural coordinate;
- fund NAV + exact UMI-06 NAV basis;
- implied volatility + reference identity;
- model/theoretical value;
- crypto-perpetual quoted value + exact UMI-08 MARK/INDEX/LAST pricing terms;
- contractual fixed-income cash-flow value.

The standalone-rate variants are each independently asserted so deletion or substitution
of the rate kind, convention, coordinate kind, or coordinate material cannot hide behind
a current-vs-current comparison.

### 4.3 Identity bridge and source projections

The suite independently reconstructs:

- a populated listing-target `ValuationIdentityBinding`, including mapping revision,
  listing identity, final economic identity, effective window, and evidence;
- a provider-native binding carrying exact external source identity;
- D05 quote source material with exact retained quote, BID selector, legacy mapping, and
  selected measure;
- D05 OHLC source material with exact retained bar, field selector, legacy mapping, and
  selected measure.

This preserves:

```text
Instrument.symbol != EconomicIdentityId
D05 MARKET OBSERVATION != D07 VALUATION OBSERVATION
EVIDENCE REF != EVIDENCE CONTENT/TRUTH
```

### 4.4 Published / observed / computed lineage

The suite independently reconstructs:

- `PublishedValuationSource` with provider-native source binding;
- `ObservedValuationObservation` including UTC-canonical `recorded_at`;
- `ValuationMethodologyIdentity`;
- two `ValuationComputedInput` values supplied in reverse caller order;
- deterministic role-based canonical ordering;
- explicit independent SHA-256 fingerprint material;
- `ComputedValuationProvenance`;
- `ComputedValuationObservation` including independent identity/as-of/measure/provenance/
  recorded-at/evidence material.

Deletion, substitution, and caller-order permutations therefore have direct discriminating
oracles rather than only semantic pairwise comparisons.

## 5. FC10-03 — residual coverage / fail-closed adjudication

Historical and current production owner coverage before this correction was:

```text
621 statements
23 missed
96%
```

Historical residual statement lines:

```text
88, 114,
315, 330, 334,
353, 357,
381, 385, 389,
430, 434,
611, 615,
635, 639, 643, 647,
669, 673,
907, 911, 915
```

Gate A conservatively described the set as two structural misses plus 21 rejection-only
misses. Gate B exact source reconstruction refines that classification without changing
production.

### 5.1 Twenty reachable fail-closed statements

The following 20 statements are reachable through ordinary invalid caller input and now
receive direct tests:

```text
315,
330, 334,
353, 357,
381, 385, 389,
430, 434,
611, 615,
635, 639, 643,
669, 673,
907, 911, 915
```

They cover wrong value/convention/reference/coordinate types across fixed-income,
standalone-rate, discount-factor, crypto value/measure, cash-flow-value, and D05 OHLC
source boundaries.

### 5.2 Three structural statements — no coverage gaming

The following are not valid-state coverage targets:

```text
88   _validate_code secret-marker raise
114  _validate_revision secret-marker raise
647  CryptoPerpetualPriceMeasure role-not-certified raise
```

**88 / 114** — the secret-marker checks occur after canonical regex validation. Every
configured secret marker requires either `=` or a space, while the accepted code/revision
alphabets contain neither. Inputs containing those markers fail earlier at canonical syntax.
The later marker-specific raises are therefore structurally unreachable under the current
validated alphabet.

**647** — a valid `CryptoPerpetualPricingTerms` is owned by UMI-08 and requires exactly all
three roles:

```text
MARK_PRICE
INDEX_PRICE
LAST_PRICE
```

`CryptoPerpetualPriceMeasure.role` must itself be one of that same closed enum. Therefore,
for a valid exact UMI-08 pricing-terms object, a valid UMI-10 role cannot be absent from
`pricing_terms.roles`. The branch is defensive against an upstream invariant breach, not a
valid caller state.

The Gate B suite explicitly proves the upstream three-role constructor invariant and does
not use `object.__setattr__`, monkeypatching, invalid-state mutation, coverage pragmas,
skips, xfails, or a production edit to force these statements green.

Canonical rule:

```text
100% STATEMENT COVERAGE != ORACLE COMPLETENESS
STRUCTURALLY UNREACHABLE != UNTESTED REACHABLE FAIL-CLOSED PATH
NO COVERAGE GAMING
```

## 6. Production non-mutation

Gate B makes no change to:

`src/qore/infrastructure/universal_valuation_observation.py`

No pricing engine, provider adapter, currentness resolver, valuation producer, network
boundary, execution authority, settlement mutation, account/risk authority, production
credential, or real-capital capability is added.

The #350 methodology/producer boundary remains separate. #332/#333 remain cross-owner and
are not converted into UMI-10 debt by this correction.

## 7. Determinism and security review of the correction

The new test material uses:

- explicit deterministic UUIDs;
- explicit timezone-aware datetimes;
- literal canonical UTC expectations;
- finite explicit Decimals;
- immutable tuples;
- deterministic independent JSON/SHA-256 fingerprint reconstruction;
- no implicit `now`, `today`, `uuid4`, random, global mutable state, network, retry, sleep,
  thread, scheduler, or hidden I/O;
- no credentials, secrets, tokens, account identifiers, or production material.

The correction introduces no suppression, strictness downgrade, skip, xfail, pragma,
coverage exclusion, or test deletion.

## 8. Quality-gate state at Gate B

The repository workflow runs QORE CI for pull requests targeting `main` and pushes to
`main`. Gate B does not authorize opening a pull request, and therefore does not fabricate
an exact-candidate CI result.

The new test source was syntax-compiled before publication to the branch. This is not a
substitute for the canonical Quality Gate:

```text
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

The exact candidate Quality Gate must run under Gate C after explicit Gate C authorization
creates the Draft PR. No PASS is claimed here for Ruff, Mypy, Pytest, or coverage.

## 9. Candidate-level finding disposition

```text
FC10-02 TEST_ORACLE
  -> CORRECTION PRESENT IN GATE B CANDIDATE
  -> NOT YET FULL-CLOSURE VERIFIED

FC10-03 FAIL-CLOSED ORACLE
  -> 20 REACHABLE DIRECT TESTS PRESENT
  -> 3 STRUCTURAL MISSES EXPLICITLY ADJUDICATED
  -> NOT YET FULL-CLOSURE VERIFIED

FC10-04 RECERTIFICATION LEDGER
  -> CORRECTION PRESENT IN GATE B CANDIDATE
  -> NOT YET FULL-CLOSURE VERIFIED
```

No Gate B evidence may be promoted to sealed truth until the exact-candidate CI, mandatory
independent Claude audit, IA exact-candidate final falsification, Ready gate, protected
merge gate, post-merge validation, final whole-UMI audit/falsification, and #301 evidence
are completed under their own authorizations.

## 10. Gate boundary after this ledger

Upon a coherent branch diff and exact candidate freeze, the intended state is:

```text
GATE A = COMPLETE / CONSUMED
GATE B = COMPLETE / CONSUMED
GATE C = AVAILABLE / NOT AUTHORIZED
GATE D = NOT AVAILABLE / NOT AUTHORIZED
GATE E = NOT AVAILABLE / NOT AUTHORIZED
GATE F = NOT AVAILABLE / NOT AUTHORIZED

PR = NOT CREATED
READY = NOT AUTHORIZED
MERGE = NOT AUTHORIZED
UMI10 = NOT SEALED / NOT CLOSED
UMI11 = NOT STARTED / NOT AUTHORIZED
```

Gate C must revalidate live `main`, exact branch head/tree/parent, exact diff, production
blob identity, open-PR overlap, and owner discovery before creating a Draft PR. Any drift
must be reconciled before CI evidence is accepted.
