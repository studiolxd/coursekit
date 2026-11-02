# Captura de aplicaciones reales: lo pendiente

`coursekit capture` (navegador, escritorio y terminal, escenarios, repetición, tapado de datos personales) está publicado y
documentado (`docs/*/03-commands.md › coursekit capture`, `05-agents.md › The capture MCP server`, `07-media.md`,
`04-configuration.md › capture`, `11-troubleshooting.md › Capture`). Esta nota guarda lo que falta por probar; sustituye
también a la nota del modo terminal.

## Escritorio en Windows y Linux con X11

Escrito y probado solo con dobles (teclas, búsqueda de la ventana, lo que dice xdotool), nunca en máquinas reales. Por
corregir en las pruebas:

- El foco en Windows: `SetForegroundWindow` puede negarse (`capture/windows.py` envía antes un Alt).
- El escalado de pantalla con `gdigrab` (se pide `SetProcessDpiAwarenessContext(-4)`).
- `ImageGrab` en Linux sin XCB (`capture/x11.py` no tiene alternativa).
- La ventana bajo el puntero con distintos gestores de ventanas.

## Por comprobar

- Que opencode y Codex pasen al modelo las imágenes que devuelve una herramienta MCP; si no, la captura con agente queda
  para Claude Code (`replay` y `redact` sirven en todos). La documentación ya lo avisa.
- Confirmar que están probadas a mano en macOS las partes que la nota antigua daba por pendientes (el README lo da por
  probado y la CI corre el navegador real, el OCR, las caras y el vídeo): el inicio de sesión real, el OCR y el vídeo, una
  sesión con Playwright, el screencast y clics, teclado, `screencapture` y avfoundation en el escritorio.
- Decidir si se quieren dos piezas del primer diseño que no se hicieron: una tecla para parar la sesión en el escritorio
  (`stop_key`) y un tamaño de ventana del navegador en el guion (`viewport`).

## Modo terminal

- [ ] Un handoff completo con el modo terminal en un curso real (el README lo da por demostrar).
- [ ] Que el vídeo y las imágenes se lean bien a 1920 px y con la fuente del sistema.
- [ ] Que `wait_for` baste para esperar a un modelo que tarda en contestar.
