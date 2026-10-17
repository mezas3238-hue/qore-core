# VT08 — Contrato de alcance del Owner: QORE-alpha EXCLUIDO

**Fecha:** 2026-10-15 · **Autoridad:** corrección explícita del Owner durante la certificación de VT08.  
**Ámbito:** metodología VT08, cognitiva VT08, Gate económico, investigaciones R1–R15, arquitectos A y B y cualquier siguiente handoff.  
**Prioridad:** esta regla de alcance prevalece sobre propuestas experimentales de cualquier arquitecto, informe de terceros o anteriores comentarios que supongan otra vía de VT08.

## Decisión obligatoria

**QORE-alpha ya fue excluido del programa y NO puede mezclarse con VT08 actual.** No habilitar QORE-alpha como alternativa, subtipo, rama derivada, vía de rescate, grupo de comparación, estrategia paralela ni nueva versión de VT08. No trasladar desde esa estrategia excluida su metodología, reglas, filtros, setups, señales, señales de origen desconocido, cognitiva, optimizaciones ni estadísticas a la certificación de VT08.

**Única identidad de investigación y certificación:** `VT08`, metodología TTrades legítima contrastada con las fuentes originales y cognitiva VT08 evaluada con procedencia causal auténtica. Tener infraestructura compartida bajo el repositorio denominado QORE CORE no implica compartir, importar o autorizar **QORE-alpha**. Los instrumentos `Trader Lab`, `QORE Research`, CI o runners pueden procesar pruebas de VT08 si los datasets, reglas, receipts y manifest permanecen inequívocamente **VT08-only**; ningún alpha-model constituye una dependencia metodológica permitida.

### Gobierno de reglas incompletas

Si TTrades no especifica una elección entre Protected Swings, POI, stop/buffer o targets:
- `D_PENDING_SOURCE_AUTHORITY`, `WAIT`, `SOURCE_COMPLETE=false`, `COGNITIVE_ADMISSION=false`, sin fills ni Gates económicos hasta fuente/adjudicación auténtica.
- No suplir huecos mediante QORE-alpha ni reglas C/ajustes de QORE-alpha presentados como autor TTrades.
- No seleccionar la regla por PF/DD/Sharpe/Sortino, no usar sizing para certificar, no tocar el holdout 7Y sellado, no ordenar en VPS/LIVE/DEMO y no hacer merge sin aprobación.
- Las 2.657 geometrías M30→M3 y los recibos R9–R15 son investigación **source-only de VT08** y no pueden reclasificarse en otro programa.

### Rechazo inmediato (fail-closed)

Cualquier CandidateEvent, manifest, workflow o handoff de certificación de VT08 con `methodology_program`, `variant`, `signal_origin`, `cognitive_origin`, `strategy_id` o `lineage` referente a `QORE-alpha`, `QORE_ALPHA`, `VT08-QORE-ALPHA`, `alpha fork` o a un **modelo/feature de metodología alpha** debe rechazarse por contaminación de alcance. Un resultado de CI de geometría no es autorización metodológica o cognitiva.

### Rectificación histórica documentada

La sección antigua del informe [B R15](VT08_B_R15_DEEPSEEK_V2_FIDELIDAD_AUTOR_EQ_POI_CORRECCIONES_SOURCE_2026-10-15.md) que proponía `VT08-QORE-ALPHA` como segunda vía fue **retirada expresamente** por mandato del Owner. Los documentos/issue anteriores que sugieran ese track han quedado superados. No existe una opción alpha habilitada pendiente de confirmación. **Los arquitectos A y B deben continuar exclusivamente el VT08 actual y su certificación por metodología+cognitiva.**

**Estado de certificación a este corte:** `VT08_NO_CERTIFICADO`, `SOURCE_COMPLETE=0`, `COGNITIVE_REAL_ADMISSIONS=0`, `BROKER_FILLS=0`, `PF/DD/SHARPE/SORTINO=NOT_EVALUABLE`. La exclusión QORE-alpha es una restricción de programa, no una prueba de calidad o rentabilidad.
