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
same logical-value trust edges. The candidate then rejected every non-printable
Unicode character before credential analysis while preserving legitimate printable
Unicode text.

A fresh Expert review of that exact candidate found that printable Unicode could
still obfuscate the same credential grammar. Fullwidth `=` (`U+FF1D`) and `@`
(`U+FF20`) survived the printable-character gate while remaining compatibility
equivalents of ASCII credential delimiters, and printable Unicode marks such as
variation selector-16 (`U+FE0F`) could interrupt a token before an ASCII delimiter.
The finding was independently reproduced and accepted. Credential detection now
uses a detection-only NFKC skeleton and removes Unicode mark categories (`Mn`,
`Mc`, `Me`) before applying the existing marker, assignment and URL-userinfo gates.
The retained original value is neither normalized nor rewritten.

Later exact-head Expert rounds closed bounded Greek/Cyrillic label and punctuation
confusables, including the accepted R7 Cyrillic small letter i `и` witness for
`authorization`. Expert R8 on HEAD
`9300bd9efebe053d04412e759d044711ecba81dd` then exposed a distinct URL-userinfo
iteration defect: `_contains_url_userinfo` inspected only the first authority in a
retained string. Thus a benign first URL could mask a later credential-bearing URL,
for example
`https://safe.example/https://alice:password@example.invalid/evidence`. The same
text validator protects reasons, evidence source names and evidence locators, so the
finding was independently reproduced and accepted as material at the retained-state
trust boundary.

Expert R9 on HEAD `4ccb42efdda62e9b5070a805c45c4c602b6e953c` then exposed a
second URL-userinfo defect in the corrected scanner. The global detection skeleton
folded `U+2215 DIVISION SLASH` and `U+2044 FRACTION SLASH` to ASCII `/` before
URL inspection. In `https://alice:password\u2215foo@example.invalid/evidence`, that
folding created an artificial path terminator before the real `@`, causing the
userinfo regex to miss a credential-bearing authority. The finding was independently
reproduced and accepted as material.

Expert R10 on HEAD `7e24bc07bf74f879ffe7655fe9217db7ff6600de` then showed that
NFKC itself could recreate the same class before the R9 protection ran. In the exact
witness `https://alice:password／foo@example.invalid/evidence`, `U+FF0F FULLWIDTH
SOLIDUS` normalized to ASCII `/`, manufacturing a terminator before the real `@`.
The finding was independently reproduced and accepted as material.

Before freezing the R10 correction, Integration Authority falsification widened the
same mechanism without changing scope. Compatibility characters can expand under
NFKC to strings containing `/`, `?`, `#` or whitespace, each of which terminates
the URL-userinfo regex. Concrete witnesses include `℀` (`ACCOUNT OF` → `a/c`),
`？` → `?`, `＃` → `#`, and printable spacing diaeresis `¨` → ASCII space plus a
combining mark; after mark removal that last case leaves an artificial space before
`@`. The correction therefore protects every authority terminator introduced by a
non-terminating source character's per-character NFKC expansion while leaving real
ASCII `/`, `?`, `#` and real whitespace untouched.

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
8. `_validate_text` rejects non-printable Unicode before semantic inspection. For
   credential detection only, printable text is NFKC-folded and Unicode marks are
   removed so compatibility delimiters and invisible printable marks cannot hide
   credential syntax. The existing detectors then reject supported sensitive
   assignments with whitespace before delimiters and multiple space, underscore or
   hyphen separators in composite names. URL-userinfo detection scans URL-like
   authority starts throughout a dedicated URL skeleton, including later embedded
   `scheme://authority` and scheme-relative forms. Explicit slash confusables `∕`
   and `⁄` remain un-folded inside that URL skeleton. Before whole-string NFKC,
   source characters are normalized individually; for any source character that is
   not already a real URL terminator, newly introduced `/`, `?`, `#` or whitespace
   is replaced by a stable detection-only non-terminator sentinel (`∕`, `¿`, `♯`,
   `¤`). Real ASCII terminators and real whitespace remain terminators. The
   authority-start matcher accepts ASCII `/`, `∕` and `⁄` in the two slash positions,
   closing ordinary, explicit-confusable and NFKC-confusable authority starts without
   rewriting retained text.

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

`tests/infrastructure/test_instrument_universe_registry_unicode_confusables.py`
adds permanent falsification for printable Unicode credential obfuscation:

- fullwidth `=` in sensitive assignments;
- printable variation-selector marks interleaved into sensitive names;
- fullwidth `@` inside URL authorities at construction and retained-state
  revalidation/projection boundaries;
- preservation of legitimate printable combining Unicode in the original retained
  and projected value.

`tests/infrastructure/test_instrument_universe_registry_multi_authority_userinfo.py`
adds permanent R8/R9/R10 plus pre-freeze Integration Authority coverage for:

- a later embedded credential-bearing `scheme://authority` after a benign first URL;
- an embedded scheme-relative credential-bearing authority;
- the exact R9 `U+2215 DIVISION SLASH` inside-userinfo witness;
- mixed `https:∕∕...` and scheme-relative `∕∕...` authority starts with a slash
  confusable retained inside userinfo before `@`;
- the exact R10 `U+FF0F FULLWIDTH SOLIDUS` inside-userinfo witness plus fully
  fullwidth-slash `https:／／...` and scheme-relative `／／...` authority starts;
- NFKC expansions that manufacture `/`, `?`, `#` or whitespace before the real
  `@`, including `℀`, fullwidth question mark, fullwidth number sign and spacing
  diaeresis witnesses;
- reason construction, reflective corruption, explicit `__post_init__()` re-entry
  and logical projection;
- evidence source-name and locator construction plus retained-state re-entry,
  content projection and full logical projection;
- benign URL-like text containing explicit and NFKC-derived compatibility
  punctuation after a real ASCII path slash, which remains byte-for-byte unchanged.

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
