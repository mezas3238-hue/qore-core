# UMI-14 / UMI-13 — DeepSeek Expert R16 Follow-up

## Exact reviewed candidate

- BASE: `5a158ef0fb2e21db95f2be0685373780bf1ab197`
- obsolete reviewed HEAD: `256015297b4547b411ea447b27c4255962194775`
- obsolete reviewed TREE: `e1bcb2d7fa23d81421a5adee7f26c61b8223f2f1`
- obsolete reviewed SYNTHETIC: `b1f5125692314ecd7888a34de91c947b527db8ec`
- package: `QORE-PR466-25601529-DS-EXPERT-DOUBLE-HYPHEN-R16`
- QG run: `33467245917`
- QG job: `99729553989`

## Finding

DeepSeek Expert R16 confirmed the prior bounded dash correction and identified two adjacent dash-family variants, `U+2E3A TWO-EM DASH` and `U+2E3B THREE-EM DASH`, that were not yet canonicalized by the validation-only delimiter table.

## Independent Integration Authority adjudication

**MATERIAL VALID.**

Independent reproduction confirmed for both code points:

- Unicode category `Pd`;
- printable `True`;
- NFKC leaves the character unchanged;
- neither character existed in the reviewed delimiter table;
- the existing composite-label grammar therefore did not canonicalize those separators before validation.

The finding remains inside the already declared bounded dash-family validation class and does not justify universal Unicode transliteration.

## Correction

The same Core branch adds detection-only mappings for both variants to ASCII `-` and permanent regression coverage for constructor validation, retained-state re-entry, reason/evidence projections, both composite labels, both assignment delimiters, and benign source-text retention.

Because Core changed, Expert R16 and all earlier semantic reviews are obsolete as certification PASS evidence. A fresh FULL QG and freeze are required before restarting DeepSeek Expert.

No provider, operational, Production, Risk-bypass, deposit/withdrawal, or real-capital authority is inferred.
