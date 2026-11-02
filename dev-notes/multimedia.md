# Más contenido multimedia en los cursos: diagnóstico y propuestas

Nota de trabajo (2 de noviembre de 2026, sobre `0.8.0`). Lo que se observa: un curso nuevo o importado sale muy
interactivo (acordeones, pestañas, carruseles, preguntas) pero pobre a la vista: pocas fotos, casi ninguna captura de la
aplicación que enseña, ningún vídeo de un canal oficial, y la iconografía solo aparece dentro de las infografías que el
agente dibuja. Esta nota recorre dónde está la causa en el código y las skills, y propone los cambios, ordenados por
rendimiento frente a coste. Lo que se vaya haciendo se tacha y pasa a «Hecho», al final.

## 1. Diagnóstico: por qué sale pobre

### 1.1 Las reglas piden interactivos; los visuales son un mínimo que se cumple con lo más barato

- `defaults/rules.yaml › content`: `interactive_per_hour: 4` y `min_interactive_per_content_section: 1` frente a
  `placeholders_per_hour: 2.5` **por unidad** (una unidad de 2 h: 5 recursos de cualquier tipo, audio y ayudas de trabajo
  incluidos) y `visual_sections: [intro, summary]`. Un apartado de contenido puede quedarse sin visual con un comentario
  `<!-- SIN IMAGEN: motivo -->` (`visual_decision`), y `verify` solo comprueba que el motivo no esté vacío
  (`verify.py › check_visuals`), no que sea bueno. La revisión lo deja en «mejora», que el handoff no devuelve al redactor
  (solo devuelve los hallazgos bloqueantes).
- La skill `content-writing` empuja con fuerza hacia los interactivos (una lista con títulos es pestañas o acordeón; un
  proceso es siempre un carrusel; `verify` avisa de cada uno) y, sobre lo visual, se frena a sí misma: «Nothing decorative:
  no anecdote or medium that does not explain», «Never one for its own sake: one or two per section», «A content section with
  an infographic, a diagram or a video needs no more». El redactor cumple el mínimo con lo que no cuesta nada (un
  esquema SVG, un icono grande) y no pone más.
- El diseño instruccional no planifica lo visual: `instructional-design` propone ayudas de trabajo por apartado, pero nada
  de «qué pantallas de la aplicación verá el alumnado» ni «qué apartado pide una foto, un esquema o un vídeo». Lo visual
  es una decisión del redactor, a posteriori, sin que nadie la firme.

### 1.2 Las capturas de la aplicación real casi nunca llegan a producirse

- La regla de no inventar interfaces es correcta y está bien cerrada (`media.yaml › depicts`, `media-production › 1.1`).
  Su consecuencia práctica es otra: un recurso `interface` sin material real **no se produce** (paso 4 de la skill), queda
  `scripted` con un guion para una persona y el curso se monta con la nota del placeholder a la vista. El handoff no se
  para por ello.
- Para que coursekit capture por sí mismo hace falta que una persona haya hecho `coursekit capture login` y `allow`
  **antes** del paso de medios, y el permiso caduca. Nadie se lo dice a tiempo: `/new-course` solo recuerda `/define-theme`
  (`commands/new-course.md`, paso 5) y `coursekit status` no avisa de que el curso enseña una aplicación y no hay perfil
  ni permiso. La persona se entera en el informe final del handoff, con todo ya montado.
- Cada captura es una sesión (`session_start` con código e id): para una unidad con ocho pantallas son ocho sesiones,
  cada una con su guion aprobado. El coste empuja al agente a pedir pocas capturas, o a clasificar el recurso como
  `concept` cuando puede.
- El material real que ya existe no se aprovecha. `coursekit brief` convierte PDF, Word y PowerPoint a texto y tira sus
  imágenes (MarkItDown no las extrae); de las páginas web, `tools/web2md.js` **sí** descarga las imágenes a
  `brief/text/web/<sitio>/assets/`, pero `brief/index.md` no las lista, `brief --find` no indexa sus pies ni su `alt`, y
  ninguna skill dice que existen. Los manuales oficiales y la documentación del cliente están llenos de capturas que
  nunca llegan al curso. Una imagen suelta en `brief/sources/` se lista como `kind: image` (`brief.py › convert_files`) y
  nada más: ni el redactor ni el agente de medios saben que pueden usarla (`media adopt` solo se menciona en los cursos
  importados).

### 1.3 Los vídeos de canales oficiales solo existen como política de hosts prohibidos

- `videos.py` nace para los cursos importados: `check` solo mira direcciones en hosts de `rules › forbidden › hosts`
  (vacío por defecto), y `allow_channels` cuelga de esa lista. En un curso nuevo nadie busca un vídeo oficial: la skill de
  redacción no lo menciona en el bloque de apoyo visual, y la de medios lo pone como primera opción de un recurso
  `interface` cuando el placeholder ya está escrito y el agente de medios no puede tocar el contenido.
- No hay ninguna búsqueda de vídeos: `coursekit research` busca páginas (Exa, Perplexity, Brave, Tavily) y `videos`
  solo resuelve quién publica una dirección que ya se tiene (oEmbed). Encontrar «el vídeo del fabricante sobre X» queda
  en la búsqueda web del propio agente, que en la prueba de `research.md` trae fuente oficial en menos de la mitad de las
  consultas.
- Un vídeo aprobado es **un enlace en el texto**: ningún backend lo incrusta (`assemble.py` no tiene bloque para una
  dirección externa; `htmlkit/render.py` solo reproduce un fichero subido). El alumnado ve un enlace que se abre fuera
  del curso.

### 1.4 Sin creator no hay fotografías, y las ilustraciones dependen de fuentes de marca

- `media.yaml › types.image`: la única fuente de fotografía con licencia es `creator-stock` (`mcp: search_stock_images`).
  Con el backend html, en un handoff sin conectores, o con cualquier agente que no sea Claude Code con creator, no hay
  foto posible: la cadena cae a `magnific-api` (créditos) o a `agent-svg`.
- `magnific-stock` solo busca entre los autores que la marca lista (`illustrations.search` filtra por `author_id`);
  un proyecto sin `illustration-sources.json` no tiene búsqueda de ilustraciones aunque tenga la clave.

### 1.5 Iconografía: hay un tipo de recurso, no hay iconos

- El tipo `icon` es un icono grande como imagen (`media.yaml`, receta `brand-icon`), y `brand.py` copia los iconos del
  paquete de marca a `icons/` y los cuenta en `index.md`; nada los indexa por significado, así que el agente no puede
  buscar «candado» entre 400 ficheros. Sin biblioteca de marca, `brand-icon` no tiene de dónde sacar nada y
  `creator-icons` necesita creator.
- No existe iconografía **en línea**: ni en los títulos de pestañas y paneles, ni en las tarjetas, ni en las notas por
  tipo (consejo, aviso), ni en las listas. El backend html pinta `:::note` y `:::highlight` con un borde izquierdo
  (`base.css › .ck-note`) y nada más. Por eso solo se ven iconos donde el agente escribe el SVG entero: las infografías.

### 1.6 El montaje solo conoce una disposición: la figura suelta

- Creator tiene `IMAGE_TEXT`, `IMAGE_CAROUSEL`, `IMAGE_GALLERY` y `VIDEO_GALLERY`; `directives.yaml` los apunta como
  «assembly» y `assemble.py` no los usa nunca (`MEDIA_KIND` manda todo a `IMAGE`). Cada imagen va sola, a ancho completo,
  con su pie. No hay imagen junto al texto ni galería de capturas.
- Un recurso no puede ir dentro de una directiva: el placeholder solo se reconoce en el nivel del apartado
  (`assemble.py › section_bricks`); dentro de un panel de carrusel sus líneas se convierten como una cita. Y `media scan`
  no sabe de directivas, así que un placeholder dentro de un carrusel **sí** recibe id y entra en el manifiesto, pero el
  montaje no lo sustituye. El patrón más común de un tutorial de software, un paso y su captura, no se puede escribir.

### 1.7 Nadie mide la cobertura visual

`media plan` lista opciones por recurso, la galería enseña lo producido y el handoff lista lo que espera a una persona,
pero ningún sitio dice «de 12 apartados, 7 llevan un recurso producido y 5 muestran una nota». La pobreza se ve al abrir el
curso montado.

## 2. Propuestas

Cada una con dónde toca, qué documenta y su tamaño (P pequeño: un cambio; M medio: un día; G grande: varios días).

### A. Reglas y redacción (P, el mayor efecto por el menor coste)

- **A1. Mínimos visuales por apartado, como advertencia.** En `rules.yaml › content`, sin ser exigentes:
  `visual_per_content_section: 1` (todo apartado de contenido lleva al menos un recurso visual; el comentario `SIN IMAGEN`
  sigue valiendo, con su motivo) y `photos_per_unit: 1` (al menos una **fotografía o captura** por unidad: un recurso
  `image` que no sea un icono ni un esquema, para que la unidad no se apoye solo en infografías y diagramas dibujados por
  el agente). Además, `visual_mix_max: 0.6`: si más de esa parte de los visuales de una unidad son infografías o
  diagramas, `verify` avisa y sugiere qué apartado pediría una foto o una captura. Todo son **advertencias** (familia
  `media`), nunca errores, en los cursos nuevos y en los importados, de modo que ningún curso que hoy pasa deja de pasar.
  `verify.py › check_visuals` lo comprueba. Los números llegan a las skills como tokens (`agents.context()`), nunca
  escritos.
- **A2. Reescribir el bloque visual de `content-writing`.** Quitar las frases que frenan («one or two per section», «needs
  no more») y sustituir el criterio de «decorativo» por uno de **patrones por tipo de contenido**: un procedimiento sobre
  una pantalla, una captura por paso; una comparación, una infografía; un concepto, una ilustración o una fotografía de
  la situación; una estructura o un objeto, un esquema o un gráfico con puntos; una cifra, un dato grande; un lugar o
  una situación de trabajo, una fotografía. Lo «decorativo» queda solo como criterio del texto alternativo
  (`--decorative`), no como razón para no poner una imagen. El mismo cambio, en el criterio 7 de `content-review`.
- **A3. Que el redactor reciba los hallazgos visuales.** El criterio 7 de la revisión sube a **bloqueante** un apartado de
  contenido sin visual cuyo motivo no se sostiene, y `verify` avisa cuando más de `visual_optout_max` (una fracción) de los
  apartados de una unidad renuncian al visual. Así el handoff lo devuelve al redactor en su ronda.
- **A4. Plan visual en el diseño.** La skill `instructional-design` propone, por apartado, lo que el alumnado verá (qué
  pantallas de la aplicación, qué esquemas, qué fotografías, qué vídeo), como ya propone las ayudas de trabajo:
  `design.yaml › sections[].visuals` y, en slxd, en `proposal-notes.md`; `coursekit sync` lo lleva a
  `course.yaml › units[].sections[].visuals` y al esqueleto de `content.md` (`<!-- visuals: … -->` bajo cada apartado), y
  `verify` avisa cuando un apartado tiene menos placeholders que visuales planificados. Lo visual pasa a ser una
  decisión firmada con el diseño. (M, por `sync`, el Excel del diseño y las dos skills.)

### B. Capturas de la aplicación real (M–G, decisivo en los cursos de software)

- **B1. `coursekit capture plan CODE`.** A partir de los recursos `interface` (y de A4, antes de escribir): qué aplicaciones
  enseña el curso, qué perfil y qué permiso faltan, en qué modo, con los comandos. `/new-course` lo dice en su resumen
  junto a `/define-theme`, `coursekit status` lo avisa como «siguiente paso» y el handoff lo lista **al empezar**, no al
  acabar: la persona da el permiso antes del paso de medios y las capturas se hacen en la misma pasada.
- **B2. Sesiones por aplicación, no por recurso.** `session_start` acepta varios ids del mismo perfil (o `save_shot` y
  `record_start` reciben el id), de modo que el agente recorre la aplicación una vez y toma en orden las capturas de toda
  una unidad; un solo guion por sesión (`approve script` firma la lista). Menos sesiones, más capturas. Toca
  `capture/session.py`, `mcpserver.py`, `media/__init__.py › capture_waiting` y la skill de medios.
- **B3. Las imágenes de los documentos del brief.** Las de las páginas web ya están en `brief/text/web/<sitio>/assets/`:
  falta listarlas en `brief/index.md` con su pie y su `alt` e indexarlas en `brief --find`. Las de los PDF (poppler
  `pdfimages` o `pypdf`) y de los Word y PowerPoint (del zip) hay que extraerlas a `brief/text/media/<documento>/`, con
  el pie y la página, y listarlas igual. El redactor puede señalar una en «Cómo se elabora» como material real de un
  recurso `interface`, y el agente de medios la adopta (`media adopt` con `--recipe screenshot --depicts interface` y el
  origen en el manifiesto). Solo se toman imágenes del brief o de la documentación oficial del fabricante (ver §4).
- **B4. Capturas que deja la persona.** Lo mismo para `brief/sources/*.png`: hoy solo se cuentan. Que `brief/index.md` las
  liste con su nombre y que la skill de redacción diga cómo nombrarlas en el placeholder; `media extract` las empareja por
  el título del placeholder (o la persona las deja ya en `media/recordings/<id>.png` cuando el id existe).
- **B5. El orden de las fuentes de una captura.** Para un recurso `interface`, en este orden: (1) una imagen del brief
  (B3, B4); (2) una imagen o una captura de la **documentación oficial** del fabricante (su centro de ayuda, su manual;
  perfil del navegador sin inicio de sesión), nunca de un blog, un foro u otra documentación ajena; (3) una captura que
  coursekit hace del **software instalado en el ordenador** (`coursekit capture`, con el permiso de B1); (4) si nada de lo
  anterior es posible, el recurso no se omite: se monta con la imagen provisional de B6 y su guion para una persona. El
  manifiesto guarda el origen de cada una (`source`: brief, documentación oficial con su dirección, captura local).
- **B6. Una imagen provisional en lugar de una nota.** Hoy un recurso sin producir se monta como una nota con su
  descripción (creator y html), y el curso se lee sin imágenes. En su lugar, coursekit genera para cada recurso visual
  pendiente una **imagen provisional** en el tema del curso (`media/placeholders/<id>.png`, con `media render`): el marco
  y la proporción de sus especificaciones, el tipo, el título y «Pendiente: captura de <aplicación>» o «Pendiente:
  imagen», sin nada que imite una interfaz. El montaje la pone en su sitio (en creator se sube como cualquier imagen, en
  el html va en el paquete), con un aviso en `assemble plan` y `build`, y el recurso sigue `pending` o `scripted` hasta
  que una persona o el agente pone el fichero real (`media set --file`) y se monta otra vez. La entrega (`delivery add`)
  avisa mientras quede alguna y sigue (la lista va en su resumen y en el del handoff). Así el hueco se ve, el diseño de la
  página no cambia cuando llega la imagen real y nada se omite. (P–M.)

### C. Vídeos de canales oficiales (M)

- **C1. Separar los canales oficiales de la política de hosts prohibidos.** `rules › videos › channels` (los canales
  oficiales del proyecto o del curso) independiente de `forbidden.allow_channels`, que lo sigue leyendo. Y
  `coursekit videos find CODE "<qué>"`: busca en esos canales con la API de datos de YouTube (`YOUTUBE_API_KEY`, cuota
  gratuita suficiente; `search.list` con `channelId`) y, sin clave, con el proveedor de `research` limitado a los dominios
  de los canales; imprime título, canal, duración, fecha e idioma, y el redactor propone con `videos propose`. La skill de
  redacción pone el vídeo oficial como **primera** opción de un tutorial de una aplicación, antes del placeholder.
- **C2. Incrustar el vídeo aprobado.** La línea `> **[Vídeo]** <dirección>` que ya escribe la importación pasa a ser un
  bloque de vídeo externo en los dos backends: en creator, `VIDEO` con `videoUrl` (o el `videoUrl` del ítem, dentro de un
  panel) y su transcripción; en el html, un `<iframe>` de `youtube-nocookie.com` con título, `loading` perezoso y un
  enlace de reserva (y una nota en `08-assembly.md` sobre los LMS sin salida a internet). `verify` solo lo
  admite cuando `videos check` lo tiene `approved` o `proposed`.

### D. Fotografías e ilustraciones sin creator (M)

- **D1. Fotografía con licencia en todos los proyectos, preferiblemente sin atribución.** Lo que coursekit ya tiene:
  - `creator-stock`: el buscador de creator (`search_stock_images`, que reúne Pexels, Pixabay, Unsplash y Freepik). Solo
    existe con el MCP de creator, por eso un proyecto con el backend html, o un handoff sin ese conector, se queda sin fotos;
  - la API de Magnific (`MAGNIFIC_API_KEY`, ya admitida): su catálogo es el de Freepik y tiene fotografías, pero coursekit
    solo lo usa para buscar ilustraciones SVG de los autores de la marca (`illustrations.search`) y para generar.

  Lo que se añade: `coursekit media stock CODE ID --photos --find "<términos>"`, que busca fotografías en los proveedores
  que tengan clave, con la misma salida para todos (miniatura, autor, licencia y si exige atribución):
  - **Pexels** (`PEXELS_API_KEY`, nueva; `coursekit setup` la pide como las demás y `doctor` la muestra): licencia sin
    atribución obligatoria, uso comercial;
  - **Magnific** con la clave que ya existe, filtrando fotografías (comprobar el filtro de tipo de contenido de su API):
    las de un plan premium no piden atribución; las gratuitas, sí.

  El orden lo fija `media.yaml › photos.providers` (por defecto `[pexels, magnific]`) y `photos.attribution: avoid`: se
  prefiere siempre un resultado que no exija atribución, y uno que la exige solo se toma cuando ningún otro sirve, y el
  agente dice por qué en su informe. `--take` descarga a `media/files/<id>.jpg`, pasa por `optimize` y escribe en el
  manifiesto `source` (proveedor, id, autor, licencia, dirección, `attribution: true|false`), como ya hace
  `magnific-stock`. Cuando la licencia exige atribución, el montaje la pone en el pie de foto (los dos backends; en
  creator, dentro del `caption`) y la escena `image` del vídeo la recibe como `credit`; cuando no la exige, no se pone
  nada. Receta `stock-photo` en `media.yaml › types.image`, detrás de `creator-stock` y delante de la generación, sin el
  límite `only: decorative`: una foto que muestra la situación del apartado es contenido, no adorno.
- **D2. Ilustraciones sin fuentes de marca.** `illustrations.search` con el autor opcional: sin
  `illustration-sources.json`, busca en todo el catálogo vectorial con `stock.color` y las palabras de estilo de la guía,
  y `media plan` ofrece `magnific-stock` con solo la clave.

### E. Iconografía (M–G)

- **E1. Un juego de iconos del proyecto, diseñado con su sistema de diseño.** El juego es siempre el del proyecto, nunca
  uno genérico:
  - si el sistema de diseño trae iconos, `coursekit brand` los indexa en `theme/branding/icons/index.json` (nombre,
    palabras clave del nombre y del `<title>` del SVG, tamaño) y hace una hoja de contacto (`icons.png`) para que el
    agente los **vea**; `coursekit media icons --find "lock"` busca en él;
  - si no los trae, o le faltan, `/define-theme` diseña el juego con las reglas de la guía de medios (rejilla, trazo,
    uniones, esquinas, zona útil, colores por rol), medidas sobre lo que el sistema de diseño sí tenga (sus componentes,
    su tipografía, sus formas), y lo guarda en `theme/branding/icons/` con el mismo índice; la persona lo firma con la
    guía. Los iconos que el agente de medios dibuja después (ya lo hace la skill) se suman al juego en lugar de quedarse
    en `media/files/icons/` de un curso.
  Para un icono que falta, el agente puede partir de la forma de un icono de un juego de licencia libre (Lucide, Tabler;
  licencia MIT, cuyo aviso se guarda en `theme/branding/icons/LICENSES.md`) y rehacerlo con el trazo, las esquinas, las
  uniones y la rejilla de la marca: la forma de partida no se usa tal cual. `coursekit media icons --base "lock"` lista
  candidatos de esos juegos (instalados una vez en el almacén de coursekit, como Remotion) para elegir la forma.
  Así `brand-icon` funciona en todos los proyectos y todos los iconos hablan el mismo lenguaje.
- **E2. Iconos en el contenido, donde creator los admite.** Con lo comprobado (§4), sin sintaxis en los títulos:
  - `:::note` con `kind: tip|warning|info|example` (palabra por idioma en `lang/<código>.yaml`): elige el icono del juego del
    proyecto para ese tipo (`media.yaml › icons.note`), que va como `customIconPath` del brick `NOTE`;
  - una lista con icono: `icon: check` en la línea anterior a una lista suelta, que va como `customIconPath` del brick
    `LIST` (la viñeta de todos sus ítems);
  - un icono por ítem de una colección: `icon: lock` bajo el `#### Título` del panel, que se monta como el medio del ítem
    (una imagen pequeña del icono, centrada) cuando el ítem no lleva otro medio;
  - los iconos de las instrucciones y del bloqueo de cada tipo de brick, una vez para todo el tema: `/define-theme` los
    sube del juego del proyecto y los fija en el tema de creator (`update_theme`), y el html los toma de la misma carpeta.
  Los ids son los del índice del juego del proyecto, en inglés y los mismos en todos los idiomas. El backend html pinta lo
  mismo (SVG en línea con `aria-hidden`). Cambia el formato: `content-format.md`, `verify`, `assemble`, `render.py`,
  `06-content.md` y la skill de redacción (un icono por ítem cuando los ítems son de la misma naturaleza, nunca adorno).
- **E3. Iconos en los vídeos.** Un átomo `Icon` en `videokit/atoms` que lee el mismo juego, y la escena `list` y `split`
  aceptan `icon` por ítem. Con E1 hecho, es pequeño.

### F. Montaje: disposiciones de imagen (M)

- **F1. Imagen junto al texto y galerías.** Dos o más placeholders seguidos sin texto entre ellos se montan como galería
  (`IMAGE_GALLERY` o `IMAGE_CAROUSEL` en creator, según el número; una rejilla de `figure` en el html). Un campo
  opcional del placeholder, `Disposición: junto al texto` (palabra por idioma en `lang/<código>.yaml`,
  `tests/test_content_words.py`), monta `IMAGE_TEXT` en creator y una figura flotada en el html. Comprobar antes los
  esquemas de esos bricks.
- **F2. Un recurso dentro de un panel.** Admitir el placeholder dentro de `accordion`, `tabs`, `carousel` (y de
  `flashcard-gallery`, en una cara): uno por panel, que se monta en el medio de ese ítem (`mediaType`, `imagePath`,
  `imageAlt`, `videoUrl`…; ver §4) en creator, y como su `figure` dentro del panel en el html. `media scan` ya lo numera.
  Es lo que permite «un paso, una captura» en el carrusel de un procedimiento. Mientras no esté hecho, `verify` debería
  fallar al encontrar uno (hoy no avisa).

### G. Importación (P)

- **G1.** `brief/import-report.md` lista las imágenes de cada paquete con su tamaño en píxeles y su peso, y marca las que
  parecen capturas (proporción de pantalla, pocos colores); la revisión de fidelidad y `/update-unit` preguntan si una
  captura es de la versión actual y, si no, `media redo --recapture` la manda a capturar de nuevo con B1.
- **G2.** Un fixture de pruebas con una galería de imágenes y un «image magnifier» de eXeLearning: el conversor copia cada
  `<img>` en línea, pero nadie ha comprobado que una galería salga entera y seguida (con F1 sería una galería).

### H. Medir la cobertura visual (P)

- **H1.** Una línea por unidad en `media plan`, en el resumen del handoff y en `coursekit status`: apartados con un
  recurso visual producido / total, recursos que esperan a una persona por tipo (capturas, vídeos). `assemble build` y
  `assemble plan` avisan de cada apartado que se monta solo con notas de placeholder.
- **H2.** `coursekit media report CODE`: la distribución por tipo y por unidad frente al plan visual de A4, para ver que un
  curso es pobre antes de montarlo.

## 3. Orden propuesto

1. **A1, A2, A3** (reglas y skills): sin ellas, lo demás no se usa.
2. **B6**: ningún recurso visual vuelve a omitirse; el curso montado enseña sus huecos.
3. **D1 y E1**: dan fotos e iconos a todos los proyectos, también sin creator.
4. **F2 y F1**: la captura por paso y las galerías (creator lo admite de forma nativa: ver §4).
5. **B1, B2 y A4**: que las capturas se planifiquen y se hagan en la misma pasada.
6. **C1 y C2**: vídeos oficiales buscados por el redactor e incrustados.
7. **E2 y E3**: iconografía en línea (cambio de formato: documentar en los dos idiomas y en el changelog).
8. **B3, B4 y B5**: el material real que ya existe, en el orden de fuentes decidido.
9. **G y H**.

Cada paso lleva lo que `AGENTS.md` pide: defaults comentados y sus `config/*.example.yaml`, docs en `docs/en` y `docs/es`,
línea en los dos changelogs, mensajes en `lang/messages/`, y las palabras nuevas del formato en todos los `lang/<código>.yaml`.

## 4. Decisiones

### Tomadas (2 de noviembre de 2026)

- **Origen de las capturas** (B3, B5): solo del brief o de la documentación oficial del fabricante; si no, una captura del
  software instalado en el ordenador; si tampoco, la imagen provisional de B6. Nunca de otra documentación ajena, y nunca
  se omite el recurso.
- **Iconos** (E1): el juego se diseña con el sistema de diseño del proyecto (sus iconos si los trae; si no, dibujados por
  `/define-theme` con las reglas de la guía). No hay juego genérico por defecto. Un icono que falta puede partir de la forma
  de un icono de un juego libre (Lucide, Tabler; MIT), rehecho con las reglas de la marca.
- **Imagen provisional en la entrega** (B6): la entrega avisa mientras quede alguna y sigue.
- **Fotografía** (D1): Pexels (clave nueva, `PEXELS_API_KEY`) y Magnific (la clave que ya existe), además de
  `creator-stock`; se prefieren las imágenes que no exigen atribución, y cuando una la exige va en el pie de foto.
- **Mínimos visuales** (A1): advertencias, nunca errores, poco exigentes, y con al menos una fotografía o captura por
  unidad, para que no se cumplan solo con infografías.

### Comprobado en creator (2 de noviembre de 2026, con `get_brick_type_schema`)

- **Vídeo externo** (C2): `VIDEO` acepta `properties.videoUrl` con un enlace https de YouTube o Vimeo (lo incrusta con el
  reproductor del proveedor) o de un fichero de vídeo; cualquier otra dirección se rechaza. Lleva su transcripción
  (`content.transcription`). Un vídeo aprobado de un canal oficial se monta como bloque, no como enlace.
- **Recurso dentro de un panel** (F2): no hace falta meter un `<img>` en el HTML. Cada ítem de `CAROUSEL`, `TABS` y
  `ACCORDION` tiene su propio medio: `mediaType` (`image`, `video`, `audio`) con `imagePath` e `imageAlt`, `videoPath` o
  `videoUrl` (y subtítulos y póster) o `audioPath`, y su posición frente al texto (`mediaPosition`, alineación). El
  carrusel tiene además medio en la portada y en el resumen. `FLASHCARD_GALLERY` admite una imagen en cada cara
  (`frontImagePath`, `backImagePath`). «Un paso, una captura» es nativo: un placeholder dentro de un panel se monta en el
  medio de ese ítem (uno por ítem). `TIMELINE` y `FLASHCARD_CAROUSEL` quedan por comprobar.
- **Imagen junto al texto y galerías** (F1): existen. `IMAGE_TEXT` (`imagePath`, `imageAlt`, `textPosition` izquierda o
  derecha, `imageWidth` 25 a 75 %, `verticalAlign`, el texto en `content.content` y el pie en `content.caption`);
  `IMAGE_GALLERY` (rejilla, columnas por tamaño de pantalla, `imageAlt` y pie por ítem) e `IMAGE_CAROUSEL` (una a una,
  pie por ítem). Las tres amplían la imagen al pulsarla. Además, `IMAGE` tiene `content.long_description`: la descripción
  larga de una infografía o un esquema para lectores de pantalla, que hoy no se usa.
- **Iconos** (E2): los títulos de ítem de `TABS`, `ACCORDION` y `CAROUSEL` son de una línea y solo admiten negrita y
  cursiva: **no caben iconos en los títulos**. Sí admiten icono propio, por nombre o como SVG subido (`customIconPath`, con
  `customIconTint` para pintarlo del color del texto): `NOTE` (con su posición: encima, debajo o al lado), `LIST` (el
  icono de la viñeta) y las instrucciones y el bloqueo de cada brick (`inst_icon`, `blocker_icon`). Los nombres que usa el
  tema por defecto (`Play`, `Lock`, `ListCollapse`, `PanelTop`) son los de Lucide. Consecuencia para E2: en creator, el
  icono va en las notas por tipo (consejo, aviso), en las viñetas de una lista y en las instrucciones, siempre como SVG
  subido del juego del proyecto (`customIconPath`), nunca por nombre de Lucide; un icono por ítem de una colección se
  logra con el medio del ítem (una imagen pequeña del icono), no en su título. El backend html hace lo mismo, para que los
  dos coincidan.

## Hecho

Hecho el 2 de noviembre de 2026, en el orden propuesto, sin publicar (en `Sin publicar` de los changelogs). Ruff y mypy
pasan; la suite de tests **no se ha pasado** (los casos nuevos están en `tests/test_visuals.py`, comprobados con un guion
aparte, no con pytest).

- **A1–A3.** Avisos de `verify` (`visual_per_words`, `photos_per_unit` con `photo_types`, `visual_mix_max` con
  `drawn_types`), nunca errores; la skill de redacción decide lo que se ve por tipo de contenido y la revisión añade ella
  misma los marcadores que faltan (hallazgo menor).
- **A4.** `design/visuals.yaml`, firmado con el diseño (`visuals_sha256`), en el esqueleto de `sync` y comprobado por
  `verify`, y con su hoja en el Excel del diseño.
- **B1.** `coursekit capture plan CODE`; `status` lo recuerda y el handoff lo imprime al llegar al paso multimedia.
- **B2.** `save_shot` con el `asset_id` de otra captura del curso; la repetición se lo salta.
- **B3–B5.** `brief/images.md` con las imágenes de las webs, de Word, PowerPoint y Excel y, con `pdfimages`, de PDF;
  `media adopt --depicts interface` guarda el origen. La documentación oficial que no está en el material entra por
  `brief/links.md` (el agente multimedia la añade tras `<!-- added by the media agent -->` y la lista en su informe), no con
  una captura en el navegador: así toda fuente pasa por el material y alguien la revisa. Descartado a propósito.
- **B6.** Imágenes provisionales (`coursekit media provisional`, `media set --provisional-path`, dibujadas solas en html);
  `delivery add` avisa y sigue.
- **C1–C2.** `rules › videos › channels`, `coursekit videos find` (YouTube con `YOUTUBE_API_KEY`, si no el proveedor de
  `research`); la línea `> **[Vídeo]** <dirección> <pie>` es un `VIDEO` con `videoUrl` en creator y un reproductor de
  `youtube-nocookie.com` en html.
- **D1–D2.** `coursekit media stock --photos` (Pexels con `PEXELS_API_KEY`, Magnific), primero las que no piden
  atribución, la atribución en el pie; `magnific-stock` busca en todo el catálogo sin fuentes de la marca.
- **E1–E3.** Índice y hoja de contactos del juego de iconos (`coursekit brand`), `coursekit media icons` (y `--base`, Lucide
  ISC, con su licencia en `LICENSES.md`), `/define-theme` diseña los que faltan; iconos de notas (`tipo:`) y paneles
  (`icono:`) como recursos `ICON-<nombre>`; átomo `Icon` y `marker: icon` en las escenas `list` y `split` (molécula
  `BulletList`). El catálogo
  genérico de iconos de creator deja de ser una fuente.
- **F1–F2.** Medio por panel en acordeón, pestañas y carrusel; `IMAGE_TEXT` con `Disposición: junto al texto`;
  `IMAGE_GALLERY` / `IMAGE_CAROUSEL` para imágenes seguidas; `verify` falla con un marcador que se perdería. La numeración
  de los marcadores cuenta ya los de dentro de los paneles (antes se desalineaba con el manifiesto).
- **G1.** Las skills de revisión y de actualización piden comprobar las capturas del paquete y volver a capturar las
  antiguas. **G2**: una galería de eXeLearning (imágenes seguidas, cada una enlazada a sí misma) sale con sus imágenes en
  orden, una por párrafo, y sin los enlaces de dentro del paquete, que se rompían (el fallo salió al hacer el fixture). El
  fixture es inventado: falta probarlo con un paquete real con galería.
- **H1–H2.** `coursekit media report CODE`; `media plan` empieza con una línea por unidad y el informe del handoff termina
  con ella.

### Por probar

- La suite completa, en las tres plataformas de la CI.
- En creator de verdad: el medio de los ítems, `IMAGE_TEXT`, las galerías, `videoUrl`, `customIconPath` de `NOTE` (con un
  PNG y con un SVG) y la imagen provisional subida.
- Pexels, Magnific (el filtro `filters[content_type][photo]`, sin comprobar) y la API de YouTube con claves reales.
- `pdfimages` en un PDF real con capturas.
