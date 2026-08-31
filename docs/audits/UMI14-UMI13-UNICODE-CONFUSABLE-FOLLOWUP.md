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
7. Expert R7 on HEAD `f0e2b4f31f1e3802f0e108f605936433f556b8d2` showed that the bounded homoglyph table still omitted Cyrillic small letter i `и` (`U+0438`) for ASCII `u`, allowing the supported `authorization` label to escape as `a\u0438thorization=...` or `a\u0438thorization:...`;
8. Expert R8 on HEAD `9300bd9efebe053d04412e759d044711ecba81dd` showed that URL-userinfo inspection stopped after the first authority. A benign first URL could therefore mask a later embedded credential-bearing authority, for example `https://safe.example/https://alice:password@example.invalid/evidence`;
9. Expert R9 on HEAD `4ccb42efdda62e9b5070a805c45c4c602b6e953c` showed that folding `U+2215 DIVISION SLASH` / `U+2044 FRACTION SLASH` to ASCII `/` before URL-userinfo inspection could create a false authority terminator before the real `@`. The exact accepted witness was `https://alice:password\u2215foo@example.invalid/evidence`;
10. Expert R10 on HEAD `7e24bc07bf74f879ffe7655fe9217db7ff6600de` showed that NFKC itself folded `U+FF0F FULLWIDTH SOLIDUS` to ASCII `/` before the R9 preservation rule could run. The exact accepted witness was `https://alice:password／foo@example.invalid/evidence`.

Before freezing the R10 correction, independent Integration Authority falsification found the same mechanism in compatibility expansions that introduce an authority terminator. Concrete examples were `℀` (`ACCOUNT OF` → `a/c`), fullwidth question mark `？` → `?`, fullwidth number sign `＃` → `#`, and printable spacing diaeresis `¨`, whose NFKC result starts with ASCII space followed by a combining mark. After mark removal, that space would also terminate the userinfo scan. Because `/`, `?`, `#` and whitespace all terminate the regex, the correction was broadened within the same bounded class before certification.

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
- scans URL-like authority starts throughout the detection skeleton instead of trusting only the first `scheme://authority`, including scheme-relative `//authority` forms at token boundaries;
- uses a dedicated URL-userinfo detection skeleton that preserves explicit `∕` and `⁄` inside authority text while the URL authority-start matcher accepts ASCII `/`, `∕` and `⁄` as the two slash characters introducing an authority;
- normalizes each source character independently before whole-string NFKC in that URL-specific path. When a source character is not already a real URL terminator, any newly introduced `/`, `?`, `#` or whitespace is replaced by a stable detection-only non-terminator sentinel (`∕`, `¿`, `♯`, `¤`). Actual ASCII `/`, `?`, `#` and actual whitespace are not replaced, so real authority terminators keep their semantics;
- preserves ordinary printable Unicode and benign URL-like text that does not form credential-like syntax.

The bounded label set remains limited to the existing sensitive families: authorization, bearer, credential, jwt, password, secret, token, api key, access token, client secret and private key. This is not a generic Unicode transliteration contract.

## Adversarial evidence

`tests/infrastructure/test_instrument_universe_registry_unicode_confusables_followup.py` covers:

- Cyrillic and Greek homoglyphs inside sensitive labels, including the exact R3 witnesses for `password` and `authorization`, the R4B eta witnesses for `token` and `authorization`, the R5 Cyrillic-ghe witnesses for `authorization` and `bearer`, and the exact R7 Cyrillic-`и` witnesses for `authorization` with both `=` and `:` delimiters;
- bearer assignments with `=` and `:`;
- confusable colon and hyphen separators, including the exact R5 `U+2015 HORIZONTAL BAR` witnesses for `api key` and `private key` and the exact R6 `U+02D0 MODIFIER LETTER TRIANGULAR COLON` witness for `token`;
- retained-state revalidation and logical projection for the accepted homoglyph and separator witnesses, including R7 through both explicit `__post_init__()` re-entry and `logical_values()` projection;
- retained-state revalidation for source-name projections;
- preservation of unrelated printable Greek/Cyrillic text.

`tests/infrastructure/test_instrument_universe_registry_multi_authority_userinfo.py` permanently falsifies the R8/R9/R10 URL-userinfo classes and the pre-freeze Integration Authority expansion class across:

- the exact later embedded `scheme://userinfo@authority` R8 witness;
- an embedded scheme-relative `//userinfo@authority` witness;
- the exact R9 `U+2215 DIVISION SLASH`-inside-userinfo witness;
- mixed confusable authority starts and confusable slash characters inside userinfo, including `https:∕∕...` and scheme-relative `∕∕...` forms;
- the exact R10 `U+FF0F FULLWIDTH SOLIDUS` inside-userinfo witness;
- fully fullwidth-slash `https:／／...` and scheme-relative `／／...` authority starts with fullwidth slash inside userinfo;
- NFKC expansions that would otherwise manufacture `/`, `?`, `#` or whitespace before the real `@`, including `℀`, `？`, `＃` and spacing-diaeresis witnesses;
- reason construction, reflective corruption, `__post_init__()` re-entry and `logical_values()` projection;
- evidence `source_name` and `locator` construction plus retained-state re-entry, `content_logical_values()` and full `logical_values()` projection;
- benign URL-like text containing explicit and compatibility punctuation after a real ASCII path slash, which remains accepted and projected unchanged when the `@` is outside the authority.

## Exact prior QG evidence

The exact R6 correction was mechanically validated by QORE CI run `33434829089` / job `99628598400`: Ruff PASS, Mypy PASS on 744 source files, Pytest 4961/4961 PASS with 7 warnings, total coverage 47650 statements / 6236 missed / 87%, and `instrument_universe_registry.py` 290 statements / 2 missed / 99%.

The R7-corrected candidate at HEAD `9300bd9efebe053d04412e759d044711ecba81dd` was mechanically validated by QORE CI run `33439224197` / job `99643062426`: Ruff PASS, Mypy PASS on 744 source files, Pytest 4965/4965 PASS with 7 warnings, total coverage 47650 statements / 6236 missed / 87%, and `instrument_universe_registry.py` 290 statements / 2 missed / 99%.

The R8-corrected candidate at HEAD `4ccb42efdda62e9b5070a805c45c4c602b6e953c` was mechanically validated by QORE CI run `33443877562` / job `99658290366`: Ruff PASS, Mypy PASS on 745 source files, Pytest 4976/4976 PASS with 7 warnings, total coverage 47642 statements / 6236 missed / 87%, and `instrument_universe_registry.py` 282 statements / 2 missed / 99%.

The R9-corrected candidate at HEAD `7e24bc07bf74f879ffe7655fe9217db7ff6600de` was mechanically validated by QORE CI run `33447330913` / job `99669248984`: Ruff PASS, Mypy PASS on 745 source files, Pytest 4992/4992 PASS with 7 warnings, total coverage 47645 statements / 6236 missed / 87%, and `instrument_universe_registry.py` 285 statements / 2 missed / 99%.

Expert R10 was bound to that R9-corrected HEAD and returned `VALIDACIÓN NO OK`; therefore the accepted R10 correction plus pre-freeze Integration Authority closure requires a fresh exact-head FULL QG and freeze before any new semantic reviewer stage. No prior Expert result is certification evidence for the corrected candidate.

## Non-claims

This correction does not add provider support, AI-provider dependencies, execution authority, Risk bypass, Production authority, productive credentials, real-capital authority or real-money execution capability.

Any candidate change after this correction invalidates earlier semantic reviewer approval and requires a fresh exact-head QG/freeze followed by Expert → Coder → Claude certification.
