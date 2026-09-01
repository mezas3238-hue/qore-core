# UMI-14 / UMI-13 — DeepSeek Expert R19 Follow-up

## Exact reviewed candidate

- reviewed HEAD: `cda1eb8d9b53dee456e7c3639d76de7e63fbd7c8`
- reviewed TREE: `ec80768a9c6c5c585bf743fdfcd1ee50e8b871e3`
- package: `HARNESS-ENGINEER-PR466-CDA1EB8D-R19-MARK-URL-BOUNDARY-006`

## Finding

Expert R19 extends the R18B URL-boundary interaction defect to printable
combining marks. The URL-specific detection skeleton removed every
`Mn`/`Mc`/`Me` character unconditionally, including when
`preserve_invisible_fillers=True`. A printable non-alphanumeric mark placed
immediately before a scheme-relative authority start was therefore deleted
before URL-boundary evaluation, concatenating an alphanumeric prefix with the
`//` and defeating the negative-lookbehind boundary guard.

The accepted witness is
`Evidence\uFE0F//alice:password@example.invalid/evidence` (U+FE0F VARIATION
SELECTOR-16 is printable, category `Mn`).

## Root cause

R18B corrected only the five named invisible fillers. The underlying root cause
is deletion, before URL-boundary evaluation, of an accepted printable
non-alphanumeric/non-slash source character that semantically separates an
alphanumeric prefix from a scheme-relative authority start. The R18B
`preserve_invisible_fillers` flag kept the invisible fillers, but the mark
filter still removed printable `Mn`/`Mc`/`Me` marks. `_contains_url_userinfo`
then saw the `//` preceded by an ASCII letter and declined the boundary.

## Correction

Credential detection remains detection-only. The original retained/projected
text is never rewritten.

The detector now evaluates URL-userinfo presence against two URL-specific
detection skeletons:

- the existing mark/filler-removing skeleton, which still catches a mark or
  filler placed between the two authority slashes, inside userinfo, inside the
  scheme name, or inside a sensitive credential label (`token<mark>=...`);
- a new boundary-preserving skeleton (`preserve_invisible_fillers=True` and
  `preserve_marks=True`), which keeps the printable mark/filler in place so the
  scheme-relative `//` authority start stays at its original token boundary.

The general credential skeleton keeps its mark-removal behavior, so printable
mark obfuscation inside sensitive labels remains closed.

## Adversarial evidence

`tests/infrastructure/test_instrument_universe_registry_url_boundary_mark.py`
covers:

- the exact scheme-relative mark-boundary witness across `Mn`, `Mc` and `Me`
  representatives (U+FE0F, U+034F, U+0301, U+0327, U+0903, U+20DD, U+20E3);
- an alphanumeric-prefix variant (`abc<mark>//user@host`);
- retained-state re-entry and `logical_values()` projection for the reason
  value;
- evidence `source_name` and `locator` construction plus retained-state
  re-entry, `content_logical_values()` and full `logical_values()` projection;
- regression guards that marks between authority slashes, inside userinfo and
  inside the scheme name remain rejected;
- multi-authority scanning with a mark boundary;
- a guard that the general skeleton still rejects `token<mark>=...`;
- benign source text containing the same marks outside the sensitive URL
  pattern, which remains accepted and byte-identical.

## Non-claims

This correction does not add provider support, AI-provider dependencies,
execution authority, Risk bypass, Production authority, productive credentials,
real-capital authority or real-money execution capability. Prior F1-F5, R8-R10
and R18B closures are unchanged; the general detection skeleton and the
label/assignment/homoglyph contracts are untouched. No universal Unicode
transliteration is introduced.
