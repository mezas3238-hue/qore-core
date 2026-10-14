# QORE CORE — Continuidad con los datos disponibles (sin comprar; sin forzar edge)

**Checkpoint:** 13-OCT-2026 Paraguay / 14-OCT-2026 UTC en GitHub Actions.
**Repositorio soberano:** `mezas3238-hue/qore-core`. PR actual **[#922](https://github.com/mezas3238-hue/qore-core/pull/922)** DRAFT hija de [#921](https://github.com/mezas3238-hue/qore-core/pull/921). **SIN MERGE, SIN LIVE/DEMO, SIN capital real, USD0.**

## 1. Orden de trabajo y límites

El Owner indica que hay que seguir trabajando **con lo ya conseguido**. Se conserva el activo histórico CFTC y los archivos QORE Native; eso **no** autoriza a cambiar z thresholds, pruebas previamente cerradas ni usar holdouts reservados. La PR #921 queda científicamente `CLOSED_INCONCLUSIVE_LOW_POWER` en cuanto a las hipótesis *predictivas de reversión* de WTI/NG y **operativamente pausada como familia CFTC para trading**. La PR #922 **NO REABRE** esa línea: es censo descriptivo de realidad de regímenes, sin cargar EIA ni precios, para que el siguiente arquitecto sepa la densidad verdadera de la fuente reutilizable.

## 2. Auditoría REAL de fuente CFTC sin resultados de mercado

**[Actions #38499378485](https://github.com/mezas3238-hue/qore-core/actions/runs/38499378485)** SUCCESS en commit de código `71ffa493cce8c3e0c0328f29a7bcf8f02e7be827`: 9/9 pruebas sintéticas PASS, Ruff PASS, se descargaron 10 archivos ZIP oficiales CFTC SHA256-pinned, 6 raíces, **3.132 registros raíz-semana**, 2012–2021 completos. NO se descargó NINGUNA serie de precio ni retorno.

Artefacto CFTC descriptivo: [#11864823469](https://github.com/mezas3238-hue/qore-core/actions/runs/38499378485/artifacts/11864823469), ZIP sha256 `61c180ce9a24a0f1ed6230f6235c74c6928ab143116e4d61c227cda1e0d8d0eb`.
SHA256 **lógico** del recibo: `ff0b4f99d3c7310a3448bfabb25c9d18a471f2288c26b6b8ab448044ff9f2425`.
Scripts: `.github/scripts/qore_cftc_sixroots_regime_density_census_v1.py`, tests `tests/infrastructure/trader_lab/test_qore_cftc_sixroots_regime_density_census_v1.py`, workflow `.github/workflows/qore-cftc-sixroots-regime-density-census.yml`.

Para documentar rareza se usa fórmula *existente* `(MM_long-MM_short)/OpenInterest`, Z-score de **104 reportes previos**, bandas fijas `z≥+2` y `z≤−2`. Se cuentan semanas extremas y primeras entradas extremas con **8 reportes de cooldown**. **NO son señales aprobadas ni validación de respuesta de precio**. Tampoco se aplican las ventanas de blackout y disponibilidad EIA de #921; esta es descripción de CFTC, de ahí diferencias entre los cruces admitidos de este censo y eventos elegibles de un estudio de precio.

| Raíz | Semanas extremas positivas | Semanas extremas negativas | Total semanas extremas | Nuevos cruces admitidos tras 8 reportes | Mayor racha extrema en semanas |
|---|---:|---:|---:|---:|---:|
| CL WTI | 19 | 25 | **44** | **9** | 9 |
| NG gas natural | 28 | 32 | **60** | **9** | 15 |
| GC oro | 6 | 27 | **33** | **6** | 17 |
| HG cobre | 42 | 9 | **51** | **7** | 25 |
| ZC maíz | 13 | 7 | **20** | **6** | 8 |
| ZS soja | 26 | 30 | **56** | **8** | 18 |
| **Todos** | **134** | **150** | **264** | **45** | — |

Hay 3.132 registros **market-week**, pero 264 semanas extremas se comprimen a 45 cruces de episodio en seis raíces con la regla declarada. Los 45 tampoco son independientes como panel económico: shocks de mercados pueden estar correlacionados; además no hay salida/fecha de publicación/coste ni retornos.

**Hallazgo:** escasez y persistencia de regímenes CFTC extremos explican por qué H-COT-2 no alcanzó potencia suficiente al exigir independiente-por-instrumento y DEV/DIAG. No es «CFTC nunca funciona» ni existe prueba de beneficio.

## 3. Inventario económico de lo que efectivamente existe

**CFTC:** 6 mercados × 522 informes/raíz, 2012–21. Los ZIP están disponibles en URLs oficiales y autenticados por SHA; **NO archivados permanentemente** en GitHub. Recibos tienen retención. Posicionamiento agregado, ninguna serie de precios por vencimiento.

**EIA:** cuatro series energéticas WTI/NG F1/F2 12.352 puntos referenciales, sin bid/ask, sin ejecución nativa, sin timestamp de publicación histórico individual. Las pruebas backwardation y cambio neto posicionamiento ya `NO_SUPPORT`; reversión extrema `CLOSED_INCONCLUSIVE_LOW_POWER`. Reserva 2022–24 **sellada**.

**QORE Native:** según [handoff maestro #855](https://github.com/mezas3238-hue/qore-core/pull/855), **24.377.420 barras M5 verificadas en 33 mercados**, 2016–2026 según fuente, mezclan proveedor/cuenta histórica; 231 celdas de 7 métodos × 33 mercados DEV/DIAG ya evaluadas con Holm/FDR/bootstrap: **0 hallazgos robustos positivos replicados**. Holdout desde 2024-09-17 sellado. No etiquetar 24 millones como trades independientes.

**IC Markets/cTrader BID/ASK:** [handoff de fuente #855](https://github.com/mezas3238-hue/qore-core/pull/855) documenta **127.928 ticks de 33 posiciones del universo** recogidos en **3 ventanas de 10 minutos** por símbolo (con alias NAS100/USTEC aún no homologado); otras capturas adicionales independientes de M1 Protobuf y as-of. NO equivale a histórico continuo 33 × 10 años; no hay costes de RT, slippage, swaps ni fills de todas las pruebas 231. Los spreads cero se ponen en cuarentena, no son gratuidad certificada. No afirmar PF/DD net.

## 4. Continuación concreta y proporcionada

1. **No pagar fuentes ni abrir holdouts.** No ejecutar otro z-score/momentum/hedgers CFTC después de observar la rareza; conservar seis archivos fuente anuales por SHA y el resumen como inputs *contextuales* para investigación futura, no señales de trading.
2. **Trabajo económico con M5 existente:** priorizar una sola nueva hipótesis basada en un mecanismo EXTERNO/causal explícito aún no examinado, con motivo de por qué alguien pagaría, no volver sobre siete familias gross ni variantes de Londres/ICT ya testadas. Antes de tocar retornos, congelar ventana, instrumento, señal, comparador neto, tamaño mínimo, costes y STOP; DESARROLLO/DIAGNÓSTICO ya usados son exploratorios, no OOS fresco.
3. **Antes de llamar trader rentable:** exigir cotizaciones BID/ASK históricas a horas reales de entrada/salida, identidad contractual y broker, comisión, deslizamiento, latencia y prueba fuera de muestra realmente nueva. Los recuentos de fuente no crean edge.
4. **Si no hay mecanismo nuevo que supere la criba bibliográfica:** dedicar recursos disponibles a medir cobertura causal y costo de ejecución de las estrategias V2 existentes, sin retunear outcome, ni declarar GANANCIA. Ese estudio puede ser útil para el riesgo aunque no genera alpha.

## 5. Bloqueos reales

- No hay siquiera **un** trader certificado por estas pruebas nuevas: `CERTIFIED_0_OF_3` para QORE Native y `NO_CERTIFIABLE_CFTC_EDGE` para CFTC.
- Sin flujo de datos contract-native legal y por expiración de futuros CME USD0. `SOURCE_BLOCKED` para la misión 6×2.
- EIA as-of publication no verificada; CFTC ZIP reconstruido no timestamp de primer release.
- 33 mercados M5 = velas OHLC históricas, **no** 33 fuentes nativas tick BID/ASK continuas.
- No accesos LIVE, merge, cuentas de fondeo, VPS, sizing trader, Risk/CIBO/Shared/QDLE en esta rama.

**Conclusión:** continuar QORE con el inventario real y sus límites. Un censo de regímenes observado no se comercializa como edge y no reabre automáticamente una familia sin potencia. Los activos y la trazabilidad quedan listos para un problema económico nuevo y comprobable, sin repetir el patrón de buscar un test positivo a cualquier precio.
