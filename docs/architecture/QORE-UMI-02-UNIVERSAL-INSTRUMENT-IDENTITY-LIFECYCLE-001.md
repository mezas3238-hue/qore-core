# QORE-UMI-02-UNIVERSAL-INSTRUMENT-IDENTITY-LIFECYCLE-001

## Status

**STAGE-03 / UMI-02 — FULL CLOSURE RECERTIFICATION RECORD; FINAL CLOSURE STATUS GOVERNED BY #301**

Tracking: #301  
Master roadmap: #303  
Preceding stage: STAGE-02 / UMI-01 — Full Closure baseline established before this correction  
Historical certified starting baseline: `ab69f0f2f43c73e2b0d2c4c4c4ca480b1b8f68f7`  
Historical certification PR: #309  
Historical final reviewed head: `0314e3aeb0997ff4a1e90b3e1a5c4945290d5af8`  
Historical merge commit: `89705ed8c5cc3e4bf39a74ec2c37111a52285f8f`  
Full Closure correction starting main: `9bb96525caaa6b8aaf20e0ff0dc27ae36eca721d`  
Full Closure correction starting tree: `d168c6b087112f084a98ebf068a578b872cca7d0`

This artifact is the durable UMI-02 architecture and Full Closure record. It preserves the historical identity/lifecycle certification while reconciling the current integrated repository and the later-discovered mapping-revision currentness obligation. The document does not self-certify closure. Final UMI-02 closure is governed by integrated evidence, the mandatory final whole-UMI Claude audit, independent IA falsification, #301 evidence and final baseline freeze.

## Governing invariants

```text
QORE CORE IS UNIVERSAL AND NON-SELECTIVE
SYMBOL TEXT != UNIVERSAL INSTRUMENT IDENTITY
ECONOMIC IDENTITY != LISTING / VENUE IDENTITY
TRADABLE INSTRUMENT IDENTITY != REFERENCE-OBJECT IDENTITY
PROVIDER-NATIVE ID != ECONOMIC INSTRUMENT IDENTITY
STANDARD IDENTIFIER != PROVIDER-NATIVE RUNTIME IDENTIFIER
EXTERNAL IDENTIFIER != QORE CANONICAL IDENTITY
ASSET FAMILY != INSTRUMENT IDENTITY
DISPLAY SYMBOL != CANONICAL IDENTITY
CONTINUOUS REFERENCE != NATIVE CONTRACT
COMPOSITE / SYNTHETIC != PRIMITIVE INSTRUMENT
LIFECYCLE != UNIVERSAL EXPIRY FIELD
LATEST REVISION != CURRENT MAPPING
CURRENT MAPPING != HISTORICAL IDENTITY INTERPRETATION
EFFECTIVE TIME != KNOWLEDGE CUTOFF
MAPPING DIGEST != RETAINED VERSIONED MAPPING EVIDENCE
IDENTITY FOUNDATION != FAMILY-SPECIFIC ECONOMIC TERMS
NO DATA PROVENANCE -> NO QUANTITATIVE CLAIM
NO REPRODUCIBILITY -> NO PROMOTION
NO VERIFIED SEMANTICS -> NO SUPPORT CLAIM
NO PARTIAL UMI WORK
NO ISOLATED FIX AS UMI CLOSURE
NO FRAGMENTED DELIVERY
CROSS-OWNER LABEL != PERMISSION TO EXPORT UMI-02 INTERNAL DEBT
```

## Scope and authority

Markets / Instruments owns canonical economic identity/reference facts and the interpretation policy for retained external-identity mapping revisions. Provider/platform adapters retain provider-native identifiers and map them through governed boundaries. Market Data, Execution, Position, Risk, Research, Valuation, Client EA and presentation surfaces consume identity; none becomes a parallel identity authority.

UMI-02 owns:

- stable economic/reference identity;
- independent listing/venue identity;
- external identifier classification and mapping lineage;
- typed effective-dated identity relationships;
- heterogeneous lifecycle facts;
- canonical graph integrity;
- deterministic mapping-revision resolution over retained UMI-02 history.

UMI-02 does not own provider discovery, market sessions/calendars, family valuation, risk models, execution economics, provider runtime capability, production support or productive authorization.

---

# 1. Canonical identity graph

`EconomicIdentityId` is the stable QORE identity for one economic instrument or reference object. It is independent of display symbol, provider identifier and listing.

`EconomicIdentityKind` distinguishes tradable instruments from reference objects. `IdentityConstructionKind` distinguishes native, synthetic, composite and continuous-reference construction; a continuous reference must remain a reference object rather than masquerade as a native dated contract.

`ListingIdentity` is a separately governed listing representation with its own ID, parent economic identity, venue, display symbol, effective interval and evidence reference.

```text
SAME SYMBOL != SAME LISTING
SAME ECONOMIC IDENTITY MAY HAVE MULTIPLE LISTINGS
```

Legacy `market_data.Instrument`, `ExecutionInstrument`, executive/presentation symbols and provider-native symbol material retain their bounded meanings. UMI-02 is additive; it does not silently reinterpret them as sovereign economic identity.

---

# 2. External identifier model

`ExternalIdentifier` retains external identity material explicitly and non-sovereignly. Its semantic classes remain:

- `LEGACY_QORE`;
- `PROVIDER_NATIVE`;
- `VENUE_NATIVE`;
- `STANDARD`;
- `NETWORK_NATIVE`.

Provider-native identifiers require explicit source provenance. Venue-native identifiers require explicit venue scope. Legacy QORE identifiers cannot masquerade as provider/venue facts. Public identifier material must remain secret-free.

```text
STANDARD IDENTIFIER MAY AID CROSS-PROVIDER RECONCILIATION
!=
STANDARD IDENTIFIER BECOMES QORE SOVEREIGN IDENTITY
```

---

# 3. Typed identity relationships

`IdentityRelationship` is an immutable effective-dated directed edge between economic identities. Relationship roles are extensible validated codes rather than one universal family enum.

The graph can represent underlying/reference, series membership, benchmark, denomination/trading/settlement currency and ordered component relationships without absorbing family-specific economics. Optional positive `ordinal` preserves material component order. Self-relations, dangling endpoints and duplicate ordered ordinals in the same scope fail closed.

Currency may be represented as a canonical reference-object identity for relationship topology, but UMI-02 does not create a universal money amount/value primitive.

---

# 4. Contract / series / derivative boundary

A dated contract may have its own `EconomicIdentityId`; a continuous series or benchmark may have a distinct reference-object identity; `IdentityRelationship` links them.

```text
UMI-02 MUST MAKE FAMILY TERMS ATTACHABLE WITHOUT IDENTITY REDESIGN
!=
UMI-02 IMPLEMENTS EVERY FAMILY ECONOMIC TERM
```

Strike/right/exercise, coupon/yield, multiplier, payoff, settlement, corporate-action and other family economics remain with their certified downstream owners.

---

# 5. Lifecycle model

`IdentityLifecycleEvent` remains an immutable evidence-bearing lifecycle fact with explicit event ID, economic-or-listing subject, extensible event code, `effective_at`, `recorded_at` and evidence reference.

There is intentionally no universal expiry field and no global lifecycle-state enum. `recorded_at` is distinct from `effective_at`, permitting future-dated announcements and later-discovered evidence without rewriting historical time.

---

# 6. Versioned mapping lineage

`ExternalIdentityMappingRevision` retains:

- stable mapping ID;
- positive revision;
- exact parent revision;
- exact external identifier;
- canonical economic or listing target;
- half-open effective interval `[effective_from, effective_until)` where bounded;
- explicit `recorded_at`;
- retained evidence reference.

`IdentityMappingHistory` remains one immutable linear history for one mapping ID and exact external identity. Revisions are contiguous from 1, parent-linked and strictly increasing by `recorded_at`. The canonical graph forbids multiple retained histories for the same exact external identity and rejects dangling mapping targets.

Historical certification established retained mapping lineage but did not define the cross-revision currentness/precedence resolver later required by UMI09/10/11/13. Full Closure therefore adds a pure resolver over the existing history rather than a second identity system.

---

# 7. Mapping currentness / precedence policy

Canonical resolver:

`resolve_identity_mapping_revision(history, *, effective_at, known_at)`

The resolver is deterministic and has no implicit wall clock.

For a requested interpretation:

1. `effective_at` is the economic instant being interpreted.
2. `known_at` is the explicit information cutoff for replay/currentness evaluation.
3. A revision is eligible only if `revision.recorded_at <= known_at`.
4. It must also satisfy `effective_from <= effective_at` and `effective_at < effective_until` when `effective_until` is present.
5. If multiple retained linear-history revisions are eligible because effective intervals overlap, the highest already-known revision has precedence.
6. If no revision is eligible, resolution fails closed with a typed UMI-02 resolution error.

```text
LATEST REVISION PROPERTY != CURRENTNESS RESOLUTION
EFFECTIVE AT T + KNOWN AT K -> REPRODUCIBLE HISTORICAL INTERPRETATION
LATER BACKFILL != SILENT REWRITE OF AN EARLIER KNOWLEDGE CUTOFF
OVERLAPPING EFFECTIVE WINDOWS + LINEAR REVISION CHAIN -> HIGHEST KNOWN ELIGIBLE REVISION
NO ELIGIBLE REVISION -> FAIL CLOSED
```

This policy intentionally separates economic applicability from knowledge chronology. It does not require `known_at >= effective_at`; future-effective mappings may be known before activation, and backfilled revisions may be recorded after the period they reinterpret.

The resolver does not choose provider capability, market session state, topology, valuation currentness, execution route or any other downstream policy.

---

# 8. Canonical graph integrity

`UniversalInstrumentIdentityGraph` remains an immutable composition boundary, not a database or registry implementation. It requires:

- at least one economic identity;
- unique economic IDs;
- unique listing IDs and retained listing parents;
- unique relationship IDs and retained endpoints;
- unique lifecycle event IDs and retained subjects;
- unique mapping IDs;
- one retained mapping history per exact external identity;
- retained mapping targets;
- deterministic canonical ordering.

```text
TYPES EXIST != GRAPH IS CONSISTENT
LOCAL INPUT ORDER != CANONICAL LOGICAL ORDER
```

No SQL/event-log/consensus/distributed-registry technology is selected here.

---

# 9. Historical UMI-02 certification record

Historical UMI-02 was implemented and integrated through PR #309 from certified base `ab69f0f2f43c73e2b0d2c4c4c4ca480b1b8f68f7`.

Permanent historical ledger:

- PR: `#309`;
- final reviewed head: `0314e3aeb0997ff4a1e90b3e1a5c4945290d5af8`;
- merge commit: `89705ed8c5cc3e4bf39a74ec2c37111a52285f8f`;
- historical scope: economic/reference identity, independent listing identity, external identifier classification, relationships, lifecycle, versioned mapping lineage, canonical graph integrity and adversarial conformance;
- legacy symbol contracts were retained rather than redefined;
- PR #298 remained HOLD and was not promoted by UMI-02.

The historical certification is preserved. Full Closure does not retroactively invalidate those results; it closes a later-discovered internal obligation that subsequent UMI work explicitly left with D04/UMI-02.

---

# 10. Current-main reconstruction and no-regression result

Full Closure reconstruction began from integrated main:

- main: `9bb96525caaa6b8aaf20e0ff0dc27ae36eca721d`;
- tree: `d168c6b087112f084a98ebf068a578b872cca7d0`.

Current source still preserves the certified UMI-02 identity split:

- `EconomicIdentityId` remains distinct from `ListingIdentityId`;
- `IdentityFamilyCode` remains classification, not identity;
- `EconomicIdentity` remains independent of provider/listing symbol text;
- `CONTINUOUS_REFERENCE` remains constrained to reference-object identity;
- mapping history remains retained, immutable and evidence-bearing;
- the canonical graph still forbids parallel mapping histories for one exact external identity.

Later Program-D stages preserve UMI-02 ownership instead of replacing it:

- UMI09 explicitly retained the inherited UMI-02 current/as-of resolver obligation;
- UMI10 assigns mapping revisions/currentness policy and reference meaning to D04/UMI-02 and refuses to choose current mapping itself;
- UMI11 consumes UMI-02 identity/listing/venue material and refuses to select a current mapping/listing revision;
- UMI13 preserves UMI-02 cross-revision overlap/precedence/currentness as a carry-forward rather than absorbing it.

Result before this correction:

`VERIFIED UMI-02 INTERNAL GAP — CROSS-REVISION MAPPING CURRENTNESS/PRECEDENCE`

No evidence was found that a downstream UMI had become a second sovereign economic/listing identity owner.

---

# 11. Full Closure findings and correction ledger

The complete UMI-02 Full Closure reconstruction identified four UMI-02-owned findings:

### FC02-01 — historical/candidate document state stale

The architecture artifact still described itself as an implementation candidate after PR #309 had already been integrated. Full Closure replaces that stale state with this durable certification/recertification record.

### FC02-02 — current-main authority/no-regression reconciliation absent

The historical document predated UMI03..13 and therefore did not permanently record their identity-authority relationship to UMI-02. Section 10 records the current integrated authority result and confirms that later stages consume rather than replace UMI-02 identity.

### FC02-03 — cross-revision mapping currentness/precedence missing

Later certified stages repeatedly preserved this obligation with D04/UMI-02. Full Closure adds the pure deterministic resolver and adversarial tests in:

- `src/qore/infrastructure/universal_instrument_identity_resolution.py`;
- `tests/infrastructure/test_universal_instrument_identity_resolution.py`.

The correction reuses `IdentityMappingHistory`; it does not create a second graph, database, provider resolver, wall clock or mutable registry.

### FC02-04 — Full Closure protocol stale

The historical closure gate did not contain the definitive integrated-state sequence requiring zero internal pending work, mandatory final whole-UMI Claude audit, complete correction/re-audit of any surviving findings, final IA falsification, #301 evidence and baseline freeze. Section 15 now governs.

These findings are one complete UMI-02 correction contract, not four independent deliveries.

---

# 12. Adversarial resolution requirements

The Full Closure resolver must prove at minimum:

```text
FC02-RES-01  Explicit timezone-aware effective_at required
FC02-RES-02  Explicit timezone-aware known_at required
FC02-RES-03  Invalid/non-history input fails closed
FC02-RES-04  Effective interval is half-open [from, until)
FC02-RES-05  Revision recorded after known_at cannot affect replay
FC02-RES-06  Latest-revision property is not historical currentness
FC02-RES-07  Highest known eligible revision wins an effective overlap
FC02-RES-08  Backfilled revision cannot rewrite an earlier knowledge cutoff
FC02-RES-09  Older revision may remain applicable outside a bounded later override
FC02-RES-10  No known/effective revision fails closed
FC02-RES-11  Timezone-equivalent instants resolve identically
FC02-RES-12  Returned revision preserves exact target/evidence lineage
```

No test may replace the repository-wide quality gate.

---

# 13. Historical certification cases retained

The original UMI02 cases remain part of the closure surface:

```text
UMI02-CASE-01  Stable economic identity independent of symbol/provider
UMI02-CASE-02  Tradable vs reference-object distinction
UMI02-CASE-03  Multiple listings for one economic identity
UMI02-CASE-04  Provider / venue / standard identifier separation
UMI02-CASE-05  Underlying / reference / currency / series relationships
UMI02-CASE-06  Ordered composite / multi-leg relationships
UMI02-CASE-07  Lifecycle without universal expiry
UMI02-CASE-08  Perpetual / non-expiring identity conformance
UMI02-CASE-09  Versioned effective-dated mapping lineage
UMI02-CASE-10  Historical mapping retention / reproducibility
UMI02-CASE-11  Graph referential integrity / no dangling identities
UMI02-CASE-12  No parallel external mapping authority
UMI02-CASE-13  Deterministic canonical graph ordering
UMI02-CASE-14  Strict runtime type/time validation
UMI02-CASE-15  Legacy compatibility / no silent reinterpretation
UMI02-CASE-16  PR #298 remains HOLD pending compatibility certification
```

Historical certification of these cases does not substitute for current Full Closure recertification of the integrated UMI-02 surface.

---

# 14. Downstream boundary and carry-forwards

UMI-02 does not absorb:

- UMI03 fixed-income/bond economics;
- UMI04 rate/curve/term-structure economics;
- UMI05 derivative strike/right/exercise/multiplier/payoff semantics;
- UMI06 equity/fund/corporate-action economics;
- UMI07 commodity/delivery economics;
- UMI08 crypto/perpetual/funding/network economics;
- UMI09 structured/hybrid/payoff semantics;
- UMI10 valuation-observation semantics or valuation methodology/producer work;
- UMI11 market-topology semantics;
- UMI13 date-qualified instrument-universe registry authority;
- UMI14 final Program-D reconstruction/falsification authority;
- D05 raw market evidence;
- D06 calendars/sessions/other temporal policy outside UMI-02 mapping interpretation;
- D08/D09 Portfolio/Risk state;
- D10/D18 execution authority;
- D20 executive/presentation identity projection;
- Program G research execution/analysis-lineage producer gaps;
- provider/platform operational capability;
- productive credentials, Production readiness or real-capital authority.

PR #298 remains outside UMI-02 Full Closure unless independently reactivated and certified under its own gate.

---

# 15. Full Closure Definition of Done

UMI-02 Full Closure requires all of the following on one integrated candidate lineage:

1. Preserve historical PR #309 evidence and original UMI02-CASE-01..16 semantics.
2. Preserve economic/listing/reference identity separation.
3. Preserve legacy symbol meanings; no silent reinterpretation.
4. Preserve external-identifier scope/provenance and secret hygiene.
5. Preserve relationship/lifecycle/graph integrity.
6. Resolve FC02-01 through FC02-04 in one complete correction contract.
7. Implement mapping currentness on retained `IdentityMappingHistory`, not a second identity system.
8. Use explicit `effective_at` and `known_at`; no implicit wall clock.
9. Apply deterministic highest-known-eligible revision precedence over overlap.
10. Fail closed when no revision is known and effective.
11. Demonstrate historical replay is not rewritten by later backfills.
12. Demonstrate half-open interval boundaries and timezone equivalence.
13. Keep downstream owner boundaries intact.
14. Keep UMI13 date-qualified registry authority intact.
15. Keep UMI14 final Program-D audit authority intact.
16. No Production/provider-support/readiness claims.
17. Diff/blast-radius audit shows only UMI-02-owned correction material.
18. `ruff check .` passes on the exact candidate head.
19. `mypy src tests` passes on the exact candidate head.
20. `pytest --cov=src/qore --cov-report=term-missing` passes on the exact candidate head.
21. Exact-head CI is green; CI green alone is not engineering approval.
22. Independent exact-candidate adversarial review is complete.
23. IA candidate falsification passes.
24. Ready is separately authorized.
25. Merge is separately authorized and uses the expected exact head.
26. Actual merge commit/parents/tree and resulting main are verified.
27. Integrated state is reconstructed after merge.
28. Integrated reconstruction provisionally demonstrates ZERO UMI-02-owned pending work.
29. Claude Code performs the mandatory final **whole-UMI02 integrated-state audit**, not merely a PR-diff review.
30. If Claude identifies material UMI-02 work, UMI-02 remains OPEN; every surviving finding is corrected inside the same complete UMI-02 work unit, integrated and re-audited.
31. Final Claude audit reports zero surviving material UMI-02 findings.
32. IA performs final independent falsification against live GitHub after Claude is clean.
33. #301 receives the exact final UMI-02 baseline plus Claude/IA dispositions under separately authorized Gate F.
34. #301 remains governed by broader Program-D criteria and is not closed merely because UMI-02 closes.
35. Final UMI-02 baseline is frozen from live GitHub evidence.
36. Only then may UMI-02 be declared FULL-CLOSURE RECERTIFIED / SEALED / CLOSED.
37. Only then may UMI03 Full Closure begin.

Canonical sequence:

```text
FULL UMI RECONSTRUCTION
-> ALL UMI-OWNED WORK DISCOVERED
-> ONE COMPLETE CORRECTION CONTRACT
-> ALL UMI-OWNED WORK IMPLEMENTED
-> ZERO INTERNAL PENDING WORK
-> FINAL CLAUDE CODE WHOLE-UMI AUDIT
-> COMPLETE CORRECTION + RE-AUDIT IF ANY FINDING SURVIVES
-> IA FINAL VERIFICATION
-> #301 FINAL EVIDENCE
-> BASELINE FREEZE
-> UMI CLOSED
-> NEXT UMI
```

No intermediate PR, merge, CI result, document update or favorable review is equivalent to UMI closure.

---

# 16. Explicit non-claims

This record does **not** claim:

- final Claude approval;
- final IA closure;
- #301 mutation has occurred;
- every asset family is fully modeled;
- family valuation/economic semantics are owned by UMI-02;
- provider catalog/capability support is universally certified;
- PR #298 is ready to merge/promote;
- historical datasets were rewritten;
- a productive instrument registry exists;
- a database/event log/consensus mechanism has been selected;
- operational trading support is enabled;
- research producer/lineage gaps are closed;
- Production is authorized.
