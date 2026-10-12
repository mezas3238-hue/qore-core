# QORE Native GROSS-04 — 33/33 mercados, sweep-reclaim: RESULTADO CERRADO NO_SUPPORT

**2026-10-12 UTC.** Hipótesis estructural pre-registrada ANTES de acceder a resultados de esta ronda mediante [commit SHA `9b147f0a385213dd4b0183b3205c6c9d467581ad`](https://github.com/mezas3238-hue/qore-core/commit/9b147f0a385213dd4b0183b3205c6c9d467581ad). Se ejecutó en [Actions #38208073921](https://github.com/mezas3238-hue/qore-core/actions/runs/38208073921) con **35/35 jobs SUCCESS**: prereg+causality, doce fuentes originales SHA, veintiún fuentes nuevas SHA y un panel conjunto sin selección. Tested exact GitHub code HEAD `77e3c67bf2dcaad956e0167d84f07a71e41e7094`. [PR #830](https://github.com/mezas3238-hue/qore-core/pull/830) DRAFT; no merge.

**Artefacto final original:** [#11727579847](https://github.com/mezas3238-hue/qore-core/actions/runs/38208073921/artifacts/11727579847), JSON `qore-native-gross04-panel33-result.json` SHA256 `3002d8c763cba61b717857db1e4c0c8edf987b0b17debfaf5d171d2762be463e`, sidecar y `OUTPUT_SHA256SUMS.txt`. Este hash se comprobó sobre el archivo extraído del artefacto, no el ZIP.

## Pregunta económica congelada

¿En el panel completo de **33 mercados** el retorno posterior a un intento de barrer un extremo de un rango previo, seguido de cierre de vuelta dentro del rango, supera la reversión ingenua del desplazamiento de la última hora? Barrido máximo/mínimo previo 08:00–12:00 UTC; probe sweep/reclaim 12:00–13:00 UTC; entrada/exit **referencia OHLC** 13:00 open y 14:55 close, un trade teórico por día y símbolo a lo sumo. Benchmark contrarian del movimiento del probe en las MISMAS fechas/horas. Requiere 48/12/24 velas M5 intactas; doble barrido, sin recuperación, vela incompleta o señal cero => sin evento, no inferencia de spread/fill/SL real. Ningún indicador futuro ni apertura de datos desde 2024-09-17.

Fuente fuente SHA inmutable [G0 33/33 #829](https://github.com/mezas3238-hue/qore-core/pull/829): 24.377.420 M5 originales. 33 artefactos de observación individuales por mercado, SHA-verificados en misma corrida; 12 originales cTrader DEMO y 21 nuevos IC Markets DEMO **sin concatenación de cotizaciones ni equivalencia de broker inferida**.

## Resultado primario: panel de 33 sin cherry-picking

| Test congelado | Desarrollo 2016-09-17→2022-09-17 | Diagnóstico 2022-09-17→2024-09-17 |
|---|---:|---:|
| Mercados con integridad M5 G0 comprobada | 33/33 | 33/33 |
| Mercados con n/semana mínimo | 33/33 | 33/33 |
| Eventos-día símbolo (solo patrones válidos) | 13.989 | 4.680 |
| n por símbolo (rango observado) | 325–473 | 119–171 |
| Semanas UTC bootstrap sincronizadas | 313 | 105 |
| Estrategia gross media bps, **cada mercado igual peso** | +0,151074 | +0,099568 |
| Benchmark media gross bps, igual peso | +0,184328 | −0,046864 |
| **Delta pareada gross bps** | **−0,033253** | **+0,146432** |
| IC98,75% delta, bootstrap 2.000 semanas sincronizadas | [−1,295593; +1,219408] | [−2,102263; +2,683191] |
| IC98,75% gross estrategia | [−0,803398; +1,033823] | [−1,546941; +1,788440] |
| Bootstrap draws nulos por alguna serie | 0/2.000 | 0/2.000 |
| Mean con supuesto coste RT 1 bp **NO BROKER** | −0,848926 | −0,900432 |
| Mean con supuesto coste RT 3 bps **NO BROKER** | −2,848926 | −2,900432 |
| **Dictamen** | **NO_SUPPORT** | **NO_SUPPORT** |

Se cumplen las condiciones de n y semanas de cada uno de los 33, pero el límite inferior de delta del test nominal 98,75% es negativo en ambos períodos y la estimación media en development también lo es. CI gross incluye cero. Por tanto **NO hay señal de ventaja económica robusta** en esta regla exacta, incluso antes de medir BID/ASK. No reclasificar como edge del panel y no calibrar horarios/rangos para rescatarla.

### Familias: exclusivamente diagnóstico descriptivo, no selección de mejores

| Familia fija | n | Development: eventos | Gross / Delta dev (bps) | Diagnóstico: eventos | Gross / Delta diagnóstico (bps) |
|---|---:|---:|---:|---:|---:|
| Índices | 3 | 1.075 | +0,209 / +2,854 | 425 | −2,079 / −1,318 |
| Metales | 2 | 905 | +1,978 / −1,427 | 299 | −0,042 / +5,122 |
| FX mayores | 7 | 2.870 | +0,158 / −0,212 | 912 | +0,615 / −0,339 |
| FX cruces | 21 | 9.139 | −0,034 / −0,253 | 3.044 | +0,252 / +0,044 |

**Importante:** los datos por familia no son cuatro pruebas confirmatorias. Ninguna familia recibió un test de significancia ni permiso para seleccionarse como ganadora. Los aparentes valores positivos de una familia no son señal replicada: índices delta positivo en desarrollo y negativo en diagnóstico; metales a la inversa. No presentar el delta +5,122bps de metales diagnóstico como edge sin su contraparte dev negativa y el control por multiplicidad.

## Qué quedó bloqueado

- La investigación mide OHLC **gross-only**, el precio open/close no es BID/ASK ejecutable. Supuestos de coste roundtrip `[0,1,3,5,10,20]`bps ilustran sensibilidad y nada más. El coste de equilibrio medio gross del panel 0,151/0,100bps no equivale a fricción broker tolerada con confianza estadística. Incluso supuesto 1bp deja negativos ambos períodos.
- No hay histórico de spreads BID/ASK de esas cuentas con mismo alcance, slippage de stops, comisión RT, swaps, calendario broker ni exposición de capital. No hay Sharpe/Sortino/PF net certificado, no LIVE/PAPER orders.
- Calendario económico historical known-as-of no validado; los resultados pueden incluir 12:30 UTC noticias de alto impacto y son `GROSS_PANEL_NEWS_UNFILTERED_NOT_TRADABLE`; política QORE Native NO-NEWS #814 sigue bloqueando trading.
- Los motores de GROSS04 y las tres rondas previas no abrieron OHLC del período 2024-09-17 a 2026-09-17. El diagnóstico 2022–24 no puede proclamarse OOS global nunca usado por Core.

## Auditoría de intentos y continuación

| Intento económico | Mercado/eje | Resultado prereg |
|---|---|---|
| [GROSS-01 PR #822](https://github.com/mezas3238-hue/qore-core/pull/822) | EURUSD momentum H4 | NO_SUPPORT |
| [GROSS-02 PR #825](https://github.com/mezas3238-hue/qore-core/pull/825) | XAUUSD reversión H4 | NO_SUPPORT |
| [GROSS-03 PR #827](https://github.com/mezas3238-hue/qore-core/pull/827) | NAS100 cash-open drive vs premarket | NO_SUPPORT |
| [GROSS-04 PR #830](https://github.com/mezas3238-hue/qore-core/pull/830) | Barrido/reclaim 33 mercados, control pareado | **NO_SUPPORT** |

**Próximas decisiones técnicas sin pesca de ganadores:** mantener el universo 33 congelado y contabilizar estos cuatro tests negativos. Priorizar especificar y recolectar **datos forward de BID/ASK/fills/costes efectivos y calendario de noticias known-as-of**, además de sellar una hipótesis causal diferente por incentivos microestructurales ANTES de otro ensayo. Consultar DeepSeek como auditor externo si surgen ambigüedades, pero pruebas verificables son los commits/Actions/GitHub artifacts firmados. Evitar variantes de hora/símbolo/SL optimizadas sobre los mismos datos y utilizar instrumentos 33 solo dentro de procedimientos de multiplicidad preregistrados.

**QORE Native 33/33 FUENTES G0 PASS**, **0/3 traders certificados**, **4/4 hipótesis exploratorias NO_SUPPORT**, ninguna operación nueva; VPS/MT5/CIBO/Shared/QDLE/LIVE y main intactos.