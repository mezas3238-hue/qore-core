# QORE UMI-12 Final Owner Recertification — R50 Hardening

## Scope

This additive hardening closes the valid DeepSeek Expert R50 finding on the frozen UMI-14 / UMI-12 final-owner recertification candidate.

R50 identified that exact builtins identity had been enforced at final `Ellipsis` lookup endpoints, while inherited namespace-derivation helpers could still collapse a mixed abstract value containing both `builtins` and an unknown alternative into the exact builtins namespace.

The affected derivations were:

- `vars(value)`;
- `getattr(value, "__dict__")`;
- `operator.attrgetter("__dict__")(value)`.

For a branch-merged receiver such as `builtins if flag else SafeLookup()`, that promotion was unsound. On the non-builtins branch, `__dict__["Ellipsis"]` may be an ordinary numeric value, so unary arithmetic can succeed and a later `eval`/`exec` call remains reachable.

## Correction

`test_universal_cross_asset_conformance_final_owner_r50_guards.py` adds a successor scanner over the R49 layer. It requires exact abstract-value equality with the canonical builtins namespace before any of the three namespace-derivation paths can return the builtins namespace.

A mixed or otherwise non-exact receiver remains unknown instead of being promoted from mere builtins co-presence.

The correction is deliberately bounded:

- historical scanner layers remain unchanged;
- exact builtins behavior remains preserved;
- mixed `vars`, `getattr(..., "__dict__")`, and `attrgetter("__dict__")` witnesses must preserve reachable later dynamic calls;
- the full current owner surface plus the historical closure oracle must remain free of dynamic-execution markers.

## Boundaries

This change is tests/docs-only. It does not modify `src/qore`, provider behavior, runtime composition, execution capability, Production authorization, or real-capital readiness.

A green local/CI suite is necessary but not sufficient for semantic acceptance. Any new candidate HEAD requires a fresh exact-head adversarial review chain.
