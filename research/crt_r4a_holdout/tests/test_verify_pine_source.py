"""Source fingerprint guards use synthetic bytes; actual Pine checked in CI."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from research.crt_r4a_holdout.verify_pine_source import (
    EXPECTED_BLOB,
    git_blob_sha,
    inspect,
)


class ImmutablePinTests(unittest.TestCase):
    def test_01_correct_git_blob_encoding(self) -> None:
        b = b"hello\n"
        digest = hashlib.sha1(b"blob 6\0hello\n").hexdigest()
        self.assertEqual(git_blob_sha(b), digest)

    def test_02_blank_file_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "file.pine"
            p.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "PIN MISMATCH"):
                inspect(p)

    def test_03_fake_r4a_source_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "file.pine"
            p.write_text("// R4-A\nf_engine() =>\n  1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PIN MISMATCH"):
                inspect(p)

    def test_04_expected_pin_exact(self) -> None:
        self.assertEqual(
            EXPECTED_BLOB, "693e3f49719e86e2ea0702f7b355af33bd0c4c7c"
        )

    def test_05_substituting_r5_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "wrong.pine"
            p.write_bytes(b"// QORE R5 QA other source\n")
            with self.assertRaisesRegex(ValueError, "PIN MISMATCH"):
                inspect(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
