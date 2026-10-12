# QORE-Alpha 2 W2 — PADE v0.1 preregistro económico causal PRE-RESULTADOS

**2026-10-12 / investigación aislada / PROPUESTA DE HIPÓTESIS COMPLETAMENTE NUEVA.**
PADE = *Presión de Actividad con Desplazamiento Escaso* (participation–displacement elasticity).
**No** copia los siete esquemas QORE Native, TTrades ni Silver Bullet.
Es una hipótesis propia **falsable**, no una promesa de rentabilidad ni de originalidad matemática universal.

## Congelación científica y antecedentes expuestos

- W1/PATR: 224 señales, 176 pareadas brutas, retorno medio DEV −0,1674 bps y DIAG −3,4237 bps, comparación parcialmente tautológica y potencia insuficiente. **W1 CERRADO: NO SUPPORT / UNDERPOWERED. No retocar sus parámetros.**
- W2 G0 source 33/33: GitHub Actions #38273144621, exact-head `acf421591a2ded838b0bd73fc6a98a0d918d81e6`, 19.496.136 registros M5 anteriores a `2024-09-17T00:00Z`, campo `volume` entero positivo en todos. Fuente 33 certificada SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`.
- El campo `volume` se trata únicamente como **actividad reportada por el proveedor (proxy)**. No sabemos si representa ticks o volumen ejecutado; no etiquetar como order flow de bolsa. El origen de los 12 Atlas y 21 IC Markets DEMO no está demostrado como una misma cuenta, por tanto analizar separadamente cohortes.
- DEV `[2016-09-17,2022-09-17)` y diagnóstico temporal `[2022-09-17,2024-09-17)` ya fueron estudiados por otros experimentos de QORE; **ninguno es OOS virgen**. OHLC desde `2024-09-17` embargado: no abrir ni para señales, ni resultado, ni reentrenamiento.

## Mecanismo único hipotético

Durante una hora completa con **actividad excepcionalmente elevada** pero **escaso desplazamiento neto del precio**, compradores y vendedores compiten en el mismo rango. La dirección de la actividad de velas M5 ponderada por `volume` puede contener información sobre qué lado domina, incluso si la vela H1 termina casi donde empezó. Hipótesis direccional: la siguiente expansión se inclina hacia el desequilibrio de actividad firmada.

No se afirma que cada cambio de precio M5 sea una ejecución compradora/vendedora real. No se afirma que el predictor sobrevivirá a costes.

### Regla fija de fuente y calendario

- Universo total: 33 símbolos; cada worker descarga RAW original (12 Atlas run #35166210458 o 21 ICMarkets DEMO run #38193802541), manifiesto G0 run #38207337960, y revalida once particiones anuales RAW+QUALITY antes de examinar cualquier OHLC.
- Tiempo UTC exclusivamente. Considerar 8 bloques H1 `[08:00,09:00), ..., [15:00,16:00)` de cada día de lunes a viernes; bloque de exactamente 12 M5 contiguas con hora y minuto correctos, sin sustituir periodos faltantes. Por símbolo y día, **a lo sumo una señal**, la primera hora que satisfaga las reglas; no elegir el mejor precio/dirección a posteriori.
- Para cada hora `h`, usar exactamente las 10 últimas horas `h` completas en **10 fechas UTC anteriores distintas**, con máximo de 35 días de antigüedad. Mediana de su `sum(volume)` = línea base conocida. No usar el propio día en ese cálculo.
- Señal en cierre H1 `decision = h + 1h` sólo si: `sum(volume)` actual / mediana previa >= **1,65**; rango H1 `max(high)-min(low) > 0`; `abs(close_last-open_first)/rango_H1 <= 0,20`; desequilibrio `I = Σ(volume_m5 * sign(close_m5-open_m5))/Σ(volume_m5)` con `abs(I) >= 0,30`; dirección `sign(I)`. Volúmenes cero/nulos/invalidables, o cualquier bar M5 inválida => abstención y razón contada.
- **Control direccional pareado genuinamente independiente**: dirección `sign(close_{h-1}−close_{h-3})` usando exclusivamente H1 completadas anteriores con continuidad temporal exacta. Si es cero, ambos brazos se abstienen y se registra la razón. Este control NO está forzado por la condición `I`; una comprobación sintética exigirá casos de dirección opuesta para descartar el defecto algebraico de W1.
- Stop fijo en unidades del precio del origen: mediana de **las 20 H1 completas anteriores**, todas contiguas y cerradas antes de la hora de señal; si no existen, abstenerse. No introducir ATR, ML, tunings por símbolo ni reglas del autor de otra metodología.
- Primera entrada teórica en `decision + 5 minutos`, al OPEN de la M5 nativa exacta; distancia stop `d=mediana(rangos_H1_20)`; salida target `2d`; vencimiento exacto `entry+4h`. Mismas entrada, distancia, target simétrico, reloj y reglas para control. No operaciones simultáneas por símbolo por regla de una diaria.

### Política de ejecución adversarial (sólo proxy GROSS)

- Faltante M5 en trayecto/entrada/vencimiento => CENSURADA, no imputar retorno. Stop/target simultáneos en la misma M5 => STOP primero. GAP desfavorable apertura más allá de stop => salida al OPEN adverso; favorable al target => máximo TARGET, nunca mejora gratis. Sin trailing/breakeven/parciales.
- `R=dir*(exit-entry)/d` y `bps=10000*dir*(exit-entry)/entry`. **OPEN de OHLC no es BID/ASK ejecutable.** La financiación, spread, slippage, commissions y PIT noticias no se conocen; PROHIBIDO afirmar PF/Sharpe/Sortino/DD NET ni trader certificado.

### Comparaciones y falsación predefinidas

- Único contraste inferencial: diferencia PATR-NO, **PADE bruto − control de tendencia retardada de dos horas**, pareados misma oportunidad y mismo riesgo nominal, panel completo 33. PnL absoluto PADE como segundo requisito económico (no p exploratorio adicional).
- Reportar 33 filas de mercado incluidas las de 0 eventos, cuatro familias, origen 12/21, years/folds, censura por razón, meses/semanas y simultaneidad. Desarrollo requiere ≥**150 pareadas y 52 semanas**; diagnóstico ≥**50 pareadas y 26 semanas**; cada cohorte también debe superar ≥20 eventos diagnósticos para considerarse generalizable entre orígenes.
- Bootstrap de calendario sincronizado 1/2/4 semanas, 4000 réplicas por era, semilla 20261012, un solo conjunto de semanas para todos los mercados (preserva shocks cruzados) y semanas de cero actividad; diferencia positiva, IC95 con extremo inferior >0 bajo todos los bloques y bruto medio positivo en **ambas eras**. Sensibilidad de coste ida-vuelta `0,1,3,5,10,20 bps` sólo hipotética, no resultados NET.
- Cualquier fallo => `NO_SUPPORT`, `UNDERPOWERED` o `SOURCE/REPLAY_BLOCKED` según corresponda; no seleccionar una subfamilia ganadora a posteriori. No reabrir ni retunear con el mismo historial. Si pasa grosso modo, sólo `GROSS_RESEARCH_CANDIDATE`, nunca certificación.
- Sin búsqueda masiva de variantes, sin p-hacking, sin selección de resultados. Análisis futuro sólo con nuevo prereg y reserva realmente independiente, no reutilizar 2024+ sin permiso explícito y diseño de holdout.
- Gate UTC-001 posterior exige **cada año/fold**, BID/ASK real, news PIT, risk book causal, potencia, Monte Carlo y PF/E/Sharpe/Sortino/DD NET; nunca autorizar VPS/MT5/CIBO/Shared/QDLE/LIVE por éxito de este ensayo.

**Este documento debe quedar en commit ancestral del primer job que lea outcomes PADE.**
