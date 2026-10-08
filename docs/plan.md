# Plan de coursekit

> Estado: **fase 1 hecha**; siguiente, fase 2 (curso de prueba de extremo a extremo). Paquete `slxd-coursekit`, comando `coursekit`, repositorio
> público <https://github.com/studiolxd/coursekit>.

## 1. Objetivo

Un paquete que se instala con `uv tool install` y que, con `coursekit init`, genera un proyecto
de producción de cursos e-learning con IA: brief, diseño instruccional, redacción, revisión,
multimedia, montaje y entrega, con firmas humanas en los puntos de control.

Principios:
- **Nada de un cliente en el paquete.** El repo es público: ni nombres de clientes, ni rutas de
  carpetas compartidas, ni tenants, ni datos de redes corporativas. Todo eso va en el proyecto.
- **El flujo:** brief → diseño instruccional → redacción → revisión IA → revisión editorial y
  firma → montaje → multimedia → review del cliente → entrega.

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Repositorio | `studiolxd/coursekit` en GitHub, público. Licencia **MIT**. |
| Nombre | paquete `slxd-coursekit`, comando `coursekit`. |
| Instalación | De momento **solo desde GitHub**: `uv tool install git+https://github.com/studiolxd/coursekit` (PyPI cuando haya una versión estable); extra `[media]` para multimedia. `uv` aporta su Python (3.12–3.13; `onnxruntime`, que usa MarkItDown, aún no tiene 3.14): no hay `.venv` en el proyecto. Piper y stable-ts van como herramientas de uv aparte (`setup --media`). |
| Plataforma de montaje | Elegible por proyecto (y por curso): **creator** (slxd, MCP) o **html** (SCO propio con maqueta, componentes y `@studiolxd/scorm`). |
| Diseño instruccional | Matriz de slxd en los dos backends, de momento. Diseño local sin slxd: fase opcional. |
| Carpeta espejo | SharePoint/OneDrive, **Google Drive** y **Nextcloud** desde el principio (sección 5). |
| Idiomas | **Español e inglés desde la primera versión** (sección 4). |
| Skills, comandos y agentes | **En inglés**, sin traducir; escriben el curso en el idioma del proyecto o del curso. |
| Identidad de quien firma | `coursekit setup` pide **nombre y email** y los guarda en el `.env` (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`); las firmas (`approve`) usan esa identidad, no la de git (sección 3.8). |
| Herramientas de agente | **Claude Code, opencode y Codex indistintamente** en todas las fases (sección 3.5). |

## 3. Arquitectura

### 3.1 Qué va en el paquete y qué en el proyecto

| Paquete (`slxd-coursekit`) | Proyecto (lo genera `coursekit init`) |
|---|---|
| Motor: estados, `new`, `status`, `sync`, `verify`, `approve`, `brief`, `outline`, `write`/`review`, `assemble`, `delivery`, `catalog`, `publish`, `setup`/`doctor`, `agents`, `media`, `voice`, `tts`, `subtitles`, `theme` | `project.yaml` (cliente, idiomas, tono, tratamiento, tenant de slxd, backend de montaje, calificación, espejo, red) |
| Reglas por defecto (`rules`, `directives`, `media`, `delivery`) | `config/`: solo lo que el proyecto cambie (se fusiona sobre los valores por defecto) |
| Skills, comandos y agentes (inglés), con variables del proyecto | `.agents/`: solo sobrescrituras del proyecto (tienen prioridad) |
| Plantillas: `project.yaml`, `course.yaml`, unidad, `brief/`, `AGENTS.md`, `opencode.json`, `.mcp.json`, `.claude/settings.json`, `.env.example`, hooks | `AGENTS.md`, `CLAUDE.md`, `opencode.json`, `.mcp.json`, `.claude/settings.json`, `.env.example`, `.githooks/` (generados; se refrescan con `coursekit init --update`) |
| Backends de montaje: `creator`, `html` (componentes, maqueta base, builder) | `theme/` (tokens, logos, maqueta propia si la hay), `components/` (componentes html propios) |
| `web2md`, conversión de `brief/` (MarkItDown), Remotion base | `brief/` general, `courses/` |
| Documentación para personas (es + en) | `docs/` propios del proyecto (opcional) |

### 3.2 Configuración en capas

`valores del paquete` ← `project.yaml` y `config/` del proyecto ← `course.yaml` del curso ←
`.env` de la persona (solo lo personal: claves, modelos, rutas locales, identidad) ← opciones del
comando.

### 3.3 Skills con datos del proyecto

Las skills y comandos del paquete llevan variables (`{client}`, `{content_language}`, `{tone}`,
`{address}` tú/usted, `{platform}`…). `coursekit agents` las renderiza en `.claude/` y
`.opencode/` (copias generadas, no enlaces) y aplica las sobrescrituras de `.agents/` del
proyecto. Se regeneran en `setup`, tras cada `git pull` (hook) y con `coursekit agents`.

### 3.4 Backends de montaje

Un solo registro de directivas: cada directiva del `content.md` declara su equivalente en cada
backend.

```yaml
accordion:
  role: interactive
  creator: ACCORDION
  html: accordion
```

- **creator:** esqueleto con `design_matrix_generate_course`, volcado incremental de bricks
  (plan → diff → aplicar → registrar IDs) y exportación SCORM con `create_export`.
- **html:** SCO propio. El paquete trae solo la mecánica genérica, **sin contenido de ningún
  curso ni marca de ningún cliente**:
  - maqueta base (cabecera, navegación, progreso, accesibilidad) con variables CSS neutras,
    sustituible por la del proyecto en `theme/`;
  - biblioteca de componentes (acordeón, pestañas, carrusel, línea de tiempo, flashcards,
    preguntas…), con un catálogo documentado y ejemplos de texto genérico, ampliable por el
    proyecto en `components/`;
  - runtime SCORM con `@studiolxd/scorm` (1.2 y 2004), build con esbuild, zip;
  - verificación: el SCO contiene todo el texto del `.md`.
- El backend se elige en `project.yaml › assembly.backend` y se puede cambiar por curso.
- Título de cada paquete (contenido de creator o SCO html): el del curso si tiene una sola
  unidad; si tiene varias, «Unidad N. Título de la unidad» (con su traducción en cada idioma).
  Lo calcula el plan de montaje y el `diff` lo trata como una operación más.

### 3.5 Claude Code, opencode y Codex indistintamente

Cualquier fase se puede hacer con cualquiera de las tres herramientas; el proyecto o la persona
elige herramienta y modelo para cada rol en el `.env`, con la pareja `<ROL>_AGENT` /
`<ROL>_MODEL` y las opciones `--agent` / `--model` para un solo lanzamiento:

| Rol | Fase | Lanzador |
|---|---|---|
| `DESIGN` | diseño instruccional y cambios (MCP de slxd) | `coursekit run new-course` / `design-change` |
| `WRITER` | redacción | `coursekit write` |
| `REVIEWER` | revisión IA | `coursekit review` |
| `MEDIA` | producción multimedia (guiones, SVG, HTML, grabaciones, vídeo) | `coursekit media produce` |
| `ASSEMBLY` | montaje y entrega (MCP de creator o backend html) | `coursekit assemble` / `deliver` |

Cada rol deja constancia de quién hizo el trabajo (herramienta y modelo): `designed_with` en
`course.yaml`, `written_with` y `reviewed_with` por unidad y `made_with` por recurso en
`media/manifest.yaml`.

Una sola fuente (`.agents/` del paquete más las sobrescrituras del proyecto) y `coursekit agents`
genera lo que cada herramienta necesita:

| Pieza | Claude Code | opencode | Codex |
|---|---|---|---|
| Instrucciones del proyecto | `CLAUDE.md` → `@AGENTS.md` | `AGENTS.md` (`opencode.json › instructions`) | `AGENTS.md` |
| Skills | `.claude/skills/` | `.opencode/skill/` | `.agents/skills/` (por confirmar con la versión actual de Codex) |
| Comandos (`/new-course`…) | `.claude/commands/` | `.opencode/command/` | sin comandos de proyecto: `coursekit run <comando> …` le pasa el fichero del comando como prompt |
| Agentes y modelo por rol | `--model` al lanzar | agentes en `.opencode/agent/` con el modelo del `.env` | `--model` al lanzar |
| MCP de slxd | `.mcp.json` | `opencode.json › mcp` | `.codex/config.toml` del proyecto (por confirmar), o instrucciones de alta en `~/.codex/config.toml` |
| Bloquear `approve` y `git push` | `.claude/settings.json › permissions.deny` | `permission.bash` en `opencode.json` y agentes | reglas de ejecución de Codex (por confirmar); como mínimo, la regla en `AGENTS.md` |

- **Un lanzador para todo:** `coursekit run <comando> [args] [--agent A] [--model M]` abre la
  herramienta elegida con el comando (`new-course`, `design-change`, `write-unit`,
  `review-unit`, `assemble`, `deliver`…). Dentro de Claude Code u opencode se siguen pudiendo
  escribir los `/comandos` directamente.
- **Sin interfaz:** `--headless` (`claude -p`, `opencode run`, `codex exec`) con permisos
  acotados y log en `.cache/logs/`; sin número de unidad, todas las pendientes en orden.
- **Skills neutras:** sin sintaxis propia de una herramienta; lo específico de cada herramienta
  va en lo que genera `coursekit agents`.
- **`coursekit doctor`** comprueba, para cada herramienta instalada, que ve las skills, los
  comandos y el MCP.
- **Prueba de compatibilidad:** en cada release, un curso de prueba (una unidad corta) se
  recorre con cada herramienta en cada rol, y se anota el resultado en `docs/compatibility.md`.

### 3.5.1 Tokens de diseño antes de producir recursos

Los recursos (SVG, infografías, simulaciones, demos, vídeos) usan los tokens de diseño del
proyecto. Si se escriben a mano, se desvían del theme real y arrastran errores (p. ej. un
contraste insuficiente que nadie ha validado). En coursekit:

- **Los tokens se derivan, no se escriben a mano**, según el backend de montaje:
  - `creator`: de su theme (`get_theme` → colores, tipografías, radios, sombras);
  - `html`: de las variables CSS de la maqueta y los componentes del proyecto.
  `coursekit theme tokens` lo hace y guarda en `tokens.json` el origen (`theme_id` o fichero de
  la maqueta) y la fecha.
- **Antes de la fase de multimedia:** `coursekit media plan` avisa (y `produce` se niega salvo
  `--force`) si los tokens no proceden del theme o la maqueta del proyecto, o si han cambiado
  después de producir un recurso (para regenerarlo).
- `coursekit theme check` comprueba el contraste AA de los pares de color que usan los recursos
  y los componentes (texto/fondo, botón/texto).
- El theme o la maqueta los valida una persona (como el DI): es una firma más del proyecto.

### 3.5.2 Agentes de multimedia

- **Agente `media`** (con el modelo de `MEDIA_AGENT` / `MEDIA_MODEL`), lanzado con
  `coursekit media produce CODE [id] [--headless]`: recorre los recursos pendientes, elige la
  receta y deja constancia (`made_with`).
- **Una skill por tipo de recurso**: `media-diagram` (SVG), `media-infographic` (HTML → PNG/PDF),
  `media-terminal` (grabación real con VHS/asciinema en un proyecto de prueba fuera del repo,
  demos de terminal interactivas), `media-simulation` (escenarios ramificados y simulaciones
  HTML), `media-video` (guion, Remotion, locución y subtítulos), `media-audio` (locución con la
  voz del curso), `media-image` (generación o banco de imágenes). `media-production` queda
  como orquestadora: inventario, plan, guiones, subida y registro.
- **Descargables:** un recurso puede llevar un fichero para descargar (p. ej. el PDF de una
  infografía), que se monta como adjunto tras el recurso (`media set --download`).
- **Modelo por tipo, opcional**: `MEDIA_MODEL_<TIPO>`; si no está, `MEDIA_MODEL`.
- **Comprobación automática de cada recurso** (`coursekit media check`): tokens del proyecto,
  contraste AA, texto alternativo, tamaño y duración según el placeholder, teclado y foco
  visible en los HTML (axe en Chrome sin interfaz), sin dependencias externas, sin emojis, y en
  las grabaciones que no aparezca configuración personal (modelo, rutas, cuentas).
- **Revisión de recursos**: la hace el rol `REVIEWER` sobre la preview montada, con revisión
  parcial (solo lo nuevo o cambiado).
- **Lo real frente a lo reconstruido**: cada guion dice qué textos o pantallas salen de una
  ejecución real (con la versión) y cuáles de la documentación.

### 3.6 Material de referencia y notas generales (`brief/`)

```
<proyecto>/brief/              ← general, para todos los cursos del proyecto
├── notes.md                   ← notas generales: cómo se redacta, se diseña y se revisa
├── sources/                   ← material común: manual de estilo del cliente, guía de lenguaje
│                                claro, normativa, plantillas de referencia… (cualquier formato)
├── links.md                   ← webs comunes (accesibilidad, normativa, documentación de producto)
├── text/  index.md            ← generados por `coursekit brief`
courses/<CODE>/brief/          ← lo propio de cada curso, misma estructura
```

- **Notas por fase**, en los dos niveles (`notes.md`), con secciones fijas: *General*, *Diseño
  instruccional*, *Redacción*, *Revisión* (y *Multimedia* y *Montaje* si hace falta). Cada agente
  lee *General* y la suya. Ejemplos de notas generales de redacción: lenguaje claro, nombres
  oficiales del cliente, ejemplos situados en su sector, anglicismos, inclusividad, cifras y fechas.
- **Prioridad:** opciones del comando > notas del curso > notas generales del proyecto > valores
  del paquete. Las **reglas fijas** (formato del contenido, mínimos de palabras, placeholders,
  interactividad, sin emojis) no se anulan con notas: viven en `config/` y en `content-format`.
- `coursekit brief CODE` actualiza los dos niveles; el `index.md` del curso enlaza al general.
- El diseño cita en `proposal-notes.md` las fuentes usadas; el redactor saca de `text/` datos,
  comandos y nombres y marca con `VERIFICAR` lo que no esté; para el revisor, contradecir el
  material es bloqueante.
- Formatos: MarkItDown (PDF, Word, PowerPoint, Excel/CSV, HTML, EPUB, JSON/XML, ZIP); `.md` y
  `.txt` tal cual; webs con `web2md`; imágenes listadas; audio y vídeo piden transcripción;
  avisos de PDF escaneado, ficheros de más de 20 MB y webs que no se extraen. `text/` se
  versiona para que todos trabajen con la misma copia.

### 3.7 Funcionalidad de la primera versión

| Pieza | Qué hace |
|---|---|
| Estados y firmas | `course.yaml` con estados e `history`; firmas del DI y de cada unidad solo por `approve` (nunca un agente). |
| Diseño instruccional en slxd | matriz, validación, exportación (Excel, `matrix.json`, `validation.json`) y `sync` a `course.yaml › units`. |
| Redacción y revisión | `write`/`review` con herramienta y modelo del `.env`, `written_with`, aviso (no bloqueo) si revisa el mismo modelo que redactó; reglas del redactor en el comando, no en el agente. |
| Continuidad sin saturar el contexto | `outline` (mapa del curso y `--section U.S`). |
| Revisión parcial | huellas por apartado y actividad; `verify` detecta lo cambiado tras la revisión y `review` revisa solo eso (`--parts`, `--full`). |
| `brief/` por curso | conversión a Markdown, descarga de webs e índice. |
| Montaje incremental en creator | plan determinista desde el `.md`, `diff` por lección, IDs de bricks registrados, título del contenido, recursos como notas hasta que se producen. |
| Multimedia | manifest, recetas por tipo y proveedor, voz única por curso (TTS y subtítulos), descargables. |
| Entorno | Python 3.12 con `uv`, `setup` y `doctor` en macOS, Linux y Windows. |
| Espejo | `publish` a una carpeta sincronizada y catálogo en Excel. |

### 3.8 Identidad de quien firma

- `coursekit setup` pregunta nombre y email la primera vez (con la identidad de git como valor
  sugerido) y los guarda en el `.env` personal: `COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`.
  `coursekit setup --identity` permite cambiarlos.
- `coursekit approve` firma con esa identidad (`by: Nombre <email>`); si falta, pide ejecutar
  `coursekit setup --identity` y no firma.
- El commit de la firma usa la misma identidad como autor (`git commit --author`).
- `coursekit doctor` muestra con qué identidad se firmará; `status` y el Excel muestran quién
  firmó.
- Aplica también a `history.by` de `course.yaml`.

### 3.9 Parámetros de producción configurables

Todo lo que define el modelo de producción es configurable, con estos valores por defecto. Se
definen en `project.yaml › rules` (iguales para todo el equipo, versionados) y cada curso los
puede sobrescribir en `course.yaml › rules`. **No van en el `.env`**: es personal y no se
versiona, y `verify` daría resultados distintos según quién lo ejecutara.

| Parámetro | Valor por defecto |
|---|---|
| Páginas por hora de formación | 10 |
| Palabras por página | 500 |
| Palabras por hora (se pasa a slxd como `palabrasPorHora`) | páginas × palabras (5.000) |
| Margen recomendado sobre el mínimo de palabras | 5 % (unificar el valor de la regla y el de la skill) |
| Placeholders multimedia por hora de unidad | 2,5 |
| Tipos distintos de multimedia por unidad | 4 |
| Tipos de placeholder admitidos | Imagen, Vídeo, GIF animado, Infografía, Esquema/Diagrama, Simulación interactiva, Demo interactiva en terminal, Audio |
| Directivas interactivas por hora de apartado de contenido | 4 |
| Mínimo de directivas interactivas por apartado de contenido | 1 |
| Preguntas del banco sumativo por objetivo | 5 |
| Apartados "Introducción y objetivos" y "Resumen" | sí, sí (por curso con `--no-intro` / `--no-summary`) |
| Horas de introducción y resumen por unidad | 0,2–0,3 h |
| Competencias por curso | 2–4 |
| Objetivos por unidad | 2–4 (menos de 2 o más de 5, justificado) |
| Calificación: tests de unidad / prueba final, aprobado, intentos | 60 / 40, 50 %, 2 |
| Estructura de la matriz | `sin_modulos` |
| Símbolos permitidos (sin emojis) | `★ ✔ ✘ · — ‹ ›` |
| Exportación SCORM: estándar, informe, origen de la nota | SCORM 1.2, `passed_incomplete`, `quiz` |
| `brief/`: tamaño máximo por fichero, mínimo de palabras para no avisar de OCR | 20 MB, 20 |

- Las skills no llevan cifras escritas: las reciben como variables desde la configuración
  efectiva del curso (`coursekit rules CODE` la muestra, con el origen de cada valor).
- `palabrasPorHora` de la matriz se calcula y `doctor` / `sync --check` avisan si no coincide.
- `verify` y `sync` usan la configuración efectiva y el informe dice qué valores ha aplicado.
- Cambiar un parámetro en un curso ya verificado lo devuelve a `writing` si deja de cumplir.

## 4. Idiomas (español e inglés desde el principio)

| Qué | Cómo | Idiomas |
|---|---|---|
| **Contenido de los cursos** | `project.yaml › content_language` (por defecto) y `course.yaml › language` (por curso). Los tokens que lee el verificador salen de un catálogo por idioma: títulos fijos ("Introducción y objetivos" / "Introduction and objectives", "Resumen" / "Summary"), `## Apartado N` / `## Section N`, etiqueta de objetivo, tipos de placeholder, nombres de directivas, palabras por página (valor propio por idioma). | es, en; ampliable con un fichero de idioma |
| **Skills, comandos y agentes** | En inglés, sin traducir. Reciben el idioma del contenido y del informe como variable. | en |
| **Para personas**: documentación, mensajes de la CLI, plantillas (`notes.md`, `links.md`), Excel de seguimiento | Catálogos `es` y `en`; `project.yaml › ui_language`, sobrescribible por persona en `.env` (`COURSEKIT_LANG`). Documentación en `docs/es/` y `docs/en/`. | es, en |

Mantenimiento: `coursekit i18n check` (en CI) avisa de mensajes sin traducir y de documentos cuya
traducción está desfasada (hash del original guardado en la traducción).

Coste estimado: contenido configurable, unos 2 días; mensajes y plantillas, 1–2 días;
documentación en inglés, 1–2 días más su revisión.

## 5. Carpeta espejo: SharePoint, Google Drive y Nextcloud

`publish` copia a una carpeta local que un cliente de escritorio sincroniza. Lo que cambia por
proveedor es la configuración y los enlaces del Excel.

```yaml
# project.yaml
mirror:
  provider: sharepoint        # sharepoint | onedrive | google-drive | nextcloud | folder | rclone
  url: ""                     # dirección web de la carpeta (para los enlaces del Excel)
```

```sh
# .env (personal): ruta local de esa carpeta en el equipo de cada persona
MIRROR_DIR="…"
```

| Proveedor | Carpeta local | Enlaces a cada curso en el Excel |
|---|---|---|
| SharePoint / OneDrive | cliente OneDrive | por ruta |
| Nextcloud | cliente de escritorio de Nextcloud | por ruta: `https://<host>/apps/files/?dir=/<ruta>` |
| Google Drive | Google Drive para escritorio | los IDs no salen de la ruta: enlace a la carpeta raíz, o por curso con `rclone link` |
| folder | cualquier carpeta (NAS, Dropbox…) | sin enlaces o plantilla de URL propia |
| rclone (opcional) | sin cliente de escritorio: `rclone copy` a un remoto | `rclone link` |

## 6. Lo que es de cada proyecto (nunca del paquete)

| Qué | Dónde |
|---|---|
| Cliente, tono, tratamiento, idioma | `project.yaml` |
| Theme de creator, tokens, logos, maqueta html con la marca | `theme/` del proyecto |
| Tenant y URL del MCP de slxd | `project.yaml › platform.slxd`; `.mcp.json` y `opencode.json` generados |
| Modelos por defecto de la organización (p. ej. un proxy LLM propio) | `.env.example` del proyecto |
| Inspección TLS corporativa | genérico en el paquete, con rutas de certificado configurables en `project.yaml › network` |
| Carpeta espejo | `project.yaml › mirror` + `.env` |
| Cuentas, accesos, soporte de IT | nota de onboarding del proyecto (el paquete trae el onboarding genérico) |
| Cursos, briefs, recursos, exportaciones | `courses/` del proyecto |

## 7. Fases

Cada fase termina con algo comprobable. No se pasa a la siguiente con la anterior rota.

| # | Fase | Hecho cuando |
|---|---|---|
| 1 | **Esqueleto del paquete.** Motor, estructura de paquete (`pyproject.toml`, `src/coursekit/`, recursos), comando `coursekit`, configuración en capas, `coursekit init` y `--update`, skills en inglés con variables, CI (lint, tests, `i18n check`, comprobación de datos de clientes). | `uv tool install git+…` + `coursekit init demo` genera un proyecto que pasa `coursekit doctor`, y las tres herramientas ven skills, comandos y MCP. |
| 2 | **Curso de prueba de extremo a extremo.** Un curso corto genérico recorre todo el flujo con el backend creator, de `new` a `deliver`; queda como prueba de regresión del paquete. | El curso se genera, verifica, monta y exporta sin pasos manuales fuera de las firmas; el equipo instala con `uv tool install` y `coursekit setup`. |
| 3 | **Idiomas es/en.** Contenido configurable, mensajes y plantillas, docs `es/` y `en/`, `i18n check`. | Un curso de prueba en inglés pasa `verify`; `COURSEKIT_LANG=en coursekit status` sale en inglés. |
| 4 | **Espejo multi-proveedor.** `mirror.provider`, enlaces por proveedor, `rclone` opcional. | Publicación probada en SharePoint, Nextcloud y Google Drive. |
| 5 | **`brief/` general del proyecto** con notas por fase en los dos niveles. | Una nota general de redacción se aplica en diseño, redacción y revisión; una nota del curso que la contradice manda. |
| 6 | **Backend html.** Maqueta base y componentes genéricos, registro de directivas con columna `html`, builder con `@studiolxd/scorm`, verificador de volcado completo, entrega del zip. | Un curso de prueba genérico se genera con `coursekit assemble --backend html` y funciona en un LMS de prueba (SCORM Cloud). |
| 7 | Opcional: diseño instruccional local (sin slxd, con Excel generado); más idiomas. | — |

### 7.1 Pasos de la fase 1

| Paso | Qué | Comprobación | Estado |
|---|---|---|---|
| 1.1 | Paquete mínimo: `pyproject.toml` (hatchling, Python ≥ 3.12, MIT), `src/coursekit/`, comando `coursekit` con `--version` y `help`, `LICENSE`, CI con ruff, pytest y la comprobación de términos prohibidos. | `uv tool install git+…` y `coursekit --version` en macOS, Linux y Windows; CI en verde. | hecho |
| 1.2 | Raíz del proyecto y configuración en capas: el motor busca `project.yaml` hacia arriba (como git busca `.git`), carga los valores del paquete, `project.yaml`, `config/`, `course.yaml` y `.env`; `coursekit config [CODE]` muestra el valor efectivo y su origen. | Tests de fusión de capas; ningún módulo usa rutas relativas al paquete para datos del proyecto. | hecho |
| 1.3 | `coursekit init <carpeta>` y `init --update`: genera `project.yaml` (preguntas: cliente, idioma, tono, tratamiento, backend, espejo), `.env.example`, `AGENTS.md`, `.gitignore`, `courses/`, `brief/`, `theme/`; `--update` refresca solo lo generado. | `coursekit init demo` en una carpeta vacía y `init --update` sin tocar lo editado por la persona. | hecho |
| 1.4 | Motor de cursos: `new`, `status`, `sync`, `outline`, `verify`, `approve`, `reviewed`, `brief`, `rules`, con estados, huellas y firmas con la identidad del `.env`. Copiados y limpiados, con tests sobre un curso de ejemplo genérico. | Un curso de ejemplo en `tests/fixtures/` pasa `sync --check` y `verify`; `approve` firma con `COURSEKIT_USER_*`. | hecho |
| 1.5 | Skills, comandos y agentes en inglés con variables; `coursekit agents` genera `.claude/`, `.opencode/` y lo de Codex; `coursekit run` y `write`/`review` con `--headless`. | Las tres herramientas ven skills, comandos y MCP en el proyecto demo (`coursekit doctor`). | hecho |
| 1.6 | `setup` y `doctor` del paquete (sin `.venv` en el proyecto; extra `[media]`), red con inspección TLS configurable. | `coursekit setup` y `doctor` limpios en un equipo nuevo. | hecho |
| 1.7 | Montaje creator, multimedia, entrega, catálogo y `publish` (este último con `mirror.provider: folder` y `sharepoint`; el resto de proveedores en la fase 4). | El curso de ejemplo genera plan de montaje y catálogo. | hecho |

Orden alternativo: si corre prisa el backend html, la fase 6 puede ir justo después de la 2;
3, 4 y 5 son independientes entre sí.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Un cambio rompe el flujo | El curso de prueba de la fase 2 se recorre en CI (sin interfaz) antes de cada release. |
| Filtrar datos de proyectos al repo público | Lista de términos prohibidos (nombres, dominios, rutas, tenants) comprobada en CI antes de cada commit a `main`; nada de `courses/` ni de themes de clientes en el paquete. |
| Skills en inglés que escriben peor en castellano | Probarlo en la fase 1 redactando la misma unidad con skills en inglés y en castellano, y comparar. |
| Windows | Mantener el lanzador `.cmd` y las copias de skills cuando no hay enlaces; probar `init`, `setup` y `brief` en Windows en las fases 1 y 2. |
| Una herramienta de agente cambia su formato (skills, comandos, MCP, permisos) | Todo lo específico de cada herramienta lo genera `coursekit agents` en un solo sitio; la prueba de compatibilidad de cada release lo detecta. |
| Diferencias entre los backends | Un mismo registro de directivas y un mismo verificador del `.md`; cada backend con su verificador de salida. |
| Huecos de la plataforma creator | Lista en `docs/creator-gaps.md` (qué se pidió y cuándo); el pipeline avisa en vez de fallar mientras no estén resueltos. |

## 9. Huecos conocidos de creator

Pendientes de que creator los resuelva; mientras tanto, el pipeline los esquiva o avisa:

- Esquema del theme por MCP: qué campos admite cada bloque, su tipo, valor por defecto, de dónde
  hereda y qué pinta; y que `update_theme` devuelva los campos descartados y el motivo.
- Embeds (simulaciones, demos) en blanco en la vista compartida (`X-Frame-Options: DENY`).
- Bloque de código: opción de texto plano (la detección automática etiqueta mal) y líneas largas
  que se cortan.
- Flashcards: algunos campos del theme dejan en blanco la cara frontal; etiqueta «Voltear»
  visible bajo la tarjeta.
- Fuentes propias del theme que no cargan en el reproductor (CORS).
- Código en línea, bloques de código dentro de pestañas y desplegables, textos alternativos largos.

## 10. Pendiente de decidir

- Cuándo publicar en PyPI (`slxd-coursekit`).
- Si los componentes html se publican también como paquete npm propio.
- Si el diseño instruccional local (fase 7) es necesario para clientes sin slxd.
