# QORE-CIBO-COGNITIVE-EXECUTIVE-001 — Cognitive Executive Foundations

## Status

**IMPLEMENTED — BOUNDED FOUNDATION SLICE**

- Baseline: `main @ 576803fbda76970a4bbfe2287b5f9ca101d0f6c3` / `tree @ 11f35844670551ac4ab5be322272a3221e6b1c4b`
- Roadmap change order: qore-core Issue `#482 QORE-CIBO-COGNITIVE-EXECUTIVE-ARCHITECTURE-001`
- Parent roadmap: `#303`
- CIBO Trader Development foundation: `#479 / PR #480`
- Trader Lab: `#473 / PR #481`
- Trader reasoning/voice boundary: `#475`
- Economic evidence: `#472`
- CIBO roadmap amendment lineage: `#474`

This slice establishes the reusable, provider-neutral, deterministic foundations for
CIBO as the Cognitive Executive Director of QORE Core. It implements the first bounded
foundation only: cognitive contracts, governed memory, executive journals, adversarial
council deliberation, and the executive brain orchestration seam. It does **not** attempt
the full `#482` roadmap.

Canonical law enforced by this slice:

```text
CIBO THINKS / PLANS / QUESTIONS / LEARNS FROM GOVERNED EVIDENCE
CORE EXECUTES THROUGH FORMAL CONTRACTS
CIBO INTELLIGENCE != UNBOUNDED AUTHORITY
CIBO RECOMMENDATION != RISK BYPASS
CIBO REASONING != PROVIDER-NATIVE ORDER
CIBO MEMORY != SILENT SELF-REWRITE
TRADER VOICE != FORMAL SIGNAL
IDEA != TRADE AUTHORITY
MARKET KNOWLEDGE != CLAIM OF PERFECT CERTAINTY
PROFIT AFTER INTERVENTION != PROOF THAT CIBO CAUSED IMPROVEMENT
```

## Purpose

CIBO is a Cognitive Executive Director — not a chatbot, trader, signal source, or Trader
Manager. This slice provides the deterministic semantic layer for:

1. executive cognitive observations/hypotheses/uncertainty/recommendations;
2. explicit reasoning modes and bounded deliberation roles;
3. governed persistent executive memory with provenance/freshness/confidence/limitations;
4. executive decision/lesson/failure/economic-journal foundations;
5. adversarial critic / disagreement-retaining council deliberation;
6. an executive synthesis/orchestration seam that consumes exact CIBO/Trader evidence but
   can never create execution authority.

## Placement and reuse (LSP-verified)

Dependency direction was verified with semantic LSP (`findReferences`, `hover`,
`goToDefinition`):

- `src/qore/modules/cibo/` imports only `qore.kernel` (domain/functional cores) — it has
  no reverse dependency on `qore.infrastructure`.
- `src/qore/governance/` imports `qore.modules` but never `qore.infrastructure`.
- `src/qore/infrastructure/` already imports `qore.modules` in exactly one pre-existing
  edge (`research_analysis_lineage.py` -> `qore.modules.trader.contracts`), so the new
  infrastructure files may compose downward into the provider-neutral cognitive contracts.

New files (provider-neutral, no concrete LLM/model/provider import):

| File | Layer | Responsibility |
|---|---|---|
| `src/qore/modules/cibo/cognitive_contracts.py` | Domain | Reasoning modes, epistemic states, uncertainty, confidence, evidence ref, deliberation role, epistemic claim, formal recommendation |
| `src/qore/infrastructure/cibo_executive_memory.py` | Infrastructure | Governed provenance-bound memory kinds/items/store + summary index |
| `src/qore/infrastructure/cibo_executive_journal.py` | Infrastructure | Immutable executive decision/lesson/failure/economic journal + loss diagnosis + economic link semantics |
| `src/qore/infrastructure/cibo_executive_deliberation.py` | Infrastructure | Adversarial council: contributions, disagreements, critiques, synthesis, no-fake-consensus |
| `src/qore/infrastructure/cibo_executive_brain.py` | Infrastructure | Pure orchestration seam: observations + memory + evidence + deliberation -> advisory directive |

Reused exactly: `CiboEvidenceRef` (infrastructure economic/trade evidence link),
`InfrastructureError`/`DomainError`, `Result`/`Success`/`Failure`. New minimal types
exist only where reuse was semantically inexact (e.g. `CiboCognitiveEvidenceRef` is the
provider-neutral domain ref for cognitive evidence, distinct from the trader-facing
`CiboEvidenceRef`).

## Cognitive contracts

- `CiboReasoningMode`: `FAST`, `HIGH`, `MAX`, `COUNCIL_ADVERSARIAL` — reasoning-policy
  semantics, never concrete model names, token budgets, or API settings.
- `CiboEpistemicState`: `OBSERVATION`, `INFERENCE`, `HYPOTHESIS`, `OPINION`,
  `FORMAL_RECOMMENDATION`. None of these is `AUTHORIZED_ACTION`.
- `CiboUncertaintyKind`: `INSUFFICIENT_EVIDENCE`, `UNRESOLVED_CONTRADICTION`,
  `COMPETING_HYPOTHESES`, `MORE_EVIDENCE_REQUESTED`, `ABSTAIN_DEFER`,
  `BOUNDED_CONFIDENCE`. Certainty is never manufactured for fluency.
- `CiboConfidence`: bounded confidence always justified by non-empty evidence.
- `CiboFormalRecommendation`: advisory only; it exposes no order/intent/account/quantity/
  instrument/provider/promotion field.

## Governed executive memory

`CiboMemoryKind` distinguishes working, episodic, semantic, market, trader, research,
decision, economic, failure/lesson, and long-term-archive. Every `CiboMemoryItem` is
provenance-bound (explicit source ref + effective/recorded timestamps), evidence-bound,
freshness-tagged, and may carry bounded confidence and limitations. `CiboMemoryStore`
is a pure, functional append-only seam: supersession adds lineage links
(`supersedes`/`superseded_by`) without rewriting the superseded fact, and a summary index
references source records without replacing their evidence. Memory never mutates certified
Trader/CIBO code/config.

## Executive journals

`CiboJournalEntry` retains material episodes (decision, lesson, failure, economic) as
immutable, evidence-oriented entries with hypotheses/alternatives, uncertainty/questions,
consulted roles, rationale, expected result, risk assumptions, and optional
confidence-before/after. `CiboEconomicJournalLink` provides link-only semantics to exact
economic evidence (trader/instrument/market/regime, signal/decision/management/risk refs,
demo receipt/fill/reconciliation, certified PnL/cost/slippage/carry, stop/target, MFE/MAE,
drawdown/exposure, attribution) — it invents no PnL or cause. `CiboLossDiagnosis` makes
`INSUFFICIENT_EVIDENCE` first-class and keeps the eleven cause hypotheses
(risk containment, entry quality, market noise, regime change, volatility expansion, late
signal, lifecycle mismatch, instrument mismatch, stop methodology, concentration/
correlation, execution/cost degradation) as non-causal research inputs. Recording is
append-only; later outcomes link, never rewrite historical belief.

## Adversarial council deliberation

`CiboExecutiveDeliberation` binds exact identity/version/subject, retains a non-empty set
of role-bound `CiboDeliberationContribution` positions (argument/critique/opinion, each
evidence-bound with explicit uncertainty), and retains `CiboDisagreement` and
`CiboAdversarialCritique` records independently. Disagreement is never collapsed:
non-empty disagreements force a `DISAGREEMENT`/`NO_DECISION`/`BLOCKED` outcome and forbid
synthesis. `CiboCouncilSynthesis` is only present on a `DECISION` outcome with explicit
evidence. Roles are generic faculty identities, never operational privileges.

## Executive brain orchestration seam

`CiboExecutiveBrain.synthesize` combines observations, memory references (UUIDs only, never
inlined content), evidence, and an optional deliberation reference into a
`CiboExecutiveSynthesis` carrying a `CiboExecutiveDirectiveKind` — `RECOMMEND`, `QUESTION`,
`DEFER`, `REQUEST_EVIDENCE`, `REQUEST_RESEARCH`, or `ABSTAIN`. The output is advisory: it
can never construct a provider order, authorize execution, bypass Risk, or promote a Trader.

## Authority boundary

- `FORMAL_RECOMMENDATION != AUTHORIZED_ACTION`
- `CIBO DIRECTIVE != EXECUTION AUTHORITY` — directives are typed requests for later
  Policy/Risk handling, not `OrderIntent`/`AuthorizedOrderIntent`/`ExecutionSubmission`.
- `MEMORY != SELF-REWRITE` — memory can never silently change certified Trader/CIBO config.
- `COUNCIL SYNTHESIS != CONSENSUS` — disagreement is retained, never fabricated into
  consensus.
- Operational chain (unchanged): CIBO cognitive intent -> typed formal recommendation /
  command request -> Policy -> Risk -> authorized DEMO boundary -> execution ->
  reconciliation -> economic evidence -> CIBO learning evidence. Scope is TEST/DEMO only.

## Determinism

All value objects are `@dataclass(frozen=True, slots=True)` with exact runtime-type checks
(`bool != int`, no subclass laundering), timezone-aware caller-supplied timestamps, no
hidden `datetime.now()`/`uuid4()`/RNG/sleep/scheduler/thread/network, deterministic
canonical ordering, secret-material rejection in opaque refs/free text, recursive
`revalidate()` and `logical_values()` trust boundaries, and typed `Result`/`Success`/
`Failure` for operations that may fail. Correction-003 adds a unified secret detector
covering `sk-`/`AKIA`/`ghp_`/`xox`/JWT/URL-userinfo markers (fail closed, detection only,
never a rewrite) and recursive constructor revalidation (rebuild-on-entry) so that
reflectively corrupted nested material and hostile `logical_values()` projections fail
construction rather than persisting.

## Validation evidence

- `tests/modules/cibo/test_cibo_cognitive_contracts.py`
- `tests/infrastructure/test_cibo_executive_memory.py`
- `tests/infrastructure/test_cibo_executive_journal.py`
- `tests/infrastructure/test_cibo_executive_deliberation.py`
- `tests/infrastructure/test_cibo_executive_brain.py`
- `tests/infrastructure/test_cibo_cognitive_integration.py`

Closure ledger: see
`docs/architecture/QORE-CIBO-COGNITIVE-SUPERARCHITECTURE-001.md` "Roadmap conformance
ledger (CA-01..CA-18)" — CA-06/CA-07/CA-09 are `INTEGRATION_GATE_CLOSED`; CA-14/CA-15
remain open seams (the gate binds reasoning, evidence, faculty→role, calibration→
uncertainty, plus world/synthesis/evaluation/replay/plan/tool references).

Coverage includes bool/enum laundering, naive datetimes, secret-bearing refs/text, missing
evidence vs confidence, canonical ordering under permutation, reflective nested tampering
followed by revalidation, duplicate/conflicting memory identity, append-only supersession
without hindsight, disagreement-not-collapsed, and authority-boundary absence checks.

## Explicitly not implemented

This slice does **not** implement: the full `#482` roadmap (CE-03/05/06/07/08/09/10);
a Financial World Model; Market Intelligence Mesh; Trader Director / Trader Academy;
Portfolio/Capital/Allocation or Quantitative intelligence; economic accounting (owned by
`#472`); concrete vector databases, embeddings, cloud DBs, or an LLM memory service; any
concrete LLM/model/provider adapter; execution, promotion, Risk decisions, or any
authority transition; Production accounts or real-capital operations. These remain later
slices with only the minimal provider-neutral seams created here to stay composable.
