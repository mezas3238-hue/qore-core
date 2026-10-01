# CIBO Architect 2 — Integrator Patch Request 006

Status: **T03 FALSIFICATION RECOMMENDATION READY**

Architect 2 recommends:

`T03 -> FALSIFIED_AND_CLOSED`

Scope:

`CURRENT_GOVERNED_CTRADER_DEMO_T03_CONTRACT`

## Evidence

The earlier direct-provider screen already exhausted distinct enabled
single-instrument duplicates for the governed targets.

Architect 2 then ran a read-only exhaustive two-leg screen against the current
352-symbol cTrader DEMO catalog:

- workflow: `36936279830` — SUCCESS
- head: `9925d0f0a0e1fb88ba4da8eb15b602652e4423f8`
- artifact: `11197727438`
- artifact digest:
  `sha256:bbb52ebf064d3e90459a4fadc79b020dd04a158e2fbb6ec815c420e28b19d78f`
- report digest:
  `sha256:6630821cf0867f358ca5de28a7443e9870ef1b018168be2fdb3f8293106d407d`
- catalog symbols: 352
- enabled FX/XAU pair surface: 34
- evaluated multi-leg routes: 33
- surviving continuous lower-margin routes: **0**

Targets screened:

- AUDJPY
- EURUSD
- GBPJPY
- GBPUSD
- XAUUSD

Even before discrete-volume rounding or execution costs, no route improves
margin. The best observed continuous margin ratio remained above 1, with the
synthetic routes generally consuming approximately twice the direct margin.

For NAS100, the provider direct-candidate screen has no duplicate expression.
US30 and US500 are separately evidenced as hedge proxies with non-zero basis;
they are not exact normalized-exposure equivalents and therefore cannot be
relabelled as T03 candidates.

The frozen T03 comparison contract requires same provider/account scope.
Architect 2 therefore does not invent an alternate-provider path after seeing
the result. No candidate survives to the fresh-OOS utility stage.

## Governance

- read-only provider work: true
- broker mutation: false
- Phase22 V2 outcomes used: false
- productive authority: false
- canonical ledger modified: false

The Integrator should independently verify the evidence and, if accepted,
transition T03 to `FALSIFIED_AND_CLOSED`.
