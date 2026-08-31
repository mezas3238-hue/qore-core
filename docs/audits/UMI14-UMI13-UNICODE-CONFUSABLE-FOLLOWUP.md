# UMI-14 / UMI-13 — Unicode confusable credential-hygiene follow-up

## Scope

This follow-up records the bounded correction of material findings raised by the exact-head DeepSeek Expert reviews of PR #466.

The accepted findings were:

1. printable cross-script homoglyphs outside NFKC could obscure supported sensitive assignment names, for example `tok\u0435n=...` with Cyrillic small letter IE;
2. `bearer=...` was not included in the sensitive-assignment grammar even though bearer material was already an explicit sensitive marker family;
3. Expert R3 on HEAD `e0cadfca635af00e2461e9117da1ebc1bf7f91ba` showed that the bounded homoglyph table still omitted Greek sigma for ASCII `s` and Cyrillic ze for ASCII `z`, allowing `pa\u03c2\u03c2word=...` and `authori\u0437ation=...` to escape;
4. Expert R4B on HEAD `d540b5be87985f21de5088af66bb178d1716110a` showed that Greek eta `η` was still omitted for ASCII `n`, allowing `toke\u03b7=...` and `authorizatio\u03b7=...` to escape;
5. Expert R5 on HEAD `0a6a6ce6145983f93dbe83a9776c2d38757dc670` showed two remaining bounded confusable gaps: `U+2015 HORIZONTAL BAR` could separate composite sensitive names such as `api\u2015key=...`, and Cyrillic small ghe `г` could replace ASCII `r` in supported labels such as `autho\u0433ization=...`;
6. Expert R6 on HEAD `554c5a81d089a6054c6f878ec4016946166af41f` showed one remaining bounded colon-family gap: `U+02D0 MODIFIER LETTER TRIANGULAR COLON` could replace ASCII `:` in supported assignments such as `token\u02d0PLAINTEXT-SECRET`;
7. Expert R7 on HEAD `f0e2b4f31f1e3802f0e108f605936433f556b8d2` showed that the bounded homoglyph table still omitted Cyrillic small letter i `и` (`U+0438`) for ASCII `u`, allowing the supported `authorization` label to escape as `a\u0438thorization=...` or `a\u0438thorization:...`.

## Correction

Credential detection remains detection-only. The original retained/projected text is never rewritten.

The detector now:

- uses NFKC plus casefold and removes Unicode mark categories before semantic credential inspection;
- canonicalizes a bounded set of punctuation confusables relevant to assignment separators, composite-name separators and URL syntax, including `U+2015 HORIZONTAL BAR` as an ASCII hyphen equivalent and `U+02D0 MODIFIER LETTER TRIANGULAR COLON` as an ASCII colon equivalent for detection;
- treats `bearer` as a first-class sensitive assignment label;
- performs a second fail-closed assignment-label check that compares sensitive ASCII labels against bounded Greek/Cyrillic/Latin homoglyph equivalents character-by-character;
- includes Greek sigma as an ASCII `s` homoglyph, which also closes Greek final sigma after `casefold()`;
- includes Cyrillic small ze as an ASCII `z` homoglyph;
- includes Greek eta as an ASCII `n` homoglyph for supported sensitive assignment labels;
- includes Cyrillic small ghe as an ASCII `r` homoglyph for supported sensitive assignment labels;
- includes Cyrillic small letter i `и` as a bounded ASCII `u` homoglyph for supported sensitive assignment labels;
- preserves ordinary printable Unicode that does not form credential-like syntax.

The bounded label set remains limited to the existing sensitive families: authorization, bearer, credential, jwt, password, secret, token, api key, access token, client secret and private key. This is not a generic Unicode transliteration contract.

## Adversarial evidence

`tests/infrastructure/test_instrument_universe_registry_unicode_confusables_followup.py` covers:

- Cyrillic and Greek homoglyphs inside sensitive labels, including the exact R3 witnesses for `password` and `authorization`, the R4B eta witnesses for `token` and `authorization`, the R5 Cyrillic-ghe witnesses for `authorization` and `bearer`, and the exact R7 Cyrillic-`и` witnesses for `authorization` with both `=` and `:` delimiters;
- bearer assignments with `=` and `:`;
- confusable colon and hyphen separators, including the exact R5 `U+2015 HORIZONTAL BAR` witnesses for `api key` and `private key` and the exact R6 `U+02D0 MODIFIER LETTER TRIANGULAR COLON` witness for `token`;
- retained-state revalidation and logical projection for the accepted homoglyph and separator witnesses, including R7 through both explicit `__post_init__()` re-entry and `logical_values()` projection;
- retained-state revalidation for source-name projections;
- preservation of unrelated printable Greek/Cyrillic text.

## Exact prior QG evidence

The exact R6 correction was mechanically validated by QORE CI run `33434829089` / job `99628598400`: Ruff PASS, Mypy PASS on 744 source files, Pytest 4961/4961 PASS with 7 warnings, total coverage 47650 statements / 6236 missed / 87%, and `instrument_universe_registry.py` 290 statements / 2 missed / 99%.

Expert R7 was bound to later HEAD `f0e2b4f31f1e3802f0e108f605936433f556b8d2` and returned `VALIDACIÓN NO OK`; therefore its accepted correction requires a fresh exact-head FULL QG and freeze before any new semantic reviewer stage. No prior Expert result is certification evidence for the corrected candidate.

## Non-claims

This correction does not add provider support, AI-provider dependencies, execution authority, Risk bypass, Production authority, productive credentials, real-capital authority or real-money execution capability.

Any candidate change after this correction invalidates earlier semantic reviewer approval and requires a fresh exact-head QG/freeze followed by Expert → Coder → Claude certification.
