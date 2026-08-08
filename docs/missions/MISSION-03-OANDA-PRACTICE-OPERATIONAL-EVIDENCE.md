# QORE-LIVE-MARKET-FEED-ACTIVATION-001 — OANDA Practice Operational Evidence

## Estado

**IMPLEMENTATION READY — EXTERNAL EVIDENCE REQUIRED**

Este documento define el último gate operacional de `QORE-LIVE-MARKET-FEED-ACTIVATION-001`.

La implementación de market data OANDA Practice ya existe en `main`. Este gate no vuelve a demostrar composición determinista: ejecuta una única lectura autenticada contra el proveedor externo real y conserva evidencia sanitizada de que el resultado atravesó el flujo canónico de QORE.

## Frontera autorizada

Únicamente se autoriza:

```text
https://api-fxpractice.oanda.com
```

con:

```text
Provider: oanda-v20
Environment: DEMO
Operation: one read-only pricing request
Approved instruments: EUR_USD, GBP_USD
```

Permanecen cerrados:

- `api-fxtrade.oanda.com`;
- `stream-fxtrade.oanda.com`;
- cuentas OANDA live/production;
- capital real;
- órdenes o posiciones;
- depósitos o retiros;
- credenciales productivas;
- cualquier bypass de governance/safety.

## Workflow operacional

Workflow manual:

```text
.github/workflows/oanda-practice-market-feed.yml
```

No tiene trigger por `push`, `pull_request`, `schedule` ni ejecución recurrente. Solo puede ejecutarse mediante `workflow_dispatch`.

El workflow acepta únicamente un `instrument` de choice cerrado:

```text
EUR_USD
GBP_USD
```

No acepta host, environment, account type ni production mode como inputs.

## Secret bindings requeridos

El workflow consume dos bindings externos de GitHub Actions:

```text
QORE_OANDA_PRACTICE_ACCOUNT_ID
QORE_OANDA_PRACTICE_TOKEN
```

Se recomienda configurar ambos como **GitHub Actions repository secrets** para evitar publicar el account ID en un repositorio público, aunque el contrato QORE no clasifica `account_ref` como secret material.

El token no debe aparecer nunca en:

- archivos del repositorio;
- commits;
- PRs o issues;
- workflow inputs;
- logs;
- telemetry;
- artifacts;
- metadata pública;
- `repr` / `str`;
- `logical_values()`.

## Flujo de ejecución

```text
GitHub Actions secret bindings
    → OandaPracticeOperationalProbeInputs
    → Practice-only runtime configuration
    → supervised READ_ONLY activation
    → OandaPracticeCredentialActivation
    → ConcreteBearerHttpsExternalTransport
    → api-fxpractice.oanda.com
    → OANDA pricing JSON
    → OandaPracticeMarketDataDecoder
    → ExternalQuotePayload
    → MarketDataIngestionFlow
    → QuoteSnapshot
    → sanitized operational evidence JSON
```

El `Authorization: Bearer ...` se construye únicamente dentro del último transport boundary y nunca forma parte de `ExternalTransportRequest`.

## Evidencia sanitizada

En caso de éxito el workflow genera:

```text
artifacts/oanda-practice-market-feed-evidence.json
```

y lo sube como GitHub Actions artifact.

El JSON puede contener:

- schema de evidencia;
- status `success`;
- `run_key`;
- provider key;
- environment `demo`;
- Practice endpoint host;
- fingerprint SHA-256 truncado de la cuenta;
- instrument;
- canonical snapshot ID;
- provider `observed_at`;
- bid;
- ask.

El JSON no puede contener:

- account ID completo;
- token;
- Authorization header;
- secret reference material;
- production endpoint.

## Criterio de éxito operacional

`QORE-LIVE-MARKET-FEED-ACTIVATION-001` podrá declararse **OPERATIONALLY COMPLETED** únicamente cuando exista un run real de este workflow que cumpla simultáneamente:

1. workflow ejecutado manualmente desde `main`;
2. secret bindings presentes;
3. conexión TLS al host Practice aprobado;
4. respuesta HTTP exitosa autenticada;
5. payload OANDA válido;
6. instrument solicitado exactamente coincidente;
7. price marcado `tradeable=true`;
8. timestamp provider parseable y timezone-aware;
9. bid/ask positivos y `bid <= ask`;
10. `MarketDataIngestionFlow` produzca `QuoteSnapshot` canónico;
11. artifact sanitizado exista;
12. ningún secreto aparezca en logs o artifact.

Un run que falle por secret ausente, autenticación, network, payload, tradeability, timestamp o normalización **no** constituye evidencia operacional exitosa.

## Consecuencia para QORE-MARKET-DATA-CERTIFICATION-001

`QORE-MARKET-DATA-CERTIFICATION-001` solo debe abrirse como certificación operacional después de obtener y auditar un artifact exitoso de este gate.

La certificación posterior podrá evaluar, entre otros:

- identidad de provider/environment;
- integridad de instrument mapping;
- timestamp/freshness;
- bid/ask invariants;
- repetibilidad controlada;
- OHLC cuando corresponda;
- ausencia de secret leakage;
- continuidad de la única ruta de ingestión canónica.

Hasta entonces MISSION-03 permanece fail-closed respecto de cualquier afirmación de conexión operacional certificada.
