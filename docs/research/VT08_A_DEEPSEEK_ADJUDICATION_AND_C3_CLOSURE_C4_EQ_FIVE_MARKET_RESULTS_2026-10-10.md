# VT08 P0-A — INFORME VERIFICADO: DEEPSEEK TRIAGE + C3 CLOSURE→C4 + EQ CAUSAL
**2026-10-10** · Architect A metodología · draft [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765), issues #762 / #763 · GITHUB research-only · 7Y sealed NO leído.

## 1. Validación de fuente frente al informe DeepSeek

Fuentes originales contrastadas (no aceptar afirmaciones DeepSeek sin verificación):
- C3 Closure diciembre 2025: https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/
- Daily Bias diciembre 2025: https://ttrades.com/easy-daily-bias-a-mechanical-trading-framework/
- C3 continuación septiembre 2025: https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/
- C2 agosto 2025: https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/
- EQ expansión agosto 2025: https://ttrades.com/using-equilibrium-in-continuations/
- EQ aclaración publicada HOY octubre 10 2026: https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/
- CISD y validación HTF: https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/

**Aceptamos A verificado:** C2 completed reversal closure requiere sweep C1 y regreso al rango; C3 continuación tras C2 reversal y POI LTF; C3 Closure cuando C2 no otorga cierre, C3 cierra estrictamente sobre/bajo cuerpo C2 sin barrer extremos, puede originar expectativa C4; daily EQ continuation necesita contexto direccional + POI + closure + CISD, no EQ aislado.

**Rechazamos como SOURCE-A sin evidencia:** wick grande/pequeña >/<50% C2, `CISD caduca exactamente 8 M15`, `C4 entra directamente en EQ`, `nearest PS always`, `+200–300` candidatos C3 / `20–35%` oportunidad total. La última es pronóstico no medido. C3 continuation exige as-of **DENTRO de C3** para abrir C3; confirmar C3 cierre y pretender un fill anterior C3 es lookahead. Nueva York mantiene 01/05/09 local durante DST; cambia UTC offset, nunca se autoriza convertir 01 NY→02 NY.

**Corrección crucial EQ:** el artículo del autor de 2026-10-10 establece C2 a favor del swing => full high/low; C2 contra swing => close-to-extreme; C3 closure => full range, por lo cual no universalizar el viejo EQ `(H+L)/2` a toda C2. Nota: la precisión EQ 2026 es posterior, no un atributo literal demostrado del vídeo 2025.

Prerregistro separado congelado ANTES de replay en commit `7e5ceb2b1cea6a3a7418ac837564fcda8eb8ce68`, [VT08_A_DEEPSEEK_TRIAGE_AND_C3_CLOSURE_TO_C4_SHAPE_PREREG_2026-10-10.md](VT08_A_DEEPSEEK_TRIAGE_AND_C3_CLOSURE_TO_C4_SHAPE_PREREG_2026-10-10.md).

## 2. Código nuevo entregado

- `src/qore/infrastructure/trader_lab/vt08_5m_c3_delayed_closure_c4_shape_census_v1.py`: censo causal de C3 Closure→C4 con C1-C2-C3 completas, ausencia de reversión confirmada C2, C3 strict close over/below C2 body (NO C2 high/low sweep), distinción de body-engulf fuerte, sesgo viejo as-of, PS/CISD M15 **proxy interno** separado de POI de autor, EQ de C3 después de cierre y observación C4 primera M15, y permiso Owner para C4 en 01/05/09 NY. **NO CandidateEvent ejecutable, no take-profit, no SL, sin operaciones**.
- `src/qore/infrastructure/trader_lab/vt08_5m_ttrades_c2_c3_source_eq_range_v1.py`: fuente mecanizada de EQ de C2 *full vs close-extreme*, de C3 *full*, con orden estricto de closed H4→decision, doji C2 UNKNOWN y `closure_adjudicated` requerido. Este helper **no decide dirección, POI ni entradas**; nunca autoriza por sí solo cambiar `BIAS_UNRESOLVED` a LONG/SHORT.
- Pruebas adversariales `test_vt08_5m_c3_delayed_closure_c4_shape_census_v1.py`, `test_vt08_5m_ttrades_c2_c3_source_eq_range_v1.py`: no dato C3 sin cierre, no sweep C2, igualdad body rechazada, C4 sólo después H4 C3, NY local mismo reloj invierno/verano, EQ desde fuente e invalidación de futuro y doji.
- GitHub workflow `.github/workflows/vt08-a-c3-delayed-closure-c4-shape-1095d-v1.yml`.

## 3. Replay 1095D — éxito 5/5, fuente M15 CONSUMIDA

[GitHub Actions run #38083479769](https://github.com/mezas3238-hue/qore-core/actions/runs/38083479769) **SUCCESS 5/5**; source/test exact SHA `90f8527d06b77418789fcc98ba2ff6320ecd558c`; por mercado Ruff PASS, Pytest **18 passed**, output hash artifacts. Evidencia read-only upstream #35934924907 SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`, no holdout 7Y.

| Mercado | C1/C2/C3 H4 completas | C2 failed reversal closure | C3 strict body-close/no C2 sweep SHAPE | C4 at Owner 01/05/09 | C3 HTF shape + old bias + internal M15 PS proxy + Owner |
|---|---:|---:|---:|---:|---:|
| EURJPY | 2250 | 1574 | 79 | 56 | 12 |
| USDCHF | 2250 | 1609 | 54 | 36 | 8 |
| NZDUSD | 2248 | 1542 | 63 | 46 | 11 |
| CADJPY | 2248 | 1509 | 64 | 50 | 10 |
| USDCAD | 2248 | 1612 | 34 | 25 | 4 |
| **TOTAL** | **11244** | **7846** | **294** | **213** | **45** |

**Definiciones estrictas**:
- **294** = `SHAPE_ONLY_NOT_SOURCE_COMPLETE`, **no trades**; incluye 36 stronger C3 body-engulf proxy, 129 LTF CISD/PS interno proxy, 120 old daily bias aligned (no implica POI validado), 236 primera M15 C4 cerró del lado correcto de EQ y 188 first-M15 wick reentered half; NO utilizar después de entrada para decidir apertura C4.
- **213** C4 owner permitted **solo la H4 de continuación**; los otros **81** C4 abren fuera de 01/05/09 NY (p. ej. 13NY posterior a 09NY), quedan clasificados pero no operables con mandatos Owner actuales. Nunca cambiar relojes para aumentar volumen sin autorización.
- **45** es intersección *proxy* owner + B01 daily bias + M15 PS interno; sigue sin POI fuente validado ni full cognition, entonces **0 candidato SOURCE_COMPLETE, 0 órdenes, 0 fills, 0 PnL**.
- La definición "`C2 failed reversal`" separa C2 que no barre C1 y C2 que barrió pero no completó reversal closure; no todos esos C2 son por sí mismos C3 closure (7646 etc sin C3 confirmación). C3 actual debe cerrar H4 ANTES de evaluar C4.
- No restar/sumar estas 294 a los 488 B01, 252 C3 FVG shapes ni 1514 trades OHLC intracycle (ese ensayo previo PF/DD falsado), porque familias y ventanas se solapan y no son todos fills.

### Evidencia replicable por mercado

GitHub Actions #38083479769, ZIP por mercado incluye JSON de **cada shape** + resumen/año (retención 30 días):
- EURJPY Artifact ID `11681122873`, sha256:29e40cb4d5f32c0df0c80872ac8306e6781da76f060906e7a0bd18e073f8acfc
- USDCHF Artifact ID `11681357657`, sha256:147249d5309d4866b0709f13df942e252a27dfa52c3a82b532822496735fe471
- NZDUSD Artifact ID `11680928493`, sha256:3a814667fc8caebcb08bf3634160eec488a705081519ae531b39891cb58e6a33
- CADJPY Artifact ID `11681507366`, sha256:ec3a8bb52f4d4f04390bca20fca8002529757d7ea6fd3bfbbcd1a7092dfc7d3f
- USDCAD Artifact ID `11681147894`, sha256:876194ed4c5a8b9d51df0275b2c7d705eaa7d805e5da8161f8e9d5a8dc480d45

## 4. Consecuencias científicas y coordinación A/B

1. DeepSeek **acierta** sobre ausencia de familias y POI, pero sus supuestos de 50% wick, caducidades y densidad futura carecen de autoridad fuente; no hacer implementaciones ejecutables a partir de esos números.
2. El censo es un límite descriptivo **estrecho**; no permite declarar "C3 Closure tiene 294 trades" ni que 20% del modelo está recuperado.
3. Arquitecto B debe conservar `cognitive_ready=False` para shape-only, y falta todavía source POI+Swing confirmation y todos los features `CAUSAL_FIELDS` del Situation Model y manifest conjunto; source bias H4 M15 real ya disponible en otro bundle A.
4. Siguiente P0: POI reales/high/low/swing + CISD/PS LTF adjudicados para C3/C4 y daily EQ continuation con premisa direccional derivada de vela cerrada; cálculo temporal sin un único cutoff fingido. Al completar source methods, dar al arquitecto B **CandidateEvent** y no shape indiscriminado.
5. Decisiones económicas post-P0: target de liquidez, stop validado por swing/cuerpo, BID/ASK/spread/comisiones/slippage, y 100% cognition-on vs method-only replay pareado sobre mismo universo/datos. WFO/MC y sellado 7Y después de congelación. **No VPS, DEMO, LIVE ni broker.**
