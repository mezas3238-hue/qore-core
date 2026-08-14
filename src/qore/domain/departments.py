from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.kernel.errors import DomainError


class DepartmentArchitectureError(DomainError):
    """Base error for canonical QORE department architecture."""

    __slots__ = ()


class DepartmentValidationError(DepartmentArchitectureError):
    """Invalid department descriptor, dependency, or registry."""

    __slots__ = ()


class DepartmentId(StrEnum):
    """Stable identifiers for the CEO-frozen canonical department registry."""

    CORE_GOVERNANCE = "D01"
    IDENTITY_SECURITY = "D02"
    PLATFORM_CONNECTIVITY = "D03"
    MARKETS_INSTRUMENTS = "D04"
    MARKET_DATA = "D05"
    TIME_LIFECYCLE = "D06"
    VALUATION_ANALYTICS = "D07"
    ACCOUNT_PORTFOLIO = "D08"
    RISK = "D09"
    ORDER_EXECUTION = "D10"
    POST_TRADE = "D11"
    RESEARCH_QUANT = "D12"
    DECISION_INTELLIGENCE = "D13"
    LINEAGE_VALIDATION = "D14"
    OBSERVABILITY_RELIABILITY = "D15"
    DISTRIBUTED_RUNTIME_CLOUD = "D16"
    SIGNAL_DISTRIBUTION = "D17"
    CLIENT_EXECUTION = "D18"
    CLIENT_READ_MODELS = "D19"
    EXECUTIVE_CONTROL = "D20"
    COMMERCIAL_ENTITLEMENTS = "D21"
    COMPLIANCE_AUDIT = "D22"
    NOTIFICATIONS = "D23"
    CERTIFICATION_GATE = "D24"


class DepartmentInteractionMode(StrEnum):
    """Logical interaction mode for one canonical dependency edge."""

    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"


@dataclass(frozen=True, slots=True)
class DepartmentSpec:
    """Stable descriptor for one canonical QORE department."""

    department_id: DepartmentId
    slug: str
    canonical_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.department_id, DepartmentId):
            raise DepartmentValidationError("department_id must be DepartmentId")
        if not isinstance(self.slug, str):
            raise DepartmentValidationError("department slug must be str")
        if not isinstance(self.canonical_name, str):
            raise DepartmentValidationError("canonical department name must be str")
        if fullmatch(r"[a-z][a-z0-9-]*", self.slug) is None:
            raise DepartmentValidationError(
                "department slug must use lowercase letters, digits, or hyphens"
            )
        if not self.canonical_name.strip():
            raise DepartmentValidationError("canonical department name must not be empty")
        if self.canonical_name != self.canonical_name.strip():
            raise DepartmentValidationError(
                "canonical department name must not have surrounding whitespace"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.department_id.value, self.slug, self.canonical_name)


@dataclass(frozen=True, slots=True)
class DepartmentDependency:
    """Directed consumer-to-provider dependency between canonical departments."""

    consumer: DepartmentId
    provider: DepartmentId
    mode: DepartmentInteractionMode

    def __post_init__(self) -> None:
        if not isinstance(self.consumer, DepartmentId):
            raise DepartmentValidationError("dependency consumer must be DepartmentId")
        if not isinstance(self.provider, DepartmentId):
            raise DepartmentValidationError("dependency provider must be DepartmentId")
        if not isinstance(self.mode, DepartmentInteractionMode):
            raise DepartmentValidationError(
                "dependency mode must be DepartmentInteractionMode"
            )
        if self.consumer is self.provider:
            raise DepartmentValidationError("department cannot depend on itself")

    def logical_values(self) -> tuple[str, ...]:
        return (self.consumer.value, self.provider.value, self.mode.value)


@dataclass(frozen=True, slots=True)
class DepartmentRegistry:
    """Immutable registry with fail-closed dependency validation."""

    departments: tuple[DepartmentSpec, ...]
    dependencies: tuple[DepartmentDependency, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.departments, tuple):
            raise DepartmentValidationError("departments must be tuple")
        if not isinstance(self.dependencies, tuple):
            raise DepartmentValidationError("dependencies must be tuple")
        if not all(isinstance(spec, DepartmentSpec) for spec in self.departments):
            raise DepartmentValidationError("departments must contain DepartmentSpec values")
        if not all(
            isinstance(dependency, DepartmentDependency)
            for dependency in self.dependencies
        ):
            raise DepartmentValidationError(
                "dependencies must contain DepartmentDependency values"
            )

        ids = tuple(spec.department_id for spec in self.departments)
        if len(set(ids)) != len(ids):
            raise DepartmentValidationError("department ids must be unique")

        slugs = tuple(spec.slug for spec in self.departments)
        if len(set(slugs)) != len(slugs):
            raise DepartmentValidationError("department slugs must be unique")

        names = tuple(spec.canonical_name for spec in self.departments)
        if len(set(names)) != len(names):
            raise DepartmentValidationError("canonical department names must be unique")

        known_ids = set(ids)
        for dependency in self.dependencies:
            if dependency.consumer not in known_ids:
                raise DepartmentValidationError(
                    f"unknown consumer department: {dependency.consumer.value}"
                )
            if dependency.provider not in known_ids:
                raise DepartmentValidationError(
                    f"unknown provider department: {dependency.provider.value}"
                )

        edge_keys = tuple(
            (dependency.consumer, dependency.provider, dependency.mode)
            for dependency in self.dependencies
        )
        if len(set(edge_keys)) != len(edge_keys):
            raise DepartmentValidationError("department dependency edges must be unique")

        self._resolve_synchronous_order()

    def _resolve_synchronous_order(self) -> tuple[DepartmentSpec, ...]:
        by_id = {spec.department_id: spec for spec in self.departments}
        synchronous = tuple(
            dependency
            for dependency in self.dependencies
            if dependency.mode is DepartmentInteractionMode.SYNCHRONOUS
        )
        remaining = sorted(self.departments, key=lambda spec: spec.department_id.value)
        resolved: set[DepartmentId] = set()
        ordered: list[DepartmentSpec] = []

        while remaining:
            next_remaining: list[DepartmentSpec] = []
            progressed = False
            for spec in remaining:
                providers = tuple(
                    dependency.provider
                    for dependency in synchronous
                    if dependency.consumer is spec.department_id
                )
                if all(provider in resolved for provider in providers):
                    ordered.append(by_id[spec.department_id])
                    resolved.add(spec.department_id)
                    progressed = True
                else:
                    next_remaining.append(spec)
            if not progressed:
                raise DepartmentValidationError(
                    "synchronous department dependency cycle detected"
                )
            remaining = next_remaining

        return tuple(ordered)

    def resolve_synchronous_order(self) -> tuple[DepartmentSpec, ...]:
        """Return a deterministic provider-before-consumer synchronous order."""
        return self._resolve_synchronous_order()

    def spec(self, department_id: DepartmentId) -> DepartmentSpec:
        """Return one canonical descriptor or fail closed if it is unknown."""
        if not isinstance(department_id, DepartmentId):
            raise DepartmentValidationError("department_id must be DepartmentId")
        for spec in self.departments:
            if spec.department_id is department_id:
                return spec
        raise DepartmentValidationError(
            f"unknown canonical department: {department_id.value}"
        )

    def dependencies_for(
        self,
        department_id: DepartmentId,
        *,
        mode: DepartmentInteractionMode | None = None,
    ) -> tuple[DepartmentDependency, ...]:
        """Return deterministic dependencies consumed by one department."""
        if not isinstance(department_id, DepartmentId):
            raise DepartmentValidationError("department_id must be DepartmentId")
        if mode is not None and not isinstance(mode, DepartmentInteractionMode):
            raise DepartmentValidationError(
                "mode must be DepartmentInteractionMode or None"
            )
        if department_id not in {spec.department_id for spec in self.departments}:
            raise DepartmentValidationError(
                f"unknown canonical department: {department_id.value}"
            )
        selected = tuple(
            dependency
            for dependency in self.dependencies
            if dependency.consumer is department_id
            and (mode is None or dependency.mode is mode)
        )
        return tuple(
            sorted(
                selected,
                key=lambda dependency: (
                    dependency.provider.value,
                    dependency.mode.value,
                ),
            )
        )

    def logical_values(self) -> tuple[object, ...]:
        """Canonical registry material independent of declaration order."""
        department_values = tuple(
            spec.logical_values()
            for spec in sorted(
                self.departments,
                key=lambda spec: spec.department_id.value,
            )
        )
        dependency_values = tuple(
            dependency.logical_values()
            for dependency in sorted(
                self.dependencies,
                key=lambda dependency: (
                    dependency.consumer.value,
                    dependency.provider.value,
                    dependency.mode.value,
                ),
            )
        )
        return (department_values, dependency_values)


CANONICAL_DEPARTMENTS: tuple[DepartmentSpec, ...] = (
    DepartmentSpec(
        DepartmentId.CORE_GOVERNANCE,
        "core-governance",
        "Core Governance & Constitutional Contracts",
    ),
    DepartmentSpec(
        DepartmentId.IDENTITY_SECURITY,
        "identity-security",
        "Identity, Security & Cryptographic Trust",
    ),
    DepartmentSpec(
        DepartmentId.PLATFORM_CONNECTIVITY,
        "platform-connectivity",
        "Platform Connectivity & Provider Capability",
    ),
    DepartmentSpec(
        DepartmentId.MARKETS_INSTRUMENTS,
        "markets-instruments",
        "Markets, Instruments & Reference Data",
    ),
    DepartmentSpec(
        DepartmentId.MARKET_DATA,
        "market-data",
        "Market Data & Market Evidence",
    ),
    DepartmentSpec(
        DepartmentId.TIME_LIFECYCLE,
        "time-lifecycle",
        "Time, Calendars, Sessions & Instrument Lifecycle",
    ),
    DepartmentSpec(
        DepartmentId.VALUATION_ANALYTICS,
        "valuation-analytics",
        "Valuation, Pricing, Yield & Analytics",
    ),
    DepartmentSpec(
        DepartmentId.ACCOUNT_PORTFOLIO,
        "account-portfolio",
        "Account, Cash, Collateral & Portfolio",
    ),
    DepartmentSpec(
        DepartmentId.RISK,
        "risk",
        "Risk, Margin, Exposure & Limits",
    ),
    DepartmentSpec(
        DepartmentId.ORDER_EXECUTION,
        "order-execution",
        "Order, Execution & Routing",
    ),
    DepartmentSpec(
        DepartmentId.POST_TRADE,
        "post-trade",
        "Position, Settlement, Post-Trade & Reconciliation",
    ),
    DepartmentSpec(
        DepartmentId.RESEARCH_QUANT,
        "research-quant",
        "Research, Replay & Quant",
    ),
    DepartmentSpec(
        DepartmentId.DECISION_INTELLIGENCE,
        "decision-intelligence",
        "Decision Intelligence — CIO / CIBO / Specialized Traders",
    ),
    DepartmentSpec(
        DepartmentId.LINEAGE_VALIDATION,
        "lineage-validation",
        "Data Lineage, Knowledge, Statistics & Validation",
    ),
    DepartmentSpec(
        DepartmentId.OBSERVABILITY_RELIABILITY,
        "observability-reliability",
        "Observability, Reliability & Incident Operations",
    ),
    DepartmentSpec(
        DepartmentId.DISTRIBUTED_RUNTIME_CLOUD,
        "distributed-runtime-cloud",
        "Distributed Runtime, Hosting, VPS & Cloud Operations",
    ),
    DepartmentSpec(
        DepartmentId.SIGNAL_DISTRIBUTION,
        "signal-distribution",
        "Signal Production, Security & Distribution",
    ),
    DepartmentSpec(
        DepartmentId.CLIENT_EXECUTION,
        "client-execution",
        "Client Execution Ecosystem — EA / Agent",
    ),
    DepartmentSpec(
        DepartmentId.CLIENT_READ_MODELS,
        "client-read-models",
        "Client Read Models & Widget Presentation",
    ),
    DepartmentSpec(
        DepartmentId.EXECUTIVE_CONTROL,
        "executive-control",
        "Executive / CEO Control Surfaces",
    ),
    DepartmentSpec(
        DepartmentId.COMMERCIAL_ENTITLEMENTS,
        "commercial-entitlements",
        "Commercial Products, Billing, Payments & Entitlements",
    ),
    DepartmentSpec(
        DepartmentId.COMPLIANCE_AUDIT,
        "compliance-audit",
        "Compliance, Regulatory Evidence & Audit Reporting",
    ),
    DepartmentSpec(
        DepartmentId.NOTIFICATIONS,
        "notifications",
        "Notifications & Client/Operational Communication",
    ),
    DepartmentSpec(
        DepartmentId.CERTIFICATION_GATE,
        "certification-gate",
        "Certification & Integration Gate",
    ),
)


S = DepartmentInteractionMode.SYNCHRONOUS
A = DepartmentInteractionMode.ASYNCHRONOUS
D = DepartmentId


CANONICAL_DEPARTMENT_DEPENDENCIES: tuple[DepartmentDependency, ...] = (
    DepartmentDependency(D.MARKET_DATA, D.MARKETS_INSTRUMENTS, S),
    DepartmentDependency(D.MARKET_DATA, D.TIME_LIFECYCLE, S),
    DepartmentDependency(D.MARKET_DATA, D.PLATFORM_CONNECTIVITY, A),
    DepartmentDependency(D.VALUATION_ANALYTICS, D.MARKETS_INSTRUMENTS, S),
    DepartmentDependency(D.VALUATION_ANALYTICS, D.TIME_LIFECYCLE, S),
    DepartmentDependency(D.VALUATION_ANALYTICS, D.MARKET_DATA, A),
    DepartmentDependency(D.ACCOUNT_PORTFOLIO, D.MARKETS_INSTRUMENTS, S),
    DepartmentDependency(D.ACCOUNT_PORTFOLIO, D.VALUATION_ANALYTICS, A),
    DepartmentDependency(D.ACCOUNT_PORTFOLIO, D.POST_TRADE, A),
    DepartmentDependency(D.RISK, D.MARKETS_INSTRUMENTS, S),
    DepartmentDependency(D.RISK, D.ACCOUNT_PORTFOLIO, S),
    DepartmentDependency(D.RISK, D.MARKET_DATA, A),
    DepartmentDependency(D.RISK, D.VALUATION_ANALYTICS, A),
    DepartmentDependency(D.RISK, D.POST_TRADE, A),
    DepartmentDependency(D.ORDER_EXECUTION, D.PLATFORM_CONNECTIVITY, S),
    DepartmentDependency(D.ORDER_EXECUTION, D.MARKETS_INSTRUMENTS, S),
    DepartmentDependency(D.ORDER_EXECUTION, D.ACCOUNT_PORTFOLIO, S),
    DepartmentDependency(D.ORDER_EXECUTION, D.RISK, S),
    DepartmentDependency(D.POST_TRADE, D.PLATFORM_CONNECTIVITY, S),
    DepartmentDependency(D.POST_TRADE, D.MARKETS_INSTRUMENTS, S),
    DepartmentDependency(D.POST_TRADE, D.ORDER_EXECUTION, S),
    DepartmentDependency(D.POST_TRADE, D.ACCOUNT_PORTFOLIO, A),
    DepartmentDependency(D.RESEARCH_QUANT, D.MARKETS_INSTRUMENTS, S),
    DepartmentDependency(D.RESEARCH_QUANT, D.TIME_LIFECYCLE, S),
    DepartmentDependency(D.RESEARCH_QUANT, D.MARKET_DATA, A),
    DepartmentDependency(D.DECISION_INTELLIGENCE, D.MARKETS_INSTRUMENTS, S),
    DepartmentDependency(D.DECISION_INTELLIGENCE, D.TIME_LIFECYCLE, S),
    DepartmentDependency(D.DECISION_INTELLIGENCE, D.MARKET_DATA, A),
    DepartmentDependency(D.DECISION_INTELLIGENCE, D.VALUATION_ANALYTICS, A),
    DepartmentDependency(D.DECISION_INTELLIGENCE, D.ACCOUNT_PORTFOLIO, A),
    DepartmentDependency(D.DECISION_INTELLIGENCE, D.RESEARCH_QUANT, A),
    DepartmentDependency(D.LINEAGE_VALIDATION, D.MARKET_DATA, A),
    DepartmentDependency(D.LINEAGE_VALIDATION, D.RESEARCH_QUANT, A),
    DepartmentDependency(D.LINEAGE_VALIDATION, D.DECISION_INTELLIGENCE, A),
    DepartmentDependency(D.DISTRIBUTED_RUNTIME_CLOUD, D.IDENTITY_SECURITY, S),
    DepartmentDependency(D.DISTRIBUTED_RUNTIME_CLOUD, D.ACCOUNT_PORTFOLIO, S),
    DepartmentDependency(D.DISTRIBUTED_RUNTIME_CLOUD, D.OBSERVABILITY_RELIABILITY, A),
    DepartmentDependency(D.DISTRIBUTED_RUNTIME_CLOUD, D.COMMERCIAL_ENTITLEMENTS, A),
    DepartmentDependency(D.SIGNAL_DISTRIBUTION, D.IDENTITY_SECURITY, S),
    DepartmentDependency(D.SIGNAL_DISTRIBUTION, D.DECISION_INTELLIGENCE, S),
    DepartmentDependency(D.SIGNAL_DISTRIBUTION, D.COMMERCIAL_ENTITLEMENTS, S),
    DepartmentDependency(D.SIGNAL_DISTRIBUTION, D.OBSERVABILITY_RELIABILITY, A),
    DepartmentDependency(D.CLIENT_EXECUTION, D.IDENTITY_SECURITY, S),
    DepartmentDependency(D.CLIENT_EXECUTION, D.ACCOUNT_PORTFOLIO, S),
    DepartmentDependency(D.CLIENT_EXECUTION, D.RISK, S),
    DepartmentDependency(D.CLIENT_EXECUTION, D.ORDER_EXECUTION, S),
    DepartmentDependency(D.CLIENT_EXECUTION, D.DISTRIBUTED_RUNTIME_CLOUD, S),
    DepartmentDependency(D.CLIENT_EXECUTION, D.SIGNAL_DISTRIBUTION, S),
    DepartmentDependency(D.CLIENT_EXECUTION, D.COMMERCIAL_ENTITLEMENTS, S),
    DepartmentDependency(D.CLIENT_READ_MODELS, D.ACCOUNT_PORTFOLIO, A),
    DepartmentDependency(D.CLIENT_READ_MODELS, D.POST_TRADE, A),
    DepartmentDependency(D.CLIENT_READ_MODELS, D.OBSERVABILITY_RELIABILITY, A),
    DepartmentDependency(D.CLIENT_READ_MODELS, D.DISTRIBUTED_RUNTIME_CLOUD, A),
    DepartmentDependency(D.CLIENT_READ_MODELS, D.CLIENT_EXECUTION, A),
    DepartmentDependency(D.CLIENT_READ_MODELS, D.COMMERCIAL_ENTITLEMENTS, A),
    DepartmentDependency(D.EXECUTIVE_CONTROL, D.CORE_GOVERNANCE, S),
    DepartmentDependency(D.EXECUTIVE_CONTROL, D.IDENTITY_SECURITY, S),
    DepartmentDependency(D.EXECUTIVE_CONTROL, D.OBSERVABILITY_RELIABILITY, A),
    DepartmentDependency(D.COMMERCIAL_ENTITLEMENTS, D.IDENTITY_SECURITY, S),
    DepartmentDependency(D.COMPLIANCE_AUDIT, D.CORE_GOVERNANCE, A),
    DepartmentDependency(D.COMPLIANCE_AUDIT, D.LINEAGE_VALIDATION, A),
    DepartmentDependency(D.COMPLIANCE_AUDIT, D.OBSERVABILITY_RELIABILITY, A),
    DepartmentDependency(D.COMPLIANCE_AUDIT, D.COMMERCIAL_ENTITLEMENTS, A),
    DepartmentDependency(D.NOTIFICATIONS, D.OBSERVABILITY_RELIABILITY, A),
    DepartmentDependency(D.NOTIFICATIONS, D.CLIENT_READ_MODELS, A),
    DepartmentDependency(D.NOTIFICATIONS, D.COMMERCIAL_ENTITLEMENTS, A),
    DepartmentDependency(D.CERTIFICATION_GATE, D.CORE_GOVERNANCE, A),
    DepartmentDependency(D.CERTIFICATION_GATE, D.LINEAGE_VALIDATION, A),
    DepartmentDependency(D.CERTIFICATION_GATE, D.OBSERVABILITY_RELIABILITY, A),
    DepartmentDependency(D.CERTIFICATION_GATE, D.COMPLIANCE_AUDIT, A),
)


CANONICAL_DEPARTMENT_REGISTRY = DepartmentRegistry(
    departments=CANONICAL_DEPARTMENTS,
    dependencies=CANONICAL_DEPARTMENT_DEPENDENCIES,
)
