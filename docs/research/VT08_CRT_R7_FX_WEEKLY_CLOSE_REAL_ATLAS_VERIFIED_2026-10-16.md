# VT08 CRT — R7 Resultado verificado: cierre semanal FX vs hueco M5 interno

**Fecha:** 2026-10-16. **Estado:** AUDITORÍA EMPÍRICA COMPLETA en muestra 2024–2026 CONSUMIDA; NO certifica bróker, metodología, trader ni edge económico. **No** cambia V1/V2/V3/G-M4. Preregistro publicado **antes** de la reproducción: [R7 prereg](VT08_CRT_R7_ORIGINAL_ATLAS_FX_WEEKLY_CLOSE_GAP_FORENSICS_PREREG_2026-10-16.md), commit `1654c5dd11dbfae2b1e414fa48b2daf2b483e288`.

## Evidencia instrumentada en GitHub Actions

- [**Run #38902464494**](https://github.com/mezas3238-hue/qore-core/actions/runs/38902464494) **SUCCESS 3/3 jobs** (quality, original AUDUSD, original USDJPY) con código exacto `b196934584d5acf752e73b89e290eb8394d7471c`. Quality Ruff + mypy sobre 3 fuentes, **35 pytest PASS**. Datos cargados con adaptador hash-validado original CIBO Atlas run `35166210458`, sin credenciales de bróker ni nuevo feed.
- Archivos nuevos: `src/qore/infrastructure/trader_lab/vt08_crt_original_fx_weekly_close_forensics.py`, `tests/infrastructure/trader_lab/test_vt08_crt_original_fx_weekly_close_forensics.py`, integrado en `vt08_crt_g2_g7_real_atlas_pit_bridge.py` y `.github/workflows/vt08-crt-g2-g7-real-atlas-pit-audit.yml`.
- 148,171 M5 AUDUSD / 148,201 M5 USDJPY = **296,372** M5 originales. V3 + G-M4 permanecen **139** identidades, **5** UNKNOWN; G7 mantiene **108** WAIT. Sin fills, sin PnL, sin cambio de fuente ni sizing.

## Resultado decisivo de la comparación NY-DST

Se compararon, SIN seleccionar semanas retrospectivamente, **8 viernes previos + el viernes del gap + 8 posteriores** por cada caso. Se convirtió cada viernes a **17:00 hora America/New_York** con `zoneinfo` IANA; no se aplicó hora UTC fija, y se verificó la vela M5 inmediatamente anterior, el hueco en el corte y ausencia de nuevas barras durante 60 minutos.

| Caso | NY local | Semanas con M5 previa, sin M5 al cierre ni en hora posterior | Dictamen factual |
|---|---|---:|---|
| **AUDUSD 2025-04-25 21:00Z**, evento `bfc66b2457f3e3ec93ae` | 17:00 EDT | **17/17** | `CONVENTION_CONSISTENT_PROVIDER_CALENDAR_UNVERIFIED` |
| **USDJPY 2026-06-19 21:00Z**, evento `a63b7073af8d33e8963a` | 17:00 EDT | **17/17** | `CONVENTION_CONSISTENT_PROVIDER_CALENDAR_UNVERIFIED` |
| **USDJPY 2025-02-12 22:30Z**, evento `11a7c3cdb30a9eabdbbe` | Miércoles 17:30 EST | No corresponde al cierre del viernes | `INTERNAL_ONE_BAR_GAP_PROVIDER_SOURCE_REQUIRED`: 22:25 y 22:35 M5 EXISTEN; 22:30 falta |

La conversión NY demuestra también EST→EDT: p. ej. 28-FEB-2025 y 07-MAR-2025 cierre habitual 22:00Z; 14-MAR-2025 21:00Z. Los 17/17 de AUDUSD cubren 2025-02-28…2025-06-20; los de USDJPY 2026-04-24…2026-08-14. Es **evidencia empírica fuerte de que el feed sigue el cierre semanal habitual**, pero no confirma que el servidor/cuenta específica declarase ese schedule en 2025/2026. Fuente externa como comparación, NO prueba de ese bróker: [FOREX.com, Forex Market Hours, domingo-viernes 17 ET](https://www.forex.com/en-us/help-and-support/market-trading-hours/).

### Qué queda realmente pendiente de los cinco UNKNOWN

1. **Dos fuera de invalidación observados en el open de decisión:** AUDUSD `fa3965fd21bc149c2ce8` (2026-08-06 21:00Z), USDJPY `9572d855b2dedc8fecb2` (2024-12-26 23:00Z). No se deben retro-etiquetar como trade ni terminal; requieren precondición cognitiva documentada de *NO-VIABLE ABSTAIN*, aprobada por revisión de artículo G5/G7 antes de aplicarse al runtime.
2. **Dos cierres semanales compatibles:** AUDUSD viernes 25-ABR-2025 21Z y USDJPY viernes 19-JUN-2026 21Z. Para cambiar G-M4, obtener calendario histórico propio del símbolo/servidor/venue, política explícita de expiración al cierre de sesión sin inventar un toque, firma metodológica y event ledger con reloj. No adjudicar automáticamente.
3. **Un gap M5 aislado comprobado:** USDJPY miércoles 12-FEB-2025 22:30Z. Recuperar M5 del **mismo productor** con identidad UTC y SHA/autenticación; alternativa válida mantener censurado. **No** insertar interpolación ni datos de broker distinto para ganar clasificación.

G7 sigue protegido: la política experimental de **ALL-PRIOR-TERMINAL** genera **108 WAIT debido a arrastre de 5 UNKNOWN**, pero eso no valida relajar la regla. **R7 deja los cinco UNKNOWN, los 108 WAIT y G-M4 PASS=False**. El efecto de la política G7 debe arbitrarse por corpus de 3 fuentes e independiente, no por densidad histórica o PnL.

## Artefactos R7 y custodia

**AUDUSD:** artifact GitHub `12046397924`, ZIP SHA256 `fc25417bd2e42994788658c3a5ebb0d18f7e15d08198c8307ea2a316172a57f2`.

**USDJPY:** artifact GitHub `12046911206`, ZIP SHA256 `a81db8e9cc89904b5a614b1cec48fa2023fed8f6677a65cf04bccebfc03ef175`.

GitHub consultado `expired=false`; ambos expiran nominalmente `2027-01-14T12:42:51Z`. Dentro: `g2-g7-real-atlas-pit-summary.json`, `g2-g7-real-atlas-pit-ledger.jsonl`, `g2-c0-c1-blind-predecision-cases.jsonl`, `gm4-unknown-expost-forensics.jsonl`, **`r7-original-m5-fx-weekly-close-evidence.jsonl`** y `SHA256SUMS.txt` con commit. Original Atlas expira antes (2026-12-16): proteger conforme a issue #837. No decir que un ZIP temporal es un vault.

## Dictamen de certificación y próximas acciones

**CI y evidencia causal excelentes no equivalen a G-M1 PASS.** G2: 36 conflictos de referencia C0/C1 (14 opuestos) y un inventario old CRT integral pendiente; 48 FIRST-LOOK G-M2 aún sin reseña humana; G-M3/G-M4 autenticación de cognitiva y de terminación; G-M1 revisión G1-G7 y firma por Owner+auditor independiente #976; G-M5 no emitido. Global PF/costes/BID-ASK/OOS virgen/WFO/MC/Sortino/Sharpe y DD patrimonial exclusivo CIBO/Risk aún ausentes. V2/V3 trayectorias adversas no pueden certificarse por pruebas positivas del pipeline.

**Estado:** G-M1..G-M4 PARTIAL, G-M5 NOT ISSUED, GLOBAL NOT CERTIFIED. PR #626 DRAFT, ningún merge, VPS/demo/live/órdenes. **Sizing VT08 categóricamente prohibido** incluso hipotético.
