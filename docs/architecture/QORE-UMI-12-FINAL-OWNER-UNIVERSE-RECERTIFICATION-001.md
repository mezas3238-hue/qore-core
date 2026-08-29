# QORE-UMI-12-FINAL-OWNER-UNIVERSE-RECERTIFICATION-001

Status: **candidate recertification for F-UMI14-UMI12-001 / issue #458**

## Purpose

Re-certify the UMI-12 cross-asset falsification harness against the complete D04 semantic-owner surface present on the activation baseline, rather than the historical 14-module universe frozen by the earlier full-closure harness.

Activation baseline:

- `main`: `ebd0adf000874797653df92ea1c08a892cce6c8c`
- tree: `08ce942dd944a2c02a1aa9971dbfbe011def919d`
- post-merge QORE CI: `#1478` / run `32907374346` / success
- production semantic source delta for this correction: **zero by design**

UMI-12 remains a falsification/evidence harness. This correction creates no new semantic owner.

## Current D04 owner universe

The recertification freezes an explicit owner manifest and independently discovers every `src/qore/infrastructure/*_semantics.py` and `*_qualification.py` module. The only current non-D04 qualification, `dataset_integrity_qualification`, is an explicit audited exclusion because it qualifies research/data evidence rather than market/instrument semantics. Six legacy D04 owners whose filenames use neither suffix are explicit carry-ins. Exact equality between the discovered D04 surface and the frozen manifest is the guard.

This discovery contract is intentionally tied to the actual D04 naming conventions plus the six audited legacy carry-ins. UMI-12 does not classify every arbitrary `src/qore/infrastructure/*.py` file as a potential D04 owner: that directory also contains provider, runtime, execution, persistence, research, hosting and other non-D04 modules. A new D04 owner that intentionally bypasses the established naming/registration convention is an architecture-governance violation to classify at source, not a reason to couple this semantic recertification to a global allowlist of all infrastructure modules.

### Legacy owners

1. `universal_instrument_identity`
2. `universal_instrument_identity_graph`
3. `fixed_income_economics`
4. `rate_term_structure`
5. `universal_valuation_observation`
6. `universal_market_topology`

### Semantic owners / qualifications discovered through `_semantics.py`

1. `advanced_payable_scf_semantics`
2. `cash_money_market_semantics`
3. `commodity_contract_delivery_semantics`
4. `crypto_perpetual_funding_semantics`
5. `crypto_staking_tokenization_semantics`
6. `derivative_contract_semantics`
7. `equity_fund_corporate_action_semantics`
8. `event_contract_semantics`
9. `fixed_income_securitization_semantics`
10. `futures_deliverable_basket_semantics`
11. `futures_final_settlement_semantics`
12. `fx_semantics`
13. `insurance_linked_risk_transfer_semantics`
14. `loan_credit_facility_semantics`
15. `option_exotic_semantics`
16. `product_composition_semantics`
17. `rainbow_option_composition_semantics`
18. `rates_otc_semantics`
19. `securities_financing_semantics`
20. `shariah_cross_family_semantics`
21. `specialized_commodity_semantics`
22. `structured_hybrid_synthetic_semantics`
23. `structured_note_payoff_semantics`
24. `sukuk_structural_semantics`
25. `supply_chain_finance_semantics`
26. `volatility_variance_semantics`
27. `warrant_convertible_qualification_semantics`

### D04 owners discovered through `_qualification.py`

1. `cfd_contract_qualification`
2. `uit_contract_qualification`

`dataset_integrity_qualification` is intentionally excluded from D04 because it qualifies research/data evidence rather than markets/instruments. Any new `*_qualification.py` file therefore fails closed until it is explicitly classified by this recertification surface.

Total current recertified owner/qualification modules on the activation baseline: **35**. The count is descriptive evidence, not the source of truth; source discovery plus exact manifest equality is the guard.

## Falsification claims

The updated UMI-12 guard/oracle surface verifies the following boundaries against the current owner universe:

- every manifest owner exists and the discovered live `*_semantics.py` + `*_qualification.py` D04 surface matches it exactly, with only the audited non-D04 dataset qualification excluded;
- all 19 Program-D family codes can bind through UMI-02 `EconomicIdentity` / `CanonicalIdentityRef` without provider symbol text becoming economic identity material;
- `EconomicIdentity` retains its exact canonical field surface and therefore cannot silently absorb listing/provider symbol material without recertification;
- listing identity remains distinct from economic identity;
- owner modules and the historical oracle statically reject direct provider/runtime/network imports and dynamic import/code-execution mechanisms (`importlib`/`import_module`, `__import__`, `eval`, `exec`), including `builtins` aliases/attribute access, `__builtins__` lookup shapes, and direct callable rebinding covered by the final guard;
- relative `from .…` owner imports are resolved to fully-qualified module names before provider/runtime/network and reverse-dependency/collision checks, so relative syntax cannot bypass either exclusion family;
- a numerically identical finite `Decimal` remains semantically distinct across RATE, YIELD, SPREAD, PRICE, NAV, IV, NOTIONAL, QUANTITY, and WEIGHT; quantity and weight remain explicitly discriminated even though they share the generic product-composition magnitude type;
- generic identity, derivative, product-composition, and valuation authorities do not reverse-import product-specific qualifications;
- rainbow qualification composes existing option economics and product-composition authority instead of owning either one;
- Sukuk structural qualification and Shari'ah cross-family qualification remain distinct owner types without mutual owner imports;
- insurance-linked risk-transfer terms and event-contract terms remain distinct owner types without mutual owner imports;
- securities-financing semantics reject current-state authority class shapes involving account, balance, current state, exposure, inventory, position or Risk while retaining bounded static contractual collateral/margin terms;
- Advanced Payable SCF extends the existing Supply Chain Finance owner directionally; the ICC-2017 owner does not reverse-import the later qualification;
- the historical FX, option-exotic, and fixed-income-securitization carry-forward specimens and their deterministic projections remain unchanged;
- the oracle continues to define no semantic facsimile classes and no execution/routing/valuation/settlement helper authority.

## Expert R1 hardening

Independent Expert review identified three harness bypasses: undiscovered future `*_qualification.py` D04 owners, dynamic import/code-execution paths invisible to ordinary import-node scans, and an exact-name-only SFT current-state blacklist. Independent adjudication reproduced all three as accepted-invalid harness witnesses. The correction is test-only: fail-closed qualification discovery, prohibition of dynamic import/code-execution mechanisms across owners/oracle, and structural SFT current-state class-shape rejection. No production semantic owner was modified.

## Expert R2 adjudication and hardening

Independent Expert R2 proposed four additional findings. Independent adjudication accepted three and rejected one as outside the bounded #458 contract:

1. **Accepted — builtins/alias dynamic-execution bypass.** `builtins.eval`/`builtins.exec`/`builtins.__import__` and direct aliases imported from `builtins` could evade the prior scanner. The final guard now resolves these shapes, `getattr` on builtins aliases and `__builtins__` subscript access, with a fixed synthetic regression witness.
2. **Accepted — relative-import reverse-dependency bypass.** `from .product_specific_module import …` was not normalized to a fully-qualified dependency by the historical helper. The final guard now resolves relative imports and independently rechecks generic/product, Sukuk/Shari'ah, ILS/event-contract and SCF/Advanced-Payable directionality. A fixed synthetic regression witness proves the resolver itself.
3. **Rejected as non-material — arbitrary non-conventional `future_d04_owner.py`.** #458 requires reconstruction of the complete current D04 owner/qualification set from source/tests/docs and final currentness across the actual D04 conventions. Treating every future arbitrary `infrastructure/*.py` as D04 would force a global allowlist covering operational/provider/research/runtime modules and would broaden UMI-12 beyond its semantic-owner mandate. Established suffix discovery plus audited legacy carry-ins remains the bounded contract.
4. **Accepted — tautological UMI-02 symbol-laundering witness.** Checking that one listing symbol string is absent from one current economic-identity projection does not prevent a future optional economic field from carrying listing/provider material. The final guard now freezes the exact `EconomicIdentity` dataclass field surface; any new field requires explicit recertification rather than silently passing the symbol-separation proof.

All accepted R2 corrections remain test/doc-only. No production semantic owner was modified.

## Expert R3 adjudication and hardening

Independent Expert R3 proposed two additional high-severity harness bypasses. Independent adjudication reproduced and accepted both:

1. **Accepted — dangerous callable rebinding.** A local alias such as `f = eval; f("1+1")`, a transitive alias such as `g = f`, or a binding from `builtins.eval`, `getattr(builtins, "__import__")`, or `__builtins__["eval"]` could evade call-site-only detection. The final scanner now propagates dangerous callable bindings through `Assign`, `AnnAssign` and named-expression targets until a fixed point and rejects both the binding and subsequent call. A fixed synthetic regression witness covers direct, transitive, annotated, `getattr`, and `__builtins__` shapes.
2. **Accepted — relative provider/runtime import bypass in historical exclusion helpers.** The historical `_imported_modules` / `_file_imports` helpers ignore `ImportFrom` nodes where `node.module is None`, so `from . import provider_runtime` could make those individual historical assertions pass. The final recertification guard now independently applies the normalized relative-import resolver across every current D04 owner and the historical oracle, then enforces the same provider/runtime/network exclusions. A fixed synthetic witness proves that `from . import provider_runtime` and `from . import execution_boundary` resolve to fully-qualified forbidden dependencies. Therefore the complete recertification suite fails closed even if the historical helper alone would miss that syntax.

All accepted R3 corrections remain test/doc-only. No production semantic owner was modified. Because the candidate HEAD changed, all prior SHA-bound review authorization is invalidated and the serial external-review chain must restart from Expert after a new full Quality Gate and freeze.

## Determinism, immutability, and evidence posture

The recertification uses fixed UUIDs, fixed dates/timestamps, exact `Decimal` values, immutable owner value objects, deterministic `logical_values()` projections and fixed in-memory AST regression specimens. It introduces no wall clock, implicit UUID generation, network access, provider query, secret, credential, mutable global state, scheduler, retry loop, execution call, or settlement mutation.

The harness validates semantic ownership and collision resistance. It does not manufacture operational evidence.

## Explicit non-claims

This recertification does **not** claim or authorize:

- provider support or provider operational readiness;
- market-data connectivity;
- valuation correctness or valuation-engine authority;
- execution, routing, matching, order submission, or settlement authority;
- current position, collateral, account, or Risk state;
- OANDA/cTrader/other provider activation;
- Production readiness;
- Production accounts or productive credentials;
- real-money trading or real-capital authority.

`PROGRAM-D semantic recertification != provider operational readiness != Production readiness != real-capital authorization.`

## Quality gate required before adjudication

The candidate is not approved by this document. Approval requires exact-head success for:

```text
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

After exact-head CI and diff audit, the candidate must be frozen and reviewed serially under the repository review protocol. Any candidate mutation invalidates prior SHA-bound review authorization.
