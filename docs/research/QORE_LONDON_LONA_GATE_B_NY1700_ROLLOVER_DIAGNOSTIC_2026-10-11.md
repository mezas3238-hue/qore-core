# QORE LON-A — GATE B / Causa probable del 0/312 Daily UTC completas

**Fecha:** 2026-10-11 · **Issue:** [#785](https://github.com/mezas3238-hue/qore-core/issues/785) · **PR:** [#788](https://github.com/mezas3238-hue/qore-core/pull/788)

**Dictamen:** `M1_NY_1700_MISSINGNESS_PATTERN_VERIFIED` · `D1_NATIVE_UNVERIFIED` · `FEED_CORRUPTION_NOT_PROVEN` · `NO_OOS` · `NO_ECONOMIC_REPLAY`.

## 1. Anomalía original

[Gate B inicial, run #38168967976](https://github.com/mezas3238-hue/qore-core/actions/runs/38168967976): en el histórico **2025-09-17 → 2026-09-17**, ya consumido por investigación, se identificaron **369.903** barras M1 EURUSD y **369.833** GBPUSD. Las 312 fechas UTC con al menos una M1 conservaron como máximo **1.438 de 1.440** minutos por día. Ninguna pasó el criterio *estrictísimo* de cobertura 1440/1440. Esto **NO** prueba que la vela Daily del broker sea incorrecta o que no exista; un proveedor forex puede no publicar M1 durante un tramo de sesión cerrada, inactiva o sin transacciones.

## 2. Nuevo diagnóstico auténtico por M1/minuto del día — ejecución verificada

[GitHub Actions #38173764426](https://github.com/mezas3238-hue/qore-core/actions/runs/38173764426), commit `4b0495feaf9a82f9d6fa8d8cffeb0e93b1072a52`: **SUCCESS** en los tres jobs, **18/18** pruebas sintéticas y lectura de las mismas fuentes M1, con particiones 2025/2026 confrontadas con manifiestos/hash. Artefactos de sólo auditoría: [EURUSD #11714563748](https://github.com/mezas3238-hue/qore-core/actions/runs/38173764426/artifacts/11714563748), [GBPUSD #11715351190](https://github.com/mezas3238-hue/qore-core/actions/runs/38173764426/artifacts/11715351190).

Prerregla descriptiva (ingeniería QORE, NO TTrades): examinar separadamente los días UTC con **≥1.300 M1** (224 por símbolo), sin filtrar por ganancias ni pérdidas. En cada fecha se calcula **qué hora UTC corresponde a las 17:00 America/New_York**, de acuerdo con DST; contar presencia/ausencia de ese minuto y del inmediatamente anterior. No se rellenan datos, no se reconstruye un precio y no se ejecuta replay económico.

| Diagnóstico | EURUSD | GBPUSD |
|---|---:|---:|
| Días UTC con ≥1.300 M1 | 224 | 224 |
| NY en horario verano (17:00 NY = 21:00 UTC) | 137 | 137 |
| Faltan 20:59 **y** 21:00 UTC en esos días | **137/137** | **137/137** |
| NY en horario invierno (17:00 NY = 22:00 UTC) | 87 | 87 |
| Faltan 21:59 **y** 22:00 UTC en esos días | **87/87** | **87/87** |
| Días densos con ambas barras ausentes según el reloj correcto | **224/224 (100%)** | **224/224 (100%)** |
| Días con 1.438 M1 exactos | 4 | 13 |
| Días con 1.440 M1 exactos | 0 | 0 |

**Hallazgo P0:** la concentración de ausencias en la transición de las 17:00 NY es sistemática, se reproduce en los **dos símbolos** y respeta los cambios de horario. **Es compatible** con un horario de mantenimiento/rollover o falta de publicación M1 en esa zona, pero el censo **no distingue** definitivamente: (1) feed broker sin velas M1 porque no hubo operaciones, (2) cierre reglamentario/rollover, (3) mantenimiento, (4) fallo de captura/retención. Atribuirle una causa única sin registros de origen o datos nativos es incorrecto.

La fracción 100% aplica **solo** a los 224 días densos y a esas **dos posiciones temporales**; NO prueba integridad total de D1, H4 o resto de minutos ni demuestra que todas las otras ausencias de 312 fechas sean benignas.

## 3. Consecuencias prácticas para la investigación Londres

1. **No perseguir 1440/1440 como único certificado de una vela Daily forex.** 0/312 es consecuencia del requisito matemático sobre M1 registrados y no una condena automática a los datos.
2. **Tampoco relajar la condición a 1438/1440 ni interpolar OHLC.** Se necesitaría contrastar contra **D1 nativa** del proveedor (y H4 nativa o perfil exacto del autor), con provider/timestamps/UTC, rango O/H/L/C e integridad de sesiones documentados.
3. **Contabilizar explícitamente censura**: la cobertura M15/H4 de UTC es descriptiva sobre bins no vacíos; una selección de solo bins completos puede introducir sesgo horario. Comparar horarios Londres y otros fuera de sesión, sin usar PnL.
4. **No declarar que el horario H4 del autor es UTC o el NY de Capitalizer V48:** el patrón de 17:00 NY es del *feed*, no evidencia suficiente para imponer ancla metodológica.
5. **Próxima auditoría fuente:** verificar los intervalos sin M1 alrededor del rollover contra los horarios de sesión del símbolo y solicitar/rastrear D1/H4 nativas, preferiblemente desde la misma cuenta DEMO read-only; si no es posible, `DATA_GATE_B_PARTIAL`.

## 4. Contratos y prohibiciones

Source run #35548099334; SHA fuente `18c338aedd5013ce65a6cb6408ffbc2e904a6217`, EURUSD artefacto `10618547852`, GBPUSD `10618811910`. Comprobación de particiones SHA-256, sin regenerar fuente ni modificar histórico.

Código: [censo de minutos y régimen NY DST](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/src/qore/infrastructure/trader_lab/qore_london_lona_data_census_gate_b_v1.py). Tests: [18 sintéticos](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/tests/infrastructure/trader_lab/test_qore_london_lona_data_census_gate_b_v1.py).

**El avance no constituye prueba de que el TTrades London Fractal original tenga edge neto.** Se mantiene `data_gate_b_certified=false`, `fresh_holdout_eligible=false`, `economic_replay_authorized=false`, `live_authorized=false`. No se cambió VPS, MT5 ni CIBO.
