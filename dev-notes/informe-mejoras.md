# Informe de mejoras de coursekit

Nota de trabajo (1 de noviembre de 2026). Revisión rápida del paquete en su estado actual: `0.7.0` en
`pyproject.toml`, 80 módulos en `src/coursekit`, unos 27 000 líneas de Python, 61 ficheros de tests con
más de 700 pruebas, 9 ficheros de documentación por idioma. Las propuestas están ordenadas por lo que
más conviene atacar primero. Cada una cabe en un cambio pequeño salvo donde se indica.

Cómo se aborda, por fases y con la validación de cada una: [plan de mejoras](plan-mejoras.md).

Lo que se va haciendo se tacha y pasa a la sección [Hecho](#hecho), al final, con la fecha y cómo se resolvió.

## 1. Estructura del código

Nada pendiente: ver [Hecho](#hecho).

## 2. Calidad y pruebas

- **Tiempo de la suite.** Las pruebas que necesitan navegador, ffmpeg, OpenCV o pyte ya se saltan solas cuando falta
  la herramienta, y la CI las corre en un trabajo aparte. Un marcador `slow` solo si una medida de duraciones lo pide.
## 3. Experiencia de uso

- **`--help` largo y en dos idiomas.** 59 ficheros de mensajes y un `cli.py` con más de 140 cadenas.
  Falta un `coursekit help <comando>` que muestre también el fragmento de `docs/<lang>/03-commands.md`
  del comando, y un `--json` en los comandos de consulta (`status`, `verify`, `doctor`, `media check`)
  para que los agentes lean la salida sin analizar texto.
- **Salida de `verify` sin niveles.** Las advertencias han crecido mucho (lenguaje inclusivo, carga
  cognitiva, crosshairs, barajado…). Un `--only` / `--ignore` por familia de regla y un resumen por
  unidad al final harían la salida manejable en cursos de diez unidades.
## 4. Dependencias y distribución

- **El extra `capture` no se instala con Python 3.13.** Todas las versiones de `rapidocr-onnxruntime` exigen Python
  anterior a 3.13, y el paquete admite 3.13. Es también lo que impide abrir 3.14. Su sucesora es `rapidocr` (3.x, admite
  3.8 a 3.x), con otra forma de importar y de devolver los resultados: hay que cambiar `redact._rapidocr` y probar el OCR
  con capturas reales antes de publicarlo. Mientras tanto, el extra `capture` necesita Python 3.12.

## 5. Documentación

- **`docs/` suma más de 6 000 líneas por idioma** y `08-assembly-and-delivery.md` mezcla ensamblado,
  entrega, banco de preguntas, revisión de cliente y límites de creator. Partirlo en
  `08-assembly.md`, `09-delivery.md` (con el banco de preguntas) y `10-client-review.md`, y renumerar
  `troubleshooting`. `tests/test_docs.py` ya protege los enlaces.
- **Las notas de `dev-notes/`** (`assessment-delivery`, `capture`, `field-feedback`, `gemini-tts`,
  `pedagogical-criteria`, `research`, `terminal-capture`, `video`) corresponden a funciones que el
  README ya da por publicadas. Según las reglas del repositorio, lo que ya está en `docs/` debe
  borrarse de aquí; conviene repasar cada una y dejar solo las decisiones abiertas.

## Orden propuesto

Sigue las fases del [plan](plan-mejoras.md).

1. Marcador de pruebas lentas, si lo pide una medida de duraciones de la suite completa (sección 2).
2. Ampliar `mypy` a más módulos, uno a uno (sección 2).
3. `--json`, `verify --only` / `--ignore` y `help <comando>` (sección 3; fase 5).
4. Reparto de `08-assembly-and-delivery.md` y limpieza de `dev-notes/` (sección 5; fase 6).
5. OCR de `capture` con `rapidocr` para Python 3.13 y 3.14 (sección 4; fuera del plan, necesita probarse con capturas reales).

## Hecho

### Incoherencias visibles (arreglo inmediato)

- ~~**La versión del README no es la del paquete.**~~ Hecho el 2 de noviembre de 2026. El estado del README, los límites
  de creator y `CONTRIBUTING` ya no llevan número; solo el encabezado de cada README, y `tests/test_docs.py` comprueba
  que coincide con `pyproject.toml`.
- ~~**No hay `CHANGELOG`.**~~ Hecho el 2 de noviembre de 2026. `CHANGELOG.md` y `CHANGELOG.es.md` con todas las
  versiones y un apartado sin publicar; el estado del README en cinco bloques cortos (asentado, nuevo, en desarrollo,
  por demostrar, todavía no). `CONTRIBUTING` y `AGENTS.md` piden su línea en cada cambio, y un test comprueba que los
  dos changelogs listan las mismas versiones y la actual.
- ~~**Diferencia sin commit muy grande.**~~ Hecho el 1 de noviembre de 2026: confirmada y subida en un solo commit
  (`a813564`), sin partir por temas.

### Dependencias y diagnóstico (fase 1 del plan)

- ~~**`markitdown` es la dependencia más pesada.**~~ Hecho el 2 de noviembre de 2026: extra `docs`; la instalación base pasa de
  48 paquetes a 7. `brief` y `brand` avisan con el comando, y `doctor` lo pide solo si hay documentos que convertir.
- ~~**`doctor` no comprueba los extras.**~~ Hecho el 2 de noviembre de 2026: `coursekit/extras.py` da el comando que conserva
  los extras instalados, y todos los avisos de extras lo usan.
- ~~**`opencv-python` fijado a `<5`.**~~ Hecho el 2 de noviembre de 2026: `doctor` avisa de varios OpenCV instalados y la
  solución de problemas lo explica.
- ~~**Actualización de ejemplos de configuración.**~~ Hecho el 2 de noviembre de 2026 como `coursekit config --check` (una
  opción, porque `config` ya recibe el nombre de la configuración como primer argumento).

### Pruebas (fase 2 del plan)

- ~~**Los fixtures de proyecto se construyen a mano en cada test.**~~ Hecho el 2 de noviembre de 2026: `make_project` y
  `make_course` en `tests/conftest.py`; doce fixtures reescritos sobre ellos, con los mismos 821 tests recogidos. Al
  provocar fallos para comprobarlos salió un hueco: nada probaba que el redactor retoma una unidad a medio escribir
  (`launch.units_to_do`); ya tiene su test.

### Calidad estática (fase 3 del plan)

- ~~**Reglas de ruff que faltan.**~~ Hecho el 2 de noviembre de 2026: `SIM` (sin `SIM905`), `RET` y `PTH`. `PERF` se
  descartó: solo pedía `extend` en bucles que construyen informes de pocas líneas, a costa de leerse peor.
- ~~**Sin comprobación de tipos.**~~ Hecho el 2 de noviembre de 2026 con `mypy` en lugar de `pyright` (el paquete de
  `pyright` descarga Node en la caché del usuario): siete módulos con todas las funciones anotadas (`commands`, `config`,
  `course`, `i18n`, `paths`, `status`, `sync`), un trabajo de CI que bloquea, y `files` en `pyproject.toml` para ampliar.
  Los quince avisos que dio eran variables reutilizadas con otro tipo y funciones sin anotar; ninguno era un fallo.

### Estructura del código (fase 4 del plan)

- ~~**`commands.py` declara 38 subcomandos en un solo `register(sub)`.**~~ Hecho el 2 de noviembre de 2026: paquete
  `commands/` con un módulo por grupo (`course`, `brief`, `roles`, `media`, `assembly`, `common`), cada uno cargado solo cuando
  se ejecuta su comando; la CLI atrapa una clase base, `errors.CoursekitError`, en lugar de importar veintiún módulos para
  conocer sus errores. `openpyxl` se carga solo al escribir un Excel. La importación de la CLI pasa de unos 100 ms a 41 ms y
  `coursekit --version` de 0,20 s a 0,11 s; la ayuda de los 46 comandos es idéntica en los dos idiomas.
- ~~**Familia `capture_*`, `media*` y `video*`.**~~ Hecho el 2 de noviembre de 2026: subpaquetes `capture/`, `media/` y
  `video/`, sin alias para los nombres antiguos.
- ~~**Llamadas a programas externos repartidas.**~~ Hecho el 2 de noviembre de 2026 con alcance distinto al propuesto: los
  avisos de programa que falta ya eran coherentes y se dejan en cada módulo; `external.run` resuelve lo que sí fallaba, quince
  llamadas que leían la salida con la codificación del sistema (cp1252 en Windows).
- ~~**Peticiones HTTP sin cliente común.**~~ Hecho el 2 de noviembre de 2026: `http.py` con `request` y `download`; los
  reintentos solo donde el módulo los pide (la búsqueda web), nunca por defecto.
