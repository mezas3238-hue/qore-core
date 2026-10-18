# VT08 B R24 — 809 PS originales del detector requieren reanclaje as-of C3; hechos de fuente y tres casos concretos

**18 de octubre de 2026** · **Arquitecto B**, PR #764 DRAFT, A #765 DRAFT. Programa único Owner **VT08 actual TTrades + cognitiva VT08**; QORE-alpha estrictamente excluido, no sizing, 7Y sealed untouched, no VPS/DEMO/LIVE ni merge.

## Dictamen de auditoría actual

**[CI ORIGINAL FINAL B R24 #39096870184](https://github.com/mezas3238-hue/qore-core/actions/runs/39096870184) — 6/6 SUCCESS**: 18 tests adversariales sintéticos + Ruff y cinco trabajos independientes sobre A R3 original + bytes M3 cTrader originales + blind R19 original SHA congelado. Todos **2.657/2.657** eventos y **107/107** expedientes outcome-blind preservados. El run contiene **logs con 3 casos por mercado seleccionados por orden de `selection_rank_sha256` originalmente preregistrado**, no por resultado. Los tests prueban ataque de primer bajo inventado, CISD futuro, falsa firma, M3 incompleta y acceso a 7Y. Primer intento CI #39096662952 FALLÓ por Ruff import no usado; corregido sin cambiar reglas. Primera corrida completa #39096692008 6/6 SUCCESS; corrida FINAL #39096870184 agrega identificador SHA exacto + UTC + precio del primer nuevo low posterior y conteos de unión.

El detector A original y el verificador B R14 construyen `ps_low_proxy` como **el bajo de una serie M3 bearish precedente al cierre CISD**. Esto es exactamente un PROXY físico, no un protected swing autenticado. R24 verifica los **10 M3 originales cerrados de C2** con `_verify_bar` contra el RAW M3, valida relojes `CISD<=C2.close=C3.open`, el mínimo de la serie original y registra qué pasa **desde la vela que confirmó CISD y en las velas M3 subsiguientes dentro de C2**. El segundo componente B R23 confirma por SHA el preregistro original R19 para extraer 107/107 fichas SIN cambiar la muestra. Se muestran price lows y raw bar IDs en artefactos GitHub Actions privados/con retención temporal, no outcomes ni PnL.

### 1. Tabla verificable, sin exclusión de candidatos ni optimización

| Mercado | Casos | Low serie roto DESPUÉS CISD, antes C3 | Low original más bajo en MISMA M3 CISD | Solapan ambos | Unión: proxy original requiere reanclaje as-of C3 | Sin posterior low menor | Retocó igual low después | CISD al cerrar C2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EURJPY | 538 | 79 | 116 | 23 | 172 | 425 | 3 | 31 |
| USDCHF | 518 | 68 | 105 | 18 | 155 | 411 | 4 | 35 |
| NZDUSD | 550 | 65 | 95 | 22 | 138 | 446 | 8 | 31 |
| CADJPY | 516 | 66 | 119 | 18 | 167 | 414 | 1 | 35 |
| USDCAD | 535 | 70 | 129 | 22 | 177 | 435 | 9 | 21 |
| **TOTAL** | **2.657** | **348** | **564** | **103** | **809** | **2.131** | **25** | **153** |

**Conservación de estados POST-CISD:** 348 + 2.131 + 25 + 153 = 2.657. **Unión de incompatibilidad con origen bajo de la serie original:** 348 + 564 − 103 = **809** (30,45 % del universo fuente-only).

**Importante distinción:** la vela M3 CISD que imprime bajo inferior **lo hizo antes de su propio cierre CISD**; no conocemos el orden de sus ticks, y el low podría ser un nuevo extremo legítimo que deba substituir al bajo de la serie. Un low posterior al CISD tampoco demuestra que **todo setup** sea inválido, pues puede formarse una segunda estructura/cierre; solamente desautoriza usar el `ps_low_proxy` ORIGINAL como mínimo intacto de ese movimiento al abrir C3. Por lo tanto R24 devuelve `new_author_ps_reestablished=D_NOT_ASSESSED`, `author_protected_swing_validated=False`. Nada de 809 «trades perdedores» ni 809 exclusiones económicas automáticas. La cualificación debe ser decidida frente a la fuente original.

### 2. Primeros casos originales reales de revisión humana source-first (no outcomes)

**USDCHF, 27-sep-2023** · `case_id_sha256=83c687ffa373093c3ea211eafdbb4f015f9068cfc8aa0fceb5f8184799bcb990`:
- C2 M30 abre **13:00 UTC**, CISD M3 cierra **13:06 UTC**; bajo original de opposing run `0.91758`.
- M3 posterior cierra **13:12 UTC** con nuevo low `0.91750`, estrictamente inferior a `0.91758`. Original cTrader source bar ID `3d2c6d8041545d87abd49fafc600c68e8da2f5dc21a26f7178bc9001302d456a`. Todo se conoce antes de C3 13:30 UTC.
- **Dictamen físico individual (sin firma):** `ORIGINAL_PS_PROXY_LOW_BROKEN_AFTER_CISD_BEFORE_C3`. Si A pretendiera usar el PS `0.91758` intacto en C3, sería una contradicción de OHLC real. Debe revisar si se creó **otro** protected swing legítimo, con su POI + opposing series+close y la parada fuente, no atribuir el nuevo valor a A sin prueba.

**USDCHF, 07-nov-2023** · `case_id_sha256=c463ba07bb354d4cd617f8d3c0d1a8073a9cd9b67c7c3f19af43b6321189dbae`:
- C2 12:00 UTC, CISD 12:09 UTC, `ps_low_proxy=0.90072`; nuevo mínimo posterior `0.90069` confirmado por barra M3 a **12:15 UTC**, source bar ID `00a27e66ca41b2da89410b6ce7b6ae011d6c750b91638cf24561014f993cae1a`.
- Primera categoría R19 original: `CONTROL_NO_THREE_H1_FVG` **no significa ausencia de otro POI** fuera de esas tres H1 ni que el setup sea autor-inválido. `C3.open=12:30 UTC`; old PS price no es un low intacto en ese momento.

**NZDUSD, 25-feb-2026** · `case_id_sha256=ab42c7b10290b2ab1af37cb9efc479fbc3366fb3f3a601f96810a95d510088d1`:
- C2 09:00 UTC, CISD 09:18 UTC, bajo original de run `0.59735`; M3 cerrada a **09:21 UTC** imprime `0.59733` (source bar `f2e71adf73841b1e67a28ccdb7c27c27eb516565050adcb60b3e24b1c2e0230c`) y ya es conocido antes de C3 09:30.
- Además, la **propia vela CISD tiene low menor que el run low**, pero el orden intrabar no está disponible sin ticks. No se cuentan dos casos: es **uno** en la unión. Revisión de swing alterno y POI sigue `D/WAIT`.

**Contraejemplo físico sin break posterior:** NZDUSD 17-ago-2026, `case_id=44de7cd206a9005a677c344ae5bdeaaec651c19a8858d8043525ac8a5f0c15c1`; FVG bullish H1 pre-CISD presente (estrato R19), c2=08:00/CISD=08:12, run-low `0.59185`; el bar CISD imprime menor low pero **NINGÚN M3 POST-CISD vuelve a cruzar el run-low**. Requiere reanclaje al mínimo de la propia confirmación y, si procede, revisión de POI: NO es una señal certificada por FVG. Este caso demuestra por qué `confirm-bar new low` y `later new low` son categorías distintas.

Todos los cuatro ejemplos proceden de los **tres primeros expedientes por ranking R19 SHA ciego de su mercado**, no fueron elegidos después de examinar performance.

### 3. Fuente primaria TTrades — resolver correctamente la semántica

- [Ideal Formation (27-jun-2026)](https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/), secciones **Understanding Protected Swings** y **The Ideal Candle 2 Formation**: el protected swing necesita barrido + cierre C2/C3 **a través de la serie opuesta que creó el extremo**, en un POI significativo; no igualar C2 bullish con PS válido.
- [Protected Swings (06-ago-2025)](https://ttrades.com/protected-swings-understanding-trends-and-invalidations/), secciones **What Is a Protected Swing?** y **Anticipation vs. Confirmation**: swing low se espera intacto para continuación; no inferir un nuevo PS por simple low ni por cambio de proxy.
- [Let The Wick Form, Trade The Body (29-ago-2026)](https://ttrades.com/let-the-wick-form-trade-the-body-stop-getting-stopped-out/), sección **Place the Stop on the Wick**: el autor expresa que tomar el nivel del PS invalida la premisa de que esa mecha ya esté formada. R24 detecta **touch físico del low**, pero no reemplaza prueba de stop ejecutado BID/ASK, buffer o autoridad de POI/PS. Diferenciar wick breach, close-break y stop-fill; **R24 no afirma 348 stops**.

**NUEVA publicación fuente del día anterior, ausente en R17–R23:** [How to Have Better Stop Losses for Trading (TTFM), 17-oct-2026](https://ttrades.com/how-to-have-better-stop-losses-for-trading-ttfm/). El autor fija reglas escritas de stop: general en swing protegido y refinamiento opcional al **cuerpo opuesto SOLAMENTE si está más allá del 50 % del opposing run**; para reversal el texto también exige medir opposing run. **Clase A para la regla condicional de refinación**, pero qué swing/run/cuerpo seleccionar depende primero de POI/PS verdaderos. No imponer retroactivamente body stop en el arquetipo Example1 M30→M3, donde [Time Frame Alignment](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/) habla de stop debajo de EQ y breaker low. Resolver precedencia/compatibilidad de esas dos fuentes con A+B source review y nunca por PnL.

### 4. Próximos trabajos para certificar en vez de añadir solo instrumentos

**Arquitecto A P0:** analizar ejemplos (USDCHF 27-sep-2023 y 07-nov-2023; NZDUSD 25-feb-2026) con barras SHA proporcionadas, identificar si posterior nuevo low está seguido de OTRO cierre sobre la serie adecuada antes de C3, y qué importante POI fue realmente barrido/tocado. Si no puede, registrar `NOT_SOURCE_SPECIFIABLE_D`; no falsificar firmas, no aplicar una simple sustitución de `ps_low_proxy`. Priorizar los **809** eventos de origen contradicho como estrato de metodología, conservando denominador completo 2.657 y 107 preregistrados. No descartar los otros 1.848 como trades válidos.

**Arquitecto B P0:** contrastar con los originales M3/M15 y revisar independientemente el PS A, vinculando bar IDs, UTC, POI, regla TTrades y disenso. Reutilizar los dossiers R19/R23/Ed25519 **sin fingir claves de revisores**. Cuando exista PS genuino seguir con EQ, breaker low, stop, target HTF untouched y 27 campos cognitivas con fuente/clocks independientes. Después bid/ask neto, OOS pre-registrado, PF/DD/Sortino/Sharpe/MC, sin sizing ni 7Y.

**Estado honesto:** `R24_RAW_PHYSICAL_PASS`; `ORIGINAL_PROXY_REANCHOR=809/2657`; `AUTHOR_VALIDATED_POI_PS=0`; `COGNITIVE=0`; `FILLS=0`; `GATES_NOT_EVALUABLE`; **VT08 NO CERTIFICADO**. Original source SHA no alterado, QORE-alpha totalmente excluido. La ejecución CI valida estructura/bytes/contabilidad, no el valor económico ni un dictamen humano real.
