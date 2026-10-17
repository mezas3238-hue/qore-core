# VT08 CRT PURE — G-M1/G-M2: 131 geometrías de Model #1 NO AUTENTICADAS, 48 casos reales

**Corte:** 14-OCT-2026 · repo `mezas3238-hue/qore-core` · PR #626 DRAFT · **SIN SIZING**, sin merge, sin broker ni certificación.

## Propósito

Pasar de una comparación estática de dos extremos H4 a una comparación **causal** de cada referencia contra la mecánica fuente ya parcialmente cerrada de Model #1 sobre M15. La finalidad NO es detectar entradas ni seleccionar retrospectivamente un old CRTH/CRTL: es identificar dónde la regla de selección no puede eludirse.

**Método exacto, pre-decisional:** sobre los 48 prefijos G-M2 obtenidos del Atlas original, inspeccionar *ambos* extremos H4 **CRUDOS** (C1 y C2 conocidos antes del reloj M15) e iterar las velas M15 cerradas observadas. Para cada posible referencia, aplicar la detección original interna `detect_model1_candidate()` (barrido con vela de cuerpo del sentido correspondiente) y buscar `assess_model1_confirmation()` entre velas M15 posteriores **ya cerradas antes del reloj de decisión**, sin consultar futura C3, BID/ASK ni resultado. Registramos una sola primera confirmación cronológica por pareja referencia+vela de origen. El plazo preciso de la confirmación y la pertenencia del nivel antiguo al autor **no están certificados**; por eso las coincidencias son *geometrías de ingeniería* exclusivamente.

## Resultado original reproducible

**CI [#38659834142](https://github.com/mezas3238-hue/qore-core/actions/runs/38659834142): quality, AUDUSD y USDJPY SUCCESS**; commit `8d185ab50fd7506d5d8bb90d645f908046063482`. Se descargaron los **dos paquetes REVIEWER-BLIND-ONLY**, se verificaron **9/9 checksums internos de cada ZIP** y la ausencia de `gm2-sealed-c3-witness.jsonl` en el ZIP. Fuente M5 original previamente validada y caso de ensayo estratificado, **NO fresh holdout**.

| Descripción | AUDUSD | USDJPY | Total |
|---|---:|---:|---:|
| Prefijos históricos reales | 24 | 24 | **48** |
| Dos H4 extremos crudos por caso | 48 | 48 | **96** |
| Hipótesis de vela Model #1 contra extremos crudos | **81** | **50** | **131** |
| Hipótesis que alcanzaron confirmación mecánica por cierre de cuerpo antes del reloj | **23** | **27** | **50** |
| Casos con geometría contra al menos un origen de nivel | 20 | 13 | **33** |
| Casos con geometría contra **ambos** orígenes | **16** | **12** | **28** |
| Casos con geometría contra un solo origen | 4 | 1 | **5** |
| Casos sin esa geometría | 4 | 11 | **15** |
| **Old CRTH/CRTL auténticos certificados por Romeo** | 0 | 0 | **0** |

**Artefactos:** AUDUSD ciego artifact **11937963848**, USDJPY ciego artifact **11938616846**, cada uno con `gm1-model1-raw-reference-summary.json` y `gm1-model1-raw-reference-observations.jsonl` más G-M2/G-M3. Los ZIP sellados de futuro son otros artifacts: AUDUSD **11937948831**, USDJPY **11938348098**. NINGUNO del futuro alimentó los cálculos.

## Conclusión causal: por qué G-M1 es de veras P0

Para **28 de 48 casos**, ambos extremos H4 crudos tenían una vela M15 compatible con la geometría preliminar Model #1. Esto muestra directamente que **un detector de patrón no resuelve por sí mismo la propiedad del nivel de referencia**. Afirmar que uno de los dos casos «ganó» requeriría escoger un nivel fuera de la norma Romeo verificada. No se hizo.

Las 50 confirmaciones **NO son 50 trades ni 50 aciertos**. Son pares geométricos referencia-vela que pasaron el cierre por cuerpo bajo una hipótesis no aprobada de qué constituye old CRTH/CRTL. Algunos casos tienen más de una hipótesis, se repiten velas de origen frente a distintos niveles, y la fuente original puede excluir ambas opciones o preferir otros antiguos niveles fuera de la ventana C1/C2. No comparar con rentabilidad ni sizing para resolverlo.

## Protección de G-M5 comprobada en los mismos 48 casos

En [#38659571365](https://github.com/mezas3238-hue/qore-core/actions/runs/38659571365) quality + ambos mercados SUCCESS: 48 ABSTAIN cognitiva, 48 WAIT router certificador y **48 intentos adversariales con cuatro falsos PASS de G-M1..G-M4 rechazados por `model1_source_ready()`**. Artefactos `gm3-real-safety-summary.json`: `G_M5_fake_all_pass_certificates=0` y `G_M5_primary_source_guard_checked=true` en cada par. Regresión sobre misma fuente causal, no autoriza G-M4 PASS.

## Próximos pasos realmente necesarios

1. Fuente A Romeo original: video con minuto exacto + evidencia de viejo CRTH/CRTL, desempate de referencias, destino, límites y caducidad; lista priorizada en [cola de videos originales 2024–2026](VT08_CRT_PURE_GM1_PRIMARY_VIDEO_REVIEW_QUEUE_2026-10-14.md).
2. Adjudicación visual ciega de los **28 casos ambiguos** primero, además de los 5 que solo tienen geometría con un origen y los 15 sin geometría; registrar si C1/C2/ambos/ninguno son CRT auténticos bajo palabras y gráficos originales. No forzar 50 señales.
3. Si el autor NO ofrece desempate universal, elevar propuesta **identificada como INGENIERÍA QORE**, bajo aprobación Owner. No alterar memoria `CRT_PURE_SOURCE_REGISTRY` para simular autoridad Romeo.
4. G-M3: probar decisiones de cognitiva contra esos dictámenes independientes. G-M4: demostrar cadena E2E **positiva y negativa** con regla genuina; no limitarse a tests de abstención. G-M5 solo emitible con cuatro Gates PASS documentados y fuente realmente cerrada.

**Estado:** G-M1 PARTIAL, G-M2 PARTIAL, G-M3 PARTIAL, G-M4 PARTIAL, G-M5 NOT_CERTIFIED. CIBO mantiene autoridad exclusiva de volumen y capital. NO SIZING para VT08, NO MERGE, NO DEMO/LIVE, NO VPS.
