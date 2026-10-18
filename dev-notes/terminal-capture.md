# Captura de terminal y escenarios

Nota de desarrollo: se borra cuando la función esté validada y publicada (lo que dure va a `docs/` y a los READMEs).

Objetivo: que el agente de media grabe él mismo lo que muestra una aplicación de terminal (una TUI como la de un agente de
programación, una instalación, unas órdenes), sin tomar la pantalla de la persona, y que prepare antes el entorno que la
grabación necesita (un proyecto de ejemplo, un estado concreto, una máquina sin el programa instalado).

## Decisiones de base

- **Un tercer modo de captura, `terminal`**, junto a `browser` y `desktop`: `coursekit capture allow CODE --mode terminal`
  (sin perfil ni ventana). Las herramientas son las del servidor `coursekit-capture` de siempre; la sesión no abre ninguna
  ventana: coursekit lanza una shell en un pseudoterminal propio (`pty`), le escribe lo que el agente teclea y lee lo que
  sale. Solo macOS y Linux (Windows no tiene `pty`; allí sigue el modo `desktop`).
- **Un emulador de terminal en el proceso** (`pyte`, Python puro, en el extra `capture`): mantiene la pantalla a partir de lo
  que sale; de ella salen el texto que lee el agente (`read_screen`) y la imagen que ve (`screenshot`, dibujada con Pillow y
  una fuente monoespaciada del sistema). No hace falta tmux ni asciinema: el `.cast` (asciicast v2) lo escribe coursekit.
- **Material real**: lo que se graba es la salida real del programa real; dibujarla con un emulador es lo que hace cualquier
  terminal (y el reproductor de asciinema). No se inventa nada de la interfaz.
- **Un solo registro para los tres tipos de recurso**: la sesión entera queda como `.cast`. De él salen
  `media/recordings/<id>.cast` (receta `asciinema`, demo interactiva con el texto copiable), `<id>.mp4` y
  `<id>.events.json` (receta `screen-recording`: el vídeo dibujado fotograma a fotograma y los puntos que nombra la locución,
  para los zooms) y `<id>.png` (receta `screenshot`, con `save_shot`).
- **Sin `replay`**: la sesión se graba mientras ocurre. Las pausas del modelo entre acciones se recortan (`idle_limit`), y
  los tramos `record_start`/`record_stop` cortan el registro (lo anterior al primer tramo se reproduce al instante, así la
  pantalla empieza como estaba).
- **Datos personales tapados en el texto, antes del emulador**: cada trozo de salida pasa por `pii.replace` (fuera de las
  secuencias de escape) con, además, el usuario, la carpeta personal, el nombre de la máquina, el nombre y el correo de git
  y los valores de las variables de entorno que parecen secretos (`KEY`, `TOKEN`, `SECRET`, `PASSWORD`). Lo que ve el modelo,
  la imagen, el `.cast` y el vídeo salen ya tapados; el original no se guarda. Al cerrar, la pantalla de cada momento se lee
  otra vez y lo que siga pareciendo un dato personal va como aviso a la revisión.
- **Escenarios** (`media/stages/<nombre>/`): el entorno de una grabación, escrito por el agente con datos inventados y
  versionado con el curso, que coursekit monta de cero antes de cada sesión. Así cada toma empieza limpia (sin `/undo`) y se
  puede repetir.

## 1. Escenario

```
courses/<CODE>/media/stages/recipes/
  stage.yaml
  files/            # el proyecto tal como empieza (se copia entero)
```

```yaml
title: Recipe website with a search that ignores accents   # qué es (para la persona)
folder: projects     # carpeta dentro de la carpeta personal donde se monta (por defecto capture.yaml › terminal.folder)
setup:               # órdenes que lo dejan listo, en la copia, antes de cada sesión (no se graban)
  - git init -q && git add -A && git commit -qm "First version"
home: real           # real: la carpeta personal de la persona (la configuración y la sesión del programa);
                     # clean: una vacía, como una máquina recién instalada
hide: [opencode]     # órdenes que no están en el PATH (una máquina sin el programa)
env: {}              # variables de entorno añadidas
```

- La copia se monta en `<home>/<folder>/<nombre>`. coursekit apunta en su caché las carpetas que ha creado y nunca borra ni
  pisa una que no sea suya (si existe y no es suya, se para y lo dice).
- `home: clean`: una carpeta personal vacía en la caché de coursekit, con las variables XDG apuntando dentro.
- `hide`: cada carpeta del PATH que contiene una orden oculta se sustituye por una carpeta de enlaces a todo lo demás.
- Entorno de la shell: `bash --noprofile --norc`, `PS1='\W $ '`, `TERM=xterm-256color`, `COLORTERM=truecolor`, `LANG` del
  idioma del curso, autor de git inventado (de `pii.people`). Nada de los ficheros de arranque de la persona en pantalla.
- `coursekit capture stage CODE NOMBRE [--prepare "orden"]`: monta el escenario y dice dónde (también para el agente, que
  lo usa para probarlo antes de grabar).

## 2. Bloque `capture` del guion en modo terminal

```capture
mode: terminal
stage: recipes
prepare: ["rm -f AGENTS.md"]       # lo propio de este recurso, después del setup del escenario (no se graba)
terminal: {cols: 120, rows: 34}
steps: [...]                       # lo escribe session_end
```

## 3. Herramientas en modo terminal

- `session_start(code, asset_id)`: monta el escenario, lanza la shell en su carpeta y devuelve la pantalla (texto e imagen).
- `read_screen()`: el texto de la pantalla (barato; el que más usa el agente). `screenshot()`: la imagen.
- `type(text)` (letra a letra, a `replay.type_delay_ms`), `key(combo)` (Enter, Tab, Escape, flechas, ctrl+c...),
  `wait(ms)`, `wait_for(text, timeout_ms)` (hasta que el texto sale en pantalla, para las respuestas del programa).
- `point(x, y, note)`: la celda que nombrará la locución (zoom del vídeo). `save_shot`, `record_start`, `record_stop`,
  `session_end`. Los clics, el arrastre y `navigate` no existen en la terminal.
- Rechazo fijo: escribir cuando la línea del cursor pide una contraseña, una frase de paso o un token.

## 4. Configuración: `capture.yaml › terminal`

`cols`, `rows`, `width` (px de las imágenes y del vídeo), `font` (ruta; vacío: la primera monoespaciada que se encuentre),
`idle_limit` (s), `folder`, `palette` (fondo, texto y los 16 colores ANSI, claros y de alto contraste). `modes` incluye
`terminal`.

## 5. Handoff y plan

- Un recurso que espera a una persona pero que el permiso en vigor deja capturar (modo y receta compatibles) es trabajo del
  agente de media: el handoff le pasa la ronda. Si tras las rondas no lo ha capturado, no se para: va al informe como antes.
- `coursekit media plan` dice que el agente lo puede capturar.

## 6. Orden de trabajo

1. `capture_terminal.py` (pty, pyte, render, `.cast`, recorte, vídeo) y sus tests con una shell de verdad.
2. `capture_stage.py` y `coursekit capture stage`.
3. Modo `terminal` en `capture.py`, `capture_session.py` (inicio, herramientas, cierre), `replay` lo rechaza, `doctor`.
4. Handoff y plan.
5. Skill de `/produce-media`, docs en/es, READMEs.

## Por comprobar a mano

- Una sesión real de OpenCode: pantalla alternativa, colores de 24 bits, ancho de los símbolos de su interfaz.
- Que el vídeo y las imágenes se lean bien a 1920 px y con la fuente del sistema.
- Que `wait_for` baste para esperar a un modelo que tarda en contestar.

## Estado

- [x] Pasos 1 a 5 (sin commit todavía): `capture_terminal.py` (pty propio con un hilo lector, `pyte`, tapado del texto fuera
  de las secuencias de escape con espera a que la palabra o la secuencia estén enteras, dibujo con Pillow: bloques y líneas
  rectas como rectángulos para que no haya costuras, fuentes de reserva para los símbolos que no tiene la monoespaciada,
  fondo del color dominante; recorte por tramos y pausas; `.cast` v2 con la paleta; vídeo con el `encode` de `replay`, que
  ahora acepta PNG), `capture_stage.py` (montaje de cero, registro de carpetas propias, `home: clean`, `hide` con carpetas
  de enlaces, autor de git inventado, `locale` del idioma en `lang/<code>.yaml`), modo `terminal` en `capture.py`
  (`MODE_RECIPES`, `capturable`, `mount_stage`), sesión y herramientas (`read_screen`, `wait_for`, `point_text`),
  `coursekit capture stage`, `replay` lo rechaza, `doctor`, handoff (lo capturable es trabajo del agente; ronda extra para
  componer lo que se acaba de aprobar), `media plan`, skill, docs en/es y READMEs. `pyte` en el extra `capture`.
  Tests en `tests/test_capture_terminal.py`, con una shell de verdad.
- [x] Probado a mano: OpenCode 2.0.24 dentro del emulador (logotipo, caja del mensaje, colores de 24 bits, barra inferior).
- [ ] Un handoff completo con el modo terminal en un curso real.
