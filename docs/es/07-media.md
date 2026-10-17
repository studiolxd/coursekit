# Producción multimedia

Cómo los recursos multimedia reservados en el contenido se convierten en recursos producidos: el manifiesto, las opciones de producción, la locución y los subtítulos, los tokens del tema y las herramientas que necesita cada tipo.

## Recursos multimedia y tipos

Un recurso multimedia se escribe en `content.md` (formato en [06-content.md](06-content.md#recursos-multimedia)). Su tipo es uno de ocho tipos de recurso. Cada tipo tiene un **id** en inglés, igual en todos los cursos, que es lo que usan la configuración (`config/media.yaml › types` y `uses_theme`, `config/rules.yaml › content.placeholder_types`), el manifiesto multimedia (`media/manifest.yaml › assets[].type`), la salida de `coursekit media plan` y el control del tema. Lo que la persona **escribe** en el recurso reservado es la palabra del idioma del curso para ese tipo (por ejemplo `Infografía` en un curso en español e `Infographic` en uno en inglés); la tabla que relaciona cada id con sus palabras está en [06-content.md](06-content.md#recursos-multimedia). La palabra del otro idioma es un error de `coursekit verify` que enumera las palabras válidas.

| Id | Significado | Opciones, por orden de preferencia (qué necesita cada una) |
|---|---|---|
| `image` | Imagen | `creator-stock` (herramienta MCP del agente `search_stock_images`; solo imágenes decorativas) · `magnific-stock` (`MAGNIFIC_API_KEY` y fuentes de ilustraciones; solo ilustraciones de concepto) · `magnific-api` (`MAGNIFIC_API_KEY`) · `magnific-mcp` (herramienta MCP del agente `images_generate`) · `agent-svg` (nada) · `creator-stock` (cualquier imagen) · `screenshot` (solo una interfaz real: una captura de una persona) |
| `infographic` | Infografía | `agent-svg` (nada) · `magnific-api` |
| `diagram` | Esquema o diagrama | `agent-svg` |
| `animated_gif` | GIF animado | `vhs` (comando `vhs`; solo contenido de terminal) · `agent-svg-animated` (nada; con el backend creator se sube como paquete EMBED, mira [Subida](#subida-a-creator)) · `remotion-gif` (`node` y `tools/remotion/node_modules`) |
| `terminal_demo` | Demo interactiva en terminal | `asciinema` (comando `asciinema`; solo contenido de terminal) · `vhs` (alternativa en vídeo; solo contenido de terminal) |
| `video` | Vídeo | `remotion` (`node` y `tools/remotion/node_modules`) · `vhs` (solo contenido de terminal) |
| `audio` | Audio | `voice` (nada): la cadena de voz de más abajo |
| `simulation` | Simulación interactiva | `agent-html` (nada): HTML/JS autocontenido que usa `tokens.css` |

«Nada» significa que lo produce el propio agente. El agente usa la primera opción que realmente pueda ejecutar y la anota en el manifiesto. Las descripciones de las opciones que imprime `coursekit media plan` salen de la configuración y están escritas en inglés; un proyecto puede escribir las suyas en `config/media.yaml`.

## El manifiesto multimedia

`courses/PWD/media/manifest.yaml` tiene una entrada por cada recurso multimedia. Cada recurso tiene un id `U<unidad>-S<apartado>-M<k>`, donde `k` es la posición del recurso dentro de su apartado (`U1-S2-M1` es el primer recurso del apartado 2 de la unidad 1). El montaje usa los mismos ids para sustituir un recurso por su multimedia producida. El `type` de cada entrada es el id del tipo (`image`, `infographic`…), sea cual sea el idioma del curso. Los ids son posicionales: añadir un recurso antes de otro renumera los siguientes.

| Comando | Qué hace |
|---|---|
| `coursekit media extract CODE` | Sincroniza el manifiesto con los recursos de todos los `content.md` e imprime `manifest: 3 recursos (pending 3)` |
| `coursekit media plan CODE` | Por cada recurso `pending` o `scripted`, lista las opciones disponibles en este equipo |
| `coursekit media providers` | Lista todas las opciones de todos los tipos, de voz y de subtítulos con su disponibilidad (`disponible`, `falta`, `MCP del agente`) |
| `coursekit media set CODE ID …` | Actualiza un recurso (lo usa el agente de multimedia mientras produce) |

Reglas de `extract`: un recurso nuevo se añade como `pending`; uno existente conserva su avance, salvo que haya cambiado su tipo, título, descripción o especificaciones, en cuyo caso vuelve a `pending` con una nota; un recurso cuyo recurso reservado ha desaparecido del contenido se conserva con el estado `orphaned`, y sigue `orphaned` (también si el recurso reservado vuelve igual) hasta que cambien su tipo, título, descripción o especificaciones, lo que lo devuelve a `pending`.

`media set` acepta `--status`, `--recipe` (la opción usada), `--file`, `--asset-path` (ruta en la plataforma), `--alt`, `--transcript`, `--subtitles-path` y `--made-with`, y `--force` (consulta [El control de los recursos](#el-control-de-los-recursos)). Para un fichero descargable de acompañamiento (por ejemplo un PDF) usa `--download FICHERO`, junto con `--download-title` y `--download-asset-path`. Si las especificaciones de un recurso producido mencionan una descarga (`pdf`, `descargable`, `descarga`, `docx`, `xlsx`, `pptx`…) y no hay ninguna registrada, `media plan` avisa. Con el backend creator avisa también cuando el recurso está `uploaded` y una descarga registrada aún no tiene `--download-asset-path` (súbela con `request_asset_upload`, de tipo `attachment`).

### Campos de una entrada

Los ficheros de la multimedia de un curso están en `courses/PWD/media/`: `manifest.yaml`, `scripts/` (los guiones), `files/` (los ficheros producidos) y `src/` (las fuentes: los guiones `.tape` y los paquetes de simulaciones y demos). Cada entrada de `manifest.yaml` tiene estos campos:

| Campo | Contenido |
|---|---|
| `id`, `unit`, `section`, `type` | El id del recurso, los números de su unidad y su apartado, y el id de su tipo |
| `title`, `description`, `how`, `specs` | Los campos del recurso reservado tal como están escritos en el contenido: título, descripción, cómo se elabora y especificaciones |
| `status` | Uno de los estados de abajo, o `orphaned` |
| `note` | Por qué `extract` devolvió el recurso a `pending` |
| `recipe`, `made_with` | La opción usada y la herramienta o el modelo que produjo el recurso (`--recipe`, `--made-with`) |
| `file`, `alt`, `transcript`, `subtitles_path` | El fichero producido y su texto alternativo, transcripción y subtítulos (`--file`, `--alt`, `--transcript`, `--subtitles-path`) |
| `asset_path` | La ruta del recurso en la plataforma una vez subido (`--asset-path`) |
| `downloads` | Los ficheros descargables: `file`, `title`, `asset_path` y `size` de cada uno |
| `theme` | La huella de los tokens del tema con los que se hizo el recurso ([El control de los recursos](#el-control-de-los-recursos)) |
| `depicts` | Qué muestra el recurso: `interface` (una aplicación real) o `concept` (`--depicts`; [La interfaz de una aplicación real no se inventa](#la-interfaz-de-una-aplicación-real-no-se-inventa)) |

### Imágenes de las simulaciones

`extract` añade también las imágenes de las simulaciones (`:::scenario`, `:::conversation`), una por id en todo el curso,
con un `kind`:

| `kind` | Id | Qué es |
|---|---|---|
| `background` | `BG-<descripción>` | El fondo de una escena (`background` de la escena), 1920x1080, sin texto dentro |
| `layer` | `LAYER-<descripción>` | Un objeto sobre un fondo (`layers.image`), PNG transparente |
| `portrait` | `CHAR-<NOMBRE>` (también la expresión `neutral`) y `CHAR-<NOMBRE>-<EXPRESIÓN>` | Un personaje de la biblia narrativa, base y con cada expresión que usan las simulaciones, transparente, con el `look` de la biblia en su descripción |

Se producen en el estilo visual del curso (`media › visual › style`, ver [Configuración](04-configuration.md#media-opciones-de-producción)), que imprime `coursekit media plan`. Sin generador de imágenes, `plan` avisa y el estilo es `visual.fallback` (`flat`), dibujado en SVG por el rol de **ilustración**: `coursekit run produce-media <CODE> --role illustration`.

Una simulación con `audio: true` añade un `VO-<SIMULACIÓN>-<ESCENA>` por escena (tipo `audio`, kind `voice`): su texto en `narration` y, en una conversación, el `character` que lo dice. `coursekit media narrate <CODE>` los produce todos con las voces configuradas (no hace falta ningún agente), y una escena cuyo texto cambia vuelve a `pending`.

Con el backend **creator** `extract` añade también `SIM-<ID>` (kind `package`, tipo `simulation`): el paquete de cada simulación, que se construye con `coursekit media embed <CODE> SIM-<ID>` cuando sus imágenes están producidas (ver [Simulaciones en creator](08-assembly-and-delivery.md#simulaciones-en-creator)).

**Lámina de estilo.** Antes, el agente de multimedia produce una muestra en `courses/<CODE>/media/style/` (un fondo, un personaje en varias expresiones y algunos objetos) y una persona la firma con [`coursekit approve style <CODE>`](03-commands.md#coursekit-approve). Hasta entonces `coursekit media set … --status produced` rechaza esas imágenes (salvo con `--force`) y `plan` avisa. En modo handoff el agente de multimedia produce la muestra y coursekit la firma como Coursekit Handoff. El montaje toma cada imagen por su id; mientras no está producida, la simulación funciona sin ella (los retratos se sustituyen por iniciales).

### Retratos de los personajes de un diálogo

`extract` añade además un recurso `image`, con id `CHAR-<NOMBRE>` (`CHAR-DANIEL`), por cada personaje que habla en una directiva `:::dialog`: un personaje tiene un solo retrato en todo el curso, hable donde hable. El agente de multimedia lo produce como cualquier otra imagen (una ilustración plana dibujada como SVG y exportada a PNG, una imagen generada con un proveedor o una fotografía con licencia de una persona), cuadrada, como un busto sobre un fondo liso de un color de la paleta del theme, y nunca deja a un personaje con una inicial. Una vez subido, el montaje lo pone en el diálogo como avatar de ese personaje, con el texto alternativo del recurso; hasta entonces avisa `dialog: el retrato de 'Daniel' aún no está subido`.


### La interfaz de una aplicación real no se inventa

Un vídeo, imagen, GIF, infografía o diagrama que muestra la pantalla de una aplicación, plataforma, programa, sitio web o app reales (un tutorial, un menú, un cuadro de diálogo, "haz clic aquí") se hace solo con **material real**: nunca se dibuja, anima, genera ni recrea, ni de forma aproximada ni con nombres ficticios, porque el alumno lo toma por lo real y busca botones que no están o que se llaman de otra manera. El único sitio donde una interfaz inventada está bien es una simulación de decisión (`:::scenario`, `:::conversation`), donde la aplicación es ficticia.

Cada recurso de los tipos de `media › depicts › required_for` (imagen, infografía, diagrama, GIF, vídeo) dice qué muestra, con `coursekit media set CODE ID --depicts interface|concept`: `concept` para una idea, un proceso, un diagrama o una escena (se puede dibujar, generar o animar), `interface` para una pantalla real. En caso de duda, `interface`.

- `coursekit media plan` ofrece para un recurso `interface` solo las opciones que parten de material real (`shows: interface`, más `imported`, `vhs` y `asciinema`), y avisa de que un recurso que no ha dicho qué muestra tiene que decirlo.
- `coursekit media set --status produced` (o `uploaded`, la primera vez) rechaza una receta generada para un recurso `interface`, y para un recurso de esos tipos hecho con una receta generada que no ha dicho qué muestra. No tiene `--force`. Los recursos ya producidos no se vuelven a preguntar.
- Lo que se puede hacer con un recurso `interface`, por este orden: **un vídeo de un canal oficial** (no es un recurso: es una dirección en el contenido, ver [`coursekit videos`](03-commands.md#coursekit-videos)); **material real que aporta una persona** en `courses/CODE/media/recordings/<id>.mp4` o `.png` (un vídeo se compone sobre la grabación real con locución, subtítulos, zooms y resaltados, receta `screen-recording`; una imagen es una captura real que solo se recorta y se marca, receta `screenshot`; un GIF es la grabación cortada y convertida); o, si todavía no hay, **no se produce nada**: el agente escribe el guion para la persona en `media/scripts/<id>.md` (qué mostrar, la cuenta y la versión que usar, los pasos con las etiquetas como las muestra la aplicación, la locución, el fichero que entregar) y deja el recurso en `scripted`.
- **El orden se cumple, y el guion se aprueba antes.** Un vídeo oficial propuesto para el recurso (`coursekit videos propose … --for <id>`) impide capturarlo o locutarlo mientras espera a una persona, y para siempre si se aprueba. Y el guion de una grabación o de un montaje (sus pasos y su locución) lo aprueba una persona, `coursekit approve script CODE --asset ID`, antes de capturarlo o locutarlo, y de nuevo si cambia (`rules › review › scripts`; el handoff lo firma por sí solo).
- **El propio curso**: un vídeo o una captura del curso (cómo se navega, una demo para el cliente) se graba con el perfil incorporado `course` y `start: unit:N`: el paquete del backend html servido en esta máquina, o el enlace de revisión de la unidad en creator, sin iniciar sesión. Mira [`coursekit capture`](03-commands.md#coursekit-capture).
- **Datos personales en una grabación**: antes de usar una grabación o una captura que aportó una persona, `coursekit capture redact` saca el original del proyecto y tapa sus datos personales (correos, teléfonos, cuentas, documentos de identidad, nombres, caras, los términos del proyecto); una persona revisa el resultado y lo aprueba (`coursekit capture review`, `approve`), y hasta entonces el recurso no se puede producir. Mira [`coursekit capture`](03-commands.md#coursekit-capture).
- **Capturas que hace el propio coursekit** (aplicaciones web): una persona prepara el perfil de la aplicación y da un permiso que caduca (`coursekit capture login` y `allow`); después `/produce-media` puede manejar la aplicación en el navegador y guardar la captura, con los datos personales sustituidos en pantalla antes de que el agente los vea; el vídeo se graba repitiendo sus pasos al ritmo de una persona (`coursekit capture replay`), y una persona aprueba el resultado. La ventana de un programa de escritorio funciona igual, tapada sobre los píxeles, en macOS, Windows y Linux con X11 (Windows y Linux aún no se han probado en máquinas reales).
- Un recurso que espera una grabación no detiene el handoff: el curso se monta con el marcador a la vista, y el mensaje final del handoff lista cada recurso que espera a una persona, con la ruta de su guion, y cada captura con los datos personales tapados que espera revisión y aprobación (o que se rechazó); `coursekit media plan` también lo dice, con el comando que hay que ejecutar. Cuando la grabación está en `media/recordings/`, `/produce-media` compone el recurso.

### Estados

| Estado | Significado |
|---|---|
| `pending` | Solo existe el recurso reservado en el contenido |
| `scripted` | El guion está escrito (`media/scripts/<id>.md`); los vídeos, el audio, los GIF y las demos se guionizan antes de producirlos |
| `produced` | El fichero existe (`media/files/<id>.<ext>`), con su texto alternativo o sus subtítulos. Con el backend html es el estado definitivo ([Multimedia para el backend html](#multimedia-para-el-backend-html)) |
| `uploaded` | Subido a la plataforma; `asset_path` guarda su ruta |

`orphaned` lo pone `extract`, nunca `media set`, que solo acepta los cuatro anteriores. Los recursos no se aprueban uno a uno: se validan en el curso montado (la vista previa). Con el backend creator, solo los recursos `uploaded` sustituyen a su recurso reservado cuando se monta la unidad; hasta entonces se muestra como una nota ([08-assembly-and-delivery.md](08-assembly-and-delivery.md)). Con el backend html, los recursos `produced` con su fichero lo sustituyen también.

### Cómo se eligen las opciones

Por cada recurso, `media plan` toma las opciones de su tipo de `src/coursekit/defaults/media.yaml` y conserva las que cumplen sus `needs:` en este equipo:

| `needs:` | Se cumple cuando |
|---|---|
| `env: VAR` | La variable está definida (en `.env` o en el shell) |
| `bin: CMD` | El comando está instalado |
| `media: X` | `X` está instalado como comando (`coursekit setup --media` instala `piper` y `stable-ts`) |
| `path: P` | La ruta existe dentro del proyecto (por ejemplo `tools/remotion/node_modules`) |
| `mcp: TOOL` | Solo el agente puede saber si tiene esa herramienta MCP; se muestra como `si el agente tiene la herramienta MCP` |
| `none` | Siempre |

Una opción con varios `needs:` debe cumplirlos todos. `only:` limita una opción a algunos recursos, y lo decide el agente a partir de la descripción del recurso: `only: terminal`, a los que muestran un terminal; `only: decorative`, a las imágenes decorativas, las que ambientan y no explican nada (una cabecera, gente trabajando, un lugar, un objeto genérico). Por eso una imagen sale primero del catálogo con licencia de creator cuando es decorativa, y se genera cuando muestra algo concreto del contenido (una situación que describe el texto, una escena de la historia, un personaje); una decorativa sin nada en el catálogo que encaje con el estilo del curso también se genera. Un id puede aparecer dos veces en una lista, una limitado y más arriba, otra sin límite y más abajo. Si no hay nada disponible, `media plan` imprime `ninguna opción disponible: instala una herramienta o define una clave (coursekit config media)`.

```text
U1-S1-M1 [image] Nota adhesiva en un monitor
  - creator-stock (si el agente tiene la herramienta MCP, solo para contenido decorativo): Licensed stock from creator (Pexels, Pixabay, Unsplash, Freepik) + import_stock_image; nothing that fits the style of the course: go on with the next option
  - magnific-mcp (si el agente tiene la herramienta MCP): Claude's Magnific connector
  - agent-svg (sí): Illustration drawn by the agent as SVG with the theme colours and exported to PNG (creator does not take SVG as an image); portraits of characters as flat busts
  - creator-stock (si el agente tiene la herramienta MCP): Licensed stock from creator (Pexels, Pixabay, Unsplash, Freepik) + import_stock_image
U1-S2-M1 [video] Construir una frase de paso
  - vhs (sí, solo para contenido de terminal): Terminal video
    voz: elevenlabs-mcp
    subtítulos: stable-ts
```

Para `video` y `audio`, `plan` imprime además las opciones de voz y de subtítulos disponibles. Para los tipos que usan los tokens del tema avisa también cuando los tokens faltan o no están derivados del tema de la plataforma ([Tokens del tema](#tokens-del-tema)). Un proyecto puede cambiar las opciones en `config/media.yaml` (consulta [04-configuration.md](04-configuration.md)).

## Multimedia para el backend html

Con el backend html no hay plataforma a la que subir: el paquete de una unidad lleva sus recursos. Por eso un recurso `produced` es definitivo, y el estado `uploaded` y `--asset-path` no se usan. El flujo es el mismo hasta producir el fichero:

```bash
coursekit media set PWD U1-S2-M2 --status produced --recipe agent-svg \
  --file media/files/U1-S2-M2.svg --alt "Esquema de longitud, variedad y unicidad"
coursekit assemble build PWD --unit 1
```

`coursekit assemble build` copia en `media/` del paquete todos los recursos `produced` (o `uploaded`) cuyo `--file` existe y sustituye el recurso reservado por ellos. Qué hace con cada clase de recurso:

| Recurso | Qué recibe el paquete |
|---|---|
| Imagen, infografía, esquema, GIF animado, audio, vídeo | El fichero al que apunta `--file`, copiado como `media/<id>.<ext>` (el fichero se busca respecto a la carpeta del curso y a su carpeta `media/`). Las imágenes usan `--alt`; el audio y el vídeo usan `--transcript`. |
| Simulación y demo de terminal | Una carpeta: `--file` puede ser la carpeta del paquete (por ejemplo `media/src/U1-S3-M1`) o su `index.html`. La carpeta se copia en `media/<id>/` y se incrusta en la página. |
| Subtítulos | `--subtitles-path` puede ser un fichero `.vtt` local (por ejemplo `media/files/U1-S2-M1.vtt`): se copia como `media/<id>.vtt` y se asocia al vídeo. Un valor que sea una ruta en una plataforma se ignora. |
| Descargas | Los ficheros registrados con `--download FILE` se copian en `media/files/` y se muestran como adjuntos descargables después del recurso. No hace falta `--download-asset-path`. |

Un recurso `produced` cuyo fichero no existe es un aviso en la salida de `build` (`el recurso U1-S2-M2 está producido pero su fichero no existe (coursekit media set … --file): se deja el marcador`), y el recurso reservado se queda en la página como una nota visible con su descripción, igual que un recurso que aún no está producido. Los recursos que usan el tema (infografías, esquemas, simulaciones, vídeos) usan los mismos tokens que el paquete: [Tokens del tema](#tokens-del-tema).

## Medios más ligeros

Las imágenes y los vídeos pesados ralentizan el curso en el LMS, así que coursekit los aligera en local, sin gastar créditos. Los límites están en `media.yaml › optimize` (un proyecto los cambia en `config/media.yaml`, un curso en `course.yaml › media › optimize`):

| Clave | Por defecto | Significado |
|---|---|---|
| `image.max_width` | `1920` | Las imágenes más anchas se reducen conservando la proporción (`0` no reduce nunca). |
| `image.quality` | `82` | Calidad de JPEG y WebP. |
| `image.webp_from_kb` | `200` | Backend html: un PNG o JPEG que pese más va al paquete como WebP. |
| `video.max_height` | `1080` | Los vídeos más altos se reducen (`0` no reduce nunca). |
| `video.crf` | `26` | Calidad H.264: menor es más nítido y más pesado. |
| `video.preset` | `medium` | Velocidad de ffmpeg: más lento pesa menos con la misma calidad. |
| `video.audio_kbps` | `128` | Tasa de audio AAC. |
| `video.from_mb` | `8` | Backend html: un MP4 que pese más se recodifica para el paquete (necesita `ffmpeg`; sin él se copia tal cual). |

- **Backend creator:** ejecuta `coursekit media optimize CODE [ID…]` antes de subir. Actúa en su sitio sobre el fichero de cada recurso `produced` y conserva el resultado solo si pesa menos. Creator no optimiza lo que recibe.
- **Backend html:** `coursekit assemble build` optimiza la copia que pone en el paquete y no toca el fichero original; no hay nada que ejecutar.
- Los SVG, GIF, audios y paquetes no se tocan nunca. Solo se recodifican los vídeos `.mp4` (lo que escriben Remotion y VHS), así el nombre del manifiesto sigue siendo válido.

## Montaje de vídeo

Un vídeo puede ser datos en lugar de código: un montaje de escenas, `media/scripts/<id>.video.yaml`, que [`coursekit video`](03-commands.md#coursekit-video) locuta, comprueba y renderiza con una biblioteca de escenas en el tema del curso (receta `montage`, la primera opción para un vídeo). Cada escena dura lo que dura su locución, así que cambiar un texto cambia los tiempos, no el código. Un vídeo hecho a mano como composición de Remotion (receta `remotion`) sigue siendo válido.

```yaml
version: 1
format: {width: 1920, height: 1080, fps: 30}
scenes:
  - id: opening
    type: title
    props: {kicker: "Unidad 1", title: "Contraseñas largas", stress: "largas"}
    says: "Hoy vemos por qué las contraseñas largas protegen más."
  - id: length
    type: split
    props:
      title: "La longitud manda"
      points: [{text: "Doce caracteres o más", say: "doce caracteres"}]
      media: files/u1-candado.png
    says: "La longitud manda: doce caracteres o más."
  - id: close
    type: outro
    props: {title: "Larga y única"}
    duration: 3
    shows: "El cierre, sobre el color de acento: «Larga y única»"
```

Una escena tiene un `id`, un `type`, sus `props`, lo que `says` (o una `duration` cuando no dice nada) y, si hace falta, `shows` (lo que se ve, cuando la locución no lo dice) y `layers`: cada una con un `type`, sus `props`, `at` (las palabras de la locución con las que entra) y `until` (las palabras con las que sale) o `hold` (segundos, por defecto 3), por ejemplo `{type: callout, props: {text: "Doce o más"}, at: "doce", until: "más"}`. Una capa cuyas palabras no se dicen se deja fuera, y `coursekit video check` lo avisa (`ANCHOR_NOT_SAID`). Tras el render, la voz se lleva a la sonoridad de `media › checks`.

**Las piezas.** Todo se construye por niveles, cada uno solo con el de abajo:

| Nivel | Qué | En la biblioteca |
|---|---|---|
| Tokens | el tema del curso (el suyo, o si no el del proyecto) y los tokens de movimiento | colores, tipografías, radio; cuánto tardan las cosas en entrar |
| Átomos | las piezas mínimas, movidas por el fotograma | `Heading`, `Text`, `Enter`, `Stagger`, `Underline`, `Counter`, `MediaSlot`, `Ring`, `Background`, `Card`, `Badge`, `Arrow`, `ScreenRecording`; `useAt("palabra")` y `useSayTimes([...])`: cuándo la dice la locución |
| Moléculas | combinaciones pequeñas | `TitleBlock`, `BulletList`, `StatBlock`, `CompareColumn`, `StepNode` |
| Escenas | composiciones completas | `title` (la portada: lisa, de superficie, de acento o con una foto al lado del texto, bajo un panel o bajo el texto, colocada en horizontal y en vertical), `statement` (una frase que retener, con una palabra que se subraya cuando se dice), `split`, `stat`, `compare`, `list`, `quote`, `diagram` (un proceso que se construye), `outro`, `screencast` |
| Capas | sobre una escena, desde una palabra de su locución | `lower-third` (un nombre y un cargo), `callout` (una nota corta en una esquina), `highlight` (un anillo sobre un punto) |

Los tokens llegan al vídeo como datos, así que un curso con otro tema da otro vídeo sin cambiar nada. El acento es un relleno (el cierre, el círculo de un número); lo que se dibuja fino sobre el fondo con él (un subrayado, una flecha, la marca de una lista, una palabra) toma `accent-ink`, el acento que se lee sobre el fondo: el mismo color cuando el acento ya se lee, uno más oscuro, o el que fija el proyecto, cuando el acento solo es un relleno. Una marca con reglas propias (esquinas rectas, sin sombras, dos pesos, sus ficheros de fuente) las fija en `config/video.yaml` (`shapes`, `weights`, `fonts`; ver [Configuración](04-configuration.md#video-el-estilo-de-los-vídeos-hechos-como-montaje)), y todas las piezas de la biblioteca las siguen. Una escena es una carpeta con `index.tsx` (su componente) y `scene.yaml` (una capa, `layer.yaml`) (qué es, de qué está hecha y sus props: tipo, obligatoria, máximo de caracteres, en pantalla, etiqueta; su nombre para mostrar (`label`), su `description` y el `help` de cada prop pueden ser un texto o uno por idioma, `en:` y `es:`, y se muestran en el idioma de la persona, igual que el `label` de cada una de sus `variants:`; el id de la pieza, lo que escribe el guion, no cambia); `coursekit video catalog` las lista todas, para que se vean las piezas y cómo se arman. `coursekit video gallery` las pinta: cada pieza con las props de su `example:` (en su `scene.yaml` o `layer.yaml`, un bloque por idioma de los cursos, `en:` y `es:`), en el tema y el estilo del curso, renderizadas, en `.cache/media/<CODE>/gallery/`: un clip de cada pieza y de cada variante, en la misma interfaz que la galería en vivo (se abre desde el disco). Sin código, `coursekit video gallery` pinta la del proyecto (su theme, su `config/video.yaml`, sus escenas y las de la biblioteca), en `.cache/media/project/gallery/`: la que hay que mirar antes de firmar la guía de estilo del proyecto. Una escena del proyecto o de un curso también se pinta si trae su `example:`, y `variants:` (cada una con un `name` y las `props` que cambia sobre el ejemplo) la vuelve a pintar de otras maneras. La portada va primero, y cada pieza muestra sus props en una tabla: nombre, tipo, los valores que admite, si es obligatoria y para qué sirve; una prop que solo cuenta con otro valor lo dice (`when:` en sus metadatos, p. ej. `when: {background: photo}`). `coursekit video gallery --serve` abre esas mismas piezas en vivo en el navegador, como una biblioteca de componentes (la página es de coursekit y lleva el sistema de diseño de Studio LXD; cada pieza se pinta aparte, en un marco que solo tiene el theme y el estilo del proyecto): un control por prop, sus variantes en un desplegable y las props para copiarlas en el guion; una prop con `when:` se oculta mientras no se elige ese valor. Un cambio del proyecto (su `config/video.yaml`, el theme, una escena) se ve solo mientras está abierta. Lo que reproduce el navegador es muy fiel al render, pero la prueba es la galería renderizada. Las piezas que llevan foto se pintan con una foto de dominio público que trae coursekit (CC0); la galería en vivo de un curso ofrece también las imágenes de su `media/files/`.

**La tipografía de los vídeos.** Cada texto de una pieza tiene un papel (`display`, `heading`, `kicker`, `body`, `quote`, `statement`, `stat`, `step`…), y `config/video.yaml › text` da a cada papel su familia (una de las fuentes de la marca), tamaño, peso, estilo, mayúsculas, tracking, interlineado y color (un rol del theme). Las piezas de la biblioteca, del proyecto y de un curso lo siguen sin tocarlas; la página de Tipografía de la galería en vivo muestra la escala de un vistazo. Ver [`video`](04-configuration.md#video-el-estilo-de-los-vídeos-hechos-como-montaje).

**Lo que permite la marca.** La biblioteca ofrece todas las posibilidades; el proyecto las acota en `config/video.yaml › scenes` (y un curso en `course.yaml › video › scenes`): los valores que puede tomar cada prop (`allow`), el que toma cuando el guion no dice nada (`defaults`) y las piezas que quedan fuera (`<nombre>: false`); `"*"` vale para toda pieza con esa prop. Una marca sin textos centrados, por ejemplo, escribe `scenes: {"*": {allow: {align: [left]}}}`. El catálogo y las galerías muestran solo eso, y `coursekit video check` rechaza el resto (un aviso en el handoff, que su registro enumera). `/define-theme` propone estas reglas a partir de la marca. Ver [`video`](04-configuration.md#video-el-estilo-de-los-vídeos-hechos-como-montaje).

**Dónde están las escenas y cuál gana.** Una escena del curso tapa a la del proyecto con el mismo nombre, y una del proyecto a la de la biblioteca:

| Dónde | Qué |
|---|---|
| `courses/<CODE>/video/scenes/<nombre>/`, `video/layers/<nombre>/` | escenas y capas de un curso |
| `tools/remotion/src/scenes/<nombre>/`, `src/layers/<nombre>/` | escenas y capas del proyecto, para todos sus cursos |
| `tools/remotion/kit/` | la biblioteca de coursekit: la escribe cada comando `coursekit video` desde el paquete; git la ignora y nunca se edita |

**Piezas del proyecto en lugar de las de la biblioteca.** Un átomo o una molécula del proyecto (`tools/remotion/src/atoms/<Nombre>.tsx` o `src/molecules/<Nombre>.tsx`), o de un curso (`video/atoms/<Nombre>.tsx`, `video/molecules/<Nombre>.tsx`), sustituye en todas las escenas a la de la biblioteca con ese nombre: un proyecto con una marca fuerte rehace su `Heading` o su `Card` y todas las escenas lo muestran, sin tocar las escenas. Exporta el mismo nombre con las mismas props (`coursekit video` rechaza otro nombre, o uno que la biblioteca no tiene); parte del fichero de la biblioteca en `tools/remotion/kit/`. `coursekit video catalog` marca las piezas sustituidas. El estilo de los vídeos (movimiento, fondo, logo) se fija en [`video`](04-configuration.md#video-el-estilo-de-los-vídeos-hechos-como-montaje).

**Para retocarlo a mano.** `coursekit video export CODE ID` deja las piezas del vídeo por separado (cada escena limpia, cada capa con transparencia, cada voz, los subtítulos) y su línea de tiempo en FCPXML 1.10 y OpenTimelineIO, que DaVinci Resolve, Final Cut y Premiere abren con cada pieza en su sitio.

Cuando ninguna escena cuenta una idea, el agente de multimedia crea una, compuesta con los átomos y las moléculas (importándolos de `"../../../kit"`, igual en una escena del proyecto que en una del curso), así que la biblioteca del proyecto crece con el uso. Las reglas de una escena: todo se mueve con el fotograma; colores y tipografías solo del tema; lo que entra con una palabra entra cuando la locución la dice; medios por su ruta dentro de la carpeta de medios del curso; nada de la red.

## Accesibilidad de los vídeos

Lo que muestra un vídeo existe también como texto, para que lo tenga quien no puede verlo (WCAG 1.2.3, 1.2.5 y 1.2.8). Las escenas de un vídeo se describen junto a su guion, en `media/scripts/<id>.scenes.yaml`:

```yaml
words: media/files/u1-s2-m1.words.json      # los tiempos de la locución (por defecto: <fichero del vídeo>.words.json)
scenes:
  - text: "Longitud mínima: 12"             # el texto en pantalla (uno o una lista)
    says: "Abre los ajustes de seguridad y pon la longitud mínima en doce."
  - text: "Historial"
    shows: "La lista de cambios guardados, con la fecha de cada uno"   # lo que se ve, en una frase
    says: "Y ya está."
```

- **Audiodescripción integrada.** Lo importante de la pantalla también se dice: `coursekit media check` avisa (`NOT_SAID`) del texto en pantalla cuya locución no dice la mayor parte de sus palabras con significado (de cuatro letras o más, y los números, también cuando se dicen con letras), salvo que la escena describa lo que se ve en `shows`. Arréglalo en la locución o con `shows`.
- **Transcripción accesible y descripciones.** `coursekit media transcript CODE ID` escribe, escena a escena, el minuto (a partir de las palabras de la locución), lo que se ve (`shows`, o si no el texto en pantalla, tras `En pantalla:` en el idioma del curso) y lo que se dice, en `<fichero>.transcript.txt`, y lo mismo como pista WebVTT de descripciones (`kind="descriptions"`) en `<fichero>.descriptions.vtt`. La transcripción pasa a ser la del recurso, así que el montaje la pone en el curso bajo el vídeo.

## Revisar audios y vídeos

Antes de que un audio o un vídeo vaya al curso, `coursekit media check CODE` revisa su sonoridad (EBU R128 para la web: -16 LUFS, pico -1 dBTP; `--fix` la corrige), sus subtítulos (ninguno más rápido de 17 caracteres por segundo) y lo que muestra y no dice; `coursekit media sheet CODE ID` pone fotogramas de un vídeo en una sola imagen, para mirarlo sin reproducirlo. Los límites están en `media.yaml › checks`. Mira [`coursekit media`](03-commands.md#coursekit-media).

## Subida a creator

Con el backend creator los recursos se suben al contenido de su unidad, que crea el montaje, y el curso se monta otra vez para que sustituyan a sus recuadros (el handoff lo hace solo: [Modo handoff](02-workflow.md#modo-handoff)). El agente pide a creator una dirección de subida (`request_asset_upload`, o `request_embed_upload` para los paquetes) y envía el fichero con `coursekit media upload CODE --file F --url "<uploadUrl>" --content-type MIME`; después registra la ruta con `coursekit media set CODE ID --status uploaded --asset-path <ruta>`.

Creator solo admite PNG, JPEG, WebP y GIF como imagen, así que un SVG no puede ser un bloque de imagen:

- Una infografía o un diagrama estático: el agente conserva el SVG como fuente y sube un PNG exportado de él.
- Un SVG animado (`agent-svg-animated`): `coursekit media embed CODE ID` envuelve el SVG en `media/src/<id>/index.html`, con el manifiesto de creator `slxd-embed.json` (toma el alto del dibujo), el agente sube los dos ficheros como paquete EMBED, y el montaje pone un bloque EMBED donde el fichero del recurso es un `.svg`. La animación se conserva.

## Proveedores de voz

Un curso usa **una** voz para toda su locución, así que un curso nunca mezcla voces. La elección se guarda en `course.yaml › media.voice`.

| Proveedor | Necesita (en `.env`) | Voz por defecto | Notas |
|---|---|---|---|
| `elevenlabs` | `ELEVENLABS_API_KEY`; una voz en `ELEVENLABS_VOICE_ID` o `--voice` | ninguna | Mejor calidad; escribe subtítulos exactos a partir de sus marcas de tiempo |
| `azure` | `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION` | `es-ES-ElviraNeural` / `en-GB-SoniaNeural`; `AZURE_SPEECH_VOICE` la sustituye | Voces neuronales |
| `google` | `GOOGLE_TTS_API_KEY` | `es-ES-Chirp3-HD-Aoede` / `en-GB-Chirp3-HD-Aoede`; `GOOGLE_TTS_VOICE` la sustituye | Voces Chirp 3 HD |
| `gemini` | `GEMINI_API_KEY` (Gemini API, de Google AI Studio) | `Aoede` en los dos idiomas; `GEMINI_TTS_VOICE` la sustituye | Voces de Gemini TTS, con indicación de estilo ([La voz de Gemini](#la-voz-de-gemini)) |
| `piper` | `PIPER_VOICE` (ruta a una voz `.onnx`) y el comando `piper`; `PIPER_SPEAKER` para voces con varios locutores | el fichero de `PIPER_VOICE` | Voz local de borrador |

La voz por defecto depende del idioma del curso (`es` o `en`). En `media plan` y `media providers` las opciones de voz se llaman `elevenlabs-api`, `azure-api`, `google-api`, `gemini-api` y `piper` (los proveedores de arriba), además de `elevenlabs-mcp`, el agente usando directamente el conector de ElevenLabs (sin `coursekit tts`); esta siempre aparece, porque solo el agente puede saber si tiene el conector. Las opciones de subtítulos son `elevenlabs-timestamps` y `stable-ts`.

```bash
coursekit voice set gemini                 # la voz del proyecto: la heredan los cursos que no tienen la suya
coursekit voice list PWD                   # proveedores, disponibilidad y la voz del curso
coursekit voice set PWD azure              # fija el proveedor (y su voz por defecto)
coursekit voice set PWD piper --speaker 1  # un locutor de una voz de Piper con varios locutores
coursekit voice set PWD elevenlabs --voice <id-de-voz>
```

**Voces de los personajes.** Los personajes de los diálogos y de las simulaciones pueden tener voz propia, del mismo proveedor: `coursekit voice set PWD azure --voice es-ES-AlvaroNeural --character Daniel` la guarda en `course.yaml › media.voices`, y `coursekit tts --course PWD --character Daniel …` la usa. Con Piper, un personaje sin voz propia toma por turnos un locutor de la voz, en el orden del reparto de la biblia narrativa: suficiente para borradores.

`voice set <provider>`, sin curso, fija la voz del proyecto (`project.yaml › media.voice`), y la usan todos los cursos sin voz propia; `voice set <CODE> <provider>` da a un curso la suya, y `voice unset <CODE>` se la quita para que vuelva a heredar la del proyecto. Un cambio de la voz del proyecto llega a todos los cursos que la heredan, también a la locución pendiente de un curso a medias. Si el proveedor no está configurado en este equipo, avisa (puede que otras personas del equipo lo tengan) pero lo guarda igualmente. Con varios proveedores disponibles y ninguno elegido, `tts` se detiene y te pide ejecutar `voice set`; sin ninguno disponible, indica qué claves definir.

### La voz de Gemini

El proveedor `gemini` usa los modelos de síntesis de voz de la Gemini API. Además del texto aceptan una **indicación de estilo**: cómo decirlo (emociones, entonación, ritmo, volumen), que se envía con cada fragmento del guion para que el tono no cambie entre ellos. Sus ajustes están en `media.yaml › gemini` ([Configuración](04-configuration.md#media-opciones-de-producción)), y un curso los cambia en `course.yaml › media › gemini`:

```yaml
# course.yaml
media:
  gemini:
    style: "tranquila, cálida y clara, como una profesora que explica"
```

| Clave | Por defecto | Significado |
|---|---|---|
| `model` | `gemini-3.8-flash-tts` | Modelo de la Gemini API. `gemini-3.8-flash-lite-tts` cuesta menos; `gemini-3.1-flash-tts-preview` es el modelo preview anterior |
| `style` | vacío | Cómo decirlo. Vacío: la voz tal cual |
| `chunk_bytes` | `4500` | Fragmento más largo de un guion por petición, en bytes UTF-8. El modelo devuelve como mucho unos diez minutos de audio por petición |
| `tier` | `flex` | `flex`: la mitad del precio, la misma petición, y la respuesta en minutos en lugar de segundos (hasta 15); cuando Google no tiene capacidad responde 429 o 503 y coursekit lo vuelve a intentar unas cuantas veces. `standard`: el precio completo y la respuesta más rápida |
| `flex_fallback` | `true` | Cuando `flex` sigue sin capacidad tras los intentos, la petición va por el nivel estándar. `false`: falla en su lugar (código de salida 1), y no se paga nada a precio completo |

`coursekit voice set PWD gemini` escribe en el curso el modelo vigente (`course.yaml › media.voice.model`; `voice set gemini`, en la voz del proyecto): el curso conserva el modelo con el que empezó aunque cambie el valor por defecto, así que su locución nunca cambia de voz a mitad. Para pasar un curso a otro modelo, cambia esa clave y vuelve a producir su locución. Las voces son las de Gemini (`Aoede`, `Kore`, `Charon`, `Puck`…), sin idioma: el idioma es el del curso. La Gemini API marca todo el audio que genera con una marca de agua SynthID inaudible. En su nivel gratuito, Google puede usar lo que se envía para mejorar sus productos: para el contenido de un cliente, usa una clave con facturación.

### El batch de la voz de Gemini

Además de `flex`, la Gemini API tiene un **batch**: las peticiones de todo un curso se envían juntas en un trabajo y Google las responde en 24 horas como mucho (a menudo en minutos), a la misma mitad de precio. Nada espera la respuesta: las locuciones se ponen en cola, se envía el trabajo y se recogen después. Un curso guarda su cola en `media/tts-batch.yaml` (versionada: qué se envió, con qué modelo, voz y estilo, y cómo fue). Solo existe con la voz de Gemini.

Tres comandos añaden locuciones a la cola con `--batch`, en lugar de locutarlas:

| Comando | Qué va a la cola | Qué hace `collect` con ello |
|---|---|---|
| `coursekit video voice CODE ID --batch` | Las escenas de un montaje cuyo texto o voz cambió | Escribe su audio, alinea sus palabras (`stable-ts`) y anota su duración: `coursekit video render` sigue |
| `coursekit media narrate CODE --batch` | Las escenas de las simulaciones por narrar | Escribe `media/files/<id>.mp3` y marca el recurso `produced` |
| `coursekit tts --course CODE --in … --out … --batch` | Un guion | Escribe el fichero de `--out` |

Después [`coursekit tts-batch`](03-commands.md#coursekit-tts-batch) `send CODE` sube la cola (un guion largo son varias peticiones, que se vuelven a unir al recogerlas) y crea el trabajo; `status CODE` dice cómo va; `collect CODE` escribe lo que llegó y deja en la cola lo que falló, para enviarlo otra vez. Un trabajo que no termina en 48 horas caduca sin resultados y todo vuelve a la cola. Crear un trabajo no es idempotente (enviar otra vez se pagaría dos veces), así que un segundo `send` se rechaza mientras hay uno en curso. Los recursos de la cola no están pendientes para el agente multimedia ni producidos: `media plan` y el handoff los dejan estar hasta que se recogen.

En el [modo handoff](02-workflow.md#modo-handoff), cuando el agente multimedia deja locuciones en la cola, el handoff las envía y se detiene, diciendo que están en camino; `coursekit handoff CODE` más tarde las recoge (si el trabajo terminó; si no, vuelve a detenerse) y sigue con lo que dependía de ellas.

## `coursekit tts`

Lee un guion y escribe la locución:

```bash
coursekit tts --course PWD --in courses/PWD/media/scripts/U1-S2-M1.md --out courses/PWD/media/files/U1-S2-M1.mp3
```

| Opción | Significado |
|---|---|
| `--in FICHERO`, `--out FICHERO` | Guion (los espacios en blanco se colapsan) y audio de salida; ambas obligatorias |
| `--course CODE` | Usa la voz de ese curso y su idioma. Sin ella, el idioma es `es` |
| `--engine elevenlabs\|azure\|google\|gemini\|piper` | Fuerza un proveedor en lugar del del curso |
| `--voice V` | Fuerza una voz. Si no: la voz del curso (si es el mismo proveedor), después la variable de entorno del proveedor y, por último, la voz por defecto del idioma |
| `--speaker N` | Locutor de una voz de Piper con varios locutores |

El proveedor es `--engine`; si no, el `media.voice.provider` del curso; si no, el único proveedor disponible. Los guiones largos se parten al final de las frases (Azure 4.000 bytes, Google 4.500, Gemini `media.yaml › gemini.chunk_bytes`); los fragmentos se piden como audio sin comprimir, se unen uno tras otro y se codifican a MP3 una sola vez con `ffmpeg`, así que no quedan huecos entre ellos ni hay una segunda pasada de compresión; Piper también necesita `ffmpeg` para escribir MP3 (un `--out` que termina en `.wav` conserva el WAV). ElevenLabs escribe además `<out>.vtt` (mismo nombre, `.vtt`) con subtítulos a partir de sus marcas de tiempo, agrupados al final de las frases o cada unos 84 caracteres.

## `coursekit subtitles`

Alinea un guion conocido con su audio, palabra a palabra, con `stable-ts` y escribe un fichero WebVTT cuyos subtítulos terminan al final de cada frase o tras unos 84 caracteres:

```bash
coursekit subtitles --course PWD --audio courses/PWD/media/files/U1-S2-M1.mp3 \
  --text courses/PWD/media/scripts/U1-S2-M1.md --out courses/PWD/media/files/U1-S2-M1.vtt
```

`--course` toma el idioma del curso; sin él, el idioma es `--language` (por defecto `es`). `--model` es el nombre de modelo que se pasa a `stable-ts` (por defecto `base`). Úsalo con audio de Azure, Google o Piper; ElevenLabs ya escribe su propio `.vtt`. Los subtítulos son siempre obligatorios en los vídeos.

## Voz de borrador (Piper) y stable-ts

Ambos los instala `coursekit setup --media` como herramientas `uv` independientes (Python 3.12), porque pesan mucho y solo hacen falta para la multimedia. Se instalan una vez por equipo y las usan todos los proyectos:

- **Piper** es un motor local de síntesis de voz para borradores rápidos, gratuito y sin conexión. `setup --media` descarga también una voz para el idioma de contenido del proyecto en `~/.local/share/piper` (`%LOCALAPPDATA%\piper` en Windows) y define `PIPER_VOICE` en `.env` si está vacía: `es_ES-sharvard-medium` para español (locutores 0 y 1) y `en_GB-alba-medium` para inglés.
- **stable-ts** alinea los guiones con el audio para producir subtítulos (`coursekit subtitles`).

Ambos cuentan como instalados cuando su comando (`piper`, `stable-ts`) está en tu `PATH`.

## `coursekit setup --media`

Lo ejecuta una persona, nunca un agente (a los agentes se les indica que te pidan ejecutarlo). Un `coursekit setup` interactivo también te lo ofrece.

| Paso | macOS | Windows | Linux |
|---|---|---|---|
| Herramientas del sistema | `brew install` de las que falten entre `ffmpeg`, `node`, `vhs`, `asciinema` (necesita Homebrew) | `winget install` de `ffmpeg` (`Gyan.FFmpeg`), `node` (`OpenJS.NodeJS.LTS`), `vhs` (`charmbracelet.vhs`); `asciinema` no tiene versión para Windows, las demos de terminal usan VHS | No instala nada: imprime `sudo apt install …` con las que falten entre `ffmpeg nodejs npm asciinema`, y la dirección de `vhs` |
| `piper`, `stable-ts` | `uv tool install --python 3.12 piper-tts` y `stable-ts` (necesita `uv`) | igual | igual |
| Voz de borrador | Se descarga y se define `PIPER_VOICE` | igual | igual |
| Remotion | Copia la plantilla a `tools/remotion` (si falta), instala sus dependencias una sola vez en el almacén de coursekit y enlaza `tools/remotion/node_modules` a ellas ([Dónde están las herramientas](#dónde-están-las-herramientas)) | igual | igual |
| Claves de API | Solo se piden en un terminal interactivo | igual | igual |

Las claves se piden una a una con entrada oculta (pulsa Intro para omitir). Las que ya están definidas no se vuelven a pedir. Cuando se guarda una, se piden también sus valores asociados:

| Servicio | Clave | También se pide |
|---|---|---|
| ElevenLabs | `ELEVENLABS_API_KEY` | `ELEVENLABS_VOICE_ID` |
| Azure Speech | `AZURE_SPEECH_KEY` | `AZURE_SPEECH_REGION` (obligatoria, `doctor` avisa si falta), `AZURE_SPEECH_VOICE` |
| Google TTS | `GOOGLE_TTS_API_KEY` | `GOOGLE_TTS_VOICE` |
| Gemini TTS | `GEMINI_API_KEY` | `GEMINI_TTS_VOICE` |
| Magnific | `MAGNIFIC_API_KEY` | — |

Todas van a `.env`, que nunca se sube al repositorio. `coursekit doctor` muestra la sección Multimedia: `ffmpeg`, `vhs`, `asciinema`, `piper`, `stable-ts`, el almacén de coursekit (ruta y tamaño), las dependencias de Remotion (`tools/remotion/node_modules`) si el proyecto tiene un espacio de Remotion, `PIPER_VOICE` y qué claves están definidas.

## Dónde están las herramientas

Dentro de un proyecto no se instala nada pesado. Las herramientas se instalan una vez por equipo y todos los proyectos usan la misma copia:

| Herramienta | Dónde | La comparten los proyectos |
|---|---|---|
| `ffmpeg`, `node` (con `npm`), `vhs`, `asciinema` | Paquetes del sistema (Homebrew, winget o tu gestor de paquetes) | Sí |
| `piper`, `stable-ts` | Herramientas de `uv`, en la carpeta de herramientas de `uv` | Sí |
| Voz de borrador de Piper | `~/.local/share/piper`, o `%LOCALAPPDATA%\piper` en Windows | Sí |
| Dependencias de Remotion (`node_modules`) | El almacén de coursekit, en `workspaces/remotion-<hash>/`; cada proyecto se enlaza a ellas | Sí |
| Constructor del backend html (`@studiolxd/scorm`, `esbuild`) | El almacén de coursekit, en `workspaces/html-builder-<hash>/` (lo instala `coursekit setup` o la primera `coursekit assemble build`) | Sí |
| Fuentes de Remotion (`src/`, `package.json`, `tsconfig.json`) | `tools/remotion/` en el proyecto | No: son del proyecto y se versionan con él |
| Claves de API y `PIPER_VOICE` | `.env` del proyecto | No: son personales y nunca se suben al repositorio |
| El registro de lo que instaló `setup` | `installed.json` en el almacén de coursekit | Sí, uno por equipo |

### El almacén de coursekit

El almacén es `COURSEKIT_HOME` si la defines; si no, la carpeta de datos de tu usuario:

| Sistema | Almacén |
|---|---|
| macOS | `~/Library/Application Support/coursekit` |
| Linux | `~/.local/share/coursekit` (`$XDG_DATA_HOME/coursekit` si esa variable está definida) |
| Windows | `%LOCALAPPDATA%\coursekit` |

`coursekit doctor` muestra su ruta y su tamaño en la sección Multimedia. Para moverlo, mira [Solución de problemas](09-troubleshooting.md#el-almacén-de-coursekit-ocupa-mucho-espacio).

### Remotion se instala una sola vez

Remotion con sus dependencias ocupa unos 230 MB, y el navegador que descarga la primera vez que renderiza, unos 600 MB más, que se guardan dentro del mismo `node_modules`. Instalar eso en cada proyecto gastaría mucho disco y mucho tiempo, así que `coursekit setup --media`:

1. Copia la plantilla a `tools/remotion/` (solo `src/`, `package.json` y `tsconfig.json`) si el proyecto no la tiene.
2. Ejecuta `npm install` en el almacén, en `workspaces/remotion-<hash>/`, solo si esa carpeta aún no existe.
3. Hace que `tools/remotion/node_modules` sea un enlace al `node_modules` de esa carpeta: un enlace simbólico o, en Windows, una unión (junction).

El segundo proyecto que ejecuta `coursekit setup --media` no descarga nada: solo crea el enlace. El `.gitignore` del proyecto ignora `node_modules/`, así que el enlace nunca se sube al repositorio.

El `<hash>` es el del `package.json` del proyecto (y el de su `package-lock.json`, si lo hay). Los proyectos con las mismas dependencias comparten la instalación; un proyecto que cambia sus dependencias obtiene su propia instalación en el almacén, junto a la otra. Si no se puede crear el enlace, el proyecto instala su propio `node_modules` en `tools/remotion/`, como cualquier proyecto de Node; y un proyecto que ya tiene allí una carpeta `node_modules` real la conserva. Mira [Solución de problemas](09-troubleshooting.md#no-se-puede-crear-el-enlace-de-remotion).

Para quitar todo lo que `setup` instaló fuera de los proyectos, ejecuta `coursekit uninstall` (mira [Comandos](03-commands.md#coursekit-uninstall) y [Primeros pasos](01-getting-started.md#desinstalar)).

## Tokens del tema

Las infografías, los esquemas, los GIF, las simulaciones y los vídeos usan los colores y las tipografías del tema del curso para que parezcan parte del curso. Esos valores son los tokens de diseño: `tokens.json` (los valores) y `tokens.css` (los mismos valores como propiedades personalizadas de CSS, más clases base para simulaciones). Nadie los escribe a mano: coursekit los deriva del tema de la plataforma de montaje (backend creator de slxd) o de la hoja de estilos del proyecto (backend html) y anota de dónde salen, de modo que los recursos multimedia y el curso montado comparten los mismos colores y tipografías.

### Definir el tema

El comando `/define-theme [CODE]` (agente de diseño; `coursekit run define-theme [CODE]` desde una terminal) hace todo el flujo, y `/new-course` recuerda a la persona que lo ejecute cuando el proyecto aún no tiene tokens:

1. `coursekit theme show` indica si ya hay tokens y de dónde salen.
2. El agente lista los temas de la plataforma (`list_themes`) y, con la persona, elige uno, crea uno (desde cero, desde un preajuste o como copia de otro) o adapta uno con `update_theme` usando los colores y las tipografías de la marca del cliente. Un cambio de tema en la plataforma cambia todos los contenidos que lo usan, así que un curso que necesita un aspecto propio recibe una copia del tema.
3. El agente guarda el resultado completo de `get_theme` en `.cache/theme/get_theme.json` (una carpeta de caché que no se sube al repositorio).
4. `coursekit theme import .cache/theme/get_theme.json` lo convierte en `tokens.json` y `tokens.css`, e imprime las notas y el contraste de cada par. Si un par falla, se corrige el color en la plataforma (`update_theme`), se vuelve a guardar `get_theme` y se repite la importación. Los tokens nunca se editan a mano.
5. El agente vincula el tema a los contenidos con `set_content_theme`, con el id que imprime `coursekit theme show --course <CODE>`; los contenidos que se creen más tarde lo reciben al montarse ([08-assembly-and-delivery.md](08-assembly-and-delivery.md)). La persona valida el tema igual que valida el diseño.

El tema de la plataforma se puede rehacer en cualquier momento: importar de nuevo sobrescribe los tokens, y entonces `coursekit media plan` avisa de los recursos hechos con los anteriores.

Con el backend html no hay tema de plataforma y los pasos 2, 3 y 5 no se aplican: el agente escribe o adapta `theme/maqueta.css` (o `courses/<CODE>/theme/maqueta.css` para un curso) con la marca en las variables CSS, y ejecuta `coursekit theme import theme/maqueta.css` (añade `--course CODE` para el tema propio de un curso). El paquete ya usa la hoja de estilos sin la importación; la importación es lo que da a los recursos los mismos tokens y satisface el control ([El control de los recursos](#el-control-de-los-recursos)).

### El fichero de tokens

`theme/tokens.json` de un tema llamado «ACME training» (versión 3), abreviado:

```json
{
  "origin": {"source": "creator", "theme_id": "11111111-2222-4333-8444-555555555555", "name": "ACME training",
             "version": 3, "imported_at": "2026-10-09T10:14:30+02:00",
             "derived": ["accent-ink", "border", "correct-ink", "surface", "surface-highlight", "text-muted", "wrong-ink"],
             "defaults": ["radius", "space", "shadow"], "notes": []},
  "color": {"background": "#FFFFFF", "text": "#000000", "headings": "#1B365D", "accent": "#0A58CA",
            "on-accent": "#FFFFFF", "link": "#0A58CA", "correct": "#14733A", "on-correct": "#000000",
            "wrong": "#B3261E", "on-wrong": "#000000", "text-muted": "#595959", "surface": "#F5F5F5",
            "surface-highlight": "#E2EBF9", "border": "#CCCCCC", "accent-ink": "#0A58CA", "correct-ink": "#14733A",
            "wrong-ink": "#B3261E"},
  "font": {"family": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
           "headings": "'ACME Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
           "ui": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
           "size-base": "17px", "line-height": "1.5"},
  "radius": "8px",
  "shadow": {"soft": "0 2px 8px rgba(0, 0, 0, 0.12)"},
  "space": {"xs": "4px", "sm": "8px", "md": "16px", "lg": "24px", "xl": "32px"}
}
```

`origin` dice de dónde sale el fichero: `source` (`creator`), el id, el nombre y la versión del tema de la plataforma, la fecha de la importación, los tokens derivados por coursekit porque no están en la plataforma (`derived`), los grupos que son valores por defecto del paquete (`defaults`) y las notas que imprimió la importación (`notes`). Un `tokens.json` cuyo `origin.source` no es ni `creator` ni `css` cuenta como escrito a mano.

Derivado de una hoja de estilos, el `origin` es distinto (los valores, abreviados, son los de la hoja de estilos):

```json
{
  "origin": {"source": "css", "file": "maqueta.css", "sha256": "3f9a1c07be52",
             "imported_at": "2026-10-09T10:14:30+02:00", "notes": []},
  "color": {"background": "#FFFFFF", "text": "#1A1A1A", "headings": "#1A1A1A", "accent": "#7A1FA2"},
  "font": {"family": "'ACME Sans', sans-serif", "headings": "'ACME Sans', sans-serif", "size-base": "16px", "line-height": "1.6"},
  "radius": "8px"
}
```

`file` es el nombre de la hoja de estilos y `sha256` los 12 primeros caracteres del hash de su contenido; `coursekit theme show` los imprime como `origen: variables CSS de maqueta.css (huella 3f9a1c07be52), importado el 2026-10-09`. No hay listas `derived` ni `defaults`: la maqueta base del paquete declara todos los tokens, así que la hoja de estilos solo cambia los que quiere.

`coursekit theme tokens` reescribe `tokens.css` a partir de `tokens.json`: propiedades personalizadas de `:root` (`--color-<nombre>`, `--font-family`, `--font-family-headings`, `--font-family-ui`, `--font-size-base`, `--line-height`, `--radius`, `--shadow-<nombre>`, `--space-<nombre>`; `font.google`, si existe, se convierte en un `@import`) y las clases base para simulaciones (`.btn`, `.card`, `.is-correct`, `.is-wrong`, `.note`). Tampoco edites el CSS a mano.

### Un tema por proyecto, uno por curso

Un proyecto tiene un tema, en `theme/`, que heredan todos los cursos. Un curso que necesita un aspecto propio lo define con `/define-theme <CODE>` (`coursekit theme import FILE --course CODE`), que escribe `courses/<CODE>/theme/tokens.json` y `tokens.css` y anota `slxd.theme_id` en el `course.yaml`. Desde entonces ese curso usa sus tokens propios: un curso usa los tokens de `courses/<CODE>/theme/` cuando allí existe `tokens.json`, y los del proyecto en caso contrario. `coursekit theme show CODE` indica cuáles se aplican a un curso. El acento del proyecto sigue pintando el Excel de catálogo (más abajo).

### Qué se deriva y qué viene de la plataforma

| Tokens | Origen |
|---|---|
| `background`, `text`, `headings`, `accent`, `on-accent` (el rol `accentText`), `link`, `correct`, `on-correct`, `wrong`, `on-wrong` | Los roles semánticos de color del tema de la plataforma, con las referencias a la paleta resueltas. Un rol de texto que el tema no define hereda el color del texto. |
| `text-muted`, `surface`, `surface-highlight`, `border`, `accent-ink`, `correct-ink`, `wrong-ink` | Los deriva coursekit a partir de los colores anteriores (mezclas de texto, fondo y acento); el texto secundario se mantiene al menos a 4,5:1 sobre el fondo. `accent-ink`, `correct-ink` y `wrong-ink` son el acento y los colores de estado como tinta (una línea, una marca, una palabra sobre el fondo): el propio color cuando se lee ahí, oscurecido hacia el texto hasta que se lee. Constan en `origin.derived`; un rol que fija el proyecto (`theme.roles`) toma ese color y pasa a `origin.set`. |
| `palette.<id>` | Los colores con nombre del theme de la plataforma (`emerald`, `cayenne`, `prussian`…), importados con su id, para dibujar con ellos: retratos, ilustraciones. No son roles y no cambian la huella de los tokens. En `tokens.css` son `--palette-<id>`. |
| `font.family`, `font.headings`, `font.ui` | Las asignaciones de fuentes del tema: la pila de fuentes del sistema, una fuente subida por su nombre (seguida de la pila del sistema como alternativa) o una fuente incluida en la plataforma por su id, con una nota porque el nombre puede no coincidir con su familia CSS. |
| `font.size-base`, `font.line-height` | El tamaño base de fuente y el interlineado del tema. |
| `radius`, `space`, `shadow` | Valores por defecto del paquete: la plataforma no tiene esos valores. Constan en `origin.defaults`; el proyecto puede fijar el radio y la sombra (`theme.radius`, `theme.shadow`). |

Con el backend html los tokens salen de las variables CSS de la maqueta base del paquete con la hoja de estilos encima (`coursekit theme import FICHERO.css`); una referencia `var(--x)` se resuelve, gana la última declaración de una variable, y coursekit no deriva nada:

| Variable CSS | Token |
|---|---|
| `--color-<nombre>` | `color.<nombre>`: `background`, `text`, `text-muted`, `headings`, `accent`, `accent-ink`, `on-accent`, `link`, `surface`, `surface-highlight`, `border`, `correct`, `wrong`, `correct-ink`, `wrong-ink` (la maqueta base las declara todas; añade otras si las necesitas). Un valor que no es un color simple (un degradado, `color-mix()`) se conserva tal como está escrito y queda fuera de la comprobación de contraste, con una nota. |
| `--font-family`, `--font-family-headings`, `--font-family-ui` | `font.family`, `font.headings`, `font.ui` |
| `--font-size-base`, `--line-height` | `font.size-base`, `font.line-height` |
| `--radius` | `radius` |
| `--space-<nombre>` | `space.<nombre>` (`xs`, `sm`, `md`, `lg`, `xl`) |
| `--shadow-<nombre>` | `shadow.<nombre>` (`soft`) |

### Límites

- Los tokens son los del modo claro. Cuando el tema de la plataforma tiene modo oscuro, la importación deja una nota que lo dice; los recursos multimedia se producen en modo claro.
- Un rol de color que no se puede resolver recurre a un valor por defecto y deja una nota.
- Con el backend html solo se leen las variables anteriores: el resto de `theme/maqueta.css` (selectores, reglas de maquetación) da otro aspecto al paquete pero no llega a los tokens. La lectura es textual: toda declaración `--nombre: valor` del fichero cuenta esté donde esté (también dentro de un selector que no sea `:root`) y gana la última; los bloques de at-rules (`@media`, `@supports`...) se saltan, así que las variables de un modo oscuro o de una maqueta de impresión nunca llegan a los tokens.

### El control de los recursos

Los tipos de recurso que usan los tokens figuran en `uses_theme` de la configuración multimedia (por defecto `infographic`, `diagram`, `animated_gif`, `simulation`, `video` y `terminal_demo`; consulta [04-configuration.md](04-configuration.md)). Para ellos:

- `coursekit media plan` avisa cuando el curso tiene recursos de esos tipos y sus tokens faltan o están escritos a mano (ni origen `creator` ni `css`), y por cada recurso producido o subido que se hizo con otros tokens distintos de los actuales (hay que producirlo de nuevo).
- `coursekit media set CODE ID --status produced` (o `uploaded`) se rechaza mientras los tokens no estén derivados: del tema de la plataforma (backend creator) o de la hoja de estilos del proyecto (backend html, `coursekit theme import FICHERO.css`). `--force` se salta la comprobación, para el caso poco habitual de un curso que deliberadamente no sigue el tema.
- Cuando se acepta, el recurso guarda una huella de los tokens (`theme`, en `media/manifest.yaml`). Si el tema cambia y se vuelve a importar, la huella ya no coincide y `plan` avisa. La huella abarca los colores, las tipografías, el radio, los espaciados y las sombras, no el origen ni la fecha, así que importar de nuevo el mismo tema no genera avisos.

El agente multimedia se detiene y pide a la persona que ejecute `/define-theme` cuando faltan los tokens, en lugar de inventar colores.

### El material de marca

El tema de la plataforma da los colores y las tipografías del curso; la marca dice cómo se usan. Dejas el material de marca en `theme/branding/` (o, para un curso con marca propia, en `courses/<CODE>/theme/branding/`, que gana entero a la del proyecto) como dejas el material de referencia en `brief/`, y [`coursekit brand`](03-commands.md#coursekit-brand) lo convierte para los agentes:

```
theme/branding/
  sources/      ← lo que dejas: libro de marca, ficheros de tokens, fuentes, logos, imágenes
  links.md      ← dos partes: el material de marca que se lee entero (un Storybook, una web de marca, una documentación)
                  y "# Webs de las que inferir el estilo" (la web de la empresa, observada en un navegador)
  notes.md      ← tus indicaciones («la lavanda solo como relleno», «sin logo en los vídeos»…)
  index.md      ← lo escribe coursekit brand: qué hay y dónde; los agentes lo leen primero
  text/         ← lo escribe coursekit brand: el material en Markdown, lo observado
  fonts/        ← fonts/fonts.css y los ficheros de fuente (los tuyos, o Google Fonts con licencia abierta)
  logo/, tokens/, style/
  media-style.md  ← la guía de estilo de los recursos, que escribe el agente con todo esto y firmas tú
```

Un kit de marca (`.zip`) o el paquete de un sistema de diseño (`.tgz`) dejado en `sources/`, o la página de ese paquete en npm en `links.md` (se descarga del registro), se abre y solo se toman sus fuentes, iconos, logos y ficheros de tokens; los iconos van a `icons/`, para usarlos tal cual. Un Storybook se lee entero: todas las páginas de documentación y todos los componentes, con sus props, sus historias y su página, desde los manifiestos que publica. Una web bajo el segundo encabezado no se lee, se mira: sus variables CSS, los estilos de sus títulos, enlaces, botones y tarjetas, sus colores según la superficie que ocupan, sus fuentes, su logo y una captura. Lo observado es una pista para el agente, nunca una regla: si contradice el material de marca, gana la marca. Las fuentes de `fonts/fonts.css` van dentro de los vídeos y de los SVG exportados a PNG (`media › fonts`), así que se ven igual en cualquier máquina; una fuente que usa la marca sin ficheros utilizables (una fuente que sirve una web no da permiso para copiarla) se lista en el índice para que la aportes.

### Colores de la marca para los roles

Algunos roles de color de los tokens no existen en la plataforma y coursekit los calcula (`text-muted`, `surface`, `surface-highlight`, `border`, `accent-ink`, `correct-ink`, `wrong-ink`, mezclando el texto, el fondo y el acento), y el radio y la sombra son valores por defecto del paquete. Una marca suele tener su propio color para esos usos. El proyecto los fija en `project.yaml › theme` (un curso con tokens propios, en `course.yaml › theme`), sin tocar el tema de la plataforma:

```yaml
theme:
  source: tenant_default
  roles: {surface: grey-lightest, border: grey-light, text-muted: grey-darkest, accent-ink: text}
  radius: 0
  shadow: none
```

`border` (px; el color de los bordes es el rol `border` de `roles`) y `weights` (`{normal: 300, strong: 500}`) fijan del mismo modo el grosor de los bordes y los dos pesos del texto. Se puede fijar cualquier rol, también uno que da la plataforma cuando la marca dice otra cosa (el texto sobre un relleno de estado, por ejemplo); el curso en la plataforma conserva el de la plataforma. Un rol toma el nombre de un color de la paleta del tema (`coursekit theme roles` la lista), otro rol, o un hex cuando la marca lo define y la paleta no lo tiene. `coursekit theme import` los aplica en lugar de calcularlos, los anota en `origin.set` y, si un nombre no está en la paleta, se detiene con la lista. `coursekit theme roles` muestra cada rol, su valor, de dónde sale y dónde se ve en los recursos (el fondo de las tarjetas de una comparación, la fuente bajo una cifra…), que es como elige una persona, y lo que cita el agente de `/define-theme` cuando propone un color. El radio y la sombra del tema llegan también a los vídeos.

### Fuentes de ilustraciones

Las ilustraciones de una marca se parecen entre sí: una mano, una línea, una paleta. Cuando las ilustraciones de un estudio encajan con la marca, su página de Magnific va bajo `# Fuentes de ilustraciones` en `theme/branding/links.md` (`https://www.magnific.com/author/<nombre>`). Con `MAGNIFIC_API_KEY`, [`coursekit brand`](03-commands.md#coursekit-brand) obtiene el id de ese autor, guarda unas cuantas vistas previas de su obra en `style/` (referencias del estilo; una vista previa no gasta descargas) y escribe la fuente en `theme/branding/illustration-sources.json`.

El agente de multimedia busca ahí primero una **ilustración de concepto**, la que acompaña un concepto del contenido y lo refuerza: [`coursekit media stock CODE ID --find "…"`](03-commands.md#coursekit-media) lista las ilustraciones de las fuentes que coinciden (en inglés, el idioma del catálogo) y se pueden descargar en SVG, y `--take` descarga la elegida, la recolorea a la tinta y el papel de la marca (`media › stock`) y anota en el manifiesto de dónde sale y su licencia. Un estudio suele publicar cada ilustración en varias versiones; con `stock.color: black` solo se buscan las de línea y una a color se rechaza. Lo que pida el guion además (el acento en un elemento) se añade a mano, y cuando nada encaja el agente combina elementos de varias o genera una en el mismo estilo, con las vistas previas como referencia.

Una descarga por la API de un plan con descargas de stock no gasta créditos, dentro de su límite diario; un plan premium no necesita atribución. La opción es `magnific-stock` en `media.yaml › types.image` (`only: illustration`), que se ofrece cuando hay fuentes y clave.

Los tipos de ilustración son los que describe la guía de estilo: un **diagrama** (un tipo propio, dibujado en SVG con los tokens), una **ilustración de concepto** (de las fuentes, en los colores de la guía) y una **escena** con personajes (las simulaciones, una historia), que un curso puede dibujar con un estilo propio en su guía. El guion de cada recurso dice de qué tipo es.

### La guía de estilo de los recursos

`theme/branding/media-style.md` (o, para un curso, `courses/<CODE>/theme/branding/media-style.md`, que gana) es un fichero opcional en el que escribes, en Markdown sencillo, cómo deben verse los recursos de tus cursos: la composición exacta de la portada de un vídeo, los colores por nombre de token, la tipografía y, sobre todo, lo que **no** debe aparecer. El agente de recursos lo lee antes de producir nada y manda sobre los valores por defecto de coursekit en los tipos que cubre; puede ser tan estrecho (solo la portada de los vídeos) o tan amplio como quieras, y añades una sección por tipo según lo necesites. Sé exacto: tamaños en píxeles y la posición de cada elemento hacen que todas las portadas salgan iguales. Los colores se nombran mejor por su token (`--palette-<id>` y `--color-<rol>` de `theme/tokens.css`), que ya están en el proyecto; lo que el fichero mencione de fuera del proyecto (un logotipo, un fichero de fuente) debe copiarse en `theme/branding/`, porque la sesión sin interfaz del agente solo lee el proyecto. No hace falta `coursekit agents` tras editarlo: se lee tal cual. Si una instrucción no se puede cumplir, el agente lo dice y hace lo más parecido sin añadir elementos.

Con material de marca, el agente de `/define-theme` escribe la guía a partir de él ([El material de marca](#el-material-de-marca)): color, gráficos de datos, tipografía, forma, iconos, movimiento, vídeos, imágenes, logo y lo que nunca aparece, cada regla con el lugar de la marca del que sale entre corchetes; lo que la marca no dice va como pregunta, no como regla. Una persona la lee y la firma: la guía del proyecto una vez para todos los cursos que la usan, `coursekit approve media-style`, y la guía propia de un curso con su código, `coursekit approve media-style CODE`: mientras no esté firmada, o después de que cambie, ningún recurso visual se marca como producido (`rules › review › media_style: none` desactiva la firma; el handoff la firma solo). En una sesión sin nadie a quien preguntar, el agente aplica solo lo que la marca dice con todas las letras y lista el resto en `theme/branding/brand-report.md`.

El estilo visual de las escenas, personajes, objetos e ilustraciones se elige con `media › visual › style` (`flat`, `pixel-art`, `3d`, `isometric`, `illustration` o `photo`; ver [`media`](04-configuration.md#media-opciones-de-producción)); `media-style.md` añade los detalles. Las imágenes de referencia del estilo van en `theme/branding/style/` (o en el `theme/branding/style/` del curso). Las escenas de referencia, el resultado al que apuntan las escenas de los cursos (interiores y exteriores, con y sin personas, adultos y niños), van en `style/scenes/`, con hojas de modelo de personaje de ejemplo: el agente pasa la más parecida como referencia de estilo de cada escena nueva, hace una hoja de modelo por personaje y revisa las manos antes de dar una imagen por producida. Sin generador de imágenes el estilo es `visual.fallback` (`flat`), dibujado en SVG.

### Cambiar el theme después de producir el multimedia

Si el theme era incorrecto (por ejemplo el theme por defecto del tenant), el multimedia hecho con él lleva el aspecto equivocado. Para rehacerlo:

1. Corrige el theme en la plataforma (o elige otro) e impórtalo otra vez. Si el theme incorrecto era el del proyecto, `coursekit run define-theme` (sin código) sobrescribe `theme/tokens.json`, que heredan todos los cursos sin theme propio. `coursekit run define-theme CODE` escribe en cambio el theme de ese curso en `courses/<CODE>/theme/` y deja el del proyecto como está ([Un tema por proyecto, uno por curso](#un-tema-por-proyecto-uno-por-curso)).
2. `coursekit media redo CODE` marca los recursos que usan el tema y se hicieron con otros tokens (`--all` marca todos los que usan el tema; `coursekit media redo CODE ID [ID ...]`, los que nombres, para recursos que llevan el tema sin ser de esos tipos, como una imagen con el color de acento pintado). Vuelven a `scripted`.
3. `coursekit handoff CODE` continúa (o, a mano, `/produce-media`, `/assemble`, y otra vez `/produce-media` y `/assemble`): los produce de nuevo, los sube al contenido de su unidad, vuelve a vincular los contenidos al theme (`set_content_theme` se ejecuta en cada montaje) y monta el curso otra vez, de modo que el multimedia nuevo sustituye al antiguo. Con el backend html se vuelve a construir el curso. Las subidas antiguas se quedan en la plataforma hasta su limpieza de almacenamiento.

Un curso ya `delivered` no lo continúa el handoff: rehaz el multimedia y el montaje a mano y entrega una versión nueva.

### Comprobación de contraste

`coursekit theme check` informa del contraste WCAG de los pares de colores que usan los recursos y los componentes; código de salida 1 si alguno falla. Sin tokens, se detiene con `falta theme/tokens.json: derívalo del tema de la plataforma de maquetación` (con el backend html, importa `theme/maqueta.css`). Los pares que se comprueban (los que tienen ambos colores definidos):

| Par (texto sobre fondo) | Uso | Ratio mínimo |
|---|---|---|
| `text` sobre `background` | Texto del cuerpo | 4.5 |
| `text-muted` sobre `background` | Texto secundario | 4.5 |
| `on-accent` sobre `accent` | Texto del botón sobre el color de acento | 4.5 |
| `accent` sobre `background` | Elementos de acento y texto grande | 3.0 |
| `text` sobre `surface` | Texto sobre tarjetas | 4.5 |
| `text` sobre `surface-highlight` | Texto sobre resaltados | 4.5 |
| `on-correct` sobre `correct` | Texto sobre el relleno de correcto | 4.5 |
| `correct-ink` sobre `background` | Lo correcto como tinta (bordes, marcas, texto) | 4.5 |
| `on-wrong` sobre `wrong` | Texto sobre el relleno de incorrecto | 4.5 |
| `wrong-ink` sobre `background` | Lo incorrecto como tinta (bordes, marcas, texto) | 4.5 |

```text
  ok    text sobre background (texto del cuerpo): 21.00:1, mínimo 4.5:1
  FALLO on-accent sobre accent (texto del botón sobre el color de acento): 4.00:1, mínimo 4.5:1
```

La importación imprime las mismas líneas. Un par que falla no la detiene: corrige el color en el tema de la plataforma (o en la variable CSS de la hoja de estilos) e importa de nuevo.

El color de acento de los tokens del proyecto (`accent-ink`, y si no `accent`) pinta también la cabecera del Excel de catálogo ([08-assembly-and-delivery.md](08-assembly-and-delivery.md)).

## Espacio de trabajo de Remotion

Los vídeos (`video`) y algunos GIF se programan con [Remotion](https://www.remotion.dev). `coursekit setup --media` copia una plantilla en `tools/remotion/` y enlaza sus dependencias:

```text
tools/remotion/
├── package.json        scripts: studio (vista previa) y render
├── tsconfig.json
├── node_modules        enlace al almacén de coursekit (no se sube)
└── src/
    ├── index.ts        registra la raíz
    ├── Root.tsx        composición de ejemplo "title-card" (1920×1080, 30 fps, 120 fotogramas)
    ├── Screencast.tsx  una grabación real de la pantalla con zooms que siguen a la locución
    └── theme.ts        importa theme/tokens.json: color, font
```

`theme.ts` lee los tokens del proyecto; para un curso con tema propio, apunta la composición a `courses/<CODE>/theme/tokens.json`. El agente de multimedia añade una composición por cada vídeo en `src/videos/<id-del-recurso>.tsx` y la registra en `Root.tsx`. Desde `tools/remotion/`, `npm run studio` abre la vista previa y `npm run render -- <id-de-composición> <salida>` la renderiza. El proyecto conserva solo las fuentes: las dependencias están en el almacén de coursekit y las comparten todos los proyectos ([Remotion se instala una sola vez](#remotion-se-instala-una-sola-vez)). La opción `remotion` solo está disponible si `node` está instalado y existe `tools/remotion/node_modules`; un enlace que apunta a nada no cuenta (`coursekit setup --media` lo repara). Remotion es gratuito para equipos pequeños; las empresas más grandes necesitan licencia (remotion.dev/license). `coursekit setup --media` añade también a un `tools/remotion/` que ya existe los ficheros que la plantilla ha ganado desde entonces (como `Screencast.tsx`), nunca sobre los que tiene el proyecto.

### El componente Screencast

`Screencast` es la composición de un tutorial sobre una grabación real (receta `screen-recording`): la grabación no se redibuja, y sus zooms se calculan a partir de datos, no van cocidos en el vídeo, así que un zoom se cambia cambiando un número y volviendo a renderizar. Usa los eventos de la grabación (`media/recordings/<id>.events.json`, que escribe `coursekit capture replay`) y las palabras de la locución (`<audio>.words.json`, que escriben `coursekit subtitles` o la voz de ElevenLabs). El zoom sigue a lo que nombra la locución, no a cada clic: un foco entra cuando se dicen sus palabras, se mantiene hasta el final de la frase (o `hold` segundos) y vuelve a la pantalla entera; dos focos cercanos en el tiempo pasan de uno a otro sin alejarse. Sin focos, los clics cercanos en el tiempo y en la pantalla se unen en un solo zoom sostenido. Escalar alrededor de un punto dentro del encuadre siempre lo cubre entero, así que nunca se ven los bordes.

```tsx
import { Screencast } from "../Screencast";
import events from "../../../../courses/PWD/media/recordings/U1-S2-M1.events.json";
import words from "../../../../courses/PWD/media/files/u1-s2-m1.words.json";

<Screencast src={staticFile("U1-S2-M1.mp4")} events={events} words={words}
  focus={[{ word: "longitud mínima", event: "la longitud mínima" }, { word: "guardar", event: "Guardar", hold: 1.5 }]} ring />
```

| Prop | Significado |
|---|---|
| `src` | La grabación. |
| `events`, `words` | Los dos ficheros de arriba. |
| `focus` | Los zooms: `word` (las palabras de la locución con las que entra, la primera vez que se dicen tras el foco anterior) o `at` (un segundo); dónde: `event` (la etiqueta o la nota de un evento) o `fx`/`fy` (fracciones de la pantalla); `scale` y `hold`. Un foco cuyas palabras no se dicen no hace zoom. |
| `auto` | Zoom sobre los grupos de clics cuando no hay focos (por defecto `true`). |
| `startFrom`, `scale`, `ring` | Segundo de la grabación desde el que empieza; cuánto se acerca el zoom (por defecto 1,8); un anillo en el punto de cada foco. |

## Herramientas necesarias por tipo

| Tipo (id) | Herramientas |
|---|---|
| `image` | Las herramientas de stock de creator (MCP del agente) para las imágenes decorativas; `MAGNIFIC_API_KEY`, o el conector de Magnific, para generar el resto (sin ellos, dibujadas en SVG) |
| `infographic`, `diagram` | Ninguna (SVG del agente con los tokens del tema); `MAGNIFIC_API_KEY` para ilustraciones generadas |
| `animated_gif` | `vhs` (terminal), o ninguna (SVG animado), o `node` + Remotion |
| `terminal_demo` | `asciinema` (no en Windows) o `vhs` |
| `video` | `node` + Remotion (`tools/remotion`), `ffmpeg`, un proveedor de voz y `stable-ts` o ElevenLabs para los subtítulos; `vhs` para vídeos de terminal. También los tokens del tema |
| `audio` | Un proveedor de voz (`ffmpeg` para unir MP3 y para Piper) |
| `simulation` | Ninguna (HTML/JS del agente con `tokens.css`) |

Los tipos `infographic`, `diagram`, `animated_gif`, `simulation`, `video` y `terminal_demo` necesitan además los tokens del tema derivados del tema de la plataforma, o de la hoja de estilos con el backend html ([Tokens del tema](#tokens-del-tema)).

## Ejemplo completo

Producir la infografía del curso `PWD`:

```bash
coursekit media extract PWD
coursekit media plan PWD
```

```text
manifest: 3 recursos (pending 3)
U1-S2-M2 [infographic] Anatomía de una contraseña robusta
  - agent-svg (sí): SVG written by the agent with the theme tokens (coursekit theme show); icons with search_stock_icons
```

El agente de multimedia (`/produce-media PWD`, o `coursekit run produce-media PWD`) escribe el SVG con los tokens, lo guarda como `media/files/U1-S2-M2.svg` y lo registra:

```bash
coursekit media set PWD U1-S2-M2 --status produced --recipe agent-svg \
  --file media/files/U1-S2-M2.svg --alt "Diagrama de longitud, variedad y unicidad"
# U1-S2-M2: produced
```

El comando se rechaza si los tokens del curso faltan o están escritos a mano ([El control de los recursos](#el-control-de-los-recursos)): ejecuta antes `/define-theme`. Tras subirlo a la plataforma, el agente registra `coursekit media set PWD U1-S2-M2 --status uploaded --asset-path <ruta>`. El siguiente `coursekit assemble plan` sustituye entonces el recurso reservado por la imagen. Con el backend html no hay subida: el estado `produced` con su `--file` es definitivo, y `coursekit assemble build PWD --unit 1` copia el SVG en el paquete ([Multimedia para el backend html](#multimedia-para-el-backend-html)). Para un vídeo, el mismo flujo añade los pasos `scripted` (guion en `media/scripts/`), `coursekit voice set PWD <proveedor>`, `coursekit tts --course PWD …` y `coursekit subtitles …`.

Siguiente: [08-assembly-and-delivery.md](08-assembly-and-delivery.md)
