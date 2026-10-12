# QORE CORE · VT31 NAS100 · PREREGISTRO P0 DE GEOMETRÍA DE STOP (51 CASOS) Y REVISIÓN DE FUENTES ICT

**Fecha de custodia:** 2026-10-12 · **Estado:** `PREREG_DRAFT_NEEDS_DUAL_REVIEW` · **Única identidad:** `VT31` · **Ejecución metodológica:** M1 · **Sesiones internas:** London y New York AM/PM.

**Mandato de investigación:** resolver primero la regla metodológica de stop; **no abrir los 51 casos individuales, no simular sus stops, no descargar o usar ticks para imputarlos, no recalcular PnL, no ejecutar estudio económico y no modificar COG/OPS hasta terminar revisión y congelación por ambos arquitectos**. No es autorización para LIVE, VPS, MAIN, CIBO ni para abrir Fresh Holdout.

**ADVERTENCIA TEMPORAL:** este documento es preregistro para la **SIGUIENTE** adjudicación (que aún no se ha ejecutado), redactado DESPUÉS de conocer el tamaño agregado 51/2140 y los resultados A/B públicos. **No puede declararse preregistro original del A/B de 2026-10-10, ni restaurar independencia estadística en esos datos**. La regla A/B preinscrita en `d4db56fb45228d74a065349a97e562f2fbc6f657` sigue inmutable y B sigue FAIL 31,31 % unknown vs límite 10 %.

## ADENDA G3 — delimitación de los 51, decisión QORE propuesta y congelamiento irrevocable (12-10-2026)

**Dictamen de auditoría geométrica (sin abrir el replay):** los 51 no son desacuerdos cuantificados entre métodos de stop de ICT. El código B cae en `UNPROVEN_PROTECTED_STOP_GEOMETRY` cuando su **único** swing protegido no queda del lado de pérdida del CE: LONG `pivot >= CE`; SHORT `pivot <= CE`. **B no puede formular una orden auditable con stop protector en esos casos bajo su propia regla.** Un valor así no es un stop-loss elegible; tampoco prueba que C2 lo habría solucionado. El diagnóstico aplica a B experimental, no a la regla de producción vigente ni a un modelo nuevo.

### Tabla G-A — Sin contradicción de orientación del swing B en la clasificación agregada

| Sesión original | Candidatos fuera de la etiqueta `UNPROVEN_PROTECTED_STOP_GEOMETRY` | Alcance inferencial |
|---|---:|---|
| London 03–04 NY | **751** | No se detectó ese fallo puntual de orientación; **no** significa trade válida ni stop realmente negociable |
| NY AM 10–11 NY | **707** | Incluye posibles conflictos CE/cancelación en la misma M1 |
| NY PM 14–15 NY | **631** | Pendientes otros requisitos de entrada/ejecución |
| **Total** | **2.089** | `2140−51`, no 2.089 fills ni 2.089 stops certificados |

**Precisión sobre el rótulo:** “fuera de la etiqueta” es verificable en los agregados; **no** sustituye una auditoría individual de que todas las 2.089 referencias disponibles son de hecho válidas. En estos 2.089 permanecen las **619** secuencias `CE_AND_CANCELLATION_SAME_M1_UNKNOWN`; no convertirlas en contactos válidos. Esta **Tabla G-A** es un grupo geométrico, **NO** es el brazo experimental A de la prueba A/B anterior.

### Tabla G-B — Swing B del lado incorrecto de CE, sin stop protector en su propia definición

| Sesión original | `UNPROVEN_PROTECTED_STOP_GEOMETRY` | Tratamiento del ensayo B original |
|---|---:|---|
| London 03–04 NY | **15** | `INDETERMINATE`, sin operación económica auditable |
| NY AM 10–11 NY | **14** | `INDETERMINATE`, sin sustitución retrospectiva |
| NY PM 14–15 NY | **22** | `INDETERMINATE`, sin stop optimizado |
| **Total** | **51** | Etiqueta histórica inmutable del B preregistrado |

**Reconciliación obligatoria:** 2.089 + 51 = **2.140** candidatos, y dentro de los 670 indeterminados B se conserva la partición **619 + 51 = 670**. Ninguna tabla constituye nueva prueba sobre el resultado de los 51, ni validación de C2 o del swing: sólo separa las causas ya reportadas.

### Decisión normativa propuesta — **OPCIÓN 1, `QORE_NO_TRADE_IF_PROTECTED_SWING_WRONG_SIDE`**

Esta propuesta no afirma que ICT haya definido el caso. Si el **ensayo experimental B original** exigía swing protegido y ese swing queda del lado incorrecto del CE, la política prospectiva por defecto para **esa familia de estrategias basadas en swing** sería: `NO_TRADE / STOP_UNDEFINED`, sin introducir orden ni asignar R. Es la **Opción 1 conservadora**; reduce densidad de oportunidades, no demuestra rentabilidad.

- **Opción 2 — `FVG_CANDLE_FALLBACK`**: conservarla como **sensibilidad doctrinal separada**, definida antes de nuevos datos/retornos, y **NO** hacer fallback automático por caso dentro de B. Dado que elegir C1/C2/C3 cambia reglas y riesgo, requiere nueva identidad de experimento QORE independiente, definición exacta de vela, tick oficial y cohortes completas. Una eventual geometría válida no convierte a uno de los 51 históricos B en un fill.
- **Opción 3 — `DISTANCE_ATR_OR_FIXED`**: **NO AUTORIZADA** en este preregistro. Es un parámetro QORE sin respaldo primario preciso, susceptible de calibración retrospectiva; requeriría hipótesis independiente fijada ex ante, no una búsqueda adicional para salvar 51 casos.
- **Compatibilidad con [PR #881 — nueva propuesta QORE V1](https://github.com/mezas3238-hue/qore-core/pull/881)**: ese otro carril elige `QORE_C2_FULL_WICK_V1` **como stop primario desde el principio para un NUEVO trader/protocolo de investigación**, no como rescate de B en los 51 fallidos. Las propuestas no se pueden combinar silenciosamente: opción 1 gobierna la *familia swing-B*; C2 primario sólo puede gobernar el *nuevo protocolo C2* tras aprobación. **No hay doble firma** para ninguna de ellas en este corte; PR #881 figura `DECISION_DRAFT_UNSIGNED`.

### Cláusula de congelamiento **no revocable por resultados económicos**

> **Para el experimento identificado por su commit y protocolo firmado, la decisión metodológica aprobada es irrevocable respecto a ese mismo ensayo:** se declara **ANTES** de consultar resultados económicos o trayectoria posterior de esos casos. Una vez firmada y congelada, queda **prohibido** modificar la referencia inicial del stop, introducir fallback, aumentar distancia, modificar buffer o cambiar qué casos se descartan **aunque el Profit Factor, drawdown, expectancy o cualquier resultado posterior favorezca otra alternativa**. Si se considera imprescindible cambiar la regla, se debe **cerrar el ensayo original con su resultado intacto**, marcar explícitamente como `SUPERSEDED_NOT_RETROACTIVELY_RELABELED`, crear **nuevo protocolo prospectivo y nueva identidad/versionado** con preregistro separado y evaluación apropiada no consumida. No se permitirá recalcular y presentar la cohorte 3Y ya examinada como validación independiente; ningún ensayo modificado sustituye los fallos anteriores.

**Obligación de control de ejecución**: guardar el SHA completo del documento **aprobado**, firmas ARCH COG y OPS con `APROBAR/OBJETAR` y timestamp anterior al primer análisis individual de los 51, más identificador de cohorte y fuente. Si falta cualquiera, el guard exige `BLOCK_GEOMETRY_REPLAY` y `BLOCK_ECONOMIC_REPLAY`. Las firmas no se infieren de comentarios analíticos, del usuario, de los tests, ni de la mera existencia del PR. Un cambio futuro de README/documentación no puede desbloquear implícitamente el estudio.

### Dictamen cerrado sobre el **material ICT que ha podido verificarse**

- **`ICT_STOP_UNDERDETERMINED_FOR_REVIEWED_2023_MATERIAL` — CONCLUSIÓN DE REVISIÓN DOCUMENTAL, no regla pendiente de decidir.** En la transcripción completa indexada de la clase del [15-05-2023, lección original](https://www.youtube.com/watch?v=tRq1hyGGtl4) ([ASR trazable](https://info.quagmyre.com/xwiki/bin/view/Forex/The-Inner-Circle-Trader/ICT-Youtube-Series-2023/ICT-YT-2023-05-15-ICT-Mentorship-ICT-Silver-Bullet-Time-Based-Trading-Model/?xpage=print)), las referencias **10:34–10:55**, **13:12–13:55** y **14:53–15:30** explican FVG, dirección, ventana y ejemplos de operaciones, **sin precisar de manera algorítmica que todo Silver Bullet deba usar C2, far-edge, swing protegido ni un buffer numérico universal**. Menciona en **10:34–10:55** que el ejemplo no hubiera alcanzado su stop según sus reglas de otros modelos, **no especifica precio inicial de stop para nuestra implementación**.
- En la [lección del autor **22-05-2023, Evolving ICT Silver Bullet Example**](https://www.youtube.com/watch?v=DkOuO0eNwUA) ([ASR con timecodes](https://info.quagmyre.com/xwiki/bin/view/Forex/The-Inner-Circle-Trader/ICT-Youtube-Series-2023/ICT-YT-2023-05-22-ICT-Mentorship-2023-Evolving-ICT-Silver-Bullet-Example/)), en torno a **01:29–01:45** el autor describe un stop por encima del FVG para un ejemplo SHORT, luego hacia **06:50–07:05** comunica su stop revisado. **Eso acredita la existencia de un ejemplo, no una regla universal C2 vs gap vs swing para todos los casos**.
- La frase referida en la discusión como “más allá de la vela que formó el gap” **no se atribuye como cita textual verificada de la lección del 15-05-2023**, pues no se localizó allí tal prescripción con timestamp y alcance inequívocos. Si otro revisor aporta nueva grabación y timecode que la sustenten, se agregará como **evidencia doctrinal nueva, con control de versión**; no se cambiará retroactivamente la fórmula ni el ensayo ya congelado.
- **Límite de la prueba de fuentes**: se verificaron **transcripciones externas de las presentaciones originales**, no se hizo una auditoría audiovisual exhaustiva de cada diapositiva y de toda la obra de ICT. La conclusión es `NO_ACREDITADO_EN_FUENTES_REVISADAS`, no la afirmación metafísica de que el autor **jamás** prescribió otro stop.

**Estado deliberado:** `GEOMETRY_DIAGNOSIS_CLOSED / ICT_SOURCE_SCOPE_REVIEWED / QORE_OPTION_1_DRAFT_UNSIGNED / DUAL_SIGNOFF_MISSING / REPLAY_BLOCKED`. Primero decidir/fijar por los dos arquitectos; **después** auditar geometría sin PnL; y **sólo** tras fuente sub-M1/OMS y política integral aprobada plantear economía.

---

## 1. Hallazgo causal que delimita exactamente el problema

En `scripts/vt31_shadow_opposite_pivot_ab_v1.py`, función `Shadow.on_m1`, la clasificación `UNPROVEN_PROTECTED_STOP_GEOMETRY` se dispara **antes** de examinar CE, DOL, FVG, stop real o PnL si:

```python
LONG:  protected.price >= source_ce
SHORT: protected.price <= source_ce
```

El `protected.price` de B proviene del último swing opuesto local de **tres M1** confirmado **antes** del MSS que originó el setup; función `opposing_pivot`. Este requisito y ese swing son formalizaciones **experimentales QORE**, no evidencia textual de que ICT imponga dicho pivote. La etiqueta exige stop al otro lado de CE y **no dice si la vela central C2, la frontera lejana del gap o el extremo de un barrido serían mejores**. Por eso **NO** es válido afirmar que esos 51 errores se deben específicamente a la elección wick vs body de C2 o a buffers. Datos congelados del 3Y: 51 `UNPROVEN_PROTECTED_STOP_GEOMETRY` (15 London, 14 NY AM, 22 NY PM), además de **619** conflictos CE/cancelación en la misma M1. La segunda clase NO entra en este preregistro.

El modelo B preexistente **NO** se reparará retrospectivamente sustituyendo el pivote por otro stop, ni se reasignará su UNKNOWN a `VALID_CE`, `WIN`, `LOSS` o `INVALIDATED`. El libro B original queda intacto.

## 2. Jerarquía de fuentes y verificación ya realizada

| Proposición | Fuente verificable | Clasificación actual | Dictamen |
|---|---|---|---|
| Silver Bullet se basa en ventanas New York 03–04 / 10–11 / 14–15, FVG y dirección al siguiente DOL | **Fuente primaria:** [ICT, 2023 Mentorship — Silver Bullet Time Based Trading Model (video publicado 2023-05-14)](https://www.youtube.com/watch?v=tRq1hyGGtl4); [transcripción de ese mismo video, no certificada por el autor](https://sozai.app/transcript/ict-mentorship-silver-bullet-trading-model/) | `ICT_PRIMARY_SUPPORTED` con reserva de errores de transcripción | Confirmado para contexto, no para SL |
| El stop universal del Silver Bullet siempre queda por debajo/encima del **wick de vela central C2** | **NO se localizó en el material verbal de la lección 2023 consultado un pasaje inequívoco que obligue C2 con esa granularidad** | `UNVERIFIED_PRIMARY` | **NO declarar canon ICT**; exigir video original y timestamp/imagen inequívoca por revisión ARCH1+OPS |
| El stop puede usar extremo de vela que creó FVG | [Guía educativa de tercero](https://innercircletrader.net/tutorials/ict-silver-bullet-strategy/) (sitio de terceros, NO identidad acreditada de ICT) | `SECONDARY_ONLY` | Apoya hipótesis; no prueba C2 frente a C1/C3 |
| Alternativa swing previo o vela FVG | [Guía educativa de tercero](https://fxnx.com/en/blog/ict-silver-bullet-master-10-11-am-setup/) | `SECONDARY_ONLY` | Fuentes externas discrepan, no escoger ganador por reputación de marca |
| Stop basado en swing contrario de 3 M1 causal previo a MSS | [Código original B](https://github.com/mezas3238-hue/qore-core/blob/949a4fdd335eb9943ea6436f6136415029aff599/scripts/vt31_shadow_opposite_pivot_ab_v1.py) y [preregistro original A/B](https://github.com/mezas3238-hue/qore-core/blob/949a4fdd335eb9943ea6436f6136415029aff599/docs/research/VT31_OPPOSITE_PIVOT_AB_PREREGISTRATION_2026-10-10.md) | `QORE_EXPERIMENTAL_B` | Nunca atribuir al autor |
| Buffer exacto X puntos o ATR×k es obligación ICT universal | Ningún testigo primario explícito de la lección 2023 verificado hasta este corte | `UNVERIFIED_PRIMARY` | **Prohibido calibrarlo con los 51 o por PF** |

**Regla de prueba primaria:** para elevar una afirmación de stop a `ICT_PRIMARY_VERIFIED`, dos arquitectos registran **URL original en canal del autor + timestamp exacto + paráfrasis mínima + relación precisa con C1/C2/C3 o swing + confirmación de que se refiere a este modelo y no a una variante distinta**. No aceptar una infografía secundaria, blog que lleve “ICT” en el dominio, transcripción imprecisa, resumen de IA o un simple ejemplo dibujado como obligación general. Si el video 2023 no da regla única, escribir `ICT_STOP_UNDERDETERMINED` y escoger o abstener una **formalización QORE propuesta**, sin llamarla canónica.

## 3. Las tres preguntas, con resolución reproducible PREVIA a outcomes

**Q1 — ¿Qué referencia exacta constituye stop?** Congelar las tres definiciones de lectura **como alternativas doctrinales, NO tres variantes para optimizar rentabilidad**:

| ID de definición | Para LONG, precio bruto de referencia | Para SHORT, precio bruto de referencia | Procedencia |
|---|---|---|---|
| `C2_FULL_WICK` | mínimo `low(C2)` de la segunda vela de FVG M1 | máximo `high(C2)` | hipótesis basada en interpretación “vela que crea gap”; no canon demostrado |
| `FVG_FAR_EDGE` | `zone_low` del FVG de tres velas | `zone_high` | interpretación de zona (extremos C1/C3); no equivale a C2 |
| `PRE_MSS_OPPOSITE_SWING_B` | swing low contrario `protected.price` confirmado antes del MSS | swing high contrario confirmado antes del MSS | formalización EXPERIMENTAL_B original de QORE |

Identificación temporal inmutable: FVG por 3 velas **M1 contiguas** C1, C2, C3; `C1.closed_at=C2.opened_at`, `C2.closed_at=C3.opened_at`, `formed_at=C3.closed_at`. C2 no equivale automáticamente a C1 ni C3. Todos los precios de C1/C2/C3 estaban cerrados **antes** de la primera oferta después de C3; jamás usar swing confirmado post-MSS o vela posterior para elegir stop. El `FVG_FAR_EDGE` es el borde lejano de **zona no negociada**, no el mínimo/máximo de toda la secuencia de velas.

**Q2 — ¿Buffer?** La decisión de **doctrina** se hace sobre nivel **bruto, sin buffer añadido** para comparar geometría. Para una orden real “más allá del extremo”, no existe precio negociable predefinido hasta obtener el `trade_tick_size` oficial del MISMO símbolo/broker. Única opción operativa **QORE propuesta**, sujeta a revisión: un tick de instrumento al lado externo (`LONG = reference − tick_size`; `SHORT = reference + tick_size`); no 1 punto arbitrario, no ATR, no optimización. Esta política propuesta **NO** está activa y no cambia la geometría del estudio original B. Sin contrato certificado => `STOP_NOT_PRICEABLE`, no inventar tick.

**Q3 — ¿Stop de vela o stop estructural?** Son **tesis económicas distintas**. Elegir `C2_FULL_WICK` frente a `PRE_MSS_OPPOSITE_SWING_B` cambia no sólo precio del SL, sino tamaño R, elegibilidad, stops vs targets y posibles resultados. No añadir “mejor de ambos”, `min/max` a conveniencia, filtros selectivos o reelegir swing cuando B falla. Si falta evidencia primaria de prioridad del método, registrar `STOP_DOCTRINE_UNRESOLVED` y mantener los 51 UNKNOWN. Una nueva formalización (por ejemplo `C2_FULL_WICK`) requiere **un nuevo estudio prospectivo distinto, nuevo preregistro económico, mismos 2.140 IDs sin cherry-picking y revisión cruzada**. No se renombra retrospectivamente como B v1.

## 4. Prereglas mecanizables para una auditoría geométrica **posterior a sign-off**

La nueva auditoría, si es aprobada, se limita a evaluar la **consistencia causal/geométrica** de los 51 IDs, sin outcome del precio ni PnL:

1. Inmovilizar IDs originales `(ny_day, session_window, source_fvg_confirmed_at)` desde artefacto #11750991244, SHA validada. Extraer únicamente los **51** con `B_class=INDETERMINATE` + `B_research_terminal=UNPROVEN_PROTECTED_STOP_GEOMETRY`. Verificar 15/14/22 y unicidad; las otras **619** permanecerán fuera.
2. Volver a leer **solamente tres velas C1/C2/C3 ya cerradas** y pivot B original confirmado temporalmente, desde el 3Y development congelado hash `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. Reconstruir CE y zone_low/high con el motor M1 original. No mirar highs/lows posteriores ni salida.
3. Para **cada ID y cada definición** producir `reference_price`, `CE`, `side`, `as_of`, `source_label`, `reference_observed_at`, `geometry_valid`. Geometría sin buffer: `LONG reference < CE`, `SHORT reference > CE`. Igualdad = inválida; `None` o timestamp futuro => indeterminado no interpolado.
4. En cada definición reportar sin ranking de éxito: cuántos `GEOMETRY_VALID`, `WRONG_SIDE_OF_CE`, `MISSING_REFERENCE`, `CAUSAL_TIME_VIOLATION`, y matriz pareada completa de etiquetas **en los mismos 51 IDs**; **nunca** filtrar sólo por elegibles.
5. Clasificación final de doctrina sólo tras doble firma: `PRIMARY_VERIFIED_C2`, `PRIMARY_VERIFIED_GAP`, `PRIMARY_VERIFIED_SWING`, o `DOCTRINE_UNRESOLVED`. Un resultado numérico de geometría **no autoriza** ninguna de las tres etiquetas `PRIMARY_VERIFIED_*`: ellas exigen fuente original, no datos de mercado.
6. **Prohibiciones explícitas:** no calcular win rate, stop-hit, R:R, PF, DD, Sharpe/Sortino, post-CE price path ni comparar rendimiento entre alternativas. No correr backtests de variantes. No actualizar A/B original, su 10 % de límite, ni su 51 UNKNOWN. Un signo de mayor número de geometrías válidas no prueba una regla “más ICT”.

### Invariantes y tests sintéticos obligatorios ANTES de releer 51 casos

- **Long:** CE=105, C2.low=100, FVG zone_low=103, swing B=108 => `C2_FULL_WICK` y `FVG_FAR_EDGE` geométricamente válidos, `PRE_MSS_OPPOSITE_SWING_B` inválido. **Short espejo:** CE=105, C2.high=110, FVG zone_high=107, swing B=102 => C2 y FVG válidos; B inválido.
- Igualdad a CE => inválido; lado incorrecto y referencias ausentes => no elegible/unknown según causa.
- Confirmación swing posterior al MSS o vela no cerrada => no aceptar aunque el nivel sea favorable.
- `tick_size<=0`, lot/contrato desconocido, alias NDX100↔NAS100 sin prueba => no precio de orden, no fill, no certificado.
- Los 619 de misma M1 siguen intactos y nunca son incorporados a los 51 por conveniencia.

Estos son **test fixtures inventados solo para control lógico** (no cotizaciones reales, no evidencia de resultado).

## 5. Política de decisión antes de tocar el dataset

**A. Si se obtiene cita ICT primaria inequívoca para una sola referencia:** ambas partes firman qué conducta y contexto exacto especifica, separan cualquier buffer como QORE, congelan el hash del doc y habilitan **solo auditoría geométrica observacional sin PnL**; cualquier estrategia nueva tiene su preregistro económico independiente y no edita el A/B.

**B. Si el material primario presenta variantes legítimas:** no seleccionar automáticamente la que cubra más 51 casos; registrar `MULTIPLE_DOCTRINAL_VARIANTS` y mantener cada lectura separada. B original sigue FAIL.

**C. Si el material original no fija el stop con precisión algorítmica:** devolver `ICT_STOP_UNDERDETERMINED`; escoger abstención como decisión científica por defecto. Se puede **proponer** `C2_FULL_WICK` como convención nativa QORE para **futuro** estudio, pero requiere aprobación y no se anunciará como ICT original ni se validará sobre los 51 ya vistos por outcome.

**D. Si la fuente de velas o timestamps no se puede verificar:** `DATA_LINEAGE_INCOMPLETE`; no construir sustitutos sintéticos ni declarar geométricamente solucionados los casos.

**Regla de paro:** no explorar cuartos stops, buffer X, ATR, stops elegidos por resultados o relajar criterio geométrico hasta pasar revisión primaria. Los 619 conflictos intraminuto se estudiarán **sólo después** de cerrar este problema doctrinal; sin Bid/Ask real con secuencia y OMS/ACK seguirá `INSUFFICIENT_EVIDENCE`.

## 6. Hoja obligatoria de revisión cruzada (ninguna firma inferida)

| Revisor | Qué debe verificar | Estado |
|---|---|---|
| **Arquitecto COG/Methodology** | Fuente primaria, timestamp de stop C2/gap/swing, fidelidad de tesis, causalidad as-of, regla final/falta de regla | **PENDIENTE** |
| **Arquitecto OPS/Execution** | Diferencia referencia vs stop negociable, `tick_size`/broker/source, distinción oferta vs posición, no cambios a B, ningún fill supuesto | **PENDIENTE** |
| **Auditor externo (p.ej. DeepSeek Expert)** | Revisar la atribución a ICT y cualquier frase que se presente como regla universal sin cita original verificable | **CONSULTA OPCIONAL, SIN FIRMA** |

La conformidad debe registrarse con comentario explícito en [Issue #727](https://github.com/mezas3238-hue/qore-core/issues/727) enlazando el **commit SHA concreto** y una de las opciones `PRIMARY_VERIFIED_C2 / PRIMARY_VERIFIED_GAP / PRIMARY_VERIFIED_SWING / MULTIPLE_DOCTRINAL_VARIANTS / ICT_STOP_UNDERDETERMINED`, incluyendo URL+timestamp de fuente primaria cuando haya una elección. Comentarios anteriores o silencio **NO** constituyen aprobación. Tras ambas firmas, **congelar preregistro** en nuevo commit de documentación/manifest antes de ejecutar la auditoría de geometría; no seleccionar metodología usando resultados.

## 7. Estado de gates en el corte

| Gate | Estado |
|---|---|
| Identificación del bug/gate de geometría B | **VERIFICADA** a partir de código, causa agregada 51 |
| Regla universal de stop C2 supuestamente ICT | **NO ACREDITADA CON CITA PRIMARIA EN ESTE CORTE** |
| Causalidad y fórmula de comparaciones C2/far-edge/pivote | **PREREGISTRADAS COMO ALTERNATIVAS DE AUDITORÍA** |
| Revisión ARCH1 + OPS | **PENDIENTE** |
| Replay sobre los 51 IDs | **NO EJECUTADO** |
| Resolver 619 same-M1 | **PENDIENTE TICKS+OMS** |
| Edge económico, broker fills, PF, DD | **NO DEMOSTRADO** |
| Gates de B y Fresh Holdout | **B FAIL, HOLDOUT SELLADO** |
| LIVE / VPS / MAIN | **SIN AUTORIZACIÓN / SIN CAMBIOS** |

**Resultado:** preregistro documental para revisión, **NO resolución post-hoc de 51 casos**. A/B original preservado. Prioridad inmediata: contrastar la definición de stop contra la **fuente primaria** y dejar el dictamen dual antes del primer cómputo de geometría.

---

### Fuentes de custodia

- [Lección ICT 2023 primaria](https://www.youtube.com/watch?v=tRq1hyGGtl4), [transcripción de tercero de la lección](https://sozai.app/transcript/ict-mentorship-silver-bullet-trading-model/).
- [Guía de terceros, stop de vela](https://innercircletrader.net/tutorials/ict-silver-bullet-strategy/), [guía alternativa swing/FVG](https://fxnx.com/en/blog/ict-silver-bullet-master-10-11-am-setup/).
- [Código B y condición exacta que produce 51](https://github.com/mezas3238-hue/qore-core/blob/949a4fdd335eb9943ea6436f6136415029aff599/scripts/vt31_shadow_opposite_pivot_ab_v1.py).
- [Preregistro original 2026-10-10](https://github.com/mezas3238-hue/qore-core/blob/949a4fdd335eb9943ea6436f6136415029aff599/docs/research/VT31_OPPOSITE_PIVOT_AB_PREREGISTRATION_2026-10-10.md).
- [Evidencia 2.140 IDs / banda de no identificación](https://github.com/mezas3238-hue/qore-core/pull/876).
