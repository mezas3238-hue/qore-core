# QORE UMI-13 — Double Hyphen Validation Closure

## Scope

This bounded correction closes the DeepSeek Expert R15 finding for `U+2E40 DOUBLE HYPHEN` inside supported composite sensitive labels such as `api key` and `private key`.

The original retained source text is not rewritten. The correction applies only to the validation skeleton used at the UMI-13 instrument-universe registry trust boundary.

## Invariant

Supported composite sensitive labels must fail closed when an in-scope printable hyphen-family separator appears between their components. The same requirement applies at construction, explicit retained-state re-entry, and logical projection.

## Correction

`_CREDENTIAL_DELIMITER_CONFUSABLES` now maps `U+2E40 DOUBLE HYPHEN` to ASCII `-` for validation only. The existing assignment grammar then evaluates the canonical validation skeleton.

This remains intentionally bounded. It does not introduce universal Unicode transliteration, does not alter valid retained/projected text, and does not expand provider, operational, Risk, Production, credential, deposit/withdrawal, or real-capital authority.

## Regression requirements

Permanent tests cover:

- `api` and `private` composite labels with `U+2E40` and both supported assignment delimiters;
- explicit retained-state `__post_init__()` re-entry;
- reason logical projection;
- evidence `source_name` and `locator` revalidation and projections;
- benign `U+2E40` text retained byte-for-byte outside sensitive syntax.

Any subsequent Core change requires a fresh full quality gate and a new Expert → Coder → Claude certification chain.
