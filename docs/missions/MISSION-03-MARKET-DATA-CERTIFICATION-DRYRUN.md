# MISSION-03 — Market Data Certification Dry-Run

## Estado

**AUXILIARY PREPARATION — NOT OPERATIONAL CERTIFICATION**

Este documento registra un ensayo determinístico end-to-end de la ruta de market data ya integrada para OANDA v20 fxTrade Practice.

No abre, completa ni certifica `QORE-MARKET-DATA-CERTIFICATION-001`.

La certificación operacional oficial continúa bloqueada hasta que exista evidencia externa real y autenticada de OANDA Practice producida por el workflow manual ya integrado.

## Objetivo

Reducir el riesgo del futuro gate operacional comprobando ahora que una ventana representativa puede atravesar, sin rutas paralelas:

```text
OANDA-like deterministic wire fixture
        |
        v
ConcreteBearerHttpsExternalTransport
        |
        v
ReadOnlyExternalProviderAdapter
        |
        v
OandaPracticeMarketDataDecoder
        |
        v
ExternalQuotePayload / ExternalOhlcPayload
        |
        v
MarketDataIngestionFlow
        |
        v
QuoteSnapshot / OhlcSnapshot
        |
        v
MarketDataCertificationPreparationPolicy
        |
        v
MarketDataCertificationPreparationReport
```

El dry-run usa exactamente los componentes productivos existentes. Solo el transporte externo es sustituido por un boundary determinístico inyectado en test.

## Alcance

La ventana positiva cubre:

- `EUR_USD`;
- `GBP_USD`;
- quote bid/ask para ambos símbolos;
- dos candles M15 contiguas para cada símbolo;
- timestamps timezone-aware;
- source identity única;
- snapshots canónicos con identidades explícitas;
- bearer authentication inyectada únicamente en el HTTPS boundary;
- endpoint Practice exacto;
- certification-preparation sin findings.

La ventana negativa cubre una quote válida en wire-format y normalización canónica, pero stale para la policy de certificación. El resultado esperado es `QUOTE_STALE` después de atravesar decoder e ingestion.

También se valida que un payload OANDA estructuralmente inválido falle antes de que exista un snapshot canónico elegible para certificación.

## Lo que este trabajo demuestra

Demuestra determinísticamente que:

1. la configuración Practice READ_ONLY puede componerse usando los boundaries existentes;
2. las credenciales de test permanecen fuera de requests públicas y resultados de certificación;
3. quote y OHLC OANDA-like atraviesan el decoder existente;
4. `MarketDataIngestionFlow` continúa siendo la única normalización hacia contratos canónicos;
5. el harness de preparación consume exclusivamente `QuoteSnapshot` y `OhlcSnapshot`;
6. una ventana limpia EUR_USD/GBP_USD M15 produce un reporte `is_prepared=True`;
7. una quote stale puede ser válida para decoder/ingestion y aun así ser rechazada por la policy de certificación;
8. malformed wire data falla antes de entrar a la ventana canónica;
9. no se introduce un segundo market-data path;
10. no se requiere Internet para este ensayo.

## Lo que este trabajo NO demuestra

No demuestra:

- que OANDA esté accesible ahora;
- que las credenciales reales Practice estén activas;
- que el account ID real sea válido;
- que una llamada TLS haya alcanzado OANDA;
- latencia real de red;
- freshness real del provider;
- ordering real entre múltiples respuestas externas;
- gaps reales de mercado;
- comportamiento real de reconnect/throttling;
- certificación operacional de market data;
- autorización de DEMO execution;
- autorización Production;
- autorización de capital real.

Por tanto:

```text
dry-run prepared
    !=
real provider evidence
    !=
operational market-data certification
```

## Invariantes preservados

- `CoreApplication` continúa provider-free.
- No se modifica `EventBus`.
- No se modifica `RuntimePlan`.
- No se modifica `RuntimeSnapshot`.
- No se modifica `RuntimeHealth`.
- No se añade Production endpoint.
- No se añade orden ni ejecución.
- No se añade retry o reconnect ejecutable.
- No se añade `sleep`, scheduler o thread.
- No se añade network IO en CI.
- No se añade secret material al repositorio.
- El material secreto fake utilizado por test no aparece en el reporte de preparación.
- El endpoint verificado por el test es únicamente `api-fxpractice.oanda.com`.

## Relación con preparaciones anteriores

Este dry-run integra las piezas ya preparadas:

- `QORE-MARKET-DATA-CERTIFICATION-PREP-001` aporta la policy y el reporte sequence-level;
- `QORE-OANDA-MARKET-DATA-REJECTION-MATRIX-001` cubre rechazo exhaustivo del decoder;
- `QORE-HISTORICAL-OHLC-PLANNING-001` define cómo producir requests históricos canónicos en ventanas futuras;
- `QORE-OANDA-PRACTICE-EVIDENCE-AUDIT-001` auditará el artifact real del probe cuando OANDA vuelva.

Este entregable auxiliar añade la prueba de composición entre provider wire, canonical ingestion y preparation harness.

## Gate que permanece pendiente

`QORE-LIVE-MARKET-FEED-ACTIVATION-001` sigue requiriendo:

1. disponibilidad real de OANDA Practice;
2. secrets externos válidos en GitHub Actions;
3. ejecución manual del workflow `QORE OANDA Practice Market Feed Probe` desde `main`;
4. artifact sanitizado exitoso;
5. auditoría del artifact mediante los criterios ya integrados.

Solo después de esa evidencia se puede cerrar operacionalmente el entregable #5 y abrir formalmente `QORE-MARKET-DATA-CERTIFICATION-001`.

## Quality Gate

Este trabajo debe pasar sin reducción de strictness:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

Un CI verde valida el dry-run determinístico, no sustituye el probe externo real.
