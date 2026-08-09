from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.cibo_widget import CiboWidgetState
from qore.governance.executive_client_surface import ExecutiveClientSurfaceId
from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_state_sync import ExecutiveClientStateView
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveCommandCenterViewModelError(DomainError):
    """Base error for platform-neutral CEO Command Center view-state contracts."""

    __slots__ = ()


class ExecutiveCommandCenterViewModelValidationError(
    ExecutiveCommandCenterViewModelError
):
    """A Command Center presentation value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveCommandCenterSection(StrEnum):
    HOME = "home"
    CIBO = "cibo"
    MARKETS = "markets"
    TRADERS = "traders"
    VALIDATION_LAB = "validation-lab"
    TRADE_FORENSICS = "trade-forensics"
    PORTFOLIO = "portfolio"
    CEO_ACCOUNTS = "ceo-accounts"
    RISK = "risk"
    NEWS = "news"
    AUDIT = "audit"
    SYSTEM = "system"
    GOVERNANCE = "governance"
    CORPORATE_PROFIT_VAULT = "corporate-profit-vault"


class ExecutiveCommandCenterSectionState(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"


_SECTION_ORDER: tuple[ExecutiveCommandCenterSection, ...] = (
    ExecutiveCommandCenterSection.HOME,
    ExecutiveCommandCenterSection.CIBO,
    ExecutiveCommandCenterSection.MARKETS,
    ExecutiveCommandCenterSection.TRADERS,
    ExecutiveCommandCenterSection.VALIDATION_LAB,
    ExecutiveCommandCenterSection.TRADE_FORENSICS,
    ExecutiveCommandCenterSection.PORTFOLIO,
    ExecutiveCommandCenterSection.CEO_ACCOUNTS,
    ExecutiveCommandCenterSection.RISK,
    ExecutiveCommandCenterSection.NEWS,
    ExecutiveCommandCenterSection.AUDIT,
    ExecutiveCommandCenterSection.SYSTEM,
    ExecutiveCommandCenterSection.GOVERNANCE,
    ExecutiveCommandCenterSection.CORPORATE_PROFIT_VAULT,
)

_SCOPE_BY_SECTION: dict[ExecutiveCommandCenterSection, ExecutiveReadScope] = {
    ExecutiveCommandCenterSection.CIBO: ExecutiveReadScope.CIBO_STATE,
    ExecutiveCommandCenterSection.MARKETS: ExecutiveReadScope.MARKETS,
    ExecutiveCommandCenterSection.TRADERS: ExecutiveReadScope.TRADERS,
    ExecutiveCommandCenterSection.VALIDATION_LAB: ExecutiveReadScope.VALIDATION_LAB,
    ExecutiveCommandCenterSection.TRADE_FORENSICS: ExecutiveReadScope.TRADE_FORENSICS,
    ExecutiveCommandCenterSection.PORTFOLIO: ExecutiveReadScope.PORTFOLIO,
    ExecutiveCommandCenterSection.CEO_ACCOUNTS: ExecutiveReadScope.CEO_ACCOUNTS,
    ExecutiveCommandCenterSection.RISK: ExecutiveReadScope.RISK,
    ExecutiveCommandCenterSection.AUDIT: ExecutiveReadScope.AUDIT,
    ExecutiveCommandCenterSection.SYSTEM: ExecutiveReadScope.SYSTEM_HEALTH,
    ExecutiveCommandCenterSection.GOVERNANCE: ExecutiveReadScope.GOVERNANCE,
    ExecutiveCommandCenterSection.CORPORATE_PROFIT_VAULT:
        ExecutiveReadScope.CORPORATE_PROFIT_VAULT,
}


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveCommandCenterViewModelValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveCommandCenterViewModelValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_reason_code(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ExecutiveCommandCenterViewModelValidationError(
            "command center reason code must use canonical lowercase syntax"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveCommandCenterViewModelId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center view model id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveCommandCenterSectionView:
    """One navigation section bound to an existing client-safe state view when supported."""

    section: ExecutiveCommandCenterSection
    state: ExecutiveCommandCenterSectionState
    reason_code: str
    read_scope: ExecutiveReadScope | None = None
    client_state: ExecutiveClientStateView | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.section, ExecutiveCommandCenterSection):
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center section view requires ExecutiveCommandCenterSection"
            )
        if not isinstance(self.state, ExecutiveCommandCenterSectionState):
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center section view requires ExecutiveCommandCenterSectionState"
            )
        object.__setattr__(self, "reason_code", _validate_reason_code(self.reason_code))
        expected_scope = _SCOPE_BY_SECTION.get(self.section)
        if expected_scope is None:
            if self.read_scope is not None or self.client_state is not None:
                raise ExecutiveCommandCenterViewModelValidationError(
                    "unsupported/aggregate section must not fabricate a read scope or state"
                )
            if self.state is ExecutiveCommandCenterSectionState.AVAILABLE:
                raise ExecutiveCommandCenterViewModelValidationError(
                    "section without canonical read scope cannot be marked available"
                )
            return
        if self.read_scope is not expected_scope:
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center section must bind its canonical executive read scope"
            )
        if self.state is ExecutiveCommandCenterSectionState.AVAILABLE:
            if not isinstance(self.client_state, ExecutiveClientStateView):
                raise ExecutiveCommandCenterViewModelValidationError(
                    "available command center section requires ExecutiveClientStateView"
                )
            if self.client_state.scope is not expected_scope:
                raise ExecutiveCommandCenterViewModelValidationError(
                    "command center client state scope must match section scope"
                )
            return
        if self.client_state is not None:
            raise ExecutiveCommandCenterViewModelValidationError(
                "missing command center section must not masquerade as client state"
            )
        if self.state is ExecutiveCommandCenterSectionState.UNSUPPORTED:
            raise ExecutiveCommandCenterViewModelValidationError(
                "canonical read-scope section cannot be marked unsupported"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.section.value,
            self.state.value,
            self.reason_code,
            None if self.read_scope is None else self.read_scope.value,
            None if self.client_state is None else self.client_state.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveCommandCenterViewModel:
    """One platform-neutral CEO Command Center navigation and view-state composition."""

    view_model_id: ExecutiveCommandCenterViewModelId
    surface_id: ExecutiveClientSurfaceId
    observed_at: datetime
    selected_section: ExecutiveCommandCenterSection
    sections: tuple[ExecutiveCommandCenterSectionView, ...]
    cibo_widget: CiboWidgetState | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.view_model_id, ExecutiveCommandCenterViewModelId):
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center view model requires ExecutiveCommandCenterViewModelId"
            )
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center view model requires ExecutiveClientSurfaceId"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        if not isinstance(self.selected_section, ExecutiveCommandCenterSection):
            raise ExecutiveCommandCenterViewModelValidationError(
                "selected section requires ExecutiveCommandCenterSection"
            )
        if not isinstance(self.sections, tuple) or any(
            not isinstance(item, ExecutiveCommandCenterSectionView) for item in self.sections
        ):
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center sections must be an immutable tuple"
            )
        if tuple(item.section for item in self.sections) != _SECTION_ORDER:
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center sections must use the canonical complete navigation order"
            )
        if self.cibo_widget is not None:
            if not isinstance(self.cibo_widget, CiboWidgetState):
                raise ExecutiveCommandCenterViewModelValidationError(
                    "command center widget must be CiboWidgetState"
                )
            if self.cibo_widget.surface_id != self.surface_id:
                raise ExecutiveCommandCenterViewModelValidationError(
                    "CIBO widget surface must match Command Center surface"
                )
            if self.observed_at < self.cibo_widget.observed_at:
                raise ExecutiveCommandCenterViewModelValidationError(
                    "command center observation cannot predate widget observation"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.view_model_id.logical_values(),
            self.surface_id.logical_values(),
            self.observed_at.isoformat(),
            self.selected_section.value,
            tuple(item.logical_values() for item in self.sections),
            None if self.cibo_widget is None else self.cibo_widget.logical_values(),
        )


def _build_section_views(
    state_views: tuple[ExecutiveClientStateView, ...],
) -> tuple[ExecutiveCommandCenterSectionView, ...]:
    if not isinstance(state_views, tuple) or any(
        not isinstance(item, ExecutiveClientStateView) for item in state_views
    ):
        raise ExecutiveCommandCenterViewModelValidationError(
            "command center state views must be tuple of ExecutiveClientStateView"
        )
    by_scope: dict[ExecutiveReadScope, ExecutiveClientStateView] = {}
    for supplied_state_view in state_views:
        if supplied_state_view.scope in by_scope:
            raise ExecutiveCommandCenterViewModelValidationError(
                "command center state views must not duplicate executive read scopes"
            )
        by_scope[supplied_state_view.scope] = supplied_state_view

    section_views: list[ExecutiveCommandCenterSectionView] = []
    for section in _SECTION_ORDER:
        scope = _SCOPE_BY_SECTION.get(section)
        if scope is None:
            reason = (
                "section.aggregate"
                if section is ExecutiveCommandCenterSection.HOME
                else "scope.unsupported"
            )
            section_views.append(
                ExecutiveCommandCenterSectionView(
                    section=section,
                    state=ExecutiveCommandCenterSectionState.UNSUPPORTED,
                    reason_code=reason,
                )
            )
            continue
        matching_state_view = by_scope.get(scope)
        if matching_state_view is None:
            section_views.append(
                ExecutiveCommandCenterSectionView(
                    section=section,
                    state=ExecutiveCommandCenterSectionState.MISSING,
                    reason_code="state.missing",
                    read_scope=scope,
                )
            )
            continue
        section_views.append(
            ExecutiveCommandCenterSectionView(
                section=section,
                state=ExecutiveCommandCenterSectionState.AVAILABLE,
                reason_code="state.present",
                read_scope=scope,
                client_state=matching_state_view,
            )
        )
    return tuple(section_views)


def build_executive_command_center_view_model(
    *,
    view_model_id: ExecutiveCommandCenterViewModelId,
    surface_id: ExecutiveClientSurfaceId,
    observed_at: datetime,
    selected_section: ExecutiveCommandCenterSection,
    state_views: tuple[ExecutiveClientStateView, ...],
    cibo_widget: CiboWidgetState | None = None,
) -> Result[ExecutiveCommandCenterViewModel, ExecutiveCommandCenterViewModelError]:
    """Compose existing client-safe state into one canonical cross-platform view model."""

    try:
        sections = _build_section_views(state_views)
        return Success(
            ExecutiveCommandCenterViewModel(
                view_model_id=view_model_id,
                surface_id=surface_id,
                observed_at=observed_at,
                selected_section=selected_section,
                sections=sections,
                cibo_widget=cibo_widget,
            )
        )
    except ExecutiveCommandCenterViewModelError as error:
        return Failure(error)
