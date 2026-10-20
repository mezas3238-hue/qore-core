# VT08 R28 — Clasificación de cobertura M3 incompleta frente a M15 (2026-10-20)

## Alcance y método
Se reabrieron los diez ZIP RAW originales recuperados en R26. Para cada barra M15 del universo R27, se buscaron cinco barras M3 exactamente en aperturas M15 + [0,3,6,9,12] minutos UTC. Si faltaba alguna, se clasificó de forma exclusiva: (1) fuera de límites de cobertura M3; (2) con alguna apertura en sábado/domingo UTC; (3) dentro de límites pero con una o más aperturas M3 ausentes. **Esto no determina todavía la causa del gap ni acredita ninguna operación**.

| Mercado | Intervalos incompletos | Dentro de límites M3, slots ausentes | Límite fin de semana | Fuera de límites |
|---|---:|---:|---:|---:|
| EURJPY | 205 | 191 | 14 | 0 |
| USDCHF | 585 | 497 | 88 | 0 |
| NZDUSD | 544 | 506 | 38 | 0 |
| CADJPY | 291 | 257 | 34 | 0 |
| USDCAD | 644 | 570 | 74 | 0 |
| **Total** | **2269** | **2021** | **248** | **0** |

## Interpretación
Los 370210 grupos completos M3→M15 siguen con 0 mismatches OHLC (R27). Los 2269 intervalos restantes NO son comparables con agregación completa. Un hueco M3 puede obedecer a actividad de mercado, sesiones, diferencias de extracción o pérdida de datos; clasificar la causa requiere revisar timestamps vecinos, políticas del broker y otros periodos. La clasificación fin de semana usa UTC y no necesariamente la sesión local del broker. No rellenar huecos con velas sintéticas para certificar.

## Evidencia reproducible
Script local `vt08_r28_gap_audit.py`, JSON `vt08_r28_gap_classification_2026-10-20.json`, calculados contra los ZIP de R26. No se suben barras RAW licenciadas. Próxima tarea: aislar huecos que intersectan ventanas causales de los 2657 candidatos y revisar 316 breaches del corrected low R25 sin fuga de futuro.

## Gobernanza
VT08_NOT_CERTIFIED; REAL_COGNITIVE_ADMISSIONS=0; BROKER_FILLS=0; AUTHENTIC_INDEPENDENT_AB_SIGNOFFS=0. Holdout 7Y y LIVE/DEMO/VPS intactos; QORE-alpha excluido.