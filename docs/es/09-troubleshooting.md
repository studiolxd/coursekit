# Solución de problemas

Descubre qué falta con `coursekit doctor`, arréglalo con `coursekit setup` y consulta los problemas habituales.

## coursekit doctor

```bash
coursekit doctor
```

Imprime qué hay instalado y configurado en este equipo para el proyecto actual. No cambia nada y siempre termina con normalidad. Cada línea lleva una marca y, cuando falta algo, después de una flecha, el comando que lo arregla:

| Marca | Significado |
|---|---|
| `ok` | todo bien |
| `falta` | hace falta y no se encuentra; la línea sugiere cómo arreglarlo |
| `info` | información, o algo opcional |

### Base

| Comprobación | Significado y solución |
|---|---|
| `coursekit <versión> (Python <x.y>)` | `falta` si Python es anterior a la 3.12. Reinstala con uv, que trae un Python válido: `uv tool install --force git+https://github.com/studiolxd/coursekit` |
| `.env` | tu fichero de ajustes personales. Solución: `coursekit setup` |
| `identidad de firma` | el nombre y el email que firman las aprobaciones. Solución: `coursekit setup --identity` |
| `hooks de git` / `no es un repositorio git` | `info` cuando la carpeta no es un repositorio git. En otro caso, los hooks (`.githooks`) no están activos. Solución: `coursekit setup` |
| `MarkItDown (coursekit brief)` | la biblioteca que convierte los documentos del brief. Solución: reinstala coursekit |
| `Node (enlaces web de brief/links.md)` | solo hace falta para descargar las URLs del brief. Solución: `coursekit setup --media` |
| `constructor del backend html (@studiolxd/scorm y esbuild)` | solo aparece cuando `project.yaml › assembly.backend` es html (un curso que usa html por su propio `course.yaml` no lo hace aparecer). `ok` cuando el constructor está instalado en el almacén de coursekit; `info`, con la solución tras la flecha, cuando no lo está. Solución: `coursekit setup` (necesita Node y npm). Mira [El backend html](#el-backend-html) |

### Herramientas de agente

| Comprobación | Significado y solución |
|---|---|
| `servidor MCP de slxd 'slxd-creator'` | `info` con "falta mcp_url" cuando `project.yaml › platform.slxd.mcp_url` está vacío. Solución: ponla y ejecuta `coursekit agents` |
| `<herramienta>: no instalado` | `info`: esa herramienta de IA no está en este equipo. Es inofensivo si usas otra |
| `<herramienta>: skills y comandos` | la herramienta no ve las skills y los comandos generados. Solución: `coursekit agents` |
| `<herramienta>: MCP slxd-creator` | el servidor MCP no está en la configuración de la herramienta (solo aparece si hay URL). Solución: `coursekit agents` |
| `<rol>: <herramienta> · <modelo>` | la herramienta de ese rol no está instalada. Instálala o cambia `<ROLE>_AGENT` en `.env`. `modelo por defecto` significa el modelo propio de la herramienta |
| `redactor y revisor usan la misma herramienta y modelo` | `info`: otro modelo en la revisión detecta más. Cambia `REVIEWER_AGENT` / `REVIEWER_MODEL` |

### Red

| Comprobación | Significado y solución |
|---|---|
| `certificado CA corporativo: NODE_EXTRA_CA_CERTS` | existe un certificado de `project.yaml › network › ca_bundles` pero `NODE_EXTRA_CA_CERTS` no está definido. Solución: `coursekit setup` |
| `ningún certificado CA corporativo configurado ni encontrado` | `info`: no hay nada que hacer salvo que estés detrás de un proxy que inspecciona TLS (mira más abajo) |

### Carpeta espejo

| Comprobación | Significado y solución |
|---|---|
| `sin carpeta espejo` | `info`: `mirror.provider` es `none` |
| `<proveedor>: MIRROR_DIR` | `MIRROR_DIR` está vacío o la carpeta no existe. Solución: defínelo en `.env` con la ruta local de la carpeta sincronizada |

### Theme del proyecto

| Comprobación | Significado y solución |
|---|---|
| `tokens derivados del theme de la plataforma` | `ok`: existe `theme/tokens.json` y lleva el `origin` de un theme de la plataforma o, con el backend html, de una hoja de estilos (importado con `coursekit theme import`) |
| `sin tokens de diseño (theme/tokens.json)` | `info`: el proyecto aún no tiene tokens. Solución: `/define-theme` antes de producir multimedia |
| `tokens escritos a mano, no derivados de la plataforma` | `info`: existe `theme/tokens.json` pero no tiene origen de la plataforma. Solución: `/define-theme` antes de producir multimedia |

La comprobación mira los tokens del proyecto (`theme/`); un curso con theme propio se comprueba con `coursekit theme show --course CODE`. Mira [Theme y tokens de diseño](02-workflow.md#theme-y-tokens-de-diseño).

### Multimedia

Opcional. Instala lo que falte con `coursekit setup --media`: `ffmpeg`, `vhs`, `asciinema` (no disponible en Windows; las demos de terminal usan VHS), `piper`, `stable-ts` y `PIPER_VOICE` (ruta de la voz de borrador). Las cuatro claves de API (`ELEVENLABS_API_KEY`, `AZURE_SPEECH_KEY`, `GOOGLE_TTS_API_KEY`, `MAGNIFIC_API_KEY`) muestran `ok` si están definidas e `info` si no; con `AZURE_SPEECH_KEY` definida y sin `AZURE_SPEECH_REGION`, una línea `falta` `AZURE_SPEECH_REGION` pide la región de tu recurso de Azure Speech. Además muestra dos líneas sobre lo que se instala una vez por equipo ([Dónde están las herramientas](07-media.md#dónde-están-las-herramientas)):

| Comprobación | Significado y solución |
|---|---|
| `almacén de coursekit <ruta> (<tamaño>)` | `info`, aparece si el almacén existe: dónde está y cuánto ocupa. Mira [El almacén de coursekit ocupa mucho espacio](#el-almacén-de-coursekit-ocupa-mucho-espacio) |
| `dependencias de Remotion (tools/remotion/node_modules)` | Aparece si el proyecto tiene `tools/remotion`. `missing` si `node_modules` no está o es un enlace que apunta a nada (se quitó o se movió el almacén). Solución: `coursekit setup --media`. Mira [Faltan las dependencias de Remotion](#faltan-las-dependencias-de-remotion) |

Mira [Multimedia](07-media.md).

## coursekit setup

`setup` prepara este equipo para el proyecto y se puede repetir en cualquier momento. Mira [Primeros pasos](01-getting-started.md) para la lista completa de pasos.

| Opción | Qué hace |
|---|---|
| (ninguna) | `.env`, identidad, red, hooks, roles, skills y comandos, el constructor del backend html (solo en proyectos html), oferta de herramientas de multimedia, informe de doctor |
| `--identity` | solo fija o cambia la identidad de firma |
| `--name NAME`, `--email EMAIL` | la identidad, sin preguntar. Si cambias solo una, se conserva la otra |
| `--roles` | vuelve a elegir la herramienta y el modelo de cada rol |
| `--media` | instala también las herramientas de multimedia, sin preguntar |
| `--yes`, `-y` | no pregunta; toma los valores por defecto |

Sin terminal, `setup` nunca pregunta. Se saltan las preguntas y se informa de lo que falta.

## Problemas habituales

### "no hay identidad de firma" / falta la identidad de firma

Las aprobaciones necesitan tu nombre y tu email. Ejecuta `coursekit setup --identity`, o dalos directamente:

```bash
coursekit setup --identity --name "Ana Ruiz" --email ana@acme.example
```

Se guardan en `.env` como `COURSEKIT_USER_NAME` y `COURSEKIT_USER_EMAIL`. La identidad de git es solo una sugerencia; las firmas nunca la usan.

### "no se encuentra project.yaml en ... ni en ninguna carpeta superior"

Estás fuera de un proyecto. Entra en la carpeta del proyecto (vale cualquier subcarpeta), o señálala:

```bash
COURSEKIT_PROJECT=/ruta/a/acme-courses coursekit status
```

En PowerShell de Windows: `$env:COURSEKIT_PROJECT = "C:\ruta\a\acme-courses"`.

### "coursekit: ... ya es un proyecto; usa `coursekit init --update`"

`init` nunca sobrescribe un proyecto. Usa `coursekit init --update` para refrescar los ficheros generados.

### No se encuentra `coursekit` tras instalarlo

Ejecuta `uv tool update-shell` y abre una terminal nueva.

### "<herramienta> no está instalado en este equipo"

Un comando intentó lanzar una herramienta de IA que no está instalada. `coursekit roles` muestra la herramienta de cada rol y marca las que faltan con `(no instalado)`. Instala la herramienta, o cambia el rol en `.env` (`WRITER_AGENT=opencode`), o elige de nuevo con `coursekit setup --roles`. Para un único lanzamiento usa `--agent` y `--model`. `<ROLE>_AGENT` solo acepta `claude`, `opencode` y `codex`.

### Falta la URL del MCP

Sin `platform.slxd.mcp_url`, los agentes no llegan a SLXD Creator. El diseño instruccional se hace en creator con cualquiera de los dos backends, así que la URL también hace falta con el backend html (el final de `init` avisa cuando falta, elijas el backend que elijas); con el backend creator, el montaje y la entrega se apoyan además en ella. Pon la URL (`https://<tenant>.slxd.app/mcp/creator`) en `project.yaml` y ejecuta `coursekit agents`: añade el servidor a `.mcp.json`, `opencode.json` y `.codex/config.toml`. Si avisa de que un fichero JSON no es válido, arregla ese fichero y vuelve a ejecutarlo.

### Proxy corporativo y certificados

Un proxy que inspecciona TLS hace que Claude Code, opencode, npm y uv fallen con errores de certificado. Lista el certificado en `project.yaml`:

```yaml
network:
  ca_bundles:
    - /etc/ssl/certs/acme-ca.pem
```

Las rutas pueden usar `~` y variables de entorno; se usa la primera que exista en el equipo. Después ejecuta `coursekit setup`: te ofrece definir `NODE_EXTRA_CA_CERTS` y `UV_NATIVE_TLS=1` para tu usuario (el entorno de usuario de Windows, o una línea en `~/.zshrc`, o en `~/.bashrc` si tu shell es bash). Abre terminales nuevas y reinicia las herramientas de IA después. Para hacerlo a mano, define tú ambas variables.

### Problemas con la carpeta espejo

`coursekit publish --check` informa de la configuración sin publicar:

| Mensaje | Solución |
|---|---|
| `no hay carpeta espejo configurada` | hay proveedor pero falta `MIRROR_DIR`: ponlo en `.env` (con `mirror.provider: none`, `publish` solo dice que no hay nada que publicar) |
| `MIRROR_DIR no está definido en .env` | añádelo: la ruta local de la carpeta que sincroniza el cliente de escritorio |
| `MIRROR_DIR no existe` | revisa la ruta; el cliente de escritorio debe haber sincronizado la carpeta |
| `mirror.url es un enlace para compartir sin ruta de carpeta` | copia en su lugar la dirección de la barra del navegador de la carpeta |
| `no se puede reemplazar ... (¿está abierto en Excel?)` | cierra la hoja del catálogo y vuelve a publicar |

Pon entre comillas en `.env` las rutas con espacios. La carpeta espejo es una copia de solo lectura: lo que edites allí se sobrescribe en la próxima publicación. Los comandos que cambian un curso lo publican solos cuando hay carpeta espejo; si no se puede escribir en la carpeta solo imprimen un aviso (`no se pudo actualizar la carpeta espejo`) y el curso no se ve afectado: corrige la causa y ejecuta `coursekit publish`.

### Tokens del theme: faltan, están escritos a mano o han cambiado

Los tokens de diseño de la multimedia (colores y fuentes) se derivan del theme de la plataforma con `/define-theme` (mira [Theme y tokens de diseño](02-workflow.md#theme-y-tokens-de-diseño)). `coursekit theme show --course CODE` dice qué tokens usa un curso y de dónde vienen. Estos son los mensajes y qué hacer; `<CODE>` representa el código del curso.

| Mensaje | Significado y solución |
|---|---|
| `<CODE> no tiene tokens del tema: define el theme con /define-theme antes de producir infografías, esquemas, simulaciones o vídeos (--force para saltarlo)` | Lo muestra `coursekit media plan` como aviso y `coursekit media set CODE ID --status produced` como rechazo, para infografías, esquemas, GIF animados, simulaciones y vídeos. Ni el proyecto ni el curso tienen tokens. Ejecuta `/define-theme` (el theme del proyecto) o `/define-theme <CODE>` (un theme propio para el curso), valida el theme y repite. `--force` marca el recurso de todos modos; úsalo solo si el recurso no depende del aspecto del curso |
| ``no existe <path>: define el theme con /define-theme (o `coursekit theme import`)`` | La misma situación, tal como la informa `coursekit theme show` |
| `los tokens de <CODE> no vienen del theme de la plataforma (escritos a mano): impórtalos con /define-theme (--force para saltarlo)` | Existe `tokens.json` pero no tiene origen de la plataforma, porque se escribió a mano. Ejecuta `/define-theme`: la importación sustituye el fichero por tokens derivados del theme de la plataforma. Si habías ajustado valores a propósito, haz ese cambio en el theme de la plataforma. `coursekit theme show` lo dice así: `los tokens no vienen del theme de la plataforma (escritos a mano): impórtalos con /define-theme` |
| `<asset> se produjo con otros tokens del tema: vuelve a producirlo` | El recurso se marcó `produced` con unos tokens y después se importó el theme otra vez con colores o fuentes distintos. `coursekit media plan` lo lista. Vuelve a producirlo (`/produce-media <CODE> <asset>`) y márcalo con `coursekit media set`. Los recursos marcados antes de que coursekit anotara los tokens no se señalan |
| `el fichero no parece un resultado de get_theme (falta theme.config.colors)` | `coursekit theme import FILE` recibió un fichero que no es el resultado completo de `get_theme` (o no es JSON). Llama a `get_theme` otra vez y guarda el resultado entero, sin tocar, en `.cache/theme/get_theme.json` |
| `no existe el fichero <path>` / `coursekit: theme import necesita el fichero con el resultado de get_theme` | La ruta del fichero es incorrecta o falta: `coursekit theme import .cache/theme/get_theme.json [--course CODE]` |
| `algún par no llega al contraste mínimo: corrígelo en el theme de la plataforma (update_theme) y vuelve a importarlo; no edites los tokens a mano` | Tras la importación, una línea `FALLO <primer plano> sobre <fondo> (<uso>): <ratio>:1, mínimo <mínimo>:1` muestra un par de colores por debajo de su mínimo (4,5:1 para texto, 3,0:1 para el acento sobre el fondo). Corrige el color en el theme de la plataforma (`/define-theme` lo hace con `update_theme`) y vuelve a importar. `coursekit theme check` termina con 1 hasta que todos los pares pasen |
| `algún par no llega al contraste mínimo: corrige el color en la hoja de estilos y vuelve a importarla; no edites los tokens a mano` | Lo mismo que arriba, para el backend html: los tokens salen de `theme/maqueta.css`. Corrige la variable de color en ese fichero y vuelve a ejecutar `coursekit theme import theme/maqueta.css` |
| `falta <path>: derívalo del tema de la plataforma de maquetación` | `coursekit theme tokens` o `check` no encontraron `tokens.json`. Ejecuta `/define-theme` |
| `<path> no es un JSON de tokens válido` | `tokens.json` está dañado. No lo repares a mano: ejecuta `/define-theme` (o `coursekit theme import`) otra vez |
| `AVISO   la fuente «<fuente>» es una fuente incluida en la plataforma: se usa su nombre como familia CSS; ajústalo si no coincide` | No es un error: es una nota de la importación. La familia CSS es el nombre de la fuente; comprueba que sirve para la multimedia |
| `AVISO   el rol de color «<rol>» no se pudo resolver; se usa el valor por defecto` y `AVISO   el theme tiene modo oscuro: los tokens son los del modo claro` | Notas de la importación, no errores. Revisa el rol en el theme de la plataforma si el valor por defecto no es el que quieres; la multimedia sigue el modo claro |

### El backend html

El backend html construye un paquete SCORM por unidad con `coursekit assemble build` (mira [Flujo de trabajo](02-workflow.md#montaje-y-entrega-según-el-backend) y [Montaje y entrega](08-assembly-and-delivery.md)). Estos son sus mensajes y qué hacer; `<CODE>` representa el código del curso.

| Mensaje | Significado y solución |
|---|---|
| ``<CODE> se monta con el backend html: `<acción>` es del backend creator; usa `coursekit assemble build` `` | Ejecutaste `assemble plan`, `diff`, `applied` o `link` en un curso del backend html. Son de creator. Construye con `coursekit assemble build <CODE> --unit N` |
| ``<CODE> se monta con el backend «<backend>»: `build` es del backend html (project.yaml › assembly.backend o course.yaml › assembly.backend)`` | Ejecutaste `assemble build` en un curso del backend creator. Si quieres este curso en html, pon `assembly.backend: html` en su `course.yaml` (o en `project.yaml` para todos los cursos). El primer `coursekit assemble build` prepara el constructor; `coursekit setup` lo hace por adelantado solo cuando `project.yaml` dice html |
| `coursekit: assemble <acción> necesita --unit` | `plan`, `diff`, `applied` y `link` (backend creator) trabajan sobre una unidad: añade `--unit N`. Solo `build` puede ejecutarse sin `--unit` (todas las unidades) |
| `<lección>: <BRICK>: este componente aún no está disponible en el backend html (los juegos llegarán en una entrega posterior)` | La unidad usa un juego (`word-search`, `wordle`, `hangman`, `pasapalabra`, `memory` o `trivial`), por ejemplo `U1-S3: MEMORY: ...`. `assemble build` lo rechaza y `coursekit verify` lo señala como `ensamblado: ...`. Sustitúyelo en el `.md` por otra actividad (una pregunta o una directiva interactiva) o monta ese curso en creator |
| `el paquete no contiene N palabra(s) del contenido: …` | La construcción comprueba que todas las palabras que debe leer quien aprende en `content.md` y `assessment.md` están en la página, y lista las primeras que faltan. La causa habitual es una línea que el formato no representa: por ejemplo una pregunta sin su clave (`pregunta:`), una línea de una directiva en un sitio que no le corresponde o una clave desconocida. Localiza esas palabras en la unidad, corrige el `.md` como describe [Contenido](06-content.md) y construye de nuevo. Nunca edites el resultado |
| `no se pudo preparar el constructor (npm install de @studiolxd/scorm y esbuild): comprueba Node y npm con coursekit doctor` | El constructor (el runtime SCORM y esbuild) se instala una vez por equipo en el almacén de coursekit, con `npm`, y la instalación falló o falta `npm`. Instala Node (`coursekit setup --media` puede hacerlo), revisa la red y, detrás de un proxy, mira [Proxy corporativo y certificados](#proxy-corporativo-y-certificados); después ejecuta `coursekit setup` o construye de nuevo |
| `ha fallado esbuild al empaquetar el reproductor: …` | No terminó el empaquetado del reproductor; el mensaje acaba con lo que dijo esbuild. Una causa frecuente es un script roto en `components/*.js` del proyecto: arréglalo o quítalo. Si el mensaje habla de la instalación, repite `coursekit setup` para reparar el constructor |
| `el recurso X está producido pero su fichero no existe (coursekit media set … --file): se deja el marcador` | Se muestra como aviso. El recurso está marcado como `produced` pero falta su fichero, así que el paquete deja el marcador con su descripción. Registra el fichero con `coursekit media set CODE X --status produced --file media/files/X.<ext>` y construye de nuevo |
| `constructor del backend html (@studiolxd/scorm y esbuild)` en `coursekit doctor` | No es un fallo: la línea es `info` mientras no exista el constructor. Ejecuta `coursekit setup` |

Los paquetes deben probarse en el LMS al que se van a entregar (o en SCORM Cloud) antes de entregarlos: la construcción comprueba el contenido, no cómo registra el seguimiento un LMS concreto. La carpeta de vista previa abierta desde el disco, sin LMS, guarda su estado solo en memoria.

### El backend creator: plan, diff y applied

`coursekit assemble plan`, `diff` y `applied` (mira [El flujo de montaje](08-assembly-and-delivery.md#el-flujo-de-montaje)); en `coursekit verify` los mismos errores empiezan por `ensamblado:`. `<KEY>` es la clave de una lección (`U1-S2`, `U1-E1.1`) y `<N>` un número.

| Mensaje | Significado y solución |
|---|---|
| `<KEY>: directiva desconocida ':::<nombre>'` | Un `:::nombre` del `.md` no está en el registro de directivas. Corrige el nombre ([Contenido](06-content.md#directivas)); si creator tiene un brick nuevo, ejecuta `/sync-directives` |
| `<KEY>: :::<nombre> necesita exactamente una opción correcta` | Un `single-choice` no tiene opción correcta, o tiene más de una. Marca exactamente una con `[x]` |
| `<KEY>: :::<nombre> no tiene paneles: cada uno empieza con una línea '#### Título'` | Una directiva de paneles (`accordion`, `tabs`, `carousel`, `timeline`, `flashcards`...) no tiene líneas `#### Título`. Escribe una por panel |
| `Apartado <N> no está en el diseño` | `content.md` tiene un apartado que el diseño no tiene. Quítalo, o pide un cambio de diseño (`/design-change`) y ejecuta `coursekit sync` |
| `<KEY>: lección sin contenido` | Aviso: el apartado no tiene texto. Escríbelo |
| `labelled-graphic: la imagen '<título>' aún no está producida` | Aviso: la imagen del gráfico con puntos no está producida (o no está subida, con creator). Prodúcela, o acepta la lista simple de puntos |
| ``falta <fichero>: ejecuta antes `coursekit assemble plan``` | `diff` o `applied` antes del plan. Ejecuta `coursekit assemble plan CODE --unit N` |
| `la lección <KEY> no está en el plan` | `applied --lesson` con una clave que el plan no tiene. Usa las claves de `assembly/unit-NN.plan.json` |
| `<N> ids de brick pero el plan tiene <M> bricks en <KEY>` | El número de `--brick-ids` no es el de bricks de la lección: algo no se aplicó, o el plan cambió. Revisa la lección en creator, ejecuta `plan` y `diff` de nuevo y registra los ids en orden |
| `coursekit: link necesita --content-id, --preview o --review` · `coursekit: applied necesita --lesson y --lesson-id (o --content)` | Falta una opción (código de salida 2) |
| `coursekit: unidad <N> no encontrada` | La unidad no está en `course.yaml`; mira `coursekit status CODE` |
| `no existe <ruta>: guarda en ese fichero el resultado de list_brick_types (/sync-directives lo hace)` · `<ruta> no parece un resultado de list_brick_types (falta 'categories')` | `coursekit directives check` necesita el resultado completo de `list_brick_types` guardado como `.cache/list_brick_types.json`. Ejecuta `/sync-directives` |

### Palabras del contenido del otro idioma, verdadero o falso y rellenar huecos

Los tipos de recurso, las claves de las directivas (`pregunta:`, `respuesta:`…) y unas pocas palabras (`verdadero`/`falso`, `(empieza)`/`(contiene)`) se escriben en el idioma del curso; consulta [Tipos de recurso y claves de las directivas por idioma](06-content.md#tipos-de-recurso-y-claves-de-las-directivas-por-idioma). `coursekit verify` y `coursekit assemble plan` rechazan lo que no coincide. En `verify` los mensajes del ensamblador empiezan por `ensamblado:`; la etiqueta que sigue indica dónde: `U1-S2` es el apartado 2 de la unidad 1 y `U1-E1.1` es la actividad de evaluación 1.1.

| Mensaje | Significado y solución |
|---|---|
| `content.md:LÍNEA: tipo de recurso multimedia desconocido o no permitido 'Infographic' (usa: Imagen, Vídeo, GIF animado, Infografía, Esquema/Diagrama, Simulación interactiva, Demo interactiva en terminal, Audio)` | La palabra de `> **[RECURSO MULTIMEDIA — …]**` no es del idioma del curso (aquí un curso en español con una palabra en inglés), o su tipo no está en `content.placeholder_types` de `config/rules.yaml`. Escribe una de las palabras que salen tras `usa:` (no importan las mayúsculas ni los espacios). En la configuración los tipos son ids (`infographic`, no la palabra); consulta [Configuración](04-configuration.md) |
| `la clave 'question:' es del idioma «en»; en este curso se usan: feedback, feedback-correcto, feedback-incorrecto, imagen, objetivo, posición, pregunta, respuesta, respuestas, título` | Una línea `clave: valor` de una directiva usa una clave del otro idioma (`question:` en un curso en español, `pregunta:` en uno en inglés). No se ignora: sustitúyela por la clave del idioma del curso de la lista (`pregunta:`). Los nombres de las directivas (`:::single-choice`) no cambian. Si todo el curso está en el idioma equivocado, revisa `language` en `course.yaml` y `content_language` en `project.yaml` |
| `:::true-false necesita 'respuesta: verdadero\|falso'` | La pregunta no tiene línea `respuesta:`, o su valor no es una de las dos palabras del idioma del curso (`verdadero` / `falso` en español; `true` / `false` en inglés). Escribe `respuesta: verdadero` o `respuesta: falso` |
| `:::fill-in-the-blank necesita huecos escritos como {respuesta} en 'pregunta:'` | La línea `pregunta:` no tiene ningún hueco. Escribe cada hueco entre llaves dentro de la frase: `pregunta: Una contraseña robusta es {larga}.` (varias respuestas aceptadas: `{larga/extensa}`). La clave es la del idioma del curso |
| `elementos de :::pasapalabra: '- A (empieza\|contiene): definición :: RESPUESTA'` | Un elemento del rosco no sigue la forma letra, modo entre paréntesis, definición, `::`, respuesta. El modo es `(empieza)` o `(contiene)` en español y `(starts)` o `(contains)` en inglés |

### Locución, subtítulos y registros de multimedia

Estos son los mensajes de `coursekit voice`, `tts`, `subtitles` y `media`; el flujo de la locución está en [Multimedia](07-media.md#proveedores-de-voz). `<programa>` es `ffmpeg`, `piper` o `stable-ts`, y `<host>` el servicio (por ejemplo `api.elevenlabs.io`).

| Mensaje | Significado y solución |
|---|---|
| ``hay varios proveedores de voz disponibles (<lista>): elige uno para el curso con `coursekit voice set <CODE> <provider> [--voice …]``` | `tts` encontró varios proveedores configurados y el curso no tiene ninguno elegido. Ejecuta el comando que indica |
| `este curso usa <etiqueta> pero no está configurado aquí (<CLAVES> en .env)` | La voz del curso está fijada (`course.yaml › media.voice`) pero este equipo no tiene sus claves. Ponlas en `.env` (`coursekit setup --media` las pide), o elige otro proveedor con `coursekit voice set` |
| `no hay ningún proveedor de voz configurado (claves de ElevenLabs, Azure o Google, o Piper, en .env)` | No hay ningún proveedor disponible. Define una clave en `.env`, o instala la voz de borrador con `coursekit setup --media` |
| `hacen falta ELEVENLABS_API_KEY y una voz (ELEVENLABS_VOICE_ID o --voice)` | ElevenLabs no tiene voz por defecto: define `ELEVENLABS_VOICE_ID` o pasa `--voice`, o fíjala para el curso con `coursekit voice set CODE elevenlabs --voice ID` |
| `define PIPER_VOICE en .env (ruta a una voz .onnx) o pasa --voice` | Piper necesita un fichero de voz. `coursekit setup --media` descarga una y define `PIPER_VOICE` |
| `piper no está instalado (coursekit setup --media)` · `stable-ts no está instalado (coursekit setup --media)` | Ejecuta `coursekit setup --media` (necesita `uv`) |
| `<programa> no está instalado o no se encuentra en el PATH (coursekit setup --media)` | Falta `ffmpeg` (unir las partes del MP3, pasar Piper a MP3) u otro programa, o está instalado pero no en el `PATH` de esta terminal. Ejecuta `coursekit setup --media` y abre una terminal nueva |
| `<programa> terminó con error (código <N>)` | El programa se ejecutó y falló. Ejecuta el mismo programa a mano para leer su propio mensaje. `stable-ts` descarga su modelo la primera vez, así que necesita red |
| `<host> respondió <estado> <motivo>: revisa la clave, la región y la voz configuradas` | El servicio de voz rechazó la petición. `401` o `403`: clave incorrecta o (Azure) una región que no es la del recurso (`AZURE_SPEECH_REGION`); `404`: la voz no existe (`ELEVENLABS_VOICE_ID`, `AZURE_SPEECH_VOICE`, `GOOGLE_TTS_VOICE` o `--voice`); `429`: cuota o créditos agotados. Si falla, no se escribe nada |
| `no se pudo conectar con <host>: <motivo>` | Sin red, o un proxy que inspecciona TLS: mira [Proxy corporativo y certificados](#proxy-corporativo-y-certificados) |
| `no existe el fichero <ruta>` | La ruta de `--in`, `--audio` o `--text` es incorrecta (son relativas a donde ejecutas el comando) |
| `coursekit: voice set necesita CODE y PROVIDER` | `coursekit voice set PWD azure`; con `voice list` el curso es opcional |
| ``no se encuentra el recurso <ID> (ejecuta antes `coursekit media extract`)`` | El manifiesto no tiene ese id: ejecuta `coursekit media extract CODE` y revisa el id (son posicionales) |
| `el estado debe ser uno de ['pending', 'scripted', 'produced', 'uploaded']` | `media set --status` acepta uno de esos cuatro; `orphaned` lo pone `extract` |
| `--download-title y --download-asset-path necesitan --download FILE` | Añade `--download FICHERO` al mismo comando |
| `coursekit: set necesita el id de un recurso` · `coursekit: esta acción necesita un código de curso` | Falta un argumento (código de salida 2): `coursekit media set CODE ID ...` |
| `<ID>: sus especificaciones piden un fichero descargable (PDF…): coursekit media set … --download media/files/<file>` | Aviso de `media plan`: registra el fichero con `--download` (mira [Multimedia](07-media.md#el-manifiesto-multimedia)) |

### Faltan herramientas de multimedia

Ejecuta `coursekit setup --media`. En macOS necesita [Homebrew](https://brew.sh); en Windows necesita `winget`; en Linux solo imprime qué instalar (`sudo apt install ffmpeg nodejs npm asciinema`, más [vhs](https://github.com/charmbracelet/vhs)). Además necesita `uv` para instalar `piper` y `stable-ts`, y `npm` para el espacio de Remotion. Si falla la descarga de la voz, vuelve a ejecutarlo cuando tengas conexión.

### No se puede crear el enlace de Remotion

`coursekit setup --media` instala las dependencias de Remotion una sola vez en el almacén de coursekit y enlaza `tools/remotion/node_modules` a ellas. Si no puede crear el enlace (Windows sin permiso para crear uniones o un sistema de ficheros sin enlaces, como algunas unidades de red o extraíbles), no falla: ejecuta `npm install` dentro de `tools/remotion/` y el proyecto conserva su propia copia, como cualquier proyecto de Node. Verás `ok: dependencias de Remotion` en lugar de `ok: dependencias de Remotion compartidas desde <ruta>`. Todo funciona igual; el único coste es el espacio en disco de una copia más (unos 230 MB, más el navegador que Remotion descarga en su primer render, unos 600 MB).

Lo mismo ocurre si `npm install` falla en el almacén. Para tener la copia compartida, arregla la causa (red, proxy, permisos) y vuelve a ejecutar `coursekit setup --media`. Si el proyecto ya tiene una carpeta `node_modules` real, setup la conserva y lo dice; para compartir en su lugar, borra `tools/remotion/node_modules` y repite.

### Faltan las dependencias de Remotion

`coursekit doctor` muestra `falta  dependencias de Remotion (tools/remotion/node_modules)` cuando la carpeta no existe o cuando es un enlace a un almacén que ya no está: se quitó el almacén (por ejemplo con `coursekit uninstall`), se movió, o `COURSEKIT_HOME` apunta a otro sitio distinto del que usabas al instalar. Ejecuta `coursekit setup --media`: las instala de nuevo en el almacén si hace falta y repara el enlace, sin tocar las fuentes de `tools/remotion`. Si cambiaste `COURSEKIT_HOME` a propósito, asegúrate de que está definida en la terminal antes de ejecutarlo.

### El almacén de coursekit ocupa mucho espacio

El almacén guarda las dependencias de Remotion y el navegador que descarga (unos 230 MB más unos 600 MB), una sola vez para todos tus proyectos. Dónde está:

| Sistema | Almacén |
|---|---|
| macOS | `~/Library/Application Support/coursekit` |
| Linux | `~/.local/share/coursekit` |
| Windows | `%LOCALAPPDATA%\coursekit` |

`coursekit doctor` imprime su ruta y su tamaño. Para guardarlo en otro sitio (otro disco), define `COURSEKIT_HOME` **en la terminal, antes de ejecutar `coursekit setup`**, y mantenla definida en todas las sesiones siguientes (por ejemplo en el perfil de tu shell, o con `setx COURSEKIT_HOME "D:\coursekit"` en Windows), porque `doctor`, `setup` y `uninstall` buscan el almacén donde dice la variable; un valor en el `.env` de un proyecto solo valdría para ese proyecto:

```bash
export COURSEKIT_HOME=/Volumes/Grande/coursekit     # PowerShell: $env:COURSEKIT_HOME = "D:\coursekit"
coursekit setup --media
```

Con la variable definida, `setup --media` instala allí y vuelve a enlazar el proyecto en el que se ejecuta; ejecútalo una vez en cada proyecto que tuviera un enlace al almacén anterior. Para llevarte la instalación existente, mueve el contenido de la carpeta antigua a la nueva antes de ejecutarlo. Después borra el almacén antiguo, o deja que lo haga `coursekit uninstall` antes de cambiar la variable. Para liberar el espacio sin cambiar nada más, ejecuta `coursekit uninstall`: pregunta por grupos y quita las carpetas de dependencias; los proyectos conservan sus fuentes y `coursekit setup --media` las instala de nuevo cuando las necesites. Los detalles, en [Comandos](03-commands.md) y [Configuración](04-configuration.md#el-almacén-de-la-máquina).

### Otra instalación tras editar package.json

La carpeta de Remotion en el almacén se nombra con un hash del `package.json` del proyecto (y de su `package-lock.json`). Un proyecto que añade o actualiza una dependencia en `tools/remotion/package.json` ya no coincide con la instalación compartida: el siguiente `coursekit setup --media` hace una segunda instalación, `workspaces/remotion-<otro-hash>/`, y enlaza el proyecto a ella. Es normal y esperado; los demás proyectos siguen usando la primera. Cuesta el espacio en disco de una instalación más. Las carpetas de instalaciones que ya no usa ningún proyecto se quedan en el almacén hasta que `coursekit uninstall` las quita (o las borras a mano). Si no necesitas tu cambio, restaura el `package.json` de la plantilla y repite `coursekit setup --media`.

### Windows

- Los mensajes muestran las rutas con barras normales (`courses/PWD/course.yaml`).
- `setup` fija `core.autocrlf input` en el proyecto cuando activa los hooks.
- `asciinema` no existe en Windows; las demos de terminal usan VHS.
- Las variables del proxy se guardan en el entorno de usuario de Windows mediante PowerShell.
- Pon entre comillas en `.env` las rutas con espacios, como `MIRROR_DIR`.
- Las voces de Piper se guardan en `%LOCALAPPDATA%\piper`, y el almacén de coursekit (las dependencias compartidas de Remotion) en `%LOCALAPPDATA%\coursekit`. En `tools/remotion/` el enlace `node_modules` es una unión (junction); si Windows o la unidad no lo permiten, el proyecto instala su propia copia ([No se puede crear el enlace de Remotion](#no-se-puede-crear-el-enlace-de-remotion)).

### Problemas al firmar

| Mensaje | Solución |
|---|---|
| `no hay terminal interactiva` | firma en tu propia terminal, o en el chat del agente como `! coursekit approve ... --yes` |
| `hay que aprobar el diseño de nuevo` | el diseño cambió después de tu firma: revísalo y ejecuta `coursekit approve design <CODE>` |
| `falta design/matrix.json` | pide al agente de diseño que exporte antes el diseño (`/approve-design <CODE>`) |
| `el diseño tiene N errores de validación` | corrígelos en SLXD Creator, exporta de nuevo y firma |
| `la unidad N está 'verified': necesita antes la revisión (...)` | ejecuta `coursekit review <CODE> N`, o registra tu propia revisión con `coursekit reviewed <CODE> N --by "Nombre"`, o pon `review.ai: skip` en `rules` si el proyecto no usa revisión con IA |
| `falta la revisión con IA ...` | no existe el informe `reviews/unit-NN-ai-review.md`: haz la revisión, o registra la de una persona con `coursekit reviewed <CODE> N --by "Nombre"` |
| `la unidad N ha cambiado desde la revisión con IA (...)` | la unidad se editó después de la revisión y el mensaje nombra las partes. Vuelve a revisarla con `coursekit review <CODE> N` (solo esas partes), o firma igualmente con `--force` si lo aceptas |
| `la unidad N no pasa la verificación` | ejecuta `coursekit verify <CODE> --unit N` y corrige los errores |
| `registrada, sin commit` | la aprobación está guardada en `course.yaml` pero git no pudo confirmarla (por ejemplo, la carpeta no es un repositorio git). Haz el commit tú o arregla git |
| `<CODE> está en pausa desde ...` | el curso está en pausa: mira la sección siguiente |

### El curso está en pausa o la revisión del cliente bloquea la entrega

Un curso en pausa rechaza los comandos que lo modifican (`write`, `review`, `reviewed`, `approve`, `assemble`, `sync` sin `--check`, `media set`, `client`, los comandos de entrega y `run` de un comando para ese curso); los comandos de lectura, como `status`, siguen funcionando. La revisión del cliente (cuando el proyecto la exige) rechaza la entrega. Estos son los mensajes y qué hacer; `<CODE>` representa el código del curso (por ejemplo `PWD`).

| Mensaje | Significado y solución |
|---|---|
| ``<CODE> está en pausa desde <fecha> (<motivo>); estaba en «<estado>». Reanúdalo con `coursekit resume <CODE>` `` | El curso está en pausa. Mira el motivo con `coursekit status <CODE>`; si puede continuar, ejecuta `coursekit resume <CODE>` (vuelve al estado que tenía). Los agentes no pueden hacerlo: es un comando de personas |
| `<CODE> ya está en pausa` | `coursekit hold` sobre un curso que ya está en pausa. No hay nada que hacer |
| `<CODE> no está en pausa (estado: <estado>)` | `coursekit resume` sobre un curso que no está en pausa. No hay nada que hacer |
| ``<CODE> necesita la revisión del cliente antes de entregarse (delivery.yaml › client_review.required): `coursekit client <CODE> send` `` | El proyecto (o el curso) exige la revisión del cliente y todavía no hay ninguna ronda. Abre una con `coursekit client <CODE> send` o, si el cliente no la va a revisar, anota el motivo con `coursekit client <CODE> skip --reason "..."` |
| `<CODE> espera a la respuesta del cliente (ronda N, enviada a ...)` | Hay una ronda abierta. Cuando el cliente responda, anótalo: `coursekit client <CODE> approve --by "Nombre"` o `coursekit client <CODE> changes --note "..."` |
| `el cliente pidió cambios en <CODE>: aplícalos, vuelve a montar y abre otra ronda ...` | La última ronda se cerró con `changes`. Aplica los cambios (`/client-feedback <CODE>` trata los comentarios), ejecuta `/assemble <CODE>`, firma de nuevo las unidades que retrocedieron y abre la ronda siguiente con `coursekit client <CODE> send` |
| ``la ronda N sigue abierta: ciérrala con `approve` o `changes` `` | Intentaste `send` o `skip` con una ronda abierta. Ciérrala antes |
| `<CODE> está en «<estado>»: la revisión del cliente empieza con el curso montado (estado «assembly»)` | `send` (o `skip`) necesita el curso en `assembly`. Termina antes el montaje o, tras un `changes`, espera a que el curso vuelva a `assembly` |
| `no hay enlaces de revisión en las unidades: lanza /assemble (crea el enlace de cada unidad) o pasa --where con el enlace` | `send` no tiene ningún enlace que anotar. Lanza `/assemble <CODE>` (crea el enlace de revisión de cada unidad), anótalos tú con `coursekit assemble link <CODE> --unit N --review URL`, o envía un solo enlace con `--where URL` |
| `<CODE> no tiene ninguna ronda abierta con el cliente` | `approve` o `changes` sin ninguna ronda abierta. `coursekit status <CODE>` muestra la última ronda |
| `coursekit: approve necesita --by con el nombre de quien aprueba` | Añade `--by "Nombre"`: el nombre de la persona que aprueba en nombre del cliente |
| `coursekit: skip necesita --reason` | Añade `--reason "..."` |
| `aviso: <CODE> está en «<estado>», no en un estado de entrega (assembly, client_review): el paquete se registra, pero el curso no se marca como entregado` | No es un error: `delivery add` registró el paquete, pero el curso solo pasa a `delivered` desde `assembly` o `client_review`. Normalmente el curso no estaba montado o retrocedió a un estado anterior. Corrige la causa y vuelve a registrar los paquetes con `delivery add` (o comprueba que `coursekit status <CODE>` muestra lo que esperas). Con el backend html, `assemble build` lleva el curso de `media` a `assembly` solo cuando todas las unidades están construidas, así que este aviso aparece si alguna unidad aún no se construyó |

Si la revisión del cliente no es obligatoria y no la quieres, no hay nada que hacer: con `client_review.required: false` el curso se puede entregar desde `assembly`. Mira [Configuración](04-configuration.md#delivery-exportación-scorm-y-revisión-del-cliente).

### Registrar un paquete de entrega

`coursekit delivery add` comprueba el fichero antes de registrar nada.

| Mensaje | Significado y solución |
|---|---|
| `<fichero>.zip: imsmanifest.xml no está en la raíz del zip` | El zip tiene los ficheros dentro de una carpeta (se comprimió desde la carpeta superior). Comprime el contenido para que `imsmanifest.xml` quede en la raíz, o vuelve a tomar el paquete de la exportación |
| `<fichero>.zip: no es un fichero zip válido` | El fichero no es un zip, está dañado (una descarga interrumpida), o la ruta no existe. Descárgalo o constrúyelo de nuevo |
| `el paquete debe estar en <…/courses/PWD/delivery>` | `--file` debe apuntar dentro de la carpeta de entrega del curso. Mueve el zip allí, con el nombre de `coursekit delivery name` |
| `no se encuentra la unidad <N>` | `--unit` no es una unidad del curso |
| `coursekit: delivery add necesita --file` · `coursekit: delivery <acción> necesita --unit y --version` | Falta una opción (código de salida 2) |
| `registrado <fichero> · unidades pendientes de la v<versión>: [2, 3]` | No es un error: las unidades indicadas aún no tienen paquete de esa versión. El curso pasa a `delivered` cuando todas lo tienen |

Registrar el mismo paquete dos veces añade una segunda entrada a `course.yaml › deliveries`; no hace daño, pero no hace falta.

### Problemas con el servidor MCP

Una sesión sin interfaz (el handoff, `--headless`) no puede iniciar sesión en creator ni pedir un permiso. Cuando el agente de diseño no pudo usar creator, el handoff se para y nombra la causa, leída del registro de la sesión (`.cache/logs/`):

| Qué dice la parada | Significado y arreglo |
|---|---|
| `el servidor MCP «slxd-creator» no está autorizado (estado: needs-auth) ...` | El servidor de `.mcp.json` no tiene sesión. Abre tu herramienta de IA en la carpeta del proyecto y autorízalo una vez con `/mcp`; o inicia sesión en el conector de creator de tu cuenta y pon `platform.slxd.connector` |
| `el agente intentó usar las herramientas de «claude.ai <nombre>», pero en una sesión sin interfaz no están permitidas ...` | Creator está conectado por tu cuenta (un conector de claude.ai), cuyas herramientas se llaman distinto que las del servidor del proyecto. Pon `platform.slxd.connector: "<nombre>"` en `project.yaml` (viene en el mensaje) y vuelve a lanzarlo |
| `el conector «claude.ai <nombre>» de platform.slxd.connector está en estado needs-auth, no conectado ...` | El conector que nombraste no tiene sesión: inicia sesión en él desde tu herramienta de IA (`/mcp`) |
| `El agente dijo: ...` en vez de una causa | El registro no muestra un problema con los servidores; las palabras del propio agente son la mejor pista. La sesión completa está en `.cache/logs/` |

Continúa con `coursekit handoff <CODE>`: si la propuesta de diseño nunca llegó a crearse en creator, vuelve a diseñar el curso (`/new-course` sobre el curso existente); si solo falta la exportación, la pide.

### Paradas del handoff

`coursekit handoff` termina con `handoff parado. <motivo>` y `Para seguir donde se quedó, una vez resuelto:  coursekit handoff <CODE>` (código de salida 1). Los motivos que no son una unidad que no verifica (mira [Problemas al firmar](#problemas-al-firmar)):

| Motivo | Significado y solución |
|---|---|
| `<CODE>: el proyecto exige la revisión del cliente para entregar (client_review.required) y el handoff no la hace` | El handoff nunca abre una revisión del cliente. En un curso nuevo se niega antes de crear nada. Pon `client_review.required: false` en `config/delivery.yaml` (o en el `course.yaml`), o usa el flujo normal. Un curso cuya revisión ya está aprobada u omitida continúa |
| ``<CODE>: el curso está en pausa; continúa con `coursekit resume <CODE>` y después `coursekit handoff <CODE>``` | Una persona lo pausó. Reanúdalo primero |
| ``<CODE>: hay una ronda de revisión del cliente abierta; el handoff no la gestiona (`coursekit client <CODE> ...`)`` | Cierra la ronda con `approve` o `changes` ([Revisión del cliente](08-assembly-and-delivery.md#revisión-del-cliente)) y ejecuta el handoff otra vez |
| `el curso <CODE> ya existe; para continuarlo: coursekit handoff <CODE>` | Un handoff nuevo con un título cuyo código ya existe. Continúa el curso con su código, o pasa otro `--code` |
| `<CODE>: quedan recursos multimedia sin producir tras los intentos: <ids>` · `<CODE>: el multimedia necesita el theme y no se pudo definir (/define-theme)` | El agente de multimedia no terminó, o no se pudo derivar ningún theme. Lee el registro de la sesión en `.cache/logs/`, corrige la causa (claves, herramientas: `coursekit doctor`) y continúa |
| `el agente de media intentó ejecutar <programas>, pero en una sesión sin interfaz no está permitido…` (tras la línea de los recursos multimedia) | Una sesión sin interfaz no puede pedir permiso, así que el agente de media solo ejecuta `coursekit`, `npx`, Python y los programas que sus recetas declaran. Añade los que nombra a `rules › handoff › media_tools` en `config/rules.yaml` (`handoff:` / `media_tools: [blender, gs]`) y vuelve a lanzar `coursekit handoff <CODE>`. Coursekit lee los nombres del registro de la sesión; `bash`, `sh` y `node` dejan al agente ejecutar cualquier orden: añádelos solo si lo aceptas |
| `<CODE>: el curso no queda montado tras los intentos (/assemble)` · `<CODE>: el curso no queda entregado tras los intentos (/deliver)` | Ejecuta `/assemble` o `/deliver` a mano para ver el error, o lee el registro en `.cache/logs/` |
| `<CODE>: la revisión con IA sigue diciendo «not ready» en la unidad <N> tras corregirla (reviews/unit-NN-ai-review.md)` | Lee el informe de la revisión, corrige la unidad tú y continúa |
| ``<CODE>: el paso «<estado>» no avanzó nada; míralo con `coursekit status <CODE>``` | El agente terminó sin cambiar el estado. Mira `coursekit status` y el registro |

## Cambiar el idioma

Hay dos idiomas. El **idioma del curso** (`content_language` en `project.yaml` y `language` en cada `course.yaml`) es el del contenido. El **idioma de la interfaz** es el de los mensajes de coursekit y el de lo que te dicen los agentes. coursekit elige el idioma de la interfaz en este orden:

1. el idioma elegido en `init` (mientras se ejecuta);
2. `COURSEKIT_LANG` (`es` o `en`) del entorno o de tu `.env`;
3. `ui_language` en `project.yaml` (compartido por el equipo; si falta, `content_language`);
4. el idioma del sistema (`LC_ALL`, `LC_MESSAGES`, `LANG`);
5. inglés.

Para cambiarlo solo para ti, pon `COURSEKIT_LANG=es` en `.env`. Para todo el equipo, cambia `ui_language` en `project.yaml` y ejecuta `coursekit agents` para que los comandos generados lo recojan. Los textos de `--help` también lo siguen.

El idioma de la interfaz no toca el contenido. Las palabras de `content.md` (encabezados, tipos de recurso, claves de las directivas) siguen el **idioma del curso**; si lo cambias en un curso ya escrito, `coursekit verify` rechaza las palabras antiguas hasta que las reescribas (consulta [Palabras del contenido del otro idioma, verdadero o falso y rellenar huecos](#palabras-del-contenido-del-otro-idioma-verdadero-o-falso-y-rellenar-huecos)).

## Refrescar los ficheros generados

| Comando | Qué refresca |
|---|---|
| `coursekit agents` | skills, comandos, agentes, documentos y ajustes de las herramientas (`.claude/`, `.opencode/`, `.coursekit/`, `.mcp.json`, `opencode.json`, `.codex/config.toml`). Hace falta tras cambiar `project.yaml`, `.agents/` o los modelos de los roles en `.env`, tras actualizar coursekit y tras un pull (los hooks de git lo hacen por ti) |
| `coursekit init --update` | `AGENTS.md`, `CLAUDE.md`, `.env.example`, `.gitignore`, `config/*.example.yaml` y los hooks. Nunca `project.yaml` |

`init --update` conserva cualquier fichero generado que hayas editado a mano y te lo dice. Para tomar la plantilla nueva, borra ese fichero y vuelve a ejecutarlo. `coursekit agents` solo sobrescribe los ficheros que generó (llevan una marca) y deja los tuyos, informándolos como conservados.

## Preguntas frecuentes

**¿Puede firmar un agente por mí?** No. `coursekit approve` está denegado en los ajustes generados de Claude Code y opencode, y las instrucciones del proyecto lo prohíben para cualquier herramienta. Usa `!` en el chat si quieres firmar sin salir de él. Lo mismo vale para `coursekit client` (rondas de revisión del cliente), `coursekit hold`, `coursekit resume`, `coursekit handoff` y `coursekit reviewed --by`.

**¿Puede ejecutarse todo el proceso sin mí?** Sí: `coursekit handoff "<título>" <horas>`. Firma como Coursekit Handoff y nadie revisa el curso; mira [Flujo de trabajo](02-workflow.md#modo-handoff). No hace la revisión del cliente: con `client_review.required: true` se niega a empezar, y se para en un curso en pausa o con una ronda abierta. Si se para, dice por qué ([Paradas del handoff](#paradas-del-handoff)); corrígelo y ejecuta `coursekit handoff <CODE>` para continuar.

**¿Es obligatoria la revisión del cliente?** No por defecto. Lo es si el proyecto lo dice (`client_review.required: true` en `config/delivery.yaml`) o el curso (`delivery › client_review › required` en su `course.yaml`). Mira [Flujo de trabajo](02-workflow.md#revisión-del-cliente-opcional).

**¿Cómo pauso un curso?** `coursekit hold <CODE> --reason "..."`, y `coursekit resume <CODE>` para continuar. Mira [Flujo de trabajo](02-workflow.md#pausar-un-curso).

**¿Necesito saber git?** Poco. coursekit hace el commit de las firmas por ti; los agentes no hacen commit ni push salvo que se lo pidas.

**¿Qué backend debo usar?** Con `creator`, la plataforma aloja el contenido y exporta los paquetes SCORM, y el cliente revisa en los enlaces de creator. Con `html`, coursekit construye por sí mismo el paquete de cada unidad (`coursekit assemble build`): no hace falta ninguna plataforma para montar, alojas tú el zip o la vista previa para el cliente y el paquete debe probarse en tu LMS. El backend html todavía no tiene los juegos (`word-search`, `wordle`, `hangman`, `pasapalabra`, `memory`, `trivial`); si un curso los necesita, móntalo en creator. El diseño instruccional se hace en creator con cualquiera de los dos. Se fija en `project.yaml › assembly.backend` (lo pregunta el asistente de `init`) y, para un solo curso, en `course.yaml › assembly › backend`. Mira [Flujo de trabajo](02-workflow.md#montaje-y-entrega-según-el-backend).

**¿Pueden trabajar dos personas en el mismo proyecto?** Sí: `project.yaml`, `courses/` y `config/` se versionan, y cada persona tiene su propio `.env`, identidad, herramientas y modelos. Tras un pull, los hooks refrescan los ficheros generados.

**¿Dónde están los logs de las ejecuciones sin interfaz?** En `.cache/logs/`, un fichero por sesión. La carpeta no se versiona.

**¿De dónde salen los colores y las fuentes de la multimedia?** Del theme de la plataforma de maquetación, nunca de un fichero escrito a mano: `/define-theme` deriva de él `theme/tokens.json` y `tokens.css` (mira [Theme y tokens de diseño](02-workflow.md#theme-y-tokens-de-diseño)). Con el backend `html` salen de las variables CSS de `theme/maqueta.css` sobre el layout base del paquete (`coursekit theme import theme/maqueta.css`).

**¿Dónde cambio una regla de producción?** No en una skill ni en `.env`: crea `config/rules.yaml` solo con los valores que cambies (mira [Configuración](04-configuration.md)).

**He cambiado una skill y se ha sobrescrito.** Las skills se generan. Pon tu versión en `.agents/skills/<nombre>/SKILL.md` (mira [Agentes](05-agents.md)).

**¿Cómo quito todo lo que instaló coursekit?** Antes de quitar el paquete, ejecuta `coursekit uninstall --dry-run` para ver la lista y `coursekit uninstall` para quitarlo: pregunta por cada grupo (las dependencias de Node compartidas, las herramientas de multimedia instaladas con uv, las voces descargadas, las líneas añadidas a los ficheros de tu terminal y, en Windows, las variables de usuario) y, si el almacén de coursekit se queda vacío, lo borra. Los paquetes del sistema (`ffmpeg`, `node`, `vhs`, `asciinema`) solo se listan, con el comando para quitarlos tú. Después ejecuta `uv tool uninstall slxd-coursekit`. Los proyectos no se tocan nunca: borra a mano sus carpetas, o su `.claude/`, `.opencode/`, `.codex/`, `.coursekit/` y `tools/`. Si quitaste el paquete antes, `uv tool install git+https://github.com/studiolxd/coursekit` devuelve el comando para que puedas ejecutar `coursekit uninstall`. Mira [Primeros pasos](01-getting-started.md#desinstalar).

**¿Qué Python necesito?** 3.12 o 3.13. uv lo instala por ti.

Vuelve al [índice](index.md).
