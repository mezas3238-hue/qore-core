# QORE-CEO-COMMAND-CENTER-ARCH-001 — CEO Command Center & CIBO Widget Architecture

## Estado

**ARCHITECTURE DEFINED — IMPLEMENTATION NOT YET AUTHORIZED**

Base verificada al abrir este entregable:

```text
main @ 2024243301fb35f6b849728c088f9ddf6ed33d65
```

Este documento formaliza la arquitectura objetivo del QORE CEO Command Center y del CIBO CEO Widget sin activar QORE Mobile durante MISSION-03, sin introducir una interfaz pública de trading y sin conectar una UI directamente con QORE Core, brokers, providers o credenciales.

MISSION-03 — QORE Real Market Operational Activation permanece activa y su secuencia oficial no cambia. La implementación ejecutable del Control Plane corresponde a una misión posterior de gobierno ejecutivo; la implementación Desktop/iOS/Android del Command Center corresponde a una misión posterior de producto Mobile/Executive Command Center.

## Propósito

Definir una única experiencia ejecutiva multiplataforma para el CEO que permita observar, consultar y gobernar QORE mediante fronteras explícitas, auditables y fail-closed.

El producto objetivo es:

```text
QORE CEO COMMAND CENTER
        │
        ├── Desktop / PC
        ├── iOS
        └── Android
```

Las tres experiencias consumen los mismos contratos ejecutivos y representan el mismo estado autorizado. La presentación puede adaptarse al dispositivo, pero no existen tres modelos de autoridad ni tres fuentes de verdad.

## Principios rectores

El Command Center debe preservar los principios de QORE:

1. **Disciplina** — ninguna acción ejecutiva cruza una boundary sin identidad, autorización, policy y evidencia.
2. **Optimización** — la UI permite observar, comparar y aprender, pero no muta silenciosamente estrategias, traders ni policies.
3. **Escalabilidad** — Desktop, iOS y Android comparten contratos; nuevas superficies no crean rutas paralelas hacia Core.
4. **Fundamento** — toda explicación ejecutiva importante debe poder enlazarse a evidencia estructurada.
5. **Auditabilidad** — toda acción ejecutiva relevante debe dejar una traza reconstruible.
6. **Capital Preservation** — el CEO puede detener o restringir el sistema; ninguna UI puede forzar una operación que haya sido rechazada por las fronteras de trading/risk/capital protection.

> Hoy podemos ser mejores de lo que fuimos ayer.

## Frontera superior

La aplicación del CEO nunca se conecta directamente con QORE Core ni con brokers.

```text
CEO
 │
 ▼
QORE CEO COMMAND CENTER
 │
 ▼
EXECUTIVE CONTROL PLANE
 │
 ▼
AUTHORIZED INTERNAL BOUNDARIES
 │
 ▼
QORE CORE / CIBO / PORTFOLIO / RISK / GOVERNANCE
```

Queda prohibido:

```text
CEO App -> CoreApplication direct call
CEO App -> broker/provider direct call
CEO App -> execution gateway direct call
CEO App -> credential/secret store direct call
CEO App -> order submit/cancel direct call
```

El Control Plane debe ser la única frontera de entrada ejecutiva para queries, commands, notifications y evidence references.

## Separación de dominios

El CEO Command Center puede presentar información procedente de varios dominios corporativos, pero la composición visual no crea dependencias entre esos dominios.

```text
                         CEO COMMAND CENTER
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
        EXECUTIVE CONTROL PLANE         CORPORATE PLANE
                 │                             │
                 ▼                             ▼
              QORE CORE                CLIENT PROFIT VAULT
```

Invariante:

```text
QORE CORE  X  CLIENT PROFIT VAULT
```

Core no conoce el Profit Vault. El Profit Vault no conoce Core, CIBO, estrategias, traders, cuentas del CEO ni decisiones de mercado. El Command Center puede consultar ambos mediante read models separados porque representa al CEO, no porque los backends se acoplen.

## Producto único, superficies adaptadas

### Desktop / PC

La experiencia Desktop es la superficie de máxima densidad y profundidad:

- executive overview;
- panel permanente de CIBO;
- múltiples vistas simultáneas;
- markets;
- traders;
- Validation Lab;
- Trade Forensics;
- Portfolio;
- CEO Accounts;
- Risk / Drawdown;
- News;
- Audit;
- System Health;
- Governance;
- Corporate / Client Profit Vault.

### iOS

La experiencia iOS debe preservar las capacidades ejecutivas esenciales:

- CIBO Widget;
- executive overview;
- alerts / notifications;
- capital and risk state;
- market/trader/portfolio summaries;
- CEO account state;
- audit/evidence drill-down;
- governance/emergency controls;
- corporate Profit Vault view.

### Android

La experiencia Android debe ofrecer el mismo authority model y el mismo estado lógico que iOS:

- CIBO Widget;
- executive overview;
- alerts / notifications;
- capital and risk state;
- market/trader/portfolio summaries;
- CEO account state;
- audit/evidence drill-down;
- governance/emergency controls;
- corporate Profit Vault view.

No se permite que una plataforma móvil tenga más autoridad de trading que otra.

## CIBO CEO Widget

El CIBO CEO Widget es una presencia ejecutiva permanente, no un simple chatbot ni un botón de ayuda.

Debe poder existir en estados visuales como:

- collapsed;
- ambient;
- attention;
- expanded;
- full conversation;
- evidence review;
- critical interruption.

Debe ser accesible desde cualquier módulo del Command Center.

### Interacción

El Widget debe soportar conceptualmente:

- texto;
- voz;
- respuestas visuales estructuradas;
- notificaciones;
- preguntas proactivas de CIBO;
- warnings;
- explanations;
- evidence references;
- contextual navigation hacia el módulo relevante.

La voz y el texto son superficies de interacción; no constituyen autoridad adicional.

### Comunicación bidireccional

El modelo obligatorio es:

```text
CEO -> CIBO
CIBO -> CEO
```

CIBO puede iniciar comunicación cuando exista información suficientemente relevante según una future notification/interruption policy.

### Estados conversacionales de CIBO

Los estados narrativos permitidos pueden incluir:

- CONFIDENT;
- CAUTIOUS;
- UNCERTAIN;
- CONCERNED;
- CRITICAL.

Estos estados no son emociones causales. Son representaciones ejecutivas de evidencia objetiva y deben ser explicables mediante datos, policies, confidence evidence, uncertainty o risk conditions.

## Evidence-backed dialogue

Una afirmación ejecutiva de CIBO no debe terminar en narrativa no verificable.

El flujo objetivo es:

```text
CEO question
   ↓
CIBO structured answer
   ↓
Reason / evidence summary
   ↓
Evidence references
   ↓
Authorized drill-down
```

Ejemplo conceptual:

```text
CEO: ¿Por qué se rechazó esta oportunidad?

CIBO:
- decision: REJECT
- reason: regime mismatch + portfolio correlation
- trader/version: ...
- confidence evidence: ...
- policy versions: ...
- risk verdict: ...
- authorization state: NOT AUTHORIZED
```

La UI puede convertir esa estructura en lenguaje natural, pero la fuente debe ser evidence-backed y auditable.

CIBO no debe exponer chain-of-thought privado. Debe exponer razones estructuradas, evidencia a favor/en contra, incertidumbre, policies y decisiones verificables.

## Niveles de interrupción

La arquitectura debe soportar una policy explícita de interrupción. Estados conceptuales iniciales:

```text
INFORMATION
ATTENTION
IMPORTANT
DECISION_REQUIRED
CRITICAL
```

No son aún thresholds de implementación. Una misión posterior deberá definir los contratos deterministas que gobiernen cuándo una condición entra en cada nivel.

Objetivo: evitar tanto el silencio ante un evento crítico como el ruido continuo de notificaciones de bajo valor.

## Authority model CEO / CIBO

### Autoridad del CEO

El CEO puede, mediante futuras boundaries autorizadas:

- consultar;
- investigar;
- establecer o aprobar políticas de alto nivel;
- restringir scopes;
- pausar;
- detener;
- autorizar misiones o cambios de gobierno;
- revisar evidencia;
- operar emergency governance controls.

### Autoridad operacional de CIBO

CIBO mantiene juicio operacional de trading dentro de sus boundaries y policies. CIBO no es una macro ejecutora del CEO.

El CEO no obtiene un comando equivalente a:

```text
FORCE_BUY
FORCE_SELL
BYPASS_RISK
BYPASS_CAPITAL_PROTECTION
```

Si una oportunidad fue rechazada por CIBO, Portfolio, Risk, Capital Protection o una policy obligatoria, el Command Center no puede convertir el rechazo en una orden forzada.

El CEO conserva autoridad para:

```text
PAUSE
STOP
RESTRICT
REDUCE_AUTHORITY
```

La autoridad de gobierno no implica autoridad para saltarse las fronteras de seguridad operacional.

## Mapa funcional del Command Center

```text
QORE CEO COMMAND CENTER
│
├── HOME
│   ├── Executive Overview
│   ├── CIBO State
│   ├── Capital State
│   ├── Risk State
│   ├── Current Activity
│   ├── Executive Attention
│   └── Corporate Service Summary
│
├── CIBO
│   ├── Conversation
│   ├── Voice
│   ├── Current Judgment
│   ├── Confidence / Uncertainty
│   ├── Concerns
│   ├── Decisions
│   └── Evidence
│
├── MARKETS
│   ├── Market Universe
│   ├── Asset Classes
│   ├── Sessions / Calendars
│   ├── Regimes
│   └── CIBO Assessments
│
├── TRADERS
│   ├── Eligible
│   ├── Operating
│   ├── Restricted
│   ├── Training
│   ├── Suspended
│   └── Trader Evidence / Versions
│
├── VALIDATION LAB
│   ├── Candidates
│   ├── Validation Runs
│   ├── Stress / Robustness
│   ├── Optimization Evidence
│   └── Certification State
│
├── TRADE FORENSICS
│   ├── Trade Cases
│   ├── Valid Wins / Losses
│   ├── Process Findings
│   ├── Weekly Reviews
│   └── Historical Cases
│
├── PORTFOLIO
│   ├── Positions
│   ├── Exposure
│   ├── Correlation
│   └── Allocation
│
├── CEO ACCOUNTS
│   ├── Account State
│   ├── Balance / Equity
│   ├── Realized / Unrealized Performance
│   ├── Drawdown
│   ├── Margin / Exposure
│   └── Current Positions
│
├── RISK / CAPITAL PROTECTION
│   ├── State
│   ├── Drawdown
│   ├── Risk Budget
│   ├── Defensive Modes
│   └── Emergency State
│
├── NEWS
│   ├── Economic Events
│   ├── Impact
│   └── CIBO Assessments
│
├── AUDIT
│   ├── Decisions
│   ├── Actions
│   ├── Evidence
│   ├── Policy Versions
│   ├── Incidents
│   └── Audit Packages
│
├── SYSTEM
│   ├── Core Health
│   ├── CIBO Health
│   ├── Provider Health
│   ├── Runtime Health
│   └── Infrastructure Health
│
├── GOVERNANCE
│   ├── Pause
│   ├── Stop
│   ├── Restrictions
│   ├── Policies
│   ├── Mission State
│   └── Emergency Controls
│
└── CORPORATE
    └── CLIENT PROFIT VAULT
        ├── Overview
        ├── Client Ledgers
        ├── Positive Client Ledgers
        ├── Negative Client Ledgers
        ├── Evaluation / Verification / Reward-Eligible States
        ├── Monthly Settlements
        ├── Profit Share Receivable
        ├── Collected / Outstanding
        ├── Active Entitlements
        ├── Payment Due / Grace
        ├── Signal Suspensions / Reactivations
        └── Commercial Audit
```

Este mapa define intención de producto, no contratos ejecutables ya existentes.

## Separación: CEO financial performance vs Client Profit Vault

Nunca se agregan como si fueran la misma naturaleza económica.

### CEO Accounts / CEO Performance

Representa exclusivamente capital y cuentas propiedad/control del CEO.

Puede incluir:

- account state;
- balance;
- equity;
- realized PnL;
- unrealized PnL;
- drawdown;
- open risk;
- margin;
- positions;
- consolidated proprietary performance.

### Client Profit Vault

Representa exclusivamente el ledger económico del servicio cliente.

No representa capital propietario del CEO.

Debe poder mostrar de forma agregada:

- total de client ledgers;
- clientes/ledgers con resultado positivo;
- clientes/ledgers con resultado negativo;
- break-even;
- positive realized total;
- negative realized total;
- billable eligible profit;
- profit-share receivable;
- collected;
- outstanding;
- paid/pending/past-due states;
- active/grace/suspended entitlements;
- monthly history;
- commercial audit.

El porcentaje comercial actualmente definido como intención de producto es 20% sobre beneficio positivo elegible. La fórmula contractual exacta, high-water mark/loss carryforward, costs, payout eligibility, cutoff, dispute handling y settlement semantics deben formalizarse en un contrato del Profit Vault antes de implementación financiera productiva.

## Profit Vault privacy boundary

El Profit Vault debe utilizar identidades opacas, por ejemplo:

```text
SettlementLedgerId
EntitlementId
EAInstanceId
```

No necesita conocer:

- nombre real del cliente;
- número real de cuenta;
- balance completo de la cuenta;
- equity;
- drawdown operativo;
- posiciones;
- CIBO;
- estrategias;
- traders;
- decisiones de mercado.

El CEO Command Center puede presentar un ledger autorizado sin convertir esa identidad opaca en una dependencia desde Core.

## Account phase visibility for funded-account services

El Corporate / Profit Vault view debe soportar fases normalizadas de servicio sin asumir que todas las prop firms usan la misma terminología.

Conceptualmente:

```text
EVALUATION
VERIFICATION
REWARD_ELIGIBLE
PAYOUT_ELIGIBLE
SUSPENDED
UNKNOWN
```

Los resultados positivos/negativos de Evaluation o Verification pueden conservarse como historial no facturable. La obligación de profit share sólo puede generarse cuando la policy contractual y la fase de cuenta permitan beneficio económicamente elegible.

No se debe inferir `REAL` como condición universal de facturación: la elegibilidad depende del programa, policy version y condiciones económicas verificadas.

## Seguridad del Command Center

La implementación futura debe contemplar como mínimo:

- authenticated CEO identity;
- device/session security;
- explicit authorization scope;
- least privilege;
- replay protection para commands;
- command identity;
- policy/version binding;
- immutable audit evidence para acciones relevantes;
- no secret material en UI payloads;
- no provider credentials en Mobile/Desktop;
- no direct broker session en el Command Center;
- fail-closed ante identity, authorization o state ambiguity.

Los mecanismos concretos de autenticación, biometría, hardware-backed keys, token lifetime y secure storage se decidirán en la misión de Control Plane / Mobile Security correspondiente.

## Command model

La futura API ejecutiva debe separar al menos:

```text
QUERY
COMMAND
SUBSCRIPTION
EVIDENCE_REQUEST
```

Un query no muta estado.

Un evidence request no muta estado.

Una subscription no concede autoridad de command.

Un command debe requerir identidad, scope, policy, preconditions y audit record.

## Emergency controls

El Command Center podrá exponer emergency controls sólo detrás de contracts explícitos del Control Plane.

El objetivo es permitir acciones de protección, no creación improvisada de trades.

Ejemplos de intención permitida:

```text
PAUSE_SYSTEM
STOP_NEW_TRADING
RESTRICT_MARKET
RESTRICT_ACCOUNT
REDUCE_OPERATIONAL_AUTHORITY
```

La semántica exacta y sus preconditions se definirán en contratos posteriores. Este documento no crea implementaciones ni bypasses.

## Estado compartido entre Desktop y Mobile

Desktop, iOS y Android deben proyectar el mismo estado lógico autorizado.

Un cambio observado en una superficie debe poder verse en las otras después de la sincronización autorizada del Control Plane.

No se permite una cache local que se convierta en fuente de verdad para governance.

La UI debe distinguir estado actual, estado stale y estado unavailable. Ante incertidumbre, acciones sensibles fallan cerrado.

## CIBO context continuity

La conversación del CEO puede continuar entre Desktop, iOS y Android mediante un contexto ejecutivo estructurado y autorizado.

El contexto no debe depender de mantener una única app abierta y no debe almacenar secretos, chain-of-thought privado o autoridad implícita en el dispositivo.

## Notificaciones

Las notificaciones deben identificar su dominio de origen, por ejemplo:

```text
CIBO / CORE
RISK
SYSTEM
CORPORATE / PROFIT VAULT
GOVERNANCE
```

Una notificación puede informar o llevar al usuario a una pantalla autorizada, pero no debe ejecutar una operación de trading por sí sola.

## Read models

El Command Center debe preferir read models específicos en lugar de exponer object graphs internos del Core.

Objetivo:

```text
internal domain state
      ↓
controlled projection
      ↓
executive read model
      ↓
Desktop / iOS / Android
```

Esto permite evolucionar la UI sin convertir contratos internos en API pública accidental.

## Auditoría

Toda acción ejecutiva importante debe poder reconstruir:

```text
WHO
WHEN
DEVICE / SESSION
COMMAND
REASON
POLICY VERSION
PRECONDITIONS
AUTHORIZATION
RESULT
RESULT EVIDENCE
```

Una corrección de evidencia no sobrescribe silenciosamente historia; se registra como evento/record posterior referenciando el original cuando corresponda.

## Fronteras explícitamente cerradas por este entregable

Este documento no autoriza ni implementa:

- QORE Mobile ejecutable;
- CEO Widget ejecutable;
- Control Plane ejecutable;
- public API;
- direct Core access from UI;
- broker/provider access from UI;
- credential exposure;
- real-money authorization;
- Production trading;
- CEO forced trading override;
- autonomous corrective trading;
- Profit Vault implementation;
- client billing implementation;
- payment processing;
- client identity storage inside Profit Vault;
- client EA implementation;
- client widget implementation.

## Relación con la hoja de ruta

Este entregable es arquitectura preparatoria y no altera el estado de MISSION-03.

La secuencia objetivo posterior permanece:

```text
MISSION-03
QORE Real Market Operational Activation
        ↓
MISSION-04
QORE Control Plane & Executive Governance
        ↓
MISSION-05
QORE Mobile & CEO Command Center
        ↓
MISSION-06
QORE Production Trading Readiness
        ↓
separate PRODUCTION AUTHORIZATION
```

La numeración/nombre exacto de una misión futura sólo se considera oficial cuando sea integrada explícitamente en el repositorio mediante su deliverable de apertura.

## Entregables derivados recomendados

Este documento deja preparados los siguientes trabajos futuros, sujetos a apertura formal y orden de misión:

1. `QORE-EXECUTIVE-CONTROL-PLANE-001` — Executive Query/Command Boundary.
2. `QORE-CEO-IDENTITY-AUTHORITY-001` — CEO Identity, Sessions & Authority Contracts.
3. `QORE-CIBO-EXECUTIVE-DIALOGUE-001` — Evidence-Backed CIBO Dialogue Contracts.
4. `QORE-EXECUTIVE-NOTIFICATIONS-001` — Interruption & Notification Policy Contracts.
5. `QORE-EXECUTIVE-AUDIT-001` — Executive Action Audit Contracts.
6. `QORE-CEO-GOVERNANCE-CONTROLS-001` — Pause/Stop/Restriction Governance Contracts.
7. `QORE-CEO-READ-MODELS-001` — Stable Executive Projection Contracts.
8. `QORE-CEO-DESKTOP-001` — Desktop Command Center.
9. `QORE-CEO-IOS-001` — iOS Command Center.
10. `QORE-CEO-ANDROID-001` — Android Command Center.
11. `QORE-CIBO-WIDGET-001` — Cross-platform CIBO CEO Widget.
12. `QORE-CORPORATE-PROFIT-VAULT-VIEW-001` — Isolated Corporate Profit Vault read model.

Client EA, Client Widget, Profit Vault settlement engine and entitlement architecture remain separate deliverable families and must not be implemented inside QORE Core merely because the CEO Command Center can display their authorized read models.

## Criterio de aceptación arquitectónico

Este entregable se considera satisfecho cuando el repositorio establece inequívocamente que:

- existe un único CEO Command Center conceptual para Desktop, iOS y Android;
- el CIBO Widget es permanente y evidence-backed;
- Mobile/Desktop nunca acceden directamente a Core o brokers;
- Executive Control Plane es la frontera obligatoria;
- CEO governance y CIBO operational judgment tienen autoridades distintas;
- no existe forced-trade override;
- CEO proprietary financial performance y Client Profit Vault permanecen separados;
- Profit Vault puede presentarse al CEO sin conectarse a Core;
- el Command Center distingue dominios de notificación y evidencia;
- toda futura acción sensible es autenticada, autorizada y auditable;
- MISSION-03 permanece sin alteración operacional;
- la implementación queda diferida a las misiones de Control Plane y Mobile correspondientes.
