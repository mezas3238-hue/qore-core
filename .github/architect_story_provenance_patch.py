from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one replacement in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


story_path = Path("src/qore/infrastructure/trader_lab/first_cohort_story_forensics.py")
old_read = '''def _read_json(path: Path, *, field_name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortStoryForensicsError(f"cannot read {field_name}") from error
    return _object(decoded, field_name=field_name)
'''
new_read = '''def _read_json(path: Path, *, field_name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortStoryForensicsError(f"cannot read {field_name}") from error
    return _object(decoded, field_name=field_name)


def _artifact_sha256(path: Path, *, field_name: str) -> str:
    """Bind the exact retained artifact bytes consumed by Story Forensics."""

    try:
        material = path.read_bytes()
    except OSError as error:
        raise FirstCohortStoryForensicsError(f"cannot hash {field_name}") from error
    return sha256(material).hexdigest()
'''
replace_once(story_path, old_read, new_read)

old_binding = '''    source_binding = {
        "symbol": symbol,
        "account_fingerprint": account_fingerprint,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "trader_code": trader_code,
        "config_fingerprint": config_fingerprint,
        "methodology_fingerprint": methodology_fingerprint,
        "execution_period": execution_period,
    }
'''
new_binding = '''    source_artifact_sha256 = {
        "market": _artifact_sha256(market_path, field_name="market evidence"),
        "backtest": _artifact_sha256(backtest_path, field_name="backtest evidence"),
        "characterization": _artifact_sha256(
            characterization_path,
            field_name="characterization evidence",
        ),
    }
    source_binding = {
        "symbol": symbol,
        "account_fingerprint": account_fingerprint,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "trader_code": trader_code,
        "config_fingerprint": config_fingerprint,
        "methodology_fingerprint": methodology_fingerprint,
        "execution_period": execution_period,
        "source_artifact_sha256": source_artifact_sha256,
    }
'''
replace_once(story_path, old_binding, new_binding)

visual_path = Path("src/qore/infrastructure/trader_lab/story_forensics_visual_package.py")
old_sha = '''def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
'''
new_sha = '''def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _story_payload_sha256(payload: dict[str, object]) -> str:
    """Digest the exact canonical Story payload rendered by this package."""

    try:
        material = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise StoryForensicsVisualPackageError(
            "story payload must be canonical JSON"
        ) from error
    return _sha256_text(material)
'''
replace_once(visual_path, old_sha, new_sha)

old_manifest = '''        "source_binding": payload.get("source_binding"),
        "forensics_fingerprint": payload.get("forensics_fingerprint"),
        "renderer": _RENDERER,
'''
new_manifest = '''        "source_binding": payload.get("source_binding"),
        "forensics_fingerprint": payload.get("forensics_fingerprint"),
        "story_payload_sha256": _story_payload_sha256(payload),
        "renderer": _RENDERER,
'''
replace_once(visual_path, old_manifest, new_manifest)

story_test = Path("tests/infrastructure/trader_lab/test_first_cohort_story_forensics.py")
text = story_test.read_text(encoding="utf-8")
name = "test_story_forensics_fingerprint_binds_exact_source_artifact_bytes"
if name in text:
    raise SystemExit("Story provenance regression already present")
text += '''\n\ndef test_story_forensics_fingerprint_binds_exact_source_artifact_bytes(\n    tmp_path: Path,\n) -> None:\n    market, backtest, characterization = _evidence(tmp_path)\n\n    first = run_story_forensics(market, backtest, characterization, "vt-01")\n    first_binding = cast(dict[str, object], first["source_binding"])\n    first_digests = cast(dict[str, object], first_binding["source_artifact_sha256"])\n    assert set(first_digests) == {"market", "backtest", "characterization"}\n    assert all(len(cast(str, value)) == 64 for value in first_digests.values())\n\n    original = characterization.read_text(encoding="utf-8")\n    assert "canonical-test-setup" in original\n    characterization.write_text(\n        original.replace("canonical-test-setup", "changed-test-setup", 1),\n        encoding="utf-8",\n    )\n    second = run_story_forensics(market, backtest, characterization, "vt-01")\n    second_binding = cast(dict[str, object], second["source_binding"])\n    second_digests = cast(dict[str, object], second_binding["source_artifact_sha256"])\n\n    assert first_digests["market"] == second_digests["market"]\n    assert first_digests["backtest"] == second_digests["backtest"]\n    assert first_digests["characterization"] != second_digests["characterization"]\n    assert first["forensics_fingerprint"] != second["forensics_fingerprint"]\n    second_episode = cast(dict[str, object], cast(list[object], second["episodes"])[0])\n    second_decision = cast(dict[str, object], second_episode["decision_time"])\n    assert second_decision["setup_reason"] == "changed-test-setup"\n'''
story_test.write_text(text, encoding="utf-8")

visual_test = Path("tests/infrastructure/trader_lab/test_story_forensics_visual_package.py")
text = visual_test.read_text(encoding="utf-8")
name = "test_visual_manifest_binds_exact_story_payload_content"
if name in text:
    raise SystemExit("visual provenance regression already present")
text += '''\n\ndef test_visual_manifest_binds_exact_story_payload_content(tmp_path: Path) -> None:\n    first_payload = _payload()\n    first_manifest = build_visual_package(first_payload, tmp_path / "first")\n\n    second_payload = _payload()\n    second_episodes = cast(list[object], second_payload["episodes"])\n    second_episode = cast(dict[str, object], second_episodes[0])\n    second_decision = cast(dict[str, object], second_episode["decision_time"])\n    second_decision["setup_reason"] = "different-evidence-bound-reason"\n    second_manifest = build_visual_package(second_payload, tmp_path / "second")\n\n    first_digest = cast(str, first_manifest["story_payload_sha256"])\n    second_digest = cast(str, second_manifest["story_payload_sha256"])\n    assert len(first_digest) == 64\n    assert len(second_digest) == 64\n    assert first_digest != second_digest\n'''
visual_test.write_text(text, encoding="utf-8")
