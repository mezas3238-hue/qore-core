# VT31 — PRE-REGISTRO original COG LONG + SHORT, LONDON/NYAM/NYPM EST/EDT, TraderLab native 1×/32×

Fecha 2026-10-15, escrito antes de implementar el módulo. Extiende PR #965 native Trader Lab Fast Forward sólo como **aceleración de cronología simulada**, sin afirmar 32× CPU ni usar retornos, PnL, número de operaciones, sizing, ni certificar el TraderLab Gate L3.

## Hipótesis falsable
- La versión ORIGINAL protegida `VT31CleanroomCognition` (blob SHA `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`) debe producir la MISMA decisión/razón/timestamp/traza hash en replay secuencial convencional 1× que al recorrer todas las observaciones cerradas con **`TraderLabFastForwardSchedule(acceleration_factor=32)`**.
- Expandir seis fuentes originales SHORT de PR #955 (Londres, NY AM, NY PM; enero EST y julio EDT) usando una reflexión **puramente geométrica de precios** `p' = 230 - p`: `open'=230-open`, `close'=230-close`, `high'=230-low`, `low'=230-high`; timestamps y corpus M1 inalterados, sin examinar el resultado o tocar código G3. La fuente antigua cash LOW80 se refleja en HIGH150. Pivote LOW96 se refleja HIGH134, confirmación CLOSE94 a LONG CLOSE136 (14 pt hasta DOL HIGH150). El reflejo de vela crea un contrafactual LONG verificable y paralelo al SHORT 80/96/94.
- Para cada `(mes∈{1,7}, sesión∈{LONDON,NY_AM,NYPM}, lado∈{SHORT,LONG})` ejecutar (1) caso MSS confirmado y (2) cambiar **solo el cierre de la última M1** SHORT94→97 / LONG136→133, sin modificar wick, por lo que no hay cierre más allá del pivote; esperado WAIT. Total exacto **24 situaciones** y dos motores COG por cada situación, sin reutilizar memoria entre casos.
- En cada caso, la evaluación justo antes de la última M1 debe ser WAIT. Cuando MSS confirmado esperar SHORT(DOL80/MSS96) o LONG(DOL150/MSS134), `structure_break_confirmed_at=último.closed_at`, `research_only=True`, `trade_authorized=False`. El caso de `close` contrafactual termina WAIT.
- Rechazo causal adicional: calendario duplicado, reordenado o con velas futuras, falta de identidad del método y distinta disponibilidad de mercado. No atribuir TTrades H1 09 a London o NYPM, ni asumir que este control valida doctrina de origen ICT. No decidir source fidelity usando PnL.

## Integridad y scope
PR #965 ya validó 12 SHORT y el constructor/`qualify_trader_lab_fast_forward` con carrier tipado **SINTÉTICO** y candidato genérico; este trabajo **no** cambia ese resultado ni convierte los carriers en NAS100 broker real. Ninguna necesidad de volver a escanear 3Y NAS100.

Proteger blobs G3 COG `d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, OPS `0ce9707314aecb71155de8b57044b6ec028847b2` y acta `e99c70b4e018d626fb620d9a21b9314a51abc36d` en CI. Si un caso falla, registrar el defecto y corregir código de test sólo si es bug, sin retocar G3 ni elegir datos ex post.

Salidas `all_24_parity`, escenarios y hashes, metodología/cognitiva completas `PENDIENTE`, `lab_l3_real=false`, `live=false`, `orders=0`, `sizing=0`, revisión dual G3 issue #897 abierta. No merge/OMS/LIVE/FundedNext/VPS. Un solo VT31.