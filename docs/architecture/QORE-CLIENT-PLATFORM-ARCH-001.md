# QORE-CLIENT-PLATFORM-ARCH-001 — Client Execution, Accounts & Commercial Platform Architecture

## Estado

**ARCHITECTURE DEFINED — IMPLEMENTATION REQUIRES AN EXPLICIT NON-PRODUCTION MISSION**

Base verificada al abrir este entregable:

```text
main @ 9899a042084fd16fcd9e8dadd5e5dae03e978292
```

Estado externo preservado al abrirlo:

```text
MISSION-03 Gate #5 / issue #146 = OPEN / BLOCKED
MISSION-05 = COMPLETED
MISSION-06 = CLOSED
Production = CLOSED
```

Este documento no abre MISSION-06, no habilita Production y no satisface ninguna evidencia operativa externa.

## Propósito

Consolidar la siguiente frontera de producto cliente de QORE antes de autorizar implementación ejecutable.

La arquitectura une, sin mezclarlos, los dominios futuros de:

- Client / Account Foundation;
- Account & Prop Firm Policy Governance;
- QORE Client Execution Agent;
- cryptographic Core Decision delivery;
- position lifecycle and causal audit;
- Client Performance Ledger;
- trial, licensing and entitlements;
- QORE Commercial Platform;
- Corporate Profit Vault revenue projection;
- multi-account Client Widget;
- Managed Hosting;
- native broker/FCM execution boundaries;
- regional Futures execution.

## Relación con arquitectura existente

Este entregable **complementa y refina para trabajo futuro**, sin reescribir retrospectivamente:

- `QORE-CLIENT-EXECUTION-EXPERIENCE-ARCH-001`;
- `QORE-CLIENT-PROFIT-VAULT-ARCH-001`;
- los provider/adapter boundaries ya cerrados;
- los execution/safety contracts ya existentes;
- MISSION-04 Executive Control Plane;
- MISSION-05 QORE Mobile & CEO Command Center.

Los documentos anteriores siguen siendo evidencia histórica válida del alcance que cerraron.

Cuando una afirmación conceptual anterior todavía no implementada sea más débil que una invariante establecida aquí, los contratos futuros deben seguir la invariante más estricta de este documento mediante una nueva delivery. No se modifica silenciosamente una delivery cerrada.

## Invariante máxima de autoridad

```text
NO CORE DECISION -> NO NEW TRADING ACTION
```

QORE Core es la única autoridad estratégica capaz de originar una nueva acción de trading.

El Client Execution Agent no:

- busca oportunidades;
- genera señales;
- decide BUY o SELL;
- crea riesgo estratégico;
- inventa entradas;
- convierte estado comercial en trading authority.

El Agent consume una `Core Decision` auténtica y vigente y realiza **deterministic delegated execution** bajo policies autorizadas.

## Core Decision y lifecycle delegado

Una Core Decision puede autorizar el inicio de un lifecycle de posición y las policies deterministas que gobiernan sus acciones posteriores.

Por tanto:

```text
NEW POSITION / NEW TRADE
    requires Core Decision

AUTHORIZED OPEN POSITION LIFECYCLE
    may be managed deterministically
    from Core Decision + authorized policy + observed state
```

SL, TP, trailing, protective close y otras mutaciones de una posición existente no constituyen inteligencia estratégica autónoma cuando están causalmente limitadas por la decisión original y una policy versionada.

Ninguna policy de lifecycle puede utilizarse para originar una posición que la Core Decision no autorizó.

## Genealogía causal obligatoria

No deben existir acciones de trading huérfanas.

La cadena mínima es:

```text
ACTION
  -> POSITION
  -> CORE DECISION
  -> POLICY
  -> RATIONALE
  -> EVIDENCE
```

El sistema futuro debe poder reconstruir, al menos:

- por qué una cuenta ejecutó;
- por qué una cuenta bloqueó;
- por qué se eligió un tamaño;
- por qué se calculó un Stop Loss;
- por qué se calculó un Take Profit;
- por qué se movió un trailing stop;
- por qué se cerró una posición;
- qué resultado produjo;
- qué policy/version gobernó cada paso;
- qué estado observado y evidencia soportaron la acción.

`RATIONALE` significa razones estructuradas y reproducibles; no requiere almacenar private chain-of-thought.

## Multi-account

Modelo comercial y operativo objetivo:

```text
1 Client -> N independent Trading Accounts
```

Cada cuenta mantiene identidad lógica y estado independiente para:

- execution;
- account lifecycle;
- risk;
- drawdown;
- daily loss;
- prop-firm policy;
- payout state;
- realized P&L;
- performance accounting;
- Client Agent entitlement;
- hosting entitlement.

No se compensa riesgo de cuentas distintas como si perteneciera a una sola cuenta de capital.

## Un execution authority por cuenta

Cada trading account tiene una instancia lógica independiente de Client Execution Agent.

```text
Account-01 -> Agent-01
Account-02 -> Agent-02
...
Account-N  -> Agent-N
```

Varias instancias pueden ejecutar la misma versión de software, pero no comparten autoridad de cuenta.

Una Core Decision puede distribuirse a múltiples cuentas autorizadas. Cada cuenta obtiene un verdict local independiente, por ejemplo:

```text
EXECUTE
BLOCK
RISK_BLOCKED
PROP_POLICY_BLOCKED
ENTITLEMENT_BLOCKED
UNRESOLVED
```

El fan-out no duplica la inteligencia estratégica del Core.

## Client y Account Registry

La plataforma comercial futura necesita separar:

```text
Client Registry
Account Registry
```

`Client Registry` representa la relación comercial/servicio mínima necesaria.

`Account Registry` representa cuentas de trading opacas y su binding a un cliente, producto, policy y runtime autorizado.

Core no debe depender de ninguno de estos registros para producir su inteligencia estratégica.

Los identificadores de cuenta usados fuera del execution boundary deben ser opacos siempre que el número/login real no sea necesario.

## Account / Prop Firm Policy Registry

La policy efectiva de una cuenta no debe estar hardcodeada como una lista monolítica dentro del EA.

El dominio de policy debe soportar snapshots versionados con información como:

- firm;
- program;
- account class/size;
- phase;
- maximum drawdown;
- daily loss;
- static/trailing drawdown semantics;
- profit split;
- payout eligibility/policy;
- trading restrictions;
- effective version;
- provenance/evidence.

Reglas críticas requeridas para protección local deben estar disponibles en el execution runtime de forma verificable.

Policy incompleta, ambigua, no vigente o no verificable para una regla obligatoria:

```text
NO NEW TRADING
```

## QORE Client Execution Agent

El concepto superior permanece:

```text
QORE Client Execution & Capital Protection Agent
```

Una implementación de plataforma como MT5 EA es un adapter/runtime concreto de ese concepto.

Ante una Core Decision válida, el Agent futuro debe poder:

1. verificar autenticidad;
2. verificar integridad;
3. verificar protocol/version;
4. verificar freshness y expiry;
5. verificar nonce/sequence y anti-replay;
6. verificar account/runtime binding;
7. verificar entitlement;
8. resolver estado/capabilities de cuenta;
9. resolver policy snapshot autorizada;
10. aplicar local capital protection;
11. calcular sizing determinista;
12. calcular Stop Loss;
13. calcular Take Profit;
14. ejecutar mediante un execution adapter soportado;
15. administrar lifecycle autorizado, incluido trailing;
16. emitir receipts/evidence;
17. producir status/performance telemetry hacia boundaries autorizadas.

Ningún paso concede libertad para reinterpretar la intención estratégica de Core.

## Trailing Stop

Trailing Stop es una capacidad autorizable del lifecycle, no una estrategia autónoma.

```text
TRAILING ACTION
 = Core Decision
 + Authorized Trailing Policy
 + Observed Account/Market State
```

Cada modificación debe conservar evidencia equivalente a:

```text
decision_id
position_id
trailing_policy_id
trigger
previous_stop
new_stop
observed_at
action_at
evidence_refs
```

Los tipos y unidades definitivos pertenecen a contratos posteriores.

## Cryptographic Core Decision security

Una Core Decision no debe transportarse como un comando reutilizable en texto plano.

El protocolo futuro debe definir un canonical decision envelope con, como mínimo:

- protocol/schema version;
- decision identity;
- canonical payload representation;
- authenticity/signing;
- integrity protection;
- confidentiality/encryption donde el threat model lo requiera;
- nonce o mecanismo equivalente;
- issued-at;
- expiration;
- anti-replay state;
- routing/account/runtime binding cuando corresponda;
- entitlement binding o referencia verificable;
- key identity/rotation;
- revocation semantics.

Invariantes:

```text
captured decision + replay -> REJECT
wrong account/runtime binding -> REJECT
expired decision -> REJECT
revoked key/authority -> REJECT
modified payload -> REJECT
copied Agent without valid Core authority -> NO NEW TRADING
```

La inteligencia estratégica del Core no se distribuye dentro del Agent.

## Core isolation preserved

La arquitectura cliente no introduce callbacks de ejecución dentro de la lógica estratégica de Core.

Core no necesita conocer:

- identidad civil del cliente;
- billing state;
- payout state;
- broker credentials del cliente;
- posiciones de una cuenta cliente para producir una nueva decisión estratégica, salvo que una misión futura autorice explícitamente otro modelo.

Execution receipts, performance events y status telemetry se dirigen a boundaries externos apropiados, no al Core estratégico.

## Position Lifecycle & Causal Audit

El dominio futuro debe distinguir al menos:

```text
Core Decision
Execution Attempt
Execution Receipt
Position
Protection State
SL Change
TP Change
Trailing Change
Exit
Realized Result
Causal Evidence
```

Cada transición debe tener identidad, temporalidad explícita y referencia causal suficiente para reconstrucción determinista.

No debe existir automatic redispatch de una nueva ejecución ante outcome ambiguo.

Una ambigüedad de ejecución requiere reconciliation/receipt verification antes de cualquier acción que pueda duplicar exposure.

## Client Performance Ledger

Los resultados económicos de cuentas cliente pertenecen primero a un dominio de performance cliente, no al Corporate Profit Vault.

```text
Execution Result
      -> Client Performance Ledger
      -> Commercial/Billing eligibility
      -> Corporate Profit Vault projection after verified obligation/payment evidence
```

El Client Performance Ledger debe preservar por cuenta:

- realized wins/losses;
- realized P&L;
- settlement/performance events;
- trial-start evidence;
- payout/reward evidence;
- corrections;
- policy/version provenance.

`CLIENT PERFORMANCE != QORE CORPORATE MONEY`

## Profit semantics refinement

Los contratos futuros deben distinguir expresamente:

```text
GROSS TRADING PROFIT
CLIENT ENTITLED PROFIT
CLIENT PAID PROFIT
ELIGIBLE CLIENT PAID PROFIT
QORE PERFORMANCE FEE
```

La regla económica objetivo queda refinada a:

```text
QORE Core Performance Fee
 = 20% of verified Eligible Client Paid Profit
```

Ejemplo conceptual:

```text
Gross trading profit        = 10,000
Client contractual split    = 80%
Client paid profit          = 8,000
QORE performance-fee base   = 8,000
QORE 20% fee                = 1,600
```

No se debe cobrar sobre una cantidad que el cliente no recibió cuando la policy contractual define el pago efectivo como gate de elegibilidad.

Esta regla refina la semántica futura más amplia de `economically eligible positive profit` descrita en `QORE-CLIENT-PROFIT-VAULT-ARCH-001`. No requiere migración de runtime porque ese documento no autorizó una implementación financiera productiva.

Payment/payout evidence debe ser verificable. `DUE != PAID`.

## Commercial Platform

La futura `QORE Commercial Platform` es un dominio separado de Core y del execution path.

Componentes objetivo:

- Client Registry;
- Account Registry;
- Products & Plans;
- Trial Management;
- Billing;
- Invoice Ledger;
- Payments;
- Payment Reconciliation;
- Entitlements;
- Performance Accounting;
- Account/Prop Policy;
- Corporate Profit Vault.

Productos comerciales independientes pueden incluir:

- Client Execution Agent;
- Client Widget;
- Core Services;
- Managed Hosting;
- Managed Futures.

Billing tiene autoridad comercial, nunca trading authority.

## Trial semantics

Hipótesis comercial actualmente aprobada para diseño:

```text
Client Execution Agent = USD 29 / account / month
Trial = 14 days
```

El trial no comienza con download, install, registration, PC/VPS change o reinstall.

Debe comenzar únicamente con evidencia de:

```text
FIRST ELIGIBLE LIVE EXECUTION
```

Después de esa evidencia:

```text
trial_started_at = immutable
trial_expires_at = immutable
```

Una reinstalación o cambio de runtime no reinicia el trial.

Estas cantidades comerciales deben vivir en Products/Plans/versioned policy y no hardcodearse dentro del execution engine.

## Safe entitlement suspension

Impago/expiración del Agent:

```text
PAYMENT FAILED / ENTITLEMENT EXPIRED
      -> NO NEW TRADES
      -> SUSPEND_PENDING_FLAT
      -> continue only already-authorized lifecycle/protection
      -> account FLAT
      -> AGENT SUSPENDED
```

Billing no puede cerrar una posición como mecanismo de cobro.

La protección de una posición existente no se retira por impago.

## Client Widget

Hipótesis comercial actual para diseño:

```text
Client Widget = USD 9.99 / client / month
```

No es per-account.

Un cliente con N cuentas puede consumir un único read model multi-account con:

- account status;
- balance;
- generated today;
- generated this week;
- recent trade pulse;
- per-account drill-down;
- service status.

El Widget:

- no genera trades;
- no modifica risk;
- no accede al broker;
- no forma parte del execution path;
- no recibe trading authority por autenticación.

Su fuente debe ser un `Client Read Model` / Status Relay autorizado y separado.

Impago del Widget puede suspender únicamente el Widget; no modifica Agent, Core, posiciones, hosting ni risk.

## Corporate Profit Vault

Corporate Profit Vault consolida exclusivamente activos/ingresos/deudas corporativas de QORE.

Fuentes futuras pueden incluir:

- EA subscription revenue;
- Widget revenue;
- Hosting revenue;
- Futures managed revenue;
- Core performance-fee revenue;
- Cash Received;
- Accounts Receivable.

Toda entrada debe conservar atribución suficiente a client/account cuando corresponda, invoice/product/period/currency y payment evidence.

Invariantes:

```text
Client Performance Ledger != Corporate Profit Vault
DUE != PAID
payment cannot be inferred
```

## Managed Hosting

Managed Hosting es un producto independiente del Agent.

Modos conceptuales:

```text
SELF_HOSTED
QORE_MANAGED
```

QORE Managed debe permitir un execution runtime persistente sin depender del teléfono del cliente.

Componentes objetivo:

- Hosting Orchestrator;
- Account Execution Units;
- Runtime Registry;
- Health Supervisor;
- Heartbeats;
- Deployment Controller;
- Failover;
- Fencing;
- Reconciliation;
- Telemetry;
- Secret Boundary.

## Single-writer execution

Nunca deben existir dos execution authorities activas sobre una misma cuenta.

El runtime futuro debe aplicar:

```text
execution lease
+ fencing token/generation
+ account reconciliation
+ one active writer
```

Failover seguro:

```text
failure suspected
  -> current lease expires/revoked
  -> old runtime fenced
  -> account reconciled
  -> new runtime acquires authority
  -> execution may resume under current policy
```

No se activa un backup simplemente porque falta un heartbeat si todavía puede existir autoridad válida del runtime anterior.

## Hosting suspension

Impago de hosting debe preservar capital protection:

```text
HOSTING PAYMENT FAILED
  -> block new trades
  -> keep authorized open-position lifecycle/protection
  -> wait until account FLAT
  -> stop runtime
  -> HOSTING SUSPENDED
```

Billing/Hosting no adquieren autoridad para liquidar posiciones arbitrariamente.

## Native Broker / FCM execution

Provider-specific behavior permanece detrás de adapters y gateways.

Ruta objetivo:

```text
QORE CORE
  -> canonical Core Decision
  -> Distribution / Regional Execution Gateway
  -> Account Guard
  -> Broker Adapter
  -> Broker / FCM API
  -> Venue
```

Adapters futuros pueden usar, cuando estén autorizados y certificados:

- native broker API;
- FIX;
- WebSocket/API;
- MT5/EA bridge;
- otros provider protocols.

Core no importa SDKs/provider-specific protocols por esta arquitectura.

## Regional Futures Execution

Managed Futures constituye una línea de producto distinta.

Principio:

```text
Execution Region = best technical route to broker / FCM / venue
```

No se selecciona región por domicilio del cliente.

La selección futura debe basarse en evidencia técnica como:

- gateway/venue route;
- latency distribution;
- jitter;
- P95/P99;
- packet loss;
- broker ACK;
- execution RTT;
- resilience/failover capability.

El teléfono queda fuera del execution path.

`Managed Futures Execution Infrastructure` no debe reducirse comercialmente al concepto de un VPS.

## Futures economics

Las siguientes cifras son hipótesis de planificación y no contratos de producción:

```text
initial base infrastructure planning capacity ~= USD 2,500/month
Managed Futures hypothesis ~= USD 149/account/month
performance fee hypothesis = 20%
Widget hypothesis = USD 9.99/client/month
```

`USD 149` no debe hardcodearse en un contrato de producción hasta existir una decisión canónica posterior basada en costes, broker/FCM agreements, market data, licensing, regional capacity, redundancy, account density, support, payments, margins y legal/compliance.

## Identity & privacy

Principio:

```text
MINIMUM NECESSARY IDENTITY INFORMATION FOR THE SERVICE
```

Core no almacena pasaportes, selfies ni documentación civil.

EA/Widget deben evitar KYC innecesario cuando el servicio no lo requiera legal/comercialmente.

Servicios managed/broker/FCM pueden requerir verificaciones adicionales fuera de Core. Cuando sea posible se consumen attestations/references opacas en lugar de documentos crudos.

## Product/domain authority matrix

```text
CORE
  strategic trading authority

CLIENT EXECUTION AGENT
  deterministic delegated execution + capital protection

ACCOUNT / PROP POLICY
  account-local policy authority within delegated bounds

CLIENT PERFORMANCE LEDGER
  client performance/economic evidence authority

COMMERCIAL PLATFORM / BILLING
  product, invoice, payment and entitlement authority

CLIENT WIDGET
  presentation only

CORPORATE PROFIT VAULT
  QORE corporate financial projection/ledger authority

MANAGED HOSTING
  runtime-placement/availability authority, never trading strategy
```

Ningún dominio comercial o de presentación puede bypass Risk/Capital Protection ni originar una Core Decision.

## Secuencia arquitectónica recomendada

La implementación futura debe avanzar en este orden lógico, sujeto a una misión explícita y sus Quality Gates:

```text
A. Client & Account Foundation
B. Account & Prop Firm Policy Governance
C. Client Execution Agent Contracts
D. Cryptographic Decision Security
E. Position Lifecycle & Causal Audit
F. Client Performance Accounting
G. Trial & Licensing
H. Commercial Platform
I. Corporate Profit Vault Expansion
J. Client Widget Multi-Account
K. Managed Hosting
L. Native Broker Execution
M. Regional Futures Execution
N. Commercial Futures Validation
```

Las etapas que no dependen de Production o de MISSION-03 #146 pueden desarrollarse en scope no-productivo de manera independiente cuando una misión lo autorice.

Native/live broker evidence, real-money activation y Productive credentials siguen sujetos a gates separados.

## Primera brecha de implementación posterior

Una vez exista una misión no-productiva explícita, la primera brecha concreta es **Client & Account Foundation**.

Debe definir, antes de Agent runtime o billing productivo:

- opaque `ClientId`;
- opaque `TradingAccountId`;
- `1 Client -> N Accounts` relationship;
- account lifecycle/classification;
- account-to-client binding;
- account-scoped product/policy/runtime references;
- invariantes de independencia entre cuentas;
- fail-closed handling de bindings ambiguos/incompletos.

No debe almacenar broker credentials ni identidad civil dentro del Core domain.

## Fronteras explícitamente cerradas

Este entregable no implementa ni autoriza:

- Client Registry runtime;
- Account Registry runtime;
- Client Execution Agent executable;
- MT5 EA;
- signal distribution executable;
- productive cryptographic keys;
- billing/payment runtime;
- client settlement database;
- Corporate Profit Vault accounting runtime;
- native broker/FCM connection;
- Managed Hosting deployment;
- regional Futures infrastructure;
- Production trading;
- real capital;
- MISSION-03 Gate #5 closure;
- MISSION-06 activation.

## Criterio de aceptación arquitectónico

Este entregable queda satisfecho cuando el repositorio establece inequívocamente que:

- no existe new trading action sin Core Decision;
- el Agent ejecuta, pero no crea inteligencia estratégica;
- lifecycle protection puede ser delegado sólo causalmente desde una decisión/policy válida;
- toda acción futura debe tener genealogía y evidencia;
- un cliente puede poseer N cuentas independientes;
- existe una sola execution authority activa por cuenta;
- account/prop policies son versionadas y fail-closed;
- Core Decisions requieren protección criptográfica, expiry y anti-replay;
- Client Performance permanece separado de Corporate Profit;
- performance fee futuro usa verified Eligible Client Paid Profit como base;
- payment evidence no se infiere;
- trial comienza con First Eligible Live Execution verificable;
- impago bloquea nuevas operaciones sin abandonar posiciones existentes;
- Widget es presentation-only y multi-account;
- Hosting es independiente y usa lease/fencing/reconciliation;
- broker/FCM specifics permanecen detrás de adapters;
- Futures se enruta por topología técnica, no domicilio del cliente;
- PII civil no entra en Core;
- Production, MISSION-06 y MISSION-03 #146 permanecen cerrados/bloqueados según su evidencia propia.
