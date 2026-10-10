# Contribuir a coursekit

English: [CONTRIBUTING.md](CONTRIBUTING.md)

## Bienvenida

coursekit (paquete `slxd-coursekit`, comando `coursekit`) es una herramienta de línea de comandos que guía la producción de cursos e-learning asistida por IA: brief, diseño instruccional, redacción, revisión, multimedia, ensamblado y entrega SCORM, con personas que firman en cada punto de control. Consulta el [README](README.es.md) para la visión general y la documentación de usuario ([English](docs/en/index.md), [Español](docs/es/index.md)) para ver cómo funciona desde el lado de quien lo usa.

Se agradecen contribuciones de cualquier tamaño: informes de errores, correcciones, documentación, traducciones y nuevas funciones. Esta guía explica cómo preparar el proyecto, qué debe pasar antes de dar un cambio por bueno y dónde está cada cosa.

El repositorio es público. No incluyas nunca el nombre de un cliente, de una persona, de un tenant, una URL interna ni datos de un proyecto real en código, tests, fixtures, documentación, comentarios o mensajes de commit. Los ejemplos y fixtures son genéricos e inventados (por ejemplo, un curso sobre contraseñas seguras para un cliente llamado "ACME").

## Preparar el entorno

Necesitas Python 3.12 o 3.13 (`requires-python = ">=3.12,<3.14"`; `.python-version` fija 3.12) y [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/studiolxd/coursekit
cd coursekit
uv sync --group dev
```

`uv sync --group dev` crea `.venv` e instala el paquete y las herramientas de desarrollo (`pytest`, `ruff`). Ejecuta coursekit desde el código fuente, sin instalarlo:

```bash
uv run coursekit --version
uv run coursekit help
```

Para probarlo como lo haría una persona usuaria, instálalo como herramienta (CI hace lo mismo con `uv tool install .`) y trabaja en una carpeta desechable fuera del repositorio:

```bash
uv tool install --editable .
mkdir -p ~/tmp/coursekit-try && cd ~/tmp/coursekit-try
coursekit init demo --yes --no-git --client ACME
cd demo
coursekit status
```

`--editable` hace que el comando instalado siga tus cambios. Al terminar: `uv tool uninstall slxd-coursekit`. Si la terminal no encuentra `coursekit` tras instalarlo, ejecuta `uv tool update-shell` y abre una terminal nueva.

### Windows, macOS y Linux

CI se ejecuta en los tres (consulta `.github/workflows/ci.yml`), así que un cambio tiene que funcionar en los tres:

- Las rutas que se muestran en los mensajes pasan por `Path.as_posix()`, para que la salida sea igual en todas partes.
- Lee la salida de `git` (y de cualquier otra herramienta) como UTF-8.
- Los ficheros que genera coursekit se escriben en UTF-8 con saltos de línea `\n` (`write_text(..., encoding="utf-8", newline="\n")`).
- Construye las rutas con `pathlib`, no concatenando cadenas con `/` o `\`.

## Comprobaciones antes de cada cambio

```bash
uv run ruff check .
uv run pytest -q
```

Ambas deben pasar; CI ejecuta las dos (más `uv tool install .` y `coursekit --version`) en Linux, macOS y Windows con cada push a `main` y cada pull request. Ruff se configura en `pyproject.toml`: longitud de línea 140, Python 3.12 como objetivo y las reglas `E`, `F`, `I` (imports), `UP` y `B`. `uv run ruff check . --fix` corrige la mayoría de los avisos de orden de imports y de estilo.

`tests/conftest.py` fija `COURSEKIT_LANG=en` en todos los tests y restaura el entorno después, así que los mensajes en los tests están en inglés. Un test que necesite español lo indica de forma explícita (`monkeypatch.setenv("COURSEKIT_LANG", "es")` o `i18n.use("es")`).

Además de los tests de comportamiento (`test_cli.py`, `test_course_flow.py`, `test_assemble.py`, `test_delivery.py`, `test_media.py`, `test_launch.py`, `test_setup.py`, `test_config.py`, ...), algunos tests vigilan las convenciones del proyecto y fallan si un cambio olvida una parte:

| Test | Qué comprueba |
|------|---------------|
| `tests/test_i18n.py` | Cada mensaje de `src/coursekit/lang/messages/*.yaml` existe en `es` y `en` con los mismos `{valores}`; cada `t("módulo", "clave")` usado en el código existe en su catálogo y recibe los valores que necesita; no hay emojis en los catálogos. |
| `tests/test_docs.py` | `docs/en` y `docs/es` tienen los mismos ficheros y la misma estructura de encabezados; los enlaces se resuelven; no hay emojis; `docs/*/03-commands.md` menciona cada comando y cada opción de la CLI; los dos README se enlazan entre sí. |
| `tests/test_init.py` | `init.CONFIG_NAMES` es igual a `config.NAMES`; `config/<nombre>.example.yaml` es el valor por defecto completo del paquete para cada configuración. |
| `tests/test_agents.py` | Cada skill, comando y agente se genera para cada herramienta, sin ningún `{{token}}` sin sustituir. |

## Mapa del repositorio

| Ruta | Qué hay |
|------|---------|
| `src/coursekit/cli.py` | Punto de entrada (`coursekit = "coursekit.cli:main"`): el parser, `init`, `config`, `rules`, `agents` y la gestión de errores de nivel superior. |
| `src/coursekit/commands.py` | El resto de comandos: `register(sub)` añade cada subcomando y sus opciones; las funciones `cmd_*` llaman a los módulos de abajo. |
| `src/coursekit/project.py`, `envfile.py`, `config.py` | Localizar el proyecto, cargar `.env` y la configuración por capas (valores del paquete, `config/`, `project.yaml`, `course.yaml`). |
| `src/coursekit/init.py`, `setup.py`, `doctor.py` | `coursekit init` (estructura del proyecto y ficheros que mantiene al día), `setup` (herramientas de la máquina) y `doctor` (diagnóstico). |
| `src/coursekit/course.py`, `new.py`, `sync.py`, `outline.py`, `status.py`, `states.py` | El modelo del curso, crear un curso, sincronizar el diseño aprobado con el esqueleto del contenido, leer el diseño y el estado del curso. |
| `src/coursekit/verify.py`, `approve.py`, `fingerprint.py`, `identity.py` | Comprobar el contenido contra las reglas de producción, las firmas y las huellas que detectan cambios posteriores. |
| `src/coursekit/agents.py`, `launch.py` | Generar skills, comandos y agentes para cada herramienta de IA (`context()` guarda los `{{tokens}}`) y lanzar las herramientas. |
| `src/coursekit/brief.py`, `media.py`, `mediatools.py`, `voices.py`, `theme.py` | Conversión del brief, planificación y producción multimedia, voces y subtítulos, tokens del theme. |
| `src/coursekit/assemble.py`, `directives.py`, `delivery.py`, `publish.py`, `catalog.py` | Ensamblado en la plataforma de autoría, directivas, entrega SCORM, publicación y catálogo de cursos. |
| `src/coursekit/i18n.py` | Mensajes para personas: `t("módulo", "clave", valor=...)` y la elección del idioma. |
| `src/coursekit/lang/` | `es.yaml` y `en.yaml`: tokens del formato de contenido del curso por idioma. `lang/messages/<módulo>.yaml`: los catálogos de mensajes de la CLI (`es` y `en`). |
| `src/coursekit/defaults/` | Valores por defecto del paquete, comentados: `rules.yaml`, `directives.yaml`, `media.yaml`, `delivery.yaml` (un proyecto puede sobrescribirlos) y `agents.yaml` (herramienta y modelo por defecto de cada rol). |
| `src/coursekit/agentkit/` | Origen de las skills, comandos, agentes y documentos de referencia que se generan en los proyectos de curso. |
| `src/coursekit/templates/` | Ficheros que se copian en proyectos y cursos (`project/`, `course/`, `brief/`, `remotion/`). |
| `src/coursekit/tools/` | Scripts auxiliares que se distribuyen con el paquete (`web2md.js`). |
| `tests/` | La batería de tests; `tests/fixtures/` contiene datos inventados. |
| `docs/en/`, `docs/es/` | Documentación de usuario en inglés y en español (España), con los mismos ficheros en ambos idiomas. |

## Convenciones

- **Idiomas.** El código, los identificadores, los comentarios, los nombres de fichero, las claves YAML, las skills, los comandos y los agentes están en inglés. Los mensajes para personas (salida, errores, `--help`) no se escriben nunca en Python: viven en los catálogos, en español e inglés. La documentación se escribe en ambos idiomas. Los mensajes de commit se escriben en español (España), como en el historial existente.
- **Tokens de contenido.** Las palabras del formato de contenido del curso (encabezado de apartado, etiqueta de objetivo, marcador de recurso, ...) pertenecen a `src/coursekit/lang/<código>.yaml`. No las escribas fijas en Python.
- **Sin números en las skills.** Las reglas y cifras de producción viven en `src/coursekit/defaults/*.yaml` y llegan a las skills como `{{tokens}}`.
- **Sin emojis** en ningún sitio (código, documentación, mensajes, commits). Los únicos símbolos permitidos son `★ ✔ ✘ · — ‹ ›`.
- **Comentarios.** Explican el porqué, no el qué; mantenlos breves, en inglés, y actualízalos junto con el código. Los valores comentados de `src/coursekit/defaults/` hacen también de documentación de cada regla para quien usa el paquete.
- **Ejemplos y fixtures** genéricos e inventados. No copies nunca material de un proyecto real, ni siquiera en parte.
- **Producto independiente.** Escribe el código, la documentación y el historial como un producto con entidad propia; no describas de dónde viene coursekit ni ninguna de sus partes.

## Cómo hacer

### Añadir un comando o una opción

1. Pon la lógica en el módulo que corresponda (o en uno nuevo) y añade una función `cmd_<nombre>(args)` en `src/coursekit/commands.py`. Los comandos sobre el propio proyecto (`init`, `config`, `rules`, `agents`) están en `cli.py`.
2. Registra el subcomando y sus opciones en `register(sub)` (`commands.py`) o en `build_parser()` (`cli.py`). Los textos de ayuda también son mensajes: `help=t("commands", "help_<nombre>")`.
3. Para los errores que la persona puede corregir, lanza la excepción del módulo y asegúrate de que `cli.main` la captura (las excepciones de `commands.ERRORS`): escribe `coursekit: <mensaje>` en stderr y sale con código 1.
4. Añade los mensajes (más abajo) y un test; los tests de la CLI llaman a `main([...])` de `coursekit.cli` y leen la salida con `capsys`.
5. Documéntalo en `docs/en/03-commands.md` y `docs/es/03-commands.md`: una sección `### \`coursekit <nombre>\``, la entrada en las tablas de comandos y cada cadena de opción. `tests/test_docs.py` falla si falta un comando o una opción en alguno de los dos ficheros.

### Añadir o cambiar un mensaje

Los mensajes viven en `src/coursekit/lang/messages/<módulo>.yaml`, un catálogo por módulo, cada clave con los dos idiomas:

```yaml
created_env:
  es: "ok: .env creado"
  en: "ok: created .env"
```

Se usa como `t("setup", "created_env")`; con valores, `t("módulo", "clave", path=...)` y `{path}` en ambos textos (una llave literal se escribe `{{`). Los dos textos deben usar los mismos `{valores}`; lo comprueba `tests/test_i18n.py`, que comprueba también que cada clave usada en el código existe. Un módulo nuevo es un fichero `<módulo>.yaml` nuevo en esa carpeta.

### Añadir o cambiar una regla de producción o un fichero de configuración

Una regla que un proyecto puede sobrescribir vive en `src/coursekit/defaults/<nombre>.yaml`, con un comentario que diga qué hace. `coursekit init` copia cada uno de esos ficheros al proyecto como `config/<nombre>.example.yaml` (completo, coursekit no lo lee; `init --update` lo refresca), de modo que una regla nueva o un valor por defecto cambiado llegan solos a los ejemplos: basta con mantener al día su comentario.

- Una regla nueva dentro de un fichero existente: añade la clave con su valor por defecto y su comentario, úsala desde el código a través de `config` y documéntala en `docs/en/04-configuration.md` y `docs/es/04-configuration.md`. Si una skill necesita el valor, añade un token a `agents.context()` (ver más abajo).
- Un fichero de configuración nuevo: crea `defaults/<nombre>.yaml` y añade su nombre a **ambos** `config.NAMES` (`src/coursekit/config.py`) e `init.CONFIG_NAMES` (`src/coursekit/init.py`); `tests/test_init.py` falla si no. Documéntalo en las dos páginas de configuración y en `03-commands.md` si `coursekit config` debe mencionarlo.

### Editar skills, comandos y agentes

Edítalos solo en `src/coursekit/agentkit/` (`skills/<nombre>/SKILL.md`, `commands/<nombre>.md`, `agents/<nombre>.md`, `docs/`). No edites nunca las copias generadas dentro de un proyecto de curso. Cada `{{token}}` que uses debe existir en `agents.context()` de `src/coursekit/agents.py`; un token desconocido lanza un error y `tests/test_agents.py` falla. Los parciales empiezan por `_` y se incluyen con `{{> _nombre}}`. Para ver el resultado, ejecuta `coursekit agents` en un proyecto desechable y lee los ficheros generados.

### Añadir un idioma de contenido

El formato de contenido es por idioma. Como mínimo:

- `src/coursekit/lang/<código>.yaml` con todos los tokens (copia `en.yaml`), incluidos `media_types` (la palabra de cada id de tipo de recurso), `directive_keys` y `directive_words`, y el código añadido a `LANGUAGES` en `src/coursekit/lang/__init__.py`. Un tipo de recurso o una clave de directiva nuevos reciben un id y una palabra en cada fichero de idioma (`tests/test_content_words.py` lo comprueba).
- El código en `init.LANGUAGES` y sus formas de tratamiento en `init.ADDRESS`; su nombre en `agents.LANGUAGE_NAMES`; el tratamiento por defecto en `agents.context()`.
- Una plantilla de curso: `src/coursekit/templates/course/<código>/` (`content.md`, `assessment.md`).
- Valores por defecto que dependen del idioma: `catalog.CATALOG_NAME` y los textos de sus columnas, `setup.PIPER_DEFAULT`, `voices.LOCALES` y las voces por defecto de `voices.py`.
- Documentación en `docs/en` y `docs/es`, y tests.

El idioma de la interfaz (`ui_language`, `COURSEKIT_LANG`) es independiente: es `es` o `en` (`i18n.LANGUAGES`). Añadir uno supone añadir su texto a cada entrada de cada catálogo, y `tests/test_i18n.py` las exige todas.

### Añadir documentación

La documentación de usuario vive en `docs/en/` y `docs/es/`, con los mismos nombres de fichero y la misma estructura de encabezados (número y nivel). Un comando, opción, proceso, configuración o regla nuevos o modificados se documentan en los dos idiomas en el mismo cambio. Los enlaces son relativos y deben resolverse; los bloques de código no se comprueban, así que mantén exactos los comandos que contienen. Si añades una página, añádela a los dos árboles y enlázala desde `index.md`.

## Pull requests y commits

- Mantén los cambios pequeños y centrados: una corrección o función por pull request, sin reformateos ajenos al cambio.
- Código, tests y documentación van juntos. Un pull request que cambia el comportamiento incluye el test que lo cubre y las actualizaciones de `docs/en` y `docs/es`.
- Ejecuta antes `uv run ruff check .` y `uv run pytest -q`. Comprueba que la salida se lee bien en los dos idiomas en todo lo que ve una persona (`COURSEKIT_LANG=es` y `COURSEKIT_LANG=en`).
- Los mensajes de commit se escriben en español (España): una primera línea breve que diga qué cambia y, si hace falta, los detalles después. Ejemplo: `Rutas con barras normales en los mensajes de error`.
- No hagas force-push en ramas compartidas ni reescribas historial que otras personas ya hayan descargado.
- No subas ficheros generados o locales: `.venv/`, `dist/`, `build/`, cachés ni ningún `.env`.

## Versiones

Una etiqueta `vX.Y.Z` que coincida con la versión de `pyproject.toml` ejecuta `.github/workflows/release.yml`: comprueba, construye, adjunta el wheel y la distribución de código fuente a una release de GitHub y sube a PyPI (publicación de confianza: el entorno `pypi` del repositorio es el publicador registrado en PyPI). Para publicar: sube `version`, commit, `git tag vX.Y.Z`, `git push --tags`. Los proyectos siguen la versión instalada por sí solos (el primer comando tras actualizar regenera sus ficheros gestionados y los de los agentes). La versión es el campo `version` de `pyproject.toml` (ahora `0.1.4`); `coursekit --version` la lee de los metadatos del paquete instalado y muestra `0.0.0` si se ejecuta desde un checkout sin instalar. El paquete se construye con hatchling:

```bash
uv build
```

que escribe la distribución de código fuente y el wheel en `dist/` (ignorado por git). Los cambios de versión y las publicaciones los decide el equipo mantenedor.

## Informar de problemas

Abre una issue en el [repositorio](https://github.com/studiolxd/coursekit). Incluye:

- La salida de `coursekit --version` y cómo lo instalaste (`uv tool install`, `uv run` desde un checkout).
- Tu sistema operativo y su versión, y la versión de Python si ejecutas desde el código fuente.
- El comando exacto y su salida completa (añade `COURSEKIT_LANG=en` para obtener los mensajes en inglés), y la salida de `coursekit doctor` si el problema tiene que ver con las herramientas de la máquina.
- Qué esperabas y qué ocurrió, y los pasos mínimos para reproducirlo, a ser posible en un proyecto nuevo creado con `coursekit init`.

No pegues secretos ni material de cursos reales: elimina claves de API, tokens, el contenido de `.env`, URLs de sistemas internos y cualquier texto del curso de un cliente. Sustitúyelos por ejemplos inventados.
