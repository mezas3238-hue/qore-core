# VT08 CRT — R8: los tres huecos M5 conciliados con el productor original

**16 OCT 2026.** Investigación histórica original SHA-backed ejecutada, sin alterar el generador V3, G-M4 ni los 139 eventos; **NO CERTIFICACIÓN** metodológica o económica. Owner permite síntesis de RomeoTPT + SpeculatorFL + TraderFlameseN, pero G-M1 aún requiere adjudicación independiente. No sizing de VT08, broker orders, demo/live, VPS o merges.

## Verificación contra artefactos originales

[GitHub Actions **#38975246782**](https://github.com/mezas3238-hue/qore-core/actions/runs/38975246782) **SUCCESS 3/3 jobs** (calidad y originales AUDUSD+USDJPY), HEAD probado **d345770ada8c4d2815866158f557483e031d7f6a**. Ruff PASS, mypy PASS para 4 módulos, **43 tests PASS**. El preregistro [R8 original quality gap custody](VT08_CRT_R8_ORIGINAL_PRODUCER_QUALITY_LEDGER_GAP_CUSTODY_PREREG_2026-10-16.md) fue commit **e53084871793f9adb1b0f5584999f8f17288e6a5** ANTES del replay real.

El original CIBO producer commit **ab782b8e9f890f86a2b6500070f0556b4b685e3d** generó `DATA_QUALITY_LEDGER/{year}.jsonl` con `kind=UNRESOLVED_CLOSURE_OR_MISSING_DATA`. Esta auditoría cargó los **296,372 M5 originales** (148171 AUDUSD, 148201 USDJPY) verificados por manifiestos y SHA, volvió a cotejar el **SHA del ledger de calidad anual** y halló EXACTAMENTE UN registro del productor para cada uno de los tres huecos. Antes de aceptar un match verificó símbolo, producer identity, timestamp raw anterior/siguiente, magnitud real de hueco, clasificación de weekend y sello `market_open_expected = null`.

| Mercado / evento V3 | Intervalo de productor verificado | Ausencia en calendario M5 | Registro |
|---|---|---:|---|
| AUDUSD `bfc66b2457f3e3ec93ae` | 2025-04-25 **20:55** → domingo 2025-04-27 **21:00** UTC | **576 slots** | spans_weekend=true; market_open_expected=null |
| USDJPY `a63b7073af8d33e8963a` | 2026-06-19 **20:55** → domingo 2026-06-21 **21:00** UTC | **576 slots** | spans_weekend=true; market_open_expected=null |
| USDJPY `11a7c3cdb30a9eabdbbe` | miércoles 2025-02-12 **22:25** → **22:35** UTC | **1 slot** | spans_weekend=false; market_open_expected=null |

**Dictamen forense:** las tres ausencias están **en los registros de calidad nativos originales del productor CIBO del 17-SEP-2026**, así que no fueron introducidas por el posterior replay VT08. **2** son huecos completos de fin de semana convencional (evidencia R7 17/17 viernes vecinos por mercado) con barras originales reanudadas el domingo 21Z. **1** es un hueco aislado entre barras reales el miércoles; el productor NO prueba su causa ni autoriza imputación.

El productor etiquetó *los tres* **UNRESOLVED_CLOSURE_OR_MISSING_DATA** y **market_open_expected=null**. Eso **no** equivale al certificado del schedule histórico del broker cTrader. Ni atribuir un "mercado abierto" en el miércoles a un feed autenticado sin calendario ni decir que estaba "cerrado" en los viernes por autoridad contractual. R8 no convirtió ningún UNKNOWN, no abrió operaciones y no aprobó G-M4.

## Huellas de custodia

**AUDUSD:** calidad 2025 SHA256 anual `48ffebed4c26cc420dd1d56d75d03e6debd7d586ed03ef5d16e7f0e198b1895e`; SHA256 del registro específico (JSON canonical sorted): `4dee03683a3432a76a9913718faf92c502102b3a0478b932e6d663a929759266`.

**USDJPY 2025:** calidad anual `b3d1eba7c9a4a2cdee29bc7514169c6d5b65d1c42c379c1433fe891b779d671f`; registro 12-FEB-2025 `2844268b7907c239499d1d0a19d9dc003f49de7b7b1fc579180e82936aa182b2`.

**USDJPY 2026:** calidad anual `5a44d978efbc7c8d7e258b611b6770c997ea87637e709e4ae3db3b0b3dcbce0e`; registro 19-JUN-2026 `1b2d317c012ddb3ab1228d986ee2bf5b87a3f4ed3f5d20f86f7c31fe0cd1e45c`.

**Artefactos de los resultados R8, comprobados mediante GitHub API:**
- AUDUSD artifact ID **12079270181**, ZIP SHA256 `f9702a394b52347b08a604e3bd1a6f9c4f91b4278edc48416ace7ec669f2b739`.
- USDJPY artifact ID **12079026049**, ZIP SHA256 `400da2be84fd0c8a05a660aebb5520d4b4aef85ea0ffbe4d332ecb7a9a4a8c31`.
- Ambos no expirados al consultarlos, **expires_at 2027-01-14T22:21:25Z**. ZIP incluye los R4..R8 ledgers, `r8-original-producer-sha-backed-gap-custody.jsonl` con source IDs y hash, `SHA256SUMS.txt` e identidad del commit. Los originales fuente #10475697610 y #10475389415 **vencen 2026-12-16T00:21:18Z**; issue #837 custodia urgente.

## Diagnóstico integral y camino más rápido sin falsa certificación

**Cinco G-M4 UNKNOWN**:
- **2 barreras:** open de M5 de decisión estaba ya más allá de invalidación (AUDUSD `fa3965fd21bc149c2ce8`; USDJPY `9572d855b2dedc8fecb2`). Necesita G5/G7 precondición *ABSTAIN — hipótesis no viable* antes de crear estado activo, revisión humana independiente, no reetiquetar retrospectivamente el G-M4 frozen.
- **2 cierres convencionales:** viernes 17:00 ET, 576 M5 calendario por fin de semana y reanudación domingo; autenticación real de schedule histórico de símbolo/servidor y contrato para expiración por cierre de mercado. No rellenar ni fabricar C3 expiry.
- **1 hueco M5 aislado de miércoles:** USDJPY 2025-02-12T22:30Z, documento original SHA confirmado. Único camino para atribuir trayectoria sería recuperar precio de **mismo origen con provenance exacta**; si imposible, mantener UNKNOWN censurado. El quality ledger por sí solo NO contiene su OHLC.
- **Efecto derivado:** 108 WAIT G7 bajo política propuesta ALL-PRIOR-TERMINAL = arrastre de UNKNOWN, no 108 defectos independientes. Cambiar memoria/lineage requiere G-M1 firmado **antes** de OOS, jamás escoger política por densidad/PnL.
- G2 **36** referencias C0/C1 rivales con 14 opuestas: paquete OHLC causal ciego aún sin firma; NO inventario exhaustivo old CRTH/CRTL. G-M2 48 casos FIRST-LOOK sin evaluador auténtico; G-M3 verdad externa, G-M4 router y G-M5. Global BID/ASK/costs/fills reales, PF/Sortino/Sharpe/OOS nuevo, WFO, MC, DD patrimonial exclusivo CIBO Risk.

**Estado cert:** G-M1..G-M4 PARTIAL, G-M5 NOT ISSUED, GLOBAL NOT CERTIFIED; PR #626 DRAFT/no merge, no orders/demo/live/VPS; sizing VT08 prohibido incluso lotes o R ficticio. R8 fortalece custodia, no demuestra edge.
