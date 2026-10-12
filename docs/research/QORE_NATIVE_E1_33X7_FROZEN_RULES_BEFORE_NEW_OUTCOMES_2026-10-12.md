# QORE Native — Protocolo E1 PRE-OUTCOME para evaluación sistemática 33 × 7

**2026-10-12.** El primer contrato D0 ya registra 231/231 celdas sin consultar retornos. Este documento especifica siete modelos **únicos**, con sub-mecanismos dependientes de clase marcados como proxies de sesión. Debe congelarse **antes de cualquier nuevo acceso a resultados** del programa E1 y antes del primer GitHub Action económico nuevo. No convierte resultados anteriores en prospectivos: H4GROSS01, H4GROSS02, H3 NAS100 y panel GROSS04 están expuestos y registrados como tales.

**Status:** `E1_PROPOSED_SPEC_NO_ECONOMIC_RUN`. Reglas sensibles a calendario broker/macro podrían resultar NO-TESTABLE; se reportará cada celda sin censura, incluyendo 0 eventos. No prometer inferencia de apertura bursátil real en FX OTC ni en metales CFD.

## Fuente y marco temporal común

- Único universo: [G0 33/33 original M5](https://github.com/mezas3238-hue/qore-core/pull/829) SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`. Cada worker audita RAW+QUALITY SHA de 11 particiones originales **ANTES de observar cualquier precio**.
- **DEV** `[2016-09-17,2022-09-17)` UTC, **DIAGNÓSTICO temporal** `[2022-09-17,2024-09-17)` UTC. Ambos expuestos al proyecto en diversos ensayos; NO llamarlos virgin OOS. **EMBARGO** para OHLC a partir de `2024-09-17T00:00Z`, incluso cuando la fecha local NY/London cae en otro día.
- Una única señal y exposición teórica por símbolo y fecha local definida. Precondiciones estrictas: todas las barras M5 requeridas exactas, contiguas, alineadas a reloj y válidas de origen; precio `open_relative,close_relative,high_relative,low_relative` >0/coherentes. Cero señal/benchmark -> abstención pareada; ausencia de barras -> registro de exclusión, NO interpolar. No stop, objetivo, trailing ni moneymanagement optimizado: no es un trader ejecutable.
- Retorno gross teórico: `10000*direction*(ref_exit-ref_entry)/ref_entry` bps; delta primaria emparejada: gross estrategia – gross control, idénticas fechas y entrada/salida. **Open/close M5 NO son BID/ASK fill**.

## Definiciones únicas D1 — sintéticas y causales

| Regla | Precio observable ANTES de entrada | Señal del candidato | Control emparejado | Entrada y salida de referencia |
|---|---|---|---|---|
| `REVERSAL_12H` | Bloques M5 UTC exactos [04,08),[08,12),[12,16) | `−sign(close15:55 − open04:00)` | `−sign(close15:55 − open12:00)` | Open16:00→close19:55 UTC |
| `PERSISTENCE_12H` | Idéntico histórico 04–16 UTC | `+sign(close15:55 − open04:00)` | `+sign(close15:55 − open12:00)` | Open16:00→close19:55 UTC |
| `TREND_MULTI_DAY` | Tres **últimas sesiones válidas pasadas** con bloque [16,20) UTC exacto; cada sesión debe preceder a decisión y quedar a lo sumo siete días naturales atrás; además [12,16) del día actual | `+sign(close19:55 del último bloque pasado − open16:00 del primer bloque de los tres)` | `+sign(close15:55 − open12:00)` | Open16:00→close19:55 del día actual |
| `RANGE_BREAK_CONT` | Rango max/min de [08,12) UTC y probe [12,13) UTC | `+1` si close12:55 excede high del rango [08,12); `−1` si cae bajo low; en otro caso abstenerse | `sign(close11:55−open08:00)` | Open13:00→close14:55 UTC |
| `SWEEP_RECLAIM` | Igual `GROSS04`: rango [08,12), probe [12,13) | `−1` si high probe > high rango y close probe vuelve dentro; `+1` si low probe < low rango y close vuelve dentro; excluir barridos dobles | `−sign(close12:55 − open12:00)` | Open13:00→close14:55 UTC |
| `OPEN_INITIAL_REACTION` | Local *session reference* −15 min a +15 min exactos | `sign(close del primer +15min − open de la referencia local)` | `sign(close última M5 antes de la referencia − open15min antes)` | Open +15min → close +30min |
| `POST_OPEN_CONT` | Local *session reference* −30min a +30min exactos | `sign(close del primer +30min − open de la referencia local)` | `sign(close de los últimos −30min − open −30min)` | Open +30min → close +150min; para NAS100 replica target10:00→11:55 del ensayo anterior |

**Session reference = NO equivalencia automática con apertura real:** índices `09:30 America/New_York`, referencia CFD al cash open USA; FX mayores/cruces `08:00 Europe/London` = transición de liquidez OTC; metales `08:00 America/New_York` = ventana de investigación de liquidez USA NO comprobada como COMEX official open. Aplicar DST ZoneInfo a cada timestamp real, exigir que ventanas caigan en mismo día local y comprobar identidad broker real por separado. Ninguna señal del futuro entra en el cálculo del signo.

**Correlación conceptual explícita:** REVERSAL_12H y PERSISTENCE_12H son opuestos sobre las mismas fechas si sus precondiciones coinciden. OPEN_INITIAL_REACTION y POST_OPEN_CONT comparten la primera ventana parcialmente. RANGE_BREAK_CONT y SWEEP_RECLAIM pueden ser mutuamente excluyentes bajo definiciones de close. **No son siete fuentes estadísticamente independientes de alfa**. Solo se consideran mecanismos operativos, la inferencia corrige multiplicidad.

## Cuándo una celda de las 231 cuenta como «probada»

- El código escribe `strategy_n`, `baseline_n`, `weeks_n`, `excluded_n`, `gross_mean_bps`, `paired_delta_mean_bps`, intervalo y procedimiento, costes hipotéticos, `source_sha` y run HEAD, **incluso** si 0 eventos o pérdidas; no se permite omitir símbolos incómodos.
- Celdas anteriormente examinadas deben llevar marca `PRIOR_EXPOSED`. Las **33 sweep/reclaim** no pueden presentarse como confirmación independiente de GROSS04: si se recalcula para uniformizar el panel, su resultado anterior sigue NO_SUPPORT y el nuevo cómputo es **reproducción**, no un nuevo test independiente.
- No optimizar 33×horas, 33×ATR, 33×R; las horas arriba son las únicas opciones para este prereg.
- Mínimo operativo de análisis: `DEV>=150` eventos y `>=52` ISO weeks, `DIAGNÓSTICO>=50` y `>=26` ISO weeks. Si falla: `UNDERPOWERED_OR_NON_APPLICABLE`, nunca excluir del denominador 231; analizar potencia real por clase/familia.
- Para 231 tests de delta **solo dentro de un protocolo E2 aprobado**: `Holm-Bonferroni` FWER de 5% usando p-valores por bootstrap **semanal sincronizado** (o procedimiento más conservador validadamente calibrado). No usar n=231 como muestras independientes. El resampling del conjunto se sincroniza entre las 33 series y todos los métodos, conserva shocks macro cruzados, y analiza sensibilidad a bloques de 2–4 semanas. Efectivo número de factores **NO ESTIMADO**, evitar fórmulas a ojo. Mostrar 7 agregados de método, 4 familias, 33 filas de instrumento, y cada celda con estimación/CI descriptiva, ajustado y sin ajuste.
- Gate soporte candidato bruto (NO certificado): delta >0 y estabilidad de signo/dev-diagnóstico, IC corregido contra cero, gross absoluto >0, coste hipotético `0,1,3,5,10,20` bps de ida/vuelta y break-even absoluto. La entrada teórica OHLC no acredita spread/slippage, por lo que no declarar trader ejecutable, PF net, sortino net ni DD real aunque pase inferencia.
- Macro calendario conocido-as-of, noticias alto impacto, horarios broker y comisiones todavía **NO verificadas**. Todo test económico es `RESEARCH_GROSS_NEWS_UNFILTERED` y bloqueado para QORE Native NO-NEWS / producción #814. No abrir 2024+ por ninguna razón sin otra autorización/regla prereg independiente.

## Gates sin ambigüedad

`D0` = **DONE** (231 celdas registradas, 0 nuevas métricas). `D1` = definiciones cerradas en el presente documento pero **RUN BLOCKED** hasta comprobar pruebas causales de reloj, no-lookahead, datos, e implementación contra fuentes originales. `D2` = reproducción/ejecución exhaustiva de las metodologías no previamente probadas, **todos los 33, no selección ex post**. `E2` = agregación inferencial, corrección múltiple y reporte, exige firmas por 33. `G1` = economía net + no-news PIT + fills/SL, todavía bloqueado.

**No anunciar ahora 231 resultados económicos.** Esta congelación de reglas por sí sola no prueba ganancias y NO debe sobreescribir los cuatro NO_SUPPORT pasados. 0/3 traders certificados, no LIVE/VPS/MT5/CIBO/Shared/QDLE.
