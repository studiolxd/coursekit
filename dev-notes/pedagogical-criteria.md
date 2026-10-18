# Criterio pedagógico en la redacción y la maquetación

Nota de desarrollo: se borra cuando la función esté validada y publicada (lo que dure va a `docs/` y a los READMEs).

Objetivo: que el diseño, la redacción y la revisión apliquen criterios pedagógicos con respaldo (aprendizaje de adultos,
carga cognitiva, primeros principios de instrucción, motivación) en la forma de cada sección, no solo en la alineación
objetivo–contenido–actividad–evaluación, que ya está.

## Estado

- **Hecho (primera parte):** ciclo expositivo (`rules › expository.cycle`), introducción y resumen alineados, carga
  cognitiva y práctica espaciada en `content-writing`, criterio 11 «Pedagogy» en `content-review`, problema por sección en
  `instructional-design`, redundancia en `media-production`, aviso `content.chunk_max_words` en `verify` (no en importados),
  docs y READMEs.
- **Hecho (segunda parte):** las ayudas de trabajo (`job_aid`, `jobaid.py`): texto en el cuerpo del recurso, plantilla
  `theme/templates/job-aid.html` (la de coursekit en `templates/media/`), `coursekit theme sample`, `media render` a PDF
  etiquetado con el Chrome de la máquina (comprobado en macOS: `StructTreeRoot`, esquema, idioma, orden de lectura), la
  plantilla en la huella de la firma de la guía (`mediastyle.fingerprint`), `ATTACHMENT` en los dos montajes.
- **Pendiente de validar:** una ayuda subida a creator (`request_asset_upload` de tipo `attachment`) y el paquete html
  con una; el PDF con Chrome en Windows y Linux.
- **Pendiente (tercera parte):** el arreglo de los puntos de los gráficos con zonas activas (apartado 6).
- **Pendiente de validar:** un curso expositivo completo escrito y revisado con el ciclo.

## Punto de partida

Ya cubierto, aunque sin nombrar la teoría:

- Bloom revisada y alineación constructiva: `instructional-design` (un verbo observable, instrumento según nivel, «hacer, no
  reconocer», práctica antes que evaluación) y el criterio 2 de `content-review`.
- Cambio conceptual: `design/misconceptions.yaml`, que la redacción convierte en distractores y decisiones con `error`.
- Aprendizaje experiencial: el ciclo de `decision_based` (reto → explicación → práctica → decidir otra vez → cierre), el
  `debriefing` y el `:::reflection` de cierre.
- Feedback y transferencia (Gagné 7 y 9): el feedback incorrecto explica la respuesta buena; el test pone una situación nueva.
- Parte de la carga cognitiva: las reglas de legibilidad (una idea por frase, frases cortas, palabra cotidiana).
- Parte de la andragogía: la introducción presenta el uso profesional; el diseño pregunta por el contexto de la audiencia.

Falta: una estructura interna para las secciones **expositivas** (hoy solo «prosa completa y explicativa»), reglas de carga
cognitiva para la maquetación y los medios, y un criterio de revisión que mire todo esto.

Se descartan: VARK (estilos de aprendizaje: sin respaldo empírico), los modelos de proceso (ADDIE, Dick y Carey, Kemp, ASSURE,
SAM, Design Thinking: el flujo de coursekit ya cumple ese papel y no cambian la redacción), conectivismo y teoría
sociocultural (poco aplicables a un paquete autoformativo). Del aprendizaje social se aprovecha solo el modelado, que ya
permite `:::dialog`.

## Propuesta

### 1. Ciclo de la sección expositiva (primeros principios de Merrill)

Nuevo bloque en `defaults/rules.yaml`, paralelo a `decision_based`:

```yaml
expository:
  cycle: [problem, activation, demonstration, application, integration]
                               # problem        a task or situation of the audience's work, and why it matters to them
                               # activation     what the learner already knows or does, or the previous unit
                               # demonstration  the principle shown on a worked example, step by step
                               # application    practice with feedback, with less help each time
                               # integration    how they will use it in their own work
```

Todas las partes se pueden quitar: un proyecto (`config/rules.yaml`) o un curso (`course.yaml › rules`) deja en `cycle` solo
las que quiere. Por defecto van las cinco. No hay clave `optional`.

**Introducción y resumen alineados con el ciclo.** Con `activation` en el ciclo, la introducción de la unidad activa lo que
la persona ya sabe o hace (y lo de la unidad anterior) para toda la unidad; con `integration`, el resumen cierra con cómo lo
llevará a su trabajo, y su `:::reflection` es esa integración. La introducción presenta además la unidad desde el problema de
trabajo que resuelve (hoy: «su uso profesional»). Sin esas partes en el ciclo, la introducción y el resumen quedan como hoy.

Llega a las skills como `{{expository_cycle}}` (como `decision_cycle` en `agents.context()`). Recoge la andragogía (necesidad
de saber, experiencia previa, orientación a problemas), el aprendizaje significativo (activar lo previo), los eventos de Gagné
y la relevancia de ARCS sin nombrar cinco marcos.

- `content-writing`: cada sección `content` de un curso `expository` sigue el ciclo; la práctica (`application`) son las
  actividades de aprendizaje de sus objetivos, que ya van dentro de la sección.
- `instructional-design`: el título de una sección expositiva puede nombrar la tarea; en `proposal-notes.md`, el problema de
  cada sección (una línea), para que la persona lo vea al firmar.
- No se comprueba con `verify` (no hay marca mecánica fiable de «abre con un problema»): lo mira la revisión.

### 2. Carga cognitiva y principios multimedia (Sweller, Mayer)

Un apartado propio, «Carga cognitiva», en `content-writing` con las pautas de redacción, y su comprobación en el criterio
«Pedagogía» de `content-review`:

- **Segmentación:** un tramo de prosa seguida no pasa de `chunk_max_words` palabras (250). Lo cortan un encabezado, una
  directiva, un medio, un destacado (`>`, `:::highlight`), una lista o una tabla; no lo corta un salto de párrafo. Número en
  `rules.yaml › content` (0: no se comprueba); `verify` **avisa** (lo único mecánico de esta parte). La skill dice que se
  parte por ideas (un encabezado, una directiva que ordene el contenido), nunca con una lista puesta solo para cortar; la
  revisión lo mira.
- **Una idea por párrafo**, y el párrafo empieza por ella.
- **Señalización:** encabezados que dicen la idea, no el tema; el término clave en negrita la primera vez que se define;
  antes de un procedimiento o de una explicación con partes, una frase que anuncia cuántas y cuáles.
- **Lo concreto antes que lo abstracto:** el ejemplo o el caso, luego el principio que lo explica.
- **Un término para cada cosa:** el mismo nombre en toda la unidad (sin sinónimos por estilo), el del glosario y el de la
  interfaz.
- **Pasos:** un procedimiento va como lista numerada, un paso por acción; uno largo se agrupa en fases con su título.
- **Pre-entrenamiento:** los términos que un procedimiento usa se definen antes de él, no durante.
- **Coherencia:** nada decorativo (anécdotas, medios que no explican); refuerza la regla de medios «donde aporta algo».
- **Contigüidad:** el texto que explica un medio va junto a él; el placeholder dice qué parte del texto ilustra.
- **Redundancia:** en vídeo, la voz no lee el texto que hay en pantalla (va en `media-production` y en la skill de vídeo).
- **Del ejemplo al problema:** para objetivos de *apply* o más, ejemplo resuelto → ejercicio para completar → problema
  entero (encaja en `demonstration` → `application`).
- **Inversión de la pericia:** con `audience: specialist`, menos andamiaje y ejemplos más cortos.

### 3. Motivación (ARCS) en la revisión

Nuevo criterio «Pedagogía» en la rúbrica de `content-review`, que junta: sigue el ciclo de su enfoque; cada sección dice para
qué le sirve a la persona (relevancia); la dificultad progresa y los criterios de éxito están claros (confianza); carga
cognitiva (apartado 2). Y en la autorrevisión de `instructional-design`, que cada sección tenga un problema real de la
audiencia.

### 4. Ayudas de trabajo (cinco momentos de necesidad: *Aplicar* y *Resolver*)

Opcional por curso: en cursos procedimentales, una ayuda de trabajo por unidad (lista de comprobación, guía rápida) que la
persona descarga para usarla en su puesto. Se decide en el diseño.

**Un medio nuevo que se genera como PDF**, con los estilos de los medios. Lo que ya existe y se aprovecha:

- Las descargas de un recurso (`coursekit media set --download`, `asset.downloads`): los dos montajes ya las ponen como
  adjunto (creator: brick `ATTACHMENT` con `download_bricks()` de `assemble.py`; html: enlace `ck-attachment` de
  `htmlkit/render.py`, fichero en `media/files/`).
- Chrome sin interfaz de la máquina (`mediatools.py`, ya usado para pasar SVG a PNG): imprime HTML a PDF.
- Los tokens del theme (`tokens.css`), las fuentes (`media › fonts`) y la guía de estilo de los medios (`media-style.md`),
  que se firma.

Propuesta:

- **Tipo de recurso `job_aid`** (id en inglés; su palabra en `media_types` de cada `lang/<code>.yaml`), en
  `placeholder_types` y en `media.yaml › types` y `uses_theme`. Su receta: `agent-html` → PDF (`coursekit media render`
  amplía a PDF, o un comando propio).
- **El texto lo escribe el redactor**, dentro de un placeholder de medio como los demás (no una directiva propia) (su cuerpo en Markdown: título, pasos o lista de comprobación,
  notas), para que se revise con la unidad como el resto del contenido. El agente de medios no inventa contenido: lo maqueta.
- **Una plantilla del proyecto**, `theme/templates/job-aid.html` (o del curso, que gana), con los tokens y las fuentes:
  todas las ayudas de trabajo salen de ella, y por eso van en la misma línea.
- **Muestra durante el theme:** `/define-theme` genera con la plantilla una ayuda de muestra (contenido de ejemplo
  genérico) y deja el PDF en `theme/branding/samples/job-aid.pdf` (o en el theme del curso); la persona lo abre y pide
  cambios mientras ajusta el theme, y el agente lo vuelve a generar. Sin visor. La muestra va con la guía de estilo de los
  medios y se firma con ella (`coursekit approve media-style`): cambiar la plantilla pide firmar otra vez.
- **Una o varias por unidad**, las que pida el diseño (cada una, una actividad o recurso de la unidad que la persona ve al
  firmar el diseño).
- **Formato de página** en `media.yaml` (p. ej. `job_aid: {page: A4, orientation: portrait}`), por defecto A4 vertical.
- **Montaje:** el PDF se adjunta donde está el placeholder, con las descargas que ya existen. En `directives.yaml`,
  `ATTACHMENT` pasa de «not used for now» a decir que lleva las descargas de los recursos y las ayudas de trabajo.
- **Accesibilidad:** PDF etiquetado (estructura de encabezados y listas, idioma, título, orden de lectura) y contraste de
  los tokens (`coursekit theme check`). Comprobar qué da la impresión de Chrome (`--print-to-pdf`, esquema del documento) y
  si basta.

### 5. Práctica de recuperación espaciada

Las actividades de aprendizaje de una unidad recuperan algún objetivo de unidades anteriores (no la evaluación, que mide los
suyos). `coursekit outline` ya da al redactor lo que necesita.

### 6. Arreglo: los puntos de los gráficos con zonas activas

Hoy un `:::labelled-graphic` apunta a una imagen por su título y cada punto puede llevar `posición: x,y` (0–100). Sin ella, el
montaje los reparte a ciegas (`assemble.py`, `LABELLED_GRAPHIC`: x del 20 al 80 %, y al 50 %); con ella, quien redacta pone
números sin ver la imagen. En los dos casos el punto cae donde no está lo que nombra. Lo mismo puede pasar con las `area` de
los `hotspots` de una simulación sobre un fondo dibujado.

Propuesta:

- **El agente de medios sabe que la imagen es para zonas activas.** `media extract` anota en el recurso los puntos que la
  usan (`anchors: [<título de cada punto>]`, de los `:::labelled-graphic` que la nombran; y de las `area` de las simulaciones
  sobre ese fondo). El plan y la skill de medios lo dicen al producirla.
- **Una cruceta por punto en el SVG.** Al dibujar la imagen, el agente pone una cruceta pequeña en el sitio exacto de cada
  punto, con un id que la identifica (`<g id="anchor-1" data-anchor="<título>">`), en el color de los tokens y que la marca
  del punto tapa al montarse.
- **coursekit lee las crucetas.** Al registrar el recurso (`media set --status produced`, o `media render` al pasarlo a PNG)
  calcula la posición de cada cruceta en % del `viewBox` y la guarda en el manifiesto (`anchors: {<título>: [x, y]}`). El
  montaje (creator y html) usa esa posición para el punto.
- **`verify` y `media plan` avisan** de un punto sin cruceta en su imagen, de una cruceta que ningún punto usa y de un punto
  cuya `posición` escrita difiere de la cruceta.
- Una imagen que no es SVG (generada por API, una captura) no tiene crucetas: el agente de medios escribe las posiciones
  mirando la imagen (`media set --anchor "<título>=x,y"`), y `verify` avisa de los puntos sin posición.

Decisiones abiertas:

6a. ¿La cruceta se queda en la imagen final (la marca del punto la tapa) o se quita al exportar el PNG? Recomendación: se
    quita en la exportación (una cruceta visible si el punto se desplaza un poco queda fea) y se guarda solo su posición.
6b. Si hay `posición` escrita y cruceta, ¿cuál manda? Recomendación: la cruceta (es lo que dibuja la imagen); la posición
    escrita queda como aviso de `verify`.
6c. ¿Entran también las `area` de los hotspots de las simulaciones, o solo `:::labelled-graphic`? Recomendación: las dos,
    con la cruceta en el centro del área.

## Qué se toca

Criterio pedagógico:

- `src/coursekit/defaults/rules.yaml`: `expository.cycle`, `content.chunk_max_words`, comentados.
- `src/coursekit/agents.py`: tokens `expository_cycle`, `chunk_max_words`.
- Skills en `src/coursekit/agentkit/`: `instructional-design` (problema por sección, ayudas de trabajo en el diseño,
  autorrevisión), `content-writing` (ciclo, introducción y resumen, carga cognitiva, recuperación espaciada, migrados),
  `content-review` (criterio «Pedagogía»), `content-update` si toca.
- `verify`: aviso de bloque largo (no en migrados); mensajes en `lang/messages/<módulo>.yaml` (`es` y `en`).
- Tests: el aviso de segmentación y sus cortes; los tokens nuevos (ya los cubre el test de `agents.context()`).

Ayudas de trabajo:

- `job_aid` en `lang/<code>.yaml › media_types` (todos los idiomas: `tests/test_content_words.py`), `rules.yaml ›
  content.placeholder_types`, `media.yaml › types` (receta HTML → PDF), `uses_theme` y el formato de página.
- Formato del placeholder con cuerpo (`agentkit/docs/content-format.md`), `media extract` y el manifiesto.
- La impresión a PDF con el Chrome de la máquina (`mediatools.py`) y la plantilla `theme/templates/job-aid.html` (una por
  defecto en el paquete, que `init` copia).
- La muestra y su firma con la guía de estilo (`mediastyle.py`, skill `theme-definition`, `/define-theme`).
- Montaje: el PDF del placeholder como adjunto en creator (`assemble.py`) y en html (`htmlkit`); `directives.yaml ›
  ATTACHMENT` con su uso nuevo.
- Skill `media-production`: cómo se maqueta (nada de contenido nuevo) y la redundancia en vídeo.

Documentación: `docs/en` y `docs/es` — flujo (`02-workflow.md`), comandos (`03-commands.md`) si cambia alguno, configuración
(`04-configuration.md`), contenido (`06-content.md`), medios (`07-media.md`), montaje (`08-assembly-and-delivery.md`).
README / README.es: estado.

## Decisiones

1. ~~¿Obligatorio u opción?~~ **Decidido:** todas las partes configurables por proyecto y curso; por defecto, las cinco.
2. ~~¿Qué partes son opcionales?~~ **Decidido:** todas (ver 1). La introducción y el resumen recogen `activation` e
   `integration` cuando están en el ciclo.
2b. ~~Activación e integración en las secciones de contenido~~ **Decidido:** ancladas en la introducción y el resumen; en
   una sección de contenido solo cuando aporta algo que aquellas no cubren (una sección que se apoya en otra anterior, una
   tarea con su propio uso fuera del curso). No caben en más palabras: sustituyen al «uso profesional» de la introducción y
   son el `:::reflection` del resumen; `intro_share` y `summary_share` no cambian.
3. ~~`chunk_max_words`~~ **Decidido:** aviso, 250 palabras; cortan encabezado, directiva, medio, destacado, lista y tabla.
   La skill de redacción lleva las pautas de carga cognitiva (apartado 2).
4. ~~Cursos migrados~~ **Decidido:** en `design.origin: import` el ciclo no se aplica al texto del cliente, solo a lo que
   el redactor escribe nuevo (actividades y preguntas, de la ayuda al problema entero); `verify` no avisa de bloques largos;
   el criterio «Pedagogía» de la revisión se aplica, pero sobre el texto del cliente solo propone mejoras, nunca bloqueos.
5. ~~Ayudas de trabajo~~ **Decidido:** entran, como medio PDF (`job_aid`) con plantilla del theme y firma con la guía de
   estilo (apartado 4): placeholder de medio con el texto en su cuerpo; sin visor, un PDF de muestra generado; las que pida
   el diseño; página configurable en `media.yaml`, A4 vertical por defecto.
6. ~~Recuperación espaciada~~ **Decidido:** pauta recomendada en `content-writing`, sin comprobación.
7. ~~Reparto de horas~~ **Decidido:** `words_per_hour` no cambia; el ciclo reparte las palabras de la sección.
