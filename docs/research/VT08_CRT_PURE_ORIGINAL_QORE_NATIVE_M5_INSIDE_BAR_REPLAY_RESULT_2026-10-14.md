# VT08 CRT PURE — RESULTADO VERIFICADO SOBRE DATOS ORIGINALES DE QORE NATIVE

**Corte:** 2026-10-14 · **Estado:** REPLAY DIAGNÓSTICO BRUTO TERMINADO · **PR #626** (DRAFT, sin merge).  
**Orden del Owner:** usar los millones de velas YA en GitHub; comparar CRT Romeo / SpeculatorFL / TraderFlameseN y probar variantes en replay.  
**No se buscó ni necesitó descarga externa de datos de mercado.** La ruta previa de muestra externa queda reemplazada por esta evidencia original.  
**Run con resultados:** [GitHub Actions #38546723415](https://github.com/mezas3238-hue/qore-core/actions/runs/38546723415), HEAD exacto `1315d2bf41776d11557ee1a259cff3cd4303a8cb`. **quality SUCCESS** (Ruff, Mypy, 9/9 tests); **AUDUSD SUCCESS; USDJPY SUCCESS**.

## A. UBICACIÓN DE MILLONES DE VELAS — NO EN EL ÁRBOL DE COMMITS

- Atlas original QORE/CIBO, [run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458): **12 originales, 8.726.985 velas M5**, artifacts ZIP por símbolo, separados del source-tree; manifiestos RAW y SHA por año. `expired=false`, expires `2026-12-16T00:21:18Z`.
- QORE Native ampliación [run #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541): **21 adicionales, 15.650.435 velas M5** originales, `expired=false`, vencimiento `2027-01-10`. Auditado en [G0 final 33/33](https://github.com/mezas3238-hue/qore-core/blob/research/qore-native-final33-tail-ready-g0-20261012/docs/research/QORE_NATIVE_FULL_33_MARKETS_G0_EXECUTED_FINAL_2026-10-12.md).
- **Unión 33 mercados: 24.377.420 velas M5** (dos cohortes, sin afirmar broker idéntico).
- Original M1 AUDUSD y USDJPY también localizado en [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), artifacts `10618116387` / `10617557766`; no consumidos por este ensayo M5.
- **Fuente de VT08 M5:** AUDUSD artifact `10475697610` (ZIP digest GitHub `ac72aaf438c164cd79691a7cf1f3f0a68f4c65aa6a91a921a721c7a04ebdc2f0`); USDJPY `10475389415` (ZIP digest `e3ac9a45f3000c3e3bd93e50c730c952ddd08f77f1c857b5c4b3a67679fcaa51`). Cargados con `actions/download-artifact@v4`, `run-id:35166210458` y permisos `actions:read`.
- Ambos repositorios originales venían de Atlas `CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1`, código productor `ab782b8e9f890f86a2b6500070f0556b4b685e3d`; el script verificó `symbol-consumption-manifest.json`, `MANIFEST_SHA256SUMS.txt`, RAW y DATA_QUALITY de 2024, 2025, 2026 y recuentos anuales. El SHA del archivo ZIP externo procede de metadatos GitHub, no de recálculo del ZIP por el job. SHA de archivos anuales sí se verificaron localmente.

## B. HIPÓTESIS PREREGISTRADA SIN PARAMETRIZACIÓN RETROSPECTIVA

- **Fuente A RomeoTPT:** Model #1 y CRT con old CRTH/CRL, H4→M15. No se ha adjudicado una regla universal `INSIDE_BAR_REQUIRED` al autor.
- **Fuente B SpeculatorFL + TraderFlameseN:** inside bars durante el contexto de acumulación como observación estructural; textos considerablemente dependientes, NO replicaciones independientes.
- **Política única QORE:** etiqueta `INSIDE_BAR_PRESENT` si durante C1 H4 se encuentra al menos un par consecutivo completo M15 con `high_actual < high_anterior` y `low_actual > low_anterior`. `UNKNOWN` si hay cortes de data. La etiqueta ya era visible **antes de C2/C3**. No se ajustó número de inside bars en función del resultado.
- **Control inalterado:** R2-C "old-level-close-unmitigated", **QORE engineering**, pivote M15 strength1, source event+body-close confirm, entry próxima M15, SL estructural de vela fuente, destino C1 50%, fin C3, stop-first si ambigüedad de OHLC. Cada grupo es **subconjunto del ledger de control**; no se recalculan fills ni inventan trades.
- El replay usa una ventana VT08 **previamente consumida**, por lo que no constituye un OOS virgen ni prueba prospectiva de edge. La serie Atlas termina `2026-09-17`; el replay solicitaba hasta `2026-09-21`: faltan los 4 últimos días, sin relleno ni sustitución.

### Muestras y resultados BRUTOS (R; no dólares ni sizing)

| Mercado | Cohorte | Trades | PF bruto | Suma R | Máx. DD R |
|---|---|---:|---:|---:|---:|
| **AUDUSD** | Control | 69 | 1,02491 | +0,53736 | 4,67776 |
| AUDUSD | C1 Inside presente | 59 | 1,10597 | +1,88144 | 3,47391 |
| AUDUSD | C1 Inside ausente | 10 | 0,64788 | −1,34409 | 2,61819 |
| **USDJPY** | Control | 64 | 0,86449 | −3,72815 | 13,04191 |
| USDJPY | C1 Inside presente | 58 | 0,98402 | −0,37569 | 9,83503 |
| USDJPY | C1 Inside ausente | 6 | 0,16188 | −3,35246 | 4,00000 |

**Períodos previamente congelados:** period1: 2024-09-21→2025-09-21; period2: 2025-09-21→2026-09-17 (fin fuente original, no el fin pedido).

| Mercado | Cohorte | Período 1: PF, R, n | Período 2: PF, R, n |
|---|---|---|---|
| AUDUSD | Control | 0,94968 / −0,57984R / 35 | 1,11119 / +1,11719R / 34 |
| AUDUSD | Inside presente | 1,11231 / +1,03835R / 30 | 1,09908 / +0,84310R / 29 |
| USDJPY | Control | 1,61901 / +6,70507R / 31 | 0,37454 / −10,43323R / 33 |
| USDJPY | Inside presente | 1,73526 / +7,22897R / 29 | 0,44414 / −7,60466R / 29 |

**Lectura:** el filtro de contexto *inside bar* discrimina aquí algunos trades muy malos del control, especialmente fuera del grupo, pero la mejora de AUDUSD es **pequeña en escala absoluta** y USDJPY no logra PF bruto >1 en ambos períodos. **NO seleccionarlo como regla certificada**: 10 AUDUSD y 6 USDJPY en grupo ausente; muestra pequeña, dependencia temporal, dos autores Level B no independientes y una hipótesis evaluada sobre época ya utilizada.

### Evidencia de los dos runs concretos (results y SHA artifact)

- [Run SUCCESS #38546723415](https://github.com/mezas3238-hue/qore-core/actions/runs/38546723415), 3/3 jobs SUCCESS.
- [Resultado AUDUSD artifact #11885015976](https://github.com/mezas3238-hue/qore-core/actions/runs/38546723415/artifacts/11885015976), `sha256:40d3f726942e114e44c7c031e4f9dae1c40699258e87eb7d575edc6f10533be8`, calidad/guardas 9/9 SUCCESS.
- [Resultado USDJPY artifact #11885365112](https://github.com/mezas3238-hue/qore-core/actions/runs/38546723415/artifacts/11885365112), `sha256:b3e2c24de2c2ee537a427c238043222c8fda625df9987446a9c74e1097d82b08`.
- ZIPs resultados contienen `report.json`, `diagnostics.jsonl`, `stdout.log`, `git-sha.txt`, `SHA256SUMS.txt`. Las cifras arriba se copiaron de la cadena `VT08_THREE_SOURCE_INSIDE_BAR=` en cada **log GitHub CI exitoso**, NO se dedujeron ni se inventaron.

## C. CONCLUSIÓN Y REGLAS SOBERANAS

**VEREDICTO:** `INSIDE_BAR_CONTEXT_DESCRIPTIVE_SUPPORT_ONLY`; **NO EDGE CERTIFIED**, **NO PROMOTION**. Este ensayo elimina la **ambigüedad de disponibilidad del DATO**, no las ambigüedades del MÉTODO. Sostiene que la alternativa Level B merece una revisión metodológica en episodios reales, pero **NO** prueba que sea fuente primaria Romeo ni que mejore netamente el trader.

**Pendiente:** la pertenencia `OLD_LEVEL_OWNERSHIP`, autenticidad de interpretación de CSD, prioridad HTF key level, conflictos C2/C3, Journey, MOB e invalidación; luego expedientes reales trazados y gates cognitivos. Distinguir siempre `model1_source_A` de los supuestos añadidos `secondary_source_level_B`.

**Atención almacenamiento:** [Issue #837](https://github.com/mezas3238-hue/qore-core/issues/837) sigue abierta: 12 Atlas se pierden de Actions tras 2026-12-16 si no se asegura vault/restauración autorizados. No subir 728 MB a commits ni inventar permanencia.

**Prohibiciones intactas:** no merge #626, no VPS, no DEMO/LIVE operaciones, no MT5/producción, no FundedNext LIVE, no sizing/lotes/volumen/apalancamiento en VT08, autoridad CIBO/QORE Risk para dinero, no filtrar holdout por PF.  
