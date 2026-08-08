# QORE-CLIENT-PROFIT-VAULT-ARCH-001 — Client Profit Vault, Settlement & Entitlement Architecture

## Estado

**ARCHITECTURE DEFINED — IMPLEMENTATION NOT YET AUTHORIZED**

Base verificada al abrir este entregable:

```text
main @ 858a36e1458f92b0aa25a864e7f318424b98c822
```

Este documento formaliza la arquitectura objetivo del Client Profit Vault, su ledger económico, el cálculo futuro de profit share y la emisión de entitlements de servicio, preservando aislamiento absoluto respecto de QORE Core.

## Propósito

Definir un dominio corporativo independiente que pueda:

- recibir resultados económicos positivos y negativos producidos por Client Execution Agents;
- conservar historial completo por ledger cliente opaco;
- distinguir resultados facturables y no facturables;
- soportar cuentas en evaluación/verificación sin generar cargos;
- calcular el profit share aplicable cuando exista beneficio económicamente elegible;
- registrar pagos/pendientes;
- emitir o renovar entitlements de servicio;
- dejar expirar entitlements ante falta de pago;
- producir evidencia comercial/auditable;
- alimentar un read model autorizado para el CEO Command Center.

## Invariante de aislamiento

```text
QORE CORE  X  CLIENT PROFIT VAULT
```

Core no conoce que el Profit Vault existe.

Profit Vault no conoce:

- QORE Core;
- CIBO;
- traders;
- estrategias;
- mercado interno;
- cuentas del CEO;
- decisiones propietarias;
- portfolio/risk internos de Core.

Ningún estado de pago puede modificar el comportamiento de Core.

## Relación con Client Execution Agent

El Agent puede tener dos conexiones externas independientes:

```text
QORE CORE / SIGNAL DISTRIBUTION
          │
          │ signed signal
          ▼
CLIENT EXECUTION AGENT
          │
          ├── settlement result events ─────> CLIENT PROFIT VAULT
          │
          └── status snapshots ─────────────> CLIENT STATUS RELAY
```

Profit Vault no recibe status snapshots de balance/DD/positions usados por el widget.

Status Relay no recibe settlement/billing state salvo que se defina un read model futuro separado.

## Identidades opacas

Profit Vault debe operar con identificadores que no requieran identidad real del cliente:

```text
SettlementLedgerId
EntitlementId
EAInstanceId
SettlementPeriodId
SettlementEventId
```

El Vault no necesita almacenar:

- nombre real;
- documento;
- broker account number;
- login de plataforma;
- balance general de la cuenta;
- equity;
- drawdown;
- open positions.

La asociación entre cliente autenticado y ledger puede existir en un dominio comercial/identity separado.

## Settlement Event

El Client Agent debe poder emitir un evento económico mínimo, autenticado y versionado, cuando exista un resultado realizado relevante para settlement.

Conceptualmente:

```text
SettlementEvent
- protocol_version
- settlement_ledger_id
- ea_instance_id
- event_id
- sequence
- closed_at
- realized_result
- applicable_costs
- net_result
- currency
- account_phase
- settlement_class
- integrity/signature
```

Los campos exactos pertenecen a un contrato posterior.

El evento no debe transportar estrategia, trader, CIBO reasoning ni market intelligence propietaria.

## Positive and Negative History

Todos los resultados realizados elegibles para el ledger se conservan, incluidos positivos y negativos.

```text
positive result -> stored
negative result -> stored
```

Un resultado negativo:

```text
BILLING DUE = 0
```

pero no se elimina, oculta ni descarta.

El historial negativo es necesario para:

- explicar liquidaciones;
- resolver preguntas del cliente;
- reconstruir períodos;
- demostrar que las pérdidas fueron consideradas;
- auditoría/disputes;
- futuras reglas de loss carryforward/high-water mark.

## Principio comercial del 20%

La intención comercial aprobada es:

> QORE cobra 20% únicamente sobre beneficio positivo económicamente elegible bajo la policy contractual aplicable.

No existe cargo por pérdida.

No se debe calcular el 20% agregando patrimonios de clientes distintos.

Cada `SettlementLedgerId` se liquida de forma independiente.

Ejemplo conceptual:

```text
CLIENT A
eligible net positive = +10,000
20% due = 2,000

CLIENT B
eligible net result = -3,000
20% due = 0

CLIENT C
eligible net positive = +5,000
20% due = 1,000
```

Corporate aggregate receivable:

```text
2,000 + 0 + 1,000 = 3,000
```

No:

```text
(10,000 - 3,000 + 5,000) * 20%
```

## Net settlement principle

Dentro de un ledger y período, el sistema debe poder considerar resultados positivos y negativos antes de determinar beneficio elegible.

Ejemplo conceptual:

```text
positive realized total = +5,000
negative realized total = -2,000
net realized result = +3,000
eligible positive base = +3,000
20% due = 600
```

Si:

```text
net realized result <= 0
```

entonces:

```text
profit share due = 0
```

La fórmula contractual exacta debe definir costes, swaps/commissions cuando correspondan, corrections, currencies, cutoff y eligibility semantics antes de implementación financiera productiva.

## Loss carryforward / high-water-mark capability

La arquitectura debe soportar una policy que evite cobrar por mera recuperación de pérdidas previas.

Ejemplo conceptual:

```text
period 1 = -2,000
period 2 = +1,500
```

Una policy de carryforward puede mantener:

```text
unrecovered loss = -500
profit share due = 0
```

Si posteriormente:

```text
period 3 = +2,000
```

la base económicamente nueva puede quedar en:

```text
+1,500
```

Este documento exige soporte arquitectónico para esa semántica. La regla contractual definitiva y sus edge cases deberán quedar versionados antes de billing productivo.

## Funded-account service phases

Profit Vault debe distinguir resultados de fases de fondeo mediante una clasificación normalizada.

Estados conceptuales:

```text
EVALUATION
VERIFICATION
REWARD_ELIGIBLE
PAYOUT_ELIGIBLE
SUSPENDED
UNKNOWN
```

### Evaluation

Los resultados pueden almacenarse para historia y auditoría.

```text
settlement class = NON_BILLABLE
profit share due = 0
```

### Verification

Los resultados pueden almacenarse para historia y auditoría.

```text
settlement class = NON_BILLABLE
profit share due = 0
```

### Reward / payout eligible phase

Sólo cuando la policy aplicable determine que el resultado positivo puede generar beneficio económico elegible se habilita el cálculo de profit share.

No se usa `REAL ACCOUNT` como condición universal, porque los modelos de prop firms pueden usar simulación y aun así generar recompensas económicas.

## Economically eligible profit

La arquitectura debe separar:

```text
REALIZED_POSITIVE
       !=
ECONOMICALLY_ELIGIBLE_PROFIT
       !=
SETTLEMENT_CONFIRMED
```

El mero resultado positivo mostrado por la plataforma no debe crear automáticamente una deuda definitiva si la policy del programa exige revisión, payout/reward eligibility u otra condición verificable.

## Settlement lifecycle

Flujo conceptual:

```text
Settlement Events
      ↓
period aggregation
      ↓
positive / negative history
      ↓
account phase / settlement class
      ↓
loss carryforward / policy adjustments
      ↓
eligible positive base
      ↓
profit-share calculation
      ↓
settlement review/finalization
      ↓
amount due
      ↓
payment state
      ↓
entitlement renewal/expiry
```

## Settlement states

Estados conceptuales iniciales:

```text
OPEN
CALCULATING
READY
DUE
PAID
PAST_DUE
DISPUTED
CORRECTED
CLOSED
```

Los nombres exactos serán definidos por contrato posterior.

## Append-only evidence

El Vault debe preferir historial append-only.

Una corrección no sobrescribe silenciosamente el evento original.

Conceptualmente:

```text
original event
      ↓
adjustment/correction event
      ↓
reference to original
```

Esto aplica también a settlement finalizado cuando exista una corrección autorizada.

## Entitlement authority

Profit Vault actúa también como autoridad de entitlement comercial para el Client Agent, sin hablar con Core.

Modelo:

```text
PAYMENT / SERVICE STATE
        ↓
PROFIT VAULT
        ↓
signed short-lived entitlement lease
        ↓
CLIENT EXECUTION AGENT
```

El Agent valida el entitlement localmente antes de aceptar nuevas señales.

## Service Entitlement Token

Contrato conceptual:

```text
ServiceEntitlementToken
- protocol_version
- entitlement_id
- ea_instance_id
- routing_permissions
- valid_from
- valid_until
- policy_version
- sequence
- signature
```

No debe incluir información de Core/CIBO.

## Non-payment behavior

El Vault no envía una orden a Core para cortar señales.

Core sigue publicando normalmente.

Ante impago:

```text
Vault does not renew entitlement
        ↓
current lease expires
        ↓
Client Agent rejects NEW signals
```

Invariante:

```text
CORE BEHAVIOR = UNCHANGED
```

## Existing position protection

El vencimiento del entitlement no debe apagar protección de posiciones existentes.

```text
NEW SIGNAL CONSUMPTION = BLOCKED
EXISTING POSITION PROTECTION = ACTIVE
```

El agente debe poder continuar, según plataforma/runtime:

- SL;
- TP;
- trailing;
- local risk protection;
- safe close behavior required by policy.

El servicio comercial no puede poner capital en riesgo como mecanismo de cobro.

## Reactivation

Después de payment confirmation y policy satisfaction:

```text
payment confirmed
      ↓
settlement/payment state updated
      ↓
new signed entitlement issued
      ↓
Client Agent validates new lease
      ↓
new-signal eligibility restored
```

No existe intervención de Core.

## Client inquiry / statement support

El sistema debe poder producir un estado explicable para el cliente correspondiente a su propio ledger.

Ejemplo conceptual:

```text
Period: 2026-08
Positive realized: +...
Negative realized: -...
Net realized: +...
Previous loss carried: ...
Eligible positive base: +...
Profit-share rate: 20%
Amount due: ...
Amount paid: ...
Outstanding: ...
Entitlement state: ...
```

El dominio de identidad/portal que entregue ese estado debe autorizar que el solicitante sólo acceda a su ledger.

Profit Vault puede seguir utilizando identificadores opacos internamente.

## CEO Command Center read model

El CEO puede consultar un read model corporativo autorizado sin conectar Core con Profit Vault.

Dashboard objetivo:

```text
CLIENT PROFIT VAULT

Total ledgers
Positive ledgers
Negative ledgers
Break-even ledgers

Evaluation
Verification
Reward/Payout Eligible

Positive realized total
Negative realized total
Eligible positive base
20% receivable
Collected
Outstanding

Entitlements active
Payment due
Grace
Suspended
Reactivated

Settlements
Disputes
Audit exceptions
```

Los valores de clientes distintos no se mezclan para calcular cargos individuales. Los agregados son sólo vistas corporativas posteriores a cálculos por ledger.

## Per-ledger CEO view

El CEO puede inspeccionar un ledger opaco autorizado:

```text
SettlementLedgerId
current phase
current period
positive total
negative total
net result
carryforward state
eligible base
20% due
paid/outstanding
entitlement state
settlement history
suspension/reactivation history
```

No requiere revelar el número real de cuenta o identidad personal en el Vault.

## Monthly history

El Vault debe soportar historial por períodos para:

- positive/negative outcomes;
- net result;
- eligible profit;
- profit share due;
- payments;
- outstanding;
- suspensions;
- reactivations;
- adjustments;
- disputes.

El corte temporal, timezone y moneda deben definirse explícitamente por policy.

## Currency semantics

La implementación futura debe impedir sumar importes de monedas diferentes sin una policy explícita.

El ledger debe conocer la currency aplicable a cada evento/settlement.

Cualquier conversión futura requiere una fuente/version de FX explícita y auditable.

## Security and integrity

Como el Client Agent puede ejecutarse en un entorno controlado por el cliente, los settlement events no deben asumirse incorruptibles por definición.

La arquitectura futura debe contemplar:

- signed agent builds;
- instance/license binding;
- signed settlement events;
- monotonic sequence;
- anti-replay;
- event continuity checks;
- period sealing;
- duplicate detection;
- integrity findings;
- dispute/reconciliation process.

No se debe prometer tamper-proof absoluto.

## Payment provider boundary

Un sistema de pago puede integrarse con el dominio corporativo sin revelar Core.

Idealmente el Vault necesita únicamente algo equivalente a:

```text
EntitlementId / SettlementId
Payment state
Timestamp
Reference
```

La identidad de pago completa puede permanecer en otro dominio si la arquitectura legal/comercial futura lo exige.

## No trading authority

Profit Vault no posee autoridad de trading.

No puede:

- crear señales;
- modificar señales;
- cambiar estrategias;
- ordenar BUY/SELL;
- mover SL/TP;
- cambiar risk;
- cerrar posiciones como acción de cobro;
- comunicarse con Core para bloquear mercados/clientes.

Su autoridad se limita a settlement/evidence/entitlement comercial.

## Separation from CEO proprietary performance

Profit Vault no contiene PnL de cuentas propiedad/control del CEO.

```text
CEO PROPRIETARY PERFORMANCE
      !=
CLIENT SERVICE SETTLEMENT
```

El CEO Command Center puede mostrar ambos en módulos distintos, pero nunca se agregan como una sola fuente de trading profit.

## Audit package

Cada settlement finalizable debe poder explicar:

```text
WHAT
WHEN
LEDGER
PERIOD
EVENTS INCLUDED
POSITIVE TOTAL
NEGATIVE TOTAL
CARRYFORWARD / ADJUSTMENTS
ELIGIBLE BASE
POLICY VERSION
PROFIT-SHARE RATE
AMOUNT DUE
PAYMENT STATE
ENTITLEMENT STATE
CORRECTIONS
```

Esto permite responder por qué se cobró una cantidad específica sin depender de una explicación manual no reproducible.

## Fronteras explícitamente cerradas por este entregable

Este documento no implementa ni autoriza:

- Profit Vault executable;
- settlement database;
- payment integration;
- productive billing;
- automatic invoice generation;
- legal contract terms;
- tax/accounting treatment;
- client identity database;
- Client Agent implementation;
- Core-to-Vault communication;
- real-capital trading authorization;
- Production trading.

## Legal/commercial gate

Antes de comercializar ejecución automática, señales y profit-share, las condiciones contractuales, regulatorias, fiscales y de protección al consumidor deben revisarse por jurisdicción aplicable.

La arquitectura no presume una clasificación legal concreta.

## Entregables derivados recomendados

1. `QORE-SETTLEMENT-EVENT-PROTOCOL-001` — Signed Economic Result Event Contract.
2. `QORE-PROFIT-SHARE-POLICY-001` — Eligible Profit, Loss Carryforward & 20% Settlement Policy.
3. `QORE-FUNDED-ACCOUNT-SETTLEMENT-001` — Evaluation/Verification/Reward Eligibility Contracts.
4. `QORE-PROFIT-VAULT-LEDGER-001` — Append-only Client Settlement Ledger.
5. `QORE-PROFIT-VAULT-AUDIT-001` — Settlement Evidence & Corrections.
6. `QORE-SERVICE-ENTITLEMENT-PROTOCOL-001` — Signed Renewable Entitlement Lease.
7. `QORE-PROFIT-VAULT-PAYMENT-BOUNDARY-001` — Payment State Boundary.
8. `QORE-PROFIT-VAULT-CEO-READ-MODEL-001` — Corporate Dashboard Projection.
9. `QORE-CLIENT-SETTLEMENT-STATEMENT-001` — Authorized Per-Ledger Client Statement.

## Criterio de aceptación arquitectónico

Este entregable queda satisfecho cuando el repositorio establece inequívocamente que:

- Profit Vault está aislado de Core;
- resultados positivos y negativos se conservan;
- pérdidas no generan cobro;
- el 20% se calcula sólo sobre beneficio positivo económicamente elegible;
- cálculos son por ledger cliente, nunca compensando clientes distintos;
- Evaluation/Verification pueden conservar historia sin ser facturables;
- reward/payout eligibility está separada de mero realized positive;
- la arquitectura soporta loss carryforward/high-water-mark policy;
- corrections son auditables y no silenciosamente destructivas;
- Profit Vault emite entitlements sin comunicación con Core;
- impago causa no-renovación/expiración del entitlement, no una orden a Core;
- posiciones existentes mantienen protección después de expirar el servicio;
- el CEO puede ver agregados y detalle por ledger mediante un read model corporativo separado;
- CEO proprietary performance nunca se mezcla con Client Profit Vault;
- ninguna implementación financiera productiva queda autorizada por este documento.
