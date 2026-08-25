# QORE External Review Governance v1.0

## Propósito

Esta norma define el contrato obligatorio de revisión técnica externa para entregas de QORE Core. Su objetivo es preservar independencia de validación, evidencia reproducible y fail-closed ante incertidumbre sin introducir dependencias operativas o económicas del proveedor de revisión dentro de Core.

La infraestructura que ejecuta revisores externos permanece fuera de QORE Core. Core gobierna únicamente el contrato técnico que una revisión debe satisfacer; la implementación operativa, telemetría, costes y mantenimiento del reviewer viven fuera de Core.

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

Sólo puede crearse un package nuevo si el anterior quedó formalmente adjudicado y se requiere una nueva revisión por cambio de HEAD o por un cambio técnico material del reviewer. Un mismo package sólo podría reintentarse si existe evidencia inequívoca de fallo pre-dispatch con cero jobs DeepSeek creados.

## 7. Aislamiento de infraestructura

QORE Core no contiene:

- API keys de DeepSeek;
- lógica de llamada al modelo;
- balances, costes o medidores económicos del proveedor;
- workflows de reviewer externo;
- prompts operativos mutables del reviewer;
- dependencias runtime hacia DeepSeek, Claude u otro proveedor de IA.

QORE Core tampoco define, almacena, evalúa ni usa presupuestos de tokens, precios, límites de consumo, telemetría económica o baselines de coste del reviewer como criterio de aceptación, bloqueo, promoción o priorización de una entrega. Toda observabilidad económica del reviewer pertenece exclusivamente a la infraestructura externa y no forma parte del estado técnico de Core.

La infraestructura externa debe operar read-only sobre el candidato, salvo la publicación de evidencia/reviews autorizada por GitHub.

Los secretos nunca se incorporan a prompts, reviews, evidencia, logs o commits de Core.

## 8. Perfil técnico externo validado vigente

`qore-core/main`, mediante esta norma, es la fuente autoritativa del **contrato técnico** que debe satisfacer el reviewer estable activo. Debe existir exactamente un perfil técnico estable activo y reconstruible. La infraestructura externa no puede cambiar por sí sola las garantías exigidas por Core.

Contrato técnico vigente al adoptar esta norma:

- profile id: `QORE-DEEPSEEK-V2.1.1-STABLE`;
- repositorio operativo externo: `mezas3238-hue/qore-deepseek-reviewer`;
- manifest operativo de descubrimiento: `profiles/QORE-DEEPSEEK-V2.1.1-STABLE.json`;
- reviewer family: V2.1.1;
- entrypoint técnico esperado: `scripts/deepseek_reviewer_v2_1_1_entrypoint.py`;
- workflows permanentes autorizados, exactamente estos tres:
  - `.github/workflows/deepseek-auto-dispatch.yml`;
  - `.github/workflows/deepseek-connection-test.yml`;
  - `.github/workflows/deepseek-qore-review.yml`;
- modelo autoritativo para review: `deepseek-v4-pro`;
- análisis adversarial: thinking/high;
- evidence path obligatorio:
  - contenido exacto y completo de cada archivo cambiado BASE→HEAD;
  - patch BASE→HEAD exacto para archivos modificados;
  - slices semánticos deterministas de definiciones locales `qore.infrastructure` importadas directamente, con helpers referenciados de forma acotada;
  - repo state congelado, binding del PR, checks del HEAD y combined commit status exactos;
  - un único planner non-thinking acotado para evidencia adicional genuinamente necesaria;
  - herramientas de planner autorizadas exactamente: `read_file`, `search_text`, `git_show`, `github_get`;
  - `search_text` usa `git grep -n -F -I` sobre contenido tracked del checkout congelado de qore-core;
  - herramientas read-only restringidas al checkout congelado y endpoints GitHub de qore-core;
  - resultados exactos hasta el hard gate; nunca pre-clipping silencioso; falta/truncación material ⇒ `EVIDENCIA INSUFICIENTE / VALIDACIÓN BLOQUEADA`;
- emisión de veredicto: mismo modelo en non-thinking únicamente para extraer/formatear conclusiones soportadas por el análisis retenido cuando el high pass no emite contenido visible completo;
- no Flash substitution;
- no CoT continuation;
- no replay completo del evidence bundle en el extractor;
- extractor sin autoridad para inventar hallazgos ni fabricar PASS.

El manifest es **evidencia operativa externa de descubrimiento**, no autoridad constitucional ni fingerprint económico de Core. Core no pinnea ni compara el blob SHA bruto del manifest y no interpreta campos de meter, coste, tokens, precios, balances, presupuestos o telemetría. Un cambio de esos campos o de cualquier metadata externa no técnica no constituye profile drift y no puede bloquear una entrega de Core.

La verificación de perfil se hace sobre la **proyección técnica** declarada arriba y sobre el comportamiento vivo requerido: profile id, familia, entrypoint efectivo, conjunto de workflows, modelo/reasoning/extractor, evidence path, binding, anti-duplicación y fail-closed. La implementación interna del reviewer puede evolucionar sin cambiar el perfil cuando se demuestra que conserva exactamente esas garantías. Si no puede demostrarse la equivalencia técnica, se falla cerrado.

Cualquier cambio semántico que altere una garantía técnica de esta sección constituye un cambio de perfil y debe seguir la sección 11. Un sucesor puede existir como candidato o benchmark en la infraestructura sin quedar activo; sólo se activa después del gate independiente y de una actualización explícita de `qore-core/main`.

## 9. Separación de economía operativa del reviewer

La economía operativa del reviewer externo es responsabilidad exclusiva de `qore-deepseek-reviewer` y de su operación fuera de Core.

QORE Core no establece fórmulas de consumo, techos de tokens, costes máximos, precios, balances, presupuestos, objetivos de llamadas API ni clasificaciones económicas de un job. Esos datos no pueden convertirse en un gate técnico de Core, modificar el resultado de una adjudicación técnica, invalidar un PASS soportado por evidencia ni retrasar el roadmap de Core.

Si la infraestructura externa registra o reporta telemetría económica, esa información permanece fuera de los contratos y artefactos de Core. Una optimización económica del reviewer es mantenimiento externo y nunca autoriza reducir cobertura, evidencia, modelo o fail-closed.

## 10. Evidencia técnica de referencia de adopción

Como evidencia histórica de operación técnica del perfil V2.1.1 se conserva el cierre de DeepSeek Coder R1H de UNR-019 sobre el freeze:

- BASE `25ed21be1ba427820be78dbb8958d441e5f27f9c`;
- HEAD `b2fae639779bdf27c497929af1a545ae70a42649`;
- SYNTHETIC `db81e5268ee0abdc7cf07018d5daf7e9768d8604`;
- `plan_incomplete=false`;
- sin tool errors ni reason markers;
- `HALLAZGOS: NINGUNO / VALIDACIÓN OK`;
- adjudicación IA técnica: Coder PASS.

No se incorpora a Core telemetría de consumo o coste asociada a ese job. Cualquier registro económico histórico pertenece exclusivamente a la infraestructura externa y carece de autoridad sobre el estado técnico de QORE Core.

Esta evidencia demuestra comportamiento técnico observado; no es autoridad suficiente para auto-certificar un perfil ni un sucesor. Ningún PASS emitido por DeepSeek sobre su propia infraestructura puede sustituir el gate independiente de la sección 11.

## 11. Cambio de perfil técnico

Un cambio futuro del reviewer sólo requiere actualización de Core cuando cambia materialmente el contrato técnico de la sección 8. Para promover un nuevo perfil técnico estable:

1. no reduce cobertura material;
2. conserva el mismo o mayor fail-closed;
3. conserva binding exacto y anti-duplicación;
4. conserva independencia respecto de la implementación revisada;
5. no introduce secretos o autoridad operativa en Core;
6. demuestra calidad igual o superior en revisiones legítimas o benchmarks no publicantes;
7. no produce una regresión de calidad conocida;
8. recibe validación independiente que no dependa exclusivamente del componente DeepSeek que está siendo sustituido o modificado;
9. su evidencia y adjudicación quedan vinculadas desde una actualización explícita de esta norma en `qore-core`;
10. esa actualización declara el nuevo profile id y toda garantía técnica modificada: familia, entrypoint, workflows, modelo/reasoning/extractor, evidence path, binding, anti-duplicación o fail-closed.

Cambios puramente operativos, económicos, de telemetría o metadata externa que preservan el contrato técnico no son cambios de perfil Core y no requieren modificar QORE Core.

La infraestructura DeepSeek bajo cambio puede aportar benchmarks y findings como evidencia, pero no puede aprobar por sí sola su propio sucesor. El gate independiente debe incluir adjudicación técnica independiente y revisión manual de Claude Code sobre el delta técnico relevante; cualquier finding material se corrige y vuelve a validar antes de promover el candidato.

El orden de activación es obligatorio:

1. implementar o benchmarkear el candidato sin desplazar el perfil técnico estable activo;
2. producir evidencia reproducible y completar el gate independiente;
3. abrir en `qore-core` un PR de governance que actualice explícitamente esta norma sólo si cambia el contrato técnico;
4. completar para ese PR la cadena externa vigente y mergearlo de forma protegida;
5. sólo después de que `qore-core/main` publique el nuevo contrato técnico puede ese perfil usarse como estable en dispatches ordinarios.

Hasta el paso 4 inclusive, el contrato técnico anterior continúa vigente. Si no puede demostrarse que el reviewer vivo lo satisface, los dispatches se bloquean; no se adelanta el switch.

Los criterios económicos del proveedor o de la infraestructura externa no forman parte de este gate.

## 12. Persistencia entre chats, sesiones y coordinadores

El método técnico de revisión vigente es estado persistente del proyecto, no estado conversacional.

Su vigencia no cambia por abrir un chat nuevo, compactar contexto, reiniciar una sesión, cambiar dispositivo, cambiar coordinador o transcurrir tiempo entre entregas.

Al inicio de cada sesión que pueda despachar DeepSeek, el coordinador debe reconstruir desde GitHub, antes de cualquier dispatch:

1. esta norma desde `qore-core/main` como fuente autoritativa del contrato técnico;
2. el único profile id estable y las garantías técnicas explícitas de la sección 8;
3. el `main` actual de `qore-deepseek-reviewer`;
4. que el manifest operativo exista y declare el mismo profile id y la misma proyección técnica; su blob bruto y sus campos económicos no son comparados por Core;
5. que el workflow de review seleccione el entrypoint técnico esperado y que el call path vivo corresponda al modelo/reasoning/extractor/evidence path autorizados;
6. que existan exactamente los tres workflows permanentes autorizados y que el workflow de review use el modelo autorizado;
7. que el evidence path vivo preserve el mandatory bundle y exactamente las herramientas `read_file`, `search_text`, `git_show`, `github_get`, con `search_text` por `git grep` y autoridad read-only acotada a qore-core;
8. que las garantías de fail-closed, binding y anti-duplicación sigan presentes; si una equivalencia técnica no puede demostrarse, el dispatch se bloquea;
9. el último estado de `requests/current.json` para anti-duplicación;
10. los reviews/markers existentes del PR objetivo;
11. el binding exacto del PR candidato y su CI.

El coordinador no puede inferir una configuración desde memoria cuando GitHub puede verificarla.

Los commits de prompts, requests, dispatches, telemetry, meter, costes o metadata en reviewer `main` no constituyen por sí mismos una discrepancia de perfil. Sí existe discrepancia si cambia una garantía técnica de la sección 8, aparece un workflow permanente no autorizado, existe más de un perfil estable o no puede demostrarse que el call path vivo satisface el contrato técnico.

Ante una discrepancia técnica o duda material, **no se despacha DeepSeek** hasta resolverla. La ausencia de contexto conversacional nunca autoriza degradar a una configuración histórica no autorizada.

## 13. Autoridad y vigencia

Esta norma es obligatoria para nuevas entregas de QORE Core que entren al gate de revisión externa desde su merge en `main` y permanece vigente hasta el cierre formal de QORE Core o una modificación constitucional explícita.

No autoriza Production, real capital, ejecución real, bypass de Risk ni ninguna ampliación de autoridad operativa.