# QORE UMI-12 final owner recertification — R16 hardening

## Scope

This hardening records the independent adjudication of DeepSeek Expert R16 review `5031598732` for PR #461. R16 reviewed exact HEAD `69b0557c952f41cb074fb061a0d01e5ff1ce2db0` and reported three HIGH findings in the authoritative R15 dynamic-execution scanner.

R16 is provenance only after this correction because the candidate HEAD mutates. The historical R15 layer remains unchanged; `test_universal_cross_asset_conformance_final_owner_r16_guards.py` is the new authoritative complete-suite scanner layer.

## Independent adjudication

### Rejected — string `operator.itemgetter` token loss

R16 asserted that `operator.itemgetter("getattr")` produced an unprefixed token that `_value_from_itemgetter_token` could not resolve. Repository inspection disproved that claim: the inherited R12 helper creates string itemgetter atoms as `s:<key>`, which R15 already resolves. The exact R15 regression was also green in QORE CI #1524.

### Rejected — `operator.attrgetter("__call__")(eval)` loss

R16 asserted that R15 failed to propagate an already-dangerous callable through `attrgetter("__call__")`. Repository inspection disproved that claim: R15 falls through to the inherited R12 special-call evaluator, which explicitly returns a dangerous atom when the receiver is dangerous and the selected attribute is `__call__`.

Both rejected findings are retained as explicit R16 regressions so a future layer cannot accidentally introduce either defect.

### Accepted — direct builtins mapping `.get` loses a dangerous default on a missing key

The witness is real:

```python
import builtins
builtins.__dict__.get("missing", eval)("1+1")
```

R15 handles a direct `.get` over the builtins namespace through `_selected_static_value`. An absent static key collapses to `_UNKNOWN`; because the branch returns that value immediately, the explicit default argument is not propagated. The bound-method path already handles defaults correctly, so the direct path was inconsistent.

A naive `selected == _UNKNOWN -> default` correction would be unsound because R15 also represents safe existing builtins members such as `len` as `_UNKNOWN`. It would therefore false-positive on:

```python
builtins.__dict__.get("len", eval)("abc")
```

R16 hardening distinguishes statically known existing names in the active Python builtins namespace from absent static names. Existing names retain R15 member semantics; absent names select the explicit `.get` default. This remains bounded static analysis and does not introduce whole-program tainting.

## Regression evidence

The R16 layer requires:

- dangerous defaults to propagate for absent static keys over `builtins.__dict__` and `vars(builtins)`;
- existing safe builtins members not to take a dangerous default;
- `operator.itemgetter("getattr")` helper identity to remain preserved;
- `operator.attrgetter("__call__")(eval)` to remain dangerous;
- the complete D04 owner surface plus the unchanged historical oracle to remain free of dynamic execution markers.

## Boundary

This is test/doc-only hardening. It does not mutate `src/qore`, does not alter the historical full-closure oracle, and does not authorize provider support, execution, valuation methodology, Production readiness, or real capital.

Any later review must bind to the new exact HEAD/TREE/synthetic candidate; R16 review `5031598732` cannot authorize that mutated candidate.
