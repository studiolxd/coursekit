# Informe de mejoras de coursekit

Nota de trabajo (1 de noviembre de 2026). Revisión rápida del paquete en su estado actual: `0.7.0` en
`pyproject.toml`, 80 módulos en `src/coursekit`, unos 27 000 líneas de Python, 61 ficheros de tests con
más de 700 pruebas, 9 ficheros de documentación por idioma. Las propuestas están ordenadas por lo que
más conviene atacar primero. Cada una cabe en un cambio pequeño salvo donde se indica.

## 1. Incoherencias visibles (arreglo inmediato)

- **La versión del README no es la del paquete.** `README.md › Status` dice "Early development (`0.3`)"
  y `pyproject.toml` lleva `0.7.0`. Los límites conocidos del backend creator
  (`docs/*/08-assembly-and-delivery.md`) dicen "when this version (0.2) was written". Conviene que esas
  frases no lleven número, o que un test (`tests/test_docs.py`) compare el número con el de `pyproject.toml`.
- **No hay `CHANGELOG`.** El estado del proyecto vive en una lista de "New:" del README que ya ocupa
  veinte párrafos largos y que nadie podrá leer entera. Propuesta: `CHANGELOG.md` por versión (en
  inglés, con su copia `.es`), y que el README se quede con cuatro bloques cortos: sólido, nuevo, en
  curso, pendiente. Los párrafos actuales de "New" pasan al changelog de la versión en que entraron.
- **Diferencia sin commit muy grande.** Hay 48 ficheros tocados y más de 800 líneas sin confirmar que
  mezclan varios temas (banco de preguntas, galería, entrega, reglas, player html). Cuanto antes se
  partan en commits por tema, menos cuesta revisarlos y menos riesgo de perder algo.

## 2. Estructura del código

- **`commands.py` (1 720 líneas) y `cli.py` concentran el despacho de todos los comandos.** Cada
  comando nuevo crece el mismo fichero. Propuesta: un registro de comandos donde cada módulo declare
  su subcomando (`register(subparsers)`), y `cli.py` se limite a recorrer el registro. Permite además
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

## 3. Calidad y pruebas

- **Sin comprobación de tipos.** Ruff pasa (`E, F, I, UP, B`) pero no hay `mypy` ni `pyright`. Con 27 000
  líneas que mueven diccionarios de YAML, el tipado de los puntos de entrada (`course.py`, `config.py`,
  `assemble.py`, `verify.py`) con `TypedDict` o `dataclass` evitaría una clase entera de fallos.
  Propuesta: `pyright` en modo `basic` solo sobre `config.py`, `course.py`, `i18n.py` y `paths.py`, e ir
  ampliando.
- **Reglas de ruff que faltan.** Añadir `SIM`, `RET`, `PTH` (uso de `pathlib` en vez de `os.path`) y
  `PERF`. Cada una se añade con `--fix` y un commit propio.
- **Tiempo de la suite.** No hay marcador de pruebas lentas. Las que levantan navegador, ffmpeg o un
  servidor deberían llevar `@pytest.mark.slow` y quedar fuera del `pytest -q` habitual (CI las corre
  todas). Hoy el `real_defaults` es el único marcador.
- **Los fixtures de proyecto se construyen a mano en cada test.** Un `conftest.py` con un fixture
  `project(tmp_path)` que ejecute `init` y escriba un curso mínimo ("contraseñas robustas", cliente
  ACME) ahorraría código en casi todos los ficheros de `tests/`.

## 4. Experiencia de uso

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

## 5. Dependencias y distribución

- **`markitdown[pdf,docx,pptx,xlsx,xls,outlook]` es la dependencia más pesada** y solo la usa `brief`.
  Moverla a un extra `brief` (o `docs`) deja la instalación base mucho más ligera; `doctor` pide el
  extra cuando haga falta.
- **`opencv-python` fijado a `<5`** por rapidocr: anotar en `docs/*/09-troubleshooting.md` qué pasa si
  el usuario tiene otro OpenCV instalado, y comprobarlo en `doctor`.
- **Python 3.14** queda fuera (`<3.14`). Revisar qué lo impide (probablemente `rapidocr`/`onnxruntime`)
  y abrir la ventana cuando publiquen ruedas.

## 6. Documentación

- **`docs/` suma más de 6 000 líneas por idioma** y `08-assembly-and-delivery.md` mezcla ensamblado,
  entrega, banco de preguntas, revisión de cliente y límites de creator. Partirlo en
  `08-assembly.md`, `09-delivery.md` (con el banco de preguntas) y `10-client-review.md`, y renumerar
  `troubleshooting`. `tests/test_docs.py` ya protege los enlaces.
- **Las notas de `dev-notes/`** (`assessment-delivery`, `capture`, `field-feedback`, `gemini-tts`,
  `pedagogical-criteria`, `research`, `terminal-capture`, `video`) corresponden a funciones que el
  README ya da por publicadas. Según las reglas del repositorio, lo que ya está en `docs/` debe
  borrarse de aquí; conviene repasar cada una y dejar solo las decisiones abiertas.

## Orden propuesto

1. Versión y changelog (sección 1): media hora, sin riesgo.
2. Partir la diferencia pendiente en commits por tema.
3. Extra `brief` para `markitdown` y `doctor` con extras (secciones 4 y 5).
4. Subpaquetes `capture/`, `media/`, `video/` y registro de comandos (sección 2).
5. Marcadores de pruebas lentas y fixture común (sección 3).
6. Tipado gradual con `pyright` y reglas nuevas de ruff.
7. Reparto de `08-assembly-and-delivery.md` y limpieza de `dev-notes/`.
