# Trader Scalper — Tercera auditoría DeepSeek: target H1 y ensayo factorial stop M15/M1

**Fecha:** 2026-10-10. Arquitecto B, PR #759 / issue #757. Arquitecto A, PR #758 / issue #756. Parent #623. Todos los trabajos: GitHub Actions, no VPS, NO LIVE, NO MERGE; no certificado.

## 1. Correcciones de método antes de alterar políticas

**Autor TTrades, verificado en fuentes primarias:** [Scalping Model (7-Feb-2026)](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/) sitúa el sesgo operativo en H1, estructura M15 y ejecución M1; formula stops en protected swings lógicos y targets en objetivos HTF. Su referencia Daily es contexto general, no un filtro autorizable por la arquitectura QORE. [Stop Loss Mastery (7-Aug-2025)](https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/) describe stop protegido y alternativas cuerpo de vela/continuación para gestionar R:R; **no** prescribe un múltiplo fijo de ruido M1 4× a 8× ni stop único M15 obligatorio. [Let The Wick Form (29-Aug-2026)](https://ttrades.com/let-the-wick-form-trade-the-body-stop-getting-stopped-out/) exige estructura de cierre CISD sobre la serie de velas opuestas; el sweep no confirma por sí solo la reversión.

**Error a evitar:** que las pérdidas STOP se expresen como -1R *por definición* en el replay V49 **no prueba** que el stop M15 fuera geométricamente óptimo. La afirmación de DeepSeek «asimetría no está en la entrada ni sesgo H1» no está demostrada por MFE/MAE ni por pagar targets pequeños. Ambas causas pueden coexistir. El umbral 71,8% corresponde a un juego binario hipotético STOP -1R / TARGET +0,392R, **no** a todo V49 que incluye 381 salidas por fin de sesión. El promedio MFE vs MAE tampoco demuestra qué movimiento ocurrió primero dentro de una vela.

## 2. Evidencia target H1 9/9, PREREG congelado sin cambios

Workflow [GitHub #38059512447](https://github.com/mezas3238-hue/qore-core/actions/runs/38059512447) SUCCESS; lector `capitalizer_scalper_h1_target_asymmetry_audit_v1.py`, pruebas bajo `test_capitalizer_scalper_h1_target_asymmetry_audit_v1.py`. Contrato: TODAS 2,876 fuentes V49 conciliadas exactamente con su entrada, stop protegido M15, target H1, recompensa R planeada, pago target completo, identidad de fuente SHA256 y selección cronológica MAX3. **Ningún ajuste de admisión** ni P&L importado a la estrategia.

**2,020 seleccionadas MAX3**: 1,569 tenían recompensa objetivo planeada **menor a 1R** (77.67%), 1,104 menor a 0.5R (54.65%), 633 menor a 0.25R (31.34%); mediana planned R ~0.44262. De las 1,030 que alcanzaron su TARGET entero, 949 pagaron <1R (**92.14%**), 779 <0.5R (**75.63%**), 517 <0.25R (**50.19%**); mediana realized TARGET R **0.24655**, media **0.392147R**, gross +403.912R. **Ni parciales ni breakeven** en la simulación V49: STOP -1R, TARGET full witness R, SESSION_EXIT close del último M1 observado.

**Detalle arquitectónico clave:** `capitalizer_high_frequency_capacity_census_v49._untouched_h1_target_fast` recorre los **últimos 24 H1 CERRADOS** desde el más reciente y elige el primer extremo HIGH/LOW de cualquier vela H1 por delante del precio sin toque posterior (según M1 as-of). **No exige que el extremo sea un swing H1 fractal con cierre de confirmación posterior**, ni un FVG, ni una piscina de liquidez específica del autor. Es una **heurística QORE conservadora de primer testigo**, no un objetivo HTF plenamente fiel a TTrades por sí sola. El target de 0.392R es **resultado de la distribución de TARGET hits condicionados**, no promedio del objetivo planeado de todas las 2,020 entradas (media planned R = 1.16220, sesgada por extremos; mediana 0.44262). Extender el target podría reducir los hits y empeorar PF; no cambiarlo sin ensayo preregistrado y OOS.

**Límite:** las 2,876 filas se compararon contra los target witness **registrados y la función source original ya testada con causalidad**, pero el lector económico no reconstruye de forma independiente cada witness a partir de RAW M1 + H1. Ese test adicional queda separado, no declararlo completado.

## 3. A/B stop noise: diseño 2×2 congelado ANTES de ver sus resultados

**Preregistro previo a resultados:** Issue #757, comentario [#6098508938](https://github.com/mezas3238-hue/qore-core/issues/757#issuecomment-6098508938).  
**Código:** `capitalizer_scalper_stop_noise_factorial_v1.py` + `test_capitalizer_scalper_stop_noise_factorial_v1.py`.  
**GitHub Actions:** [factorial run #38059917709](https://github.com/mezas3238-hue/qore-core/actions/runs/38059917709) (primera corrida validó contrato, luego 9 mercados).  
**Fuente idéntica:** V49 histórico 9-market 2,876, RAW native M1 mismo SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`, mismos H1 targets congelados (sin optimizarlos), mismas M1 confirmations, mismo STOP-first/SESSION_EXIT, mismo MAX3 por sesión/día, no outcomes en gate.

| Brazo predefinido | Stop y veto de ruido | Qué aísla |
|---|---|---|
| B `M15_NOISE_OFF` | Protected swing M15, **sin** exigir M1 pivot/noise | Control V49 de 2,020 operaciones. Debe ser idéntico trade a trade |
| C `M15_NOISE_VETO` | Stop **M15**, pero exige M1 pivot válido y ruido 4–8× antes de admitir | Coste de convertir ruido M1 en **veto** incluso con tesis M15 válida. **C es hard gate**, NO confluencia opcional |
| D `M1_NOISE_OFF` | Pivot M1 confirmado e intacto, sin veto por ratio 4–8× | Coste puro del stop refinado M1 y ausencia de pivot, sin hard noise |
| A `M1_NOISE_VETO` | Pivot M1 confirmado e intacto, con ratio distancia/rango M1 4–8× | Variante aislada del stop/veto V50-G, sin H1 ladder ni cognitiva añadida |

**Interpretación C:** si la «confluencia opcional» propuesta por DeepSeek fuese verdaderamente opcional, admitiría los mismos candidatos y mismo stop M15 que B. Por tanto, no sería un brazo causalmente distinto hasta agregar un score/ranking predecision con política preregistrada. El brazo C publicado evalúa conscientemente una hipótesis más fuerte **y etiquetada QORE**: exigir el ruido 4–8× como VETO incluso manteniendo stop M15, para medir qué sacrifica ese veto.

**A no equivale a V50-G real:** la versión V50-G histórica también exige H1 pivot target ladder y mínimo 1R, pasa por un puente cognitivo que descarta H1/M15 stale, y modifica su target. Aquí esos factores se congelan al target ORIGINAL H1 para identificar únicamente stop y veto; no comparar PF causalmente V50-G (94 trades) contra B (2020) fingiendo aislamiento.

**Gates causales:** pivote M1 low/high protegido **confirmado por la vela derecha**, nacido desde confirmación M15 y no consumido por velas posteriores a su confirmación, todo con `bar.closed_at <= entry_at`. Ruido M1 = mediana del rango de los últimos 15 M1 ya cerrados; ratio riesgo stop M1/rango local. Si M1 pivot no está disponible, B se mantiene y A/C/D reconocen causa distinta (no fingir pivote). No usar MFE, P&L, H1 active_until futuro ni futuros cierres. Por cada mercado el programa reejecuta B y **exige igualdad dataclass EXACTA con el libro V49 original**, no sólo igualdad de PF. Las 9 matrices solo se publican si 9/9 completan con source ID intacto, raw-M1 válido, MAX3 estable, ningun spoofing de stops/targets.

**Métricas de evaluación prereg:** candidatos admitidos antes y después MAX3, 1,167 winners V49 preservados por source ID vs 934 Owner, R base positivo conservado vs 415.75R, PF bruto, netR, DD R, 9 mercados, 3 sesiones y ambas familias; cambios originados en falta pivot/inside noise/too wide. Stop M1 puede aumentar frecuencia pero empeorar stopouts; no dar por buena rama B por su densidad (PF V49 sólo 0.664); C/D/A tampoco por PF si destruyen 90% ganadores. No seleccionar ex post al ganador factorial: luego OOS, live-cost bid/ask y Master Frame A1 necesitarán estudio separado.

## 4. Siguientes preguntas fuera del factorial

- Revalidar todos los witness H1 en RAW M1 original + H1 cerrados, 24-candle reversed selection exactamente como V49 (no lookahead). Cuantificar “target ya tocado antes de entrada”: con misma implementación causal debería ser **cero**, pero hay que comprobarlo independientemente.
- Hacer comparación **target alternativo basado en objetivos H1 realmente confirmados / FVG / liquidez HTF** y rutas de continuación, con stop fijo en protected swing, prereg y OOS; no imponer un mínimo R arbitrario de TTrades ni elegirlo con el resultado histórico.
- Auditar específicamente la confirmación Sweep+CISD contra el **cierre de las velas opuestas**, no simplemente el sweep.
- Integrar cognitiva A1 plena, observaciones inter-mercado y memoria prequential settled-only SIN acceso a excursiones futuras, separando bajo rendimiento económico de falta de implementación cognitiva. NO certificar, NO merge, NO VPS/LIVE.

## 5. RESULTADO REAL FINAL 2×2 — 9/9 mercados, sin modificar el target

**Fuente:** [GitHub Actions #38059917709](https://github.com/mezas3238-hue/qore-core/actions/runs/38059917709), código/fuente experimento SHA `49cbb645fcc2845d6c9e7ddf6186f0bdba35b15b`; **11/11 jobs SUCCESS** (test contrato, 9 mercados, agregado). Los artefactos almacenan source gate por oportunidad, cuatro libros económicos por mercado, matriz de PF/DD y winner-ID retention. Igualdad estricta de **las 2,876 filas simuladas de B** con el V49 control original *dataclass por dataclass* comprobada dentro de cada job, incluyendo precios, stop, target y R. No son operaciones LIVE, ni costes físicos.

| Brazo | Operaciones después MAX3 | Ganadoras del brazo | PF bruto | R acumulado | Max DD (R) | Ganadores de V49 aún positivos (de 1167) | R ganador V49 conservado |
|---|---:|---:|---:|---:|---:|---:|---:|
| **B M15_NOISE_OFF** | 2,020 | 1,167 | **0.664463** | **-233.269R** | **236.134R** | 1167 (100%) | 461.943R (100%) |
| **C M15_NOISE_VETO** | 223 | 150 | **0.868955** | **-6.266R** | **12.687R** | 107 (9.17%) | 31.691R (6.86%) |
| **D M1_NOISE_OFF** | 1,934 | 739 | **0.796112** | **-240.719R** | **263.124R** | 704 (60.33%) | 255.576R (55.33%) |
| **A M1_NOISE_VETO** | 223 | 136 | **1.035084** | **+2.773R** | **13.027R** | 97 (8.31%) | 29.287R (6.34%) |

**Veto 4–8× antes de MAX3:** 2,370 oportunidades `M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE`, 272 sin pivote M1 confirmado, 10 por stop M1 >8× y **224** dentro de [4×,8×]; por MAX3, 223. Hay una discrepancia de **1** entre la clasificación factorial de ruido 2,370/224 y el rastro original V50-G 2,371/221 READY; versiones/contratos de entrada diferentes (también hay condiciones de ladder/target y snapshot) y NO se debe fingir identidad perfecta entre experimentos. Los módulos de geometría son el componente que aquí se aísla; el legado V50-G incluye además filtro ≥1R, H1 target ladder alternativo y puente cognitivo. Comparar sus salidas como si solo cambiara stop violaría la lógica del A/B.

**Resultado causal estructural:**
1. **Quitar el veto de ruido M1 del brazo M1** cambia A (223) → D (**1,934**): recupera **1,711 ejecuciones** en mismo dataset, pero PF bruto cae de 1.035 a **0.796** y DD sube de 13.03 a **263.12R**. **No arregla el edge negativo**, ni preserva suficientemente ganadores (704 / 1167 en vez de 934 mínimos).
2. **Mantener stop M15 y añadir veto M1** cambia B (2,020) → C (**223**) sin alterar stop ni target, y preserva solo 107 ganadores V49 (6.86% winner mass). El veto es una barrera extrema de densidad incluso cuando el stop protegido M15 existe.
3. **Cambiar M15 a M1 sin veto** B (2,020) → D (1,934): modifica la relación de recompensas objetivo a riesgo y acelera los stops; PF mejora *relativamente* de 0.664 a 0.796, pero el DD acumulado empeora (236.13R → 263.12R) y R neto se deteriora (-233.27R → -240.72R). **No es prueba de que M1 stop sea mejor**.
4. Las ramas A/C con 223 operaciones, y D con sólo 704 ganadores V49 conservados, incumplen Owner retención ≥934 originales/≥415.75R. B preserva 100% por definición pero tiene PF0.664 y DD236R. **NINGÚN brazo es elegible para certificación**. Una variante de densidad alta con PF <1 tampoco se debe promocionar.

### Lectura específica de targets: condicionamiento importa

La distribución de los 2,020 planned targets está muy sesgada: **media planned 1.162R pero mediana 0.443R**. El subconjunto que logra target (N=1030) es el de objetivos más próximos: **mediana payout 0.2465R**, mientras el subconjunto que acaba en STOP (N=609) tenía **mediana planned target 0.8315R**. Esto indica que **los targets más distantes tienen menor tasa de impacto en este ensayo**, por lo que subir mecánicamente todos los targets a 1.5R no tiene respaldo y puede convertir ganadoras existentes en stops. El target autor-faithful debe nacer de un draw-on-liquidity confirmado y de una tesis de expansión H1, no de escoger retrospectivamente la posición que hubiera pagado más.

### Lectura de certificación

- **CORROBORADA** asimetría de pagos de H1 witness (típico target demasiado próximo al stop M15).
- **CORROBORADO** veto M1 de QORE destruye la frecuencia al actuar como hard requirement.
- **FALSADA** la esperanza simple de que desactivar ese veto o cambiar solo el stop restaure edge rentable: ambos brazos de densidad alta son PF bruto <1, DD gigantesco.
- **NO DEMOSTRADA** calidad H1 bias separada, CISD Sweep metodológicamente correcto en cada trade, causalidad de todos los niveles de liquidez, ni que otra ubicación target eleve PF neto OOS.
- **PENDIENTE** rerender independiente H1 target witness con RAW M1 y pivotes confirmados, análisis multiventana OOS, costes físicos bid/ask comisiones, integración completa Master Frame A1; no usar MFE/MAE del futuro para admisión.
