# QORE Native G0C — preregistro: usar EURJPY y USDCHF ya descargados, SIN cTrader/OAuth

**Fecha:** 2026-10-11. **Estado:** preregistro anterior a inspección del índice M5 de ambos artefactos (solo se inspeccionaron metadatos, identidad, SHA y conteos previos). **Prioridad:** adaptar Core para reutilizar fuente ya conservada sin redescargar ni pedir secretos.

## Fuentes inmutables (prohibido sustituirlas)
- Original [GitHub Actions run #36079229139](https://github.com/mezas3238-hue/qore-core/actions/runs/36079229139), `head_sha=6958ea0c4f183020b5248b413af998065c6662da`.
- EURJPY artifact ID `10840979795`, archivo `raw-7y-base.json`, 521707 M5 esperadas.
- USDCHF artifact ID `10840849959`, archivo `raw-7y-base.json`, 521138 M5 esperadas.
- Ambos originalmente cTrader DEMO, `account_discovered=true`, `account_is_live=false`, `environment=demo`; rangos M5 desde 2019-09-27 hasta 2026-09-25 aproximadamente. Reusar solo desde GitHub Actions, con token automático `GITHUB_TOKEN` de lectura; **NO** `QORE_CTRADER_*`.
- Archive original `intended_future_use=VT08_COGNITIVE_EXPANSION_M3_UNSEEN_VALIDATION` y `fresh_cutoff=2023-09-24T23:45:00+00:00`; **jamás abrir precios ni índices temporales posteriores a ese cutoff para QORE** en G0C.
- El baseline de 12 símbolos de CIBO [run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) queda intacto. La descarga extra 10Y de la PR #800 falló por credenciales y está separada de este camino offline.

## Único estudio autorizado G0C: OBSERVABILIDAD, sin resultados económicos
Sobre datos M5 con `opened_at` estrictamente ANTERIOR a `fresh_cutoff`, solo timestamp, integridad, existencia de barra por franja, NO precio, high/low, PnL, labels ni señales. A partir del último timestamp permitido, cortar sin inspeccionar los registros siguientes. Todas las fechas convertidas con IANA `Europe/London` (DST, no reloj GMT fijo). Esas observaciones históricas son `DEV_PREVIOUSLY_CONSUMED`, NO virgin OOS.
- London opening-hour: 08:00–09:00 London local, 12 M5 esperados cada día nominal laborable.
- London post opening: 09:00–11:00 local, 24 M5 esperados.
- London benchmark/fixing observation 15:45–16:15 local, 6 M5 esperados.
- London research post-fix entry-to-exit support 16:05–16:35 local, 6 M5 esperados, incluye apertura de 16:30 para futuro endpoint sin outcomes. **No afirmar fill/spread/benchmark certificado**.
- Denominador: días laborales locales de lunes a viernes entre primera fecha observada y fecha anterior al cutoff, SIN declarar que festivos son errores de broker.
- Un día será completo solo si existen TODAS las barras nativas M5 esperadas; no ffill. Registrar completitud por símbolo/ventana, anomalías, por año y sincronía EURJPY↔USDCHF. Datos futuros no usados para decidir admisión en cualquiera de los dos.
- Validar continuidad estricta de timestamps UTC alineados a 5min, `closed_at = opened_at + 5min`, sin duplicados; si anomalía del proveedor, FAIL en vez de reparar.
- `G0C_PASS` significa únicamente que se pudo consumir y censar **el desarrollo permitido**, no autenticación vigente, spread real, sistema operativo autónomo completo, ni viabilidad de una estrategia de barrido.
- Prohibido seleccionar fechas/mercados a partir de precio; no se abrirán OHLC para optimizaciones, no alterar metodología RESET prioritaria, ni fusionar con VT08 resultados.

## Salida esperada
- `qore_native_existing_demo_fx_g0c_v1.py` y tests reproducibles de corte as-of, DST y censura de lagunas.
- Workflow GitHub `qore-native-existing-7y-fx-source-inventory.yml` con descarga **solo** de artifacts ya almacenados + `GITHUB_TOKEN`, sin secretos cTrader, que crea JSON + CSV de censo y SHA.
- Código de nueva captura 10Y permanece separado y manual/disabled hasta decisión de extender horizonte. No habilitar órdenes, cuentas reales ni producción.
- **Falsación del flujo:** fallo de hash, DEMO identity, falta de archivo, ausencia de fuente m5, violación de `fresh_cutoff`, timestamp duplicado, resultados reproducidos inconsistentes => FAIL. Si no hay enough bars => `INSUFFICIENT_COVERAGE`, no simular.
