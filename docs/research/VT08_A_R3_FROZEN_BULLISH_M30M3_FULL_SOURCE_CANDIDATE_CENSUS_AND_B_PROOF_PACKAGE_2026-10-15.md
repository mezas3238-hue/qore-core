# VT08 Arquitecto A — R3: censo integral de familia congelada, no PnL, con recibos para validación B

**Fecha:** 2026-10-15 · **GitHub:** `mezas3238-hue/qore-core` · **PR:** #765 DRAFT · **Asuntos:** A #762, B #763 · **Estado:** `PRE_AUTHOR_SOURCE_ADJUDICATION`, **NO CERTIFICADO**.

## 1. Qué se ejecutó verdaderamente

Se ha ejecutado un censo de la única familia fuente ya prerregistrada por A el 11-Oct: **M30 C2 reversal BULLISH → CISD/PS M3 → propuesta posicional C3.open**. No alterar short/limit/retest/C4, mercados ni escoger resultados ganadores. [Fuente autor M30→M3 Example 1](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/); [Positional Entries](https://ttrades.com/positional-entries-enter-before-the-expansion/). Conservar documento congelado [VT08_A_FINAL_ONE_FAMILY_AUTHOR_FIDELITY_FROZEN_TRIAL_PREREG_2026-10-11.md](VT08_A_FINAL_ONE_FAMILY_AUTHOR_FIDELITY_FROZEN_TRIAL_PREREG_2026-10-11.md). El ensayo #787 anterior fue CLOSED/SUPERSEDED: esto no lo reabre ni ensaya nuevamente su PnL.

**Acciones censo original:** [#38714341383](https://github.com/mezas3238-hue/qore-core/actions/runs/38714341383) **5/5 SUCCESS; 10 unit tests por job**. [R2 ampliada y snapshot C1/3-H1 fuente original #38715082259](https://github.com/mezas3238-hue/qore-core/actions/runs/38715082259) **5/5 SUCCESS, 12 unit tests+Ruff por job**. [Última comprobación de H1 por serie física #38715342991](https://github.com/mezas3238-hue/qore-core/actions/runs/38715342991) **5/5 SUCCESS**. Todos estos runs utilizan archivos M3 nativos y M15 1095d existentes, no los datos 7Y sellados.

**Identidad temporal sin lookahead:** para cada M30 C2.open dentro de las ventanas NY 01:00–13:00, saltos de 30 minutos, obtener su C1 anterior cerrado y diez M3 + dos M15 de C2 cerrados a `C3.open = C2.open+30min`; ambos agregados M30 deben coincidir. Confirmar primero C2 low sweep de C1.low, no barrer también C1.high, cierre bullish dentro del C1 rango, y luego evaluar `protected_swings_in_candle2` **sólo como PS geométrico QORE-C**, nunca PS author. Todas las ausencias y negativos se clasifican antes de buscar el siguiente candidato. No existe selección por RR/PnL.

## 2. Resultado completo de 93.230 C2 source windows

| Categoría exclusiva, primer fallo | EURJPY | USDCHF | NZDUSD | CADJPY | USDCAD | Total |
|---|---:|---:|---:|---:|---:|---:|
| C1/C2 M3/M15 incompleto | 15 | 15 | 22 | 14 | 17 | **83** |
| M3/M15 agregados M30 discordantes | 0 | 0 | 0 | 0 | 0 | **0** |
| No cumple single-low-sweep C2 con cierre bullish | 17043 | 17112 | 17055 | 17072 | 17030 | **85312** |
| Cumple C2, no hay PS/CISD shape M3 | 950 | 917 | 922 | 939 | 974 | **4702** |
| Hay múltiples PS/CISD shapes M3 (D) | 100 | 84 | 97 | 105 | 90 | **476** |
| Único PS/CISD shape M3, fuente autora POR ADJUDICAR | 538 | 518 | 550 | 516 | 535 | **2657** |
| **Todas las C2 examinadas** | **18646** | **18646** | **18646** | **18646** | **18646** | **93230** |

La ventana de 93.230 C2 no equivale al censo previo de 11.650 anchors: este último tomaba **solo anclas exactas 01/05/09**, mientras esta familia usa *todas las aperturas M30 de las tres sesiones Owner*; los universos están definidos de forma diferente. Nunca sumar ambos como evidencia independiente. Los 2.657 shapes **NO** son author setups, trades, fills ni señal confirmada. El límite Owner de máximo una entrada por mercado/día NY deja un **techo geométrico de 1.987 días-mercado**: EURJPY 399, USDCHF 390, NZDUSD 412, CADJPY 395 y USDCAD 391. No es una predicción de densidad de la metodología validada.

## 3. Custodia íntegra pre-C2 para auditor B

El último código no entrega solamente los primeros 8 ejemplos positivos. **Publica TODOS los 2.657 candidatos de forma exhaustiva** como receipts con SHA de los archivos originales, `source_bar_id`, `opened_at`, `closed_at`, `available_at`, OHLC de cada barra, cutoffs, y semántica `OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE`. Para cada posible C2 PS geométrico único:
- C1 M30: 10 M3 anteriores a C2; C2 M30: 10 M3 + 2 M15 hasta C3.open, H4/diario no inventados.
- Contexto tres H1 **anteriores a C2**: 12 M15 que cierran antes o exactamente en `C2.open`, derivados de la última hora H1 plenamente cerrada. Al faltar cualquiera de las 12, registrar `pre_c2_h1_context_available=false`, no rellenar con H1 futura ni alto completo de C2.
- **2.656/2.657** shapes tienen 12 M15 previas completas; CADJPY presenta 1 caso sin contexto H1 completo, aislado y NO elegible para validar un swing de esa referencia. Quedan **1.986 días-mercado** como techo con H1 disponible, aún NO source-equivalente a relevante TTrades.
- La fuente de H1 es un **universo de inspección contextual QORE**, no prueba de que TTrades seleccionaría el high/low observado. La relevancia del swing sigue exigiendo evaluación contextual, separación y reacción ex-ante, sin regla universal numérica [Relevant Swings](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/).

Manifest source-only congelado y cotejable máquina contra los SHA originales: [VT08_A_FROZEN_M30M3_BULLISH_FIRST_FAIL_COUNTS_2026-10-15.json](VT08_A_FROZEN_M30M3_BULLISH_FIRST_FAIL_COUNTS_2026-10-15.json); contiene cinco hashes M3/M15 de origen, 93.230, 2.657, 1.987, 2.656 y 1.986. Artefactos JSON fuente por mercado en el run real #38715342991; **retención de Actions temporal**, preservar snapshot SHA/code/run/IDs para restauración antes de caducidad. Ningún precio bruto con derechos particulares fue comiteado al repo público.

## 4. La tarea B ya no es «faltan barras»: adjudicación por fuente y cognitiva

B debe descargar los cinco artefactos R3 y auditar su productor **sin usar el código A como oráculo**. Repetir 12 bars H1 y C1/C2 M3/M15 de positivos y negativos; verificar feature cutoffs PRE-C2 vs C3. Seleccionar casos por cronología y categoría, no por PnL, y adjudicar:
1. **Bias** HTF/daily auténtico y `reference_swing` relevante conocido antes de C2.open. Diferenciar swing point 3 barras geométrico de relevant valid separation cualitativo D. Si no adjudicable, `AUTHOR_SELECTOR_UNSPECIFIED_D`.
2. **POI** significativo con fuente, orden por subfamilia (FVG>Swing>CISD escrito solo para *continuations*), reacción y desempate documentados. No elevar simple geometría H1 FVG a POI.
3. **CISD/PS** M3 origen de serie opuesta, primer open, confirmación cerrada antes C3, PS autor verdadero y múltiples escenarios; no usar nearest PS automáticamente.
4. **EQ regime** según WITH/AGAINST de swing autor válido pre-C2; `C2.high/low/close` solo disponible a C2.close. **breaker-low** auténtico y stop LONG debajo de EQ Y breaker low: `SL < min(EQ,breaker_low)`, dejando espacio FVG si el ejemplo lo requiere.
5. **HTF untouched target** válido con filtro de consumido as-of y selección previa; no usar TP fijo 2R QORE, target realizado o filtro «este trade ganó».
6. **Situations reales**: cada uno de los 27+ campos `Vt08ForexSituationModel` debe vincular su valor semántico a `source_bar_id`, archivo SHA, cutoff, tipología A/B/C/D y documento fuente, incluyendo UNKNOWN explícito. No construir `methodology_valid=True` mientras cualquiera de esas precondiciones sea D.
7. A/B debe aprobar **manifiesto verificable y firmantes independientes** solo tras validar fuente y eventos auténticos. B R2 ha reportado 226 PASS en contratos cognitivos y 120 raw muestras auditadas, pero integración M30/M3/27+ campos sigue **NO APROBADA**.

## 5. Las puertas económicas no se maquillan

**0 source-author-complete, 0 reales admitidos en cognitiva, 0 fills verificados, PF/DD/Sharpe/Sortino NOT MEASURED** bajo esta nueva familia. Para el ensayo independiente nuevo se requiere contexto fuente A+B, PIT market source y BID/ASK/fees real alineado a decisiones/fills/salidas, sin OOS previamente visto. QORE Native G1 sí preserva **3×10min snapshots históricos BID/ASK** para los cinco mercados en diferentes ramas, pero eso no es historia 3Y ejecutable. Reusar pruebas cortas como NET 3Y está prohibido.

Los Gates heredados VT08 `PF>=1.80`, `DD<=6R`, `MonteCarlo p95 DD<=15R`, `P(terminal>0)>=0.90`, media R no negativa, no sustituyen automáticamente las puertas históricas de #787 `PFnet>1.15, >=100 fills` del ensayo terminado. Sharpe/Sortino/densidad nuevos sin umbral Owner versionado siguen PENDING, jamás inventarlos. Economía futura solo sobre resultados **1R homogéneos** para evaluar método, sin lote adaptativo, sizing, apalancamiento ni composición.

**Estado y STOP verificable:** `METHODOLOGY_SOURCE_NOT_CERTIFIED`; PR #765 DRAFT, PR B #764 DRAFT, no merges, sin permiso VPS/DEMO/LIVE, sin abrir 7Y, sin operación. Si fuente relevante no reproducible, resolución de familia `NO_ESPECIFICABLE` y sin atribuir resultado negativo al método TTrades completo. Es un límite científico real, no un problema que resuelva escribir cientos de tests.


## 6. Índice exacto de artefactos con verificación de manifiesto y vencimiento

Última comprobación posterior al manifiesto congelado: [run #38715560333](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333), **5/5 SUCCESS**, HEAD ejecutado `394116f13449fc310d7fbc5f0b5f60aa1bb247d4`. Cada ejecución vuelve a leer M3/M15 del proveedor guardado, reproduce categorías y sumas sin PnL, compara hashes y conteos contra `VT08_A_FROZEN_M30M3_BULLISH_FIRST_FAIL_COUNTS_2026-10-15.json` y rechaza discrepancias. Artefactos **contienen el censo por año + 2.657 recibos positivos totales + muestras negativas**, con C1, C2 y 3 H1 previas donde disponibles.

| Mercado | Artefacto GitHub Actions ID | Caduca (UTC) |
|---|---:|---|
| EURJPY | [11962966523](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333/artifacts/11962966523) | 2026-11-14 09:48 |
| USDCHF | [11962777123](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333/artifacts/11962777123) | 2026-11-14 09:48 |
| NZDUSD | [11962337776](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333/artifacts/11962337776) | 2026-11-14 09:48 |
| CADJPY | [11961903553](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333/artifacts/11961903553) | 2026-11-14 09:48 |
| USDCAD | [11962906707](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333/artifacts/11962906707) | 2026-11-14 09:48 |

**Custodia P0:** copiar estos paquetes a almacenamiento seguro permitido ANTES del vencimiento, con SHA256 ZIP calculado y permisos/licencia verificados. El manifiesto de estadísticas está comiteado, pero el código reproducible aún necesita los raws originales de Actions: el informe por sí solo NO sustituye el respaldo del archivo bruto. No comitear datos de precio cTrader con licencia a repositorio público.
