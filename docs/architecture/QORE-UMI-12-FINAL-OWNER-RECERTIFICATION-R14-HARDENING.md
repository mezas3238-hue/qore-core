# QORE UMI-12 Final Owner Recertification — R14 Hardening

## Status

R14 DeepSeek Expert review on PR #461 identified three bounded defects in the R13 dynamic-execution falsification layer. All three findings were independently accepted as real harness defects. This correction remains test/doc-only and does not modify `src/qore`.

## Accepted R14 findings

1. Static extraction of the `builtins` namespace from list/tuple/dict containers did not preserve position/key authority, allowing forms such as `[builtins][0].eval(...)` and equivalent `operator.getitem` / `operator.itemgetter` access.
2. Bound builtins mapping methods obtained through `getattr` or `operator.attrgetter` lost the `builtins-map` helper identity, allowing aliases of `builtins.__dict__.get` / `__getitem__` to evade the scanner.
3. Boolean static indices were not normalized in index/key contexts even though Python treats `False`/`True` as integer indices `0`/`1`.

## R14 correction

The new authoritative R14 guard layer:

- adds position/key metadata for values that statically contain the `builtins` namespace;
- propagates that namespace through direct subscript, `operator.getitem`, and `operator.itemgetter` selection;
- preserves `builtins-map:get` and `builtins-map:__getitem__` through `getattr` and `operator.attrgetter`;
- represents boolean constants with a dedicated index-only atom and resolves them only when an index/key is being interpreted;
- retains dangerous-position/key metadata from prior layers;
- adds explicit safe-selection regressions so co-present `builtins` or dangerous callables do not cause blanket false positives;
- re-runs the complete current D04 owner plus historical-oracle surface through the R14 scanner.

## Boundary

This hardening changes only the UMI-12 falsification harness. It does not add provider support, runtime/network authority, valuation methodology, execution capability, Production authorization, or real-capital authority. The historical full-closure oracle remains unchanged.

Any certification from an earlier HEAD is provenance only after this mutation. The candidate must pass the full QORE quality gate and then restart independent Expert review on the new exact HEAD.
