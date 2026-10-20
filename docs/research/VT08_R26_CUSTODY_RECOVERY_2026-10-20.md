# VT08 R26 — Recuperación verificable de originales M15/M3 (2026-10-20)

## Resultado real
Descargados los diez artifacts originales de GitHub Actions (M15 run 35934924907, M3 run 35941643396). Se verificaron 10/10 hashes SHA256 de ZIP contra `digest` de la API de GitHub y 10/10 ZIP con `ZipFile.testzip()==None`; se calcularon también SHA256 de cada archivo interno. Manifest JSON creado localmente en entorno de trabajo `vt08_r26_custody_manifest_2026-10-20.json` (no contiene datos de mercado). **No afirmar backup privado permanente ni restauración desde destino externo**: archivos temporales de sesión. Issue #1002 abierta.

## Digest por artifact
| Tipo | Mercado | Artifact ID | SHA256 ZIP |
|---|---|---:|---|
| M15 | EURJPY | 10782678476 | 907fa535a463d7d91c8274eb978982afd7ad3f6087b9c95b9faf7011d1d1a9bd |
| M15 | NZDUSD | 10782895998 | dc4d590f13578dc1d590ba549b17337737a1343661e8e90caf27fd2507582a25 |
| M15 | CADJPY | 10782906805 | 8893c2221abcb25b34941b2b428a54950685c63a3d325ac934469a8df0a9f37d |
| M15 | USDCAD | 10782946642 | 30fa572a9c912a3fcc0aee8076a0917d3603c5a026e7ec20943297ce5c44c483 |
| M15 | USDCHF | 10783200186 | 410ad2e4ab22e2e37ea5caa6dca6805759ef7e860b77d62041aef0292aaa1859 |
| M3 | USDCHF | 10784733648 | bf790b9185cc4a861d648cf100a90216ef690f485360328cb7be723763633bde |
| M3 | EURJPY | 10785121839 | ee3df4ccdf81ffbf0307072965c7e2fd53c83ffd8fd15119b3bba78363ba5aa1 |
| M3 | NZDUSD | 10785212444 | 8a4a5f51601d80f6d6d87fb5241b81d4256625990731f376e95ff742f7d792b8 |
| M3 | USDCAD | 10785501601 | 90d69f8c48c0f084faee3b670a9778dd53148dcc2868284b8f2dbb573681ea32 |
| M3 | CADJPY | 10785575630 | 04265cf5fc359e2e141e314586f57aac9a3ce922f79222207ba37557ad59a0f6 |

## Siguiente paso P0
Almacenar en bucket privado autorizado y cifrado, verificar hashes contra este manifiesto, probar restauración y registrar evidencia de custodia. No subir ZIP ni JSON de datos licenciados al repositorio. No tocar holdout 7Y ni ejecutar live. La metodología y cognitiva siguen NO_CERTIFIED. QORE-alpha excluido.