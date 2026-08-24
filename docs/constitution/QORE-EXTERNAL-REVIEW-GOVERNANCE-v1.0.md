# QORE External Review Governance v1.0

## Propósito

Esta norma define el contrato obligatorio de revisión técnica externa para entregas de QORE Core. Su objetivo es preservar independencia de validación, evidencia reproducible, fail-closed ante incertidumbre y consumo eficiente de revisores externos sin degradar la calidad.

La infraestructura que ejecuta revisores externos permanece fuera de QORE Core. Core fija el contrato de revisión; la implementación operativa vive en un repositorio de reviewer aislado y puede evolucionar mientras conserve este contrato.

## 1. Fuente de verdad y binding congelado

Toda revisión externa debe ejecutarse contra una vinculación exacta y verificable:

- PR objetivo;
- BASE SHA exacto;
- HEAD SHA exacto;
- SYNTHETIC/MERGE SHA exacto cuando GitHub lo provea;
- padres del synthetic exactamente BASE + HEAD;
- árbol del synthetic idéntico al árbol del HEAD cuando corresponda;
- superficie BASE→HEAD completa, no sólo el último commit;
- estado de CI ligado al mismo HEAD.

Si cualquiera de estos valores cambia, el resultado anterior no autoriza integración del nuevo HEAD.

GitHub es la fuente de verdad. Una afirmación textual nunca sustituye la verificación viva.

## 2. Quality Gate previo

No se despacha revisión externa sobre un candidato con Quality Gate conocido en rojo.

Antes del freeze deben estar verdes, cuando apliquen:

1. `ruff check .`
2. `mypy`
3. `pytest --cov=src/qore --cov-report=term-missing`

Errores de lint, tipos, tests o CI se corrigen en la misma rama antes de congelar el paquete.

## 3. Cadena serial obligatoria

La secuencia estándar para una entrega revisable es:

1. implementación + tests + documentación necesaria;
2. Quality Gate verde;
3. freeze exacto BASE/HEAD/SYNTHETIC/delta;
4. DeepSeek Expert;
5. adjudicación IA independiente del resultado Expert;
6. DeepSeek Coder;
7. adjudicación IA independiente del resultado Coder;
8. Claude Code manual;
9. adjudicación IA independiente del resultado Claude;
10. IA FINAL;
11. Ready for Review;
12. merge protegido con `expected_head_sha`;
13. verificación post-merge de `main`, árbol, padres, CI y tracker;
14. avance al siguiente delivery.

No se prepara ni despacha Coder antes de un Expert técnicamente cerrado por adjudicación IA. No se abre Claude antes de cerrar Coder. No se marca Ready ni se hace merge antes de Claude + IA FINAL.

## 4. Adjudicación independiente

Los revisores externos aportan evidencia; no poseen autoridad final sobre QORE.

Todo hallazgo debe ser adjudicado contra el código y contrato reales. Para ser material debe incluir, como mínimo:

- ubicación exacta;
- witness/estado constructible;
- comportamiento esperado;
- comportamiento real;
- invariante o contrato violado;
- impacto;
- corrección mínima acotada.

Un hallazgo no reproducible se rechaza con evidencia. Un resultado limpio obtenido con evidencia incompleta no se promueve a PASS.

## 5. Fail-closed obligatorio

El reviewer debe bloquear una conclusión limpia si ocurre cualquiera de estas condiciones:

- binding incompleto o contradictorio;
- evidencia requerida ausente;
- herramienta requerida falla;
- evidencia truncada de forma material;
- análisis termina sin soporte suficiente para el veredicto;
- resultado final no puede vincularse al package/HEAD exacto;
- incertidumbre sobre si un defecto material quedó sin revisar.

`EVIDENCIA INSUFICIENTE / VALIDACIÓN BLOQUEADA` es un resultado válido de infraestructura, no un PASS ni un defecto automático de QORE.

## 6. Anti-duplicación de DeepSeek

Regla permanente: **ONE package → ONE dispatch → ONE DeepSeek job**.

Antes de escribir el request se verifica:

- que el package_id sea nuevo para ese stage/HEAD;
- que no exista marker publicado del mismo package;
- que `requests/current.json` no lo haya despachado previamente;
- que BASE/HEAD/SYNTHETIC sigan congelados.

Después del dispatch no se vuelve a tocar el request para ese package.

Sólo puede crearse un package nuevo si el anterior quedó formalmente adjudicado y se requiere una nueva revisión por cambio de infraestructura o de HEAD. Un mismo package sólo podría reintentarse si existe evidencia inequívoca de fallo pre-dispatch con cero jobs DeepSeek creados.

## 7. Aislamiento de infraestructura

QORE Core no contiene:

- API keys de DeepSeek;
- lógica de llamada al modelo;
- balances/cost meter del proveedor;
- workflows de reviewer externo;
- prompts operativos mutables del reviewer;
- dependencias runtime hacia DeepSeek, Claude u otro proveedor de IA.

La infraestructura externa debe operar read-only sobre el candidato, salvo la publicación de evidencia/reviews autorizada por GitHub.

Los secretos nunca se incorporan a prompts, reviews, evidencia, logs o commits de Core.

## 8. Perfil DeepSeek validado vigente

Perfil operativo validado al adoptar esta norma:

- repositorio de infraestructura: `mezas3238-hue/qore-deepseek-reviewer`;
- reviewer family: V2.1.1;
- modelo autoritativo: `deepseek-v4-pro`;
- análisis adversarial: thinking/high;
- evidencia: determinista y completa para el delta congelado, con herramientas exactas y fail-closed;
- emisión de veredicto: mismo modelo en non-thinking únicamente para extraer/formatear conclusiones soportadas por el análisis retenido cuando el high pass no emite contenido visible completo;
- no Flash substitution;
- no CoT continuation;
- no replay completo del evidence bundle en el extractor;
- extractor sin autoridad para inventar hallazgos ni fabricar PASS.

Este perfil puede evolucionar sin modificar esta norma siempre que preserve o mejore cobertura, independencia, binding, fail-closed, anti-duplicación y calidad.

## 9. Presupuesto de consumo

Para superficies comparables a las UNR recientes:

- rango preferido de prompt: 25.000–60.000 tokens;
- tolerable: ≤75.000;
- warning: >75.000;
- no estabilizado: >100.000 salvo evidencia concreta de una superficie materialmente mayor;
- objetivo normal: máximo 3 llamadas cuando se requiera planner + análisis + extractor;
- cualquier regresión de calidad atribuible a reducción de tokens obliga a aumentar evidencia/budget o revertir la optimización.

El ahorro de tokens nunca justifica reducir cobertura material, cambiar silenciosamente a un modelo inferior ni relajar fail-closed.

## 10. Evidencia de referencia de adopción

La adopción se basa en el cierre de DeepSeek Coder R1H de UNR-019 sobre el freeze:

- BASE `25ed21be1ba427820be78dbb8958d441e5f27f9c`;
- HEAD `b2fae639779bdf27c497929af1a545ae70a42649`;
- SYNTHETIC `db81e5268ee0abdc7cf07018d5daf7e9768d8604`;
- `plan_incomplete=false`;
- sin tool errors ni reason markers;
- `HALLAZGOS: NINGUNO / VALIDACIÓN OK`;
- 39.069 prompt tokens;
- 20.000 reasoning tokens;
- 3 llamadas API;
- adjudicación IA: Coder PASS.

La evidencia histórica justifica el perfil actual; no convierte esos números en una excepción para relajar la calidad.

## 11. Cambio de perfil

Una optimización futura del reviewer se acepta sólo si:

1. no reduce cobertura material;
2. conserva el mismo o mayor fail-closed;
3. conserva binding exacto y anti-duplicación;
4. conserva independencia respecto de la implementación;
5. no introduce secretos o autoridad operativa en Core;
6. demuestra consumo igual o mejor en revisiones legítimas o benchmarks no publicantes;
7. no produce una regresión de calidad conocida.

Ante conflicto entre ahorro y calidad, prevalece calidad.

## 12. Autoridad y vigencia

Esta norma es obligatoria para nuevas entregas de QORE Core que entren al gate de revisión externa desde su merge en `main`.

No autoriza Production, real capital, ejecución real, bypass de Risk ni ninguna ampliación de autoridad operativa.
