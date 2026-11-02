# Entrega y publicación

Cómo se exportan los paquetes SCORM de un curso montado, se registran, se publican en la carpeta compartida y se siguen en el catálogo. Cómo se monta el curso está en [Montaje](08-assembly.md).

## Entrega

Cada unidad es un paquete SCORM: con el backend creator, un contenido de creator exportado desde la plataforma; con el backend html, el zip que escribe `coursekit assemble build --version`.

### Antes de exportar: `delivery check`

```bash
coursekit delivery check PWD
# PWD: se puede entregar
```

`/deliver` empieza con este comando, y `delivery name` y `delivery add` aplican las mismas reglas. Se niega (código de salida 1, con un mensaje) cuando:

| Caso | El mensaje dice | Qué hacer |
|---|---|---|
| El curso está en pausa | «PWD está en pausa desde ...» | `coursekit resume PWD` |
| `client_review.required` es `true` y no hay ninguna ronda | «PWD necesita la revisión del cliente antes de entregarse ...» | Abre una ronda (`send`), o omítela con un motivo (`skip`) |
| La última ronda pidió cambios | «el cliente pidió cambios en PWD ...» | Aplica los cambios, vuelve a montar y abre la ronda siguiente (`send`) |
| La última ronda sigue abierta | «PWD espera a la respuesta del cliente (ronda N, enviada a ...)» | Anota la respuesta: `approve` o `changes` |

Los textos exactos están en [Solución de problemas](11-troubleshooting.md#el-curso-está-en-pausa-o-la-revisión-del-cliente-bloquea-la-entrega).

Cuando es solo cuestión de estado, imprime un aviso en lugar de negarse: `aviso: PWD está en «<estado>», no en un estado de entrega (assembly, client_review): el paquete se registra, pero el curso no se marca como entregado`. Sin la exigencia (`required: false`) las rondas no importan: un curso en `assembly` siempre se puede entregar.

### Ajustes de exportación SCORM

De `src/coursekit/defaults/delivery.yaml`; cámbialos en `config/delivery.yaml`, `project.yaml › delivery` o `course.yaml › delivery` ([04-configuration.md](04-configuration.md)).

| Clave | Por defecto | Valores |
|---|---|---|
| `export.deliveryType` | `lms` | |
| `export.standard` | `scorm_1_2` | `scorm_1_2`, `scorm_2004` |
| `export.reporting` | `passed_incomplete` | `passed_incomplete`, `completed_incomplete` |
| `export.scoreSource` | `quiz` | `quiz`, `lessonProgress` |
| `file_name` | `{code}-U{unit:02d}-v{version}-{standard}.zip` | Patrón del nombre de fichero |

Con el backend creator, el agente llama a la herramienta de exportación de creator con los valores de `export`, espera a que termine el trabajo y descarga el paquete. Con el backend html solo se usan `export.standard` y `file_name`: el estándar decide el manifiesto y el seguimiento del paquete, y `reporting` y `scoreSource` no se aplican (mira [Seguimiento SCORM](08-assembly.md#seguimiento-scorm)).

### Nombre del fichero y registro

```bash
coursekit delivery name PWD --unit 1 --version 1.0
# PWD-U01-v1.0-scorm12.zip
```

`{standard}` pierde los guiones bajos (`scorm_1_2` pasa a `scorm12`, `scorm_2004` pasa a `scorm2004`). El paquete se descarga a `courses/PWD/delivery/` con ese nombre y se registra:

```bash
coursekit delivery add PWD --unit 1 --version 1.0 \
  --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip --job <id-del-trabajo-de-exportación> --snapshot <id-de-la-instantánea>
# registrado PWD-U01-v1.0-scorm12.zip · curso entregado
```

Con el backend html, `build` escribe el zip directamente en `courses/PWD/delivery/` con ese nombre, así que no hay nada que descargar ni trabajo de exportación ni instantánea:

```bash
coursekit assemble build PWD --unit 1 --version 1.0
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip
# registrado PWD-U01-v1.0-scorm12.zip · curso entregado
```

`delivery add` comprueba que el fichero sea un zip válido con `imsmanifest.xml` en su raíz, que esté directamente dentro de `courses/PWD/delivery/` y que la unidad exista. Después añade una entrada a `course.yaml › deliveries` con `version`, `unit`, `date`, `by` (la identidad de firma de `.env`), `standard`, `file`, `sha256`, `export_job` y `snapshot` (vacíos en un paquete html). Cuando todas las unidades tienen un paquete de la misma versión **y el curso está en `assembly` o `client_review`**, el estado del curso pasa a `delivered` y se añade una entrada al historial. En cualquier otro estado el paquete se registra con el aviso de arriba y el estado del curso no cambia. Mientras alguna unidad no tiene paquete de esa versión, imprime `registrado <fichero> · unidades pendientes de la v<versión>: [2, 3]`. `courses/*/delivery/` está en el `.gitignore` del proyecto: los zip no se versionan, `course.yaml` sí. Cuando la unidad aún tiene recursos visuales que van como [imágenes provisionales](07-media.md#imágenes-provisionales), avisa y los nombra; el paquete se registra igualmente.

## Publicación en la carpeta espejo

La carpeta espejo es una copia de solo lectura de los cursos en una carpeta sincronizada por el cliente de escritorio de tu proveedor (o cualquier carpeta). Todo lo que se edite allí se sobrescribe en la siguiente publicación.

| Ajuste | Dónde | Significado |
|---|---|---|
| `mirror.provider` | `project.yaml` | `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder` o `none` |
| `MIRROR_DIR` | `.env` (personal) | Ruta local de la carpeta sincronizada. La escribe `coursekit init --mirror-dir RUTA` |
| `mirror.url` | `project.yaml` (compartido) | Dirección web de la carpeta espejo, usada para los enlaces a los cursos del catálogo. La escribe `coursekit init --mirror-url URL` |

`mirror.url` según el proveedor, y el enlace que se escribe en el catálogo para el curso `PWD`:

| Proveedor | Qué pegar en `mirror.url` | Enlace para `PWD` |
|---|---|---|
| `sharepoint`, `onedrive` | La dirección de la carpeta en la barra del navegador de la biblioteca (`…/Forms/AllItems.aspx?id=<ruta de la carpeta>`), una dirección de «copiar vínculo» (`…/:f:/r/<ruta>`) o una ruta simple (`/sites/<sitio>/<biblioteca>/<carpeta>`) | Desde la dirección de la biblioteca: la misma dirección con `/courses/PWD` añadido a la ruta de `id`. Desde un «copiar vínculo»: `https://<host>/<ruta de la carpeta>/courses/PWD` (se descartan el prefijo `/:f:/r` y la consulta). Desde una ruta simple: la ruta con `/courses/PWD` añadido. Un enlace para compartir (`/:f:/s/<token>`) no lleva ruta, así que no se escriben enlaces (la comprobación avisa) |
| `nextcloud` | La dirección de la aplicación Archivos con `?dir=/Carpeta` | La misma dirección con `dir=/Carpeta/courses/PWD` |
| `google-drive` | La dirección de la carpeta | La misma dirección para todos los cursos (los ids de carpeta no van en la ruta) |
| `folder` | Cualquier dirección base; `{code}` se sustituye por el código del curso | La dirección con `{code}` sustituido; sin `{code}`, la misma dirección |

```bash
coursekit publish --check    # informa de la configuración; no escribe nada
coursekit publish            # todos los cursos
coursekit publish PWD        # un curso
```

`--check` imprime una de estas líneas: `info: sin carpeta espejo (project.yaml › mirror.provider: none)`, `aviso: MIRROR_DIR no está definido en .env; no se publicará nada`, `aviso: MIRROR_DIR no existe: …` u `ok: carpeta espejo de <proveedor> en <ruta>`, seguida de una línea sobre los enlaces (`ok: enlaces a las carpetas de curso como …`, `info: no hay mirror.url…` o el aviso del enlace para compartir). `--only-if-configured` hace que `publish` no haga nada, en silencio, cuando no hay carpeta espejo; el hook de git `post-merge` lo usa para publicar tras cada pull.

### Publicación automática

Rara vez ejecutas `coursekit publish` tú. Cuando el proyecto tiene carpeta espejo, estos comandos publican el curso que han cambiado en cuanto terminan: `coursekit new`, `sync` (sin `--check`), `verify` (sin `--no-update`), `reviewed`, `approve`, `assemble applied`, `assemble link`, `assemble build`, `media set`, `delivery add`, `hold`, `resume`, `client` y `handoff` (tras cada paso). Por eso los enlaces de preview y review, el estado y los paquetes llegan al espejo y al catálogo sin que nadie lo pida.

- El catálogo del proyecto (`courses/catalogo-cursos.xlsx`) se actualiza en silencio y solo se escribe cuando sus datos cambiaron desde la última vez (las filas de cada curso se guardan en `.cache/catalog/`, así que una actualización lee solo el curso que cambió, tenga el proyecto los cursos que tenga).
- Sin espejo (`mirror.provider: none`, o sin `MIRROR_DIR`) no ocurre nada más y no se imprime nada.
- Si el espejo no se puede actualizar (la carpeta no existe, el Excel está abierto), el comando imprime un aviso por la salida de error y conserva su propio código de salida: su trabajo está hecho y `coursekit publish` lo reintenta.
- En una sesión de un agente sin interfaz (el handoff, `--headless`) los comandos que ejecuta el agente no publican (`COURSEKIT_MIRROR=deferred`): quien lanzó la sesión publica una vez al terminar, y el handoff después de cada paso. En una sesión que abres tú todo funciona como arriba.

Qué hace `publish`:

- Por cada curso copia `course.yaml`, `design/`, `content/` y `reviews/` a `<MIRROR_DIR>/courses/PWD/`, solo los ficheros cuyo contenido cambió. `brief/`, `media/` y `assembly/` no se reflejan.
- Los ficheros que publicó antes y que ya no existen en el curso se eliminan de la carpeta espejo (se registran en `courses/PWD/.published.json`, dentro de la carpeta espejo), junto con las carpetas que queden vacías. Los ficheros que nunca publicó no se tocan.
- `delivery/` solo añade: un paquete se copia una vez y nunca se sobrescribe ni se borra en la carpeta espejo, aunque se elimine en local. Una versión nueva tiene un nombre de fichero nuevo.
- Escribe el catálogo en `<MIRROR_DIR>/<fichero del catálogo>`, con enlaces a las carpetas de curso. Si el Excel está abierto, falla con `no se puede reemplazar … (¿está abierto en Excel?)`.
- Primero actualiza el catálogo de `courses/` e imprime `escrito <ruta> (N cursos, M unidades)` (no con `--only-if-configured`). Después imprime una línea por cada curso que cambió (`publicado PWD: 5 copiados, 0 eliminados, 0 sin cambios`) y una para el catálogo del espejo. Con `mirror.provider: none` imprime la primera línea y dice que no hay nada que publicar (código 0). Con un proveedor y sin `MIRROR_DIR`, falla con `no hay carpeta espejo configurada (project.yaml › mirror y MIRROR_DIR en .env)`.

## El catálogo de seguimiento

`coursekit catalog` construye el Excel de seguimiento a partir de todos los `courses/*/course.yaml`. Es un fichero generado: no lo edites nunca (los cambios se hacen en cada `course.yaml`). Se escribe junto a los cursos, en `courses/` (`--output RUTA` para cambiarlo; git lo ignora), y, con `publish`, en la carpeta espejo. La copia de `courses/` la actualizan los mismos comandos que publican, con o sin espejo, y no lleva enlaces a carpetas. El nombre del fichero y todas las etiquetas siguen el `ui_language` del proyecto: `course-catalog.xlsx` en inglés, `catalogo-cursos.xlsx` en español. El color de la cabecera es el token `accent-ink` (o, si no, `accent`) de `theme/tokens.json`, o gris oscuro; las hojas `Cursos` y `Unidades` tienen la cabecera inmovilizada y filtros. `coursekit catalog` por sí solo deja vacía la columna **Carpeta**: los enlaces los escribe `publish`.

Hojas, en el idioma del catálogo (español / inglés): `Cursos` / `Courses`, `Unidades` / `Units` e `Información` / `About`.

**Hoja de cursos** (una fila por curso)

| Columna (español) | Column (English) | Valor |
|---|---|---|
| Código | Code | `code` |
| Título | Title | `title` |
| Estado | Status | Estado del curso, traducido |
| Horas | Hours | `design.hours` |
| Unidades | Units | Número de unidades |
| Palabras mínimas | Minimum words | Suma de las palabras mínimas de los apartados |
| Palabras actuales | Current words | Palabras para el alumno escritas en cada `content.md` (el mismo recuento que `verify`) |
| % palabras | % words | Actuales entre mínimas, como porcentaje (puede superar el 100 %) |
| Recursos multimedia | Media assets | El mayor entre los recursos reservados en el contenido y los recursos del manifiesto |
| Recursos producidos | Assets produced | Recursos del manifiesto que están `produced` o `uploaded` |
| Carpeta | Folder | Enlace a la carpeta del curso en la carpeta espejo (hipervínculo; solo lo escribe `publish`, y solo con un `mirror.url` utilizable) |
| DI aprobado por | Design approved by | Quién firmó el diseño |
| DI aprobado el | Design approved on | Fecha y hora de esa firma |
| Resp. DI · Resp. redacción · Resp. revisión · Resp. multimedia · Resp. montaje | Design lead · Writing lead · Review lead · Media lead · Assembly lead | `owners` (`instructional_design`, `writing`, `review`, `media`, `assembly`) |
| Última actualización | Last update | Fecha de la última entrada de `history` |
| Última nota | Last note | Nota de esa entrada |

**Hoja de unidades** (una fila por unidad)

| Columna (español) | Column (English) | Valor |
|---|---|---|
| Código | Code | Código del curso |
| Unidad | Unit | Número de la unidad |
| Título | Title | Título de la unidad |
| Estado | Status | Estado de la unidad tal cual: `pending`, `writing`, `verified`, `reviewed` o `approved` |
| Horas | Hours | Horas de la unidad |
| Palabras mínimas · Palabras actuales | Minimum words · Current words | Como arriba, para la unidad |
| Recursos multimedia | Media assets | Recursos reservados en el `content.md` de la unidad |
| Aprobación editorial | Editorial approval | Quién firmó la unidad |
| Aprobada el | Approved on | Fecha y hora de esa firma |
| ID de contenido | Content ID | `units[].content_id` |
| Preview | Preview | `units[].links.preview` (hipervínculo): vista previa en vivo de la unidad |
| Review | Review | `units[].links.review` (hipervínculo): enlace de revisión del cliente de la unidad |

**Hoja de información**: cuándo se generó, el origen (`courses/*/course.yaml`), la rama y el commit, el usuario de git que lo generó y un aviso de que el fichero es generado y no debe editarse.

## Lista de comprobación de la entrega

Antes de exportar:

- [ ] Diseño firmado y sin cambios, y todas las unidades `approved` (`coursekit status PWD`).
- [ ] Todos los recursos multimedia `uploaded` y validados en la vista previa (ningún recurso de `media/manifest.yaml` está `pending`, `scripted` ni `produced`, y `coursekit media plan PWD` no muestra avisos: `plan` solo lista los recursos `pending` y `scripted`). Con el backend html: todos los recursos `produced` con su fichero, que `build` copia en el paquete.
- [ ] Todas las unidades montadas. Creator: `content_id` definido y `coursekit assemble diff` informa `unchanged` para el contenido y todas las lecciones. Html: `coursekit assemble build PWD` termina sin errores y has leído sus avisos. El estado del curso es `assembly` (o `client_review`, si abriste una ronda).
- [ ] Creator: enlaces de vista previa y de revisión de todas las unidades anotados (`units[].links`). Html: la vista previa abierta en un navegador (`courses/PWD/assembly/html/unit-01/index.html`) y comprobadas las lecciones, un componente de cada tipo y el test.
- [ ] Curso fuera de pausa, y `coursekit delivery check PWD` pasa.
- [ ] Revisión del cliente, si el proyecto la exige (`client_review.required`) o tú la quieres: la última ronda `approved` (`coursekit client PWD approve --by "..."`) o omitida con un motivo (`coursekit client PWD skip --reason "..."`).
- [ ] Versión decidida: `1.0` la primera vez y después `1.1`, `1.2`… según `course.yaml › deliveries`.
- [ ] Ajustes de exportación comprobados (`coursekit config delivery`).

Por cada unidad, con el backend creator:

- [ ] Instantánea del contenido llamada `v<versión>`.
- [ ] Exportación con los ajustes de `export` y espera a `COMPLETE` (con `FAILED`, detente y lee el error).
- [ ] Nombre de fichero obtenido con `coursekit delivery name`, descargado en `courses/PWD/delivery/`.
- [ ] `coursekit delivery add` (comprueba el zip y lo registra).

Por cada unidad, con el backend html:

- [ ] `coursekit assemble build PWD --unit N --version <versión>` (el zip se escribe en `courses/PWD/delivery/` con el nombre de `coursekit delivery name`).
- [ ] `coursekit delivery add` sin `--job` ni `--snapshot` (comprueba el zip y lo registra).

Al final:

- [ ] Estado del curso `delivered` (`coursekit status PWD`).
- [ ] Paquetes y catálogo en la carpeta espejo (`coursekit delivery add` los publica; `coursekit publish PWD` si en ese momento no tenías espejo).
- [ ] Al menos una unidad probada en el LMS de destino (o en SCORM Cloud). Con el backend html es imprescindible: coursekit no ha probado los paquetes en un LMS real.
- [ ] `course.yaml` con commit (los zip no se versionan); los commits solo se hacen cuando tú lo pides.

El agente hace los pasos de exportación (creator) o los de construcción y registro (html) con `/deliver PWD 1.0` o `coursekit run deliver PWD 1.0`.

## Ejemplo completo

Curso `PWD`, una unidad, cliente ACME, proveedor de carpeta espejo `folder`, backend creator:

```bash
coursekit assemble link PWD --unit 1 --content-id c-123
coursekit assemble plan PWD --unit 1
coursekit assemble diff PWD --unit 1        # contenido: rename; lecciones: create…
# el agente aplica las operaciones y registra cada lección:
coursekit assemble applied PWD --unit 1 --lesson U1-S1 --lesson-id l-1 --brick-ids a,b
coursekit assemble applied PWD --unit 1 --content
coursekit assemble diff PWD --unit 1        # hasta que todo esté "unchanged"
```

El agente anota los enlaces de la unidad:

```bash
coursekit assemble link PWD --unit 1 --preview https://acme.example.com/p/abc --review https://acme.example.com/r/xyz
```

El cliente revisa (opcional); tú abres y cierras la ronda, y el agente trata los comentarios:

```bash
coursekit client PWD send --to "equipo de formación de ACME"
# ronda 1 abierta; el curso pasa a client_review. Enlaces: ...
# /client-feedback PWD   (en el agente)
coursekit client PWD approve --by "responsable de formación de ACME"
# ronda 1 aprobada por responsable de formación de ACME: se puede entregar
```

Entrega la versión 1.0:

```bash
coursekit delivery check PWD
# PWD: se puede entregar
coursekit delivery name PWD --unit 1 --version 1.0
# PWD-U01-v1.0-scorm12.zip  (el agente lo exporta y lo descarga en courses/PWD/delivery/)
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip \
  --job job-1 --snapshot snap-1
# registrado PWD-U01-v1.0-scorm12.zip · curso entregado
coursekit publish --check
# ok: carpeta espejo de folder en /ruta/a/MIRROR_DIR
# info: no hay mirror.url en project.yaml; el catálogo no tendrá enlaces a las carpetas
coursekit publish PWD
# escrito /ruta/al/proyecto/courses/catalogo-cursos.xlsx (1 cursos, 1 unidades)
# publicado PWD: 5 copiados, 0 eliminados, 0 sin cambios
# escrito /ruta/a/MIRROR_DIR/catalogo-cursos.xlsx (1 cursos, 1 unidades)
```

El mismo curso con el backend html (`assembly.backend: html`) se salta los enlaces, la carga y la exportación; el enlace de revisión es el del paquete que alojas:

```bash
coursekit assemble build PWD --unit 1
# unidad 1: 5 ficheros en courses/PWD/assembly/html/unit-01
# vista previa: coursekit preview PWD (con LMS simulado), o abre courses/PWD/assembly/html/unit-01/index.html en el navegador
coursekit assemble build PWD --unit 1 --version 1.0
# paquete PWD-U01-v1.0-scorm12.zip (212.4 KB)
# (prueba el zip en el LMS de destino o en SCORM Cloud, y aloja el paquete para el cliente si hay revisión)
coursekit client PWD send --to "equipo de formación de ACME" --where https://lms.acme.example.com/courses/pwd
coursekit client PWD approve --by "responsable de formación de ACME"
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip
# registrado PWD-U01-v1.0-scorm12.zip · curso entregado
```

Siguiente: [Revisión del cliente](10-client-review.md)
