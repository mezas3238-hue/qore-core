"""W2 source-only pilot invariant checks; no real M5 or PnL needed."""
import pytest

from qore.research.alpha2_w2_volume_source_probe import classify_activity


@pytest.mark.parametrize(
    ("value", "label"),
    [
        (None, "NULL"),
        (0, "ZERO"),
        (1, "POSITIVE"),
        (4_000, "POSITIVE"),
        (-2, "NEGATIVE"),
        (3.0, "NON_INTEGER"),
        ("500", "NON_INTEGER"),
        (True, "NON_INTEGER"),
        ([], "NON_INTEGER"),
    ],
)
def test_provider_volume_categories_dont_fabricate_true_exchange_volume(value, label):
    assert classify_activity(value) == label
