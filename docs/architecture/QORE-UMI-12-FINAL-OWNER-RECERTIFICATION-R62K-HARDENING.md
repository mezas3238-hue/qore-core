# QORE UMI-12 Final Owner Recertification — R62K Hardening

## Status

R62K is a successor falsification-harness layer for issue #458 / PR #461. It corrects a bounded R62J over-approximation in deferred `globals()` authority without modifying `src/qore`, the historical full-closure oracle, or any Production/runtime boundary.

## Independently accepted defect

R62J correctly recognized that a deferred top-level function body can observe module bindings introduced after lexical definition. Its conservative future-suffix model nevertheless treated every later module authority state as potentially observable by that callable. This produced a material false positive when dangerous authority existed only transiently and had already been rebound or removed before every point at which the callable could actually execute.

Representative predecessor witness:

```python
def run():
    return globals()["b"].eval("1+1")
import builtins as b
b = len
try:
    result = run()
except AttributeError:
    result = 3
```

CPython cannot execute `eval` in that program, while the R62J future-suffix model still retained the transient `builtins` authority for the deferred call site.

## R62K correction

The R62K layer preserves R62J as a conservative fallback and adds bounded observability precision only for ordinary synchronous top-level functions whose reachability stays inside a statically modelled direct-name alias set. It:

- associates deferred execution-sensitive calls with their owning top-level callable while excluding nested callable bodies;
- follows straight-line direct-name aliases for top-level invocation observations;
- snapshots module authority immediately before modelled direct/alias invocations;
- includes final module authority only while the callable remains reachable through a tracked direct-name binding;
- drops transient authority when the callable was never observably invoked and becomes unreachable before final state;
- falls back to the R62J future-suffix authority model whenever the callable escapes through a container, attribute, annotation, nested deferred body, or another non-modelled use;
- treats async functions and generator-backed functions conservatively through the R62J fallback;
- preserves dangerous direct/alias invocation, late-authority, nested-scope, local-namespace, and complete owner/oracle positive/negative regressions;
- executes standalone runtime witnesses with `compile(..., dont_inherit=True)` so test-module future flags cannot alter the semantics being certified.

The resulting scanner remains fail-closed outside its explicitly bounded precision domain. It does not introduce a general control-flow interpreter or claim semantic completeness for arbitrary Python execution.

## Quality evidence before this documentation mutation

Exact code HEAD `94582de9d9fbac2e852af00dd4824eeadfa7ad2c` passed QORE CI #1652 / run `33156844740` / job `98801545458` on synthetic merge `a93873a43cf3fe9af8e0b6a2d3d22b1dac0b90d5` against protected base `ebd0adf000874797653df92ea1c08a892cce6c8c`:

- CPython 3.12.14;
- `ruff check .`: clean;
- `mypy src tests`: clean across 737 source files;
- `pytest --cov=src/qore --cov-report=term-missing`: 4806 passed, 6 pre-existing collection warnings;
- coverage: 47568 statements / 6234 missed / 87%.

This documentation commit itself mutates the candidate HEAD and therefore requires a fresh exact-head QORE Quality Gate, fresh BASE/HEAD/SYNTHETIC/TREE freeze, and fresh external review before any Coder, Claude, readiness, or merge decision.

## Boundary

R62K is test/documentation-only hardening. It does not add provider support, valuation/execution capability, network authority, Production authorization, trading authority, or real-capital authority. No earlier reviewer result certifies the post-R62K candidate after mutation.
