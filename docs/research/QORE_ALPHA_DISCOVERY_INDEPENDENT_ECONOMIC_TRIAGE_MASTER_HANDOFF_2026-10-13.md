# QORE CORE — AUDITORÍA INDEPENDIENTE DEL DESCUBRIMIENTO DE EDGE

## Dictamen ejecutivo — dejar de sumar rondas sin hipótesis ejecutable

**Fecha propietario:** 13-Oct-2026, Paraguay · ejecución GitHub 14-Oct-2026 UTC.
**Repositorio soberano:** `mezas3238-hue/qore-core`.
**PR NUEVA:** [#924](https://github.com/mezas3238-hue/qore-core/pull/924), OPEN/DRAFT, NO MERGE.
**Rama:** `research/qore-alpha-discovery-economic-audit-20261013`.
**Marco:** la orden de continuar se interpreta como auditar **el método de descubrimiento**, después de la H-TOM-1, sin introducir un cuarto experimento automáticamente. **0 nuevo PnL**, 0 precios, ninguna lectura de holdout, 0 gasto, SIN LIVE/DEMO/capital.

## 1. Qué se verificó de manera independiente y efectivamente ejecutada

[**Actions #38504196569**](https://github.com/mezas3238-hue/qore-core/actions/runs/38504196569): **SUCCESS**, 8/8 tests adversariales, Ruff PASS. GitHub Actions descargó **solo los artefactos de resultados** ya publicados —NO OHLC, BID/ASK, precios forward ni eventos nuevos— y verificó los SHA firmados y recibos en una rutina separada del ejecutor original.

| Evidencia auténtica | GitHub Actions origen | Auditoría |
|---|---|---|
| H-TOM-1 original, 3 índices, control mensual, 70 meses DEV / 23 DIAG | [#38502188181](https://github.com/mezas3238-hue/qore-core/actions/runs/38502188181) | Archivo JSON resultado y `SHA256SUMS.txt`, `exact-code-head-sha.txt` verificado `be77998d185165ff0d2cce320d015981c8a8c631` y SHA256 lógico |
| E3 Native, 33 mercados × 7 métodos originales | [#38262585848](https://github.com/mezas3238-hue/qore-core/actions/runs/38262585848) | Archivo JSON, `OUTPUT_SHA256SUMS.txt`, código original `845a7e351c1641025a6131271ae3ada37ebf37f1`, 7 métodos, 231 celdas y 0/3 traders |
| CFTC H-COT-2 extremos +2/−2 WTI/NG | [#38495515717](https://github.com/mezas3238-hue/qore-core/actions/runs/38495515717) | SHA256 lógico, prereg `1cca3399514125ba11ae446a059e09382c605d40`, fechas y `null` de p-valores por muestra insuficiente |

Artefacto auditoría: [#11866802561](https://github.com/mezas3238-hue/qore-core/actions/runs/38504196569/artifacts/11866802561), digest ZIP `sha256:d60bdcbd24bc00f8a5c98be22d38f08c777763fe86f3b44c2a6873894fa157eb`.
Recibo lógico `4d5287d15a8f09b5c6f7d8612fea38aaf6fd201b3f3f03ddca2773fe25391ac0`.
Código auditable: `.github/scripts/qore_alpha_discovery_three_exams_evidence_review_v1.py`; pruebas `tests/infrastructure/trader_lab/test_qore_alpha_discovery_three_exams_evidence_review_v1.py`; workflow `.github/workflows/qore-alpha-discovery-economic-evidence-review.yml`.

## 2. Tres fracasos diferentes que NO se deben mezclar

### A — H-TOM-1: valor absoluto bruto negativo en diagnóstico

La compra teórica de transición de mes en índices cash CFD QORE Native se comparó con una ventana emparejada de mitad de mes. **Los tres mercados mostraron media BRUTA negativa en DIAG**:

| Índice | TOM bruto DEV (bps) | TOM bruto DIAG (bps) | Exceso frente a control DIAG (bps) | Límite inferior bootstrap del exceso DIAG |
|---|---:|---:|---:|---:|
| SP500 PRIMARY | +50.9856 | **−3.0884** | +11.9820 | −57.5671 |
| US30 | +54.3581 | **−11.9489** | −12.3713 | −71.7155 |
| NAS100 | +50.7333 | **−0.2184** | +14.6498 | −93.7814 |

**Inferencia matemática y económica acotada:** si los costes totales de negociación/financiación de una posición tienen promedio **no negativo**, `gross_mean - cost_mean <= gross_mean`. Por lo tanto, ese método **long-only exacto** NO puede producir esperanza neta media positiva en ninguno de los tres mercados durante DIAG bajo dicha condición. El exceso positivo NAS100 frente al control NO salva un bruto absoluto −0.2184 bps; no hay certificado de un trader NAS100 ni se elige ganador retrospectivo. Si hubiesen créditos netos de financiación efectivamente superiores al coste, sería un **producto/hipótesis económica diferente**, hoy no acreditada; no se inventa un crédito.

**Efecto importante:** la ausencia de BID/ASK NO es excusa para rescatar H-TOM-1: los spreads y comisiones positivos solo empeoran los brutos ya negativos. El requisito estadístico prereg de SP500 además no pasó. Cierre `CLOSED_UNPROFITABLE_AVERAGE_GROSS_IN_DIAGNOSTIC` para ESTA regla exacta, sin afirmar que todo índice CFD carezca de ventaja.

### B — E3 Native 7×33: señales gross incapaces de mantener robustez temporal y estadística

La matriz del E1/E2/E3 ya consumió 231 celdas y 33×7 hipótesis de diseño, con bootstrap por semanas y siete métodos. El revisor verificó **0/7 métodos** que tengan *gross y exceso contra comparador ambos positivos en ambos períodos y las sensibilidades de bootstrap a 1/2/4 semanas*, y **0/7 BH10% positivos en ambas épocas**. No fue solo un filtro Holm «demasiado conservador»: el requisito de replicación y magnitud económica básica tampoco se satisfizo.

`CLOSED_GROSS_NOT_ROBUST_AND_REPLICATED` para la familia examinada; *no* afirmar que los 24 millones de barras se tradujeron en millones de oportunidades independientes y *no* proclamar que cualquier regla imaginable sobre los 33 mercados está refutada.

### C — H-COT-2: no hay potencia estadística efectiva, NO prueba del signo

El examen de Managed Money extremos bajo H-COT-2 tuvo estos episodios de resultado elegibles:

| Mercado | DEV | DIAG | Mínimo prereg por ventana |
|---|---:|---:|---:|
| WTI | 7 | 1 | 8, con ambos signos presentes |
| NG | 5 | 3 | 8, con ambos signos presentes |

Los p-valores se mantuvieron **null por prereg**. No hay razón para afirmar que el retorno es cero ni para extender la misma búsqueda a otros mercados: el programa operativo CFTC continúa pausado. Hay un activo de fuente de 3.132 market-weeks seis raíces, pero 45 cruces descriptivos tras cooldown en #922 NO generan 45 trades económicos validados.

## 3. Regla de admisión de toda investigación económica nueva

**NO se autoriza automáticamente otra ronda de `método nuevo→NO_SUPPORT→censo→otra variante`.** Requisitos exigibles ANTES de consultar outcomes:

1. **Mecanismo pagador independiente:** identificar actor obligado a asumir o transferir riesgo; causa exacta de presión/prima; cuándo la información se vuelve pública; y por qué sigue existiendo compensación tras arbitraje. Rechazar nuevas etiquetas de barrido/persistencia con esencia de las 7 familias E1, el fixing RESET, carry o variantes H-TOM-1 sin fuente causal nueva.
2. **Entrada/salida y fuente realmente ejecutable:** escoger de antemano el símbolo, broker, unidad de contrato, BID de venta y ASK de compra en decisiones causalmente verificables. Si únicamente hay OHLC y snapshots BIDASK de 3×10m, clasificar nueva prueba como **GROSS_EXPLORATORY**. Jamás se ofrece PF/DD/Sharpe `NET` o certificado de trader sin comisión, swap, deslizamiento, broker equivalence y contexto PIT. Impedir empates BID=ASK tratados como precio gratuito.
3. **Beneficio económico requerido antes de mirar resultado:** definir `MDE = costo redondo verificado + margen de seguridad`, comparar esperanza ABSOLUTA de estrategia contra cero y contra baseline; no aprobar solo por mejora relativa respecto a una baseline aún peor. Comprobar que el evento ocurre con frecuencia suficiente en cada split **antes de correr precios futuros**. No disminuir p, umbrales ni riesgos tras ver el diagnóstico.
4. **Capacidad independiente y muestra fresca:** tener estimación previa de eventos NO solapados, riesgo de clusters intrames/mercados y periodo no inspeccionado. Native 2016–2024 DEV/DIAG ya vistos; reserva 2024-09-17+ continúa sellada. Un ensayo exploratorio positivo en periodos vistos no basta para certificar.
5. **Cierre una sola vez:** prereg Git antes del código de outcomes, ejecución reproducible fuente-hash, reporte de n e incertidumbre, y `NO_SUPPORT` vs `INCONCLUSIVE_LOW_POWER` separados. Si no hay fuente ejecutable disponible bajo USD0, STOP nuevas propuestas de «trader rentable»; sí se puede hacer investigación descriptiva a petición expresa pero no anunciar un edge.

## 4. Decisión concreta para los recursos que ya tenemos

**Decisión:** `FREEZE_SPONTANEOUS_HYPOTHESIS_ROUNDS`. Reutilizar infraestructura y datos, pero no introducir automáticamente la estrategia número veinte. Evaluar primero si una hipótesis económica identificable puede liquidarse a un coste realista y con muestra verdaderamente independiente. La carencia de monetización certificable es **un problema de evidencia de costo/fill/hypothesis**, no de falta de potencia de cómputo.

**Estado de activos real:**
- QORE Native 33 mercados / 24.377.420 M5, fuente auténtica verificada; sin 33×10y de BID/ASK native continuo; 0/3 nativos nuevos certificados.
- cTrader histórico BID/ASK **en ventanas cortas** (ej. 127.928 ticks en tres ventanas de 10min por instrumento + capturas de QA); múltiples spread-zero cuarentenados; original 12 aún **0/12 EXACT_CONTRACT económico histórico**, comisiones RT/swap no verificadas.
- CFTC 6×10 años agregado, no CME OHLCV contract-native. EIA referencia no ejecución por vencimiento. Futuro pagado actualmente USD0.
- Separados y protegidos CIBO/Shared/VT31/VT08/Scalper y Traders históricos: esta revisión **no los audita ni modifica**, y no debe usarse para cerrar otros programas con resultados propios.

**Trabajo racional disponible sin otro ensayo PnL:** solicitar únicamente evidencia de tarifas y contratos de cTrader DEMO de una cohorte definida, preservando derechos de fuente y hashes, registrar coste/financiación real, y evaluar si un mecanismo económico con fuente accesible podría pasar el margen neto. Si no existe acceso/costo histórico admisible, la certificación NET está BLOQUEADA, no se suplanta mediante estimaciones optimistas. No se abre 2024-09-17+.

**No es una decisión de abandonar QORE**, pero sí de dejar de confundir progreso de CI con descubrimiento de ventaja. Se puede construir software sin beneficio; no se puede certificar rentabilidad sin retornos reales después de fricciones y evidencia independiente.

## 5. Handoff específico al siguiente arquitecto

- Retomar desde [PR #924](https://github.com/mezas3238-hue/qore-core/pull/924), código/8 pruebas y artifact #11866802561, **no recalcular H-TOM ni reoptimizar CFTC**. Verificar que el hash de los 3 originales sigue intacto antes de usar conclusiones.
- Si owner insiste en **nueva investigación económica**, presentar UNA tesis causal de mecanismo ajeno a modelos cerrados y un contrato `costs_and_power_admissibility` basado en datos realmente disponibles, antes de cualquier nuevo outcome. No atribuir a «datos históricos disponibles» más profundidad de quote y ejecución de la acreditada.
- Antes de certificar un trader, resolver costo y punto de entrada/salida BIDASK, comisiones/swaps/financiación, contract equivalence e identidad de cuenta/horario, PnL de tamaño real gobernado por Risk y CIBO cuando corresponda; hasta tanto `CERTIFIED_0`, `HISTORICAL_NET_BLOCKED`.
- Si ya no existen nuevas hipótesis fundamentadas, es legítimo cerrar la búsqueda algorítmica de alpha en esta cohorte sin venderlo como fracaso universal de la IA o del trading.

**Artefactos pueden expirar: conservar links+digest no equivale a copia permanente. Ninguna modificación de producción ni merges.**
