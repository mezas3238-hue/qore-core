# QORE Native G1 — concordancia histórica G0 ↔ BID/ASK proveedor G1 (12 originales), 2026-10-12

**Objetivo preregistrado antes de ejecutar auditoría CI:** resolver la *identidad declarada por proveedor* de los 12 contratos originales CIBO M5 frente al proveedor actual IC Markets DEMO, SIN afirmar identidad de cuenta, equivalencia comercial o precio de ejecución. Se usarán archivos originales existentes sin contacto con broker ni acceso a órdenes.

## Testigos SHA congelados antes de lectura

- **G0 Atlas original** [run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), código `ab782b8e9f890f86a2b6500070f0556b4b685e3d`, aggregate ZIP [#10476615509](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458/artifacts/10476615509), SHA256 ZIP `aa7aef2222ddd89536090110cc03ed4a9f2e0ca8e8e50d5ba40912cec0cd9ba7`, archivo `ten-year-consumption-index.json` con identidad símbolo, ID proveedor, `digits` y `pip_position` en particiones históricas 2016–2026.
- **G1 IC Markets** original cTrader DEMO quote source 29 [run #38283737706](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706) [#11762222336](https://github.com/mezas3238-hue/qore-core/actions/runs/38283737706/artifacts/11762222336), ZIP SHA `be123f91e2069390e3bb44f9ce8b9398e3216b9ce483b7441f7f2aebb918f1c0`;
  SP500→US500 [#11761419260](https://github.com/mezas3238-hue/qore-core/actions/runs/38282585181/artifacts/11761419260), SHA `a1fa1a7c22062f2b20970c5a8540634f3fc3ab0a165f136dce97aa3cbe26f5f5`;
  XAGUSD [#11761892358](https://github.com/mezas3238-hue/qore-core/actions/runs/38282585181/artifacts/11761892358), SHA `aaa32406dd4e2a5cc826da47e088f645f3963b88735d4ced4d7f366e5f00843e`;
  NAS100→USTEC [#11762668603](https://github.com/mezas3238-hue/qore-core/actions/runs/38285063753/artifacts/11762668603), SHA `402831fcf2ba60070bdcf92671a1470838bda44208bf40ff373d95dc066c5da4`.
- **G1 actual detail USTEC solamente** [catalog preflight #11762018327](https://github.com/mezas3238-hue/qore-core/actions/runs/38284304699/artifacts/11762018327), ZIP SHA `7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e`; aporta digits, pipPosition, lotSize, minVolume/stepVolume actuales (no históricos originales).

## Regla de decisión estricta

Comparar **12 símbolos originales y sus 11 particiones** G0, cada `provider_symbol`, `provider_symbol_id`, `digits` y `pip_position` constantes, integridad y estado `CLEAN_PROVIDER_PAYLOAD`; cruzar con `provider_symbol/provider_symbol_id` encontrados en artefactos G1 inmutables. Resultado individual:
- `PROVIDER_NAME_AND_NUMERIC_ID_CONCORDANT` si ambos campos son exactamente iguales.
- `PROVIDER_IDENTITY_MISMATCH` si difieren; fallar CI.
- `CANNOT_ATTEST` si falta fuente; fallar CI.

**Importante:** los IDs cTrader pueden ser propios de una cuenta/bróker y reutilizarse, y coincidencia de símbolo+ID **NO prueba que cuenta histórica G0 sea la misma que G1**, ni contratos equivalentes, lote, value por punto, spread ejecutable, tarifa, swap, horario o volumen mínimo. La etiqueta sólo resuelve concordancia de identidad, no el Gate contractual P0 #857. Incluso si USTEC actual coincide `digits=2,pipPosition=1` con G0, eso NO demuestra equivalencia histórica; no promover NAS100→USTEC o SP500→US500 a `EXACT_CONTRACT`.

Rechazar campos de cuenta/tokens o prices raw en salida Git. El artifact de CI incluirá exclusivamente metadata con SHA, 12 filas, comparación parcial de USTEC y blocker list. **No corre requests cTrader, ni backtest, ni historial BID/ASK continuo**. Se mantiene `BROKER_CONTRACT_EQUIVALENCE_BLOCKED`, `G1_HISTORICAL_NET_BLOCKED`, `TRADERS_CERTIFIED_0_OF_3`, E2/E3 231 sin edge positivo replicado; VPS/MT5/LIVE/CIBO/Shared/QDLE intactos.
