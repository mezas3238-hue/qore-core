# VT08 CRT — R4 G2/G7 PIT en Atlas M5 real: RESULTADO VERIFICADO

**Fecha:** 15 octubre 2026. **Estado:** investigación causal probada; certificación G-M1 y G-M4 pendiente. [GitHub Actions #38802320161](https://github.com/mezas3238-hue/qore-core/actions/runs/38802320161) SUCCESS, commit de código probado **2c23ddd72df6238e2ca3331ed3350e131ae4a5bb**. [Preregistro anterior al replay](VT08_CRT_G2_G7_REAL_ATLAS_PIT_BRIDGE_PREREG_2026-10-15.md) commit **a78e322e9a6f32c9d05d24388ddfd5ffadf3475c**.

## Ejecución real y reproducible

El job de calidad completó Ruff, mypy y **16 tests PASS**. Los dos jobs de mercado leyeron los artefactos existentes del CIBO Atlas GitHub Actions run **35166210458**, verificando los manifiestos originales, productor y SHA anuales mediante el adaptador original de QORE. Sin cTrader en vivo ni descargas de broker. Cada job recalculó el censo V3 congelado y el G-M4 histórico congelado, reconciliando por ID, mercado y reloj. **No modificamos V1, V2, V3, G-M4 ni sus parametrizaciones**, ni usamos PnL para seleccionar referencias.

| Medida auditada | AUDUSD | USDJPY | TOTAL |
|---|---:|---:|---:|
| Velas M5 originales verificadas | 148,171 | 148,201 | 296,372 |
| Candidatos V3 y G-M4 reconciliados | 61 | 78 | 139 |
| Segunda referencia H4 C0 elegible | 16 | 20 | 36 |
| Referencia C0 de dirección contraria | 4 | 10 | 14 |
| Referencia C0 de misma dirección | 12 | 10 | 22 |
| C0 ausente / H4 incompleta | 6 | 6 | 12 |
| G2 WAIT, inventario general no autenticado | 61 | 78 | 139 |
| G7 PROVISIONAL, sin autoridad | 18 | 13 | 31 |
| G7 WAIT, tesis anterior sin terminal probado | 43 | 65 | 108 |
| G-M4 UNKNOWN censurados | 2 | 3 | 5 |

**G2:** En la comparación deliberadamente acotada a las velas H4 C0 y C1, 36 casos tenían segunda referencia causalmente elegible, de los cuales **14 con dirección opuesta**. Esto demuestra ambigüedad del criterio simplificado, pero **no** una búsqueda exhaustiva de antiguos CRT highs/lows. G2 devolvió WAIT en los 139 casos **por diseño**: aún no se ha demostrado cobertura completa de referencias. En los otros 103 no puede inferirse que no existan competidores más antiguos. Nada seleccionó referencias según resultados futuros.

**G7:** Los candidatos se procesaron por reloj de decisión con mercado, H4 padre, source_event_id y generación ordinal de este estudio (NO generación autentificada del runtime). Se censuran terminales posteriores al instante de decisión, y se conservan UNKNOWN sin fabricarle resolución temporal. 31 estados PROVISIONAL **no autorizan rearm, entrada o capital**. Los 108 WAIT significan que la regla estricta no pudo probar la terminación causal de todas las tesis históricas anteriores; no significan que fuesen 108 pérdidas ni que todas las propuestas fueran fallidas.

## Custodia de artefactos de esta reproducción

**AUDUSD**
- Artifact ID: **12005455369**
- Archivo: vt08-g2-g7-real-atlas-AUDUSD-2c23ddd72df6238e2ca3331ed3350e131ae4a5bb
- SHA256 ZIP reportado por GitHub: **96f0766323ad6aae2d5c84e06b44c88f76da0bba0ee59a45f0dfdc44e1dd91eb**

**USDJPY**
- Artifact ID: **12005455361**
- Archivo: vt08-g2-g7-real-atlas-USDJPY-2c23ddd72df6238e2ca3331ed3350e131ae4a5bb
- SHA256 ZIP reportado por GitHub: **7a1dca533c9e75e6e513795a55ac316a21e9139c9fa82fec84d61bb6f0536f95**

Los dos tienen estado no vencido observado y caducidad declarada **2027-01-13T20:29:10Z**, no constituyen bóveda perpetua. Cada artefacto incluye resumen JSON, ledger JSONL, commit SHA y sumas SHA256 internas. Los originales Atlas son otra custodia temporal, issue [#837](https://github.com/mezas3238-hue/qore-core/issues/837).

## Calidad, límites y pendientes

- Primer CI detuvo por import no usado; segundo CI encontró que el fixture adversarial cerraba exactamente sobre el borde de C0, mientras la V3 congelada exige reclaim estrictamente adentro. Solo se cambió el **fixture sintético**; los precios reales y la lógica original quedaron intactos. La repetición pasó 16 tests y ambos mercados reales.
- Esta evidencia es desarrollo **2024–2026 ya explorado**, no OOS virgen, no backtest económico, y no justifica recalibrar V3. No se estimaron Profit Factor, Sharpe, Sortino, capital, DD patrimonial, fill o órdenes.
- Falta G2 con inventario PIT completo de old CRTH/CRTL y adjudicación de 36 rivales (incluidos 14 opuestos); G7 necesita investigación independiente de 108 WAIT y ledger persistente auténtico. No reinterpretar UNKNOWN como terminal.
- Faltan revisor metodológico distinto del implementador, firmas por siete artículos G1–G7 [issue #976](https://github.com/mezas3238-hue/qore-core/issues/976), 48 blind cases G-M2, validación externa G-M3, G-M4 y cinco UNKNOWN, y Gates económicos globales con nueva fuente BID/ASK y OOS verdaderamente virgen.
- **VT08 sizing PROHIBIDO** incluso 1 lote o R ficticia. Capital y volumen son exclusivamente responsabilidad CIBO/QORE Risk. BTCUSD congelado; PR DRAFT, sin merge, demo/live, broker, VPS ni órdenes.

**Dictamen:** G-M1…G-M4 PARTIAL, G-M5 NOT ISSUED y GLOBAL NOT CERTIFIED. Los tests de ingeniería no emiten certificado.
