# UMI14 / UMI13 — Invisible-Filler Follow-up

## Reviewer result

DeepSeek Expert R11 reviewed exact PR #466 HEAD `b9a1e24a9cc752a230d23adc6ced490f76c29994` and returned `VALIDACIÓN NO OK`.

The material witness was:

`tok\u3164en=PLAINTEXT-SECRET`

`U+3164 HANGUL FILLER` is printable and survives the prior mark-removal policy through NFKC as `U+1160`. This interrupts the supported sensitive label `token`, allowing credential-like material to be retained and projected.

## Integration Authority adjudication — R11

The finding was independently reproduced against the exact frozen implementation and is **MATERIAL VALID**. R11 therefore does not certify the candidate and DeepSeek Coder remains blocked.

The independent follow-up bounded the immediate invisible non-mark filler class to source forms:

- `U+115F`;
- `U+1160`;
- `U+3164`;
- `U+FFA0`;
- `U+2800`.

After NFKC, the production detector only needs to remove the normalized detection-only set `U+115F`, `U+1160`, and `U+2800`. The change does not mutate retained/projected text.

## Reviewer result — R12

DeepSeek Expert R12 reviewed exact PR #466 HEAD `6373b339ca5251cb5bdfe6eba8abc73ae707aa87` and returned `VALIDACIÓN NO OK` with one material finding.

Exact witness:

`token\u0301=PLAINTEXT-SECRET`

The candidate applied NFKC before filtering Unicode marks. In that order, `n + U+0301 COMBINING ACUTE ACCENT` composes to `ń` (`U+0144`, category `Ll`). The mark filter therefore sees no remaining `Mn` code point and the sensitive label no longer matches `token`.

## Integration Authority adjudication — R12

The mechanism was independently reproduced against the exact source and runtime normalization behavior and is **MATERIAL VALID**. The corrected detection-only skeleton now applies NFD after NFKC/casefold and before mark/invisible-filler filtering. This restores combining marks to filterable form without modifying the retained or projected source string.

Permanent coverage includes multiple combining marks, both `=` and `:` delimiter forms, retained-state re-entry, logical projections, evidence `source_name` / `locator`, and benign decomposed Unicode text that must remain byte-for-byte unchanged.

DeepSeek Coder remains blocked until a fresh FULL QG and a fresh Expert review certify the new exact candidate.

## Certification consequence

Any Core modification invalidates R11 and R12 for certification. After the R12 correction, the required sequence is fresh FULL QG, new exact BASE/HEAD/TREE/SYNTHETIC freeze, fresh DeepSeek Expert, independent adjudication, DeepSeek Coder, independent adjudication, Claude, and final Integration Authority adjudication before Ready/merge.

CI success remains mechanical evidence only.

## Authority boundary

No provider support, operational readiness, Production readiness, real-capital authorization, Risk bypass, productive credentials, deposits/withdrawals, or real-money execution authority is claimed or introduced.
