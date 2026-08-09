from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.domain.events as domain_events
import qore.functional.decisions as decisions
import qore.infrastructure.adapter_configuration as adapter_configuration
import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.client_decision_security as decision_security
import qore.infrastructure.client_execution_agent as client_agent
import qore.infrastructure.order_intent as order_intent
import qore.infrastructure.secrets as secrets
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 7, 0, tzinfo=UTC)
_DECISION_AT = _NOW - timedelta(seconds=30)
_ISSUED_AT = _NOW - timedelta(seconds=20)
_EXPIRES_AT = _NOW + timedelta(minutes=4)


def _uuid(suffix: int) -> UUID:
    return UUID(f"34000000-0000-0000-0000-{suffix:012d}")


def _binding(
    *,
    account_suffix: int = 11,
    runtime_suffix: int = 12,
    entitlement_suffix: int = 13,
) -> client_accounts.ClientTradingAccountBinding:
    return client_accounts.ClientTradingAccountBinding(
        client_id=client_accounts.ClientId(_uuid(10)),
        account_id=client_accounts.TradingAccountId(_uuid(account_suffix)),
        account_kind=client_accounts.TradingAccountKind.PROP_FIRM,
        lifecycle_state=client_accounts.TradingAccountLifecycleState.ACTIVE,
        policy_ref=client_accounts.AccountPolicyReference(_uuid(14)),
        product_entitlement_ref=client_accounts.ProductEntitlementReference(
            _uuid(entitlement_suffix)
        ),
        runtime_ref=client_accounts.ExecutionRuntimeReference(_uuid(runtime_suffix)),
    )


def _core_decision(
    *,
    decision_suffix: int = 1,
    timestamp: datetime = _DECISION_AT,
    expires_at: datetime = _EXPIRES_AT,
) -> client_agent.CoreTradeDecision:
    functional = decisions.FunctionalDecision(
        decision_id=decisions.DecisionId(_uuid(decision_suffix)),
        timestamp=timestamp,
        decision_type=decisions.DecisionType("core.trade"),
        status=decisions.DecisionStatus.RESOLVED,
        priority=decisions.DecisionPriority.NORMAL,
        metadata=decisions.DecisionMetadata(
            correlation_id=domain_events.CorrelationId(_uuid(2)),
        ),
        reasons=(
            decisions.DecisionReason(
                code=decisions.DecisionReasonCode("strategy.approved"),
                summary="Canonical protected Core Decision fixture",
            ),
        ),
        outcome=decisions.DecisionOutcome.APPROVED,
    )
    return client_agent.CoreTradeDecision(
        decision=functional,
        instrument=order_intent.ExecutionInstrument("EUR_USD"),
        side=order_intent.OrderSide.BUY,
        order_type=order_intent.OrderType.MARKET,
        expires_at=expires_at,
    )


def _payload(
    *,
    ciphertext: bytes = b"opaque-ciphertext-v1",
    tag: bytes = b"authentication-tag-v1",
    signature: bytes = b"signature-v1",
) -> decision_security.ProtectedDecisionPayload:
    return decision_security.ProtectedDecisionPayload(
        ciphertext=ciphertext,
        authentication_tag=tag,
        signature=signature,
    )


def _envelope(
    binding: client_accounts.ClientTradingAccountBinding,
    decision: client_agent.CoreTradeDecision,
    *,
    envelope_suffix: int = 20,
    protocol: str = "qore.client-decision.v1",
    issued_at: datetime = _ISSUED_AT,
    expires_at: datetime | None = None,
    nonce: bytes = b"0123456789abcdef",
    key_suffix: int = 30,
    key_version: int = 1,
    payload: decision_security.ProtectedDecisionPayload | None = None,
    account_id: client_accounts.TradingAccountId | None = None,
    runtime_ref: client_accounts.ExecutionRuntimeReference | None = None,
    entitlement_ref: client_accounts.ProductEntitlementReference | None = None,
) -> decision_security.ClientDecisionEnvelope:
    return decision_security.ClientDecisionEnvelope(
        envelope_id=decision_security.ClientDecisionEnvelopeId(_uuid(envelope_suffix)),
        protocol_version=decision_security.DecisionProtocolVersion(protocol),
        protection_profile=decision_security.DecisionProtectionProfile.SIGNED_ENCRYPTED,
        decision_id=decision.decision.decision_id,
        account_id=account_id or binding.account_id,
        runtime_ref=runtime_ref or binding.runtime_ref,
        entitlement_ref=entitlement_ref or binding.product_entitlement_ref,
        issued_at=issued_at,
        expires_at=expires_at or decision.expires_at,
        nonce=decision_security.DecisionNonce(nonce),
        key_id=decision_security.DecisionKeyId(_uuid(key_suffix)),
        key_version=decision_security.DecisionKeyVersion(key_version),
        protected_payload=payload or _payload(),
    )


def _secret_ref(*, suffix: int = 40) -> secrets.SecretRef:
    return secrets.SecretRef(
        ref_id=secrets.SecretRefId(_uuid(suffix)),
        name=adapter_configuration.AdapterSecretName("qore-decision-verification-key"),
        external_reference=secrets.SecretExternalReference(
            "qore/client-decision/verification-key"
        ),
    )


def _key(
    envelope: decision_security.ClientDecisionEnvelope,
    *,
    status: decision_security.DecisionKeyStatus = decision_security.DecisionKeyStatus.ACTIVE,
    effective_at: datetime = _NOW - timedelta(days=1),
    expires_at: datetime | None = None,
) -> decision_security.DecisionKeySnapshot:
    return decision_security.DecisionKeySnapshot(
        key_id=envelope.key_id,
        version=envelope.key_version,
        status=status,
        material_ref=_secret_ref(),
        effective_at=effective_at,
        expires_at=expires_at,
    )


class FakeKeySource:
    def __init__(
        self,
        snapshot: decision_security.DecisionKeySnapshot,
        error: decision_security.ClientDecisionSecurityError | None = None,
    ) -> None:
        self.snapshot = snapshot
        self.error = error
        self.calls: list[
            tuple[
                decision_security.DecisionKeyId,
                decision_security.DecisionKeyVersion,
                datetime,
            ]
        ] = []

    def resolve(
        self,
        key_id: decision_security.DecisionKeyId,
        version: decision_security.DecisionKeyVersion,
        *,
        evaluated_at: datetime,
    ) -> result.Result[
        decision_security.DecisionKeySnapshot,
        decision_security.ClientDecisionSecurityError,
    ]:
        self.calls.append((key_id, version, evaluated_at))
        if self.error is not None:
            return result.Failure(self.error)
        return result.Success(self.snapshot)


class FakeCryptoVerifier:
    def __init__(
        self,
        decision: client_agent.CoreTradeDecision,
        *,
        error: decision_security.ClientDecisionSecurityError | None = None,
        digest_override: str | None = None,
    ) -> None:
        self.decision = decision
        self.error = error
        self.digest_override = digest_override
        self.calls: list[
            tuple[
                decision_security.ClientDecisionEnvelope,
                decision_security.DecisionKeySnapshot,
            ]
        ] = []

    def verify_and_decrypt(
        self,
        envelope: decision_security.ClientDecisionEnvelope,
        key: decision_security.DecisionKeySnapshot,
    ) -> result.Result[
        decision_security.DecisionCryptographicVerification,
        decision_security.ClientDecisionSecurityError,
    ]:
        self.calls.append((envelope, key))
        if self.error is not None:
            return result.Failure(self.error)
        digest = self.digest_override or decision_security.protected_payload_digest(
            envelope.protected_payload
        )
        return result.Success(
            decision_security.DecisionCryptographicVerification(
                decision=self.decision,
                protected_payload_digest=digest,
            )
        )


class FakeReplayPort:
    def __init__(
        self,
        status: decision_security.ClientDecisionReplayClaimStatus = (
            decision_security.ClientDecisionReplayClaimStatus.ACQUIRED
        ),
        *,
        error: decision_security.ClientDecisionSecurityError | None = None,
        bind_correctly: bool = True,
    ) -> None:
        self.status = status
        self.error = error
        self.bind_correctly = bind_correctly
        self.calls: list[
            tuple[decision_security.ClientDecisionReplayKey, str]
        ] = []

    def claim(
        self,
        key: decision_security.ClientDecisionReplayKey,
        fingerprint: str,
    ) -> result.Result[
        decision_security.ClientDecisionReplayClaim,
        decision_security.ClientDecisionSecurityError,
    ]:
        self.calls.append((key, fingerprint))
        if self.error is not None:
            return result.Failure(self.error)
        returned_fingerprint = fingerprint if self.bind_correctly else "0" * 64
        return result.Success(
            decision_security.ClientDecisionReplayClaim(
                key=key,
                fingerprint=returned_fingerprint,
                status=self.status,
            )
        )


def _verify(
    *,
    binding: client_accounts.ClientTradingAccountBinding | None = None,
    decision: client_agent.CoreTradeDecision | None = None,
    envelope: decision_security.ClientDecisionEnvelope | None = None,
    key: decision_security.DecisionKeySnapshot | None = None,
    key_source: FakeKeySource | None = None,
    crypto: FakeCryptoVerifier | None = None,
    replay: FakeReplayPort | None = None,
    evaluated_at: datetime = _NOW,
) -> tuple[
    result.Result[
        decision_security.VerifiedClientDecision,
        decision_security.ClientDecisionSecurityError,
    ],
    FakeKeySource,
    FakeCryptoVerifier,
    FakeReplayPort,
]:
    selected_binding = binding or _binding()
    selected_decision = decision or _core_decision()
    selected_envelope = envelope or _envelope(selected_binding, selected_decision)
    selected_key = key or _key(selected_envelope)
    selected_key_source = key_source or FakeKeySource(selected_key)
    selected_crypto = crypto or FakeCryptoVerifier(selected_decision)
    selected_replay = replay or FakeReplayPort()
    verified = decision_security.verify_client_decision_envelope(
        selected_envelope,
        selected_binding,
        selected_key_source,
        selected_crypto,
        selected_replay,
        evidence_ref=client_agent.DecisionSecurityEvidenceReference(_uuid(50)),
        evaluated_at=evaluated_at,
    )
    return verified, selected_key_source, selected_crypto, selected_replay


def test_external_envelope_contains_only_protected_trading_payload() -> None:
    binding = _binding()
    decision = _core_decision()
    payload = _payload(ciphertext=b"BUY EURUSD plaintext must not appear")
    envelope = _envelope(binding, decision, payload=payload)

    assert envelope.protection_profile is (
        decision_security.DecisionProtectionProfile.SIGNED_ENCRYPTED
    )
    assert not hasattr(envelope, "instrument")
    assert not hasattr(envelope, "side")
    assert not hasattr(envelope, "order_type")
    assert not hasattr(envelope, "quantity")
    assert not hasattr(envelope, "stop_loss")
    assert not hasattr(envelope, "take_profit")
    assert "BUY EURUSD" not in repr(payload)
    assert "opaque" not in repr(payload)


def test_protected_payload_logical_values_and_replay_fingerprint_are_secret_free() -> None:
    binding = _binding()
    decision = _core_decision()
    payload = _payload(ciphertext=b"sensitive-protected-bytes")
    envelope = _envelope(binding, decision, payload=payload)

    logical = str(payload.logical_values())
    fingerprint = decision_security.client_decision_replay_fingerprint(envelope)

    assert "sensitive-protected-bytes" not in logical
    assert len(fingerprint) == 64
    assert "sensitive-protected-bytes" not in fingerprint
    assert fingerprint == decision_security.client_decision_replay_fingerprint(envelope)


def test_fingerprint_changes_for_nonce_or_protected_payload_changes() -> None:
    binding = _binding()
    decision = _core_decision()
    first = _envelope(binding, decision)
    changed_nonce = _envelope(
        binding,
        decision,
        nonce=b"fedcba9876543210",
    )
    changed_payload = _envelope(
        binding,
        decision,
        payload=_payload(ciphertext=b"different-ciphertext"),
    )

    assert decision_security.client_decision_replay_fingerprint(first) != (
        decision_security.client_decision_replay_fingerprint(changed_nonce)
    )
    assert decision_security.client_decision_replay_fingerprint(first) != (
        decision_security.client_decision_replay_fingerprint(changed_payload)
    )


def test_happy_path_returns_verified_attestation_for_exact_account_runtime() -> None:
    verified, key_source, crypto, replay = _verify()

    assert isinstance(verified, result.Success)
    value = verified.value
    assert value.attestation.status is client_agent.DecisionSecurityStatus.VERIFIED
    assert value.attestation.account_id == client_accounts.TradingAccountId(_uuid(11))
    assert value.attestation.runtime_ref == client_accounts.ExecutionRuntimeReference(
        _uuid(12)
    )
    assert value.decision.decision.decision_id == decisions.DecisionId(_uuid(1))
    assert len(key_source.calls) == 1
    assert len(crypto.calls) == 1
    assert len(replay.calls) == 1


def test_wrong_account_runtime_or_entitlement_rejects_before_key_or_crypto() -> None:
    binding = _binding()
    decision = _core_decision()
    wrong_account = _envelope(
        binding,
        decision,
        account_id=client_accounts.TradingAccountId(_uuid(999)),
    )
    wrong_runtime = _envelope(
        binding,
        decision,
        runtime_ref=client_accounts.ExecutionRuntimeReference(_uuid(998)),
    )
    wrong_entitlement = _envelope(
        binding,
        decision,
        entitlement_ref=client_accounts.ProductEntitlementReference(_uuid(997)),
    )

    for envelope in (wrong_account, wrong_runtime, wrong_entitlement):
        verified, key_source, crypto, replay = _verify(
            binding=binding,
            decision=decision,
            envelope=envelope,
        )
        assert isinstance(verified, result.Failure)
        assert str(verified.error) == (
            "decision envelope account/runtime/entitlement binding mismatch"
        )
        assert key_source.calls == []
        assert crypto.calls == []
        assert replay.calls == []


def test_expired_or_future_envelope_rejects_before_key_resolution() -> None:
    binding = _binding()
    decision = _core_decision()
    expired = _envelope(
        binding,
        decision,
        issued_at=_NOW - timedelta(minutes=2),
        expires_at=_NOW,
    )
    future = _envelope(
        binding,
        decision,
        issued_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(minutes=2),
    )

    expired_result, expired_keys, expired_crypto, expired_replay = _verify(
        binding=binding,
        decision=decision,
        envelope=expired,
    )
    future_result, future_keys, future_crypto, future_replay = _verify(
        binding=binding,
        decision=decision,
        envelope=future,
    )

    assert isinstance(expired_result, result.Failure)
    assert str(expired_result.error) == "decision envelope is expired"
    assert expired_keys.calls == []
    assert expired_crypto.calls == []
    assert expired_replay.calls == []
    assert isinstance(future_result, result.Failure)
    assert str(future_result.error) == "decision envelope issued_at is in the future"
    assert future_keys.calls == []
    assert future_crypto.calls == []
    assert future_replay.calls == []


def test_unsupported_protocol_fails_closed_without_crypto() -> None:
    binding = _binding()
    decision = _core_decision()
    envelope = _envelope(binding, decision, protocol="qore.client-decision.v2")

    verified, key_source, crypto, replay = _verify(
        binding=binding,
        decision=decision,
        envelope=envelope,
    )

    assert isinstance(verified, result.Failure)
    assert str(verified.error) == "unsupported decision protocol version"
    assert key_source.calls == []
    assert crypto.calls == []
    assert replay.calls == []


def test_revoked_or_unknown_key_rejects_without_crypto_or_replay() -> None:
    binding = _binding()
    decision = _core_decision()
    envelope = _envelope(binding, decision)

    for status in (
        decision_security.DecisionKeyStatus.REVOKED,
        decision_security.DecisionKeyStatus.UNKNOWN,
    ):
        selected_key = _key(envelope, status=status)
        verified, key_source, crypto, replay = _verify(
            binding=binding,
            decision=decision,
            envelope=envelope,
            key=selected_key,
        )
        assert isinstance(verified, result.Failure)
        assert str(verified.error) == "decision key is not authorized for verification"
        assert len(key_source.calls) == 1
        assert crypto.calls == []
        assert replay.calls == []


def test_verify_only_key_supports_rotation_of_already_issued_envelopes() -> None:
    binding = _binding()
    decision = _core_decision()
    envelope = _envelope(binding, decision, key_version=7)
    rotated = _key(envelope, status=decision_security.DecisionKeyStatus.VERIFY_ONLY)

    verified, key_source, crypto, replay = _verify(
        binding=binding,
        decision=decision,
        envelope=envelope,
        key=rotated,
    )

    assert isinstance(verified, result.Success)
    assert key_source.calls[0][1] == decision_security.DecisionKeyVersion(7)
    assert len(crypto.calls) == 1
    assert len(replay.calls) == 1


def test_key_material_is_only_an_opaque_secret_reference() -> None:
    binding = _binding()
    decision = _core_decision()
    envelope = _envelope(binding, decision)
    key = _key(envelope)

    assert isinstance(key.material_ref, secrets.SecretRef)
    assert not hasattr(key, "private_key")
    assert not hasattr(key, "secret_value")
    assert not hasattr(key, "key_bytes")
    assert "verification-key" in repr(key.material_ref)


def test_crypto_failure_or_modified_payload_never_claims_replay() -> None:
    binding = _binding()
    decision = _core_decision()
    envelope = _envelope(binding, decision)
    crypto_error = decision_security.ClientDecisionSecurityVerificationError(
        "signature verification failed"
    )
    failing_crypto = FakeCryptoVerifier(decision, error=crypto_error)

    failed, _, _, failed_replay = _verify(
        binding=binding,
        decision=decision,
        envelope=envelope,
        crypto=failing_crypto,
    )
    bad_digest_crypto = FakeCryptoVerifier(decision, digest_override="0" * 64)
    modified, _, _, modified_replay = _verify(
        binding=binding,
        decision=decision,
        envelope=envelope,
        crypto=bad_digest_crypto,
    )

    assert isinstance(failed, result.Failure)
    assert str(failed.error) == "signature verification failed"
    assert failed_replay.calls == []
    assert isinstance(modified, result.Failure)
    assert str(modified.error) == "cryptographic protected-payload digest mismatch"
    assert modified_replay.calls == []


def test_decrypted_decision_identity_or_expiry_mismatch_never_claims_replay() -> None:
    binding = _binding()
    decision = _core_decision()
    envelope = _envelope(binding, decision)
    wrong_id = _core_decision(decision_suffix=777)
    wrong_expiry = _core_decision(expires_at=_EXPIRES_AT + timedelta(seconds=1))

    id_result, _, _, id_replay = _verify(
        binding=binding,
        decision=decision,
        envelope=envelope,
        crypto=FakeCryptoVerifier(wrong_id),
    )
    expiry_result, _, _, expiry_replay = _verify(
        binding=binding,
        decision=decision,
        envelope=envelope,
        crypto=FakeCryptoVerifier(wrong_expiry),
    )

    assert isinstance(id_result, result.Failure)
    assert str(id_result.error) == "decrypted Core Decision identity mismatch"
    assert id_replay.calls == []
    assert isinstance(expiry_result, result.Failure)
    assert str(expiry_result.error) == "decrypted Core Decision expiry mismatch"
    assert expiry_replay.calls == []


def test_duplicate_and_conflicting_replay_are_both_fail_closed() -> None:
    for status, expected_message in (
        (
            decision_security.ClientDecisionReplayClaimStatus.DUPLICATE,
            "decision replay duplicate rejected",
        ),
        (
            decision_security.ClientDecisionReplayClaimStatus.CONFLICT,
            "decision replay conflict rejected",
        ),
    ):
        replay = FakeReplayPort(status)
        verified, _, crypto, selected_replay = _verify(replay=replay)

        assert isinstance(verified, result.Failure)
        assert str(verified.error) == expected_message
        assert len(crypto.calls) == 1
        assert len(selected_replay.calls) == 1


def test_replay_claim_is_exactly_once_and_never_released_or_retried() -> None:
    replay = FakeReplayPort()

    verified, _, _, selected_replay = _verify(replay=replay)

    assert isinstance(verified, result.Success)
    assert len(selected_replay.calls) == 1
    assert not hasattr(selected_replay, "release")
    assert not hasattr(selected_replay, "retry")


def test_same_core_decision_can_fan_out_to_independent_account_replay_keys() -> None:
    decision = _core_decision()
    first_binding = _binding(account_suffix=11, runtime_suffix=12, entitlement_suffix=13)
    second_binding = _binding(
        account_suffix=111,
        runtime_suffix=112,
        entitlement_suffix=113,
    )
    first_envelope = _envelope(first_binding, decision, envelope_suffix=120)
    second_envelope = _envelope(second_binding, decision, envelope_suffix=121)

    first, _, _, first_replay = _verify(
        binding=first_binding,
        decision=decision,
        envelope=first_envelope,
    )
    second, _, _, second_replay = _verify(
        binding=second_binding,
        decision=decision,
        envelope=second_envelope,
    )

    assert isinstance(first, result.Success)
    assert isinstance(second, result.Success)
    assert first_replay.calls[0][0].decision_id == second_replay.calls[0][0].decision_id
    assert first_replay.calls[0][0].account_id != second_replay.calls[0][0].account_id


def test_stolen_account_a_envelope_cannot_authorize_account_b() -> None:
    decision = _core_decision()
    account_a = _binding(account_suffix=11, runtime_suffix=12, entitlement_suffix=13)
    account_b = _binding(
        account_suffix=211,
        runtime_suffix=212,
        entitlement_suffix=213,
    )
    stolen = _envelope(account_a, decision)

    verified, keys, crypto, replay = _verify(
        binding=account_b,
        decision=decision,
        envelope=stolen,
    )

    assert isinstance(verified, result.Failure)
    assert str(verified.error) == (
        "decision envelope account/runtime/entitlement binding mismatch"
    )
    assert keys.calls == []
    assert crypto.calls == []
    assert replay.calls == []


def test_security_orchestrator_does_not_expose_broker_or_execution_methods() -> None:
    assert not hasattr(decision_security.ClientDecisionEnvelope, "submit_order")
    assert not hasattr(decision_security.VerifiedClientDecision, "execute")
    assert not hasattr(decision_security.DecisionCryptoVerifier, "broker")
    assert not hasattr(decision_security.ClientDecisionReplayClaimPort, "redispatch")
