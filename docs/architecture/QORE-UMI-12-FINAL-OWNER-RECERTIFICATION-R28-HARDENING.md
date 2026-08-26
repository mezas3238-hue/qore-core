# QORE UMI-12 final owner recertification — R28 hardening

## Trigger

DeepSeek Expert R28 reviewed PR #461 at exact HEAD
`134ffe6d2d740d3334167fb60eb90ed73ccfdbcc` and reported three HIGH
iteration-target findings.

Each finding was independently adjudicated against Python assignment and
unpacking semantics before changing the candidate.

## Adjudication

### R28-H1 — divergent outer sequence lengths

**REJECTED as stated.**

Witness:

```python
for fn, safe in ((eval,) if False else (eval, exec)):
    fn("1+1")
```

The selected iterable is `(eval, exec)`. Each loop item is therefore a builtin
function object, not a two-element sequence. On the first iteration Python
attempts `fn, safe = eval` and raises `TypeError` before entering the body.
The existing zero-marker result is correct. Widening this witness to a call
marker would create a false positive.

R28 adds an explicit negative regression so this invalid reachability claim
cannot drive a later widening.

### R28-H2 — sensitive `Attribute`/`Subscript` below `Starred`

**ACCEPTED.**

A starred loop target can legally store its collected list into an executable
attribute or subscript target. R25 delegated that store directly to the base
`_assign_target`, which does not model `Attribute`/`Subscript`; R27's
fail-closed sensitive-target rule was therefore bypassed.

R28 keeps the existing exact prefix/suffix distribution but routes the starred
target value back through `_assign_iterated_target`. Sensitive starred values
assigned to `Attribute`/`Subscript` now emit the same bounded `binding` marker
as ordinary iteration targets. No arbitrary container taint is introduced.

### R28-H3 — ordered target execution before a later unpacking failure

**ACCEPTED.**

For a structurally compatible outer unpack, Python performs target stores from
left to right. A later nested unpacking failure does not erase target
expressions already executed earlier in the assignment.

R27 computed whole-target reachability first and returned before scanning any
target expression when a later nested target was impossible. R28 replaces
that all-or-nothing step with ordered target-execution reachability:

- an immediate arity/non-iterable failure occurs before child target stores;
- after a compatible outer unpack, child targets are visited in Python store
  order;
- execution scanning stops at the first statically definite nested failure;
- target expressions before that failure are scanned;
- target expressions after it, plus the loop/comprehension body, remain
  unreachable;
- ambiguous structure stays conservative rather than being declared
  unreachable.

The same ordered rule is used for synchronous `for` and comprehensions.

## Regression evidence

The new R28 guard covers:

- the rejected H1 witness as an explicit safe negative;
- starred `Subscript` receiving `eval`, which must fail closed with `binding`;
- a prefix subscript containing `eval(...)` before a later nested arity failure;
- the inverse ordering, proving a subscript after an earlier failure is not
  scanned;
- the equivalent comprehension ordering;
- a compatible starred-name safe-selected-slot negative;
- complete current owner + historical oracle zero-marker recertification.

## Scope

This remains a tests/docs-only UMI-12 recertification hardening. It does not
change `src/qore`, the historical full-closure oracle, provider support,
Production authorization, execution readiness, or real-capital posture.
