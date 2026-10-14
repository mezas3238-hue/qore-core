# QORE CORE — CFTC EXTREME Z2 — HANDOFF MAESTRO Y CIERRE OPERATIVO

**Checkpoint local:** 13-oct-2026; GitHub Actions 14-oct-2026 UTC.
**Repositorio soberano:** `mezas3238-hue/qore-core` · **PR:** [#921](https://github.com/mezas3238-hue/qore-core/pull/921), OPEN/DRAFT.
**Rama:** `research/qore-cftc-extreme-z2-contrarian-final-exam-20261013`.
**PR fuente madre:** [#920](https://github.com/mezas3238-hue/qore-core/pull/920); heredadas #919 ← #918 ← #916.
**SIN MERGE, SIN LIVE/DEMO, SIN COMPRA DE DATOS, SIN USO DEL HOLDOUT, SIN SIZING POR TRADER.**

## 1. Por qué se abrió este ÚNICO nuevo examen

Auditoría de la hipótesis anterior H-COT-1: `(MM_Long−MM_Short)/OI` cambio a cuatro semanas ⇒ continuación alcista. Los ensayos WTI/NG terminaron `NO_SUPPORT` en [run #38493719365](https://github.com/mezas3238-hue/qore-core/actions/runs/38493719365). NO prueban la conjetura distinta **posicionamiento extremo de especuladores ⇒ reversión**. El propietario solicitó exactamente un examen de esta versión contraria **sin** recuperar precios de los cuatro instrumentos restantes ni ajustar después del resultado.

La literatura no garantiza reversión universal: [Boos & Grob, Tracking speculative trading (2023)](https://www.sciencedirect.com/science/article/pii/S1386418122000635) muestran que el posicionamiento de Managed Money sigue tendencias; los productores pueden actuar de modo contrario. La CFTC publica disaggregated futures-only semanal, generalmente **viernes 15:30 ET con posiciones del martes previo** ([CFTC Release Schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm)); correcciones históricas/feriados impiden tomar los report dates por instantáneas de publicación.

## 2. Preregistro de H-COT-2 congelado *antes del primer resultado nuevo*

**Commit científico:** `1cca3399514125ba11ae446a059e09382c605d40`.
Documento: [QORE_CFTC_EXTREME_POSITION_Z2_CONTRARIAN_SINGLE_FINAL_PREREG_2026-10-13.md](https://github.com/mezas3238-hue/qore-core/blob/research/qore-cftc-extreme-z2-contrarian-final-exam-20261013/docs/research/QORE_CFTC_EXTREME_POSITION_Z2_CONTRARIAN_SINGLE_FINAL_PREREG_2026-10-13.md).

Todos los parámetros cerrados:
- Solo WTI y NG, códigos CFTC `067651` y `023651`, futures-only, series semanales 2012–21 SHA fijados; EIA F1 congelado por SHA sin datos 2022+.
- `P=(ManagedMoneyLong−ManagedMoneyShort)/OpenInterest`; z de **104 semanas anteriores** (excluye semana actual de media/stdev).
- Solo primer **cruce** z≥+2 ⇒ signo futuro de referencia negativo; z≤−2 ⇒ signo futuro positivo. No registrar cada semana extrema consecutiva.
- Espera mínima de **21 días naturales desde fecha as-of CFTC** hasta primer precio EIA; salida primer precio EIA al menos **42 días naturales** después de entrada. Ni replay de retornos, ni precios de contratos CME nativos.
- Cooldown **8 reportes**, sin solapamiento de horizontes del mismo mercado. Selección cronológica bloquea el evento antes de inspeccionar el signo de su resultado. Blackouts previamente definidos 2013 Sep–Nov y 2018 Dec–2019 Apr.
- DEV desde 2014-01-01 a 2018-12-31; DIAG 2019-01-01 a 2021-12-31; fecha CFTC + entrada + salida han de quedar en el mismo intervalo. Reserva desde 2022 intacta.
- Un contraste exacto binomial unilateral por mercado/ventana `H: Pr(reversión)=más del 50%`, familia WTI/NG Bonferroni alfa individual ≤ **0.025**, exactitud ≥ **65%**, mínimo **8 eventos independientes por raíz y ventana** con ≥2 eventos extremos de cada signo. No sustituir el mínimo por semanas de fuente, porque las señales extremas son escasas/autocorrelacionadas.
- Si algún estrato carece de episodios mínimos, `CLOSED_INCONCLUSIVE_LOW_POWER` y pausa/cierre **operativo**, no NO_EDGE general; si las cuatro celdas poseen muestra pero hay algún no-apoyo, `NO_SUPPORT_FINAL_CFTC_FAMILY_FOR_QORE`; si las cuatro pasan `PRELIMINARY_REFERENCE_ASSOCIATION_NOT_TRADABLE` sin promoción.

**Crítico:** DEV/DIAG EIA ya se usaron con H-COT-1 y F1/F2 anterior. Este es un nuevo preregistro sobre muestras **diagnósticas vistas previamente por QORE**, no una certificación con OOS independiente. El hash de Git y ancestry no prueban ceguera humana ni timestamp histórico CFTC first-published-at.

## 3. Ejecución efectiva, no simulación de resultados

**[GitHub Actions #38495515717](https://github.com/mezas3238-hue/qore-core/actions/runs/38495515717)**: **SUCCESS**, código HEAD probado `3f323af411224fa8d3c6c8f2fe511154ba29f7d9`. Confirmación real de `git merge-base --is-ancestor` del commit prereg + igualdad del Git blob. **9/9 pruebas adversariales, Ruff PASS**, ejecución real del runner CFTC/EIA fuente SHA fijada, sin compra y sin OOS reservado.

**Artifact:** [#11862474349](https://github.com/mezas3238-hue/qore-core/actions/runs/38495515717/artifacts/11862474349) (ZIP digest `sha256:bbee0001a0f0ef1842198739345236459af42879b313fe321d13da49fa7d0e21`; retención 90 días).
**Receipt científico lógico SHA256:** `e5d417db9b6d89252aa880cadd916e877d82a99f87b53518cd4e2cef83f3447d`.

| Root | Período | Episodios no superpuestos | z≥+2 | z≤−2 | Reversiones correctas (NO inferir accuracy) | Adjudicación |
|---|---|---:|---:|---:|---:|---|
| WTI | DEV 2014–18 | **7** | 4 | 3 | 2 | INCONCLUSIVE_TOO_FEW_EXTREMES |
| WTI | DIAG 2019–21 | **1** | 1 | 0 | 0 | INCONCLUSIVE_TOO_FEW_EXTREMES |
| NG | DEV 2014–18 | **5** | 2 | 3 | 4 | INCONCLUSIVE_TOO_FEW_EXTREMES |
| NG | DIAG 2019–21 | **3** | 0 | 3 | 0 | INCONCLUSIVE_TOO_FEW_EXTREMES |

Detalles de selección (ambos instrumentos 522 reportes fuente):
- WTI: **11** candidatos de primer cruce, 1 blackout, 2 en cooldown, 0 sin precio o ventana, **8** episodios puntuables.
- NG: **11** cruces, 0 blackouts, 2 cooldown, 1 sin precio o ventana, **8** puntuables.
- Ningún empate de precio.
- Los p-values y exactitud se informan **null**, como fijado: faltaron n≥8 y dos eventos por signo en cada ventana. No cambiar el p-threshold, incluir semanas consecutivas ni recortar lag para aumentar N.

**VEREDICTO: `CLOSED_INCONCLUSIVE_LOW_POWER`.**
**Acción QORE: `STOP_THIS_FAMILY_WITHOUT_UNIVERSAL_NO_EDGE_CLAIM`.**

No extrapolar a «CFTC no tiene edge», tampoco proclamar que los 4 aciertos NG DEV entre 5 indican éxito (muestra insuficiente y 0/3 NG DIAG). Los números no justifican PF/DD/Sharpe/PnL; no son órdenes con precios negociables y tampoco demuestran ventaja neta.

## 4. Patrimonio de datos que se conserva

**3.132 market-weeks** oficiales y verificados de CFTC de 6 raíces sobre 2012–2021 permanecen como **fuente recuperable** (10 URLs CFTC oficiales y digests) en la investigación [#920](https://github.com/mezas3238-hue/qore-core/pull/920), fuente validada [Actions #38493219775](https://github.com/mezas3238-hue/qore-core/actions/runs/38493219775). No se desecha el conocimiento ni el contrato de origen.

**Precisión de custodia:** los diez archivos ZIP de la CFTC se re-descargaron directamente desde el emisor durante los replays, no se versionaron los ZIP enteros en este repositorio; el artifact GitHub contiene **recibo**, no todos los datos crudos. Conservar los SHA/histórico de autenticación; los artifacts tienen retención temporal y una revisión posterior debe validar acceso futuro. «Activo real» aquí significa fuentes públicas verificadas y recuperables, no repositorio inmutable de todos los bytes.

**No resuelto:** mercado CME contract-native por vencimiento dos contratos/raíz, cotizaciones bid/ask, costes de compra/venta, derecho de uso comprobado, first-published-at antiguo de cada reporte, serie EIA F1 realmente ejecutable. No hay edge certificado.

## 5. Decisión estratégica y prohibiciones de continuación

**CERRAR / PAUSAR familia de hipótesis CFTC de QORE con los recursos actuales**, por escasez efectiva de episodios y ausencia de certificado económico. No extender a los cuatro instrumentos GC/HG/ZC/ZS; no probar z=1.5, z=2.5 ni ventanas 4/8wk retrospectivas; no comercial hedgers combinados ni invertir señales al ver los fallos. El requerimiento del propietario «un examen y nada de otra ronda» se cumple.

La familia teórica no queda refutada en general. Retomar únicamente por **nueva orden expresa** con cambio MATERIAL de información (p. ej., un histórico point-in-time más largo y fuente ejecutable auténtica) y prereg independiente desde cero, sin convertir este resultado no concluyente en soporte.

Próxima prioridad QORE, si se reasigna la misión: otro universo ya con datos reales ejecutables y nuevos mecanismos causales, no otra cadena de cinco gates sobre CFTC. Mantener todas las reservas selladas, no comprar datos ni habilitar traders.

**Archivos implementación:** `.github/scripts/qore_cftc_extreme_z2_contrarian_final_exam_v1.py`, `tests/infrastructure/trader_lab/test_qore_cftc_extreme_z2_contrarian_final_exam_v1.py`, workflow `.github/workflows/qore-cftc-z2-contrarian-final-exam.yml`; documento previo prereg arriba. Este handoff se publicó **después** de la CI SUCCESS, sin afectar las reglas de estudio ejecutadas.

**Dictamen al propietario:** el examen contrario correcto metodológicamente se efectuó una sola vez. Resultado no concluyente por escasez de extremos; cerrar CFTC como línea operativa, sin afirmar que el mercado carece de edge ni que QORE puede operarlo.
