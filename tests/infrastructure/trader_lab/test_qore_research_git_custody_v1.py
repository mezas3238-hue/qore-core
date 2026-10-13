"""Adversarial unit tests: immutable Git evidence, no scientific promotion."""
from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from typing import Any
from unittest.mock import patch

from qore.infrastructure.trader_lab import qore_research_git_custody_v1 as g

_MODULE = "qore.infrastructure.trader_lab.qore_research_git_custody_v1"
_HEAD = "a" * 40
_HISTORICAL = b"NO EIA prereg H1_WTI and H1_NG"
_EMPTY = b'{"schema":"qore.research.prereg-drafts.v1","drafts":[]}'


def _good_git(*parts: str) -> bytes:
    if parts == ("rev-parse", "HEAD"):
        return (_HEAD + "\n").encode()
    if parts == ("status", "--porcelain", "--", g.DRAFT_PATH):
        return b""
    raise AssertionError("Unexpected git call")


def _good_blob(commit: str, path: str, expected: str) -> bytes:
    if commit == g.EIA_PREREG_COMMIT and path == g.EIA_PREREG_PATH:
        return _HISTORICAL
    if path == g.DRAFT_PATH:
        return _EMPTY
    raise AssertionError("Unexpected Git blob")


class TestGitCustody(unittest.TestCase):
    def _witness(self) -> dict[str, Any]:
        with (
            patch(f"{_MODULE}._git", side_effect=_good_git),
            patch(f"{_MODULE}._blob", side_effect=_good_blob),
            patch(f"{_MODULE}._ancestor") as ancestry,
        ):
            output = g.verify_readonly_git_custody(_HEAD)
            self.assertEqual(ancestry.call_count, 2)
        return output

    def test_valid_witness_is_readonly_and_deterministic(self) -> None:
        a = self._witness()
        b = self._witness()
        self.assertEqual(a, b)
        self.assertEqual(a["draft_count"], 0)
        self.assertTrue(a["historical_eia_prereg_is_ancestor"])
        self.assertTrue(a["draft_manifest_unchanged_since_baseline"])
        for flag in (
            "new_prereg_scientifically_frozen",
            "new_outcome_experiment_executed",
            "historical_outcome_retested",
            "first_publication_asof_certified", "source_license_verified",
            "can_open_holdout", "can_promote_trader",
        ):
            self.assertIs(a[flag], False)
        self.assertEqual(a["market_data_spend_usd"], 0)
        copy = {k: v for k, v in a.items() if k != "custody_receipt_sha256"}
        digest = hashlib.sha256(json.dumps(
            copy, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()).hexdigest()
        self.assertEqual(digest, a["custody_receipt_sha256"])

    def test_untrusted_head_rejected(self) -> None:
        for value in ("", "NOT_A_SHA", "A" * 40, "abc"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "INVALID_COMMIT_SHA"):
                    g.verify_readonly_git_custody(value)

    def test_actions_sha_different_from_checkout_rejected(self) -> None:
        with patch(f"{_MODULE}._git", return_value=("b" * 40).encode()):
            with self.assertRaisesRegex(ValueError, "GITHUB_SHA_HEAD_MISMATCH"):
                g.verify_readonly_git_custody(_HEAD)

    def test_original_eia_ancestry_required(self) -> None:
        with (
            patch(f"{_MODULE}._git", side_effect=_good_git),
            patch(f"{_MODULE}._ancestor", side_effect=ValueError("NOT_ANCESTOR")),
        ):
            with self.assertRaisesRegex(ValueError, "NOT_ANCESTOR"):
                g.verify_readonly_git_custody(_HEAD)

    def test_historical_prereg_exact_blob_required(self) -> None:
        with (
            patch(f"{_MODULE}._git", side_effect=_good_git),
            patch(f"{_MODULE}._ancestor"),
            patch(f"{_MODULE}._blob", side_effect=ValueError("BLOB_CHANGED")),
        ):
            with self.assertRaisesRegex(ValueError, "BLOB_CHANGED"):
                g.verify_readonly_git_custody(_HEAD)

    def test_old_prereg_text_fields_required(self) -> None:
        def bad_old(commit: str, path: str, expected: str) -> bytes:
            if path == g.EIA_PREREG_PATH:
                return b"unrelated text"
            return _EMPTY

        with (
            patch(f"{_MODULE}._git", side_effect=_good_git),
            patch(f"{_MODULE}._ancestor"),
            patch(f"{_MODULE}._blob", side_effect=bad_old),
        ):
            with self.assertRaisesRegex(ValueError, "EIA_PREREG_CONTENT_MISMATCH"):
                g.verify_readonly_git_custody(_HEAD)

    def test_modified_manifest_cannot_be_rebranded_as_empty(self) -> None:
        def altered(commit: str, path: str, expected: str) -> bytes:
            if path == g.EIA_PREREG_PATH:
                return _HISTORICAL
            if commit == _HEAD:
                return b'{"schema":"qore.research.prereg-drafts.v1","drafts":[{"fake":1}]}'
            return _EMPTY

        with (
            patch(f"{_MODULE}._git", side_effect=_good_git),
            patch(f"{_MODULE}._ancestor"),
            patch(f"{_MODULE}._blob", side_effect=altered),
        ):
            with self.assertRaisesRegex(ValueError, "MANIFEST_NONEMPTY_OR_CHANGED"):
                g.verify_readonly_git_custody(_HEAD)

    def test_dirty_worktree_not_an_attestation(self) -> None:
        def dirty(*parts: str) -> bytes:
            if parts == ("rev-parse", "HEAD"):
                return (_HEAD + "\n").encode()
            return b" M docs/research/QORE_RESEARCH_PREREG_DRAFTS_2026-10-13.json"

        with (
            patch(f"{_MODULE}._git", side_effect=dirty),
            patch(f"{_MODULE}._ancestor"),
            patch(f"{_MODULE}._blob", side_effect=_good_blob),
        ):
            with self.assertRaisesRegex(ValueError, "WORKTREE_MANIFEST_DIRTY"):
                g.verify_readonly_git_custody(_HEAD)

    def test_invalid_json_or_changed_empty_schema_fails_closed(self) -> None:
        for result in (
            b"not json",
            b'{"schema":"wrong","drafts":[]}',
            b'{"schema":"qore.research.prereg-drafts.v1","drafts":[1]}',
        ):
            def mocked(commit: str, path: str, expected: str) -> bytes:
                if path == g.EIA_PREREG_PATH:
                    return _HISTORICAL
                return result

            with self.subTest(result=result), (
                patch(f"{_MODULE}._git", side_effect=_good_git),
                patch(f"{_MODULE}._ancestor"),
                patch(f"{_MODULE}._blob", side_effect=mocked),
            ):
                with self.assertRaisesRegex(
                    ValueError, "MANIFEST_JSON_INVALID|MANIFEST_NONEMPTY_OR_CHANGED"
                ):
                    g.verify_readonly_git_custody(_HEAD)

    def test_missing_file_and_unavailable_git_fail_closed(self) -> None:
        with patch(f"{_MODULE}.subprocess.run", side_effect=FileNotFoundError()):
            with self.assertRaisesRegex(ValueError, "COMMAND_UNAVAILABLE"):
                g._git("rev-parse", "HEAD")
        with patch(f"{_MODULE}.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 12)):
            with self.assertRaisesRegex(ValueError, "ANCESTRY_UNAVAILABLE"):
                g._ancestor("a" * 40, "b" * 40)

    def test_git_blob_bytes_are_recomputed_from_object_content(self) -> None:
        fake = b"document with immutable Git object bytes"
        object_hash = hashlib.sha1(
            b"blob " + str(len(fake)).encode() + b"\x00" + fake
        ).hexdigest()
        with patch(f"{_MODULE}._git", side_effect=[
            (object_hash + "\n").encode(), fake,
        ]):
            self.assertEqual(g._blob("a" * 40, "docs/research/evidence.md", object_hash), fake)
        with patch(f"{_MODULE}._git", side_effect=[
            (object_hash + "\n").encode(), fake,
        ]):
            with self.assertRaisesRegex(ValueError, "HISTORICAL_BLOB_CHANGED"):
                g._blob("a" * 40, "docs/research/evidence.md", "0" * 40)


if __name__ == "__main__":
    unittest.main()
