from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v4_execution_authorization import (
    AUTHORIZATION_RELATIVE_PATH,
    build_phase22_v4_execution_authorization,
)
from qore.infrastructure.cibo_phase22_v4_execution_manifest import (
    build_phase22_v4_execution_manifest,
)
from qore.infrastructure.cibo_phase22_v4_one_shot_claim import (
    build_phase22_v4_one_shot_claim_receipt,
)
from qore.infrastructure.cibo_phase22_v4_store_contract import (
    PHASE22_V4_STORE_IDENTITIES,
    PHASE22_V4_STORE_ROOT_NAME,
    assert_phase22_v4_store_pristine,
)
from qore.infrastructure.cibo_phase22_v4_vt31_abi import (
    adapt_v4_vt31_market_evidence,
    v4_vt31_source_abi_sha256,
)


class _FakeVt31Source:
    series = (object(),)
    fingerprint = "sha256:" + "a" * 64
    last_closed_at = datetime(2015, 4, 19, tzinfo=UTC)
    corpus_git_sha = "b" * 40
    provider_symbol = "USTEC"


def test_v4_execution_manifest_is_exact_7_7_and_nonexecuting() -> None:
    manifest = build_phase22_v4_execution_manifest()

    assert manifest.candidate_id == (
        "CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4"
    )
    assert tuple(item.trader_id for item in manifest.trader_bindings) == (
        CANONICAL_PHASE22_TRADER_IDS
    )
    assert manifest.vt31_source_abi_sha256 == v4_vt31_source_abi_sha256()
    assert manifest.fresh_outcomes_executed is False
    assert manifest.broker_mutation_authorized is False
    assert manifest.live_authorized is False
    assert manifest.real_capital_authorized is False
    assert manifest.production_authorized is False
    assert manifest.merge_authorized is False
    assert manifest.productive_authority is False
    assert manifest.fingerprint().startswith("sha256:")


def test_v4_vt31_abi_is_exact_six_fields() -> None:
    result = adapt_v4_vt31_market_evidence(_FakeVt31Source())

    assert len(result) == 6
    series, account, evidence, checked_at, collector_sha, provider = result
    assert series == _FakeVt31Source.series
    assert account == "PHASE22_V4_HISTORICAL_ACCOUNT_NOT_CLAIMED"
    assert evidence == _FakeVt31Source.fingerprint
    assert checked_at == _FakeVt31Source.last_closed_at
    assert collector_sha == _FakeVt31Source.corpus_git_sha
    assert provider == _FakeVt31Source.provider_symbol


def test_v4_store_namespace_is_pristine_and_disjoint(tmp_path: Path) -> None:
    root = tmp_path / PHASE22_V4_STORE_ROOT_NAME
    assert_phase22_v4_store_pristine(root)
    assert len(PHASE22_V4_STORE_IDENTITIES) == 5
    assert all(
        item.relative_path.startswith("phase22-v4-stores/")
        for item in PHASE22_V4_STORE_IDENTITIES
    )
    assert all(
        "phase22-v2-stores" not in item.relative_path
        and "phase22-v3-stores" not in item.relative_path
        for item in PHASE22_V4_STORE_IDENTITIES
    )
    with pytest.raises(CiboCapitalManagementError, match="V4 store root"):
        assert_phase22_v4_store_pristine(tmp_path / "phase22-v3-stores")


def test_v4_claim_is_bound_to_authorization_and_pristine_store(
    tmp_path: Path,
) -> None:
    authorization = build_phase22_v4_execution_authorization(
        owner_authorization_id="OWNER_PHASE22_V4_UNIT_TEST",
        authorized_parent_head_sha="a" * 40,
    )
    claim = build_phase22_v4_one_shot_claim_receipt(
        authorization=authorization,
        runner_git_sha="b" * 40,
        run_id=1,
        run_attempt=1,
        started_at=datetime(2026, 10, 2, tzinfo=UTC),
        store_root=tmp_path / PHASE22_V4_STORE_ROOT_NAME,
    )

    assert claim.trader_ids == CANONICAL_PHASE22_TRADER_IDS
    assert claim.second_execution_authorized is False
    assert claim.broker_mutation_authorized is False
    assert claim.live_authorized is False
    assert claim.real_capital_authorized is False
    assert claim.production_authorized is False
    assert claim.productive_authority is False


def test_v4_authorization_receipt_is_not_materialized_pre_owner_gate() -> None:
    assert not Path(AUTHORIZATION_RELATIVE_PATH).exists()
