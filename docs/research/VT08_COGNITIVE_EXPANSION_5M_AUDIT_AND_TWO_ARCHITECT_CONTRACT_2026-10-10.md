# QORE CORE — VT08 5M — Audit and Two-Architect Coordination Contract

**Date:** 2026-10-10  
**Repository:** `mezas3238-hue/qore-core`  
**Parent PR:** [#634](https://github.com/mezas3238-hue/qore-core/pull/634)  
**Audited HEAD:** `8405bd85c075a1cae5c9fde794721ca933304966`  
**Original handoff:** [Master handoff](VT08_COGNITIVE_EXPANSION_5M_MASTER_HANDOFF_2026-10-10.md)  
**Status:** STATIC REPOSITORY/CODE/SOURCE-REFERENCE AUDIT + HISTORICAL CI VERIFICATION. No new economic replay, empirical test, sealed holdout evaluation, DEMO or LIVE authorization performed by this audit.  
**Result:** RESEARCH ACTIVE — NOT CERTIFIED / NO PRODUCTION AUTHORITY.

## 1. Audited sources and coverage

- Confirmed PR #634 OPEN/DRAFT/UNMERGED/MERGEABLE; PR base `agent/vt08-cognitive-v1-001`.
- Verified handoff at parent commit `8405bd85...`, plus parent PR metadata/discussion.
- Examined VT08 source contract R3.9, source kernel entry-family authority, expansion evaluator and backtest, latest-PS/Core Stack frontier, cognitive orchestrator, reasoning, memory, strategy identity, hypothesis lifecycle, Situation Model, Position Intelligence, and selected unit tests/workflows.
- Verified GitHub Actions run [36177811524](https://github.com/mezas3238-hue/qore-core/actions/runs/36177811524) SUCCESS and entry-geometry census run [36177811605](https://github.com/mezas3238-hue/qore-core/actions/runs/36177811605) SUCCESS at `6020b487...`; **these runs do not verify cognitive replay and are not a new CI execution at this audit HEAD**.
- Verified sealed archive acquisition run [36079229139](https://github.com/mezas3238-hue/qore-core/actions/runs/36079229139) SUCCESS; successful acquisition is not proof of prospective validation. Older sealed economic results must remain unopened before final pre-registration.
- Consulted author TTrades' official primary-video companion [4-hour Power of Three](https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/) for qualitative C2/C3, M15 and 01/05/09 NY Forex anchors. Source precedence still requires video/framebook timestamps for any precise new fill mechanics. The site article alone does **not** authorize retest fill rules or numeric thresholds.

## 2. Confirmed technical findings

### P0-C1 — Cognitive replay bypass

- `src/qore/infrastructure/trader_lab/vt08_cognitive_expansion_5m_evaluator_v1.py` builds source-derived candidates without calling Cognitive Orchestrator.
- `src/qore/infrastructure/trader_lab/vt08_cognitive_expansion_5m_backtest_v1.py` directly models trades and PnL; it does not call `evaluate_cognitive_hypothesis()` or `evaluate_in_trade_cognition()`.
- `src/qore/infrastructure/trader_lab/vt08_cognitive_latest_ps_core_stack_frontier_v1.py` selects methodology candidates and management directly.
- Thus historic replay PF/DD is valid **for the expressly defined research contract**, not proof of full sovereign cognition applied on every action. Do not overwrite baseline. Add versioned cognitive-consumed adapter.

### P0-C2 — Expansion universe incompatible with cognitive Forex identity and memories

- Research `EXPANSION_MARKETS = (EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD)` in `vt08_cognitive_expansion_5m_v1.py`.
- `Vt08ForexSituationModel.__post_init__` validates `market in vt08_forex.AUTHORIZED_MARKETS`, which does **not** include EURJPY, USDCHF, NZDUSD or CADJPY. These four fail Situation Model construction under current frozen parent contracts.
- Both `market_anchor_prior()` and `experience_cell()` validate that same certified operational `AUTHORIZED_MARKETS`, and their embedded datasets exclude these four expansion markets.
- Required: a distinct, scoped **research authorization** and research memory interface with explicit provenance/coverage/UNKNOWN state, while keeping production `AUTHORIZED_MARKETS` and frozen certified memory untouched. Missing market-specific experience is UNKNOWN, not fabricated, borrowed or replaced with another market's statistics. New research priors require governed consumed-only evidence with as-of/partition controls. Fail closed for any unapproved market.

### P0-C3 — Metacognitive UNKNOWN currently not a binding execution veto

- `metacognitive_assessment()` returns `UNKNOWN` when `supporting_evidence` is empty.
- `reason()` selects `EXECUTE` if explicit contradiction/uncertainty and entry/CISD/PS checks all pass, **without checking this UNKNOWN metacognitive state**.
- Consequence: a fully completed-looking situation with zero supplied evidence can be accepted by reasoning (static-code finding). Create a minimal adversarial regression test. Set a clear, provenance-backed execution-material evidence policy; do not indiscriminately mark every nonmaterial unknown as a trading ban. Document that metacognition is semantically active, not only logged.

### P0-C4 — Temporal causality is declared but end-to-end provenance is not yet proven

- `Vt08ForexSituationModel` checks timezone-aware `as_of`, primitive field validity and bans explicit `terminal_pnl` / `post_outcome_label` values. These checks alone do not prove every input was derived from bars closed by `as_of`.
- Build bar-close boundary and time-availability assertions for source events, memory snapshots and position updates; adversarial future-bar/date shuffle tests; deterministic fingerprints and same-event no-rearm tests; zero same-bar order/execution lookahead.
- `RESEARCH_UNCALIBRATED_POSITION_POLICY` disables PROTECT and REDUCE; lifecycle/destination EXIT actions are available but need a source/Owner-research policy reconciliation, since exact filled-position H4 lifecycle is unresolved in R3.9. Replay execution must not silently treat proposals as broker fills.

### P0-M1 — Entry families are source identities, not complete machine contracts

- `vt08_cognitive_entry_family_authority_v1.py`: positional-entry is the *only* machine-complete current-line family; reversal, continuation, confident, open and POI-continuation remain `SOURCE_IDENTITY_ONLY`.
- Every other family requires precisely sourced: entry trigger, decision time, fill/price rule, POI/FVG conditionality, stop geometry, structural target hierarchy, lifecycle, ambiguities, and one-fill/day resolution.
- The author source recognizes shallow C2 versus deep C2/C3 qualitatively; no universal numeric cutoff is sourced. Do not fill ambiguity with after-the-fact profitable thresholds.
- Fixed 2R and H4 containment are QORE replay containments, not universal author target/lifecycle truth.

### P0-M2 — Opportunity density is not executable trade density

- Previous `M3 latest-PS` line: EURJPY 161, USDCHF 149, NZDUSD 182, CADJPY 161, USDCAD 159 trades over ~3Y. Owner rejected this density.
- Outcome-blind M3 CISD+PS geometry census: 452–502 distinct New York dates over ~3Y (~301–335 distinct dates/2Y) depending on market; **upper-bound observable reservoir, not fills**.
- Later CISD level retests ~291–318 distinct days/2Y; also **geometry only**, no source-backed historical fill authorization yet.
- Mechanical C2 profile union 1,157 over 11,655 anchors after identity deduplication; 195 separate C3 shapes. Cross-profile union is diagnostic; not permission to combine LTF M15/M5/M3 in live selection.
- C3, multiple-PS selection, both-side-sweep, exact source day, stop offsets and target priority remain unresolved. No retrospective mechanical rescue is authorized.

### P1-E1 — Economic development is mixed; currently not a certified candidate

- Consumed ~1095d narrow baseline: raw equal-risk PF EURJPY 1.3251, USDCHF .5638, NZDUSD 1.2278, CADJPY 1.0837, USDCAD .6256; managed Core Stack numbers are separate.
- Consumed ~3Y M3 latest-PS raw PF: EURJPY 1.4746, USDCHF .9479, NZDUSD .9469, CADJPY 1.0555, USDCAD 1.0599. Some management reduces DD; some degrades edge.
- The EURJPY strict 5Y Core Stack was explicitly rejected on temporal gates despite favorable aggregate metrics. Neither a management frontend nor a historic favorable subperiod can rescue certification.
- Frozen economic research gates from earlier program: PF >=1.80, DD <=6R, mean R >=0, MC p95 DD <=15R, MC positive-terminal >=.90, temporal/anchor/stress stability. The old 50 trades/2Y minimum is **retired**; owner-approved replacement density gate remains UNDECIDED. Do not invent one.

### P1-QA — CI coverage vs end-to-end proof

- Existing unit tests for cognitive contracts, memories, kernel, journey and position, plus extensive Trader Lab lab tests; workflows run ruff/mypy/pytest in their scopes.
- These do not presently prove a five-market, candle-by-candle, cognitive-consumed replay with per-trade attribution. Require new contract/integration/causal tests and an evidence artifact containing join keys and missing-decision counts.
- Keep tests that establish original certified runtime unchanged and production not exposed to the expansion market authority.

## 3. Two-architect organization — independent ownership, mandatory collaboration

### Architect A — METHODOLOGY AND SOURCE FIDELITY

**Owns:** primary TTrades provenance, R3.9/R3.2 adjudication, six entry families, C2/C3/PS/CISD/POI/targets/stops/lifecycle, M3/M5/M15 independent research profiles, bias/anchor/cardinality mechanics, density reservoir and candidate-source contract.

**Must deliver in order:**
1. Source-exact evidence table: URL/video timestamp/page/frame; quote or description; `SOURCE_EXPLICIT` / `SOURCE_INFERRED` / `QORE_CONTAINMENT` / `UNRESOLVED`. No PnL permitted in source adjudication.
2. Resolve **one** promising high-density family, if possible, with frozen market-neutral cause-and-effect entry+stop+target+lifecycle bundle before looking at economic returns; if impossible, record unresolved and prohibit fill simulation rather than invent rules.
3. A pure deterministic research `CandidateEvent` producer, with as-of and evidence fingerprints, chronological event list and no outcomes, no broker/capital authority, no cross-profile after-the-fact union.
4. A complete methodology-only baseline and candidate ledger (discovery/candidate/abstention by reason, timestamp, market, anchor, LTF, source identity, stop/target and expiry) maintaining the one-market-one-NY-day filled policy.
5. Tests: candle boundary/DST, bar-close availability, candidate/PS multiplicity, unique source identity, C2/C3 ambiguity, stop/target positivity, no invalid entry retrofilling, profile independence and no leakage.

**Ownership boundary:** Architect A never writes Cognitive Orchestrator/reasoning/memory internals, never changes QORE Risk or live certified runtime, never chooses source semantics by best PF.

### Architect B — COGNITION AND CONSUMED REPLAY

**Owns:** Cognitive V1 contracts and research market-scope adapter, per-market memories, Strategy Identity evidence binding, Causal Situation Model, reasoning/adversarial/metacognitive veto, hypothesis state machine, Journey/Position Intelligence and full cognitive replay adapter/decision ledger.

**Must deliver in order:**
1. Scoped five-market research authority: no production `AUTHORIZED_MARKETS` expansion; provenance-safe UNKNOWN market/anchor memories, no borrowed PnL, no runtime self-training.
2. Fix/prove metacognitive UNKNOWN/materiality behavior and strict fail-closed source/evidence/time validation without general-purpose arbitrary filters.
3. An independent, deterministic end-to-end replay consuming A's `CandidateEvent` stream; `WAIT` remains live, `ABSTAIN` kills its source fingerprint, `EXECUTE` only authorizes proposed admission, source rearm requires a genuinely new event.
4. In-trade per-closed-bar causal situation -> journey -> position assessment; policy gating before management actions, stop never widens, no unexplained EXIT/REDUCE/PROTECT fills, no bypass on fallback.
5. Per-candidate/trade immutable telemetry: methodology source id, cognitive decision+reason+memory fingerprints, prior event time, position lifecycle, baseline counterfactual and identical-trade attribution.
6. Tests: five-market context, unknown-memory behavior, no-evidence EXECUTE regression, ABSTAIN bypass, WAIT continuation/timeout, kill-rearm, DST/time perturbation, sentinel future bars, position monotonicity and replay reproducibility.

**Ownership boundary:** Architect B never fabricates entry families, alters source signal definitions or chooses profitable source variants, never grants lotage/leverage/capital authority, never edits sealed economics.

### Mandatory shared interface, version 1 — freeze jointly BEFORE implementation

An immutable research-only `VT08_5M_CANDIDATE_EVENT_V1` is emitted by A and consumed by B, with:
- schema/fingerprint/source-version/provenance and source-authority class;
- immutable market, side, NY anchor/date, LTF profile and **distinct** source-event identity;
- H4/cycle/C2-or-C3 and chosen entry family with machine-complete authority reference;
- observation timestamp, confirmation-bar close timestamp, earliest lawful decision/fill timestamp, source data cutoff;
- causal POI, CISD, PS identity and timestamp, entry/stop/target price/zone/expiry;
- context/evidence pointers and material unknowns, no terminal PnL, no future bar, no realized trade outcome;
- cardinality/selection contract version, research_only=true, capital_authority=false.
A supplies only complete authorized hypothetical fills or separately labeled **shape-only** events; B must refuse historical execution for shape-only or unresolved families. B may only choose EXECUTE/WAIT/ABSTAIN within A's authority and is not allowed to invent/mutate A's price mechanics.

**Decision join key:** `(market, NY_date, ltf_profile, source_event_fingerprint, decision_as_of)`. Exact deterministic one-to-many hypothesis timeline from a single causal source identity; no post-PnL reclassification.

**Collaboration protocol:** Every cross-lane schema change receives a written compatibility discussion on PR #634 and one acknowledgement from each responsible architect before shared integration. Each lane writes only to its own branch and submits its own PR for research integration. No unilateral merge or live deployment. Evidence requires each author to link commit/tests and document deviations from baseline.

## 4. Integration and certification gates

- **G0 source gate:** non-positional entry bundle has source refs and formal ambiguity resolution; unready cases are not executable.
- **G1 interface gate:** both lanes agree on typed candidate event, time/identity, source/market authority and reproducible fixture.
- **G2 cognitive-saturation gate:** 100% of admissible candidate decisions have cognition+hypothesis+memory fingerprints and temporal proof, zero noncognitive filled trades, 100% of filled positions receive causal Journey/Position decisions at required evaluation points, zero same-source ABSTAIN fallback, zero uncalibrated policies masquerading as active.
- **G3 matched replay gate:** identical input evidence and chronological candidate ledger produce (i) legacy raw, (ii) source-complete methodology, (iii) full cognitive consumed; explicitly decompose entry gating and management deltas. Do not report capital-weighted PF as source PF.
- **G4 temporal/robustness gate:** WFO, annual/monthly blocks, per-market and per-anchor PF/DD, MC block bootstrap, friction stress, top-winner dependence, missing data and DST, no duplicate cross-profile/day execution.
- **G5 pre-registered sealed holdout:** after frozen candidate and owner-approved numeric density gate, only then inspect pre-cutoff older 7Y evidence (signals and exits strictly before `2023-09-24T23:45:00Z`). Candidate failure means new candidate identity, no tuned retest on the same holdout.
- **G6 certification:** ALL market/density/economic/causal/robustness gates met, independent reviewer accepts; only explicit subsequent Owner authorization can permit DEMO/LIVE. No VPS change.

## 5. Coordination checkpoints and first tasks

1. Both architects start from the same audited commit/contract. Agree to candidate-event schema and source/decision clocks, plus a shared golden toy-day fixture.
2. A runs source-first adjudication of the best-supported non-positional entry; B builds five-market safe cognition adapters and no-evidence regression test **in parallel**.
3. A emits pure causal candidate fixture; B proves the fixture goes through reasoning, WAIT/ABSTAIN/EXECUTE and post-entry lifecycle with immutable ledger.
4. Joint integration PR/CI demonstrates 100% cognition event coverage and deterministic matched replay on consumed corpus. Do not unseal older 7Y.
5. Owner approves a new numeric density gate before freezing the final economic candidate and arranging independent certification battery.

## 6. Explicit negative claims

This audit does not claim to have run pytest, mypy, ruff, a new economic replay, an independent live-source frame adjudication of all five families, a WFO or MC; prior CI outcomes are cited as historic GitHub evidence only. The original primary video/framebook source SHA is quoted from the frozen repo contract, not recomputed from a fresh video download. Two assigned **work lanes** are not autonomous background agents; separate architect sessions must actually take ownership and publish work. The 7Y sealed validation remains unconsumed for strategy selection.

**Rule:** SOURCE FIRST — CAUSAL COGNITION NEXT — FROZEN ECONOMICS — SEALED VALIDATION LAST.
