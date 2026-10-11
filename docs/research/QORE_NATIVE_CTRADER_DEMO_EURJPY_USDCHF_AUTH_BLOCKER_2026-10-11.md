# QORE NATIVE — fallo verificable de credenciales en captura cTrader DEMO EURJPY/USDCHF

Fecha: 2026-10-11. Alcance: [PR #800](https://github.com/mezas3238-hue/qore-core/pull/800). Prerregistro anterior a captura commit `2f2af1b26ec7bbd329a287ee3d0592442ee241aa`. Fuente solicitada: cTrader DEMO, dos símbolos EURJPY y USDCHF, M5 provider-native, ventana 2016-09-17 a 2026-09-17 exclusive. **No PnL, VPS, MT5, órdenes o cuentas live.**

## Evidencia de GitHub Actions

- [Run #38172092086](https://github.com/mezas3238-hue/qore-core/actions/runs/38172092086), código commit `c5854f6c5e18b4e5bde52b82eea4d5e1349adef3`.
- `frozen_contract` **SUCCESS**: pruebas, import del runtime existente, ventana y símbolos fijos.
- `download_m5 (EURJPY)`, job **114566713685** **FAILED** al verificar cuenta DEMO.
- `download_m5 (USDCHF)`, job **114566713704** **FAILED** en el mismo paso.
- Causa literal en los dos logs: `CTraderDemoAccountDiscoveryError: cTrader access token invalid and refresh failed`.
- La etapa `Download EURJPY or USDCHF cTrader DEMO provider-native M5` figura **SKIPPED** en ambos trabajos. No se ha iniciado la lectura de velas; ausencia de captura usable, no afirmar retained M5 ni cobertura 10Y.
- Si existen artifacts de diagnóstico `git-sha.txt`, **no** son datasets. El manifiesto M5 no fue escrito; no importarlos a QORE Native.
- El fallo no significa que EURJPY o USDCHF falten en IC Markets: la API no llegó a resolución de símbolos. Tampoco prueba que el código de descarga M5 sea correcto contra esos símbolos; solo pasaron los tests de contrato.

## Desbloqueo necesario — operador, sin compartir secretos en issues/chat

Conforme a documentación oficial https://help.ctrader.com/open-api/account-authentication/ :

1. **Reautorizar** la aplicación Open API de QORE con el cTrader ID propietario y **la cuenta cTrader DEMO exacta**. Elegir solamente el scope `accounts` (read-only), no `trading`.
2. Obtener un par nuevo `accessToken` y `refreshToken` por el flujo de autorización oficial, registrando en privado el resultado. Los refresh tokens anteriores pueden haber sido invalidados por reautorización o rotación; no reintentarlos indefinidamente.
3. Actualizar **GitHub repository Settings → Secrets and variables → Actions**: `QORE_CTRADER_ACCESS_TOKEN`, `QORE_CTRADER_REFRESH_TOKEN`, y si procede `QORE_CTRADER_CLIENT_ID` / `QORE_CTRADER_CLIENT_SECRET`. El workflow admite alternativamente los nombres `QORE_CTRADER_DEMO_*`. Nunca subir valores reales a comentarios, commit o chat.
4. Verificar que `QORE_CTRADER_DEMO_ACCOUNT_ID` corresponda exactamente a la DEMO descubierta, o dejarlo vacío para que el workflow determine una sola cuenta de tipo `isLive=false`. No introducir IDs de cuenta LIVE.
5. Tras restaurar secretos, **volver a ejecutar** [workflow #38172092086](https://github.com/mezas3238-hue/qore-core/actions/runs/38172092086) desde GitHub Actions (Re-run all jobs). Una modificación de secrets no desencadena por sí sola un nuevo push.
6. Comprobar jobs **SUCCESS**, presencia de dos artifacts M5, símbolo/ID exacto, timestamps UTC, primeras/últimas velas realmente observadas, manifests y SHA256 del ledger. Documentar si el proveedor ofrece menos de 10 años.

**GATE:** `DOWNLOAD_BLOCKED_AUTHENTICATION`, `DATASET_EURJPY_NOT_ACQUIRED`, `DATASET_USDCHF_NOT_ACQUIRED`. NO declarar problema de datos, edge, OOS ni certificación. La fuente de doce mercados [Atlas 10Y run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) sigue intacta.

Nota técnica: documentación cTrader advierte que el refresh token antiguo se invalida al rotarlo; si otra ejecución ha renovado los tokens sin actualizar los secretos almacenados, el siguiente workflow observará justamente credenciales obsoletas. Verificar primero eso, sin asumir que sea la causa única.
