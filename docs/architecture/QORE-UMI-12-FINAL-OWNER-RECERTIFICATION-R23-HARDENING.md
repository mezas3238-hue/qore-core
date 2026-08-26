# QORE UMI-12 final owner recertification — R23 hardening

## Trigger

DeepSeek Expert R23 on exact HEAD `d2366381a630b67222328dc30878f60ec3e8e772` found a bounded false negative in the authoritative R20C scanner inheritance chain:

```python
for fn in (eval,):
    fn("1+1")
```

The R20 `ast.For` / `ast.AsyncFor` branch scanned the iterable but discarded its abstract value, assigned `_UNKNOWN` to the loop target, and therefore missed the reachable `eval` call.

## Adjudication

The synchronous `for` finding is accepted. Python iterates an exact tuple, binds `fn` to each element, and executes the body. The correction therefore propagates the semantic atoms of any statically known non-empty sequence into the synchronous loop target. This closes both the exact singleton witness and the same bounded defect for an exact multi-element sequence such as `(len, eval)`.

The review suggestion to apply the same tuple propagation to `async for` is intentionally not adopted. A plain tuple is not an asynchronous iterable; `async for fn in (eval,)` raises before binding `fn` or entering the body. Treating that tuple as an async yielded value would create a false positive. Unknown asynchronous iterables remain `_UNKNOWN`; no arbitrary async-iterator analysis is introduced.

## Scope

The R23 layer:

- inherits all R20B global/delete semantics and R20C class-scope mutation fail-closed behavior;
- changes only synchronous `ast.For` target propagation for exact non-empty sequence values;
- preserves executable assignment-target scanning and existing environment merge behavior;
- adds regressions for singleton dangerous iteration, multi-element dangerous iteration, safe singleton iteration, and the sync-tuple `async for` negative;
- re-runs the complete current owner plus historical-oracle dynamic-execution surface.

No `src/qore` code changes. No provider, runtime, execution, Production, credential, or real-capital authority is introduced.
