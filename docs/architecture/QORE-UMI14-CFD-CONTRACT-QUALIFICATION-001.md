# QORE-UMI14-CFD-CONTRACT-QUALIFICATION-001

## 1. STATUS

PROGRAM D / UMI-14 — UNR-015 FULL-CLOSURE CANDIDATE

Tracker: #398  
PR: #399  
Family: `contracts-for-difference`

This document describes the current integration candidate. Certification still
requires an exact frozen SHA, post-freeze full CI, serial independent review and
protected expected-head merge.

## 2. CURRENT CERTIFIED PREDECESSOR BASELINE

The candidate is synchronized after UNR-014 integration to certified `main`:

`59767ac2fccd1ee6db0a199800e55d6e0c6f0ba2`

The previous preparatory CFD candidate was built on an earlier snapshot and is
historical only. No earlier CI/reviewer result certifies the current candidate.

## 3. AUTHORIZED D04 MISSION

UNR-015 does **not** create one universal standalone CFD economic owner.
It composes already certified static authority and adds only bounded CFD
qualification where the tracker proved material residual semantics:

1. CFD family/economic-form qualification over UMI-02 + UMI-05;
2. explicit price-determination reference binding for a bounded cash-settled
   forward-form CFD when the economic and fixing references differ;
3. bounded rolling-spot lifecycle qualification retaining:
   - the certified FX quoted-pair / quotation-direction reference;
   - contract period;
   - automatic contract rollover;
   - party termination capability.

`CFD QUALIFICATION != NEW UNIVERSAL CFD ECONOMIC IDENTITY`

## 4. CERTIFIED AUTHORITY REUSE

- UMI-02: `EconomicIdentity`, `EconomicIdentityId`, family classification and
  `IdentityRelationship`.
- UMI-05: `ForwardContractTerms`, price strike, fixing and CASH settlement.
- Certified FX lane: `FxQuotedCurrencyPair` + `FxQuoteBasis` for the rolling-spot
  reference. UNR-015 does not duplicate FX pair or quotation-direction authority.
- D06-owned calendar semantics may remain referenced by an existing UMI-05
  settlement convention, but this owner generates no dates.

## 5. FORWARD-FORM CFD QUALIFICATION

`CfdForwardFormQualification` requires:

- exact CFD `EconomicIdentity` with family `contracts-for-difference` and
  `TRADABLE_INSTRUMENT` kind;
- identity ID equal to the reused UMI-05 forward instrument identity;
- exact `ForwardContractTerms`;
- CASH settlement;
- PRICE strike semantics;
- explicit fixing terms;
- exact finite positive notional state and exact nested identity wrappers;
- all retained nested UMI-05 material revalidated before logical projection.

When the forward economic reference and fixing reference are identical, no
extra relationship is needed and a redundant relationship is rejected.

When they differ, an exact `IdentityRelationship` is mandatory:

- source = forward economic reference;
- target = fixing reference;
- relationship code = `price-determination-reference`;
- explicit effective interval retained as UMI-02 static relationship material;
- no ordinal precedence on this single binding.

## 6. NO INVENTED FIXING-DAY TIME LAW

The earlier preparatory candidate required the relationship to cover the entire
UTC civil fixing date. That rule is removed.

A UMI-05 fixing carries an exact `date`, not an intraday fixing instant. UNR-015
therefore cannot prove or execute a universal UTC-day coverage rule without
inventing timing authority. Relationship effective dates are retained and
revalidated, but this D04 owner does not evaluate whether a runtime/intraday
fixing instant lies inside them.

`STATIC RELATIONSHIP != D06 FIXING-TIME EVALUATION`

## 7. ROLLING-SPOT CFD QUALIFICATION

`CfdRollingSpotLifecycleQualification` retains exactly:

- CFD qualification ID;
- CFD economic identity;
- certified `FxQuotedCurrencyPair` as the spot/quotation reference;
- exact positive `FinancialTenor` contract period;
- type-encoded `automatic-contract-rollover` semantic;
- type-encoded `party-termination-capability` semantic;
- evidence reference.

The CFD identity must not collapse into the FX quoted-pair identity.

The value stores no current spot price, observed fixing, generated roll date,
roll scheduler, order, margin state or settlement mutation.

## 8. WHY THE FX REFERENCE IS NOW PRESENT

The preparatory CFD branch predated certification of the FX lane and therefore
could only state that future rolling-spot composition must reuse certified FX
pair/quotation semantics later.

That predecessor is now integrated. The current UNR-015 candidate therefore
performs the required sequential composition and binds the rolling-spot
qualification to `FxQuotedCurrencyPair` rather than inventing a second FX model.

## 9. EXACT-TYPE / MALFORMED-STATE LAW

The local owner hardens reused older contracts at the composition boundary:

- exact local wrappers and exact UUIDs;
- exact `EconomicIdentityId` plus exact nested UUID;
- exact family/kind/construction/evidence types;
- exact UMI-05 forward/notional/strike/fixing/reference/evidence types;
- exact finite `Decimal` where retained;
- exact dates (not `datetime`);
- exact settlement-convention children when supplied;
- exact UMI-02 relationship IDs/codes/timestamps/evidence;
- exact FX pair IDs, quote basis and evidence;
- exact positive `FinancialTenor` and unit.

Every local `logical_values()` re-runs validation. Parent projections therefore
fail closed against `object.__setattr__` corruption of nested retained state.
Partially fabricated objects with missing required slots fail before trust and
cannot become valid logical identity.

## 10. LOGICAL IDENTITY

Forward-form identity contains:

- qualification ID;
- full CFD economic identity projection;
- full reused forward projection;
- price-determination relationship projection when required;
- evidence reference.

Rolling-spot identity contains:

- qualification ID;
- full CFD economic identity projection;
- full certified FX quoted-pair projection, including quotation direction;
- contract period;
- automatic-rollover marker;
- party-termination marker;
- evidence reference.

Material reference/binding/period dimensions must not collapse. No caller-order
collection exists in this bounded owner.

## 11. NEGATIVE SPACE / OWNER MAP

This module owns no:

- current market observation or resolved state (D05);
- clock, calendar generation or intraday fixing evaluation (D06);
- payoff, PnL, probability or valuation (D07);
- account, position, leverage or margin state (D08/D09);
- order, close-out or execution (D10);
- settlement/cash mutation (D11);
- legal/regulatory/spread-bet determination (D22);
- provider/network capability;
- Production or real-capital authority.

No universal CFD financing convention is claimed.
No complete total-return-swap CFD owner is claimed.

## 12. DETERMINISM / SECURITY

- local values are `dataclass(frozen=True, slots=True)`;
- no implicit wall clock;
- no random UUID generation;
- no mutable dataclass singleton used as a module constant;
- no filesystem/network/provider access;
- no retry/scheduler/thread/subprocess authority;
- no secrets or productive credentials;
- deterministic logical projection from retained static state.

## 13. TEST / FALSIFICATION OBLIGATIONS

The owner tests must falsify at least:

- same vs distinct fixing-reference binding;
- wrong binding endpoints/code/ordinal;
- absence of the old invented complete-UTC-day law;
- non-PRICE / non-CASH forward-form rejection;
- exact wrappers, subclasses and nested UUID/Decimal/date corruption;
- post-construction corruption during `logical_values()`;
- FX spot-reference pair/quotation non-collapse;
- CFD identity vs FX pair identity non-conflation;
- contract-period non-collapse;
- negative operational/Production authority;
- AST checks covering both direct-name and attribute calls.

Green coverage is mechanical evidence only and never substitutes for reviewer
falsification.

## 14. SERIAL GATE

Required integration sequence for the final candidate:

`VERIFY CURRENT MAIN`
`-> HARDEN/SYNC CANDIDATE`
`-> FULL CI`
`-> DIFF AUDIT`
`-> FREEZE EXACT HEAD + SYNTHETIC`
`-> POST-FREEZE FULL CI`
`-> DEEPSEEK EXPERT`
`-> IA ADJUDICATION`
`-> DEEPSEEK CODER`
`-> IA ADJUDICATION`
`-> CLAUDE CODE`
`-> IA ADJUDICATION`
`-> IA FINAL`
`-> READY`
`-> PROTECTED EXPECTED-HEAD MERGE`
`-> POST-MERGE MAIN VERIFICATION`
`-> #398 CLOSE IF SATISFIED`

Any material HEAD mutation after freeze invalidates that round and restarts the
serial review chain from DeepSeek Expert.

## 15. NON-CLAIMS

No UMI-14 final pass. No Program-D final pass. No QORE universal-market-ready
claim. No provider readiness. No Production. No real capital.
