# UMI-14 / UMI-12 R38 hardening

## Scope

This additive hardening layer adjudicates the five DeepSeek Expert R38 findings against the frozen PR #461 candidate. All five findings are accepted as valid bounded defects in the UMI-12 falsification harness. No production semantic owner is changed and `src/qore` remains unchanged.

## Accepted findings

1. Exact starred positional arguments were evaluated but not expanded into the positional argument list used by helper semantics. A construct such as `{}.get(*["missing", eval])("1+1")` therefore lost the reachable dangerous default.
2. Tuple/list/dict expression scanning did not stop after a nested `_FAILURE_VALUE`, allowing markers from Python-unreachable later elements after a recognized exception.
3. Exact `None` mapping keys had no selection token, causing both dangerous false negatives and safe-selection false positives.
4. `builtins.__dict__.get` only resolved static string keys. Exact non-string keys such as `0` or `None` are definitely absent from the builtins namespace and must select the supplied default.
5. The special `.get` path was applied to exact sequence receivers even though `list`/`tuple` do not define `.get`; Python fails during attribute lookup before evaluating call arguments.

## Correction

`test_universal_cross_asset_conformance_final_owner_r38_guards.py` adds a bounded successor scanner. It:

- expands `ast.Starred` positional arguments only when the starred value is an exact modeled sequence;
- preserves source evaluation order and propagates definite failure through tuple/list/dict element evaluation;
- adds an exact `None` key token with last-write-wins mapping metadata;
- treats exact integer/bool/None keys as definite misses for `builtins.__dict__.get` when the inherited string resolver cannot select a member;
- fails early for `.get` on an exact sequence, before scanning arguments, while preserving exact `.__getitem__` selection;
- retains exact selected-slot behavior rather than reintroducing co-presence propagation.

## Non-claims

This layer does not claim whole-program Python interpretation, arbitrary iterable expansion, arbitrary descriptor behavior, provider readiness, operational readiness, Production readiness, real-capital authorization, or Program-D final PASS. It is confined to the bounded static falsification semantics already governed by #458/#363.
