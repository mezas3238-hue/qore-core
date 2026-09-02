# QORE UMI-13 — Double Oblique Hyphen Credential Closure

## Scope

This bounded correction closes the DeepSeek Coder R14B witness for `U+2E17 DOUBLE OBLIQUE HYPHEN` inside supported composite credential labels such as `api key` and `private key`.

The retained source text is not rewritten. The change affects only the credential-detection skeleton used by the UMI-13 instrument-universe registry trust boundary.

## Invariant

Supported composite sensitive labels must fail closed when an in-scope printable hyphen-family confusable separates their components. A value such as:

```text
private⸗key=PLAINTEXT-SECRET
```

must be rejected at construction, retained-state re-entry, and logical projection.

## Correction

`_CREDENTIAL_DELIMITER_CONFUSABLES` now maps `U+2E17 DOUBLE OBLIQUE HYPHEN` to ASCII `-` for detection only. The existing assignment grammar then evaluates the canonical detection skeleton.

This is intentionally bounded. It does not introduce universal Unicode transliteration, does not alter valid retained/projected text, and does not expand provider, operational, Risk, Production, credential, deposit/withdrawal, or real-capital authority.

## Regression requirements

Permanent tests cover:

- `api⸗key` and `private⸗key` with both `=` and `:`;
- explicit retained-state `__post_init__()` re-entry;
- reason logical projection;
- evidence `source_name` / `locator` revalidation and projections;
- benign `U+2E17` text retained byte-for-byte outside credential-like syntax.

Any subsequent Core change requires a fresh full quality gate and a new Expert → Coder → Claude certification chain.
