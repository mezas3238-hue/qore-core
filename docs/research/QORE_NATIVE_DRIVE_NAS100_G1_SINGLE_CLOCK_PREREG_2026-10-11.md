# QORE NATIVE DRIVE — G1 preregistro congelado, NAS100 M1 nativo cTrader, impulso inicial NY

**2026-10-11 — PRE-OUTCOME.** Documento publicado ANTES de leer el resultado de esta hipótesis. Hipótesis económica independiente de RESET (cerrado G1/G2) y de ICT/TTrades. No se optimizarán horarios, instrumentos, cuantiles ni stops después de conocer los retornos. **Desarrollo consumido; jamás etiquetar OOS virgin.**

## 1. Pregunta económica estricta

¿El signo del desplazamiento **ya completado** al inicio de la mañana de Nueva York en el CFD NAS100 (símbolo del proveedor `USTEC`) predice el retorno posterior **mejor que la dirección equivalente del último día observable anterior**?

Hipótesis falsable, sin atribución institucional no observada: presión de demanda y descubrimiento de precios podrían persistir tras movimientos iniciales. Se mide **continuación de precio**, NO división de órdenes, intenciones institucionales, RTH CME real ni ejecución broker.

- Fuente única: **CIBO cTrader DEMO nativo M1 archivado** [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), `qore-capitalizer-cibo-10y-native-m1-NAS100-18c338aedd5013ce65a6cb6408ffbc2e904a6217`, artifact **#10618862813**, `RAW_M1_LEDGER/2016.jsonl`.. `2026.jsonl`, manifiesto y SHA256. Captura 2016-09-17 00:00 UTC..2026-09-17 00:00 UTC exclusivos; hash de cada partición, OHLC/orden causal y conteo total. No APIs, OAuth, VPS, fuentes externas ni M1 sintetizado.
- No consumir fuentes selladas pre-2016 ni abrir datos de otros traders. Datos CIBO 2025–26 ya inspeccionados en G0 y la historia 10Y pertenece a programas previos, por lo que todo es **DEV/RESEARCH_EVIDENCE_CONSUMED**, no backtest final de certificación.
- Reloj exclusivamente IANA **America/New_York** (DST). 09:30 NY es una hora de referencia, **no** una verificación de que el mercado CFD equivale a la apertura oficial del futuro CME ni a calendario bursátil. Días con M1 faltante, festivos, noticias y shocks se registrarán como fuente observada, no se imputarán.

## 2. Una sola configuración preregistrada

1. **Formación:** M1 provider-native desde apertura **09:30** hasta apertura **10:00** NY; `formation = ln(open_10:00/open_09:30)`, observada a las 10:00; no usar retornos en formación de una vela incompleta. Si `formation=0` abstención. No hay filtro cuantílico ni parámetro afinable.
2. **Entrada proxy:** `open M1 10:01 NY`; **salida proxy:** `open M1 11:00 NY`. Retorno prospectivo hipotético `Y = 10000 ln(open_11:00/open_10:01)` en bps logarítmicos del índice CFD, no PnL ni precio de fill BID/ASK. La señal de 10:00 se sabe ANTES de 10:01. Sin costes/fills, topes, stop ni TP; no afirmar tradabilidad.
3. **Exigir 91 aperturas reales consecutivas** 09:30..11:00 NY, una por minuto, mismo día, timestamp UTC correcto. Si falta una, excluir día completo de ambos brazos, etiquetar `MISSING_NY_91_M1`; no forward-fill. Un día con `formation=0` se excluye de ambos, separadamente.
4. **Placebo causal dentro del MISMO horario de retorno:** `S_t = sign(formation_t)` (DRIVE); `S_{t-1} = sign(formation en última fecha elegible anterior)`, con máximo **5 días naturales** de antigüedad y fecha anterior completa. La elección de baseline se conoce ANTES de la entrada actual; no depende de `Y_t`. Si signo previo es cero/no válido/desactualizado o no hay fecha anterior observada, excluir el día de ambos brazos, no usar acceso a datos futuros. La referencia controla parcialmente drift del mismo horario y parte de la persistencia direccional, sin afirmar matching perfecto de volatilidad o calendario.
5. Para los dos brazos, `GROSS_DRIVE_t = S_t * Y_t`; `GROSS_STALE_t = S_{t-1} * Y_t`. **Endpoint primario único** `delta = mean(GROSS_DRIVE_t-GROSS_STALE_t)`. No se examinan submuestras para elegir ganador; sign up/down y años son únicamente reportes de estabilidad sin promover reglas nuevas.
6. **IC95 principal** sobre `delta`: bootstrap pareado de bloques ISO-week completos (semana NY), **2.000 replicaciones**, generador `random.Random(941211)`, percentiles lineales 2.5/97.5; las fechas del mismo bloque se remuestrean juntas, mismas observaciones para DRIVE y placebo.
7. **Muestra mínima**: **500 fechas apareadas** con fuente 91/91, mínimo **150 long** y **150 short** para evitar una conclusión unidireccional; 2000/2000 boots válidos, al menos 100 bloques semanales. Si falla, `DEV_DRIVE_UNDERPOWERED`.
8. **Criterio científico de posible señal bruta**: `delta>0`, IC95 inferior `>0` y `mean(GROSS_DRIVE)>0` (todas las anteriores). Si lo cumple: `DEV_DRIVE_GROSS_SIGNAL_ONLY` y siguiente gate **costes y falsación OOS**; si no: `DEV_DRIVE_GROSS_NO_SUPPORT`. No hay target externo de rendimiento ni optimización de umbral post-hoc. El tamaño relativo al spread/latencia se reporta como **desconocido** hasta auditoría posterior.
9. **Cierre disciplinado:** NO probar otro rango 9:15, 10:15, 12:00, otro símbolo, filtros de volumen o cuantiles si G1 falla. Un nuevo experimento necesitaría mecanismo independiente real + prereg nuevo y multiplicidad registrada.

## 3. Enfoque de inferencia

Un eventual efecto positivo es solo **descriptivo y post hoc respecto al conocimiento general de los años ya investigados**, aunque este resultado DRIVE no haya sido consultado para fijar su configuración. No hay OOS virgen de CIBO verificado. La muestra de validación cronológica puede reportarse descriptivamente, **no debe fingir certificación independiente**.

La persistencia en NAS100 CFD puede depender de noticias, horario del broker, rollover y spread. La correlación serial por ISO semana está contemplada de manera aproximada; una señal `delta>0` puede reflejar estructura de volatilidad distinta en vez de causación de order flow, y no implica que ninguna operación pueda abrirse realmente.

Los resultados publicarán: fecha NY, timestamps, signos causal y placebo, formación, retorno Y y contribuciones bps; contabilidad íntegra de missingness y abstenciones; diez años desglosados **sin seleccionar**; hashes de archivos/manifiestos/prereg/código; un solo delta e IC, denominadores y veredicto. Validación independiente de artefactos al cerrar.

## 4. Restricciones de QORE

No usar M1 de VX31, Scalper u otros traders como prueba de edge de DRIVE. **Sin implementación de trader, cognitiva, QDLE, órdenes, modificación Shared/CIBO, MT5, VPS ni capital real.** El programa #789 sigue `0/3 CERTIFIED`.

**Esta congelación precede a todos los retornos calculados por DRIVE G1.**
