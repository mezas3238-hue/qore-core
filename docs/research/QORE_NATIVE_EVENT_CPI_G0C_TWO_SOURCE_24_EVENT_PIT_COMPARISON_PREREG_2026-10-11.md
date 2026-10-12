# QORE CPI G0C — muestra comparativa de 24 eventos CONGELADA ANTES DE FORECASTS

**2026-10-11.** Protocolo documental de validación de consenso, SIN consulta actual a ningún proveedor y sin acceder a expectativas, CPI reales, retornos ni costes. La lista se seleccionó exclusivamente de las **119 fechas del artefacto BLS original #11720651765**: tres fechas en 2016 (muestra parcial), dos por año 2017–2025 (un evento Q1 y uno Q4, incluyendo excepcional de 2025), y tres en 2026 (parcial). **Muestra de cobertura diagnóstica, no muestreo aleatorio ni validación estadística de precisión.** La selección no cambia si una fuente no tiene el evento: se reporta `MISSING`.

## Muestra sellada de cotejo (24/119; cero precios y forecasts inspeccionados)

| Año | Fechas CPI de publicación a verificar |
|---|---|
| 2016 | 2016-10-18, 2016-11-17, 2016-12-15 |
| 2017 | 2017-03-15, 2017-10-13 |
| 2018 | 2018-03-13, 2018-10-11 |
| 2019 | 2019-03-12, 2019-10-10 |
| 2020 | 2020-03-11, 2020-10-13 |
| 2021 | 2021-03-10, 2021-10-13 |
| 2022 | 2022-03-10, 2022-10-13 |
| 2023 | 2023-03-14, 2023-10-12 |
| 2024 | 2024-03-12, 2024-10-10 |
| 2025 | 2025-03-12, **2025-10-24** (CPI de referencia SEPTIEMBRE 2025; fecha reprogramada) |
| 2026 | 2026-01-13, 2026-05-12, 2026-09-11 |

**El evento 2025-10-24 no es CPI de referencia octubre**; octubre 2025 no tuvo comunicado, según BLS. El comunicado de referencia septiembre se publicó excepcionalmente octubre 24. Fechas actuales BLS archivo = calendario retrospectivo, no prueba de aviso previo as-of. Confirmación original cabe en G0B, no en este cotejo.

## Dos fuentes INDEPENDIENTES obligatorias

**Fuente A candidata:** Trading Economics Economic Calendar Point-in-Time API: https://docs.tradingeconomics.com/economic_calendar/point-in-time/ , pero su documentación no es prueba del acceso, licencia ni existencia de vintage 2016 CPI. **Fuente B:** prensa Reuters/Bloomberg, Econoday u otra base de forecasts contemporáneos con timestamp verificable, licencia de conservación y procedencia distinta. **Ninguna fuente está conectada/autorizada en este estudio**; no afirmar descarga ni congruencia.

Por CADA uno de los 24 eventos de la lista, adquirir solamente de fuentes autorizadas y registradas:
- `headline CPI MoM seasonally adjusted` y `core CPI MoM seasonally adjusted` **con unidades idénticas**, referencia mensual y definición de encuesta; no mezclar YoY, anualizado, mediana, consenso BLS inexistente o TEForecast propio con consenso panel.
- Instantánea histórica registrada **antes** del anuncio: `T-24h` y `T-5min` hora America/New_York, normalizada UTC. Debe constar timestamp/vintage del dato o fuente periodística publicada previamente; `LastUpdate` posterior no demuestra disponibilidad as-of. Valores `Actual` / revisiones CPI **prohibidos** para detectar consenso.
- Hash de testigo y condición de licencia; discrepar sobre huso horario, campo, sesgo de revisión o procedencia elimina la comparabilidad de ese par, no se imputa.
- Comparación por evento: cobertura A/B, temporalidad confirmada, diferencia absoluta del consenso en **puntos porcentuales** (tolerancia diagnóstica previa `<=0.05 pp`, no un edge), mismo signo de sorpresa **solo posteriormente** si el mecanismo G1 lo exige (actual CPI no forma parte de la primera auditoría de forecast), fuente real de desacuerdo y último snapshot válido.

**Regla operativa de calidad:** exigir **≥23 de 24 coincidencias** de definición/unidades/timing con diferencia <=0.05pp en AMBOS headline/core, y **24/24 con procedencia revisable**. No se debe informar `96% agreement` si 8 o 10 filas son missing, compartidas entre proveedores o no as-of: denominador completo 24. Incluso 24/24 no demuestra fiabilidad poblacional al 95%; IC binomial exacto inferior alrededor del 85.8%.

Antes de contratar un feed: obtener 2–3 **muestras de demostración legalmente accesibles** para comprobar que PIT significa verdaderamente snapshot pre-evento, cobertura 2016 y campos CPI. Consultar condiciones de precios/acceso, sin asumir que Bloomberg/Reuters son gratis ni que prensa contemporánea es comparable a panel de consenso.

**Si no hay dos fuentes independientes comparables**: `G0C_SOURCE_NOT_AUTHORIZED` / `G1_BLOCKED`. No copiar secretos, citar contratos o inventar datos.

## Bloqueo adicional separado: costes 08:30 NY

Un consenso preciso no demuestra un edge neto. Se requiere histórica del mismo CFD USTEC/broker para distintas latencias post-CPI (T+60s, T+300s, etc.), entrada y salida BID/ASK, tamaño/slippage y comisiones. El coste genérico normal NO sustituye el de shock. Cualquier futuro esquema T+05→T+35 minutos se congela **antes de leer precios**, condicionado a coste y potencia observados con información as-of.

**No autoriza G1, no modifica CIBO/Shared/VPS/MT5.**
