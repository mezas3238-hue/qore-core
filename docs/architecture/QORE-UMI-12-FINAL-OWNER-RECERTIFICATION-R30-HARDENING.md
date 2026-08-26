# QORE UMI-12 final owner recertification — R30 hardening

## Disposition

DeepSeek Expert R30 reviewed frozen HEAD
`4258cfe1222b8de42f807d388d507d9368db4fb7` and returned two HIGH
findings. Both were independently adjudicated as valid against Python's real
left-to-right iteration, unpacking, and starred-target semantics.

R30 is therefore consumed as a valid review of that prior HEAD but cannot
certify this correction commit.

## Accepted R30-H1 — later comprehension unpack failure

Witness:

```python
values = [fn("1+1") for fn, safe in ((len, str), (eval, len, str))]
```

The first item binds `fn = len`. The second item has arity three and raises
during unpacking before the element is evaluated. `eval` is never called.

R29 found the definite failure position but then delegated successful-prefix
execution to the inherited collapsed iterable model, which merged the
incompatible later item back into `fn`.

### Correction

The R30 scanner processes exact sequence iteration item-by-item in Python
iteration order. A definite target failure stops the current loop or the whole
comprehension before later items, filters, generators, elements, or `else`
paths can be fabricated.

The same ordered rule is applied recursively to later comprehension
generators. A definite failure in a later generator propagates outward and
terminates the comprehension path.

## Accepted R30-H2 — starred name loses slot/length correlation

Witness:

```python
for *safe, tail in ((len, eval), (len, str, exec)):
    for fn in safe:
        fn("1+1")
```

Python creates `safe` as `[len]` and then `[len, str]`; `eval` and `exec` bind
only to `tail`. The R29 collapsed fallback flattened whole items and could
place the tail values into `safe`.

### Correction

For one-starred exact structural assignment, R30 materializes the starred
capture as an abstract **sequence value** with its own exact length and
selected-slot metadata. Prefix and suffix targets receive only their exact
slots. This preserves the Python rule that starred assignment creates a list
and prevents tail values from leaking into the starred name.

Sensitive starred `Attribute`/`Subscript` targets remain fail-closed: if the
actual starred slice contains `eval`, `exec`, or another sensitive value, the
existing bounded `binding` marker still fires.

## Regression surface

R30 adds executable guards for:

- the exact R30-H1 comprehension witness;
- the exact R30-H2 starred-name witness;
- a positive starred-name case where dangerous callables really are inside the
  starred slice and must still produce a call marker;
- a later comprehension generator whose second item definitely fails unpacking
  and must stop the entire comprehension;
- a positive later-generator prefix where a dangerous call is genuinely
  reached before the later failure;
- preservation of the R29 sensitive starred-`Subscript` binding guard;
- the complete current D04 owner universe plus the unchanged historical
  full-closure oracle remaining marker-free.

## Scope remains bounded

This is a test-harness correction only. It does not add generic whole-program
taint analysis, arbitrary iterable interpretation, provider functionality,
Production authorization, execution capability, or real-capital readiness.

The bounded D04 owner convention and all prior R4-R29 accepted invariants
remain unchanged. `src/qore` is intentionally untouched.
