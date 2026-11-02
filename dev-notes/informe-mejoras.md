# Informe de mejoras de coursekit

Nota de trabajo (1 de noviembre de 2026). Revisión rápida del paquete en su estado actual: `0.7.0` en
`pyproject.toml`, 80 módulos en `src/coursekit`, unos 27 000 líneas de Python, 61 ficheros de tests con
más de 700 pruebas, 9 ficheros de documentación por idioma. Las propuestas están ordenadas por lo que
más conviene atacar primero. Cada una cabe en un cambio pequeño salvo donde se indica.

Cómo se aborda, por fases y con la validación de cada una: [plan de mejoras](plan-mejoras.md).

Lo que se va haciendo se tacha y pasa a la sección [Hecho](#hecho), al final, con la fecha y cómo se resolvió.

## 1. Estructura del código

- **`commands.py` (1 720 líneas) declara 38 subcomandos en un solo `register(sub)`.** Cada comando nuevo crece el
  mismo fichero, y al importarlo se cargan todos sus módulos (`openpyxl` incluido). Propuesta: partirlo en un módulo por
  grupo de comandos, cada uno con su `register`. Permite además
  cargar módulos pesados (`capture_*`, `video`, `exelearning`) solo cuando se invoca su comando, lo que
  acorta el arranque de `coursekit --help`.
- **Familia `capture_*` (seis módulos, más `capture.py` y `capture_session.py`, ~4 000 líneas).** Es ya
  un subpaquete de hecho: moverlo a `coursekit/capture/` con `macos.py`, `windows.py`, `x11.py`,
  `terminal.py`, `session.py`, `replay.py`, `stage.py`. Lo mismo para `media*` (`media`, `mediaaccess`,
  `mediacheck`, `mediagallery`, `mediaopt`, `mediascript`, `mediastyle`, `mediatools`) y para
  `video*`. Cambio mecánico, sin lógica; conviene hacerlo en un commit solo.
- **Llamadas a programas externos repartidas.** Hay 121 usos de `subprocess` o `shutil.which` en los
  módulos de primer nivel. Un módulo `coursekit/external.py` con una función por programa (ffmpeg,
  ffprobe, chrome, git, agente) centralizaría la búsqueda del binario, el mensaje de "no está instalado"
  (`doctor` ya lo hace a medias) y el tratamiento de la salida como UTF-8 en Windows, que hoy se
  repite a mano.
- **Peticiones HTTP sin cliente común.** 13 módulos hacen peticiones con `urllib`/`requests` cada uno a
  su manera (TTS, búsqueda web, Magnific, creator, PyPI). Un `http.py` con reintentos, tiempo de
  espera y el `User-Agent` del paquete, y una sola forma de leer las claves del `.env`.

## 2. Calidad y pruebas

- **Sin comprobación de tipos.** Ruff pasa (`E, F, I, UP, B`) pero no hay `mypy` ni `pyright`. Con 27 000
  líneas que mueven diccionarios de YAML, el tipado de los puntos de entrada (`course.py`, `config.py`,
  `assemble.py`, `verify.py`) con `TypedDict` o `dataclass` evitaría una clase entera de fallos.
  Propuesta: `pyright` en modo `basic` solo sobre `config.py`, `course.py`, `i18n.py` y `paths.py`, e ir
  ampliando.
- **Reglas de ruff que faltan.** Añadir `SIM`, `RET`, `PTH` (uso de `pathlib` en vez de `os.path`) y
  `PERF`. Cada una se añade con `--fix` y un commit propio.
- **Tiempo de la suite.** Las pruebas que necesitan navegador, ffmpeg, OpenCV o pyte ya se saltan solas cuando falta
  la herramienta, y la CI las corre en un trabajo aparte. Un marcador `slow` solo si una medida de duraciones lo pide.
- **Los fixtures de proyecto se construyen a mano en cada test.** Un `conftest.py` con un fixture
  `project(tmp_path)` que ejecute `init` y escriba un curso mínimo ("contraseñas robustas", cliente
  ACME) ahorraría código en casi todos los ficheros de `tests/`.

## 3. Experiencia de uso

- **`--help` largo y en dos idiomas.** 59 ficheros de mensajes y un `cli.py` con más de 140 cadenas.
  Falta un `coursekit help <comando>` que muestre también el fragmento de `docs/<lang>/03-commands.md`
  del comando, y un `--json` en los comandos de consulta (`status`, `verify`, `doctor`, `media check`)
  para que los agentes lean la salida sin analizar texto.
- **`doctor` no comprueba los extras.** Debería decir qué grupo de `pip install` falta para cada
  función (`capture`, `media`) y qué binarios de sistema faltan, con el comando exacto para esta
  plataforma.
- **Salida de `verify` sin niveles.** Las advertencias han crecido mucho (lenguaje inclusivo, carga
  cognitiva, crosshairs, barajado…). Un `--only` / `--ignore` por familia de regla y un resumen por
  unidad al final harían la salida manejable en cursos de diez unidades.
- **Actualización de ejemplos de configuración.** `init --update` refresca los
  `config/<name>.example.yaml`, pero no avisa de claves del proyecto que ya no existen en los defaults.
  Un `coursekit config check` que compare `config/*.yaml` con `defaults/*.yaml` cerraría el hueco.

## 4. Dependencias y distribución

- **`markitdown[pdf,docx,pptx,xlsx,xls,outlook]` es la dependencia más pesada** (trae `onnxruntime`, `pandas` y
  `numpy`) y solo la usan `brief` y `brand`. Moverla a un extra `docs` deja la instalación base mucho más ligera; `doctor` pide el
  extra cuando haga falta.
- **`opencv-python` fijado a `<5`** por rapidocr: anotar en `docs/*/09-troubleshooting.md` qué pasa si
  el usuario tiene otro OpenCV instalado, y comprobarlo en `doctor`.
- **Python 3.14** queda fuera (`<3.14`). Revisar qué lo impide (probablemente `rapidocr`/`onnxruntime`)
  y abrir la ventana cuando publiquen ruedas.

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

1. Extra `brief` para `markitdown` y `doctor` con extras (secciones 3 y 4).
2. Subpaquetes `capture/`, `media/`, `video/` y registro de comandos (sección 1).
3. Marcadores de pruebas lentas y fixture común (sección 2).
4. Tipado gradual con `pyright` y reglas nuevas de ruff (sección 2).
5. Reparto de `08-assembly-and-delivery.md` y limpieza de `dev-notes/` (sección 5).

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
