# QORE External Review Governance v1.0

## Propósito

Esta norma define el contrato obligatorio de revisión técnica externa para entregas de QORE Core. Su objetivo es preservar independencia de validación, evidencia reproducible, fail-closed ante incertidumbre y consumo eficiente de revisores externos sin degradar la calidad.

La infraestructura que ejecuta revisores externos permanece fuera de QORE Core. Core fija el contrato de revisión; la implementación operativa vive en un repositorio de reviewer aislado y puede evolucionar mientras conserve este contrato. La identidad y el tuple operativo del perfil estable activo, sin embargo, son gobernados exclusivamente por `qore-core/main` conforme a las secciones 8 y 11.

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

`qore-core/main`, mediante esta norma, es la fuente autoritativa del perfil DeepSeek estable activo. Debe existir exactamente un perfil estable activo y reconstruible. Un commit, merge, branch, prompt o request en `qore-deepseek-reviewer` no puede cambiar por sí solo cuál perfil está autorizado operativamente.

Perfil operativo validado al adoptar esta norma:

- profile id: `QORE-DEEPSEEK-V2.1.1-STABLE`;
- repositorio de infraestructura: `mezas3238-hue/qore-deepseek-reviewer`;
- profile manifest autoritativamente pinneado por Core: `profiles/QORE-DEEPSEEK-V2.1.1-STABLE.json`;
- blob SHA esperado del manifest: `14db06a4a8014f7af114d9832f11542c70ddb28c`;
- reviewer family: V2.1.1;
- meter: `scripts/run_review_with_meter.py`;
- entrypoint: `scripts/deepseek_reviewer_v2_1_1_entrypoint.py`;
- workflows permanentes autorizados, exactamente estos tres:
  - `.github/workflows/deepseek-auto-dispatch.yml`;
  - `.github/workflows/deepseek-connection-test.yml`;
  - `.github/workflows/deepseek-qore-review.yml`;
- modelo autoritativo: `deepseek-v4-pro`;
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
- el manifest pinneado enumera por blob SHA toda la cadena ejecutable que materializa este evidence path, además del meter y workflows; todos esos blobs forman parte del perfil y deben coincidir en vivo;
- emisión de veredicto: mismo modelo en non-thinking únicamente para extraer/formatear conclusiones soportadas por el análisis retenido cuando el high pass no emite contenido visible completo;
- no Flash substitution;
- no CoT continuation;
- no replay completo del evidence bundle en el extractor;
- extractor sin autoridad para inventar hallazgos ni fabricar PASS.

El manifest vive en la infraestructura externa sólo como descripción/fingerprint verificable. No posee autoridad para activar perfiles: su path y blob SHA esperado son fijados por esta norma en `qore-core/main`. Cambiar o reemplazar el manifest en reviewer sin actualizar Core conforme a la sección 11 produce discrepancia y bloquea dispatch.

El `main` del reviewer puede avanzar por prompts, requests, dispatches, telemetría u otros cambios que no alteren el perfil. Eso no cambia el profile id estable mientras el manifest pinneado y todos sus blobs de componentes sigan coincidiendo. Cualquier cambio semántico que altere el manifest, el meter seleccionado, el entrypoint o su cadena ejecutable, la familia, el modelo, el modo de reasoning, la política del extractor, el evidence path, el fail-closed o el conjunto de workflows permanentes constituye un cambio de perfil y debe seguir la sección 11.

Un sucesor puede existir como candidato o benchmark en la infraestructura sin quedar activo. No sustituye a `QORE-DEEPSEEK-V2.1.1-STABLE` por estar implementado, benchmarkeado, revisado por DeepSeek o mergeado en `qore-deepseek-reviewer`. La activación sólo ocurre después de completar el gate independiente de la sección 11 y mergear en `qore-core/main` una actualización explícita de esta norma que nombre el nuevo profile id y su tuple operativo.

## 9. Presupuesto y revisión de consumo

Para cada trabajo DeepSeek Expert o DeepSeek Coder se calcula y publica el consumo total del job como `prompt_tokens + completion_tokens`, agregado sobre todas sus llamadas API. `reasoning_tokens` se informa como telemetría adicional pero no se suma nuevamente al total porque ya forma parte de `completion_tokens`.

Reglas operativas de consumo:

- techo de vigilancia por trabajo: **52.000 tokens totales**;
- cada reporte DeepSeek debe incluir, como mínimo, prompt, completion, reasoning, total, número de llamadas API, límite vigente y estado respecto del límite;
- total `≤52.000` ⇒ `DENTRO DEL LÍMITE` y la cadena puede continuar normalmente si los gates técnicos también están cerrados;
- total `>52.000` ⇒ `REVISIÓN DE CONSUMO ACTIVADA`; debe identificarse qué etapa produjo la regresión y qué optimización acotada puede reducir consumo antes de considerar ese nivel como baseline estabilizado;
- superar 52.000 no invalida por sí solo un resultado técnico ya vinculado y soportado por evidencia, pero sí constituye una regresión de consumo que debe investigarse;
- objetivo normal: máximo 3 llamadas cuando se requiera planner + análisis + extractor;
- cualquier optimización debe conservar cobertura material, modelo autorizado, evidencia obligatoria y fail-closed.

El ahorro de tokens nunca justifica reducir cobertura material, cambiar silenciosamente a un modelo inferior ni relajar fail-closed.

## 10. Evidencia de referencia de adopción

Como evidencia histórica de operación del perfil V2.1.1 se conserva el cierre de DeepSeek Coder R1H de UNR-019 sobre el freeze:

- BASE `25ed21be1ba427820be78dbb8958d441e5f27f9c`;
- HEAD `b2fae639779bdf27c497929af1a545ae70a42649`;
- SYNTHETIC `db81e5268ee0abdc7cf07018d5daf7e9768d8604`;
- `plan_incomplete=false`;
- sin tool errors ni reason markers;
- `HALLAZGOS: NINGUNO / VALIDACIÓN OK`;
- 39.069 prompt tokens;
- 20.020 completion tokens;
- 20.000 reasoning tokens, incluidos dentro de completion;
- 59.089 tokens totales bajo la fórmula vigente `prompt + completion`;
- 3 llamadas API;
- límite vigente de comparación: 52.000 tokens;
- estado bajo la política vigente: `REVISIÓN DE CONSUMO ACTIVADA` por excedente histórico de 7.089 tokens;
- adjudicación IA técnica: Coder PASS.

R1H ocurrió antes de la adopción de la sección 9 y conserva valor como evidencia técnica de calidad, binding y comportamiento del perfil, pero **no es un baseline de consumo aceptable** bajo la política vigente. La revisión de consumo retrospectiva identifica el exceso en la suma agregada de 39.069 prompt + 20.020 completion dentro de un flujo de 3 llamadas. El PASS técnico no se invalida por esa regresión de consumo; cualquier recurrencia futura por encima de 52.000 debe investigarse antes de considerar ese nivel como baseline estabilizado, sin reducir modelo, cobertura, evidencia ni fail-closed.

Esta evidencia demuestra comportamiento observado; no es autoridad suficiente para auto-certificar un perfil ni un sucesor, ni evidencia de cumplimiento presupuestario vigente. La autoridad del perfil activo proviene del tuple explícito de la sección 8 publicado en `qore-core/main` después de completar la cadena de revisión de Core. Ningún PASS emitido por DeepSeek sobre su propia infraestructura puede sustituir el gate independiente de la sección 11.

La evidencia histórica justifica mantener el perfil actual por sus propiedades técnicas; no convierte esos números en una excepción para relajar la calidad ni el umbral de vigilancia.

## 11. Cambio de perfil

Una optimización futura del reviewer se acepta sólo si:

1. no reduce cobertura material;
2. conserva el mismo o mayor fail-closed;
3. conserva binding exacto y anti-duplicación;
4. conserva independencia respecto de la implementación;
5. no introduce secretos o autoridad operativa en Core;
6. demuestra consumo igual o mejor en revisiones legítimas o benchmarks no publicantes;
7. no produce una regresión de calidad conocida;
8. recibe validación independiente que no dependa exclusivamente del componente DeepSeek que está siendo sustituido o modificado;
9. su evidencia y adjudicación quedan vinculadas desde una actualización explícita de esta norma en `qore-core`;
10. esa actualización declara el nuevo profile id, profile manifest path + blob SHA esperado, meter, entrypoint, workflows permanentes, evidence path y cualquier otra parte modificada del tuple operativo.

La infraestructura DeepSeek bajo cambio puede aportar benchmarks y findings como evidencia, pero no puede aprobar por sí sola su propio sucesor. El gate independiente debe incluir, como mínimo, adjudicación técnica independiente de la evidencia y revisión manual de Claude Code sobre el delta de infraestructura/perfil relevante; cualquier finding material se corrige y vuelve a validar antes de promover el candidato.

El orden de activación es obligatorio:

1. implementar o benchmarkear el candidato sin desplazar el profile estable activo;
2. producir evidencia reproducible y completar el gate independiente;
3. abrir en `qore-core` un PR de governance que actualice explícitamente esta norma y enlace/resuma la evidencia material de validación;
4. completar para ese PR la cadena externa vigente y mergearlo de forma protegida;
5. sólo después de que `qore-core/main` publique el nuevo tuple puede ese perfil usarse como estable en dispatches ordinarios.

Hasta el paso 4 inclusive, el tuple estable anterior continúa siendo la única configuración autorizada. Si el reviewer no puede ejecutar ese tuple mientras un candidato está en evaluación, los dispatches se bloquean; no se adelanta el switch.

Ante conflicto entre ahorro y calidad, prevalece calidad.

No existe fallback permitido a una familia histórica de reviewer por iniciar un chat nuevo, perder contexto, cambiar coordinador o reiniciar una sesión. Si el perfil estable no puede reconstruirse con evidencia desde GitHub, el dispatch se bloquea hasta reconstruirlo; nunca se sustituye silenciosamente por una configuración anterior.

## 12. Persistencia entre chats, sesiones y coordinadores

El método de trabajo DeepSeek vigente es **estado persistente del proyecto**, no estado conversacional.

Su vigencia no cambia por:

- abrir un chat nuevo;
- compactar o perder contexto conversacional;
- reiniciar una sesión;
- cambiar de dispositivo;
- cambiar el coordinador técnico o agente que continúa el trabajo;
- transcurrir tiempo entre entregas.

Al inicio de cada sesión que pueda despachar DeepSeek, el coordinador debe reconstruir desde GitHub, antes de cualquier dispatch:

1. esta norma desde `qore-core/main` como fuente autoritativa;
2. el único profile id estable, manifest path + blob SHA esperado y tuple operativo explícitos de la sección 8;
3. el `main` actual de `qore-deepseek-reviewer`;
4. que el manifest exista en reviewer `main`, su blob sea exactamente el pinneado por Core, declare el mismo profile id y marque exactamente los componentes/evidence contract del perfil;
5. que cada meter/engine/workflow blob enumerado por el manifest coincida exactamente con el archivo vivo correspondiente; una diferencia es profile drift y bloquea dispatch;
6. que `scripts/run_review_with_meter.py` seleccione el entrypoint estable declarado y que la cadena ejecutable corresponda al modelo/reasoning/extractor/evidence path autorizados;
7. que existan exactamente los tres workflows permanentes autorizados declarados en la sección 8 y que el workflow de review use el meter/modelo autorizados;
8. que el evidence path vivo preserve el mandatory bundle y exactamente las herramientas `read_file`, `search_text`, `git_show`, `github_get`, con `search_text` por `git grep` y autoridad read-only acotada a qore-core; cualquier drift debe fallar cerrado;
9. el último estado de `requests/current.json` para anti-duplicación;
10. los reviews/markers existentes del PR objetivo;
11. el binding exacto del PR candidato y su CI.

El coordinador no puede inferir una configuración DeepSeek desde memoria, un prompt antiguo o un chat anterior cuando GitHub puede verificarla.

Los commits de dispatch o requests en reviewer `main` no constituyen por sí mismos una discrepancia de perfil. Sí existe discrepancia si el manifest pinneado no coincide, cualquiera de sus blobs de componentes no coincide, el call path o cualquier semántica definitoria del perfil no corresponde al tuple estable publicado por Core, aparece un workflow permanente no autorizado, o existe más de un perfil marcado como estable.

Ante cualquiera de esas discrepancias, o ante duda sobre qué perfil está activo, **no se despacha DeepSeek** hasta resolverla. La ausencia de contexto conversacional nunca autoriza degradar a una configuración histórica de mayor consumo.

El perfil estable permanece obligatorio **hasta el cierre formal de QORE Core**, salvo que antes sea sustituido por un sucesor validado bajo la sección 11. En cualquier caso, siempre existe exactamente un perfil operativo estable vigente y reconstruible desde GitHub.

## 13. Autoridad y vigencia

Esta norma es obligatoria para nuevas entregas de QORE Core que entren al gate de revisión externa desde su merge en `main` y permanece vigente hasta el cierre formal de QORE Core o una modificación constitucional explícita.

No autoriza Production, real capital, ejecución real, bypass de Risk ni ninguna ampliación de autoridad operativa.
