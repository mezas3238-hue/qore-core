# LON-A / Gate A — Segunda adjudicación de fuentes, temporalidad y reglas de ejecución

**Issue:** [#785](https://github.com/mezas3238-hue/qore-core/issues/785).
**PR de trabajo:** [#788](https://github.com/mezas3238-hue/qore-core/pull/788).
**Estado:** `GATE_A_PARTIAL / AUTHOR_EXACT_BLOCKED / NO_ECONOMIC_REPLAY / NO_LIVE`.

## 1. Nuevas fuentes originales verificadas en esta ronda

### A6 — [Easy Daily Bias: A Mechanical Trading Framework](https://ttrades.com/easy-daily-bias-a-mechanical-trading-framework/), 13 dic 2025
- Apartado **Framing a Reversal Day**: reversión se enmarca cerca de máximo/mínimo de jornada previa; wick pequeña vs grande condiciona anticipación vs espera.
- Apartado **Framing a Continuation Day**: después de cierre alcista, retroceso previo a EQ del día anterior y posible expansión a su máximo; inverso para bajista.
- Apartado **Using Lower Timeframes for Confirmation**: para Asia/Londres sugiere H1 o M30, y para NY M5/M15. **Esta selección de LTF de otro artículo NO sustituye el M15 explícito de LON-A**.
- **Adjudicación:** confirma familias de sesgo Daily pero NO resuelve cómo elegir sin ambigüedad entre reversión y continuación cuando coexisten señales. No convertir ni H1 ni M30 en trigger londinense.

### A7 — [Stop Loss Mastery: Using Protected Swings](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/), 7 ago 2025
- Apartados **What is a Protected Swing** y **Why Use ... Stop Loss Placement**: la invalidación estructural alcista se referencia bajo protected low; bajista sobre protected high.
- Apartado **Adjusting for Risk-to-Reward**: alternativa sobre el cuerpo de la vela o esperar otro swing de continuación; el autor ADVIRTE que más R:R puede implicar ser expulsado sin invalidación estructural.
- **Adjudicación:** ancla swing high/low respaldada, pero **ni buffer en pips ni tratamiento de spread/saltos ni precio ejecutable exacto** definidos como regla universal LON-A. Stop body es alternativo: no elegir ex post el que optimiza P&L.

### A8 — [How to Trade Candle 3 in the Fractal Model](https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/), 6 sep 2025
- **The key concept: wick size and expansion**: el autor diferencia vela C2 con mecha pequeña/grande para trade C2 vs esperar C3.
- **Trading Candle 3**: espera cierre HTF de reversión y confirmación LTF CISD / POI / protected swing.
- **Adjudicación:** no hay ratio wick/body o ATR canónico para grande/pequeña. Cualquier threshold numérico será variante QORE, no exacta del autor. No confundir ejemplo Daily→Hourly de A8 con LON-A Daily→H4→M15.

### A9 — [How To Use Equilibrium (EQ) — TTrades Fractal Model](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/), 10 oct 2026
- Apartados **Using EQ With Full Bodied Candles**, **Using EQ With Large Wicks**: define EQ como el 50% de un rango; para C2 a favor del swing usa full range; C2 en contra usa tramo `close ↔ wick extreme`; para C3 usa full range.
- **When EQ Is Not Respected**: EQ es contexto, no una señal standalone.
- **Critical gap**: decidir *qué swing* es válido, *qué vela* pertenece a C2/C3 y *si* el cierre es en contra del swing depende de estructura que debe conocerse causalmente. Aplicar la fórmula geométrica al swing elegido retrospectivamente introduciría lookahead.
- **Adjudicación:** aquí SÍ se certifica una fórmula de 50% CONDICIONADA a haber elegido causalmente la rama; no se certifica el selector de ramas/swing para LON-A. Además A9 es POSTERIOR al artículo Londres (un mes): mejora la comprensión del concepto, **NO prueba que TTrades ya exigiese esa misma rama el 12-sep**. Registrar `AUTHOR_LATER_CLARIFICATION_UNCONFIRMED_RETROACTIVE_APPLICABILITY`.

### A2 — [How CISD Confirms Swing Points](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/), 10 ene 2026, lectura cruzada
- **How I Use CISD With Swing Points / CISD Without HTF**: el autor exige relacionarlo con cierre Candle2/Candle3 HTF, y CISD dentro de esa vela.
- **The Fractal Nature**: presenta el orden HTF closure → LTF CISD → continuation como disciplina de verificación.
- **Adjudicación causal:** si el CISD M15 ocurrió durante la vela H4, detectarlo retroactivamente al cierre H4 es válido como *evidencia a partir del cierre H4*, **pero no habilita entrada anterior**. Tampoco basta ver H4 cerrar para certificar que el swing fue operable en el M15 previo. Una ruta que opere H4 aún abierta requiere prueba AUTORAL explícita de provisionalidad y timestamp comparable.

## 2. Decisiones LON-A que siguen bloqueando una versión `author-exact`

| ID | Certificado conceptualmente | Sin resolver para ejecución única |
|---|---|---|
| LA02 Daily bias | Daily previo + familias reversión/continuación, A0/A6 | selector único priorizado frente a conflictos, hora de ancla Daily, precondiciones POI |
| LA03 C2/C3 y POI | necesidad de cierre y nivel importante, A0/A2/A8 | swing y Candle2/Candle3 disponibles causalmente, definición de POI/no-trade |
| LA04/LA06 Wick Daily/H4 | wick primero y body después, A0/A1/A8 | first-known `wick formed`, aceptación de provisionalidad, criterio pequeño/grande |
| LA05/LA07 H4 swing | estructura/swing y posible cierre C2, A0/A2 | si cierre H4 es anterior al trigger M15 o se permite actuación intra-H4 |
| LA08/LA09 M15 CISD / protected | cierre a través serie creadora, A0/A2/A7 | delimitación formal causal de la serie y selección del swing |
| LA10 Entry | ponerse a favor de continuación tras confirmación, A0 | precio exacto, ventana, retest, orden, expiry, noticia, no-trade |
| LA15 Target | extremos HTF o DOL, posibilidad runner, A0 | cuál objetivo conocido primero y orden de parciales |
| LA16 Stop | bajo protected low / sobre high, A7 | estilo wick/body entre variantes, buffer/spread/slippage y fills |
| LA11 Time | setup prevalece sobre reloj, A0 | fecha/hora y timezone ancla 22:00/02:00/06:00 de PDF; no convertir en killzone universal |
| LA14 SMT | confluencia opcional en escenarios avanzados, A0/A4 | si se usa, evento de swing correlacionado causal, sin arbitrario +10M1 |

**Contra una falsa simplificación:** `M15 close through arbitrary n opposing candles` no es author-exact. La elección de 'serie que hizo el extremo' y el protected swing debe poder auditarse instante por instante. Tampoco `previous-day close bullish = daily long always` es ley de A0.

## 3. Dos protocolos temporales mutuamente distintos: congelar antes de mirar P&L

**P-CONSERVATIVE / CLOSED_H4_SAFE_VARIANT** (QORE ingeniería, NO author-exact): cierre Daily pertinente ya disponible; H4 cerrada y swing sustentado en evidencia causal; M15 CISD de vela YA cerrada; la entrada no puede preceder la última confirmación efectivamente conocida. Si el CISD se observó dentro de H4 aún abierta, solo sirve retrospectivamente desde que H4 cerró; no se ejecuta al precio pasado. Esta ruta puede *perder entradas legítimas intrabar* y no debe disfrazarse de TTrades exacta.

**P-PROVISIONAL / INTRA_H4_AUTHOR_UNRESOLVED**: permitir actuar sobre mecha H4 antes de que H4 cierre, apoyándose en M15 ya cerrada y datos parciales. Sería una interpretación posible de gráficos/retórica del artículo LON-A, pero su admisibilidad depende de prueba fuente con escenas timestamp genuinas, contrato de 'wick formed' y ausencia de futuros H4. NO se implementa ni se autoriza con la evidencia actual.

Se rechaza arbitrar entre P-CONSERVATIVE y P-PROVISIONAL por comparación posterior de PF o DD. Si persiste indeterminación, solo se puede estudiar con etiqueta `QORE_VARIANT`; dictamen `AUTHOR_UNDERDETERMINED` para réplica exacta.

## 4. Auditoría de ingeniería ya versionada — protección frente a lookahead

- [Guard first-online](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/src/qore/infrastructure/trader_lab/qore_london_lona_first_online_chronology_gate_v1.py): módulo independiente de señales que usa D1/H4/M15 con `first_known_utc`, `bar_close_utc`, `observed_until_utc` y evidencia por regla. Solo admite **UTC explícito**, rechaza cierre futuro o sello intrabar imposible. Descarta cualquier evidencia recibida DESPUÉS de la decisión, manteniendo invariancia de prefijos. Distingue CISD **dentro de la H4** (válido solo retrospectivamente desde el primer conocimiento del cierre H4; **prohibido backdate fill**) de CISD M15 **posterior a H4**. El mínimo momento posible para una decisión está marcado como `chronology_ready_not_before_utc_not_a_fill`; no equivale a precio de entrada. Exige que Daily bias se conociera antes de la evidencia estructural. Datos parciales de wick son observaciones, **NUNCA prueba de wick finalizada**.
- [Synthetic tests](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/tests/infrastructure/trader_lab/test_qore_london_lona_first_online_chronology_gate_v1.py): casos de fuente de otro modelo, disponible después de cierre, M15 prematuro, H4 futura, mezcla EUR/GBP, error DST por local time, duplicados, wick ex-post, append de futuro. No utiliza datos ni código L1/L2/V49.
- [GitHub Actions](https://github.com/mezas3238-hue/qore-core/blob/research/london-lona-gate-a-primary-evidence-20261011/.github/workflows/qore-london-lona-first-online-chronology-no-replay.yml): ejecuta únicamente tests sintéticos y escribe resultado **fail-closed**, sin replay económico. El resultado de CI debe verificarse por URL/run antes de proclamar que está 'passed'.

**Limitaciones expresas del guard:** la identidad `DAILY_BIAS_CLOSED / H4_SWING_CLOSED / M15_CISD_CLOSED` la pasa el *fixture* o productor; el guard de tiempo no prueba matemáticamente que una vela realmente sea protected swing/CISD, ni asegura por sí mismo integridad del feed/proveedor o el origen auténtico de un timestamp. Éstos son Gate A/B/C futuros. El campo `source_id` es una etiqueta, no autenticación criptográfica. **Limitación adicional:** cualquier proveedor que falsee/anticipe `first_known_utc`, o una asignación inventada de barras a rol CISD, puede engañar al guard; es barrera parcial, no prueba de dato completo o de fuente. **Un CHRONOLOGY_PASS_ONLY jamás autoriza trades, rendimiento, producción o la palabra 'fiel'.**

## 5. Próxima misión del arquitecto

1. Revisar una muestra de vídeo Londres con evidencia de t=HH:MM:SS *del vídeo real* cuando haya vía disponible; no atribuir timestamps de voz no observados. Capturar casos con fracaso y sin entrada.
2. Precisar causalmente el selector de swing y la serie CISD (con puntos disponibles en tiempo real); no trasladar cifras de geometría de otros traders.
3. Reconciliar prioridad entre Daily bias reversión/continuación y EQ; fijar si el artículo 10-oct se incorpora como aclaración posterior o como otra variante y congelarlo explícitamente.
4. Abrir diagnóstico de datos D1/H4/M15, UTC/DST y cobertura por proveedor. Verificar el run real de CI del guard, reparar fallos si aparecen.
5. Nunca ejecutar replay económico hasta Gate A fuente+contratos, Gate B datos, Gate C motor validado y Gate D periodo OOS no consumido.

**Certificación al cierre:** `LON_A_SOURCE_AUDIT_PARTIAL`, `FIRST_ONLINE_GUARD_CODED_NOT_INTEGRATED`, `AUTHOR_EXACT_BLOCKED`, `NET_EDGE_UNTESTED`, `NO_VPS_MT5_LIVE`.
