# UMI-14 / UMI-13 — DeepSeek Expert R18B Follow-up

## Exact reviewed candidate

- reviewed HEAD: `63ca01f3c38fd0f0be875f455d561a3fc306eceb`
- reviewed TREE: `3427fdff0acc321d6309ff9223c53f9ba2a7f7d6`
- package: `HARNESS-ENGINEER-PR466-63CA01F3-R18B-URL-BOUNDARY-005`

## Finding

Expert R18B established a URL-boundary interaction defect: the URL-specific
detection skeleton removed an already-in-contract printable filler before
evaluating a scheme-relative authority boundary. Removing the filler could
concatenate an alphanumeric prefix directly with a later `//` authority start,
so the negative-lookbehind boundary guard treated the `//` as part of a word
and missed an otherwise detectable URL userinfo occurrence.

The accepted witness family is a printable invisible filler directly before a
scheme-relative authority, for example
`Evidence\u115f//alice:password@example.invalid/evidence`.

## Root cause

`_credential_detection_skeleton` removed `_CREDENTIAL_INVISIBLE_FILLERS` from
both the general and the URL-specific detection skeletons. In the URL-specific
skeleton that behavior also erased a real token boundary. The
scheme-relative matcher
`(?<![a-z0-9/∕⁄])[/∕⁄]{2}[^/?#\s]*@` then saw the `//` preceded by an
alphanumeric character and declined the boundary, even though the original
text placed the `//` after a printable invisible filler (a boundary, not an
ASCII letter or slash).

The same mechanism also covered the NFKC-equivalent fillers
`U+3164 HANGUL FILLER` and `U+FFA0 HALFWIDTH HANGUL FILLER`, which fold to
`U+1160` before filler removal, and `U+2800 BRAILLE PATTERN BLANK`.

## Correction

Credential detection remains detection-only. The original retained/projected
text is never rewritten.

The detector now evaluates URL-userinfo presence against two URL-specific
detection skeletons:

- the existing filler-removing skeleton, which still catches a filler placed
  between the two authority slashes and every prior URL protection;
- a new filler-preserving skeleton (`preserve_invisible_fillers=True`), which
  keeps the invisible printable filler in place so the scheme-relative `//`
  authority start stays at its original token boundary.

If either skeleton contains URL userinfo, the text is rejected. This preserves
the URL-specific semantic boundary and the existing fail-closed
credential/text contract without introducing transliteration or broadening
punctuation policy.

## Adversarial evidence

`tests/infrastructure/test_instrument_universe_registry_url_boundary_filler.py`
covers:

- the exact scheme-relative filler-boundary witness across all five declared
  filler sources (direct, NFKC-mapped and Braille blank);
- an alphanumeric-prefix variant (`abc<filler>//user@host`);
- retained-state re-entry and `logical_values()` projection for the reason
  value;
- evidence `source_name` and `locator` construction plus retained-state
  re-entry, `content_logical_values()` and full `logical_values()` projection;
- regression guards that fillers between authority slashes, inside userinfo and
  inside the scheme name remain rejected;
- multi-authority scanning with a filler boundary;
- benign source text containing the same fillers outside the sensitive URL
  pattern, which remains accepted and byte-identical.

## Non-claims

This correction does not add provider support, AI-provider dependencies,
execution authority, Risk bypass, Production authority, productive credentials,
real-capital authority or real-money execution capability. Prior F1-F5 closure
is unchanged; the general detection skeleton and the label/assignment/homoglyph
contracts are untouched.
