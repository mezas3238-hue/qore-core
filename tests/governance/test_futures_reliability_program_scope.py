from __future__ import annotations

from pathlib import Path

_PROGRAM = Path(
    "docs/missions/FUTURES-HOSTING-RELIABILITY-CERTIFICATION-PROGRAM.md"
)
_ARCHITECTURE = Path(
    "docs/architecture/QORE-FUTURES-RELIABILITY-PROGRAM-SCOPE-001.md"
)
_ROADMAP = Path(
    "docs/roadmap/QORE-POST-MISSION08-FUTURES-RELIABILITY-ROADMAP.md"
)
_MISSION08_CLOSURE = Path("docs/missions/MISSION-08-CLOSURE.md")

_DELIVERIES = (
    "QORE-FUTURES-RELIABILITY-PROGRAM-SCOPE-001",
    "QORE-HOSTING-RELIABILITY-LAB-CONTRACTS-001",
    "QORE-LATENCY-SAFETY-ENVELOPE-001",
    "QORE-HOSTING-IO-CERTIFICATION-001",
    "QORE-MARKET-DATA-INTEGRITY-CERTIFICATION-001",
    "QORE-RELIABILITY-INCIDENT-GENEALOGY-001",
    "QORE-EVIDENCE-GOVERNED-FAILOVER-001",
    "QORE-FUTURES-ADAPTER-CONTRACTS-001",
    "QORE-FUTURES-TRADESTATION-ADAPTER-001",
    "QORE-FUTURES-IBKR-ADAPTER-001",
    "QORE-FUTURES-TASTYTRADE-ADAPTER-001",
    "QORE-FUTURES-CROSS-PROVIDER-CERTIFICATION-001",
    "QORE-FUTURES-TRADOVATE-CANDIDATE-001",
    "QORE-SHADOW-FUTURES-CORE-CERTIFICATION-001",
    "QORE-HOSTING-RELIABILITY-DRILL-001",
    "QORE-PAPER-FUTURES-E2E-001",
    "QORE-FUTURES-RELIABILITY-CLOSURE-001",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_program_scope_opens_only_after_mission08_closure() -> None:
    assert _PROGRAM.is_file()
    assert _ARCHITECTURE.is_file()
    assert _ROADMAP.is_file()
    assert _MISSION08_CLOSURE.is_file()

    mission08 = _text(_MISSION08_CLOSURE)
    program = _text(_PROGRAM)

    assert "MISSION-08 = COMPLETED" in mission08
    assert "MISSION-08 = COMPLETED" in program
    assert "Production = CLOSED" in mission08
    assert "Production = CLOSED" in program


def test_program_formalizes_all_roadmap_work_packages_without_numeric_mission_guess() -> None:
    program = _text(_PROGRAM)
    architecture = _text(_ARCHITECTURE)

    for delivery in _DELIVERIES:
        assert delivery in program

    assert "without inventing a numeric mission identifier" in program
    assert "without assigning an arbitrary numeric mission identifier" in architecture
    assert "MISSION-09" not in program
    assert "MISSION-09" not in architecture


def test_program_preserves_trading_and_reliability_authority_separation() -> None:
    program = _text(_PROGRAM)
    architecture = _text(_ARCHITECTURE)

    required = (
        "NO CORE DECISION -> NO NEW TRADING ACTION",
        "NO RELIABILITY EVIDENCE -> NO INFRASTRUCTURE ACTION",
        "AT MOST ONE ACTIVE EXECUTION AUTHORITY PER TRADING ACCOUNT",
        "REGISTRY != AUTHORITY",
        "HEALTH != AUTHORITY",
        "TELEMETRY != AUTHORITY",
        "ORCHESTRATOR != LEASE AUTHORITY",
        "AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE",
    )
    for invariant in required:
        assert invariant in program

    assert "CORE -> CONCRETE BROKER SDK" in architecture
    assert "Never:" in architecture


def test_program_requires_three_independent_provider_certifications() -> None:
    program = _text(_PROGRAM)

    assert "1. TradeStation" in program
    assert "2. Interactive Brokers / IBKR" in program
    assert "3. tastytrade" in program
    assert "Market Data Certification" in program
    assert "Execution Certification" in program
    assert "PAPER / SIMULATION ONLY" in program
    assert "Delivery 13 is optional" in program


def test_provider_capability_is_an_external_gate_not_a_core_assumption() -> None:
    program = _text(_PROGRAM)

    assert "External provider verification — 2026-08-09" in program
    assert "TradeStation" in program
    assert "Interactive Brokers / IBKR" in program
    assert "tastytrade" in program
    assert "must be revalidated again at each provider-specific delivery" in program
    assert "external certification gates, not Core assumptions" in program
    assert "15 minutes" in program


def test_latency_integrity_shadow_and_failure_domains_are_explicit() -> None:
    program = _text(_PROGRAM)
    architecture = _text(_ARCHITECTURE)

    for metric in ("minimum", "p50", "p95", "p99", "maximum", "jitter"):
        assert metric in program

    assert "300 ms = PROVISIONAL CATASTROPHIC HARD CEILING" in program
    assert "SERVER REDUNDANCY" in architecture
    assert "FEED REDUNDANCY" in architecture
    assert "BROKER ADAPTER PORTABILITY" in architecture
    assert "SHADOW CORE" in architecture
    assert "PAPER/SIM EXECUTION" in architecture
    assert "may not silently rewrite evidence or fabricate a candle" in architecture


def test_program_keeps_secrets_issue146_and_production_closed() -> None:
    program = _text(_PROGRAM)

    assert "opaque `SecretRef` references" in program
    assert "issue #146 remains independent and OPEN/BLOCKED" in program
    assert "Production" in program
    assert "real capital" in program
    assert "Production broker execution" in program
    assert "Futures Production" in program
    assert "Native Broker Production" in program
    assert "Shadow, Paper, Simulation and Certification are not Production authorization" in program
