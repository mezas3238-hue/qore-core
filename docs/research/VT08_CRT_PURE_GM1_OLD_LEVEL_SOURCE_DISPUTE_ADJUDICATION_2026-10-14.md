# VT08 CRT PURE — G-M1: OLD CRTH/CRTL referencia y propiedad de nivel (fuente original)

**14-OCT-2026 · PR #626 (DRAFT) · Dictamen `OPEN` para selector Model #1.**
Este expediente es una investigación metodológica; NO es una señal, un backtest, un permiso de entrada ni un certificado. **Prohibido sizing** en G-M1–G-M5.

## Pregunta falsable exacta

**Ante dos o más niveles antiguos plausibles, conocidos antes de una M15 candidata, ¿cuál selecciona RomeoTPT, a qué temporalidad pertenece y qué evidencia invalida a los otros?** Necesitamos una regla causal reproducible o reconocimiento explícito de discrecionalidad. No basta con decir «old CRTH/CRTL» ni escoger retrospectivamente el nivel que habría acertado.

## Fuentes y alcance real de esta revisión

| Nivel de evidencia | Fuente | Qué se puede sostener | Qué NO puede sostenerse |
|---|---|---|---|
| Mensaje original público | [RomeoTPT oficial, post 6615](https://t.me/s/officialRomeotpt/6615) | En reacción bajista ideal, la vela puede penetrar un **old CRTH** antes de descender | Ninguna prioridad de «old CRTH» vs otro old CRTH; no describe su edad, fractal, cronología multivel, ni arbitraje |
| Mensaje original público | [RomeoTPT oficial, hilo previo a 6292](https://t.me/s/officialRomeotpt?before=6292) | Distingue viaje **HACIA** un key level de reacción **DESDE** uno | No especifica qué nivel antiguo pertenece a Model #1 cuando hay varios simultáneos |
| Mensaje original público | [RomeoTPT oficial, post 6184](https://t.me/s/officialRomeotpt/6184) | Model #1 y OTE son familias de enseñanza admitidas | No constituye algoritmo de selección de old high/low |
| Video ORIGINAL a revisar con acta y minutaje | [What is CRT? Why do all other trading strategies suck? / RomeoTPT, video ya indexado en registry](https://www.youtube.com/watch?v=UUq_wKQ61Wo&t=2332s) | Hay referencia primaria registrada sobre vela modelo y cierre de cuerpo | La localización del video NO verifica por sí sola cómo desempata old highs/lows |
| Video ORIGINAL pendiente de contrastación imagen + audio | [CRT secrets ep.5: Key level (RomeoTPT)](https://www.youtube.com/watch?v=p8UYOgVn1-g) | El episodio puede ser relevante para jerarquía de key levels, y merece inspección directa | No declarar reglas de jerarquía extraídas de resúmenes automáticos; fuentes de terceros son pistas, no autoridad Nivel A |

La búsqueda adicional de mensajes y referencias oficiales en esta ronda **NO encontró prueba directa, verificable y suficientemente específica** de desempate entre referencias simultáneas. No inferir universalmente «más cercano», «más reciente», «último swing», «máximo de H4», ni escoger por tasa de aciertos; ninguna de esas propuestas está fuente-aprobada en este registro.

## Examen independiente, obligatorio para levantar G-M1

1. Obtener video original de Romeo y capturar **video ID, fecha, minuto de inicio y fin, fotograma del gráfico, palabras exactas y SHA256 del extracto custodiado**. Sin todos esos elementos, la evidencia de video queda **NO ADJUDICADA**.
2. Presentar una misma vela candidata frente a **dos niveles antiguos distintos conocidos antes de su apertura**. Pedir un dictamen sobre cuál pertenece a CRT del autor (si alguno) con razonamiento **sin mostrar C3 futura**.
3. Repetir para: referencia M15 vs H4, old CRTH/CRTL roto y recuperado, igualdades de precio, dos niveles del mismo lado, padre H4 opuesto, sesión distinta y destino MOB bloqueado.
4. Certificar explícitamente si el autor define un algoritmo. Si no lo define, separar **discrecionalidad humana legítima** de la **política de ingeniería autónoma QORE**, que exigiría aprobación soberana independiente, jamás disfrazada de Romeo Tier A.
5. Validar el selector aprobado sobre los 48 casos G-M2 ya sellados, con diseño causal. No usar `gm2-sealed-c3-witness.jsonl` hasta después del dictamen del revisor.
6. Confrontar decisiones independientes contra `CrtPureSituationModel -> reason()` y la ruta `assess_model1_certification_entry_family`; reparar desajustes sin mirar resultados económicos.

## Estado y fallo peligroso detectado y reparado

El `crt_pure_source_registry.py` conserva `MODEL_1_REFERENCE_SELECTION=AMBIGUOUS` correctamente. Anteriormente, `crt_pure_certification_readiness.evaluate_certification_readiness` usaba solo el booleano general `strategy_identity_ready()` y `source_identity_closed` suministrado por el llamador. Con todos los booleanos artificialmente `True`, **podía devolver CERTIFIED pese a que Model #1 no tuviera selector fuente cerrado**.

**Corrección introducida:** el certificador consulta también `model1_source_ready()` directamente desde el registro; si falta, retorna `SOURCE_OPEN` con bloqueo `MODEL_1_REFERENCE_AND_SOURCE_SELECTION_NOT_CLOSED`, **incluso si todos los indicadores de entrada dicen True**. Test de regresión `test_all_green_external_flags_cannot_fake_source_certification`. No se ha emitido certificado.

## Contrato de custodia G-M2/G-M3

La versión corregida del workflow `vt08-crt-pure-gm2-blind-casebook.yml` publica **dos artefactos por mercado**, físicamente separados en el ZIP: `vt08-gm2-reviewer-blind-only-*` y `vt08-gm2-sealed-future-only-*`. Cada uno declara hashes propios; los paquetes ciegos no contienen vela C3 futura. **No es un control de permisos**: ambos siguen accesibles a personas con acceso al repositorio. El investigador debe registrar si abrió el sellado antes del fallo cualitativo; si lo hizo, no presentar la revisión como ciega.

El adaptador G-M3 ahora rechaza campos desconocidos (incluidos retornos, futuros, órdenes y sizing), parent H4 C1/C2 no causal, M15 desconectada, booleanos en OHLC y falsa calificación de holdout virgen. Estas son garantías negativas de integridad, **no identificación de Model #1, no rentabilidad y no G-M4 end-to-end PASS**.

**Decisión:** G-M1 = PARTIAL/SELECTOR OPEN; G-M2 = PARTIAL; G-M3 = PARTIAL; G-M4 = PARTIAL; G-M5 = NOT_ISSUED. PR sigue DRAFT; NO MERGE, NO DEMO/LIVE, NO VPS, SIN sizing. Solo CIBO tiene autoridad de capital/volumen.
