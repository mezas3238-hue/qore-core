# VT08 Arquitecto A — R2: custodia física nativa M3/M15 y contrato de ejemplos ciegos para B

**Fecha:** 15 octubre 2026 · **PR:** #765 DRAFT · **Issue A:** #762 · **Issue B:** #763 · **Repo:** `mezas3238-hue/qore-core` · **Tipo de evidencia:** fuentes físicas DEV, NO metodología final, NO fills, NO PnL.

## I. Avance REAL con datos existentes en GitHub

Workflow de ejecución genuina por cinco pares:
[VT08 A Native M30M3 Raw Custody, #38709204852](https://github.com/mezas3238-hue/qore-core/actions/runs/38709204852) — **SUCCESS 5/5 jobs**, Ruff green, 11 pruebas unitarias × 5 jobs green (misma suite repetida), con artefactos fuente de:
- [GitHub Actions M3 nativo cTrader #35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396): `qore-vt08-m3-fractal-${MARKET}-bc1379d7661aac202495ec67afdd3098473ba723`, `m3-evidence.json`.
- [GitHub Actions M15 #35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907): `qore-vt08-cognitive-5m-fresh-${MARKET}-b2d33e1b4829d8b4afc76983decca8a99131403c`, `market-evidence-1095d.json`.

Todos los archivos de origen se hashearon a SHA256 **sobre bytes completos** antes de parsear. Barras reconstituidas: M30 desde diez M3 cerradas Y desde dos M15 cerradas; coincidencia de OPEN/HIGH/LOW/CLOSE y horarios UTC exactos; no reparar diferencias silenciosamente. Se escanearon *todas las ventanas ancladas NY 01/05/09 detectadas en serie M3* del período DEV utilizado previamente, no solo trades positivos ni muestras elegidas por rentabilidad:

| Mercado | Ventanas detectadas | M3/M15 M30 completas | Source incomplete | M30 OHLC mismatch | SHA256 M3 | SHA256 M15 |
|---|---:|---:|---:|---:|---|---|
| EURJPY | 2330 | 2328 | 2 | 0 | `5d04a7606c3a91067b43425c215ae8df68aa4f3e59c2f7c54061d021a213d355` | `565c1f93f31ee100f07ec4aa5b058c4a2b6f1600bc7980989720589c198d5047` |
| USDCHF | 2330 | 2328 | 2 | 0 | `b10a2393a0d4ac6cd8abc456d207e9a9e14bf4d218c83a08fe800c8d608ce7f9` | `1b8541c1dc8358200a1a0d77d6a6f3df97c86b9a2b3400e7425a59c6bb12f464` |
| NZDUSD | 2330 | 2327 | 3 | 0 | `9692d8aa690d413b91a7603d7521261e6217c6b92c55647d25993e14f21e99c0` | `77a9c599f6f22c7353ded3a76ce18ced2bd2e3e5c8badfac6dfa4c3b228a99cb` |
| CADJPY | 2330 | 2328 | 2 | 0 | `9ae504602cf342667e5e64be58365e4aa0b22c47b6ffba553e90d0167a7ac8cf` | `e598cab241aa183cd9661d6939978322b1f8a9959a82c6bb409d5e2c374d44f4` |
| USDCAD | 2330 | 2328 | 2 | 0 | `7e934a106a4788e87ee05a1f04128ec1d9c8d34c308cb9c3e60758ec55e348e8` | `6a47a292f4eb3c7b35c5510602d37763edbf90b122e276a298379b2b4e53ea93` |
| **TOTAL** | **11650** | **11639** | **11** | **0** | — | — |

**Alcance exacto:** 0 mismatches en ventanas **completas**; 11 ventanas incompletas NO fueron comparables, no es exacto afirmar que absolutamente todas las velas de tres años están limpias. **Tampoco esto implica 11.639 setups.** Las 11 faltantes deben excluirse hasta acreditar missing/unclosed/source reason con reproducibilidad. El código R2 posterior `vt08_a_m30m3_raw_bar_custody_v1.py` conserva eventos concretos con `anchor_utc`, `missing_or_unclosed_m3_utc`, `missing_or_unclosed_m15_utc` en informe. Las 24 muestras por mercado se han separado cronológicamente en el período DEV usando fórmula de posición fija, independientemente de precio, setups, señales o resultados, para ofrecer al B ejemplos con distintas fechas.

**Para cada barra fuente entregamos:** mercado del reporte, `source_raw_sha256`, `opened_at_utc`, `closed_at_utc`, `available_at_utc`, `ohlc`, `source_bar_id=SHA256(JSON canónico de esas propiedades)`, `profile` M3/M15. La huella es cálculo reproducible, no certificado criptográfico del bróker y NO valida semántica de POI/swing. Disponibilidad de vela equivale al cierre, nunca antes.

## II. Fuente TTrades primaria: qué queda A y qué queda D

Fuentes revisadas directamente: [Timeframe Alignment, Example 1 / Three Layers](https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/); [Relevant Swings, Valid Separation / Fractal Lookback](https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/); [Only POI That Matter, FVG First](https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/); [EQ, C2 With/Against Swing](https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/); [Breaker Blocks Simplified, Formation/Zone](https://ttrades.com/breaker-blocks-simplified/); [Price Targets, Untouched Highs](https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/).

**A escrito (sin inferir trade):**
1. La dirección viene de contexto superior, confirmación por estructura CISD, entrada LTF (3 capas); M30→M3 es uno de los emparejamientos **del ejemplo**, no reemplaza el H4 source-day/Owner de VT08 expansión por decreto.
2. Jerarquía PARA CONTINUACIONES desde protected swing hacia rango actual: **FVG relevante primero, swing high/low después, retest CISD al final**. La prioridad entre **categorías** es fuente A escrita, pero identificar los FVG válidos/tocados, segmento espacial y empate entre múltiples FVGs **es aún D**; OB aparece también como nivel en artículo de alignment, no se puede declarar que el artículo POI impone la misma jerarquía a TODAS las familias.
3. Un pivot básico requiere izquierda/derecha; relevancia requiere extremo contextual y separación. Fuente declara explícitamente **sin fórmula numérica estricta de separación**. Tres velas HTF incluyendo actual: valores de vela actual SOLO snapshot parcial as-of; no high final futuro. Qué pivot es genuinely relevant es D sin adjudicación cognitiva ciega.
4. EQ del C2 tiene **dos regímenes** dependiendo del swing válido y dirección de cierre: full range with swing, close-to-extreme against swing. No definir full-high-low como regla universal ni usar C2 final antes de C2.close.
5. Breaker bullish descrito low→high→lower low→higher high y velas up-close en zona; **no son necesariamente cuatro velas consecutivas M3**. Para Example1 LONG el stop debe ir debajo de EQ y breaker low, además permitir FVG inferior si aparece continuación. `SL<min(EQ,breaker)` necesaria, identidad de niveles D.
6. Target long: high anterior HTF **untouched**. El artículo no define un desempate total universal entre varios highs; no elegir ganador mirando target alcanzado.

**Prohibiciones:** no promocionar `QORE_PS_ONLY_PROXY`, 4-M3 breaker geometry, external H1 pivot automáticamente a `AUTHOR_A`. `source_complete_candidate_events=0` y `APPROVED_A_B_MANIFEST_SHA256=None` hasta verificar casos completos con B.

## III. Tarea de B: clasificar ejemplos sin contaminar el outcome

La tabla de evidencia por barra y 120 ejemplos de contextos distribuidos temporalmente debe usarse para una ronda de anotación **ciega**. Cada caso de fuente debe vincular:
- IDs de swing pre-C2 y criterio contextual; HTF bias as-of y owner-source scope.
- Nivel POI y otros POIs elegibles **ANTES** de la decisión, junto con la jerarquía A que se aplica solo a la familia correspondiente; aceptar discrepancia `AMBIGUOUS_D` cuando dos estructuras valen.
- CISD M3 opposing-series origin/close, PS auténtico, breaker candle IDs y low, EQ label desde swing pre-C2, target high untouched y reloj de entrada.
- Para cada uno de los campos requeridos de `Vt08ForexSituationModel`, enlace a `source_bar_id`, `source_raw_sha256`, `available_at` y autoridad A/B/C/D; UNKNOWN honesto cuando no hay prueba.
- Registro de positivos, negativos, ambiguos y no-decidibles basado en metodología sin mirar PnL; rater1/rater2 independientes y discrepancias registradas. Hacer review usando **texto y barras brutas**, no veredicto o flag del productor A.

### Límite del presente R2

La selección temporal de barras produce **ejemplos de mercado**, NO 120 decisiones de trade ni un censo de verdaderas oportunidades. Para certificar una señal faltan: POI/relevant swing/breaker/target exactos y revisión B, 27+ campos completos, manifest A/B, broker BID/ASK y costes para entradas/salidas, runner económico pareado sin sizing y Gates PF/DD/Sharpe/Sortino/OOS aprobados por identidad nueva. 7Y sellado, no LIVE, no merge ni VPS.

## IV. Trabajo de A incorporado y próximos pasos sin tuning

- `src/qore/infrastructure/trader_lab/vt08_a_m30m3_raw_bar_custody_v1.py`: generador de custodia por vela, validación as-of y checksums de fuente nativa.
- `tests/infrastructure/trader_lab/test_vt08_a_m30m3_raw_bar_custody_v1.py`: faltantes, manipulación OHLC, DST, ancla, hash fraudulento y control de ausencia de permisos.
- `.github/workflows/vt08-a-m30m3-native-raw-custody-source-only.yml`: cinco jobs aislados, artefactos y logs.
- `vt08_a_final1_three_verdict_author_fidelity_gate_v1.py`: barrera A/B fuente-sólo endurecida previamente, **NO señal real**.
- Arch. A solicita **B revisión de este corpus y schema de cada feature**; la rama B continúa con 205 PASS, pero está pinned a un contrato antiguo M15 y NO puede declarar integración M30/M3 actual sin nuevo pin/freeze revisado.

**Status certificación:** `UNVERIFIED_AUTHOR_SELECTORS_AND_BROKER_EXECUTION`; M0 pendiente, C0 pendiente, X0 pendiente, Gates económicos no medidos. Cero new-source-complete fills, cero ejecución real. Sin sizing.
