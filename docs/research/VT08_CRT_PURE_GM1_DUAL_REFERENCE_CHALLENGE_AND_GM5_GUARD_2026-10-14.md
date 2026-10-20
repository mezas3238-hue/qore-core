# QORE CORE — VT08 CRT PURE: G-M1 doble referencia y protección G-M5

**Fecha:** 14-OCT-2026 · **Rama:** `agent/vt08-crt-pure-source-identity-001` · **PR:** #626 DRAFT (sin merge).  
**Alcance:** certificación **metodológica y cognitiva** exclusivamente. **No sizing, no PnL, no ejecución de órdenes.** Todos los PASS siguen pendientes.

## 1. Caso crítico específico que impide certificar la metodología

La [fuente primaria de RomeoTPT, Telegram #6615](https://t.me/s/officialRomeotpt/6615), describe una reacción bajista desde un *old CRTH*. El texto **no contiene una regla de prioridad ni un arbitraje causal verificable** para casos con dos o más old CRTH/CRTL simultáneos. La [distinción oficial journey/reaction a key level](https://t.me/s/officialRomeotpt?before=6280) tampoco define ese arbitraje. Nada encontrado en esta ronda permite elegir «último», «más cercano», «más extremo» u otro criterio sin sustituir la fuente por ingeniería.

Las fuentes de terceros pueden ayudar a localizar material original, pero **no reemplazan al autor** para establecer la identidad CRT PURE. Los videos originales requieren visionado con minutaje, comparación de fotogramas, evidencia textual y custodia antes de cerrar la norma.

## 2. Examen reproducible con velas reales — PRUEBA CIEGA

Se incorporó `vt08_crt_pure_gm1_reference_challenge.py`, conectado al flujo nativo de Atlas y al adaptador G-M3 que ya rechaza información futura. Por cada registro G-M2 **enumera sin escoger** el mínimo H4 C1 y H4 C2 si el contexto H4 es alcista, o los máximos si el contexto es bajista. Toda barra H4 lleva timestamp original, momento en que quedó cerrada y precio entero relativo original. La verificación confirma que **ambas barras eran conocidas antes de la decisión M15 C2**.

**Advertencia metodológica fundamental:** los H4 HIGH/LOW crudos **NO se consideran ni se renombran old CRTH/CRTL canónicos**. La elección de lado utiliza únicamente el sesgo de ingeniería del parent H4. Las dos posibilidades son **preguntas de revisión**, no señales, detectores ni modelos de entrada.

**Datos verificados:**

| Mercado | Casos causales | Referencias H4 enumeradas | Casos con dos precios distintos | Orígenes certificados por Romeo |
|---|---:|---:|---:|---:|
| AUDUSD | 24 | 48 | 24 | 0 |
| USDJPY | 24 | 48 | 24 | 0 |
| **Total** | **48** | **96** | **48** | **0** |

Fuente: [GitHub Actions #38650459457](https://github.com/mezas3238-hue/qore-core/actions/runs/38650459457), commit `b9f88621747803a3669514c250d3ecad1077a6f9`. La ejecución de control de calidad, AUDUSD y USDJPY terminó **SUCCESS**. Artefactos de revisor sin C3 futuro: AUDUSD **11934262952**, USDJPY **11933349915**. Se descargaron ambos ZIP, se cotejaron los **7 hashes SHA256 internos en cada ZIP**, el manifiesto y los 24 registros por mercado. Ambas listas incluyen 24 pares con precios distintos.

El material sellado de futuro C3 sigue en **ZIP independientes**, nunca alimenta el clasificador de referencias. No se usa BID/ASK de ejecución, PnL, beneficios ni sizing.

## 3. Qué pedir a un auditor independiente del método del autor

Entregar los dos ZIP del revisor y la fuente Romeo original, **sin futuro sellado**. Exigir dictamen registrado por `case_id`:

1. ¿El máximo/mínimo H4 C1 cumple la noción de **old CRTH/CRTL** del autor? Respuesta: SÍ/NO/INDETERMINADO con locator original.
2. ¿Y el C2 H4? Mismas alternativas y evidencia.
3. Si los dos fueran válidos, ¿Romeo da una prioridad explícita y verificable? Consignar minuto/fotograma/texto exacto; nunca deducir el desempate por lo que hizo C3.
4. Si ninguno fuera válido, marcar ambos **RECHAZADOS**. Si la fuente no permite resolver, marcar **INDETERMINADO** y mantener el caso `WAIT/ABSTAIN` — no contarlo como modelo confirmado.
5. Solo después del dictamen firmado, abrir el sellado y **comparar comportamiento**, nunca alterar la regla para mejorar PnL.

No hay dictamen independiente registrado aún. Estos 48 casos no son un holdout virgen: la cohorte ya se usó antes.

## 4. Certificador metodológico separado de certificado económico

Se añadió `crt_pure_methodological_certification.py` con `CrtPureMethodGateEvidence`, estados `OPEN/PARTIAL/PASS` para G-M1..G-M4, y `evaluate_methodological_gm5()`. El módulo **no contiene sizing, PF, Sharpe, retorno ni umbrales de inversión** y jamás concede autoridad de volumen, broker, DEMO o LIVE.

La emisión G-M5 requiere: los **cuatro Gates en PASS**, enlaces a evidencia, dictamen independiente, atestación de no-leakage, orden e identidad íntegros, y *comprobación independiente* de `model1_source_ready()` contra el registro original. Incluso **cuatro Gates fraudulentamente marcados PASS** siguen produciendo `G-M5=NOT_CERTIFIED` mientras `MODEL_1_REFERENCE_SELECTION` esté `AMBIGUOUS`. Tests impiden PASS sin pruebas, duplicación/omisión de Gate y sizing. [Cognitive Gate #38650560776](https://github.com/mezas3238-hue/qore-core/actions/runs/38650560776) **SUCCESS**.

**Resultado actual G-M5:** G-M1 PARTIAL, G-M2 PARTIAL, G-M3 PARTIAL, G-M4 PARTIAL, G-M5 **NOT_CERTIFIED**.

## 5. Trabajo aún indispensable y causas raíz

- **P0 FUENTE:** Romeo original no resuelve la elección entre múltiples old levels en corpus revisado; localizar y auditar enseñanza primaria con minutaje. Si el autor no define el selector, separar política QORE pendiente de orden Owner sin afirmar fidelidad canónica.
- **P0 METODOLOGÍA:** estos H4 máximos/mínimos NO prueban ser CRTH/CRTL; requieren validación humana fuente-causal y taxonomía de referencias.
- **P1 G-M2:** 48 prefijos auténticos y 96 referencias a auditar, sin compararlos con velas posteriores ni convertirlos en trades.
- **P1 G-M3:** la cognitiva funciona en modo seguro, pero 48 ABSTAIN ante fuente abierta no significan 48 interpretaciones CRT correctas. Falta reconciliar decisiones contra la fuente.
- **P1 G-M4:** integración desde data→identidad→referencia seleccionada→cognición→router→expiración y manejo de hipótesis muertas aún no cuenta con prueba metodológica E2E de los cuatro Gates cerrados.
- **P2 G-M5:** no emitir certificado hasta cumplimiento verificable de G-M1..G-M4; certificación económica distinta no se confunde con la metodología.

**Custodia y prohibiciones:** repo soberano `mezas3238-hue/qore-core`, PR DRAFT sin merge, NO VPS, NO DEMO/LIVE, NO órdenes; absolutamente **sin sizing** para VT08: volumen/capital son solo de CIBO.
