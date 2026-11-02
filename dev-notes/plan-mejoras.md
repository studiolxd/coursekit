# Plan de mejoras de coursekit

Plan para abordar entero el [informe de mejoras](informe-mejoras.md), en fases ordenadas de menor a mayor riesgo. Cada fase dice
qué se hace, cómo se valida antes de darla por buena y qué decide el mantenedor. Nota de trabajo: se borra cuando el informe
quede vacío.

## Reglas comunes a todas las fases

- **Una fase, una rama y varios commits pequeños.** Cada commit deja `ruff` en verde y se puede revertir solo. La rama se
  fusiona cuando la CI pasa en Linux, macOS y Windows, incluidos los trabajos `capture` y `video-types`.
- **Antes y después.** Cada fase empieza midiendo lo que va a tocar y termina comparando con esa medida. Sin una medida que
  mejore o un test que falle antes y pase después, el cambio no entra.
- **La suite completa la lanzas tú o me pides que la lance.** Yo ejecuto `ruff` y solo los ficheros de test que toca el cambio.
- **Al cerrar la fase:** una línea en `CHANGELOG.md` y `CHANGELOG.es.md` si lo nota una persona, la documentación en `docs/en`
  y `docs/es` si cambia un comando o una opción, y el punto tachado y movido a "Hecho" en el informe.

## Correcciones al informe antes de empezar

Al preparar el plan salieron tres datos que el informe tenía mal. Se corrigen en él en la fase 0.

- **El registro de comandos ya existe a medias.** `commands.register(sub)` declara 38 subcomandos; `cli.py` solo declara
  `init`, `config`, `rules`, `agents` y `uninstall`. Lo que falta es partir `commands.py` y cargar cada módulo cuando hace falta.
- **`markitdown` no lo usa solo `brief`.** También lo usa `brand.py` para leer el libro de marca, y `doctor` ya lo comprueba.
- **Las pruebas pesadas ya se saltan solas.** Las de navegador, ffmpeg, OpenCV y pyte llevan `skipif` o `importorskip`, y la CI
  las corre en un trabajo aparte con el extra `capture`. El marcador `slow` solo hace falta si la medida dice que la suite base
  es lenta.

## Fase 0. Línea base (sin cambios de código)

**Qué se hace.** Se mide el estado actual y se guardan los resultados en `dev-notes/plan-mejoras-base/`, fuera del paquete:

- el número de tests que se recogen y los 25 más lentos (`pytest --collect-only -q`, `pytest --durations=25`);
- la salida de `coursekit --help` y de `--help` de cada comando, en los dos idiomas, para compararla después;
- el tiempo de arranque de `coursekit --version` y las importaciones más caras (`python -X importtime -m coursekit --version`);
- el tamaño de la instalación base sin extras, en un entorno temporal del scratchpad o en la CI.

**Validación.** Ninguna: es la referencia de las fases siguientes. Se corrigen en el informe los tres datos de arriba.

**Decide el mantenedor.** Nada.

## Fase 1. Dependencias y diagnóstico (informe, secciones 3 y 4)

**Qué se hace.**

- `markitdown` pasa a un extra `docs`. `brief` y `brand` ya avisan cuando falta (`markitdown_missing`); el aviso nombra el extra
  y el comando exacto para instalarlo.
- `doctor` dice qué extra falta para cada función (`docs`, `capture`) y qué programas de sistema faltan (ffmpeg, Chrome, node),
  con el comando para esa plataforma. También avisa si hay instalado un OpenCV distinto del que pide rapidocr.
- `coursekit config --check` compara cada `config/<name>.yaml` del proyecto con `defaults/<name>.yaml` y avisa de las claves que
  ya no existen o están mal escritas.
- Se apunta en el informe qué dependencia impide Python 3.14, sin abrir todavía la versión.

**Validación.**

- Un test por cada aviso nuevo: `brief` y `brand` sin `markitdown` (importación simulada) nombran el extra; `doctor` lista lo que
  falta; `config check` detecta una clave obsoleta y una mal escrita en un proyecto de prueba ("contraseñas robustas", cliente
  ACME).
- Un trabajo nuevo de CI instala el paquete sin extras, ejecuta `coursekit --version` y `coursekit doctor`, y comprueba que
  `brief` con un PDF da el aviso del extra en lugar de fallar.
- Comparar el tamaño de la instalación base con el de la fase 0.
- Los mensajes nuevos van en `lang/messages/*.yaml` en los dos idiomas, y `tests/test_i18n.py` los comprueba.

**Decide el mantenedor.** Sacar `markitdown` de la base rompe a quien actualice con `uv tool upgrade`: su `brief` dejará de leer
PDF hasta que instale el extra. Hay dos opciones: aceptarlo con un aviso en el changelog y en `doctor`, o dejar `markitdown` en
la base y no hacer este cambio.

## Fase 2. Pruebas (informe, sección 2)

**Qué se hace.**

- Un fixture `project` común en `conftest.py`. Hoy hay nueve versiones locales del mismo fixture (`test_agents`, `test_config`,
  `test_decision_based`, `test_handoff`, `test_local_design`, `test_course_flow`, `test_setup`, `test_refresh`, `test_store`).
  Se unifican las que hacen lo mismo y se dejan las que preparan algo distinto.
- El marcador `slow` solo si la fase 0 muestra tests base de más de un par de segundos.

**Validación.**

- El número de tests recogidos es el mismo que en la fase 0, y no aparece ningún `skip` nuevo.
- Se rompe a propósito una función que cubre cada fichero migrado y se comprueba que sus tests siguen fallando. Así se sabe que
  el fixture nuevo no los ha vaciado.
- El tiempo total no empeora respecto a la fase 0.

**Decide el mantenedor.** Nada, salvo si añadir el marcador `slow`.

## Fase 3. Calidad estática (informe, sección 2)

**Qué se hace.**

- Reglas nuevas de ruff, una por commit: `SIM`, `RET`, `PERF` y `PTH`. Cada una se aplica con `ruff --fix` y se repasa a mano lo
  que el arreglo automático no resuelve.
- `pyright` en modo `basic` en el grupo `dev`, solo sobre `config.py`, `course.py`, `i18n.py` y `paths.py`. Se tipan sus
  funciones públicas con `TypedDict` o `dataclass` donde hoy pasan diccionarios de YAML.

**Validación.**

- Cada commit de una regla de ruff solo cambia la forma del código. Se revisa su diff buscando cambios de comportamiento, sobre
  todo en `PTH`, donde `os.path` y `pathlib` difieren en Windows. La CI de Windows es la prueba que cuenta.
- `pyright` entra primero en la CI sin bloquear. Pasa a bloquear cuando los cuatro módulos estén limpios.
- Ningún cambio de mensajes ni de salida: la salida de `--help` es la misma que en la fase 0.

**Decidido.** `PTH` entra (nueve cambios). `PERF` no. `mypy` en lugar de `pyright`, porque el paquete de `pyright`
descarga Node en la caché del usuario; ya limpio, su trabajo de CI bloquea desde el principio.

## Fase 4. Estructura del código (informe, sección 1)

La fase de más riesgo. Va después de la 2 y la 3 porque necesita tests fiables y tipos en los módulos centrales.

**Qué se hace.**

1. `coursekit/external.py`: una función por programa externo (ffmpeg, ffprobe, Chrome, git, node, el agente). Centraliza la
   búsqueda del binario, el mensaje de que falta y la lectura de su salida como UTF-8. Los módulos lo adoptan uno por commit.
2. `coursekit/http.py`: un cliente con tiempo de espera, reintentos y el `User-Agent` del paquete, para los once módulos que hoy
   hacen peticiones cada uno a su manera (`delivery`, `updatecheck`, `mediatools`, `research`, `storybook`, `brief`, `ttsbatch`,
   `setup`, `illustrations`, `brand`, `videos`).
3. Subpaquetes `coursekit/capture/`, `coursekit/media/` y `coursekit/video/`, moviendo los módulos sin cambiar su lógica, un
   subpaquete por commit.
4. `commands.py` se parte en un módulo por grupo de comandos, cada uno con su `register`, y cada comando importa su módulo
   pesado solo cuando se ejecuta.

**Validación.**

- Antes de mover un módulo se buscan en todo el repositorio las referencias a su nombre como texto: plantillas, skills de
  `agentkit`, el servidor MCP, `python -m`, la documentación y los ficheros que genera `init`. Cada una se actualiza en el mismo
  commit.
- La salida de `--help` de todos los comandos es idéntica a la de la fase 0, en los dos idiomas.
  `tests/test_docs.py` sigue encontrando todos los comandos y opciones.
- El tiempo de arranque y las importaciones de `--version` mejoran respecto a la fase 0. Si no mejoran, el paso 4 no entra.
- `uv build` y una instalación del wheel en un entorno limpio. Después se ejecuta `--help` de cada comando y un flujo corto
  sobre el proyecto de prueba: `init`, `new`, `verify`, `assemble build` con el backend html.
- Para `external.py` y `http.py`: tests con un binario falso en el `PATH` y con las peticiones simuladas, incluidos el tiempo
  de espera, el reintento y el mensaje de que falta un programa.
- La CI de Windows en verde en cada commit, porque las rutas y la codificación son lo que más se rompe al mover código.

**Decidido.** Sin alias para los nombres antiguos de los módulos: los proyectos que existan se actualizan con la versión
nueva (el primer comando tras actualizar regenera sus ficheros gestionados).

## Fase 5. Experiencia de uso (informe, sección 3)

**Qué se hace.**

- `--json` en `status`, `verify`, `doctor` y `media check`, con una salida estable para los agentes.
- `verify --only` y `--ignore` por familia de regla, y un resumen por unidad al final.
- `coursekit help <comando>` muestra también el apartado del comando en `docs/<lang>/03-commands.md`.
- Las skills que hoy leen la salida en texto pasan a usar `--json`.

**Validación.**

- Un test por comando fija la forma del JSON: sus claves y sus tipos. Un cambio de forma rompe el test a propósito.
- `verify --only` y `--ignore` sobre el curso de prueba: cada familia se puede encender y apagar, y el código de salida sigue
  siendo de error si queda un error sin ignorar.
- Se lanza una unidad del curso de prueba con un agente real usando las skills con `--json`, para ver que lo lee bien.
- La documentación de cada opción nueva en `03-commands.md` en los dos idiomas.

**Decidido.** Familias en inglés, como los identificadores de tipos de recurso: `structure`, `words`, `style`, `language`,
`readability`, `media`, `activities`, `simulations`, `assembly`.

## Fase 6. Documentación y notas (informe, sección 5)

**Qué se hace.**

- `08-assembly-and-delivery.md` (744 líneas, 38 apartados) se parte en `08-assembly.md`, `09-delivery.md` con el banco de
  preguntas y `10-client-review.md`. `09-troubleshooting.md` pasa a `11`.
- Repaso de las ocho notas de `dev-notes/`: lo que ya está en `docs/` se borra, y de cada nota quedan solo sus decisiones
  abiertas.

**Validación.**

- `tests/test_docs.py`: los mismos ficheros en los dos idiomas, todos los enlaces y anclas resuelven, y la forma de los
  encabezados coincide.
- Búsqueda de enlaces a los nombres viejos fuera de `docs/`: READMEs, skills, plantillas de proyecto y mensajes de la CLI. Las
  URL absolutas a GitHub que tengan los proyectos ya creados se rompen; se mira si hay alguna y se decide si se deja una página
  que redirija.
- Para cada nota de `dev-notes/` que se borre, se comprueba antes, punto por punto, que lo que describe está en `docs/`. Lo que
  no está se pasa a `docs/` antes de borrar.

**Decide el mantenedor.** Qué decisiones abiertas de cada nota siguen vivas. Solo él sabe cuáles se cerraron fuera del
repositorio.

## Calendario orientativo

| Fase | Tamaño | Depende de |
|---|---|---|
| 0. Línea base | una sesión corta | nada |
| 1. Dependencias y diagnóstico | una sesión | 0 |
| 2. Pruebas | una sesión | 0 |
| 3. Calidad estática | dos sesiones | 2 |
| 4. Estructura | tres o cuatro sesiones | 2 y 3 |
| 5. Experiencia de uso | dos sesiones | 4 para `help <comando>`; el resto, solo 0 |
| 6. Documentación y notas | una sesión | ninguna; mejor al final para no partir dos veces lo que cambie la fase 5 |

Las fases 1 y 2 se pueden hacer en paralelo. Cada fase se publica cuando se cierra, sin esperar a las demás.
