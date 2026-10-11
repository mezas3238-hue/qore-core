# SCALPER — Arquitecto B: metodología, fuentes y certificación

**Parent:** #623; **task:** #757; **base:** `48525bb6dcc2ed5dd9862422ede6a272bfa3c13e`.  
**Status:** INITIALIZED, NOT CERTIFIED. Exclusive changes to source-ledger, route grammar, stop/target parity, V53/V54 harness quality and source-fidelity gates.

## Primary-source differential already checked
- [TTrades Scalping Model](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/): Daily broader directional context; H1 bias (including Candle-2/3 closure); M15 swing; M1 entry/continuation, protected swing stop, HTF target.
- [TTrades Asia](https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/): positional OR 4H Candle-2→M15, higher-TF framework mandatory for literal Asia.
- [TTrades London](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/): Daily→4H→M15 route, not literal H1→M15→M1.
- [TTrades NY Manipulation](https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/): FVG/OB/another refinement are alternatives; CISD confirms sweep/reversal.
- [TTrades FTM](https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/): failed reversal + HTF reason + new continuation; not standalone.
- ICT derivations require video timestamp per hard rule; unresolved is not approved.
- QORE V49 frozen H1→M15→M1 for all sessions is **a specialization**; do not rewrite it as a verbatim universal TTrades model.
- Older `capitalizer_dual_source_entry_acceptance_v1.py` requires M1 MSS AND FVG AND OB, contrary to V49 alternative trigger policy and unsupported as universal by NY source. Prove exact callable chain before deleting/altering old gates.

## Immediate safe patches
1. Quality-only: Ruff I001 in V53 winner-preserving rearm economics and V54 structural partial/runner, plus Mypy five-field/two-field key variable in V54-A; verify current GitHub run before and after.
2. Complete one ledger row per executable rule with primary source, exact section/video timestamp, mandatory/alternative, caller, time horizon, route, conflict status, and action. All hard clauses must be MATCH or approved-QORE-adaptation, **never fabricated SOURCE_FAITHFUL**.
3. Build `AUTHOR_SOURCE_GRAPH -> QORE_RULE_GRAPH -> DIFF` for Generic, Asia, London, NY manipulation and FTM. Decide exact applicable model identity per session; refer source conflicts to Owner without changing frozen H1/M15/M1.
4. Add code-level fail-closed `author_fidelity_audit_passed` check to certification (with missing/false/true tests) and separate `owner_observed_dd_at_most_6r` acceptance when evidence is sufficient. Preserve current V2 numeric thresholds and backward compatibility.
5. Compare exact source engine to replay candidate path + fills/stops/targets and controlled cognitive adapter; publish A/B preregistration and preserved edge metrics.

## Collaboration
Consume Architect A's `ScalperCausalDecisionTrace v1` and independently verify every source plan and execution decision. Ask for evidence of per-trade Master Frame invocation (no fake readiness). Cross-review A's PR in #756; A reviews the source/route semantics here.

## Hard rejection boundaries
90 trades are *not* a viable final high-frequency solution. Winner count >=80% and winner-R >=90%. Observe Owner DD <=6R acceptance on top of V2 DD<=10R per-era criterion. Fresh independent/prospective OOS after candidate freeze, no VPS/production/live/merge.
