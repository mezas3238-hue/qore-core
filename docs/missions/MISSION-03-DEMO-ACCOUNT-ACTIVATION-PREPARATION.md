# QORE-DEMO-ACCOUNT-ACTIVATION-PREPARATION-001 — OANDA Practice Demo Account Preparation

## Estado

**PREPARATION READY — EXTERNAL OANDA PRACTICE ACCOUNT STILL REQUIRED**

Este entregable prepara la frontera determinística del Gate #7 de MISSION-03 sin afirmar que una cuenta OANDA Practice exista, esté autenticada o haya sido activada operacionalmente.

La dependencia externa sigue siendo explícita:

```text
OANDA Practice account + Practice token
        -> todavía no provisionados
```

Por tanto, los Gates #5, #6 y #7 continúan abiertos operacionalmente aunque la preparación técnica avance.

## Objetivo

Definir y probar offline la lectura exacta que posteriormente verificará una cuenta OANDA Practice antes de reutilizar la autorización TEST/DEMO canónica de QORE.

El flujo preparado es:

```text
OandaPracticeRuntimeConfiguration
        |
        v
OandaPracticeAccountSummaryRequestFactory
        |
        v
GET /v3/accounts/{account_ref}/summary
        |
        v
ExternalTransportResponse
        |
        v
OandaPracticeAccountSummaryDecoder
        |
        v
OandaPracticeAccountSummarySnapshot
        |
        v
future operational evidence
        |
        v
existing authorize_market_test_account(...)
```

La preparación no ejecuta network IO y no resuelve secretos.

## Invariantes del request

El request factory sólo construye una lectura sobre la configuración OANDA Practice ya aprobada:

- endpoint REST exacto de la configuración Practice;
- método `GET`;
- path exacto `/v3/accounts/{account_ref}/summary`;
- timeout explícito de la configuración;
- `Accept: application/json`;
- `Accept-Datetime-Format: RFC3339`;
- sin bearer token, secret, credential o authorization header observable.

La autenticación seguirá perteneciendo al secret-aware transport boundary existente cuando el gate se ejecute de verdad.

## Invariantes del decoder

Una respuesta sólo puede producir `OandaPracticeAccountSummarySnapshot` cuando:

1. la respuesta de transporte es 2xx;
2. el payload es JSON UTF-8 con root object;
3. existe `account` como object;
4. `account.id` coincide exactamente con el `MarketTestAccountIdentity.account_ref` configurado;
5. `currency` usa tres letras mayúsculas;
6. `createdTime` es parseable y timezone-aware;
7. `hedgingEnabled` es booleano explícito;
8. pending orders, open trades y open positions son enteros no negativos, sin aceptar `bool` como `int`;
9. `marginRate` es decimal positivo y finito;
10. `lastTransactionID` del root y del account son referencias numéricas válidas e idénticas;
11. el timestamp de observación no antecede a la creación de la cuenta.

Cualquier incertidumbre devuelve `Failure` tipado.

## Identidad y evidencia

El snapshot mantiene el `MarketTestAccountIdentity` canónico para composición interna.

Para evidencia pública/sanitizada existe una vista separada que reemplaza el account ref por un fingerprint SHA-256 truncado y estable.

El account ref continúa siendo un identificador externo no secreto según los contratos actuales de QORE, pero no es necesario publicarlo en artifacts de activación.

Nunca se incorpora:

- token Practice;
- Authorization header;
- secret reference material;
- password;
- Production endpoint;
- account credential.

## Qué NO hace este entregable

No:

- verifica que el token pueda acceder a una cuenta real;
- realiza una llamada a OANDA;
- crea una cuenta;
- activa el Gate #7;
- llama `authorize_market_test_account()` automáticamente;
- habilita ejecución;
- crea órdenes;
- modifica posiciones;
- habilita Production;
- utiliza capital real.

## Uso futuro operacional

Cuando existan la cuenta y el token Practice, el Gate #7 deberá ejecutar esta misma frontera detrás del transport autenticado ya gobernado y conservar evidencia sanitizada.

Un snapshot construido sólo desde fixtures o tests nunca es evidencia suficiente para declarar `QORE-DEMO-ACCOUNT-ACTIVATION-001` operacionalmente completado.

## Relación con la secuencia MISSION-03

La secuencia permanece intacta:

```text
#5 Real Market Feed Activation       -> pendiente de credenciales/evidencia real
#6 Market Data Certification         -> preparado offline, cierre operacional pendiente
#7 Demo Account Activation           -> preparación de este entregable
#8 Demo Execution Activation         -> no cerrado
#9 Operational Safety Certification  -> no cerrado
```

La implementación preparatoria de gates posteriores no autoriza su cierre fuera de orden.

## Quality Gate

La rama debe pasar sin suppressions ni checks debilitados:

```bash
ruff check .
mypy src tests
pytest --cov=src/qore --cov-report=term-missing
```

## Fronteras cerradas

Permanecen **CLOSED**:

- OANDA Production;
- credenciales productivas;
- capital real;
- real-money trading;
- autonomous CIBO execution;
- corrective trading automático;
- bypass de Risk/Portfolio/Capital Protection.
