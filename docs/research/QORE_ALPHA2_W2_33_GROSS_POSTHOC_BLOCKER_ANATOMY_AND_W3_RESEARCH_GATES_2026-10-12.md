# QORE-Alpha 2 — W2 PADE auditoría causal y potencia posthoc, 33 mercados

**Origen immutable:** W2 first GROSS run [#38283326547](https://github.com/mezas3238-hue/qore-core/actions/runs/38283326547), HEAD `3f81e41ba6af5c226402f68621db7f78980231fe`, 35/35 PASS. Auditoría POSTHOC sin ninguna OHLC nueva ni reoptimización [#38283910730](https://github.com/mezas3238-hue/qore-core/actions/runs/38283910730), HEAD `ed7a66d5b6f2b75e947a605ca88825ed9e446b86`, SUCCESS. Artefactos JSON + SHA en ambos runs.

## Censo completo

- **33/33** símbolos reportados incluyendo seis sin señales; total **265** oportunidades y **265** pareadas, 134 con dirección PADE vs control distinta (control no tautológico).
- Índices: **3**, 0 señales. Metales: **2**, 0 señales. Mayores FX: **7**, 63 señales pareadas, 27 decisiones opuestas al control. Cruces FX: **21**, 202 señales, 107 contrarias. Total 0/5 índices/metales por precondiciones; **no** afirmar que su alpha es cero ni descartarlos.
- **Principales razones de abstención**, desglosadas por H1 comprobada de los 33 worker SHA: actividad <1,65× mediana histórica 325.766; falta de 20 H1 anteriores consecutivas 204.203; desplazamiento H1 >0,20 rango 9.978; falta de 10 horas históricas mismas UTC 2.653; desequilibrio de ticks no suficiente 2.134. Estas categorías son secuenciales, no causas econométricas independientes; los mismos eventos pueden fallar otras precondiciones no evaluadas. Especialmente la ausencia de 20 horas seguidas responde a sesiones de índices/metales, **no es prueba económica de fracaso en estas familias**.
- Desarrollo: 220 operaciones, 114 semanas activas de 314, resultado bruto −1,7980 bps/evento, delta PADE–control −4,5586 bps. IC bootstrap con bloques 4 semanas **[−13,5758; +1,6414] bps**, p exploratorio 0,2624; el IC cruza cero.
- Diagnóstico: 45 operaciones, 25 semanas activas de 106, resultado bruto +3,3943 bps, delta −1,9728 bps, IC 4 semanas **[−8,1538; +2,4867] bps**, p exploratorio 0,4739; también cruza cero. Falta de n≥50 y ≥26 semanas. Ningún control múltiple transforma esto en soporte positivo. Estudios 2016–2024 YA CONSUMIDOS, no OOS virgen.

## Dictamen y progreso

**W1 PATR:** `UNDERPOWERED, NEGATIVE_GROSS, CONTROL_TAUTOLOGICAL`.
**W2 PADE:** `UNDERPOWERED, NEGATIVE_PAIRED_EDGE, CI_INCLUDES_ZERO, 0_INDICES/METALS`.
**0 traders certificados** y **0 señales autorizadas LIVE/PAPER**. Los 33 originales y el flujo SHA sí están disponibles: la infraestructura no es el cuello de botella principal; falta hipótesis económica soportada, BID/ASK executable y PIT macro.

No ajustar PADE para quitar la condición de 20 H1 contiguas, mover horarios, subir/bajar ratio actividad o seleccionar sólo FX por la presente auditoría. El próximo modelo W3 sólo puede ser un mecanismo PRE-reg nuevo, etiquetado EXPLORATORIO, con base en restricciones de fuente/horarios identificadas independientemente del PnL y control discriminativo. No atribuir a W3 más evidencia de independencia de la que exista. Recomendada máxima familia adicional exploratoria **W3** antes de requerir fuente temporal separada y brokerage tick BID/ASK; no continuar lanzando miles de estrategias y escoger una ganadora por azar.

## Bloqueantes que persisten

La fuente `ProtoOATrendbar.volume` se documenta como **tick volume** (no real traded quantity): https://help.ctrader.com/open-api/model-messages/#protooatrendbar . Confirmar que el productor CIBO 12 e ICMarkets21 copiaran el campo sin transformación requiere código de productor + witness. Misma cuenta de broker entre ambas cohortes no probada. Noticias conocidas-as-of, spreads completos, slippage, financiación, cambios contractuales del CFD y comprobación de fills siguen `UNVERIFIED`.

**PROHIBIDO** inferir PF/Sharpe/Sortino/DD neto de los proxies, atribuir USD de PnL a R no escalado, publicar comparaciones con cartera sin risk book, merge a main o abrir operaciones en VPS/MT5/QDLE/Shared/CIBO.
