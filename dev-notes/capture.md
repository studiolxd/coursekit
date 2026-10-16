# Captura con navegador y computer use

Nota de desarrollo: se borra cuando la función esté validada y publicada (lo que dure va a `docs/` y a los READMEs).

Objetivo: que coursekit produzca él mismo la captura o la grabación real que hoy aporta una persona en
`media/recordings/<id>.png|mp4` (recetas `screenshot` y `screen-recording`), con el permiso de la persona y
anonimizando los datos reales que aparezcan. Las recetas que componen sobre la grabación y la regla de
`--depicts interface` no cambian: sigue siendo material real.

## Decisiones de base

- **Un servidor MCP local de coursekit** (`coursekit capture serve`, stdio), registrado en `.mcp.json`, `opencode.json`
  y `.codex/config.toml` como el de slxd. coursekit sigue sin llamar a la API de Anthropic y vale para los tres agentes.
  Sus herramientas imitan las acciones de computer use, así que cualquier modelo sabe manejarlas.
- **La anonimización se hace dentro del servidor**, antes de devolver cada imagen: ningún píxel sin anonimizar llega al
  modelo.
- **Solo la persona** inicia sesión, da permiso y aprueba: son comandos denegados a los agentes (`DENY_CLAUDE`,
  `DENY_OPENCODE` en `agents.py`), como `coursekit approve`.
- **Los estados del manifiesto no cambian** (`pending, scripted, produced, uploaded`). La captura lleva su subestado en
  `asset.capture.state` (`captured` → `approved`); al aprobarla el fichero entra en `media/recordings/<id>` y
  `/produce-media` lo compone como ahora.
- **Primero datos de demostración.** El guion pide una cuenta o un entorno de pruebas con datos inventados; la
  anonimización es la red de seguridad, no la medida principal.

## 1. Configuración: `defaults/capture.yaml`

En `config.NAMES` y `init.CONFIG_NAMES`. Esbozo:

```yaml
enabled: false                 # nothing is captured until a project turns it on
grant_minutes: 60              # how long `coursekit capture allow` lasts
modes: [browser, desktop]      # the modes a project allows
screenshot:
  max_edge: 1920               # px: what the model receives (coordinates are in this space)
  device_scale: 2              # browser: sharpness of the final captures
profiles: {}                   # name → {start_url, allow_domains: [...], account: "label, never the secret"}
redact:
  mode: replace                # replace (fictional data) | blur | pixelate | solid
  patterns: [email, phone, iban, card, national_id, ip]
  names: true
  faces: true
  extra_terms: []
  selectors: []
  pixel_check: true            # browser: OCR over the final captures as a safety net
raw:
  keep_days: 7                 # originals with no redaction, outside the project, deleted when approved
desktop:
  window_only: true            # clicks outside the chosen window are refused
  stop_key: "ctrl+alt+esc"
```

Los conjuntos de datos ficticios (nombres, empresas, dominios `example.com`) van en `lang/es.yaml` y `lang/en.yaml`.

## 2. Comandos

De la persona (denegados a los agentes):

| Comando | Qué hace |
|---|---|
| `coursekit capture login PERFIL` | Chromium visible con perfil persistente; la persona inicia sesión (SSO, MFA) y cierra |
| `coursekit capture logout PERFIL` | Borra el perfil |
| `coursekit capture allow CODE [ID…] --mode browser\|desktop [--profile P] [--window "Nombre"] [--minutes N]` | Permiso con caducidad; sin él el servidor no hace nada |
| `coursekit capture revoke CODE` | Lo anula antes de tiempo |
| `coursekit capture approve CODE ID` | Mueve el resultado a `media/recordings/`, borra el original, anota quién y cuándo |
| `coursekit capture reject CODE ID --note "…" [--mask "…"]` | Rechaza y añade lo que faltó tapar |

También para el agente:

| Comando | Qué hace |
|---|---|
| `coursekit capture profiles` | Perfiles, desde cuándo tienen sesión y la etiqueta de la cuenta (si la sesión sigue viva se sabe al abrirla, en `session_start`) |
| `coursekit capture serve` | El servidor MCP |
| `coursekit capture replay CODE ID` | Repite la sesión grabada sin modelo (cuando la aplicación cambia de versión) |
| `coursekit capture redact CODE ID` | Anonimización por píxeles de una grabación aportada por una persona → `captured` |
| `coursekit capture review CODE ID` | Hoja de contactos HTML local con las zonas tapadas y los avisos de `pixel_check` |

Perfiles, permisos y originales viven en la caché del usuario (`~/Library/Caches/coursekit/capture/…` o el equivalente),
con permisos `0700`, nunca en el proyecto.

## 3. Herramientas del servidor MCP

- `session_start(code, asset_id)` → modo, tamaño de captura, dominios permitidos. Falla si `enabled` es falso, si no hay
  permiso vigente, si el recurso no es `depicts: interface` con receta `screenshot`/`screen-recording`, o si la sesión del
  perfil ha caducado.
- `screenshot()`, `zoom(x, y, w, h)`: siempre anonimizadas.
- `left_click`, `double_click`, `right_click`, `mouse_move`, `drag`, `scroll`, `type(text)`, `key(combo)`, `wait(ms)`,
  `navigate(url)` (solo navegador). Coordenadas en el espacio de la captura; el servidor las escala.
- `save_shot(name)`, `record_start()`, `record_stop()`.
- `session_end(notes)` → escribe el resultado y el guion repetible, `capture.state: captured`.

Rechazos fijos: escribir en `input[type=password]` o en campos de un solo uso; navegar fuera de `allow_domains`; en
escritorio, clics fuera de la ventana; seguir tras un redirect al login (se detiene y pide `capture login`).

## 4. Bloque de pasos del guion

En `media/scripts/<id>.md`, junto a la prosa, un bloque `capture` con esquema fijo en inglés (como las simulaciones);
los textos van en el idioma de la aplicación.

```capture
mode: browser
profile: acme-admin
start: /settings/security
viewport: {width: 1440, height: 900}
steps:
  - click: {label: "Seguridad"}
  - fill: {label: "Longitud mínima", value: "12"}
  - shot: paso-2
  - record: start
  - click: {label: "Guardar"}
  - wait: 1500
  - record: stop
mask: [{selector: ".account-email"}, {text: "Ana García"}]
```

## 5. Anonimización

- **Navegador** (`dom.js`, inyectado antes de cargar): recorre los nodos de texto (y los nuevos con `MutationObserver`),
  sustituye lo que coincide por un dato ficticio coherente (hash del valor → índice del conjunto), difumina avatares,
  `img`/`video`/`canvas` y los `selectors`, tapa contraseñas. `pixel_check`: OCR sobre las capturas finales; lo que siga
  coincidiendo sale como aviso en `review`.
- **Editar el HTML en directo, decisiones** (para `dom.js`): `add_init_script` (antes que la página y en todos los frames) y
  página oculta hasta la primera pasada; solo `nodeValue` de los nodos de texto, nunca la estructura; **nunca** el `value` de
  `input`/`textarea`/`contenteditable` (un Guardar enviaría el dato falso a la aplicación real): se tapan con una capa;
  tampoco se reescriben respuestas de red (`page.route`) por la misma razón; atributos visibles (`title`, `placeholder`,
  `alt`, título de la pestaña); shadow DOM abierto, y `attachShadow` parcheado para que los cerrados nazcan abiertos;
  sustituto de longitud y formato parecidos; mismo valor → mismo ficticio en toda la sesión. Lo que no es texto (imágenes,
  `canvas`, PDF, vídeo) se difumina o queda para `pixel_check`. Desplegables nativos y autocompletado no salen en el
  screencast.
- **Píxeles** (escritorio y `capture redact`): OCR (Apple Vision en macOS; rapidocr-onnxruntime en el resto) → patrones +
  nombres + `extra_terms`; caras con YuNet (OpenCV); en vídeo, fotogramas de muestra + seguimiento de cajas con OpenCV
  interpolado, render con ffmpeg (`boxblur`/`drawbox`).
- **Revisión humana obligatoria** antes de entrar en `media/recordings/`.

## 6. Modos de ejecución

- **Navegador**: `launch_persistent_context` con el perfil y el Chrome/Edge/Chromium de la máquina (`executable_path`, el mismo
  que busca `htmlkit.playcheck.find_browser`: no se descarga ningún navegador), ventana visible; `page.screenshot`; vídeo con el screencast de
  CDP → ffmpeg.
- **Escritorio**: macOS (Quartz/ScreenCaptureKit, `CGEventPost`, `ffmpeg -f avfoundation` recortado), Windows (mss +
  `SendInput`), X11 (mss + `xdotool`). Wayland fuera de esta fase (límite conocido).
- `doctor`: extra instalado, navegador de la máquina, ffmpeg y, en macOS, "Grabación de pantalla" y "Accesibilidad".

## 7. Integración

- `pyproject.toml`: extra `capture` (playwright, mcp, opencv-python-headless, rapidocr-onnxruntime, mss; pyobjc Quartz y
  Vision solo en macOS).
- `agents.py`: registra `coursekit-capture` cuando `enabled`; denegaciones de `capture login|logout|allow|revoke|approve|reject`.
- `media.py`: `awaiting_recording()` distingue "falta la captura" de "pendiente de revisión"; `media plan` lo muestra.
- `handoff.py`: lista los recursos en `captured` con la orden de revisarlos.
- `agentkit/skills/media-production`: sección de captura (`{{tokens}}` desde `capture.yaml`); no usar herramientas de
  navegador propias del agente; nunca iniciar sesión.
- `lang/messages/capture.yaml`; docs en/es: 03, 04, 05, 07, 09 y READMEs.

## 8. Tests

- Puros: patrones con ejemplos inventados es/en, sustitutos coherentes, caducidad de permisos, escalado de coordenadas,
  clics fuera de ventana, campos de contraseña, lista de dominios, bloque `capture`, denegaciones, configuración.
- Con Playwright (marca `capture`, se saltan si falta): panel "ACME" en `tests/fixtures/capture/` servido con
  `http.server`.
- Escritorio: modo simulado; pruebas reales a mano en macOS. CI: un trabajo en Linux con Chromium para `capture`.

## 9. Orden de trabajo

1. `capture.yaml`, perfiles, `login`/`logout`/`profiles`, `allow`/`revoke` y sus denegaciones.
2. Detección de datos personales, datos ficticios por idioma, anonimización por píxeles, `capture redact` y
   `review`/`approve`/`reject`.
3. Modo navegador, `dom.js`, servidor MCP, sesiones y `replay`.
4. Handoff (lista lo que espera revisión), registro del servidor en `agents`, skill de `/produce-media`.
5. Escritorio: macOS, después Windows y X11.
6. Vídeo de escritorio con ffmpeg (el de navegador ya está, en `replay`).

## Por comprobar

- Que opencode y Codex pasen al modelo las imágenes que devuelve una herramienta MCP. Si no, la captura con agente queda
  para Claude Code; `replay` y `redact` sirven en todos.
- El peso del extra (OpenCV, OCR y Playwright suman cientos de MB): por eso va aparte.

## Estado

- [x] Paso 1 (sin commit todavía): `defaults/capture.yaml` (`enabled`, `grant_minutes`, `modes`, `profiles`; las claves de
  los pasos siguientes se añaden con ellos), `capture.py`, `coursekit capture login|logout|profiles|allow|revoke`,
  denegaciones (`agents.DENY_*`, `launch.CLAUDE_DENY`), `uninstall` borra `capture/`, extra `capture = ["playwright"]`,
  docs en/es (03, 04, 07) y READMEs, `tests/test_capture.py`. El login real con navegador falta probarlo a mano.
- [x] Paso 2 (sin commit todavía): `pii.py` (patrones de `capture.yaml › redact › patterns` con comprobación de dígitos
  de control donde el texto es exacto; nombres por lista de nombres de pila de todos los idiomas; `extra_terms`; ficticios
  estables con forma y longitud parecidas y mismo género, de `lang/<code>.yaml › capture_people`), `redact.py` (OCR
  rapidocr o tesseract; caras con el Haar de OpenCV en vez de YuNet, para no llevar un modelo en el paquete; vídeo:
  lecturas a `video_fps` y cada fotograma tapado con la lectura anterior y la siguiente, en vez de seguimiento de cajas),
  `capture redact|review|approve|reject` (adelantados del paso 4: sin ellos `redact` no sirve), `media set` rechaza
  `produced` mientras la captura espera revisión o está rechazada, denegaciones de `approve`/`reject`, extra con
  rapidocr-onnxruntime y opencv-python-headless. Falta probar a mano el OCR real y el vídeo (el test del vídeo se salta sin
  OpenCV). Apple Vision en macOS queda pendiente.
- [x] Paso 3a (sin commit todavía): `mcpserver.py` (MCP mínimo por stdio, sin dependencias), `tools/capture-dom.js`
  (probado en el Chrome de la máquina con `--dump-dom`: texto, atributos, título, shadow DOM cerrado, lo que llega después,
  campos y áreas editables difuminados sin tocar su valor, selectores, avatares), `capture_session.py` (sesión, permiso
  comprobado en cada acción, `login_url`, dominios, campos secretos, coordenadas, `pixel_check`, pasos al bloque del guion),
  `coursekit capture serve`, registro de `coursekit-capture` en los tres ficheros, herramientas permitidas al agente de
  multimedia sin interfaz, skill de `/produce-media`. El vídeo se graba en `replay` (3b), no durante la sesión: el modelo
  piensa entre acciones y el vídeo saldría con pausas. Falta probar a mano una sesión real con Playwright.
- [x] Paso 3b (sin commit todavía): `capture_replay.py` y `coursekit capture replay`: pasos del bloque a ritmo humano
  (`capture.yaml › replay`), destino por nombre primero y posición como recurso, `tools/capture-cursor.js` (probado en
  Chrome), screencast de CDP → ffmpeg (montaje probado con el ffmpeg de la máquina), tramos unidos, `pixel_check` sobre el
  vídeo. Falta probar a mano el screencast real con Playwright.
- [x] Paso 5, macOS (sin commit todavía): `capture_desktop.py` sin dependencias (ctypes sobre CoreGraphics,
  CoreFoundation y Accessibility; `screencapture -R` de la zona de la ventana con el programa al frente y las ventanas de
  otros programas encima pintadas; clics solo si bajo el puntero hay una ventana del programa; campo seguro o activo
  desconocido → no se escribe; OCR obligatorio en cada pantalla). `replay` en escritorio: posición dentro de la ventana,
  vídeo con `ffmpeg -f avfoundation` recortado a la ventana, siempre tapado sobre los píxeles o se borra. `doctor` con la
  sección Captura. Probado aquí lo que no toca la pantalla: lista de ventanas y permisos con ctypes. Las capas del sistema
  (Dock, barra de menús, superposiciones del tamaño de la pantalla) se ignoran al decidir qué hay encima. Falta probar a
  mano clics, teclado, `screencapture` y la grabación con avfoundation.
- [x] Paso 5, Windows y X11 (sin commit todavía), escritos y SIN PROBAR en máquinas reales: `capture_window.py` (lo
  común: qué se ve, qué se tapa, puntero, grabación con ffmpeg), `capture_macos.py` (antes `capture_desktop.py`),
  `capture_windows.py` (user32/dwmapi/kernel32 con ctypes, Pillow `ImageGrab`, `SendInput`, `gdigrab`; sin permisos;
  contraseña solo detectable en cuadros de edición clásicos) y `capture_x11.py` (`xdotool`, Pillow `ImageGrab`, `x11grab`;
  Wayland rechazado; no se conocen las ventanas de encima ni el campo activo). Probados solo con fakes (teclas, búsqueda de
  la ventana, lo que dice xdotool). Por corregir en las pruebas: el foco de Windows (SetForegroundWindow puede negarse),
  el escalado de pantalla en `gdigrab`, `ImageGrab` en Linux sin XCB, y la ventana bajo el puntero con distintos gestores
  de ventanas.
