from __future__ import annotations

from typing import cast

import pytest

from qore.infrastructure.trader_lab.story_forensics_review_panel import (
    ReviewRole,
    StoryForensicsReviewError,
    build_review_panel,
    build_trader_policy_candidate,
    reviewer_packet,
    seal_assessment,
    synthesize_subject,
)


def _story() -> dict[str, object]:
    episode = {
        "episode_id": "episode-001",
        "trader_code": "vt-09",
        "symbol": "EURUSD",
        "execution_period": "M15",
        "classification": "LOSS_AFTER_1R_OR_MORE",
        "outcome": "loss",
        "decision_time": {"signal_at": "2026-01-01T00:00:00+00:00"},
        "post_outcome": {"close_path_mfe_r": "1.20"},
        "chart": {
            "source_of_truth": "qore-retained-evidence",
            "frame_sequence": [
                {
                    "stage": "signal",
                    "visible_through": "2026-01-01T00:00:00+00:00",
                    "visible_through_unix": 1767225600,
                }
            ],
        },
        "trajectory": [],
    }
    return {
        "schema": "qore.trader_lab.first_cohort_story_forensics.v1",
        "research_only": True,
        "execution_authority": False,
        "forensics_fingerprint": "f" * 64,
        "story_families": {
            "winning_streaks": [],
            "losing_streaks": [
                {
                    "streak_id": "streak-001",
                    "outcome": "loss",
                    "length": 1,
                    "episode_ids": ["episode-001"],
                    "selection_reason": "most-recent",
                }
            ],
        },
        "episodes": [episode],
    }


def _subject(panel: dict[str, object], subject_id: str) -> dict[str, object]:
    subjects = cast(list[dict[str, object]], panel["subjects"])
    return next(row for row in subjects if row["subject_id"] == subject_id)


def _assessment(
    panel: dict[str, object],
    *,
    subject_id: str,
    role: ReviewRole,
    candidate: str | None = None,
    risk: str | None = None,
) -> dict[str, object]:
    subject = _subject(panel, subject_id)
    favorable = candidate or f"{role.value}: preserve selectivity and test a narrower filter"
    return {
        "subject_digest": subject["subject_digest"],
        "role": role.value,
        "favorable_candidate": favorable,
        "degradation_risks": [risk or f"{role.value}: over-filtering could remove valid edge"],
        "preserve": ["preserve frozen Trader identity and existing valid edge"],
        "evidence": ["episode reached favorable excursion before final stop"],
        "counterexample_or_falsifier": "fresh holdout shows lower expectancy or robustness",
        "scope": "preservation" if favorable == "NO_SAFE_IMPROVEMENT_FOUND" else "filter",
        "confidence": "medium",
        "fresh_holdout_required": True,
    }


def test_review_panel_covers_every_episode_and_selected_streak() -> None:
    panel = build_review_panel(_story())
    subjects = cast(list[dict[str, object]], panel["subjects"])

    assert {row["subject_id"] for row in subjects} == {"episode-001", "streak-001"}
    for subject in subjects:
        lanes = cast(dict[str, dict[str, object]], subject["review_lanes"])
        assert set(lanes) == {
            "harness",
            "expert",
            "work",
            "architect",
            "human_owner",
        }
        assert all(lane["status"] == "PENDING" for lane in lanes.values())
        assert subject["synthesis_status"] == "BLOCKED_PENDING_REVIEWS"


def test_machine_packet_is_independent_and_human_waits_for_machine_reviews() -> None:
    panel = build_review_panel(_story())
    packet = reviewer_packet(
        panel,
        subject_id="episode-001",
        role=ReviewRole.HARNESS,
    )

    assert packet["mode"] == "independent_first_pass"
    assert "sealed_machine_reviews" not in packet
    subject = cast(dict[str, object], packet["subject"])
    assert "review_lanes" not in subject

    with pytest.raises(
        StoryForensicsReviewError,
        match="human review is blocked",
    ):
        reviewer_packet(
            panel,
            subject_id="episode-001",
            role=ReviewRole.HUMAN_OWNER,
        )


def test_human_review_cannot_seal_before_machine_first_passes() -> None:
    panel = build_review_panel(_story())
    human = _assessment(
        panel,
        subject_id="episode-001",
        role=ReviewRole.HUMAN_OWNER,
    )

    with pytest.raises(
        StoryForensicsReviewError,
        match="human review cannot seal",
    ):
        seal_assessment(panel, subject_id="episode-001", assessment=human)


def test_all_five_reviews_retain_disagreement_without_activation_authority() -> None:
    panel = build_review_panel(_story())
    for role in (
        ReviewRole.HARNESS,
        ReviewRole.EXPERT,
        ReviewRole.WORK,
        ReviewRole.ARCHITECT,
    ):
        panel = seal_assessment(
            panel,
            subject_id="episode-001",
            assessment=_assessment(panel, subject_id="episode-001", role=role),
        )

    human_packet = reviewer_packet(
        panel,
        subject_id="episode-001",
        role=ReviewRole.HUMAN_OWNER,
    )
    sealed = cast(dict[str, object], human_packet["sealed_machine_reviews"])
    assert set(sealed) == {"harness", "expert", "work", "architect"}

    human = _assessment(
        panel,
        subject_id="episode-001",
        role=ReviewRole.HUMAN_OWNER,
        candidate="NO_SAFE_IMPROVEMENT_FOUND",
        risk="human_owner: changing lifecycle may destroy a valid loss distribution",
    )
    panel = seal_assessment(panel, subject_id="episode-001", assessment=human)
    synthesis = synthesize_subject(panel, subject_id="episode-001")

    assert synthesis["state"] == "RESEARCH_CANDIDATE_ONLY"
    assert synthesis["activation_authority"] is False
    assert synthesis["consensus_required"] is False
    assert synthesis["disagreement_retained"] is True
    assert synthesis["fresh_holdout_required"] is True
    favorable = cast(list[str], synthesis["favorable_candidates"])
    assert "NO_SAFE_IMPROVEMENT_FOUND" in favorable
    assert len(favorable) == 5


def test_no_safe_improvement_must_be_preservation_scope() -> None:
    panel = build_review_panel(_story())
    assessment = _assessment(
        panel,
        subject_id="episode-001",
        role=ReviewRole.HARNESS,
        candidate="NO_SAFE_IMPROVEMENT_FOUND",
    )
    assessment["scope"] = "lifecycle"

    with pytest.raises(
        StoryForensicsReviewError,
        match="must use preservation scope",
    ):
        seal_assessment(panel, subject_id="episode-001", assessment=assessment)


def test_trader_policy_stays_blocked_until_every_subject_has_five_reviews() -> None:
    panel = build_review_panel(_story())
    for role in (
        ReviewRole.HARNESS,
        ReviewRole.EXPERT,
        ReviewRole.WORK,
        ReviewRole.ARCHITECT,
    ):
        panel = seal_assessment(
            panel,
            subject_id="episode-001",
            assessment=_assessment(panel, subject_id="episode-001", role=role),
        )
    panel = seal_assessment(
        panel,
        subject_id="episode-001",
        assessment=_assessment(
            panel,
            subject_id="episode-001",
            role=ReviewRole.HUMAN_OWNER,
        ),
    )

    policy = build_trader_policy_candidate(panel)
    assert policy["state"] == "BLOCKED_PENDING_REVIEWS"
    assert policy["activation_authority"] is False
    assert policy["pending_subject_ids"] == ["streak-001"]
