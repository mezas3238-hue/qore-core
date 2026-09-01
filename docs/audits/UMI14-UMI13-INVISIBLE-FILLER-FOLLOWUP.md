# UMI14 / UMI13 — Invisible-Filler Follow-up

## Reviewer result

DeepSeek Expert R11 reviewed exact PR #466 HEAD `b9a1e24a9cc752a230d23adc6ced490f76c29994` and returned `VALIDACIÓN NO OK`.

The material witness was:

`tok\u3164en=PLAINTEXT-SECRET`

`U+3164 HANGUL FILLER` is printable and survives the prior mark-removal policy through NFKC as `U+1160`. This interrupts the supported sensitive label `token`, allowing credential-like material to be retained and projected.

## Integration Authority adjudication

The finding was independently reproduced against the exact frozen implementation and is **MATERIAL VALID**. R11 therefore does not certify the candidate and DeepSeek Coder remains blocked.

The independent follow-up bounded the immediate invisible non-mark filler class to source forms:

- `U+115F`;
- `U+1160`;
- `U+3164`;
- `U+FFA0`;
- `U+2800`.

After NFKC, the production detector only needs to discard the normalized detection-only set `U+115F`, `U+1160`, and `U+2800`. The change does not mutate retained/projected text.

## Certification consequence

Any Core modification invalidates R11 for certification. After the correction, the required sequence is fresh FULL QG, new exact BASE/HEAD/TREE/SYNTHETIC freeze, fresh DeepSeek Expert, independent adjudication, DeepSeek Coder, independent adjudication, Claude, and final Integration Authority adjudication before Ready/merge.

CI success remains mechanical evidence only.

## Authority boundary

No provider support, operational readiness, Production readiness, real-capital authorization, Risk bypass, productive credentials, deposits/withdrawals, or real-money execution authority is claimed or introduced.
