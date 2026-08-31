# QORE-UMI-13-RECURSIVE-REGISTRY-REVALIDATION-001

## Status and scope

**PROGRAM D / UMI-13 — OWNER-STAGE CORRECTION CANDIDATE; INDEPENDENT CERTIFICATION REQUIRED**

Tracking: Issue #465

Parent final audit: Issue #363

Discovery baseline: `main@5a158ef0fb2e21db95f2be0685373780bf1ab197`
Accepted finding: `UMI14-R2-UMI13-REVALIDATION-001`

This additive evidence records the bounded correction to the retained-state trust
boundary in `instrument_universe_registry.py`. It does not rewrite either the
historical 2026-08-15 inventory or the later UMI-13 full-closure ledger.

```text
EXACT RUNTIME TYPE
!= VALID RETAINED CHILD STATE

SUCCESSFUL ORIGINAL CONSTRUCTION
!= PERMANENT VALIDITY AFTER REFLECTIVE CORRUPTION

LOGICAL PROJECTION
= TRUST BOUNDARY THAT MUST REVALIDATE
```

## Accepted defect

The prior contract validated local values and exact child types during ordinary
construction, but trusted those frozen/slotted objects during later projections.
Python reflective mutation through `object.__setattr__` could therefore corrupt a
retained reason or evidence locator after construction. Re-entering snapshot
`__post_init__()` did not recursively validate the child state, and
`logical_values()` could emit credential-like material.

The accepted witness retained both:

- `token=PLAINTEXT-SECRET` in an `InstrumentUniverseReason`;
- `https://alice:password@example.invalid/evidence` in an evidence locator.

The defect is classified as a material D04 / UMI-13 canonical-evidence integrity
defect. It is not evidence of provider, operational, execution, risk, settlement or
Production readiness.

The first published candidate exposed the same retained-state class in the three
local `StrEnum` contracts. Exact enum type and member identity did not prove that a
process-global singleton still retained its canonical `_name_` and `_value_` after
reflective mutation. This follow-up closes accepted finding
`F-UMI13-ENUM-REVALIDATION-002` without expanding the owner boundary.

Subsequent independent DeepSeek Expert review of an obsolete candidate exposed two
credential-hygiene gaps at the same Core trust boundary:

- assignments with whitespace before the delimiter, such as
  `token = PLAINTEXT-SECRET`, were accepted;
- scheme-relative authority userinfo, such as
  `//alice:password@example.invalid/evidence`, was accepted.

Both findings were independently reproduced and accepted. A later fresh Expert
review of the corrected candidate then exposed one remaining bounded gap: composite
credential names allowed only zero or one separator, so values such as
`api   key = PLAINTEXT-SECRET` and `private   key = PLAINTEXT-SECRET` could still
pass. That finding was also independently reproduced and accepted.

The next exact-head Expert review exposed a Unicode-obfuscation variant of the same
credential-hygiene boundary. Internal NBSP (`U+00A0`) and zero-width space
(`U+200B`) were not rejected by the prior C0/DEL-only control check, allowing values
such as `api\u00a0key = PLAINTEXT-SECRET` and
`token\u200b=PLAINTEXT-SECRET` to evade the credential detector. This finding was
accepted as material because the retained text could still be projected through the
same logical-value trust edges. The current candidate rejects every non-printable
Unicode character before credential analysis while preserving legitimate printable
Unicode text.

## Corrected trust edges

The correction revalidates before hashing, set construction, sorting, relationship
checks or output:

1. evidence, owner and semantic refs plus reasons re-enter their local validators in
   every `logical_values()` call;
2. evidence records revalidate their exact evidence ref and all content fields in
   `__post_init__()`, `content_logical_values()` and `logical_values()`;
3. entries revalidate the imported `IdentityFamilyCode` through its canonical UMI-02
   validator after enforcing exact class and exact plain-`str` state, then revalidate
   every local ref and reason;
4. snapshots recursively revalidate every exact entry and evidence record before
   any graph operation;
5. snapshot `logical_values()` re-enters full graph validation;
6. `entry_for_family()` revalidates both the snapshot graph and the query
   `IdentityFamilyCode` before returning a retained child;
7. evidence-source, coverage and owner enums validate the canonical name and value
   of every known singleton before retained-member comparisons or projection;
   business decisions use the independently retained primitive canonical value, not
   mutable `StrEnum` equality or hashing;
8. `_validate_text` rejects non-printable Unicode before semantic inspection, then
   rejects supported sensitive-assignment families even when the delimiter is
   preceded by whitespace and when composite names (`api key`, `access token`,
   `client secret`, `private key`) contain multiple space, underscore or hyphen
   separators; URL userinfo is rejected for both ordinary `scheme://authority` and
   scheme-relative `//authority` forms.

All boundary failures remain deterministic
`InstrumentUniverseRegistryValidationError` failures. Valid tuple shapes and
canonical ordering remain unchanged.

## Permanent falsification evidence

`tests/infrastructure/test_instrument_universe_registry_recursive_revalidation.py`
uses independently written primitive expected tuples and direct reflective
corruption. It covers:

- credential material injected into a reason;
- URL userinfo injected into an evidence locator;
- corrupt evidence, owner and semantic reference codes;
- construction of new aggregates from exact children already corrupted, including an
  unhashable ref value rejected by the owner validator before hashing;
- corrupt imported `IdentityFamilyCode` state in an entry and lookup query;
- isolated subprocess mutation of `_value_` and `_name_` for all three local enum
  classes, covering evidence record, entry and snapshot re-entry/projection;
- explicit `__post_init__()` re-entry;
- evidence content/full projections, entry projection, snapshot projection and
  snapshot lookup;
- unchanged valid logical output and deterministic ordering.

`tests/infrastructure/test_instrument_universe_registry_credential_variants.py`
adds permanent adversarial coverage for the Expert follow-up findings:

- whitespace-tolerant sensitive assignments across authorization, credential, JWT,
  password, secret, token, API key, access token, client secret and private key;
- multiple-space composite credential names at construction and retained-state
  revalidation/projection boundaries;
- NBSP and zero-width Unicode credential obfuscation at construction and retained
  revalidation/projection boundaries;
- preservation of legitimate printable Unicode text;
- scheme-relative authority userinfo at construction and after reflective
  corruption, including evidence content and full logical projections.

## Non-claims and gate

```text
THIS CORRECTION DOES NOT AUTHORIZE PRODUCTION
THIS CORRECTION DOES NOT AUTHORIZE REAL CAPITAL
THIS CORRECTION DOES NOT ESTABLISH PROVIDER OR OPERATIONAL READINESS
THIS CORRECTION DOES NOT BYPASS RISK
```

CI green is mechanical evidence only. The candidate requires exact-head quality
evidence, independent review, Integration Authority adjudication, protected merge,
post-merge quality validation and a fresh execution of parent audit #363.
