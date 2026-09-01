# QORE UMI-13 — Credential Invisible-Filler Closure 001

## Scope

This bounded correction closes DeepSeek Expert R11 finding `QORE-PR466-B9A1E24A-DS-EXPERT-NFKC-AUTHORITY-R11` on PR #466. The exact witness `tok\u3164en=PLAINTEXT-SECRET` showed that a printable non-mark invisible filler could interrupt a supported sensitive assignment label and survive the credential-detection skeleton.

The correction is limited to the credential-hygiene detection path. It does not rewrite retained text and does not create provider, execution, Risk, Production, productive-credential, or real-capital authority.

## Failure mechanism

The prior detection skeleton applied NFKC/casefold and removed Unicode mark categories `Mn`, `Mc`, and `Me`. `U+3164 HANGUL FILLER` is printable and category `Lo`; NFKC maps it to `U+1160 HANGUL JUNGSEONG FILLER`, also category `Lo`. The filler therefore remained between the ASCII letters of `token`, defeating both the contiguous sensitive-assignment regex and the bounded character matcher.

## Bounded correction

After NFKC/casefold, the detection-only skeleton removes the normalized invisible filler set:

- `U+115F HANGUL CHOSEONG FILLER`;
- `U+1160 HANGUL JUNGSEONG FILLER`;
- `U+2800 BRAILLE PATTERN BLANK`.

Source witnesses `U+3164 HANGUL FILLER` and `U+FFA0 HALFWIDTH HANGUL FILLER` normalize to `U+1160` and are therefore closed by the same rule. The retained original string is unchanged when it is otherwise valid.

This is deliberately not a generic Unicode transliteration or blanket deletion policy. Visible punctuation and script characters are not discarded merely because their Unicode name contains words such as `FILLER` or `GAP`.

## Required regression properties

Permanent tests prove:

- construction rejects supported sensitive labels interrupted by each immediate invisible-filler source form;
- compound labels such as `api key` cannot be split by the same fillers;
- reflective retained-state corruption fails closed in `__post_init__()` and logical projection;
- evidence `source_name` and `locator` revalidation/projection fail closed;
- benign printable filler text outside credential-like syntax remains accepted and projected byte-for-byte unchanged.

## Non-claims

This semantic hygiene correction does not establish provider support, operational readiness, Production readiness, real-capital authorization, Risk bypass, productive credentials, execution capability, deposits, withdrawals, or real-money trading authority.
