# UMI-14 / UMI-13 — Unicode confusable credential-hygiene follow-up

## Scope

This follow-up records the bounded correction of two material findings raised by the exact-head DeepSeek Expert review of PR #466 at HEAD `273c04a1d75793ffa0b685aff669293f653d251f`.

The findings were independently accepted:

1. printable cross-script homoglyphs outside NFKC could obscure supported sensitive assignment names, for example `tok\u0435n=...` with Cyrillic small letter IE;
2. `bearer=...` was not included in the sensitive-assignment grammar even though bearer material was already an explicit sensitive marker family.

## Correction

Credential detection remains detection-only. The original retained/projected text is never rewritten.

The detector now:

- uses NFKC plus casefold and removes Unicode mark categories before semantic credential inspection;
- canonicalizes a bounded set of punctuation confusables relevant to assignment separators, composite-name separators and URL syntax;
- treats `bearer` as a first-class sensitive assignment label;
- performs a second fail-closed assignment-label check that compares sensitive ASCII labels against bounded Greek/Cyrillic/Latin homoglyph equivalents character-by-character;
- preserves ordinary printable Unicode that does not form credential-like syntax.

The bounded label set remains limited to the existing sensitive families: authorization, bearer, credential, jwt, password, secret, token, api key, access token, client secret and private key. This is not a generic Unicode transliteration contract.

## Adversarial evidence

`tests/infrastructure/test_instrument_universe_registry_unicode_confusables_followup.py` covers:

- Cyrillic and Greek homoglyphs inside sensitive labels;
- bearer assignments with `=` and `:`;
- confusable colon and hyphen separators;
- retained-state revalidation for reason/source-name projections;
- preservation of unrelated printable Greek/Cyrillic text.

## Non-claims

This correction does not add provider support, AI-provider dependencies, execution authority, Risk bypass, Production authority, productive credentials, real-capital authority or real-money execution capability.

Any candidate change after this correction invalidates earlier semantic reviewer approval and requires a fresh exact-head QG/freeze followed by Expert → Coder → Claude certification.
