# QORE-CLIENT-EXECUTION-EXPERIENCE-ARCH-001 — Client Execution Agent & Mobile Widget Architecture

## Estado

**ARCHITECTURE DEFINED — IMPLEMENTATION NOT YET AUTHORIZED**

Base verificada al abrir este entregable:

```text
main @ e4e47b81d35e8e735841a8e4ad76404acf89cfa6
```

Este documento formaliza la arquitectura objetivo del producto cliente sin introducir implementación ejecutable dentro de QORE Core.

## Propósito

Definir un producto cliente simple, seguro y escalable compuesto por:

```text
QORE CLIENT EXECUTION AGENT
        +
QORE CLIENT MOBILE APP / WIDGET
```

El agente ejecuta y protege la cuenta local del cliente. La experiencia móvil es observacional y read-only.

## Invariante principal

```text
CLIENT OBSERVES
AGENT GOVERNS LOCAL EXECUTION
CORE PUBLISHES INTELLIGENCE
```

El cliente no configura la lógica operativa, de riesgo o ejecución del agente.

## Separación respecto de QORE Core

QORE Core no conoce:

- identidad del cliente;
- número de cuenta;
- balance;
- equity;
- drawdown;
- posiciones;
- broker local;
- si una señal fue ejecutada o rechazada;
- resultado final de la operación.

El Client Execution Agent no conoce:

- internals de CIBO;
- traders virtuales;
- Validation Lab;
- cuentas del CEO;
- estrategias internas no publicadas;
- otros clientes.

La intersección de trading entre ambos dominios es exclusivamente un protocolo de señal unidireccional autorizado.

```text
QORE CORE
   │
   │ signed/coded signal
   ▼
SIGNAL DISTRIBUTION
   │
   ▼
CLIENT EXECUTION AGENT
   │
   ▼
CLIENT ACCOUNT
```

No existe callback de ejecución hacia Core.

## Concepto general de Agent

`EA` es una implementación específica de plataforma. El concepto superior es:

```text
QORE Client Execution Agent
```

Posibles implementaciones futuras:

- MetaTrader 5 EA;
- MetaTrader 4 EA;
- cTrader cBot;
- NinjaTrader Agent;
- Sierra Chart Agent;
- Interactive Brokers Agent;
- exchange/crypto adapter agent;
- future supported execution environments.

La arquitectura no debe asumir una sola plataforma.

## Open Broker Compatibility

Core no necesita poseer ni operar una cuenta en el broker del cliente.

El agente es responsable de resolver localmente:

```text
canonical instrument
      ↓
local platform symbol
      ↓
contract specification
      ↓
account capability
      ↓
local policy / risk
      ↓
execution eligibility
```

La ausencia de un broker en las cuentas del CEO no bloquea automáticamente el servicio cliente.

El requisito es que el entorno local sea soportado y suficientemente certificable por el Client Agent.

Si no puede clasificarse de forma segura:

```text
ACCOUNT / ENVIRONMENT = UNRESOLVED
NEW TRADING = BLOCKED
```

## Account discovery

El Client Agent debe poder descubrir, cuando la plataforma lo permita:

- platform;
- broker/provider/server identity;
- account environment;
- account type;
- local symbols;
- contract specifications;
- tick size/value;
- lot/quantity constraints;
- margin/leverage capabilities;
- stop/freeze constraints;
- trading hours;
- execution capabilities.

No debe inferir una policy de prop firm sólo por nombre parcial, región o una suposición comercial.

## Account Governance Profile

La operación cliente requiere un profile local suficientemente resuelto.

Conceptualmente:

```text
AccountGovernanceProfile
=
provider/broker
+ platform
+ program/account class
+ account phase
+ policy version
+ execution constraints
+ capital/risk rules
```

La policy efectiva debe ser versionada y verificable.

Ante policy desconocida/incompleta para una regla obligatoria:

```text
FAIL CLOSED
```

## Funded-account phases

El agente debe conocer la fase normalizada de una cuenta de fondeo cuando ese servicio esté soportado.

Estados conceptuales:

```text
EVALUATION
VERIFICATION
REWARD_ELIGIBLE
PAYOUT_ELIGIBLE
SUSPENDED
UNKNOWN
```

Una prop firm puede usar otros nombres. El agente debe mapearlos a un estado normalizado mediante policy/evidence, no por heurística insegura.

La fase influye en:

- reglas de trading;
- límites de pérdida/DD;
- objetivos aplicables;
- restricciones de noticias/overnight/weekend;
- condiciones de elegibilidad económica para settlement.

## Signal processing pipeline

El pipeline local objetivo es:

```text
Signal received
      ↓
authenticity
      ↓
freshness / expiry
      ↓
anti-replay / sequence
      ↓
routing compatibility
      ↓
service entitlement
      ↓
account classification
      ↓
account policy
      ↓
local market/instrument mapping
      ↓
local risk
      ↓
margin/exposure/spread checks
      ↓
position sizing
      ↓
SL/TP/trailing translation
      ↓
EXECUTE or REJECT
```

Core no recibe el resultado de este pipeline.

## Local Risk

El Client Agent debe aplicar protección local incluso si el broker no impone reglas equivalentes.

Debe poder contemplar mediante policies futuras:

- daily loss;
- maximum drawdown;
- balance/equity semantics;
- trailing/static DD semantics;
- open risk;
- total exposure;
- correlation;
- simultaneous position limits;
- margin/leverage;
- spread/slippage conditions;
- instrument restrictions;
- news restrictions;
- provider/platform health.

La implementación exacta pertenece a contratos posteriores.

## Zero Client Configuration

El Client Execution Agent será `Zero Client Configuration` para toda lógica operativa.

El usuario no podrá configurar manualmente:

- strategy;
- risk percentage;
- lot multiplier;
- confidence threshold;
- SL logic;
- TP logic;
- trailing logic;
- news filters;
- session filters;
- correlation rules;
- account-policy rules;
- signal-routing logic;
- execution bypasses.

## No configurable != no adaptable

El agente sí puede autoconfigurarse de forma gobernada a partir de:

- certified account policy;
- certified platform capabilities;
- signed configuration/policy package;
- verified account phase;
- local contract specifications;
- signed agent version.

La adaptación es automática y policy-driven; no es user-defined behavior.

## Integrity and tamper response

El producto futuro debe contemplar:

- signed builds;
- version identity;
- integrity verification;
- license/instance binding;
- anti-tamper evidence cuando sea viable;
- signed policy packages;
- signed protocol versions;
- controlled upgrades.

No se debe afirmar que software ejecutado en un entorno controlado por el cliente es absolutamente invulnerable.

Ante una falla de integridad significativa:

```text
NO NEW TRADING
```

La protección de posiciones ya abiertas debe continuar en la medida permitida por el runtime/plataforma.

## Safe update principle

Las actualizaciones no deben convertir una posición abierta en exposición desprotegida.

Secuencia objetivo:

```text
update pending
      ↓
pause eligibility for new signals if required
      ↓
keep existing protection active
      ↓
verify signed compatible update
      ↓
activate new version
      ↓
restore new-signal eligibility
```

## Mobile-first client experience

El cliente puede poseer únicamente un teléfono.

El producto no debe requerir que el teléfono sea el runtime permanente del agente.

La arquitectura distingue:

```text
MOBILE EXPERIENCE
       !=
EXECUTION RUNTIME
```

El Agent puede vivir en una plataforma/routing runtime persistente compatible mientras el teléfono actúa como consola observacional.

## QORE Client Mobile App

La app cliente debe soportar al menos:

```text
iOS
Android
```

No es una plataforma de trading completa.

Su función principal es autenticar al cliente para su propia instancia y presentar el estado producido por su Client Agent.

## QORE Client Widget

El widget es deliberadamente pequeño.

Información objetivo:

- account/agent state;
- account balance;
- realized result today;
- realized result current week;
- recent trade pulse.

Trade pulse puede incluir:

- timestamp;
- instrument/pair;
- direction cuando la policy de producto lo permita;
- closed result positivo/negativo;
- optional active/closed state si se autoriza posteriormente.

Ejemplo conceptual:

```text
QORE
Account: ACTIVE

Balance       ...
Today         ...
Week          ...

PULSE
14:32 EURUSD BUY   +...
11:47 GBPUSD SELL  -...
09:18 EURUSD BUY   +...
```

## Widget is read-only

El widget no ofrece:

```text
BUY
SELL
CLOSE
MODIFY LOT
MOVE SL
MOVE TP
CHANGE RISK
CHANGE STRATEGY
DISABLE PROTECTION
```

La app/widget no adquiere autoridad de trading por estar autenticada.

## Status Relay

Como el Agent puede ejecutarse en un runtime distinto al teléfono, se define conceptualmente un `QORE Client Status Relay`.

```text
CLIENT AGENT
    │
    │ authenticated status snapshot
    ▼
STATUS RELAY
    │
    ▼
CLIENT APP / WIDGET
```

El Status Relay:

- transporta estado observacional;
- no recibe señales de Core;
- no envía órdenes al Agent;
- no modifica risk/policies;
- no modifica posiciones;
- no conoce CIBO internals;
- no es source of truth de trading.

## ClientStatusSnapshot

El read model mínimo futuro puede incluir conceptualmente:

```text
schema_version
agent_instance_id
timestamp
agent_state
account_state
balance
today_realized_pnl
week_realized_pnl
recent_trade_pulse
```

La implementación deberá definir tipos, currency semantics, timezone/cutoff y freshness explícitos.

No se deben incluir credenciales de broker ni secretos de señal.

## Data minimization

El Widget sólo recibe los datos necesarios para la experiencia definida.

No necesita:

- account credentials;
- CIBO evidence;
- trader identities;
- strategy versions;
- Core market analysis;
- other client data;
- Profit Vault settlement history completo;
- internal risk algorithms.

## Separation from Profit Vault

El mismo Agent puede producir dos salidas externas completamente separadas:

```text
CLIENT AGENT
    │
    ├── status snapshot ──────> STATUS RELAY -> CLIENT WIDGET
    │
    └── settlement event ─────> CLIENT PROFIT VAULT
```

El Status Relay y Profit Vault no necesitan conocerse.

El Client Widget no consulta Profit Vault para construir balance, today, week o trade pulse.

## Separation from Core

El Client Widget nunca se conecta con Core.

```text
CLIENT WIDGET X QORE CORE
CLIENT WIDGET X CIBO
CLIENT WIDGET X CORE CONTROL PLANE
```

Su fuente funcional es exclusivamente el status feed autorizado de su Client Agent.

## Existing-position protection after service loss

Si el entitlement del servicio expira o no se renueva:

```text
NEW SIGNALS = BLOCKED
EXISTING POSITION PROTECTION = REMAINS ACTIVE
```

El producto comercial no debe utilizar una suspensión de servicio para retirar SL, TP, trailing o protecciones locales de una posición existente.

## Account-state concepts for the Widget

La UI puede representar estados normalizados como:

```text
ACTIVE
PROTECTED
TRADING_BLOCKED
POLICY_UNRESOLVED
ENTITLEMENT_EXPIRED
AGENT_OFFLINE
STALE
UNAVAILABLE
```

Los nombres definitivos serán contratos futuros.

La UI debe distinguir claramente `no new trading` de `agent unavailable` y de `account unsupported`.

## Security of mobile read model

La implementación futura debe considerar:

- authenticated client identity/instance binding;
- device/session security;
- encrypted transport;
- replay protection;
- snapshot freshness;
- authorization limited to the client's own instance;
- no cross-ledger/account data access;
- revocable mobile session;
- minimal local storage.

## Non-operational client settings

La app puede permitir preferencias de experiencia que no alteren trading, por ejemplo:

- language;
- notification preference;
- biometric access;
- appearance;
- support/contact options.

Estas preferencias no pueden modificar policies operativas del Agent.

## Auditability

El Agent debe poder producir localmente o hacia boundaries autorizadas evidencia suficiente para reconstruir:

```text
signal received
routing decision
signature/freshness decision
entitlement state
account policy version
local risk verdict
sizing decision
execution/rejection
broker/platform response
position protection state
```

Esa evidencia no se envía a Core automáticamente.

## Fronteras explícitamente cerradas por este entregable

Este documento no implementa ni autoriza:

- Client Agent executable;
- MT4/MT5/cTrader concrete code;
- client mobile application;
- iOS widget;
- Android widget;
- Status Relay executable;
- signal distribution executable;
- Profit Vault executable;
- billing/payment processing;
- productive credentials;
- real capital authorization;
- a user-configurable trading engine;
- callback/reconciliation from client account to Core.

## Relación con QORE CEO Command Center

El Client product es distinto del CEO product.

```text
QORE CEO COMMAND CENTER
    governance / CIBO / proprietary operations / corporate oversight

QORE CLIENT APP / WIDGET
    own account status / balance / today / week / pulse
```

No se reutiliza el CEO Command Center como app cliente.

## Entregables derivados recomendados

1. `QORE-CLIENT-SIGNAL-PROTOCOL-001` — Signed/Coded Signal Contract.
2. `QORE-CLIENT-ACCOUNT-GOVERNANCE-001` — Local Account Classification & Policy Contracts.
3. `QORE-CLIENT-LOCAL-RISK-001` — Local Capital Protection Contracts.
4. `QORE-CLIENT-ENTITLEMENT-001` — Local Service Entitlement Validation.
5. `QORE-CLIENT-AGENT-INTEGRITY-001` — Signed Version & Integrity Contracts.
6. `QORE-CLIENT-STATUS-RELAY-001` — Read-only Status Snapshot Boundary.
7. `QORE-CLIENT-WIDGET-001` — Cross-platform Client Widget Read Model.
8. `QORE-CLIENT-IOS-001` — iOS Client Experience.
9. `QORE-CLIENT-ANDROID-001` — Android Client Experience.
10. platform-specific execution agent adapters only after explicit platform certification.

Profit settlement, 20% billing semantics and payment/entitlement issuance remain separate Profit Vault deliverables.

## Criterio de aceptación arquitectónico

Este entregable queda satisfecho cuando el repositorio establece inequívocamente que:

- Client Agent es conceptualmente independiente de Core;
- Core no necesita operar el broker del cliente;
- el Agent clasifica localmente cuenta/plataforma/policy;
- account/policy uncertainty fails closed;
- funded-account phases are explicit;
- el cliente no configura lógica de trading/risk/execution;
- signed/certified automatic adaptation sigue siendo posible;
- el producto es mobile-first sin exigir que el teléfono sea el execution runtime;
- iOS y Android reciben un read-only Client Widget;
- el Widget muestra únicamente estado, balance, día, semana y trade pulse;
- Status Relay es observacional y no controla trading;
- Widget no habla con Core ni Profit Vault;
- Profit Vault recibe settlement events por una boundary separada;
- entitlement expiration bloquea nuevas señales sin retirar protección de posiciones existentes;
- ninguna implementación productiva queda autorizada por este documento.
