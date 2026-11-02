# Registro de cambios

[English](CHANGELOG.md)

Lo que cambia en cada versión de coursekit, de la más reciente a la más antigua. Qué está asentado, qué falta por demostrar y
qué no está hecho está en el estado del [README](README.es.md#estado). Las versiones se publican en PyPI como `slxd-coursekit`.

## Sin publicar

- Cursos más visuales. La redacción decide qué ve el alumnado según el tipo de contenido (una captura por cada paso sobre una pantalla real, una foto de la situación, una ilustración de una idea, un icono, una infografía para una comparación), y `verify` avisa, sin fallar nunca, de un apartado largo con pocos visuales, de una unidad sin fotografía ni captura y de una unidad cuyos visuales son casi todos infografías y esquemas (`content.visual_per_words`, `photos_per_unit`, `visual_mix_max`). La revisión con IA añade los marcadores que faltan en lugar de solo proponerlos.
- Un recurso visual por producir (una captura que espera a una persona, una grabación, una imagen sin generador) nunca se queda fuera del curso: va como una imagen provisional con el tema, su título y lo que falta, en los dos backends (`coursekit media provisional` y `media set --provisional-path` para creator). `delivery add` avisa de las unidades que se entregan con ellas.
- Fotografías con licencia en todos los proyectos, también sin creator: `coursekit media stock CODE ID --photos` busca en Pexels (clave nueva `PEXELS_API_KEY`, sin atribución) y en las fotografías de Magnific, primero las que no piden atribución; una fotografía que la pide la lleva en su pie.
- El juego de iconos del proyecto: `coursekit brand` indexa los iconos del sistema de diseño (`icons/index.json` y una hoja de contactos), `/define-theme` diseña los que le faltan a la marca, los iconos que dibuja el agente multimedia se suman al juego y `coursekit media icons CODE --find` busca en él. Un icono que falta puede partir de la forma de un icono libre (`--base`, Lucide), siempre redibujado con las reglas de la marca. El catálogo genérico de iconos de creator deja de ser una fuente.
- `coursekit media stock` busca en todo el catálogo de ilustraciones cuando la marca no tiene fuentes de ilustraciones.
- Cada medio en su sitio: un marcador dentro de un panel de un acordeón, unas pestañas o un carrusel pasa a ser el medio de ese panel (una captura por cada paso de un procedimiento), un marcador de imagen con `Disposición: junto al texto` va al lado de su párrafo, y las imágenes escritas una tras otra van juntas en rejilla o en un carrusel de imágenes, en creator y en el backend html. `verify` falla con un marcador que se perdería dentro de otra directiva. La numeración de los marcadores de un apartado cuenta ya los de dentro de los paneles, como hace el manifiesto.
- `coursekit capture plan CODE`: qué recursos esperan una captura de una aplicación real y qué falta para hacerlas (la captura activada, el permiso, la sesión de un perfil), con los comandos; `status` y el handoff lo recuerdan a tiempo. Una sesión de captura hace las capturas de otros recursos en el mismo recorrido (`save_shot` con su `asset_id`).
- El plan visual del diseño (`design/visuals.yaml`): lo que ve el alumnado en cada apartado, decidido por el agente de diseño y firmado con el diseño; `sync` lo muestra en el esqueleto y `verify` avisa cuando un apartado lleva menos que su plan. El Excel del diseño lleva una hoja con el plan visual.
- Vídeos de canales oficiales: `coursekit videos find CODE "<qué>"` busca en los canales oficiales del proyecto (`rules › videos › channels`; con `YOUTUBE_API_KEY`, la API de YouTube, si no el proveedor de búsqueda de `research`), y una línea `> **[Vídeo]** <dirección> <pie>` pasa a ser un reproductor en los dos backends (el reproductor de YouTube con privacidad mejorada en html, con la dirección debajo) en lugar de un enlace.
- Iconos en el texto, del juego de iconos del proyecto: una `:::note` con `tipo: consejo|aviso|información|ejemplo` (o `icono:`) lleva el icono de su tipo, y un panel de un acordeón, unas pestañas o un carrusel con `icono: <nombre>` lo lleva encima de su texto, en creator y en html. `media extract` toma cada icono del juego como un recurso `ICON-<nombre>`, que se sube a cada unidad que lo muestra.
- Un átomo `Icon` para los vídeos (un icono del juego del proyecto pintado con un color del tema), y `marker: icon` en las escenas `list` y `split` (y la molécula `BulletList`), cada elemento con su icono.
- `coursekit media report CODE`: cuánto se ve de cada unidad (apartados con un visual producido, visuales por tipo producidos, pendientes y planificados); `media plan` y el informe del handoff lo resumen.
- La importación de eXeLearning conserva las imágenes de una galería en su orden, una por párrafo, sin los enlaces a los ficheros de dentro del paquete que se rompían en el curso.

## 0.8.0 — 2026-11-02

- La revisión pide un procedimiento como carrusel, una diapositiva por paso, igual que la redacción (aún pedía pasos numerados), y en un curso importado quien redacta usa `research` solo para comprobar un dato o encontrar la documentación de referencia.
- La documentación del montaje y la entrega se parte en tres capítulos: [Montaje](docs/es/08-assembly.md), [Entrega y publicación](docs/es/09-delivery.md) y [Revisión del cliente](docs/es/10-client-review.md); la resolución de problemas pasa a ser el capítulo 11.
- `verify` dice la familia de cada aviso (`structure`, `words`, `style`, `language`, `readability`, `media`, `activities`, `simulations`, `assembly`), admite `--only` e `--ignore` para ver solo algunas (una comprobación parcial nunca cambia el estado), resume los errores y avisos de cada unidad cuando comprueba varias e imprime JSON con `--json`. `status`, `doctor` y `media check` imprimen JSON con `--json` también, para los agentes.
- `coursekit help COMMAND`: las opciones de un comando y su apartado de la referencia de comandos, en el idioma de la persona.
- Todos los comandos arrancan antes: cada uno carga solo los módulos que usa (`coursekit --version` tarda más o menos la mitad), y la salida de ffmpeg, git y los demás programas se lee en UTF-8 también en una consola de Windows.
- MarkItDown, que convierte los documentos del brief y del material de marca, pasa al extra opcional `docs`: la instalación base pasa de 48 paquetes a 7, unos 250 MB menos. Sin él, `brief` sigue leyendo Markdown, texto, paquetes de eXeLearning y enlaces web. **Para seguir convirtiendo PDF, Word o PowerPoint tras actualizar:** `uv tool install --force "slxd-coursekit[docs]"` (con `capture` también, nombra los dos: `[docs,capture]`).
- Todo mensaje que pide un extra da el comando con los extras ya instalados, porque reinstalar con uno quita los demás. `doctor` pide `docs` solo cuando hay documentos que convertir, y avisa cuando hay instalado más de un paquete de OpenCV.
- `coursekit config --check`: las claves de `config/*.yaml`, `project.yaml` y cada `course.yaml` que coursekit no lee (mal escritas o de una versión anterior), cada una con la clave que probablemente se quería poner.
- coursekit funciona con Python de 3.12 a 3.14, también el extra `capture`: su OCR pasa a ser `rapidocr` 3 (lleva sus modelos y lee como una sola línea un nombre repartido en varias cajas) y su OpenCV el headless, que en Linux no necesita ninguna biblioteca gráfica.
- Las opciones de las preguntas se barajan para cada alumno, en la práctica y en las evaluaciones (`delivery › shuffle_options`, por proyecto, curso y pregunta con `barajar: sí|no`), en creator, el backend html y Moodle XML. El banco de preguntas dice cómo activar el barajado en el LMS, porque no puede llevar el orden él mismo.
- `verify` falla con un feedback que nombra una opción por su posición o su letra, y la redacción pide que todo feedback diga por qué. También avisa de un objetivo citado por su identificador en el texto que lee el alumno, de una lista con títulos que va como pestañas o acordeón, de pasos numerados que van como carrusel, del reverso de una tarjeta demasiado largo y de un tipo de recurso que no puede ser decorativo.
- El plan de creator envía los campos de una línea (las opciones de una pregunta, los títulos de los paneles) sin código en línea, enlaces ni saltos de línea, para que se aplique tal cual; `assemble plan` y `verify` avisan de cada campo cambiado.
- `coursekit media gallery CODE`: una página con todos los recursos de un curso, dónde va cada uno y cómo se hizo; con `--serve` se mantiene al día mientras se producen.
- Un gráfico con puntos muestra su imagen una sola vez, y su imagen es una base ligera, no una infografía.
- Una sesión de navegador con escenario sirve el sitio del escenario en local, sin perfil ni servidor que arrancar a mano.
- Captura de terminal con caracteres anchos, un servidor de captura que no se cae y un handoff que se para con su resumen entero.
- `coursekit media redo --recapture`: un recurso que muestra una interfaz real olvida su captura y se vuelve a grabar; las grabaciones viejas se apartan para que no se vuelvan a usar.
- `handoff.media_tools` admite `"*"`: el agente de media puede ejecutar cualquier programa, y lo siempre denegado sigue denegado.

## 0.7.0 — 2026-10-19

- Apoyo visual de los apartados: la introducción y el resumen llevan siempre una imagen, una ilustración, un icono o una infografía; un apartado de contenido lleva uno o dice por qué no, y `verify` lo comprueba. Tipos de recurso nuevos `illustration` e `icon`.
- Modo terminal: las esperas del programa se aceleran (nunca se cortan), los capítulos marcan dónde se para una demo de terminal, una grabación puede tener varias partes (una terminal y un navegador) y las capturas que aprobó el handoff se revisan en una página.
- Los zooms de una grabación de pantalla son solo para detalles, encuadrados por la caja del elemento y con una marca que se lee.
- La ayuda de `coursekit media` ya no falla por un `%` en sus textos.
- Los tests pasan en Windows, y la CI comprueba los tipos de los vídeos.

## 0.6.0 — 2026-10-19

- Criterio pedagógico en la redacción. Cada apartado de contenido de un curso expositivo sigue un ciclo (`rules › expository.cycle`: un problema del trabajo del público, activación de lo que ya sabe, un ejemplo resuelto, práctica con menos ayuda cada vez, integración en su trabajo; un proyecto o un curso puede quitar cualquier parte), que comparten la introducción y el resumen de la unidad. La redacción sigue reglas de carga cognitiva, `verify` avisa de los tramos de prosa largos (`content.chunk_max_words`) y la revisión tiene un criterio de pedagogía.
- Ayudas de trabajo (`job_aid`): una lista de comprobación o una guía rápida que el alumno descarga en PDF, escrita por la redacción en su recurso e impresa con una plantilla del tema (`theme/templates/job-aid.html`, firmada con la guía de estilo de los medios; `coursekit theme sample` imprime una muestra para ajustarla), etiquetada para lectores de pantalla y montada como descarga en los dos backends.
- Crucetas en las imágenes con puntos (`coursekit media anchors`): dónde va cada punto de un gráfico etiquetado y cada zona activa de una simulación, dibujado en la imagen desde el contenido para que quien revisa lo vea y pueda pedir moverlo; `verify` falla cuando dejan de coincidir.
- Permisos de captura del proyecto, ampliables por curso, con varios modos. El handoff firma los guiones de lo que se puede capturar, vuelve a grabar tras el montaje y, en un curso entregado, dice cómo grabar lo que el permiso deja capturar.
- Modo terminal: una shell propia en un escenario del curso que prepara el agente de media (un proyecto con datos inventados, montado de cero antes de cada toma), grabada mientras ocurre en un `.cast`, un vídeo o una captura, con su salida tapada en el texto.
- `/define-theme` completa lo que falta en un tema ya definido.
- Retratos compartidos entre unidades en creator.
- La salida de coursekit va siempre en UTF-8, también en la consola cp1252 de Windows.

## 0.5.0 — 2026-10-18

- Lo aprendido en un curso piloto completo. Cada curso guarda un registro de lo que decidieron las personas y de los rótulos de interfaz que comprobaron (`decisions.md`), que respetan la redacción y la revisión, y el revisor comprueba cada pendiente contra el estado actual antes de repetirlo.
- `verify` avisa de una actividad que no está escrita con la directiva de su tipo, de una pregunta del test que repite una situación de la práctica y de un error de una simulación sin consecuencia; las normas de redacción cubren las preguntas de ordenar con un solo orden, la retroalimentación y la interfaz actual.
- El manifiesto de recursos se bloquea mientras se escribe (agentes en paralelo), `media render` reintenta el navegador, `brief` convierte los PDF enlazados, la guía de estilo de los recursos cita cada línea de `notes.md` (y `approve media-style` avisa de las que faltan), los hablantes pueden ir sin retrato o con un avatar de la marca, y se firman varios guiones a la vez.

## 0.4.0 — 2026-10-18

- Vídeos como datos (`coursekit video`): un montaje de escenas en el tema del curso, con una biblioteca de átomos, moléculas y escenas que amplían el proyecto y cada curso, y cada escena dura lo que su voz. Las escenas y las capas son configurables y siguen la marca del proyecto (`config/video.yaml`); `coursekit video gallery` las pinta todas con el tema y el estilo del curso, y `coursekit video export` escribe la línea de tiempo para DaVinci Resolve, Final Cut o Premiere.
- Revisión de los audios y vídeos producidos (`coursekit media check`: sonoridad, subtítulos demasiado rápidos para leerlos, lo que está en pantalla y no se dice), su transcripción accesible y su pista de descripciones (`coursekit media transcript`), una hoja de contactos para mirar un vídeo sin reproducirlo (`coursekit media sheet`) y zooms de una grabación de pantalla que siguen a la locución (el componente `Screencast`).
- La voz de Gemini TTS (proveedor `gemini`, con indicación de estilo y el modelo fijado en cada curso), a mitad de precio: en el nivel `flex` por defecto, o en batch para todo un curso (`coursekit tts-batch`: en cola con `--batch`, recogido horas después, también por el handoff). Los guiones largos de Azure, Google y Gemini se unen como audio sin comprimir y se codifican una sola vez. La voz del proyecto la heredan los cursos que no fijan la suya.
- La marca en los recursos. `coursekit brand` lee el material de marca que se deja en `theme/branding/` (un libro de marca, un Storybook entero, la web de la empresa observada en un navegador) y saca sus fuentes, logos y tokens; el agente del theme escribe con él la guía de estilo de los recursos, que firma una persona una sola vez para todos los cursos del proyecto (`coursekit approve media-style`), y propone el color de la marca para cada rol que la plataforma no tiene (`project.yaml › theme.roles`, `coursekit theme roles`). Las fuentes de la marca van dentro de los vídeos y de los SVG exportados a PNG.
- Fuentes de ilustraciones de la marca. La página de Magnific de un autor cuyas ilustraciones encajan con la marca va en `theme/branding/links.md`; `coursekit brand` guarda vistas previas de su obra como referencia del estilo, y `coursekit media stock` busca entre sus ilustraciones la que necesita un concepto, la toma en SVG y la recolorea a la tinta y el papel de la marca (`media › stock`), con su origen y su licencia en el manifiesto. Las imágenes decorativas salen primero del catálogo; las necesarias se generan.
- Dónde van las evaluaciones (`delivery › assessment`): dentro de cada unidad, o aparte en un paquete propio después de las unidades (`placement: separate`); y sus preguntas como lecciones de los paquetes o como banco de preguntas que importa el LMS (`format: aiken | gift | moodle-xml | qti`: con el backend creator lo exporta creator desde un contenido propio, con html lo escribe `coursekit delivery questions`), con `verify` rechazando los tipos de pregunta que el formato no admite. Las unidades sin evaluación pueden calificarse por completado.
- Lenguaje inclusivo (`rules › inclusive_language`: `none`, `neutral` por defecto, `split`, `slash`): lo siguen el diseño, la redacción y la revisión, y `verify` avisa del masculino genérico y de las barras con un léxico por idioma.
- El mismo Excel de revisión para un diseño hecho en slxd que para uno local (`coursekit design CODE` lo escribe a partir de `matrix.json` y `validation.json`): competencias, objetivos con dónde se desarrollan, se practican y se evalúan, horas y palabras mínimas por apartado, calificación de los tests, errores comunes y la validación con los avisos esperados aparte. El Excel que exporta slxd se guarda como copia, en el idioma de la persona.
- Fuentes oficiales con una API de búsqueda web (`coursekit research`: Exa, Perplexity, Brave o Tavily, elegida en el `.env`). El diseño busca con ella la documentación de referencia y quien redacta la fuente de un dato que el brief no tiene; solo propone direcciones, en el idioma del curso cuando el sitio tiene traducción, y entran en el curso por `brief/links.md`. `coursekit brief` abre con el navegador de la máquina las páginas oficiales que rechazan una descarga directa.
- Capturas de aplicaciones reales (`coursekit capture`): perfiles de las aplicaciones web y el permiso para capturar, que da solo una persona; el tapado de los datos personales de una grabación que aporta una persona (`capture redact`, `review`, `approve`, `reject`: OCR, revisado y aprobado por una persona); un agente que maneja una aplicación web en el navegador con los datos personales sustituidos en pantalla (`capture serve`, un servidor MCP); su vídeo grabado al repetir los pasos a ritmo humano (`capture replay`); el propio curso (su paquete html servido en local o su enlace de revisión en creator, sin iniciar sesión); y la ventana de un programa de escritorio, tapada sobre los píxeles, en macOS, Windows y Linux con X11.
- El guion de una grabación o de un vídeo se aprueba antes de hacerlo, y un vídeo oficial propuesto frena su recurso.
- Las galerías llevan la interfaz de Studio LXD y hablan el idioma de la persona. Los conectores MCP del proyecto, el paquete npm de la marca y el idioma de la conversación se fijan por proyecto.

## 0.3.0 — 2026-10-16

- Migrar un curso que ya existe desde paquetes de eXeLearning: un lector y un conversor (`coursekit import`), un modo migración que reutiliza el texto, `/update-unit` con una comprobación opcional de que el contenido está al día, y un handoff que se para donde debe decidir una persona.
- Vídeos de canales oficiales en sitios que prohíben descargarlos (`coursekit videos`).
- Optimización de imágenes y vídeo, configurable, con `coursekit media optimize` y en el backend html.
- La interfaz de una aplicación real nunca se inventa: `--depicts`, recetas de material real y guion de grabación.
- `coursekit media redo --clean`: el recurso olvida su fichero, su texto alternativo, su transcripción, sus subtítulos y su herramienta.
- Catálogo y carpeta espejo más baratos: caché por curso, escritura solo cuando cambia y publicación aplazada durante las sesiones de agentes.

## 0.2.1 — 2026-10-15

- `/new-course` pregunta el enfoque del curso cuando no se indica `--approach`.

## 0.2.0 — 2026-10-14

- El enfoque basado en decisiones: el enfoque del curso y sus reglas, una biblia narrativa en el diseño, simulaciones (`:::scenario`, `:::conversation`) con pieles de aplicación, escenas en otras aplicaciones, retratos y voces por personaje, audio por escena, mecánicas (diagnóstico, investigación, bandeja y reparto), tiempo estricto y bloques adaptativos (`:::if`); juegos y pieles del proyecto en el backend html; `coursekit paths` informa de los caminos de una simulación.
- Simulaciones en creator con el protocolo `slxd-embed`: la simulación que abre un apartado retiene la lección hasta su final, e informa de su estado, su nota y sus decisiones.
- Diseño instruccional local, sin slxd ni creator.
- `coursekit preview`: las unidades html con un LMS simulado; `assemble check` juega el paquete html en un navegador antes de entregarlo.
- Errores típicos: el diseño los recoge, el contenido los muestra y `verify` lo comprueba.
- Comprobaciones de legibilidad y reflexión, informe de corrección en el handoff y búsqueda en el material de partida.
- `coursekit media fit` y `render`: tamaño y SVG en local, sin créditos. Modelo, resolución y versiones por receta de multimedia.

## 0.1.4 — 2026-10-11

- Un estilo de la casa para los recursos.

## 0.1.3 — 2026-10-11

- coursekit avisa cuando se publica una versión nueva.

## 0.1.2 — 2026-10-10

- La publicación en PyPI ya no depende de una variable del repositorio.

## 0.1.1 — 2026-10-10

- Los tests ya no dependen de que `claude` esté instalado.

## 0.1.0 — 2026-10-10

Primera versión publicada.

- Proyectos: `coursekit init` e `init --update`, la raíz del proyecto y la configuración en capas; los proyectos siguen al coursekit instalado por sí solos.
- El motor de cursos: `new`, `status`, `sync`, `outline`, `verify`, `reviewed`, `approve`, `brief`, `rules`.
- Agentes: skills, comandos y agentes para Claude Code, opencode y Codex (`coursekit agents`), y `write`, `review` y `run` para lanzar el agente de cada rol.
- `coursekit setup` y `doctor`.
- Multimedia: `coursekit media`, `voice`, `tts` y `subtitles`, con agentes de media sin interfaz limitados a los programas de sus recetas.
- Montaje en creator (`coursekit assemble`, `directives check`) y el backend html, que construye un paquete SCORM por unidad.
- Entrega: descarga del paquete, registro del cierre, catálogo, `publish` y la carpeta compartida con su hoja de seguimiento.
- Revisión del cliente, elección del theme al crear el proyecto y calificación de cada test desde el diseño.
- El modo handoff: pausa para el material de partida, registros firmados de los agentes, enlaces de revisión tras la subida y `--new-version` para reabrir un curso entregado.
