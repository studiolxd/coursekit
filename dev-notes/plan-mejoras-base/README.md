# Línea base de las mejoras (fase 0)

Medido el 2 de noviembre de 2026 sobre `main` (`a813564`) con el changelog añadido, en macOS, Python 3.12.

| Medida | Valor | Fichero |
|---|---|---|
| Tests recogidos | 814 | `tests.txt` |
| Ayudas de la CLI | 46 (comando raíz y subcomandos), en `es` y `en` | `help-es.txt`, `help-en.txt` |
| Arranque de `coursekit --version` | 0,20 s en caliente | `startup.txt` |
| Importación de `coursekit.cli` | 122 ms, de ellos 53 ms de `openpyxl` (por `approve` y `localdesign`) | `importtime.txt` |
| Entorno con el grupo `dev` | 300 MB; `onnxruntime` 111 MB, `pandas` 40 MB y `numpy` 24 MB llegan por `markitdown` | `size.txt` |

Las duraciones de los tests no se midieron: la suite completa la lanza el mantenedor.

Se compara con estos ficheros al cerrar cada fase. La carpeta se borra con el plan.
