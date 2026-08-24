# QORE-UMI-08-FULL-CLOSURE-RECERTIFICATION-001

## Status

**PROGRAM D / UMI-08 — FULL-CLOSURE RECERTIFICATION CORRECTION CANDIDATE**

This artifact is the current temporal/governance ledger for UMI-08 Full Closure.
It does not rewrite historical evidence and it does not itself certify, merge, seal, or authorize
UMI-08.

```text
HISTORICAL IMPLEMENTATION != CURRENT FULL-CLOSURE SEAL
CI GREEN != ENGINEERING APPROVAL
MERGED != SEALED
AUTHORIZATION NEVER PROPAGATES
NO FINAL #301 EVIDENCE -> NO FULL-CLOSURE SEAL
```

Tracking:
- UMI-08 historical owner: #330;
- historical implementation PR: #331;
- logical-identity retrospective: #405;
- Full Closure parent authority: #301;
- predecessor frozen authority: UMI-07 Full Closure final evidence in #301.

## 1. Frozen starting authority

Gate A reconstructed UMI-08 from the exact sealed UMI-07 baseline:

- `main`: `b48f92fa776059b6c60723f397c8f53f11a95f61`;
- tree: `cdd1ad5760ff7019f43225e30c91e51f0438946f`;
- parent 1: `d36bb93205d3330b0645730c570461fa95090090`;
- parent 2: `59b4fdd02efc4d4b4ab8869986fac7ad0078367d`;
- GitHub merge signature: verified / valid.

This is the only authorized base for the present Gate-B correction branch.
No newer downstream branch, historical UMI-08 merge, draft PR, or preparatory UMI-14 lane is
allowed to replace that authority.

## 2. Historical UMI-08 implementation ledger

UMI-08 was historically implemented and certified through #330 / PR #331.

Historical exact candidate:
- base: `c7173ab0b21969c8d836127999f70c10ad66707c`;
- head: `2b40b1e31c3ac3dc0e5d31d7bf3494126aea666f`;
- candidate tree: `96a82a535710f723a17713cf3dbd2693ad33bc30`;
- synthetic PR merge: `2b03349e6ddee68be996a1cb96c8688216f04039` — CI only;
- actual protected merge: `78142031c1a857d9d5f1c54d5d6b7873d1b0de23`;
- actual merge tree: `96a82a535710f723a17713cf3dbd2693ad33bc30`;
- actual merge parents: historical base + exact candidate head;
- actual merge signature: GitHub verified / valid;
- blast radius: exactly 3 additive files / `+1219/-0`.

Historical exact-head quality evidence:
- QORE CI #1059;
- run `31848616056`;
- job `94919963985`;
- Ruff: PASS;
- Mypy: PASS — 580 source files;
- Pytest: PASS — 2590 passed / 6 inherited warnings;
- global coverage: 84% — 37849 statements / 5890 missed;
- UMI-08 owner coverage: 92% — 172 statements / 14 missed.

Historical owner blobs, still present unchanged at the Gate-A starting main:
- source `src/qore/infrastructure/crypto_perpetual_funding_semantics.py`:
  `f459f73bf5d5eb2556e207b3ebfdf591edde79d8`;
- primary historical tests `tests/infrastructure/test_crypto_perpetual_funding_semantics.py`:
  `ef64ef5ccf0c5e8c0a758c9d470813f8445f2c89`;
- historical architecture
  `docs/architecture/QORE-UMI-08-CRYPTO-PERPETUAL-FUNDING-NETWORK-SEMANTICS-001.md`:
  `bba67cc77d9332ef45cfa231856d04508c11e02d`.

The historical primary test and architecture files remain deliberately byte-identical in this
Full Closure candidate. Historical wording is evidence of its time and is not silently rewritten.
This recertification artifact is the temporally current authority for Full Closure status.

## 3. Historical independent review disposition

The historical #331 independent review returned `READY FOR INTEGRATION GATE`.
Integration Gate historically recorded:

- `FINDING-UMI08-01` — UUID `isinstance` vs exact type:
  historical disposition `NON-BLOCKING HARDENING / LOW`;
- `FINDING-UMI08-02` — 14 wrong-type rejection branches uncovered:
  historical disposition `NON-BLOCKING TEST HARDENING / LOW`;
- `FINDING-UMI08-03` — independent architecture fetch limit:
  historical disposition `INFORMATIONAL`, resolved by Integration Gate inspection.

Those dispositions are preserved as historical facts. They are not automatically sufficient for
the later serial Full Closure standard.

## 4. Retrospective evidence after historical merge

Issue #405 performed the UMI logical-materiality retrospective and established:

`UMI08-LI-01 = CONFIRMED ORACLE GAP / MEDIUM`

No current UMI-08 production projection omission was established by that finding. The gap was
that current tests did not independently reconstruct complete material for funding, network,
pricing, and perpetual parent projections, so some future omission/substitution mutations could
survive.

The owner-level Full Closure work package further required:

- `FUND-001` — complete independent funding projection;
- `NET-001` — complete network projection with identifier present;
- `NET-002` — complete network projection with identifier absent;
- `PRICE-001` — complete pricing projection from caller-unsorted roles with literal expected
  canonical order;
- `PERP-POPULATED-001` — complete parent projection with tick and network present;
- `PERP-OPTIONAL-00`, `PERP-OPTIONAL-10`, `PERP-OPTIONAL-01` — the three remaining valid optional
  parent combinations.

The populated parent must not manufacture false correlation among distinct economic identities.
The Full Closure oracle therefore deliberately uses:
- reference identity `UUID(int=2)`;
- settlement identity `UUID(int=3)`;
- multiplier unit identity `UUID(int=6)`;
- tick-value identity `UUID(int=7)`.

All four `(tick present?, network present?)` combinations are valid: `00`, `01`, `10`, `11`.
No invalid-state `object.__setattr__` corruption is used to manufacture coverage.

## 5. Full Closure production counterexample

Historical source validated UMI-08-local UUID values with:

```python
if not isinstance(value, UUID):
    ...
```

`CryptoTermsId.logical_values()` and `CryptoEvidenceRef.logical_values()` serialize
`str(self.value)`.

A Python `UUID` subclass may satisfy `isinstance(value, UUID)` while overriding `__str__`.
Therefore the historical guard did not guarantee canonical UUID textual material for UMI-08-local
IDs.

Current Full Closure classification:

`FC08-03 = LOCAL DETERMINISM / TYPE-CANONICALITY PRODUCTION DEFECT / MEDIUM`

Minimum owner-local correction:

```python
if type(value) is not UUID:
    ...
```

The correction applies only to UMI-08-local `CryptoTermsId` and `CryptoEvidenceRef` through the
existing local helper. UMI-02 and UMI-05 wrappers are not modified by this work order.

Normal exact `UUID` material remains behaviorally identical.

## 6. Historical rejection-branch debt

Historical exact-head coverage explicitly recorded these 14 UMI-08 uncovered rejection
statements:

`168, 180, 205, 213, 217, 222, 279, 314, 334, 338, 342, 346, 353, 360`

Gate A re-mapped them on the frozen starting main. They remain reachable owner-local fail-closed
branches for wrong wrapper/material types:

1. funding interval wrong type;
2. funding evidence ref wrong type;
3. network terms ID wrong type;
4. network role wrong type;
5. network evidence ref wrong type;
6. network identifier wrong type;
7. pricing evidence ref wrong type;
8. perpetual terms ID wrong type;
9. perpetual multiplier wrong type;
10. perpetual funding wrong type;
11. perpetual pricing wrong type;
12. perpetual evidence ref wrong type;
13. perpetual tick value wrong type;
14. perpetual network binding wrong type.

Full Closure does not export these as optional future hardening. The new owner-local test file hits
every branch directly while retaining the validation code unchanged.

Target: UMI-08 owner statement coverage 100%, subject to exact-candidate CI evidence at Gate C.
No pragma, suppression, skip, xfail, validation deletion, or coverage weakening is authorized.

## 7. Gate-B correction surface

Authorized branch:

`agent/qore-umi08-full-closure-001`

Authorized production mutation:
- `src/qore/infrastructure/crypto_perpetual_funding_semantics.py`;
- one semantic change only: exact `UUID` type requirement in the existing local helper.

New Full Closure oracle:
- `tests/infrastructure/test_crypto_perpetual_funding_semantics_full_closure.py`.

New current recertification ledger:
- `docs/architecture/QORE-UMI-08-FULL-CLOSURE-RECERTIFICATION-001.md`.

Files intentionally unchanged:
- historical primary UMI-08 test;
- historical UMI-08 architecture artifact.

No other source owner is modified.

## 8. Independent-oracle law

Expected logical material in the new Full Closure oracle is manually reconstructed from literal
contract facts. Expected parent material must not be built from the SUT's own
`logical_values()` or from target enum `.value` attributes.

The oracle proves, independently:

- full funding material;
- full network material both with and without NETWORK_NATIVE identifier;
- exact external-identifier nested material;
- caller-unsorted price roles normalize to the literal canonical order
  `index-price`, `last-price`, `mark-price`;
- complete perpetual parent material;
- multiplier unit identity is independent from reference identity;
- tick-value identity is independent from settlement identity;
- tick and network parent slots remain discriminating across all four valid combinations.

Existing historical semantic, fail-closed, immutability, negative-space, inverse-style, and
role-distinction tests are retained rather than replaced.

## 9. Current authority boundaries

UMI-08 owns only bounded immutable provider-neutral crypto/perpetual/funding/network contractual
qualification.

Sovereign boundaries remain:

- UMI-02 / D04: economic/reference identity, relationship graph, lifecycle, NETWORK_NATIVE external
  identifier semantics;
- UMI-05: reusable derivative multiplier/tick primitives and generic dated derivative contracts;
- D05: observed provider/venue/on-chain evidence;
- D06: clock/schedule/calendar resolution;
- D07 / UMI-10: observed mark/index/last/funding values, valuation and methodology;
- D08: account/collateral balances;
- D09: margin, liquidation, exposure, risk and capacity;
- D10 / D18: execution;
- D11: position/cash/custody/settlement/reconciliation mutation;
- UMI-11: CEX/AMM/OTC/on-chain topology;
- UMI-14 #390 lane: staking/yield-bearing/tokenization qualification.

Explicitly absent from this candidate:
- provider/exchange/blockchain support;
- wallet/custody/private-key/signing/RPC;
- oracle ingestion;
- current price or funding observations;
- margin/liquidation engine;
- settlement/payment mutation;
- execution;
- productive credentials;
- Production authorization;
- real capital.

## 10. Downstream/current-state reconciliation

Historical UMI-08 architecture listed several then-open carry-forwards. Their present state must
not be inferred from that historical artifact.

Current Gate-A reconciliation:
- #333 / `GAP-FND04-TIME-01`: CLOSED / completed — historical UMI-08 OPEN claim is stale;
- #332 / `GAP-FND07-RES-01`: OPEN — remains D08/D09/D10 cross-owner work;
- PR #298: OPEN / DRAFT / HOLD — provider-catalog lane, not UMI-08 Full Closure authority;
- other execution/research methodology gaps remain under their own owner evidence.

A cross-owner HIGH does not become UMI-08 debt merely because historical UMI-08 documentation
listed it as a carry-forward.

## 11. Open-PR overlap reconciliation

Gate A re-enumerated the ten open PRs then present:

`#401, #399, #397, #395, #393, #391, #389, #386, #298, #291`

Their cumulative changed-file sets showed zero overlap with:

- the UMI-08 production owner;
- the historical UMI-08 primary test;
- the historical UMI-08 architecture artifact;
- the new Full Closure oracle path;
- this recertification path.

PR #391 is crypto-adjacent but adds a distinct staking/yield/tokenization semantic owner and
reuses UMI-08 authority without mutating it.

Any later Gate-C qualification must recheck overlap/live main before opening the PR.

## 12. Full Closure finding ledger

### FC08-01 — historical lifecycle/status ledger

Historical #330 and architecture status do not represent present Full Closure state.

Disposition: **RESOLVED IN CURRENT RECERTIFICATION LEDGER**.
Historical artifacts remain immutable evidence of their time.

### FC08-02 — retrospective ledger

`UMI08-LI-01` and owner-level Full Closure requirements were not integrated into a current UMI-08
ledger.

Disposition: **RESOLVED IN CURRENT RECERTIFICATION LEDGER + OWNER ORACLES**.

### FC08-03 — local UUID type canonicality

Malicious UUID subclass can alter UMI-08-local deterministic material under historical
`isinstance` guard.

Disposition: **CORRECTED IN PRODUCTION + DIRECT REGRESSION ORACLE**.

### FC08-04 — historical rejection branches

Fourteen known reachable owner-local wrong-type statements lacked direct tests.

Disposition: **CORRECTED TEST-ONLY; ALL 14 DIRECTLY EXERCISED**.

### FC08-05 — logical-materiality oracle independence

Funding/network/pricing/perpetual complete projections and optional parent slots lacked complete
independent reconstruction.

Disposition: **CORRECTED TEST-ONLY** through `FUND-001`, `NET-001/002`, `PRICE-001`, populated
parent and remaining optional-state guards.

### FC08-06 — definitive Full Closure procedure gap

Historical merge predates definitive serial Gate A-F closure.

Disposition: **PROCEDURALLY CONTAINED**. This candidate does not claim the later gates. Exact
candidate audit, Gate C/D/E, post-merge exact-main CI, Claude FINAL, IA FINAL and Gate F remain
future lifecycle steps.

### FC08-07 — downstream status drift

Historical `TIME-01 OPEN/HIGH` claim became stale after #333 closure.

Disposition: **RESOLVED IN CURRENT RECERTIFICATION LEDGER** without rewriting historical evidence.

### FC08-08 — historical finding disposition

Historical `FINDING-UMI08-01..03` dispositions were not reconciled under Full Closure.

Disposition: **RESOLVED**. Their historical classifications are retained; UUID canonicality is
superseded for present closure purposes by FC08-03, while the architecture-access limitation was
historically resolved and rejection-branch hardening is now closed by FC08-04.

### FC08-09 — current-main/blob/ownership reconciliation

No current artifact bound the frozen UMI-07 baseline, current historical blobs, retrospective,
downstream state, overlap, and present correction scope.

Disposition: **RESOLVED BY THIS RECERTIFICATION ARTIFACT**.

## 13. Gate law after Gate-B correction

Gate-B completion requires:

```text
exact frozen base preserved
-> only authorized owner-local blast radius
-> FC08-01..09 corrected/resolved
-> zero verified UMI08-internal pending work
-> exact branch diff audit
-> no cross-owner scope absorption
```

Gate-B completion does not authorize or perform:
- PR creation / Gate C;
- Draft -> Ready / Gate D;
- merge / Gate E;
- #301 final evidence / Gate F;
- UMI-08 seal;
- UMI-09 activation.

Mandatory exact-candidate CI and synthetic-merge evidence attach at Gate C because the repository's
QORE CI workflow is triggered for pull requests to `main`, not arbitrary feature-branch pushes.

Until those later independently authorized gates complete:

`UMI08 FULL CLOSURE = NOT SEALED / NOT CLOSED`
