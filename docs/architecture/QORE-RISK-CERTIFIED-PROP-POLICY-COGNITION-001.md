# QORE-RISK-CERTIFIED-PROP-POLICY-COGNITION-001

## Status

**IMPLEMENTED CANDIDATE — NON-PRODUCTION / DRAFT / NO LIVE AUTHORITY**

Base:

```text
main @ c98d486a760056d9a71173c7041cf6f0c58bd9e9
```

Branch:

```text
agent/qore-risk-certified-prop-source-cognition-001
```

## Owner intent

Close the account/prop-firm cognition boundary so QORE Risk can reason from account rules while
consuming **only verified and certified provider-authoritative sources**.

The governing rule is:

```text
NO CERTIFIED SOURCE -> NO RISK POLICY
NO CURRENT CERTIFICATION -> NO NEW TRADING
NO EXACT FIRM/PROGRAM MATCH -> NO NEW TRADING
NO POLICY CONTENT BINDING -> NO NEW TRADING
```

This delivery does not authorize LIVE, Production, real capital, deployment or merge.

## Existing foundation retained

`QORE-ACCOUNT-PROP-POLICY-001` already models provider-neutral account facts:

- account kind and phase;
- account size;
- maximum drawdown;
- daily loss;
- STATIC / TRAILING drawdown semantics;
- client profit split;
- normalized trading/payout rules;
- effective and expiry time;
- firm/program references.

That foundation is not replaced.

The missing trust edge was that `AccountPolicyRegistrySnapshot` represented a normalized policy
but did not itself prove that the commercial/provider facts came from a verified certified source.

## New Risk trust boundary

`src/qore/infrastructure/certified_account_policy.py` adds a separate one-way boundary:

```text
PROVIDER-AUTHORITATIVE SOURCE
        |
        v
VERIFIED SOURCE OBSERVATION
        |
        v
SOURCE CERTIFICATE + CONTENT SHA-256
        |
        v
NORMALIZED ACCOUNT POLICY
        |
        v
POLICY SHA-256 + POLICY CERTIFICATION
        |
        v
CertifiedAccountPolicyRegistrySnapshot
        |
        v
resolve_for_risk(...)
        |
        v
QORE RISK COGNITION
```

Risk is expected to consume the certified registry, not raw provider text and not an uncertified
`AccountPropPolicySnapshot`.

## Allowed source authority classes

The contract accepts explicit provider-authoritative source classes only:

```text
OFFICIAL_PROVIDER_TERMS
OFFICIAL_PROVIDER_HELP_CENTER
OFFICIAL_PROVIDER_ACCOUNT_CONTRACT
OFFICIAL_PROVIDER_DASHBOARD
```

A source locator must be an absolute HTTPS URL and must not embed credentials or fragments.

The enum establishes authority class semantics only. It does not claim that a particular URL is
official. Official-source verification belongs to the certifier/adapter boundary and is recorded
by the certificate.

## Verifier trust root

A certificate is not trusted merely because it contains a verifier UUID.

`PolicyVerifierRegistrySnapshot` is the explicit trust anchor consumed by the Risk-facing
registry. Each `CertifiedPolicyVerifier` declares:

```text
verifier_ref
authorized_at
valid_until
may_certify_policies
allowed source-authority classes
revoked_at
```

At resolution time Risk rejects:

- unknown/self-declared verifier references;
- expired or revoked verifiers;
- a verifier that is not authorized to certify normalized policies;
- a source verifier acting outside its certified authority class.

Therefore:

```text
CERTIFICATE WITHOUT TRUSTED VERIFIER != CERTIFIED POLICY
```

## Source evidence

`CertifiedPolicySourceEvidence` contains:

```text
evidence_id
certificate_id
verifier_ref
authority
HTTPS locator
content_sha256
observed_at
certified_at
valid_until
firm_ref
program_ref
revoked_at
```

The evidence is immutable provenance. It contains no provider credential and performs no network
fetch.

A source is invalid for Risk when:

- evaluation predates certification;
- certification/evidence has expired;
- evidence has been revoked;
- source identity does not match the policy firm/program;
- required time/identity invariants are invalid.

## Policy content binding

`derive_account_policy_sha256(...)` hashes canonical `AccountPropPolicySnapshot.logical_values()`
using deterministic JSON encoding and SHA-256.

`CertifiedAccountPolicy` refuses a certificate when the supplied policy digest does not match the
actual normalized policy content.

Therefore a valid source certificate cannot be detached and silently attached to a changed
drawdown percentage, profit split, rule disposition, phase, account size or drawdown mode.

## Firm/program binding

For a PROP_FIRM account every supporting source must carry exactly the same:

```text
firm_ref
program_ref
```

as the normalized policy.

A FundedNext program source cannot certify an FTMO policy, and one program inside the same provider
cannot certify another program by accidental name similarity.

No provider identity is inferred from account name, server string, region or commercial marketing
text.

## Certification lifetime

A policy certification:

- cannot predate its supporting source certification;
- cannot outlive any supporting source evidence;
- must be current at Risk evaluation time;
- becomes unusable after source revocation.

Policy effective/expiry semantics from `AccountPropPolicySnapshot` remain independently mandatory.

## Risk-facing resolver

`CertifiedAccountPolicyRegistrySnapshot.resolve_for_risk(...)` requires:

```text
account_id
policy_ref
evaluated_at
```

Resolution succeeds only when:

1. the exact account/policy binding exists;
2. the policy source certification is current;
3. all supporting certified sources are current and not revoked;
4. firm/program identity matches;
5. the normalized account policy itself remains complete/effective under
   `AccountPolicyRegistrySnapshot.resolve_for_new_trading(...)`.

A success means **certified policy readiness for Risk cognition only**.

It does not grant:

- a Core Decision;
- position sizing;
- trading authority;
- execution authority;
- LIVE activation;
- provider login/API authority.

The existing invariant remains:

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

## Cognitive meaning

QORE Risk may reason from facts such as:

```text
MAX_DRAWDOWN = 6%
DRAWDOWN_MODE = TRAILING
DAILY_LOSS = ...
PROFIT_SPLIT = ...
NEWS_TRADING = ALLOW/PROHIBIT
EA_TRADING = ALLOW/PROHIBIT
PAYOUT_RULE = ...
```

only after those facts are represented in a normalized policy that passed this certified-source
boundary.

Risk cognition may then calculate account-specific operating room, internal buffers, heat,
portfolio constraints and mission budgets in later/authorized layers.

The cognition must never "guess" a prop rule from an LLM answer, search snippet, forum, affiliate
site, cached memory or unverified URL.

## Deliberately not implemented

This delivery does **not** implement:

- automatic web browsing/scraping by Risk;
- a FundedNext-specific adapter;
- an FTMO-specific adapter;
- auto-update from commercial pages;
- policy interpretation by an LLM;
- live balance/equity/DD calculation;
- mission target sizing;
- CIBO zig-zig authorization;
- order sizing/execution;
- VPS changes;
- LIVE/Production/real-capital changes.

Those consumers/adapters must sit outside this trust contract and may publish a policy only after
source verification/certification.

## Tests

`tests/infrastructure/test_certified_account_policy.py` proves:

- deterministic policy SHA-256 content binding;
- HTTPS-only source locators;
- source certification chronology;
- digest mismatch rejection;
- firm/program mismatch rejection;
- policy certification cannot outlive evidence;
- Risk resolves a current certified TRAILING policy;
- raw uncertified policies are rejected by the Risk registry;
- untrusted/self-declared verifier rejection;
- verifier source-authority scoping;
- source revocation fails closed;
- certification expiry fails closed;
- underlying UNKNOWN policy semantics still fail closed;
- wrong-account and missing-policy resolution fail closed.

## Acceptance target

This candidate is acceptable only if the exact PR HEAD passes the repository `quality` gate.

Even after green CI:

```text
NO MERGE WITHOUT OWNER ORDER
NO LIVE
NO PRODUCTION
NO REAL CAPITAL
```
