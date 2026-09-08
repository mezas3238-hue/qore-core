# QORE UMI-13 — Extended Dash Validation Closure

## Scope

This bounded correction closes the DeepSeek Expert R16 finding for `U+2E3A TWO-EM DASH` and `U+2E3B THREE-EM DASH` inside supported composite sensitive labels.

The retained source text is not rewritten. The correction applies only to the validation skeleton used at the UMI-13 instrument-universe registry trust boundary.

## Invariant

Supported composite sensitive labels must fail closed when an in-scope printable dash-family separator appears between their components. The same requirement applies at construction, explicit retained-state re-entry, and logical projection.

## Correction

`_CREDENTIAL_DELIMITER_CONFUSABLES` now maps `U+2E3A TWO-EM DASH` and `U+2E3B THREE-EM DASH` to ASCII `-` for validation only. The existing assignment grammar then evaluates the canonical validation skeleton.

This remains intentionally bounded. It does not introduce universal Unicode transliteration and does not alter valid retained/projected text.

## Regression requirements

Permanent tests cover:

- both new dash variants;
- the supported `api` and `private` composite labels;
- both supported assignment delimiters;
- constructor validation;
- explicit retained-state `__post_init__()` re-entry;
- reason logical projection;
- evidence `source_name` and `locator` revalidation and projections;
- benign source text retained byte-for-byte outside sensitive syntax.

Any subsequent Core change requires a fresh full quality gate and a new Expert → Coder → Claude certification chain.

## Non-claims

This semantic validation correction does not establish provider support, operational readiness, Production readiness, Risk bypass, deposits/withdrawals, or real-capital authorization.
