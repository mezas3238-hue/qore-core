"""Sanitized, deterministic FundedNext MT5 account identity fingerprints."""

from __future__ import annotations

import hashlib


def fundednext_mt5_account_fingerprint(
    *,
    login: int,
    server: str,
    company: str,
    currency: str,
    leverage: int,
) -> str:
    """Return a non-reversible identity digest without persisting the MT5 login.

    The login participates in the digest so two FundedNext accounts with otherwise
    identical broker metadata cannot share an identity fingerprint.
    """

    if not isinstance(login, int) or isinstance(login, bool) or login <= 0:
        raise ValueError("MT5 login must be a positive integer")
    if not isinstance(leverage, int) or isinstance(leverage, bool) or leverage <= 0:
        raise ValueError("MT5 leverage must be a positive integer")
    values = (server, company, currency)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("MT5 server, company and currency must be non-empty")
    identity_material = "|".join(
        (
            str(login),
            server.strip(),
            company.strip(),
            currency.strip().upper(),
            str(leverage),
        )
    )
    return hashlib.sha256(identity_material.encode("utf-8")).hexdigest()
