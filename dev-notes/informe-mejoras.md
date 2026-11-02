# Informe de mejoras de coursekit

Nota de trabajo (1 de noviembre de 2026). Revisión rápida del paquete en su estado actual: `0.7.0` en
`pyproject.toml`, 80 módulos en `src/coursekit`, unos 27 000 líneas de Python, 61 ficheros de tests con
más de 700 pruebas, 9 ficheros de documentación por idioma. Las propuestas están ordenadas por lo que
más conviene atacar primero. Cada una cabe en un cambio pequeño salvo donde se indica.

Cómo se aborda, por fases y con la validación de cada una: [plan de mejoras](plan-mejoras.md).

Lo que se va haciendo se tacha y pasa a la sección [Hecho](#hecho), al final, con la fecha y cómo se resolvió.

## 1. Estructura del código

Nada pendiente: ver [Hecho](#hecho).

## 2. Calidad y pruebas

## 3. Experiencia de uso

Nada pendiente: ver [Hecho](#hecho).

## 4. Dependencias y distribución

Nada pendiente: ver [Hecho](#hecho).

## 5. Documentación

Nada pendiente: ver [Hecho](#hecho).

## Orden propuesto

Sigue las fases del [plan](plan-mejoras.md).

1. Tipar los 39 módulos de `[tool.mypy] exclude`, uno a uno (sección 2).

## Hecho

### Incoherencias visibles (arreglo inmediato)

- ~~**La versión del README no es la del paquete.**~~ Hecho el 2 de noviembre de 2026. El estado del README, los límites
  de creator y `CONTRIBUTING` ya no llevan número; solo el encabezado de cada README, y `tests/test_docs.py` comprueba
  que coincide con `pyproject.toml`.
- ~~**No hay `CHANGELOG`.**~~ Hecho el 2 de noviembre de 2026. `CHANGELOG.md` y `CHANGELOG.es.md` con todas las
  versiones y un apartado sin publicar; el estado del README en cinco bloques cortos (asentado, nuevo, en desarrollo,
  por demostrar, todavía no). `CONTRIBUTING` y `AGENTS.md` piden su línea en cada cambio, y un test comprueba que los
  dos changelogs listan las mismas versiones y la actual.
- ~~**Diferencia sin commit muy grande.**~~ Hecho el 1 de noviembre de 2026: confirmada y subida en un solo commit
  (`a813564`), sin partir por temas.

### Dependencias y diagnóstico (fase 1 del plan)

- ~~**`markitdown` es la dependencia más pesada.**~~ Hecho el 2 de noviembre de 2026: extra `docs`; la instalación base pasa de
  48 paquetes a 7. `brief` y `brand` avisan con el comando, y `doctor` lo pide solo si hay documentos que convertir.
- ~~**`doctor` no comprueba los extras.**~~ Hecho el 2 de noviembre de 2026: `coursekit/extras.py` da el comando que conserva
  los extras instalados, y todos los avisos de extras lo usan.
- ~~**`opencv-python` fijado a `<5`.**~~ Hecho el 2 de noviembre de 2026: `doctor` avisa de varios OpenCV instalados y la
  solución de problemas lo explica.
- ~~**Actualización de ejemplos de configuración.**~~ Hecho el 2 de noviembre de 2026 como `coursekit config --check` (una
  opción, porque `config` ya recibe el nombre de la configuración como primer argumento).

### Pruebas (fase 2 del plan)

- ~~**Los fixtures de proyecto se construyen a mano en cada test.**~~ Hecho el 2 de noviembre de 2026: `make_project` y
  `make_course` en `tests/conftest.py`; doce fixtures reescritos sobre ellos, con los mismos 821 tests recogidos. Al
  provocar fallos para comprobarlos salió un hueco: nada probaba que el redactor retoma una unidad a medio escribir
  (`launch.units_to_do`); ya tiene su test.

### Calidad estática (fase 3 del plan)

- ~~**Reglas de ruff que faltan.**~~ Hecho el 2 de noviembre de 2026: `SIM` (sin `SIM905`), `RET` y `PTH`. `PERF` se
  descartó: solo pedía `extend` en bucles que construyen informes de pocas líneas, a costa de leerse peor.
- ~~**Sin comprobación de tipos.**~~ Hecho el 2 de noviembre de 2026 con `mypy` en lugar de `pyright` (el paquete de
  `pyright` descarga Node en la caché del usuario): siete módulos con todas las funciones anotadas (`commands`, `config`,
  `course`, `i18n`, `paths`, `status`, `sync`), un trabajo de CI que bloquea, y `files` en `pyproject.toml` para ampliar.
  Los quince avisos que dio eran variables reutilizadas con otro tipo y funciones sin anotar; ninguno era un fallo.

### Estructura del código (fase 4 del plan)

- ~~**`commands.py` declara 38 subcomandos en un solo `register(sub)`.**~~ Hecho el 2 de noviembre de 2026: paquete
  `commands/` con un módulo por grupo (`course`, `brief`, `roles`, `media`, `assembly`, `common`), cada uno cargado solo cuando
  se ejecuta su comando; la CLI atrapa una clase base, `errors.CoursekitError`, en lugar de importar veintiún módulos para
  conocer sus errores. `openpyxl` se carga solo al escribir un Excel. La importación de la CLI pasa de unos 100 ms a 41 ms y
  `coursekit --version` de 0,20 s a 0,11 s; la ayuda de los 46 comandos es idéntica en los dos idiomas.
- ~~**Familia `capture_*`, `media*` y `video*`.**~~ Hecho el 2 de noviembre de 2026: subpaquetes `capture/`, `media/` y
  `video/`, sin alias para los nombres antiguos.
- ~~**Llamadas a programas externos repartidas.**~~ Hecho el 2 de noviembre de 2026 con alcance distinto al propuesto: los
  avisos de programa que falta ya eran coherentes y se dejan en cada módulo; `external.run` resuelve lo que sí fallaba, quince
  llamadas que leían la salida con la codificación del sistema (cp1252 en Windows).
- ~~**Peticiones HTTP sin cliente común.**~~ Hecho el 2 de noviembre de 2026: `http.py` con `request` y `download`; los
  reintentos solo donde el módulo los pide (la búsqueda web), nunca por defecto.

### Experiencia de uso (fase 5 del plan)

- ~~**`--help` largo y en dos idiomas.**~~ Hecho el 2 de noviembre de 2026: `coursekit help COMMAND` da las opciones y el
  apartado de `03-commands.md` en el idioma de la persona (el wheel lleva la referencia en `coursekit/manual/`); `--json` en
  `status`, `doctor`, `media check` y `verify`.
- ~~**Salida de `verify` sin niveles.**~~ Hecho el 2 de noviembre de 2026: nueve familias (`structure`, `words`, `style`,
  `language`, `readability`, `media`, `activities`, `simulations`, `assembly`) con `--only` e `--ignore`; una comprobación
  parcial no cambia el estado. Resumen por unidad al final. Las skills de redacción y revisión lo mencionan, sin obligar a
  usar JSON: el texto ya les sirve.

### Documentación (fase 6 del plan)

- ~~**`docs/` suma más de 6 000 líneas por idioma.**~~ Hecho el 2 de noviembre de 2026: `08-assembly.md`,
  `09-delivery.md` y `10-client-review.md`, y la resolución de problemas pasa a `11`. El banco de preguntas se queda en
  Montaje, dentro de «Dónde van las evaluaciones», porque es parte del plan de montaje; mover solo ese apartado partía en
  dos una explicación. Los enlaces se rehicieron por el fichero donde vive cada ancla.
- ~~**Las notas de `dev-notes/`.**~~ Hecho el 2 de noviembre de 2026: cada punto se comprobó contra `docs/`, el código y el
  README. Quedan `capture.md` (junta la del modo terminal), `gemini-tts.md`, `pedagogical-criteria.md` y `research.md` con
  lo pendiente y el fundamento, y `validacion-pendiente.md` con lo que solo falta probar (evaluaciones aparte, curso piloto,
  vídeos). Lo que solo estaba en las notas pasó a `docs/` antes de borrarlo: lo que el screencast no muestra, lo que no es
  texto en la página, la carpeta personal tapada en el modo terminal y `home: clean`, y `research` en los cursos
  importados. La revisión salió con una contradicción con la redacción (pasos numerados frente a carrusel), ya corregida.

### OCR y Python 3.13 y 3.14

- ~~**El extra `capture` no se instala con Python 3.13.**~~ Hecho el 2 de noviembre de 2026: `rapidocr` 3 (lleva sus modelos,
  no descarga nada) con `onnxruntime` 1.24.1 o posterior, y OpenCV headless, que `rapidocr` exige y que en Linux no necesita
  `libgl1`. Su salida da a veces una caja por palabra: `redact._rows` junta en una línea las cajas a la misma altura, para
  que un nombre repartido se siga encontrando. `requires-python` pasa a `<3.15`. Probado en macOS con 3.12 y 3.14 (no hay
  3.13 en la máquina; la CI lo cubre). Python 3.14 sacó además un fallo: su `argparse` comprueba la ayuda al declarar cada
  opción, y un `%` de un mensaje la rompía; ahora se escapa al declararla. Nuevo trabajo de CI con 3.14 y los dos extras.

### mypy en todo el paquete

- ~~**Ampliar `mypy` a más módulos.**~~ Hecho en parte el 2 de noviembre de 2026: comprueba ya todo el paquete (76 ficheros)
  salvo 39 módulos que daban más de tres avisos, en `[tool.mypy] exclude`; un módulo nuevo nace tipado. Los 50 avisos de
  los 25 módulos añadidos eran anotaciones que faltaban y valores de YAML o JSON sin tipo; ninguno era un fallo.
- ~~**Tiempo de la suite.**~~ Descartado el 2 de noviembre de 2026 con la medida: 850 tests en 5 min 18 s en macOS, con el
  extra `capture`; el más lento tarda 5 s y los 25 más lentos suman unos 50 s. El tiempo está repartido: un marcador `slow`
  ahorraría poco y dejaría tests fuera de la pasada habitual.
