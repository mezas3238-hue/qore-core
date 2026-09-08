# UMI-14 / UMI-13 — DeepSeek Coder R14B Follow-up

## Exact reviewed candidate

- BASE: `5a158ef0fb2e21db95f2be0685373780bf1ab197`
- obsolete reviewed HEAD: `7f4f3c7138b04ec26c7d4b2c448046dd5b2a164f`
- obsolete reviewed SYNTHETIC: `02b1ec1f851289d54e911e8a008a9d54494d1648`
- package: `QORE-PR466-7F4F3C71-DS-CODER-COMBINING-MARK-R14B`
- review run: `33462489079`
- review job: `99715411569`

## Finding

DeepSeek Coder R14B reported that `U+2E17 DOUBLE OBLIQUE HYPHEN` remained outside the bounded delimiter-confusable table. The exact witness was:

```text
private⸗key=PLAINTEXT-SECRET
```

The reviewer reported that the value was accepted and projected because `U+2E17` is printable, is not changed by NFKC, is not a Unicode mark, and was not mapped to ASCII `-` before the composite-sensitive-label checks.

## Independent Integration Authority adjudication

**MATERIAL VALID.**

Independent reproduction confirmed:

- `U+2E17` has Unicode category `Pd` and is printable;
- NFKC leaves it unchanged;
- the exact reviewed `_CREDENTIAL_DELIMITER_CONFUSABLES` did not contain it;
- `private(?:[ _-]*key)` therefore did not match the witness;
- the confusable label matcher also did not skip it before the correction.

This remains inside the already declared bounded hyphen-family credential-hygiene class; it does not justify a universal Unicode-confusable expansion.

## Correction

The same Core branch adds detection-only mapping:

```python
("⸗", "-"),
```

and permanent regressions for construction, retained-state re-entry, reason/evidence projections, `api key` / `private key`, both assignment delimiters, and benign source-text retention.

Because Core changed, Expert R13 and Coder R14B are obsolete as certification PASS evidence. A fresh FULL QG, freeze, DeepSeek Expert, independent adjudication, DeepSeek Coder, independent adjudication, Claude review, and final Integration Authority adjudication are required.

No provider/operational/Production/real-capital authority is inferred.
