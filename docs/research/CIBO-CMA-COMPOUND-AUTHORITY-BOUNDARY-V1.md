# CIBO CMA ↔ Compound Authority Boundary V1

Status: **ENGINEERING CLOSURE GATE / RESEARCH-SHADOW**

This gate proves the constitutional boundary between the original CIBO Capital
Management Authority foundation and the newer Compound Engine.

It asserts:

1. TraderOpportunityEnvelope contains market geometry and no sizing/capital
   allocation field.
2. Account-scoped CIBO sizing alone creates executable volume from the
   opportunity plus current capital/provider constraints.
3. Compound capital is admitted only from reconciled terminal settlement.
4. Source Ledger REALIZED_PROFIT and GEN-C admission are equivalent
   representations of the same value and cannot be summed twice.
5. The closing realized-capital identity reconciles exactly.

This closes duplicate-authority/accounting risk at the engine level. It does
not prove economic utility or certify CIBO.

## Terminalization rule

The master ledger may mark `CMA_FOUNDATION_INTEGRATION` terminal only after
the `cibo-cma-compound-boundary` workflow is GREEN on the current Architect A
lineage. Later capital-science work does not reopen this engineering boundary
unless it changes one of the authority/accounting surfaces covered by that
workflow.
