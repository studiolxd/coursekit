# Producción multimedia

Cómo los recursos multimedia reservados en el contenido se convierten en recursos producidos: el manifiesto, las opciones de producción, la locución y los subtítulos, los tokens del tema y las herramientas que necesita cada tipo.

## Recursos multimedia y tipos

Un recurso multimedia se escribe en `content.md` (formato en [06-content.md](06-content.md#recursos-multimedia)). Su tipo es uno de ocho tipos de recurso. Cada tipo tiene un **id** en inglés, igual en todos los cursos, que es lo que usan la configuración (`config/media.yaml › types` y `uses_theme`, `config/rules.yaml › content.placeholder_types`), el manifiesto multimedia (`media/manifest.yaml › assets[].type`), la salida de `coursekit media plan` y el control del tema. Lo que la persona **escribe** en el recurso reservado es la palabra del idioma del curso para ese tipo (por ejemplo `Infografía` en un curso en español e `Infographic` en uno en inglés); la tabla que relaciona cada id con sus palabras está en [06-content.md](06-content.md#recursos-multimedia). La palabra del otro idioma es un error de `coursekit verify` que enumera las palabras válidas.

| Id | Significado | Opciones, por orden de preferencia (qué necesita cada una) |
|---|---|---|
| `image` | Imagen | `magnific-api` (`MAGNIFIC_API_KEY`) · `magnific-mcp` (herramienta MCP del agente `images_generate`) · `creator-stock` (herramienta MCP del agente `search_stock_images`) |
| `infographic` | Infografía | `agent-svg` (nada) · `magnific-api` |
| `diagram` | Esquema o diagrama | `agent-svg` |
| `animated_gif` | GIF animado | `vhs` (comando `vhs`; solo contenido de terminal) · `agent-svg-animated` (nada) · `remotion-gif` (`node` y `tools/remotion/node_modules`) |
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

Una opción con varios `needs:` debe cumplirlos todos. `only: terminal` limita una opción a los recursos que muestran un terminal; lo decide el agente a partir de la descripción del recurso. Si no hay nada disponible, `media plan` imprime `ninguna opción disponible: instala una herramienta o define una clave (coursekit config media)`.

```text
U1-S1-M1 [image] Nota adhesiva en un monitor
  - magnific-mcp (si el agente tiene la herramienta MCP): Claude's Magnific connector
  - creator-stock (si el agente tiene la herramienta MCP): Licensed stock from creator (Pexels, Pixabay, Unsplash, Freepik) + import_stock_image
U1-S2-M1 [video] Construir una frase de paso
  - vhs (sí, solo para contenido terminal): Terminal video
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

## Proveedores de voz

Un curso usa **una** voz para toda su locución, así que un curso nunca mezcla voces. La elección se guarda en `course.yaml › media.voice`.

| Proveedor | Necesita (en `.env`) | Voz por defecto | Notas |
|---|---|---|---|
| `elevenlabs` | `ELEVENLABS_API_KEY`; una voz en `ELEVENLABS_VOICE_ID` o `--voice` | ninguna | Mejor calidad; escribe subtítulos exactos a partir de sus marcas de tiempo |
| `azure` | `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION` | `es-ES-ElviraNeural` / `en-GB-SoniaNeural`; `AZURE_SPEECH_VOICE` la sustituye | Voces neuronales |
| `google` | `GOOGLE_TTS_API_KEY` | `es-ES-Chirp3-HD-Aoede` / `en-GB-Chirp3-HD-Aoede`; `GOOGLE_TTS_VOICE` la sustituye | Voces Chirp 3 HD |
| `piper` | `PIPER_VOICE` (ruta a una voz `.onnx`) y el comando `piper`; `PIPER_SPEAKER` para voces con varios locutores | el fichero de `PIPER_VOICE` | Voz local de borrador |

La voz por defecto depende del idioma del curso (`es` o `en`). En `media plan` y `media providers` las opciones de voz se llaman `elevenlabs-api`, `azure-api`, `google-api` y `piper` (los proveedores de arriba), además de `elevenlabs-mcp`, el agente usando directamente el conector de ElevenLabs (sin `coursekit tts`); esta siempre aparece, porque solo el agente puede saber si tiene el conector. Las opciones de subtítulos son `elevenlabs-timestamps` y `stable-ts`.

```bash
coursekit voice list PWD                   # proveedores, disponibilidad y la voz del curso
coursekit voice set PWD azure              # fija el proveedor (y su voz por defecto)
coursekit voice set PWD piper --speaker 1  # un locutor de una voz de Piper con varios locutores
coursekit voice set PWD elevenlabs --voice <id-de-voz>
```

`voice set` necesita el código del curso y el proveedor. Si el proveedor no está configurado en este equipo, avisa (puede que otras personas del equipo lo tengan) pero lo guarda igualmente. Con varios proveedores disponibles y ninguno elegido, `tts` se detiene y te pide ejecutar `voice set`; sin ninguno disponible, indica qué claves definir.

## `coursekit tts`

Lee un guion y escribe la locución:

```bash
coursekit tts --course PWD --in courses/PWD/media/scripts/U1-S2-M1.md --out courses/PWD/media/files/U1-S2-M1.mp3
```

| Opción | Significado |
|---|---|
| `--in FICHERO`, `--out FICHERO` | Guion (los espacios en blanco se colapsan) y audio de salida; ambas obligatorias |
| `--course CODE` | Usa la voz de ese curso y su idioma. Sin ella, el idioma es `es` |
| `--engine elevenlabs\|azure\|google\|piper` | Fuerza un proveedor en lugar del del curso |
| `--voice V` | Fuerza una voz. Si no: la voz del curso (si es el mismo proveedor), después la variable de entorno del proveedor y, por último, la voz por defecto del idioma |
| `--speaker N` | Locutor de una voz de Piper con varios locutores |

El proveedor es `--engine`; si no, el `media.voice.provider` del curso; si no, el único proveedor disponible. Los guiones largos se parten al final de las frases (Azure 4.000 bytes, Google 4.500) y se unen con `ffmpeg`; Piper también necesita `ffmpeg` para escribir MP3 (un `--out` que termina en `.wav` conserva el WAV). ElevenLabs escribe además `<out>.vtt` (mismo nombre, `.vtt`) con subtítulos a partir de sus marcas de tiempo, agrupados al final de las frases o cada unos 84 caracteres.

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
             "derived": ["accent-strong", "highlight", "line", "surface", "text-soft"],
             "defaults": ["radius", "space", "shadow"], "notes": []},
  "color": {"background": "#FFFFFF", "text": "#000000", "headings": "#1B365D", "accent": "#0A58CA",
            "on-accent": "#FFFFFF", "link": "#0A58CA", "correct": "#14733A", "on-correct": "#000000",
            "wrong": "#B3261E", "on-wrong": "#000000", "text-soft": "#595959", "surface": "#F5F5F5",
            "highlight": "#E2EBF9", "line": "#CCCCCC", "accent-strong": "#0A58CA"},
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
| `text-soft`, `surface`, `highlight`, `line`, `accent-strong` | Los deriva coursekit a partir de los colores anteriores (mezclas de texto, fondo y acento); el texto suave se mantiene al menos a 4,5:1 sobre el fondo. `accent-strong` es igual a `accent`. Constan en `origin.derived`. |
| `font.family`, `font.headings`, `font.ui` | Las asignaciones de fuentes del tema: la pila de fuentes del sistema, una fuente subida por su nombre (seguida de la pila del sistema como alternativa) o una fuente incluida en la plataforma por su id, con una nota porque el nombre puede no coincidir con su familia CSS. |
| `font.size-base`, `font.line-height` | El tamaño base de fuente y el interlineado del tema. |
| `radius`, `space`, `shadow` | Valores por defecto del paquete: la plataforma no tiene esos valores. Constan en `origin.defaults`. |

Con el backend html los tokens salen de las variables CSS de la maqueta base del paquete con la hoja de estilos encima (`coursekit theme import FICHERO.css`); una referencia `var(--x)` se resuelve, gana la última declaración de una variable, y coursekit no deriva nada:

| Variable CSS | Token |
|---|---|
| `--color-<nombre>` | `color.<nombre>`: `background`, `text`, `text-soft`, `headings`, `accent`, `accent-strong`, `on-accent`, `link`, `surface`, `highlight`, `line`, `correct`, `wrong` (la maqueta base las declara todas; añade otras si las necesitas). Un valor que no es un color simple (un degradado, `color-mix()`) se conserva tal como está escrito y queda fuera de la comprobación de contraste, con una nota. |
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

Los tipos de recurso que usan los tokens figuran en `uses_theme` de la configuración multimedia (por defecto `infographic`, `diagram`, `animated_gif`, `simulation` y `video`; consulta [04-configuration.md](04-configuration.md)). Para ellos:

- `coursekit media plan` avisa cuando el curso tiene recursos de esos tipos y sus tokens faltan o están escritos a mano (ni origen `creator` ni `css`), y por cada recurso producido o subido que se hizo con otros tokens distintos de los actuales (hay que producirlo de nuevo).
- `coursekit media set CODE ID --status produced` (o `uploaded`) se rechaza mientras los tokens no estén derivados: del tema de la plataforma (backend creator) o de la hoja de estilos del proyecto (backend html, `coursekit theme import FICHERO.css`). `--force` se salta la comprobación, para el caso poco habitual de un curso que deliberadamente no sigue el tema.
- Cuando se acepta, el recurso guarda una huella de los tokens (`theme`, en `media/manifest.yaml`). Si el tema cambia y se vuelve a importar, la huella ya no coincide y `plan` avisa. La huella abarca los colores, las tipografías, el radio, los espaciados y las sombras, no el origen ni la fecha, así que importar de nuevo el mismo tema no genera avisos.

El agente multimedia se detiene y pide a la persona que ejecute `/define-theme` cuando faltan los tokens, en lugar de inventar colores.

### Comprobación de contraste

`coursekit theme check` informa del contraste WCAG de los pares de colores que usan los recursos y los componentes; código de salida 1 si alguno falla. Sin tokens, se detiene con `falta theme/tokens.json: derívalo del tema de la plataforma de maquetación` (con el backend html, importa `theme/maqueta.css`). Los pares que se comprueban (los que tienen ambos colores definidos):

| Par (texto sobre fondo) | Uso | Ratio mínimo |
|---|---|---|
| `text` sobre `background` | Texto del cuerpo | 4.5 |
| `text-soft` sobre `background` | Texto secundario | 4.5 |
| `on-accent` sobre `accent` | Texto del botón sobre el color de acento | 4.5 |
| `accent` sobre `background` | Elementos de acento y texto grande | 3.0 |
| `text` sobre `surface` | Texto sobre tarjetas | 4.5 |
| `text` sobre `highlight` | Texto sobre resaltados | 4.5 |
| `correct` sobre `background` | Respuesta correcta | 4.5 |
| `wrong` sobre `background` | Respuesta incorrecta | 4.5 |

```text
  ok    text sobre background (texto del cuerpo): 21.00:1, mínimo 4.5:1
  FALLO on-accent sobre accent (texto del botón sobre el color de acento): 4.00:1, mínimo 4.5:1
```

La importación imprime las mismas líneas. Un par que falla no la detiene: corrige el color en el tema de la plataforma (o en la variable CSS de la hoja de estilos) e importa de nuevo.

El color de acento de los tokens del proyecto (`accent-strong`, y si no `accent`) pinta también la cabecera del Excel de catálogo ([08-assembly-and-delivery.md](08-assembly-and-delivery.md)).

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
    └── theme.ts        importa theme/tokens.json: color, font
```

`theme.ts` lee los tokens del proyecto; para un curso con tema propio, apunta la composición a `courses/<CODE>/theme/tokens.json`. El agente de multimedia añade una composición por cada vídeo en `src/videos/<id-del-recurso>.tsx` y la registra en `Root.tsx`. Desde `tools/remotion/`, `npm run studio` abre la vista previa y `npm run render -- <id-de-composición> <salida>` la renderiza. El proyecto conserva solo las fuentes: las dependencias están en el almacén de coursekit y las comparten todos los proyectos ([Remotion se instala una sola vez](#remotion-se-instala-una-sola-vez)). La opción `remotion` solo está disponible si `node` está instalado y existe `tools/remotion/node_modules`; un enlace que apunta a nada no cuenta (`coursekit setup --media` lo repara). Remotion es gratuito para equipos pequeños; las empresas más grandes necesitan licencia (remotion.dev/license).

## Herramientas necesarias por tipo

| Tipo (id) | Herramientas |
|---|---|
| `image` | `MAGNIFIC_API_KEY`, o el conector de Magnific, o las herramientas de stock de creator (MCP del agente) |
| `infographic`, `diagram` | Ninguna (SVG del agente con los tokens del tema); `MAGNIFIC_API_KEY` para ilustraciones generadas |
| `animated_gif` | `vhs` (terminal), o ninguna (SVG animado), o `node` + Remotion |
| `terminal_demo` | `asciinema` (no en Windows) o `vhs` |
| `video` | `node` + Remotion (`tools/remotion`), `ffmpeg`, un proveedor de voz y `stable-ts` o ElevenLabs para los subtítulos; `vhs` para vídeos de terminal. También los tokens del tema |
| `audio` | Un proveedor de voz (`ffmpeg` para unir MP3 y para Piper) |
| `simulation` | Ninguna (HTML/JS del agente con `tokens.css`) |

Los tipos `infographic`, `diagram`, `animated_gif`, `simulation` y `video` necesitan además los tokens del tema derivados del tema de la plataforma, o de la hoja de estilos con el backend html ([Tokens del tema](#tokens-del-tema)).

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
