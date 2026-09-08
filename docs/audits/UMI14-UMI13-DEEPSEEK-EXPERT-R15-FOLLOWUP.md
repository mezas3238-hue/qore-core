# UMI-14 / UMI-13 — DeepSeek Expert R15 Follow-up

## Exact reviewed candidate

- BASE: `5a158ef0fb2e21db95f2be0685373780bf1ab197`
- obsolete reviewed HEAD: `a872d12db02690b25fb5b66f4f116baa2ad0085e`
- obsolete reviewed TREE: `3cf47539f28bd2bf87126a8e1d161462af53e3e9`
- obsolete reviewed SYNTHETIC: `935c086bcffbfe9f2d8f63a0f968aa7e2f02d393`
- package: `QORE-PR466-A872D12D-DS-EXPERT-DOUBLE-OBLIQUE-HYPHEN-R15`
- review run: `33464610498`
- review job: `99721776546`

## Finding

DeepSeek Expert R15 confirmed the previous `U+2E17` correction and identified an adjacent bounded hyphen-family variant, `U+2E40 DOUBLE HYPHEN`, that was not yet canonicalized by the validation-only delimiter table.

The reported mechanism was that `U+2E40` is printable, remains unchanged by NFKC, is not a Unicode mark or retained filler, and therefore remained visible between the components of a supported composite sensitive label.

## Independent Integration Authority adjudication

**MATERIAL VALID.**

Independent reproduction confirmed:

- Unicode name: `DOUBLE HYPHEN`;
- Unicode category: `Pd`;
- printable: `True`;
- NFKC leaves the character unchanged;
- the reviewed `_CREDENTIAL_DELIMITER_CONFUSABLES` did not contain the character;
- the existing composite-label grammar and label matcher therefore did not canonicalize that separator before validation.

The finding is inside the already declared bounded hyphen-family validation class. It does not justify universal Unicode transliteration.

## Correction

The same Core branch adds the detection-only mapping:

```python
("⹀", "-"),
```

Permanent regression coverage verifies both supported composite labels, both supported assignment delimiters, construction, retained-state re-entry, reason/evidence projections, and benign source-text retention.

Because Core changed, Expert R15 and every earlier semantic review are obsolete as certification PASS evidence. A fresh FULL QG and freeze are required before restarting DeepSeek Expert on the corrected candidate.

No provider, operational, Production, or real-capital authority is inferred.
