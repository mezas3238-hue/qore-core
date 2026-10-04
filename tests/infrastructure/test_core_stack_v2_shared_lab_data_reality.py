from dataclasses import replace
from qore.infrastructure.core_stack_v2.shared_lab_data_reality import CanonicalIdentity, DataFailure, DataQualityThresholds, DegradationClass, ProviderDatum, ProviderProvenance, classify_resilience, compute_quality_metrics, fingerprint_datum, provider_disagreement, resolve_identity, validate_market_hours, validate_values


def _datum(sequence: int = 1, bid: float = 1.1, ask: float = 1.1002) -> ProviderDatum:
    identity = CanonicalIdentity("FX:EURUSD", "FX", "EUR", quote_currency="USD")
    provenance = ProviderProvenance("p1", "feed-A", "a" * 64, "decoder-v1", "map-v1")
    return ProviderDatum(datum_id=f"d{sequence}", provider_symbol="EUR/USD", provider="p1", sequence=sequence,
        observed_at_ns=sequence * 1_000, available_at_ns=sequence * 1_000 + 10, bid=bid, ask=ask,
        metadata_asset_class="FX", provenance=provenance, canonical_identity=identity, market_open=True, session_id="LONDON")


def test_alias_identity_is_economic_not_textual() -> None:
    identity = _datum().canonical_identity
    aliases = {"EURUSD": (identity,)}
    for symbol in ("EURUSD", "EUR/USD", "eur_usd"):
        resolved, failures = resolve_identity(symbol, aliases, "FX")
        assert resolved == identity and failures == ()


def test_ambiguous_and_wrong_class_fail_closed() -> None:
    identity = _datum().canonical_identity
    ambiguous = {"EURUSD": (identity, replace(identity, economic_id="FX:OTHER"))}
    _, failures = resolve_identity("EUR/USD", ambiguous, "FX")
    assert failures == (DataFailure.IDENTITY_AMBIGUOUS,)
    _, failures = resolve_identity("EUR/USD", {"EURUSD": (identity,)}, "INDEX")
    assert failures == (DataFailure.WRONG_ASSET_CLASS,)


def test_market_hours_and_values_are_not_timestamp_only() -> None:
    datum = _datum()
    ok, failures = validate_market_hours(datum, expected_open=True)
    assert ok and not failures
    ok, failures = validate_market_hours(datum, expected_open=False)
    assert not ok and DataFailure.UNEXPECTED_MARKET_OPEN in failures
    ok, failures = validate_values(replace(datum, bid=-1.0))
    assert not ok and DataFailure.INVALID_VALUE in failures


def test_quality_metrics_and_resilience_are_individual_not_pooled() -> None:
    data = (_datum(1), _datum(2), _datum(3))
    metrics = compute_quality_metrics(data, expected_observations=3, freshness_limit_ns=10_000, now_ns=3_100)
    assert metrics.passes(DataQualityThresholds())
    assert classify_resilience(1, 0, 0, 0.99) is DegradationClass.ABSTENTION_REQUIRED
    assert classify_resilience(2, 1, 2, 0.9) is DegradationClass.DEGRADED_BUT_USABLE


def test_provider_disagreement_is_detected_and_fingerprinted() -> None:
    left = _datum()
    right = replace(_datum(), provider="p2", provenance=ProviderProvenance("p2", "feed-B", "b" * 64, "decoder-v1", "map-v1"), bid=1.2)
    assert provider_disagreement(left, right, tolerance=0.001)
    assert len(fingerprint_datum(left)) == 64
