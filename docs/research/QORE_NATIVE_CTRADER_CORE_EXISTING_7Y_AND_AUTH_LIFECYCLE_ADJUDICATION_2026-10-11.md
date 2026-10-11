# QORE Native — reconciliación real del acceso cTrader de Core y EURJPY/USDCHF

**11-oct-2026.** Corresponde a [PR #800](https://github.com/mezas3238-hue/qore-core/pull/800), [#789](https://github.com/mezas3238-hue/qore-core/issues/789), [#793](https://github.com/mezas3238-hue/qore-core/issues/793). **Owner directive:** Core debe usar su conexión cTrader DEMO existente para descargar cuando lo necesite, sin tratar el provisionamiento como algo inexistente.

## Hallazgo 1 — Core YA HABÍA descargado ambos símbolos por cTrader DEMO

El histórico original se conservó en [GitHub Actions #36079229139](https://github.com/mezas3238-hue/qore-core/actions/runs/36079229139), commit `6958ea0c4f183020b5248b413af998065c6662da`, artifacts **EURJPY #10840979795**, **USDCHF #10840849959**. Se descargaron ZIPs y se inspeccionó el prefijo documental `raw-7y-base.json` (NO análisis de OHLC/PnL).

**Auditoría CI de metadata SIN OAuth ni outcomes**: [run #38173077639](https://github.com/mezas3238-hue/qore-core/actions/runs/38173077639), head `0b42629c26f39e40322279f83069c7a5d507fa42`, jobs `contract`, `archive_metadata EURJPY`, `archive_metadata USDCHF` **3/3 SUCCESS**. Los reports están en artifacts [EURJPY #11714827002](https://github.com/mezas3238-hue/qore-core/actions/runs/38173077639/artifacts/11714827002), [USDCHF #11714637430](https://github.com/mezas3238-hue/qore-core/actions/runs/38173077639/artifacts/11714637430). Ambos poseen `environment: demo`, `account_is_live:false`, `account_discovered:true`; usan el mismo `account_fingerprint` no secreto. No se imprimieron tokens.

| Símbolo | M5 observadas | M15 | H4 | M1 (muy corto) | Primer M5 UTC | Último M5 cierre UTC | SHA256 de `raw-7y-base.json` |
|---|---:|---:|---:|---:|---|---|---|
| EURJPY | 521707 | 173833 | 10703 | 4999 | 2019-09-27 00:50 | 2026-09-25 00:45 | `2a3afd8075b70fd7791ffbdefb15214e7174e7be7e0367cfa49037aa6b7af3e5` |
| USDCHF | 521138 | 173805 | 10703 | 4999 | 2019-09-27 00:50 | 2026-09-25 00:45 | `6afd148635907ba936a52c25817cacac7397de4da224a1b2581e75fa95e50edf` |

**Limitaciones esenciales:** son aprox. siete años, no el **objetivo nuevo de diez años**. Los M1 están limitados a aproximadamente tres días de 2026. Los archivos están etiquetados `intended_future_use:VT08_COGNITIVE_EXPANSION_M3_UNSEEN_VALIDATION`; **NO reutilizarlos para seleccionar parámetros QORE, ni declararlos OOS nuevo**; inventariar metadata no consume sus OHLC o derechos de autoría. `account_fingerprint` acredita DEMO pero no prueba por sí solo broker IC Markets/servidor exacto; vincular al registro de broker si existe evidencia adicional.

## Hallazgo 2 — Los nuevos intentos de 10 años SÍ fallaron por OAuth

- [Intento #38172092086](https://github.com/mezas3238-hue/qore-core/actions/runs/38172092086): quality PASS; jobs EURJPY y USDCHF FAILED en account discovery. `cTrader access token invalid and refresh failed`.
- [Intento #38172295246](https://github.com/mezas3238-hue/qore-core/actions/runs/38172295246): quality PASS; se priorizaron `QORE_CTRADER_DEMO_*` por encima de `QORE_CTRADER_*`, mismo error para ambos. **Ninguna de las dos ejecuciones solicitó una vela histórica**.
- No podemos leer secret values mediante el conector GitHub; no deducir que Core carece de otra fuente de tokens vigente ni declarar invalidada la cuenta real a partir de un job de Actions.

## Hallazgo 3 — Errores concretos de arquitectura de credenciales

Revisado en el baseline usado por Atlas `agent/cibo-market-atlas-20y-v1-001`:

1. `src/qore/infrastructure/ctrader_open_api_client.py` método `_refresh_tokens()` **actualiza `self._access_token` y `self._refresh_token` solo en RAM**. No implementa `persist()`, CAS, vault ni refresh bajo lock inter-proceso. Si ese refresh ocurrió usando secretos de Actions, los secretos de siguientes runs pueden quedar obsoletos. Es **causa estructural plausible**, **no raíz demostrada** de la invalidez específica actual.
2. `src/qore/infrastructure/ctrader_demo_account_discovery.py` requiere `permissionScope == 1` (trading) y `ctrader_open_api_client.py` también espera 1. Esto **prohíbe SCOPE_VIEW=0** que sería el permiso mínimo apropiado para lectura histórica. Es una discrepancia funcional real con el flujo de research (pero no causó los errores actuales, que ocurrieron antes de validar el scope).
3. Core contiene lectores de mercado, cliente TLS, cuenta DEMO, refresh y prueba de descargas pasadas, pero **no se ha demostrado un token vault persistente compartido y utilizable desde ese workflow**. Tampoco hay obligación de renovar manualmente si ya existe tal almacén fuera de la rama; hay que localizar el dueño canónico y usarlo, evitando otro token independiente.

La [documentación oficial cTrader](https://help.ctrader.com/open-api/account-authentication/) describe la rotación: recibir nuevos access+refresh invalida los anteriores. Los [scopes oficiales](https://help.ctrader.com/open-api/model-messages/) son `SCOPE_VIEW=0`, `SCOPE_TRADE=1`. La ruta histórica no debe solicitar privilegios de trading para compensar un gate mal configurado.

## Resolución estructural que debe ejecutar Core para que una descarga futura sea autónoma

**P0A — DESCUBRIMIENTO DEL DUEÑO DE CREDENCIALES, sin leer secretos:** localizar el servicio/secret resolver activo para cTrader DEMO y el último token versionado (solo fingerprints/epochs no sensibles). Si Core dispone de un vault funcional, el descargador debe usarlo como fuente de verdad; no duplicar credenciales por workflow.

**P0B — SESIÓN DE CREDENCIALES FÁCILMENTE REUTILIZABLE:** read-only `DEMO` account discovery permite `SCOPE_VIEW=0` o `SCOPE_TRADE=1` pero nunca enviar órdenes; exigir exactamente la cuenta DEMO previamente vinculada. No modificar puertas ejecutivas de trading en producción como consecuencia de un workflow de investigación.

**P0C — REFRESH ATÓMICO CENTRALIZADO:** un solo escritor por grant cTrader bajo lease/CAS y revisión de versión; persistir **ambos** tokens renovados atómicamente en vault seguro **antes** de publicar una sesión autenticada. No imprimir secretos, no subir a Actions artifacts/commits/issues, y no permitir carreras entre jobs paralelos que invaliden el mismo refresh. Si no hay escritura durable, falla cerrado ANTES de consumir un refresh token. Reutilizar el access token válido hasta refresh coordinado.

**P0D — CONEXIÓN WORKFLOW:** el job GitHub debe recibir una credencial válida desde ese mecanismo autorizado sin ampliar privilegios a cuentas LIVE. Un `GITHUB_TOKEN` de Actions con permisos `contents:read` / `actions:read` no es un almacén de secretos rotativos. Si el vault no existe/está inaccesible, es inevitable un paso autorizado de mantenimiento del grant; no exigir por rutina al Owner cada descarga.

**P0E — VALIDACIÓN EN CI:** tests de expiración/rotación con memoria falsa y persistencia inyectada, concurrencia de dos jobs, scopes 0/1 en lectura y rechazo de LIVE/mapping ambiguo; test real únicamente cuando exista backend de credenciales autorizado, sin operaciones de trading. Todo sobre rama research GitHub.

**Estado de este turno:** `7Y_EXISTING_EURJPY_USDCHF_VERIFIED_FROM_CORE`; `10Y_NEW_CAPTURE_AUTH_BLOCKED`; `CREDENTIAL_LIFECYCLE_REPAIR_PENDING`; `VT08_RESERVED_ARCHIVE_UNTOUCHED`; `0_EDGE_CLAIMS`; `NO_VPS_NO_MT5_NO_LIVE`.
