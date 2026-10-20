# VT08 CRT PURE — G-M2: 48 expedientes VISUALES PRIMERA MIRADA (neutrales al resultado)

**Checkpoint:** 15-OCT-2026 · PR #626 DRAFT · NO MERGE · NO SIZING · NO LIVE/DEMO.
**Estado:** SOFTWARE / CORPUS DE REVISIÓN LISTO, **ADJUDICACIÓN HUMANA ORIGINAL AÚN PENDIENTE**. No constituye G-M1/G-M2/G-M3/G-M4 PASS, G-M5, resultado económico ni nueva fuente original autenticada.

## 1. Problema científico auditado y reparación

El paquete reviewer-blind anterior incluía correctamente la secuencia pre-decisión, pero **también** observaciones geométricas Model #1 y los outputs cognitivos de fail-close. Aunque no contiene C3 futuro, puede inducir al revisor a aceptar o rechazar niveles conforme a la máquina, en vez de razonar independientemente conforme al autor RomeoTPT.

Solución: módulo [vt08_crt_pure_gm2_visual_firstlook.py](../../src/qore/infrastructure/trader_lab/vt08_crt_pure_gm2_visual_firstlook.py) con visualizaciones SVG de **velas H4 C1/C2 y prefijo cerrado M15**, tabla OHLC, market, timestamp UTC y hash independiente por caso. Se ocultan **parent directional bias de ingeniería, selector propuesto, hipótesis de geometría, resultado de cognitiva, valor posterior C3 y todo trading/sizing**. Ni siquiera hay una lista de niveles elegidos; los dos H4 bar extremes están disponibles solamente como **datos crudos**. Un old CRTH/CRTL válido podría ser **cualquier nivel previo**, no solo H4 C1/C2; el revisor debe explicitar la insuficiencia del contexto y solicitar historial previo cuando haga falta.

Solo se usa la función de auditoría del prefijo causal existente y datos H4/M15 que eran conocidos a la hora de la decisión. Gráficas locales SVG sin JavaScript, solicitudes web ni imágenes externas; los campos y caso_id se escapan como HTML. Cada página contiene **preguntas en blanco**, no etiquetas metodológicas ni dictámenes. **NO es una revisión visual YA realizada.**

## 2. Resultado verificado con DATA ORIGINAL

GitHub Actions [run #38706589343](https://github.com/mezas3238-hue/qore-core/actions/runs/38706589343), código commit **a263120f99cd43b5522468042af9b1f38685caad**: 
- **Quality = SUCCESS (Ruff/mypy/pytest)**, **AUDUSD = SUCCESS**, **USDJPY = SUCCESS**. Los runs anteriores **#38706453267** y **#38706530885** tuvieron errores de import order y un directorio previo al `tee`; arreglados por commits posteriores. No tratarlos como metodología fallida; tampoco ocultar los fallos.
- **AUDUSD 24 expedientes; 48 gráficos** (2/caso H4 y M15), [artifact FIRST-LOOK #11958423126](https://github.com/mezas3238-hue/qore-core/actions/runs/38706589343/artifacts/11958423126).
- **USDJPY 24 expedientes; 48 gráficos**, [artifact FIRST-LOOK #11958537855](https://github.com/mezas3238-hue/qore-core/actions/runs/38706589343/artifacts/11958537855).
- **Total: 48 casos y 96 gráficos, 0 dictámenes o niveles source-approved.**
- Ambos ZIP **descargados y abiertos de manera independiente**: SHA256SUMS completo PASS, hash de HTML coincide con manifiesto, no se detectaron indicadores mecánicos/modelos cognitivos/sesgo alcista-bajista ni campo sellado de futuro. Manifest `source_reference_authenticated=false`, `G_M2_passed=false`, `G_M5_certificate_issued=false`.
- **Vencimiento nominal de los seis artifacts actuales:** **2027-01-13T08:34:05Z**, según metadata Actions, siempre volver a comprobar antes de usarlo; el Dataset Atlas12 ORIGINAL vence antes (**2026-12-16**, issue #837).

## 3. Tres niveles de aislamiento del revisor, sin afirmar seguridad ACL

Por cada mercado hay ahora **tres ZIP distintos**, pero todos heredan permisos de lectura del repositorio y del run; **esto es separación de contenido, NO control real de acceso**.

| Paquete | AUDUSD artifact | USDJPY artifact | Quién debe abrirlo y cuándo |
|---|---:|---:|---|
| **FIRST LOOK NEUTRAL VISUAL** | **11958423126** | **11958537855** | Revisor metodológico independiente ANTES de ver respuestas de QORE |
| Reviewer-blind análisis técnico (geometría G-M1 y cognitiva G-M3) | **11958542859** | **11958433059** | Auditor técnico DESPUÉS del dictamen metodológico sellado |
| **SEALED C3 FUTURE** | **11958418187** | **11958128799** | Solo DESPUÉS de dictamen independiente firmado; no para elegir la regla |

Si no hay separación real entre personas/permisos, exigir manifestación verificable de qué se consultó y cuándo. Ningún hash por sí solo prueba que un humano no abrió otro artifact.

## 4. Protocolo humano que falta ejecutar para intentar cerrar G-M2

1. Seleccionar dos revisores metodológicos **independientes de la construcción de QORE**, con experiencia fuente CRT original. Identificar identidad verificable y constancia de no consulta a resultados posteriores; **no son reviewers ficticios ni los inventa el pipeline**.
2. Entregar **solo los FIRST LOOK** por GitHub Actions o vía custodio autorizado, con lecciones originales RomeoTPT [post old CRTH](https://t.me/s/officialRomeotpt/6615) y [base video](https://www.youtube.com/watch?v=UUq_wKQ61Wo). El post oficial describe una reacción sobre old CRTH, pero **no establece un selector inequívoco multirreferencia** en el texto verificado. No copiar reglas de terceros ni inventar un desempate.
3. Dictamen de cada case_id sin usar el futuro: modelo de tesis H4, key level *source-authenticated o desconocido*, niveles H4 C1/C2/anteriores, validez, barrido, confirmación M15, referencia elegida o NONE/UNKNOWN, contratesis, DOL, expiración, motivo EXECUTE conceptual / WAIT / ABSTAIN. Adjuntar URL primaria/minuto/fotograma o registrar **SOURCE_UNRESOLVED**, sin false PASS.
4. Comparar dos revisores independientemente y registrar diferencias y cómo se adjudican. **No premiar el consenso a ciegas si ambos usaron fuente insuficiente.**
5. Sellar actas y sus hashes **antes** de mirar los diagnósticos G-M3 o ZIP C3. Solo entonces hacer comparación del software con los humanos, descubrir divergencias y corregir cognitiva (G-M3) SIN elegir reglas por resultado.
6. Requerir mejor contexto histórico si los dos H4 no bastan: estas páginas muestran **dos H4 anteriores y prefijo M15**, no un historial multisemana exhaustivo. Una selección old CRTH fuera de ese contexto debe declararse **INSUFFICIENT_CONTEXT**, no forzar H4_C1 o H4_C2.

## 5. Qué cambió en el repo / cómo reproducir

- Fuente: `src/qore/infrastructure/trader_lab/vt08_crt_pure_gm2_visual_firstlook.py`
- Pruebas adversariales: `tests/infrastructure/trader_lab/test_vt08_crt_pure_gm2_visual_firstlook.py` — futuro prohibido, inyección HTML, duplicados, secuencia no causal, ocultamiento de ingeniería y output sin certificado.
- Workflow: `.github/workflows/vt08-crt-pure-gm2-blind-casebook.yml` — genera los FIRST-LOOK en la rama DRAFT por cada símbolo del Atlas original y publica ZIP **antes de abrir** el paquete de análisis.
- Archivos: `gm2-methodologist-firstlook.html`, `gm2-firstlook-manifest.json`, `git-sha.txt`, `SHA256SUMS.txt` y salida manifest. Abrir HTML LOCAL tras descargar el artifact, SIN revelar resultados G-M1/G-M3 o sealed.
- Nunca usar PnL/sizing/Sortino/DD para resolver qué reconoce el autor; el carril económico global es otra etapa con Gates aún OPEN.

## 6. Bloqueos reales preservados

**G-M1:** falta selector old CRTH/CRTL respaldado por Romeo original; los videos en la cola no han recibido acta con minuto/fotograma de autoridad. **G-M2:** primera mirada preparada, revisión humana fuente-original **0/48**, por eso PARTIAL. **G-M3:** 48 ABSTAIN de seguridad no demuestran acierto. **G-M4:** faltan casos positivos E2E con regla fuente verdadera. **G-M5:** no emitido. **GLOBAL PF/DD/Sharpe/Sortino/OOS:** pendiente; NO sizing en el Trader.

**Acción próxima del sucesor:** empezar el verdadero juicio metodológico independiente de los 48 FIRST LOOK, empezando por casos con información de referencia suficiente y registrando `INSUFFICIENT_CONTEXT` en los demás. No seguir creando testigos/heurísticas para llamar PASS algo que el autor no avaló.
