# Mejoras tras un curso de prueba completo

Nota de desarrollo: se borra cuando las mejoras estén validadas y publicadas (lo que dure va a `docs/` y a los READMEs).

**Estado (18 de octubre de 2026):** en curso.

Origen: las apreciaciones de producir un curso entero con coursekit (diseño, redacción, revisión, medios). Cada punto lleva
su número de la lista original.

## Fase 1: robustez y comandos

- [x] **7. Escrituras simultáneas en `manifest.yaml`.** `media.editing_manifest()` bloquea el fichero (`media/.manifest.lock`,
  `util.file_lock`: `flock` / `msvcrt`, reentrante, dos minutos de espera) desde la lectura hasta la escritura, y escribe de forma
  atómica (`util.save_yaml_atomic`). Lo usan todos los que escriben el manifiesto: `extract`, `set`, `redo`, `stock`, `narrate`,
  `tts-batch`, `transcript`, capturas (redact, sesión, repetición, decisión). Los que tardan (narrar, descargar) releen el
  manifiesto al final y solo bloquean para escribir.
- [x] **6. `media render`.** Cada intento con un perfil de Chrome propio (dos a la vez no se pisan: el código 2), un tiempo
  límite (se mata si se cuelga), una ventana más alta que el dibujo y el PNG recortado a su tamaño exacto (la ventana sin
  interfaz pinta menos de lo que mide: el borde de abajo sin pintar). Tres intentos.
- [x] **4. PDF en `brief`.** Un enlace de `links.md` que sirve un PDF o un fichero de Office se descarga y se convierte con
  MarkItDown, como los de `sources/`. Si no tiene texto (escaneado), lo dice.
- [x] **3. Resumen de las ejecuciones headless.** El agente termina con un bloque `<summary>…</summary>`; coursekit toma el
  último de la sesión. En la revisión, si no lo hay, el resumen sale del informe.
- [x] **8.** `approve script --asset A,B,C` (o repitiendo `--asset`): una pregunta, una firma por guion, un commit.
  `media fit` y `media render` aceptan `--file` (un fichero aún no registrado, una muestra de la lámina de estilo).
- [x] **9.** La misma frase en el revisor y en `status`: se comprueba con `/approve-unit` y se firma con
  `coursekit approve content`.
- [x] **20.** `setup` avisa, como ya hacía `doctor`, cuando redactor y revisor tienen la misma herramienta y modelo.

## Fase 2: memoria del curso, normas y avisos

- [x] **2 y 16.** `courses/<CODE>/decisions.md` (plantillas en `templates/course/<idioma>/`): lo crean `new` y, en los cursos
  anteriores, `brief`. Decisiones de personas y rótulos de interfaz comprobados; el redactor y el revisor lo respetan. El
  revisor vuelve a comprobar cada pendiente contra el estado actual y `decisions.md` antes de repetirlo.
- [x] **10, 11, 12, 14, 15, 17.** Normas en los skills de redacción y revisión (solo la interfaz actual, orden único, test con
  situaciones nuevas, retroalimentación, el diseño desfasado se avisa, `media-style.md` antes de describir un recurso).
- [x] **13.** `simulation.consequence_warnings`: decisión con `error` que lleva directa a un final `good`, o que va donde una
  correcta sin puntos, cambios de estado ni feedback. Norma en los skills (consecuencia visible y continuidad).
- [x] **15.** `directives.yaml › activity_types` (tipo de actividad del diseño → directivas); `verify` avisa si la sección de
  la actividad no tiene ninguna.
- [x] **12.** `rules › content.bank_practice_overlap` (0,5): `verify` avisa de una pregunta del banco que comparte demasiadas
  palabras (Jaccard sobre los términos de pregunta y opciones) con una práctica del contenido.
- [x] **18.** `media.yaml › speakers`: `learner` y `anonymous` sin retrato (y admitidos fuera del reparto); `avatars`: una
  imagen de la marca que `media extract` toma como retrato.
- [x] **19.** El skill de medios: un icono que falta se dibuja con las reglas de la guía y se lista en el informe.
- [x] **21.** La guía cita cada línea de `notes.md` en una tabla; `mediastyle.missing_notes` avisa en `approve media-style` y
  en `media plan`; los agentes de medios leen también las notas (mandan sobre la guía).
- [x] **5.** Sin comando. Un `matrix.json` guardado de nuevo con el contenido de la última firma conserva su validación; el
  skill de diseño copia la respuesta guardada del MCP cuando la hay y no reescribe lo que no cambió.

## Pendiente

- [x] Documentación en `docs/en` y `docs/es` y los READMEs.
- [ ] Pasar la batería entera de tests (`tests/test_field_feedback.py` es nuevo) y probarlo en un curso real.

## Descartado

- Comando `coursekit decide`: basta el fichero; se añade si se echa en falta.
- Aviso de `verify` para «ya no existe», «antes se llamaba»: demasiados falsos positivos (un curso sobre un cambio de norma
  tiene que decirlo). Queda como norma de los skills.
