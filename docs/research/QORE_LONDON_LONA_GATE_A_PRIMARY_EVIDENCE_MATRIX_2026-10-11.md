# GATE A / LON-A — Matriz de evidencia primaria y ambigüedades (primera revisión)

**Fecha:** 2026-10-11. **Misión rectora:** [Issue #785](https://github.com/mezas3238-hue/qore-core/issues/785). **Predecesor:** [handoff maestro / PR #786](https://github.com/mezas3238-hue/qore-core/pull/786). **Modelo:** *How to Trade London Using TTrades Fractal Model* (12 septiembre 2026).

**ESTADO:** `GATE_A_PARTIAL / AUTHOR_EXACT_BLOCKED / ECONOMIC_REPLAY_NOT_AUTHORIZED / NO_LIVE`.

Este documento es una adjudicación documental de primera pasada. **No** declara fuente/vídeo certificado, no implementa algoritmo, no afirma edge y no crea entrada. No fusionar variantes Londres 2025, Scalping 2026 (H1/M15/M1), QORE L1/L2 o SMT-T0 con LON-A. El histórico ya consultado no es OOS virgen.

## A. Fuentes efectivamente inspeccionadas

| ID | Fuente | Alcance real en esta ronda |
|---|---|---|
| A0 | [Artículo London Fractal 12-sep-2026](https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/) | Texto íntegro HTML leído. Fuente ancla. |
| A1 | [PDF oficial TTrades-Trading-London.pdf](https://ttrades.com/wp-content/uploads/2026/09/TTrades-Trading-London.pdf) | 11 páginas, gráficos inspeccionados: pág. 2–4 Daily Bias (página PDF 1–3); p. 5 4h Swing (PDF índice 4); p. 6–10 H4 > M15 (PDF 5–9). Los diagramas son ejemplos ilustrativos, **NO dataset con timestamps reales**. |
| A2 | [How CISD Confirms Swing Points, 10-ene-2026](https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/) | Texto íntegro HTML leído. Fuente conceptual *complementaria*, no prueba automáticamente precedencia exacta intrabar en LON-A. |
| A3 | [How to Trade Candle 2, 16-ago-2025](https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/) | Texto íntegro HTML leído. Complementaria: wick, calidad y objetivos contextuales. |
| A4 | [How To Use SMT Divergence, 30-may-2026](https://ttrades.com/how-to-use-smt-divergence-ttrades-fractal-model/) | Texto íntegro HTML leído. SMT como confluencia adicional, no fundamento de trade. |
| A5 | [Vídeo original Londres](https://www.youtube.com/watch?v=tUbrCewFdCU) | Enlace verificado desde A0; **transcripción audiovisual NO accesible**. Herramienta vidIQ devolvió insuficiencia de 5 créditos (0 cobrados; renovación indicada 28-oct). **Cero timestamps o afirmaciones específicas atribuidas a escenas**. |

Otros artículos enlazados en el handoff quedan **PENDIENTES de lectura completa**. En particular fuente Daily Bias, Protected Swings/Stop Mastery, EQ, Candle3 y material audiovisual. La ausencia de lectura es explícita.

## B. Matriz LON-A / 18 reglas o decisiones

**Léxico de evidencia:** `A0_TEXT` = explícito en artículo específico de Londres; `A1_FIGURE` = figura oficial contextual, no regla computable; `SUPPLEMENTAL` = enseñanza de autor en publicación diferente; `QORE_ENGINEERING` = convención que debe declararse como variante; `UNRESOLVED` = decisión todavía no justificada. Una regla puede tener narrativa A0 y umbral UNRESOLVED. `available_at` especifica restricción causal requerida, **no significa que tengamos algoritmo certificado**.

| ID | Requisito/concepto | Evidencia trazable | Causalidad o criterio que falta | Dictamen |
|---|---|---|---|---|
| LA01 | Identidad London Fractal = Daily → H4 → M15 | A0, secciones Introduction/Full Fractal/How to Trade; A1 p.5–10 | Mantener independiente de H1/M15/M1 | `A0_TEXT` |
| LA02 | Determinar sesgo Daily ANTES de entrada Londres | A0, Start With A Daily Bias | Cómo elegir entre Phases of Price, EQ, POI y C2/C3 si discrepan; lógica de no-trade | `A0_TEXT + UNRESOLVED` |
| LA03 | C2 o C3 closure en POI como vía para bias | A0, Start With A Daily Bias; A2, Valid Candle 2 / Candle 3 | Determinar POI causal, cierres válidos, ancla del Daily, si alternativas son autorizadas | `A0_TEXT + SUPPLEMENTAL + UNRESOLVED` |
| LA04 | Esperar formación de mecha contraria Daily | A0, Let The Daily Wick Form; A1 p.2–4 | `wick_complete` first-online: no inferir del high/low definitivo de la jornada | `A0_TEXT + UNRESOLVED` |
| LA05 | Seleccionar swing H4 alineado a sesgo Daily | A0, Use The 4 Hour Candle; A1 p.5 | Cómo se sabe low/high antes de confirmación, pivote, ventanas H4 y fuente horaria | `A0_TEXT + UNRESOLVED` |
| LA06 | Dejar formar mecha H4 antes de operar body | A0, Use The 4 Hour Candle, London Timing; A1 p.5–10 | `h4_wick_complete` en tiempo real, cierre H4 sí/no requerido, evidencia para anticipación | `A0_TEXT + UNRESOLVED` |
| LA07 | Candle 2 H4 *puede* confirmar swing / anticipar C3 | A0, Use The 4 Hour Candle; A2, Higher TF closure + CISD | Si es obligación para TODA configuración LON-A, o vía preferente; qué ocurre con Early C2 | `A0_TEXT + UNRESOLVED` |
| LA08 | CISD M15: cierre atravesando serie de velas causantes del extremo | A0, Confirm The Swing On The 15 Minute; A2, What Is CISD | Seleccionar la serie y el open relevante sin etiquetas retrospectivas ni lookahead | `A0_TEXT + UNRESOLVED` |
| LA09 | Protected swing al confirmarse CISD M15 | A0, Confirm The Swing On The 15 Minute; A1 p.6–10 | Extremo congelado en evento, distinguir swing provisional/ex-post; invalidación definitiva | `A0_TEXT + UNRESOLVED` |
| LA10 | Continuación a favor de Daily y H4 | A0, Confirm The Swing, Full Fractal | Si tras CISD se compra/vende al cierre, en pullback o en una segunda confirmación | `A0_TEXT + UNRESOLVED` |
| LA11 | La killzone exacta NO es regla universal de inclusión | A0, London Session Timing; A1 incluye ejemplos 22:00/02:00 y 02:00/06:00 | Ancla horaria de figuras, NY/London/broker, DST; no convertir horas ilustrativas en filtros | `A0_TEXT` (no umbral horario) |
| LA12 | Reversión puede iniciar en Asia o inicio de Londres | A0, London Timing/London Reversals | Cuál es universo elegible y expiración, si el trade sucede Asia o Londres | `A0_TEXT + UNRESOLVED` |
| LA13 | Failure swing necesita más confirmación | A0, Failure Swings Need More Confirmation | Qué es failure swing de modo operativo, qué confirmación adicional es suficiente | `A0_TEXT + UNRESOLVED` |
| LA14 | SMT es posible confluencia | A0, London Reversals/Failure Swings; A4, SMT Within Model | No aparece como condición universal, ni se especifica sincronización de 10 minutos | `A0_TEXT + SUPPLEMENTAL` (NO filtro obligatorio) |
| LA15 | Objetivos altos/bajos HTF o DOL, runner posible | A0, Holding The Expansion; A3, wick-size targets | Elegir objetivo único de forma prospectiva y priorizar primer DOL, runner/partiales | `A0_TEXT + UNRESOLVED` |
| LA16 | Precio exacto de entrada, stop y buffer | A0, Full Fractal / How to Trade (orienta entrada sin orden mecánica exacta) | Market next-open vs close, limit/OB/FVG; SL swing/wick/body y pip buffer | `UNRESOLVED_BLOCKING` |
| LA17 | Calidad: estructura y cierre por encima de 'cualquier CISD' | A2, How CISD Defines Trend Shifts / High-Quality CISD | Qué es V-shape, displacement, minimal chop SIN umbrales arbitrarios | `SUPPLEMENTAL + UNRESOLVED` |
| LA18 | Sin fills ni edge certificados | Ninguna fuente provee replay LON-A cuantitativo EURUSD/GBPUSD | Contrato de broker/costes/dual-touch, muestra OOS virgen, benchmark y potencia | `BLOCKED_ECONOMIC` |

**IMPORTANTÍSIMO:** A2 (enero 2026) indica que el autor no trata CISD aislado como suficiente: busca cierre C2/C3 HTF y CISD en el interior de esa vela HTF. Esto plantea un problema **de disponibilidad temporal**, no una licencia de conocer anticipadamente el cierre. Dos caminos deben separarse experimentalmente *antes* de cualquier resultado: (a) esperar HTF confirmada y usar el CISD histórico solo como evidencia del swing, pudiendo entrar a partir del cierre HTF; (b) autorizar entrada intra-HTF únicamente si una fuente de LON-A permite expresamente actuar con HTF provisional. **No adjudicamos (b) como autoral**, ni seleccionamos la ruta que dé mejores resultados.

## C. Hallazgos de gráficos en el PDF oficial (NO etiquetar retrospectivamente como trade)

- **Páginas PDF índice 1–3 / diapositivas Daily Bias:** ejemplo alcista con reacción desde área POI sombreada, continuación; no etiqueta un ticker, fecha, cuantía o disponibilidad horaria. No prueba selector diario cuantitativo.
- **Página PDF índice 4 / lámina 5:** vela H4 de reversión y vela Daily, con referencia «02:00 or 22:00» junto al extremo. No se declara zona horaria, por lo que **no** es lícito convertirlo automáticamente a America/New_York o Europe/London.
- **Páginas PDF índice 5–9 / láminas 6–10:** sucesión H4 > M15; figuras M15 exhiben una zona de giro y línea azul horizontal en la confirmación, junto a distintas fases de expansión H4, con referencia «2:00 or 6:00». **Interpretación visual preliminar**: la secuencia de gráficos ilustra cómo la confirmación intradía acompaña al giro HTF, no demuestra precio exacto de entrada, SL, TP ni instante en que H4 se reputaba finalizada.
- Prohibido crear fixtures "validados" a partir de diagramas sin ticker/fecha real: útiles como **synthetic schematic fixtures** para dirección/orden lógico solamente.

## D. Fallos que pueden falsificar artificialmente un backtest (tests P0 propuestos)

1. **Cierre superior futuro**: M15 CISD a t1, H4 C2 closure a t2 > t1, entrada etiquetada t1 con la confirmación futura t2. Debe rechazarse para la variante cierre-H4-confirmado.
2. **Mecha final futura**: etiquetar 'wick formed' a t1 porque el mínimo diario/H4 definitivo ocurre posteriormente. Debe rechazarse.
3. **Serie CISD reescrita**: nuevas velas tras t alteran la serie que supuestamente causó el mínimo en t. Prefix-invariance obligatorio.
4. **Swing protegido reubicado**: swing marcado al ver velas futuras y aplicado al instante del extremo. Detectar evento `available_at` distinto de `extreme_at`.
5. **H4 parcial**: tick/dato M1 faltante mezclado con barras OHLC completas; exigir cobertura explícita y clasificar missing history / missing bar.
6. **Cambio horario**: reanclar H4 o sesión por DST cambia oportunidades con fecha inalterada; reportar por UTC + zona y prueba de primavera/otoño.
7. **Conflicto same-bar**: en ejecución OHLC, una M15/M1 toca SL/TP sin orden intrabar observada; marcado ambiguo, no resultado fill inventado.
8. **Selección ex post**: usar los 458 outcomes de proxy QORE o datos 2025-09→2026-09 ya vistos para elegir umbrales de LON-A y proclamarlos OOS. Prohibido.
9. **Falsa fidelidad a gráficos**: diagramas esquemáticos usados como fechas reales de trades. Prohibido.
10. **Hora ejemplar convertida en filtro**: 22:00/02:00/06:00 del PDF interpretada como killzone universal, pese a A0. Prohibido.

## E. Preguntas a resolver por orden, fuente y/o revisión externa

- **Q1 [Bloqueo]** ¿Qué regla exacta decide el sesgo Daily entre múltiples narrativas del autor, sin utilizar cierres aún no disponibles?
- **Q2 [Bloqueo]** ¿Qué observación first-online certifica que la mecha Daily/H4 terminó y el swing de H4 está protegido?
- **Q3 [Bloqueo]** ¿Se exige siempre cierre H4 completo antes de poder usar CISD M15 como entrada? Si no, ¿dónde lo autoriza *explícitamente* LON-A?
- **Q4 [Bloqueo]** ¿Cuál es la definición causal y única de serie CISD M15 y el close through? ¿Cómo se maneja reescritura del open y swings débiles?
- **Q5 [Bloqueo]** ¿En qué precio y condición se entra? ¿SL/tolerancia exactos? ¿Dónde se liquida sin conocer futuro? ¿Cómo se gestionan múltiples DOL?
- **Q6 [Bloqueo]** ¿Cuál es la zona horaria/anchor 22:00, 02:00, 06:00 ilustrada en el PDF? ¿Está el perfil Londres definido como sesión estricta o como contexto?
- **Q7 [Pendiente]** ¿Qué condiciones convierten Failure Swing y SMT en aceptables? ¿SMT es opcional siempre?
- **Q8 [Pendiente]** Revisión de escenas de vídeo con min:seg genuino; ejemplos perdedores y contradicciones documento/voz; sin acceso no inventar.
- **Q9 [Datos/OOS]** Auditoría de M15/H4 y disponibilidad de holdout no consultado. No ejecutar backtest económico hasta gates A–D.

DeepSeek es revisor externo de argumentos/ambigüedades si está disponible, **no** fuente atribucional del autor. Toda propuesta de umbral/timeout/filtro emitida por una IA se marca `QORE_ENGINEERING`, no `A0_TEXT`.

## F. Dictamen de esta ronda

**Avance real:** fuente ancla del 12-sep, artículo, **PDF oficial de 11 páginas** y fuentes complementarias CISD/C2/SMT cotejadas. Se han separado 18 decisiones, incluidas **entrada, stop, salida y temporización HTF/LTF como bloqueos críticos**. No hay audición completa del vídeo (vidIQ sin créditos; renovación 28-oct indicada), ni adjudicación suficiente para llamarlo "author exact".

**Siguiente trabajo permitido:** documentar vídeo/manual si se habilita otra fuente legítima; cotejar EQ/Daily Bias/Protected Swing/C3; fijar protocolo causal de casos no-trade y conseguir 10–20 fixtures *fechados/verificables*, no solo dibujos; resolver incertidumbre de la precedencia H4↔M15 antes de comenzar el motor.

**Gates:** A = `PARTIAL`; B = `PENDING`; C = `NOT_STARTED`; D = `NOT_STARTED`; E = `PROHIBITED`; F = `IN_PROGRESS`. **No modificaciones en producción, VPS ni MT5.**
