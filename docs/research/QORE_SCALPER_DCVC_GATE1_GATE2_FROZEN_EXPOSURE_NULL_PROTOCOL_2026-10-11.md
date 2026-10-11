# DCVC GATE 1 / GATE 2 — Falsación congelada antes de nuevas aleatorizaciones

**Fecha 2026-10-11.** Observaciones previas: Audit01 B 266 trades y PF bruto 0.8518, coste supuesto 0.025R PF 0.76975 y DD 23.0384R; 100 placebos posthoc matched-date ya vistos. Esto es investigación EXPLORATORIA con el histórico consumido, no pre-registro de un holdout virgen. **El presente contrato congela las nuevas aleatorizaciones antes de ejecutarlas.** A/B v0.1 y decisiones, entradas, stop, target, liquidación, fuente 2876 y MAX3 inmutables.

## GATE 1 (STOP antes de reparar detector)

Hipótesis nula principal: entre las mismas 2876 oportunidades fuente, seleccionar **266** sin aprovechar el régimen ni su R futuro, respetando máximo 3 por sesión/fecha y chronology, produce rendimiento igual o mejor que B con frecuencia comparable. Comparador **G1-GLOBAL-266**: para cada semilla 20261011+iteración, permutar uniformemente los 2876 IDs fuente y tomar los primeros 266 válidos bajo capacidad MAX3; no utilizar resultados para selección, NO igualar conteos diarios observados de B. Esta permutación offline iguala solo el **N total conocido** de B; por tanto no es política prospectiva, ni cambia A/B ni es validación OOS. Usar **2000 aleatorizaciones**.

**Sensibilidades**: (i) **A-FIRST3-266**: elegir 266 de las 2020 originales A, para aislar selección A-only de efecto de relleno MAX3 (2000 semillas independientes); (ii) **B-SYMBOL-SESSION-MATCHED**: seleccionar 266 con los **márgenes de símbolo/sesión de B**, respetando MAX3; condiciona en márgenes **conocidos posthoc**, etiqueta EXPLORATORIO Y NO PRINCIPAL (1000 semillas), con reporte de cualquier imposibilidad/ sesgo por priorización. (iii) mantener antiguo placebo por sesión/día como diagnóstico, NO comparador principal.

Para cada permutación calcular **PF, esperanza por trade y DD en R** por cronología de salida, tanto bruto como coste supuesto constante 0.025R. Métrica primaria: **esperanza neta asumida por operación** de B vs G1-GLOBAL-266; secundarias PF neto supuesto y DD neto R. P empíricos unilaterales con corrección +1 en colas; reportar también percentiles 2.5/50/97.5 y **corrección Holm-Bonferroni** a tres pruebas. No tratar significancia de estos P como confirmatoria. Las muestras independientes son jornadas/episodios, no 266 trades iid; los placebos por permutación de IDs NO sustituyen bootstrap por día ya ejecutado.

**Comparador de exposición**: A escalado a B/A por cantidad (r factor 266/2020) se reporta como heurística; el bootstrap 500 bloques × 5 días incluye 0 en diferencial de DD exposure-matched. Ningún orden de entrada/stop/lifecycle se altera.

**Potencia y MDE con escenarios congelados**: 1000 simulaciones de selección aleatoria válida desde 2876 y escenarios de desplazamiento hipotético +0.05R, +0.10R, +0.20R, +0.30R por trade, sobre bruto y luego coste 0.025R. Usar umbral percentil 95% de la distribución G1-GLOBAL-266 de esperanza como rechazo unilateral, estimar potencia por escenario. Buscar tamaño mínimo que alcance 80% potencia mediante esos cuatro escalones; si no alcanza, MDE reportar >0.30R. NO son efectos reales ni una estimación de rentabilidad. No tunear el DCVC con estos escenarios.

**STOP**: B sólo promovible con esperanza neta positiva, PF neto >1, frecuencia y retención útiles, robustez physical costs y verdadera evaluación OOS, no solo con p favorable. Si cualquiera falla, v0.1 queda NO_PROMOVIBLE; si poder insuficiente para descartar mejora económicamente interesante, edge global queda INCONCLUSIVE_UNDERPOWERED, nunca EDGE_REFUTED universal.

## GATE 2 — anatomía SIN NUEVA ADMISIÓN

Releer únicamente la decisión original DCVC V01 (mismo run #38107014488, no reejecutar ni variar fórmula), ledger fuente congelado y resultados económicos **ex-post separados**. Validar 2876 IDs, 2020 A, 266 B, 184 UNKNOWN y 181 B-UNKNOWN. Contabilizar motivo efectivo exclusivo `COLD_START_PASS`, `UNKNOWN_INFORMATIONAL_PASS`, `UNDERPOWERED_INFORMATIONAL_PASS`, `FROZEN_POSTERIOR_EXPECTANCY` y causas `MAX3_CAPACITY`. Separar `admitted_pre_capacity` de `selected`: MAX3 puede impedir un pase y un `FROZEN_POSTERIOR_EXPECTANCY` también puede rechazar por expectativa negativa. Conservar cross-tab motivo×régimen×símbolo×mes; winners R históricos en salida ex-post nunca en features/decisions. `A∩B`, `A\\B`, `B\\A` y A-only veto diagnósticos, nunca afirmar equivalencia de la trayectoria de aprendizaje al usar A-only.

No cruzar_gate2 con future outcomes al decidir; cualquier estimador futuro tiene solo validez descriptiva.

## Gate 3 / 4 / 5

Gate3 UNKNOWN causa y predicción condicionada requiere control confusores por símbolo, franja horaria/semana y fuente M1; rama aparte, **suspendido hasta Gate1**. Gate4 BID/ASK real falta, stress fijo es hipotético. Gate5 Master Frame real bloqueado: no proxy de cognitiva. Mantener TTrades M30→M3 como modalidad independiente del H1/M15/M1 V49. Cero certificación, VPS, MT5, live o merge.

### Fuentes de la revisión previa
Audit01: GH Actions run `38107014488`, SHA `9d1f073960d4a422a40f8c982ec312f115f95af7`, artefacto `11690128444`. Bootstrap: run `38107458602`. Instrucción del auditor: comentario PR #767 `6104960779`.
