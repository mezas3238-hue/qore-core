# QORE-alpha V1 — FUENTE 2022/2023 RECUPERADA PARA LOS 5 MERCADOS **M5** (G0)

**Auditoría GitHub del 12-oct-2026.** Evidencia ejecutada, no simple inferencia de memoria: [run #38259002749](https://github.com/mezas3238-hue/qore-core/actions/runs/38259002749) **SUCCESS 5/5** con source code SHA `c359fddb0628d351427c4f7c8245fc1b7ec6327c`. El laboratorio lee exclusivamente GitHub Actions originales, no usa nuevas claves, ni abre el VPS/LIVE, ni accede al holdout 7Y sellado. En cada uno comprueba el `symbol-consumption-manifest.json`, los manifiestos año `2022.json`, `2023.json`, y las huellas SHA256 de los **`RAW_M5_LEDGER/2022.jsonl` y `RAW_M5_LEDGER/2023.jsonl` completos** frente al manifiesto original.

| Mercado | Run fuente ORIGINAL | Artefacto fuente original | Original M5 2022 | Original M5 2023 | SHA256 original raw M5 2022 |
|---|---:|---:|---:|---:|---|
| EURJPY | 38193802541 | 11723592292 | 74.529 | 74.510 | `5eb3da3b30858873d3264a49c01990e1073d271802aad5bd78dbdc421dcb7767` |
| USDCHF | 38193802541 | 11722633876 | 74.466 | 74.431 | `b9b7f49997ce25b926a1aac205ea2221b8be657a9c0b4e399aabe414f9c1ba74` |
| NZDUSD | 38193802541 | 11723435593 | 74.524 | 74.431 | `37e841d85af830bfd2db0c697ca4804ff4019ed1557746a91744b5a7c5e9f107` |
| CADJPY | 38193802541 | 11726771423 | 74.526 | 74.495 | `2bbd280bf576e091e3e14f4ec7b2c2465aaf5d71ce2e2787950f954f52093566` |
| USDCAD | 35166210458 | 10475972108 | 74.534 | 74.455 | `9a91cbbd883ba3b204c1b6da60097f6938c3f0157a0e2beaea1e0ea0cb582794` |

Fuente física M5 2022 para los 5: `2022-01-02T23:00:00Z` primera barra hasta `2022-12-30T21:55:00Z` última, coherente con días de trading FX. Ambas particiones 2022/2023 fueron comprobadas y no contienen conflicto SHA contra original. Integridad declarada original `CLEAN_PROVIDER_PAYLOAD`; no equivale a garantía sin agujeros respecto a calendario/session FX. La API de GitHub devuelve los originales aún no expirados a fecha de prueba.

**Recibos de la comprobación independiente** (ZIP con resumen y SHA, no precios, retención 90 días):
- EURJPY `11751911066`
- USDCHF `11751867153`
- NZDUSD `11751426987`
- CADJPY `11751607263`
- USDCAD `11751112747`

### Qué desbloquea / NO desbloquea

- **SÍ**: la afirmación vieja "enero 2022 no existe en GitHub" queda **CORREGIDA** para los 5 mercados y temporalidad M5. CIBO antes sólo contenía USDCAD en los 12 originales, pero QORE Native añadió EURJPY, USDCHF, NZDUSD y CADJPY a las 33 fuentes originales el 12-oct-2026.
- **SÍ**: de cada grupo de **3 M5 consecutivas en 15 minutos** con el mismo proveedor es factible reconstruir M15 (cuando todas existen) y verificar contra otra fuente; aún no ejecutado para estas particiones, NO promover M15 completed.
- **NO**: el M5 **no se puede convertir causal y fielmente a velas M3**. El dataset M3 de los cinco sigue arrancando 2023-09-24. No rellenar 2022 con M3 derivado de M5, interpolación de cierres ni simple sustitución M5 por M3 (implicaría alterar el preregistro congelado de 96).
- **NO**: no están comprobados BID/ASK históricos reales, comisiones ni slippage del periodo de los cinco.
- **NO**: no hay resultados de walkforward 96×3 del programa QORE-alpha v1; **0 variantes evaluadas económicamente bajo este protocolo**.

**Estado correcto:** `G0_2022_2023_NATIVE_M5_5_OF_5_SHA_VERIFIED_M3_AND_BIDASK_BLOCKED`. Próxima dependencia necesaria para ejecutar EXACTAMENTE el programa preregistrado: encontrar **fuente M3 genuina o M1 genuino con suficiente granularidad desde enero 2022** por 5 pares, en archivo DE INVESTIGACIÓN AUTORIZADO (NO el holdout 7Y sellado) y ejecución BID/ASK, después origen/hash/timestamp y split inmutable. Credenciales cTrader DEMO no son imprescindibles para M5 pues los archivos 2022 ya existen, pero M3/M1 2022 aún no está demostrado disponible sin ellas.
