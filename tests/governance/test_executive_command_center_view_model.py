from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.governance.cibo_widget import (
    CiboWidgetMode,
    CiboWidgetStateId,
    build_cibo_widget_state,
)
from qore.governance.executive_client_surface import ExecutiveClientSurfaceId
from qore.governance.executive_command_center_view_model import (
    ExecutiveCommandCenterSection,
    ExecutiveCommandCenterSectionState,
    ExecutiveCommandCenterViewModelValidationError,
    ExecutiveCommandCenterViewModelId,
    build_executive_command_center_view_model,
)
from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_state_sync import (
    ExecutiveClientStateStatus,
    ExecutiveClientStateView,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 15, 0, tzinfo=UTC)
_SURFACE = ExecutiveClientSurfaceId(UUID("58000000-0000-0000-0000-000000000001"))


def _state(
    scope: ExecutiveReadScope,
    *,
    status: ExecutiveClientStateStatus = ExecutiveClientStateStatus.UNAVAILABLE,
) -> ExecutiveClientStateView:
    return ExecutiveClientStateView(
        status=status,
        scope=scope,
        observed_at=_NOW,
        reason_code="state.unavailable" if status is ExecutiveClientStateStatus.UNAVAILABLE else "state.unknown",
    )


def test_view_model_uses_canonical_navigation_and_existing_read_scopes() -> None:
    result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=2)),
        surface_id=_SURFACE,
        observed_at=_NOW,
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(
            _state(ExecutiveReadScope.SYSTEM_HEALTH),
            _state(ExecutiveReadScope.CIBO_STATE),
            _state(ExecutiveReadScope.RISK),
        ),
    )

    assert isinstance(result, Success)
    model = result.value
    assert tuple(item.section for item in model.sections) == (
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
    section_by_name = {item.section: item for item in model.sections}
    assert section_by_name[ExecutiveCommandCenterSection.SYSTEM].read_scope is ExecutiveReadScope.SYSTEM_HEALTH
    assert section_by_name[ExecutiveCommandCenterSection.CIBO].read_scope is ExecutiveReadScope.CIBO_STATE
    assert section_by_name[ExecutiveCommandCenterSection.RISK].read_scope is ExecutiveReadScope.RISK
    assert section_by_name[ExecutiveCommandCenterSection.NEWS].state is ExecutiveCommandCenterSectionState.UNSUPPORTED
    assert section_by_name[ExecutiveCommandCenterSection.NEWS].read_scope is None
    assert model.logical_values() == model.logical_values()


def test_missing_scope_is_explicit_and_never_assumed_current() -> None:
    result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=3)),
        surface_id=_SURFACE,
        observed_at=_NOW,
        selected_section=ExecutiveCommandCenterSection.MARKETS,
        state_views=(),
    )

    assert isinstance(result, Success)
    markets = next(
        item
        for item in result.value.sections
        if item.section is ExecutiveCommandCenterSection.MARKETS
    )
    assert markets.state is ExecutiveCommandCenterSectionState.MISSING
    assert markets.client_state is None
    assert markets.reason_code == "state.missing"


def test_duplicate_scope_fails_closed() -> None:
    state = _state(ExecutiveReadScope.AUDIT)
    result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=4)),
        surface_id=_SURFACE,
        observed_at=_NOW,
        selected_section=ExecutiveCommandCenterSection.AUDIT,
        state_views=(state, state),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveCommandCenterViewModelValidationError)


def test_ceo_accounts_and_profit_vault_remain_separate_sections_and_scopes() -> None:
    result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=5)),
        surface_id=_SURFACE,
        observed_at=_NOW,
        selected_section=ExecutiveCommandCenterSection.CEO_ACCOUNTS,
        state_views=(
            _state(ExecutiveReadScope.CEO_ACCOUNTS),
            _state(ExecutiveReadScope.CORPORATE_PROFIT_VAULT),
        ),
    )

    assert isinstance(result, Success)
    section_by_name = {item.section: item for item in result.value.sections}
    accounts = section_by_name[ExecutiveCommandCenterSection.CEO_ACCOUNTS]
    vault = section_by_name[ExecutiveCommandCenterSection.CORPORATE_PROFIT_VAULT]
    assert accounts.read_scope is ExecutiveReadScope.CEO_ACCOUNTS
    assert vault.read_scope is ExecutiveReadScope.CORPORATE_PROFIT_VAULT
    assert accounts.client_state is not vault.client_state


def test_widget_must_belong_to_same_surface_and_not_postdate_view_model() -> None:
    widget_result = build_cibo_widget_state(
        state_id=CiboWidgetStateId(UUID(int=6)),
        surface_id=_SURFACE,
        mode=CiboWidgetMode.AMBIENT,
        observed_at=_NOW,
    )
    assert isinstance(widget_result, Success)

    valid = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=7)),
        surface_id=_SURFACE,
        observed_at=_NOW,
        selected_section=ExecutiveCommandCenterSection.CIBO,
        state_views=(),
        cibo_widget=widget_result.value,
    )
    assert isinstance(valid, Success)

    mismatched_widget = replace(
        widget_result.value,
        surface_id=ExecutiveClientSurfaceId(UUID(int=8)),
    )
    mismatch = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=9)),
        surface_id=_SURFACE,
        observed_at=_NOW,
        selected_section=ExecutiveCommandCenterSection.CIBO,
        state_views=(),
        cibo_widget=mismatched_widget,
    )
    assert isinstance(mismatch, Failure)

    later_widget = replace(widget_result.value, observed_at=_NOW + timedelta(seconds=1))
    chronology = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=10)),
        surface_id=_SURFACE,
        observed_at=_NOW,
        selected_section=ExecutiveCommandCenterSection.CIBO,
        state_views=(),
        cibo_widget=later_widget,
    )
    assert isinstance(chronology, Failure)


def test_view_model_is_presentation_only_and_has_no_execution_surface() -> None:
    result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=11)),
        surface_id=_SURFACE,
        observed_at=_NOW,
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(_state(ExecutiveReadScope.GOVERNANCE),),
    )
    assert isinstance(result, Success)
    model = result.value

    assert not hasattr(model, "submit_order")
    assert not hasattr(model, "buy")
    assert not hasattr(model, "sell")
    assert not hasattr(model, "bypass_risk")
    assert not hasattr(model, "android_view")
    assert not hasattr(model, "ios_view")
    assert not hasattr(model, "desktop_window")
