# QORE Native G0C — informe EJECUTADO: EURJPY/USDCHF ya descargados en Core, SIN OAuth

**Fecha:** 2026-10-11. **Estado:** `G0C_OBSERVABILITY_PASS`; `NO_ECONOMIC_TEST`; `NO_NEW_CAPTURE`; `NO_CTRADER_CREDENTIALS_REQUIRED_FOR_REUSE`; `OOS_UNTOUCHED`. **Prerregistro:** `docs/research/QORE_NATIVE_EXISTING_7Y_G0C_DEV_ONLY_PREREG_2026-10-11.md`, commit `c8c66f48f4c3f62715423a8cdba64a9986c4f09d` anterior al análisis de relojes de esta línea.

## Testigo de CI y fuente

- [GitHub Actions G0C #38173936802](https://github.com/mezas3238-hue/qore-core/actions/runs/38173936802), código ensayado commit `e54946f06361b697f64d77c0cbd88037ade029da`, **3/3 jobs SUCCESS**, suite de tests (inventario + G0C) y validación SHA256.
- Artifact G0C EURJPY `#11714983311`, Artifact G0C USDCHF `#11715480643`; incluyen `*-g0c.json`, `*-g0c-daily.csv`, inventario y `REPORT_SHA256SUMS.txt`.
- Fuente **original** [GitHub Actions #36079229139](https://github.com/mezas3238-hue/qore-core/actions/runs/36079229139) commit `6958ea0c4f183020b5248b413af998065c6662da`, archivo base EURJPY artifact `#10840979795`, USDCHF artifact `#10840849959`.
- EURJPY SHA256 original `raw-7y-base.json`: `2a3afd8075b70fd7791ffbdefb15214e7174e7be7e0367cfa49037aa6b7af3e5`; USDCHF `6afd148635907ba936a52c25817cacac7397de4da224a1b2581e75fa95e50edf`. Validación contra hashes congelados y `account_is_live=false`, `environment=demo`.
- Archivo 7Y **total**, NO inspeccionado para resultados aquí: EURJPY `521707` M5; USDCHF `521138` M5. **Submuestra DEV autorizada** `opened_at < 2023-09-24T23:45:00Z`: EURJPY `297766`, USDCHF `297352` M5. Primer timestamp DEV `2019-09-27T00:50Z`; último `2023-09-24T23:40Z`. El sector posterior queda reservado al desarrollo/validación VT08 original, no es un nuevo holdout disponible para selección en QORE Native.
- Lector `src/qore/infrastructure/trader_lab/qore_native_existing_demo_fx_g0c_v1.py`: lee solamente timestamps de apertura/cierre M5 del prefijo permitido, detiene lectura en cutoff, no decodifica OHLC ni calcula señales/P&L. Conversión London `ZoneInfo("Europe/London")`, incluyendo BST.

## Resultado comprobado — ventanas NOMINALES de Londres

Denominador: **1.041 días laborables locales** entre finales de septiembre de 2019 y septiembre de 2023, SIN excluir festivos ni imponer horario IC Markets no acreditado. Cada par tiene el MISMO censo de presencia por minuto M5 en las cuatro ventanas: **cero divergencias de disponibilidad por símbolo** en estas ventanas de desarrollo. Esto es congruencia del feed, NO correlación de retornos/edge.

| Ventana Europe/London | M5 nativas observadas por símbolo | M5 nominales | Días íntegros / 1041 | Tasa cobertura M5 |
|---|---:|---:|---:|---:|
| 08:00–09:00 apertura Londres | 12.426 | 12.492 | 1.035 | 99,47% |
| 09:00–11:00 continuación Londres | 24.864 | 24.984 | 1.036 | 99,52% |
| 15:45–16:15 alrededor fixing FX | 6.216 | 6.246 | 1.036 | 99,52% |
| 16:05–16:35 observación posterior a fixing | 6.215 | 6.246 | 1.035 | 99,50% |

**Sincronía EURJPY↔USDCHF**: para 08:00–09:00 `12426` M5 presentes en ambos y `0` presentes solo en uno; 09:00–11:00 `24864` en ambos y `0` unilateral; fixing 15:45–16:15 `6216` ambos, `0` unilateral; post-fix 16:05–16:35 `6215` ambos y `0` unilateral. Igualdad de disponibilidad **no demuestra independencia estadística ni calidad de precios**.

### Fechas incompletas — conservar, no imputar motivos

- 2019-12-25, 2020-01-01, 2020-12-25, 2021-01-01, 2022-12-26: las cuatro ventanas sin ninguna barra en ambos símbolos. Pueden ser cierres festivos, pero hasta contrastar calendario efectivo del proveedor siguen `MISSING_UNATTRIBUTED`.
- 2021-05-25: 08:00–09:00 Londres **6/12** M5 observadas en ambos símbolos, hueco intraventana `0xf03`. No es un cierre general y requiere investigación de calidad.
- 2022-11-07: 16:05–16:35 Londres **5/6** M5 observadas en ambos, máscara `0x1f`. Razón no adjudicada.
- Todas las demás fechas locales laborables **completas** en estas ventanas.

## Decisión de arquitectura

**Esta investigación YA NO necesita reautorizar cTrader ni volver a descargar EURJPY/USDCHF.** La [workflow de inventario offline](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-ctrader-demo-eurjpy-usdchf-m5-20261011/.github/workflows/qore-native-existing-7y-fx-source-inventory.yml) usa `actions/download-artifact` + `GITHUB_TOKEN` de solo lectura, y ya ha tenido éxito. La [workflow de captura nueva 10Y](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-ctrader-demo-eurjpy-usdchf-m5-20261011/.github/workflows/qore-native-ctrader-demo-eurjpy-usdchf-m5-10y.yml) fue convertida a **manual-only con opt-in explícito falso por defecto**; no reintenta OAuth automáticamente.

Distinguir `7Y_REUSE_COMPLETE` de `10Y_EXTENSION_AUTH_BLOCKED`. No atribuir a Core falta de datos existentes. Los problemas de persistencia de tokens reportados en documento de autenticación pueden merecer reparación arquitectónica **solo** si más adelante se solicitan nuevas capturas, y no deben bloquear ninguna investigación sobre lo ya archivado.

## Límites científicos

`G0C_OBSERVABILITY_PASS` **no es** edge, rendimiento, PF, Sharpe, Sortino, spread, fill o certificación de traders. Los datos de este censo son **desarrollo previamente consumido**; el periodo reservado tras cutoff **no fue abierto** para investigar señales de QORE Native. La metodología RESET con EURUSD sigue separada; el experimento externo de barrido de primera hora EURJPY/USDCHF exigiría su **propio prerregistro falsable**, endpoints y costes cuando se autorice, pero ya no una captura duplicada.

**Próximos bloques reales:** (1) auditar calendarios y los dos huecos intraventana con metadata de proveedor si existe; (2) prereg nuevo experimento exclusivamente de desarrollo, con reglas M5/targets/horario Europe/London precisos; (3) confirmación independiente nueva/auténtica no consumida antes de declarar ventaja económica. No tocar Shared, CIBO, VT08, VPS, MT5, cuenta DEMO transaccional ni LIVE.
