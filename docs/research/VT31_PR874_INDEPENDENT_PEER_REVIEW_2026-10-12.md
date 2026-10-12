# VT31 — Revisión independiente del PR #874 (screening direccional M1)
**Fecha:** 2026-10-12 · **Rol:** arquitecto revisor independiente · **Ámbito:** research-only, no cambios COG/OPS, no producción, no OOS.

## Objeto del peer review
- [PR #874](https://github.com/mezas3238-hue/qore-core/pull/874), script `scripts/vt31_edge_directional_15m_preregistered_3y_v1.py`, preregistro y reporte.
- Documento de continuidad [PR #872](https://github.com/mezas3238-hue/qore-core/pull/872); contrato de cotizaciones tests adversariales [PR #873](https://github.com/mezas3238-hue/qore-core/pull/873).
- Evaluar **validez de inferencia y timing** del screening ya ejecutado. NO recalcular 3Y sin la fuente ni ampliar variantes. La nueva suite adjunta comprueba solo *fixtures deterministas sintéticos*, separados de cualquier dato de resultado de mercado.

## Cadena documental comprobada en GitHub
- Commit preregistro `edd3e16183e3cca6d1547faca96cd0b7579253f8` (2026-10-12 21:27:25Z).
- Commit implementación `5a862a34c31bc5966d492bdf47260997eb3832f0` (21:28:59Z), hijo del preregistro.
- Commit workflow `0ff8ae437efd882bd41c0da5058c5e23dfab69a0` (21:29:27Z), después de las definiciones previas.
- Primer resultado CI reportado: [#38310949637](https://github.com/mezas3238-hue/qore-core/actions/runs/38310949637), artifact `11774781034`; documento final `b1d4590af7e22b97a533d160a3788568588ad028` posterior a primer runner. **La secuencia de commits favorece el preregistro, pero una secuencia git no demuestra por sí sola ausencia de cualquier exploración previa externa.**

## Inspección de contrato y código — hallazgos
1. **Identidad y reloj:** `prepare()` exige ID único, 3 minutos exactos entre `source_first_m1_open` y `formed_at`, timezone UTC normalizado y ventanas 03/10/14 New York. `collect_market()` exige M1 1 minuto, monotonicidad y conteo 1,059,784; `screen()` utiliza `open[formed_at]` y `open[formed_at+h]` con todas las aperturas M1 intermedias presentes. El `formed_at` es el cierre del tercer M1 por contrato. **No se observa lectura de precio posterior para seleccionar una señal en estas funciones.**
2. **Ejecutabilidad temporal:** el OPEN del M1 en `formed_at` coincide en reloj con el cierre de la tercera M1. Es un **benchmark de latencia cero e hipotética entrada de mercado**, no prueba de que una orden pudo llegar al broker a ese mismo precio. No reclasificarlo como fill.
3. **Prueba estadística:** el promedio agrupa los 2,140 eventos sin seleccionar CE-touch a posteriori. Bootstrap por semanas ISO NY vuelve a sortear sumas y conteos de semanas y calcula media ponderada por eventos; sign-flip aplica el mismo signo a todos los eventos de una semana. Esta construcción respeta la dependencia intra-semana bajo sus hipótesis, pero la validez exacta de p requiere hipótesis de simetría/intercambiabilidad de signos a nivel semanal; **el p no prueba causalidad ni que invertir señales genere edge**.
4. **Resultado primario y coste:** informe original de 15m: gross `−1.919664` pts, net hipotético `−3.519664` pts, IC95 bootstrap net `[−5.130648, −2.019817]`. Como el coste fijo se resta idénticamente a cada evento, el mismo IC trasladado algebraicamente a gross es **[−3.530648, −0.419817]**. La media adversa del proxy *no se explica por la extrapolación del spread 1.60*: **ya era negativa antes de ese supuesto**. Esto no salva el problema NAS100 vs NDX100, fuente OHLC no verificada como MID y selección no CE.
5. **Unidad correcta de interpretación:** los 2,140 candidatos y la media son un **screening direccional post-FVG**, no 2,140 posiciones ejecutadas, no expectancy de estrategia ICT CE, ni PF, DD, Sharpe, capital, ACK, SL/TP.
6. **Generalización:** los tres años son datos de desarrollo que ya guiaron el diseño previo; el preregistro protege la nueva comparación de horizontes, pero NO convierte automáticamente los resultados en holdout independiente.

## Pruebas adversariales añadidas sin tocar estrategia
`tests/infrastructure/test_vt31_edge_directional_peer_audit.py` verifica: hora NY e invierno/verano, cierre del tercer M1, firmas direccionales LONG/SHORT, cálculo del costo fijo de ida/vuelta, detectores de ID duplicado/formación fuera de ventana/fechas naive, gaps sin forward fill, control de negativo bruto y conversión algebraica del IC publicado. La CI aislada debe ser consultada **antes de afirmar PASS**.

## Veredicto de revisión
**APOYO LA CONCLUSIÓN LIMITADA DEL AUTOR:** `NO_EVIDENCIA_PREDICTIVA_NETA_EN_SCREENING_15M`; la señal direccional *next-open/15m* aparece adversa en la muestra de desarrollo y el efecto no depende únicamente del spread fijado. **NO AVALO ninguna extrapolación a `VT31 ICT CE jamás rentable` ni al edge de una estrategia inversa.**

**P0 compartido para OPS y COG:** (a) doctrina original ICT y contratos de stop/target precedencia; (b) fuente BID/ASK real históricamente equivalente con UTC y tick/contract/currency info oficial; (c) replay PAPER de orden limitada CE con ACK independiente de quote touch (simulated y broker confirmed en categorías separadas), cancel races y límites de ambigüedad; (d) caso contrario cerrar por `DATOS_INSUFICIENTES` con plazo acordado. B 31.31% UNKNOWN permanece FAIL, no habilitarla por haber 577 posibles contactos en spread sintético.

**Prohibiciones:** no editar metodología, no optimizar horizontes, no abrir fresh holdout, no MAIN/VPS/LIVE ni certificar, no sustituir histórico bid/ask por screenshot puntual. Enviar esta revisión al autor del PR #874 y a Issue #727 para colaboración real.
