# QORE UMI-12 Final Owner Recertification — R15 Hardening

## Status

R15 DeepSeek Expert review on PR #461 identified three bounded defects in the R14 dynamic-execution falsification layer. All three findings were independently accepted as real harness defects. This correction remains test/doc-only and does not modify `src/qore`.

## Accepted R15 findings

1. Static mapping `.get(...)` / `.__getitem__(...)` selection did not propagate the exact selected `builtins` namespace from container metadata, allowing forms such as `{"ns": builtins}.get("ns").eval(...)`.
2. `getattr` / `vars` helper identity could be lost when those builtins members were extracted through mapping or operator accessors, allowing statically resolved helper chains to evade dynamic-execution detection.
3. Dictionary metadata did not respect Python last-write-wins semantics for equivalent boolean/integer keys, producing stale dangerous metadata and false positives such as `{False: eval, 0: len}[False](...)`.

## R15 correction

The new authoritative R15 guard layer:

- records exact selected-slot metadata for statically modeled sequence and mapping positions;
- centralizes static selection semantics across direct subscript, mapping methods, `operator.getitem`, and `operator.itemgetter`;
- preserves `builtins`, dangerous callable, `getattr`, and `vars` identities only for the statically selected slot;
- applies deterministic last-write-wins construction for duplicate static mapping-key tokens, including boolean/integer key equivalence;
- preserves safe co-present values without blanket dangerous propagation;
- propagates a static `.get(...)` default when a modeled mapping key is absent while keeping `.__getitem__` misses fail-closed as unknown;
- retains every accepted R6–R14 regression through the inherited scanner chain;
- re-runs the complete current D04 owner plus historical-oracle surface through the R15 scanner.

## Quality-gate hardening after implementation

The first R15 candidate was rejected by Ruff for one unused import, the next by Mypy for a local variable-name reuse, and the subsequent candidate reached Pytest and exposed that mapping `.get(...)` defaults were unreachable on a static miss. Those failures were corrected without weakening tests or changing production code. The semantic regression remains explicit: `{}.get("missing", eval)(...)` must propagate the dangerous default, while a present safe key must continue to select the safe value.

## Boundary

This hardening changes only the UMI-12 falsification harness and its architecture evidence. It does not add provider support, runtime/network authority, valuation methodology, execution capability, Production authorization, or real-capital authority. The historical full-closure oracle remains unchanged.

Any certification from an earlier HEAD is provenance only after this mutation. The final R15 candidate must pass the complete QORE quality gate before a new exact-HEAD Expert review is dispatched.
