# Lo que necesita creator para los cursos basados en decisiones

> Notas de mantenimiento (no es documentación de usuario). Especificación de lo que coursekit necesita de creator para
> que un curso basado en decisiones (`design.approach: decision-based`, sección 11 de `plan.md`) funcione en creator
> igual que en el backend html. Describe el comportamiento que coursekit espera, no cómo debe implementarlo creator.
> Los ejemplos son del curso de prueba genérico (contraseñas seguras en una empresa ficticia, ACME).

## 0. Situación de partida

Hoy coursekit monta un curso basado en decisiones en creator así (`assemble.for_creator`, sección 11.9 de `plan.md`):

| Pieza | backend html | creator hoy |
|---|---|---|
| Simulación (`:::scenario`, `:::conversation`) | componente de la página | EMBED de un paquete propio (`SIM-<ID>`, `coursekit media embed`) |
| Estado de la simulación | se guarda en `suspend_data` y se recupera al volver | vive en el iframe mientras la página está abierta; se pierde |
| Bloque adaptativo (`:::if` / `:::else`) | muestra la rama que corresponde | solo la rama neutra (`:::else`), con aviso |
| Simulación evaluable | suma a la nota de su prueba con su peso | su puntuación no llega al SCORM |
| Interacciones (una por decisión) | `cmi.interactions` | no se registran |
| Prueba formada solo por simulaciones | se califica sola al llegar al final | no existe |
| Altura de la simulación | la de su contenido | la del iframe, fija |

El objetivo es que no haya diferencias. Lo que sigue son las piezas que faltan, de más a menos importante.

## 1. Comunicación entre un EMBED y su lección

Una simulación corre dentro de un EMBED (un iframe con el paquete que construye coursekit). Para todo lo demás (estado,
nota, bloques condicionales, altura) la simulación y la lección tienen que hablar. Propuesta: mensajes `postMessage` con
un prefijo propio, en los dos sentidos.

### 1.1 Del EMBED a la lección

Todos llevan `source: "coursekit"`, `version: 1` y el `id` de la simulación (único en el curso: `[a-z][a-z0-9_]*`).

| Mensaje | Cuándo | Datos |
|---|---|---|
| `ck:ready` | el EMBED ha cargado y espera su estado | `{ id }` |
| `ck:state` | después de cada decisión y al llegar a un final | `{ id, at, env, score, done, ending }` |
| `ck:result` | al llegar a un final | `{ id, score, max_score, grade, ending, kind }` |
| `ck:interaction` | después de cada decisión | `{ id, n, type, response, result, weighting }` |
| `ck:resize` | cuando cambia la altura de su contenido | `{ id, height }` (px) |

Ejemplo de `ck:state` y `ck:result` de la simulación evaluable de la unidad 2 del curso de prueba:

```json
{"source": "coursekit", "version": 1, "type": "ck:state", "id": "sim_u2_eval_lunes",
 "at": "fin_bueno", "env": {"avisado": true, "clic": false, "denegado": true, "verificado": true},
 "score": 8, "done": true, "ending": "fin_bueno"}

{"source": "coursekit", "version": 1, "type": "ck:result", "id": "sim_u2_eval_lunes",
 "score": 8, "max_score": 8, "grade": 100, "ending": "fin_bueno", "kind": "good"}
```

- `env`: las variables de la simulación (números o booleanos), las que leen los bloques condicionales.
- `grade`: 0–100, puntos del camino sobre el máximo alcanzable (lo calcula la simulación; creator no necesita saber
  cómo).
- `kind`: `good`, `mixed` o `bad`.
- `ck:interaction`: `type: "choice"`; `response`, el texto de la decisión (máx. 250 caracteres); `result`, `correct`,
  `incorrect` o `neutral`; `weighting`, los puntos en valor absoluto (1 si 0). `n` numera las decisiones del intento.

### 1.2 De la lección al EMBED

| Mensaje | Cuándo | Datos |
|---|---|---|
| `ck:restore` | respuesta a `ck:ready`: el estado guardado, si lo hay | `{ id, state }` (lo último recibido en `ck:state`, o `null`) |
| `ck:reset` | la prueba abre un intento nuevo (sección 4) | `{ id }` |

### 1.3 Requisitos

- La lección acepta solo mensajes de los EMBED que ella misma contiene (comprueba `event.source` contra sus iframes y el
  origen de los ficheros subidos) y con `source: "coursekit"`.
- Un EMBED sin estos mensajes (una demo de terminal, una animación) sigue funcionando como hoy.
- La vista compartida o de revisión no puede bloquear el iframe (hoy `X-Frame-Options: DENY` lo deja en blanco).

## 2. Estado y persistencia

- La lección guarda, por simulación, lo último recibido en `ck:state`, y lo devuelve en `ck:restore` cuando la
  simulación vuelve a cargar (al cambiar de lección o al reabrir el contenido).
- Persiste en `suspend_data` junto al resto del estado del contenido. Presupuesto: SCORM 1.2 admite 4.096 caracteres
  para todo; coursekit ya manda solo lo mínimo (`at`, `env`, `score`, `done`) y el html lo guarda así:
  `{"s": {"<id>": {"a": "<escena>", "e": {…}, "s": 8, "d": 1}}}`. Una simulación típica ocupa 60–120 caracteres.
- Si no cabe, se prioriza el estado de las simulaciones evaluables y de las que leen los bloques condicionales.

## 3. Bloques condicionales

Contenido que cambia según lo que el alumno decidió en una simulación anterior:

```markdown
:::if sim_u1_cuenta_nueva.reused
Le hiciste caso a Ramón y reutilizaste la contraseña de siempre. Veamos qué la hace previsible.
:::else
Tanto si elegiste una frase larga como si no, la pregunta es la misma: ¿qué hace previsible una contraseña?
:::
```

### 3.1 Brick

Propuesta: un brick contenedor `CONDITIONAL` con:

- `condition`: texto con la condición (3.2);
- dos ramas, `then` y `else`, cada una con sus bricks hijos (texto, tabs, preguntas, imágenes…; cualquier brick salvo
  otro `CONDITIONAL`).

La alternativa (una condición en cada brick suelto) obliga a repetir la condición y complica el editor; el contenedor
es lo que ya genera el plan de coursekit (`{"type": "CONDITIONAL", "data": {"condition", "then", "else"}}`).

### 3.2 Condiciones

La misma sintaxis en todos los idiomas, la de `coursekit/simulation.py` y `player/expr.js` (se pueden reutilizar):

```
condición  := o
o          := y ( "||" y )*
y          := no ( "&&" no )*
no         := "!" no | comparación
comparación:= suma ( ("==" | "!=" | "<" | "<=" | ">" | ">=") suma )?
suma       := unario ( ("+" | "-") unario )*
unario     := "-" unario | "(" o ")" | número | "true" | "false" | variable
variable   := id "." nombre        (p. ej. sim_u1_cuenta_nueva.reused)
```

### 3.3 Qué rama se ve

- La rama `then` solo cuando **todas** las simulaciones que lee la condición han llegado a un final (`done`) y la
  condición se cumple con sus variables.
- En cualquier otro caso, la rama `else` (la neutra): quien aún no ha jugado, quien no cumple la condición, y si algo
  falla al evaluarla.
- Se reevalúa cada vez que llega un `ck:state` y al entrar en la lección.
- En el editor y en la vista previa de edición se ven las dos ramas, marcadas.

## 4. Nota y seguimiento SCORM

### 4.1 Propiedades del EMBED de una simulación

| Propiedad | Valor |
|---|---|
| `simulationId` | el `id` de la simulación (para casar los mensajes) |
| `scored` | si cuenta para la nota |
| `weight` | su peso entre las evaluables (por defecto 1) |

### 4.2 Cómo cuenta

Igual que en el backend html (`player/entry.js`):

- **En una lección de evaluación:** la nota de la prueba combina sus preguntas y sus simulaciones evaluables. Cada
  pregunta pesa 1 (vale 1 si es correcta); cada simulación pesa `weight` y vale `weight × grade / 100`.
  `nota = 100 × (aciertos + Σ peso·nota/100) / (preguntas + Σ pesos)`, redondeada.
- La prueba no se puede enviar hasta que sus simulaciones evaluables han llegado a un final.
- **Prueba formada solo por simulaciones:** sin botón de enviar. Se califica al recibir el `ck:result` de la última que
  faltaba; si quedan intentos y la simulación vuelve a empezar (un nuevo `ck:state` sin `done`), es un intento nuevo;
  sin intentos, se puede jugar sin nota.
- **Simulaciones evaluables fuera de una prueba,** en una unidad sin prueba: la nota de la unidad es la media ponderada
  de sus notas cuando todas han terminado.
- **Interacciones:** cada `ck:interaction` se registra en `cmi.interactions` (`id`: `<simulación>-<n>`), con el
  contador de interacciones del contenido.
- Aprobado y número de intentos: los del ajuste de la prueba (los que coursekit ya pasa con `update_quiz_settings`).

## 5. Altura del EMBED

Una simulación cambia de altura según la escena (un chat que crece, un final con debriefing). El EMBED ajusta su altura
a lo que diga `ck:resize`, con un mínimo razonable y sin barra de desplazamiento propia.

## 6. MCP

Lo que el agente de montaje necesita hacer por MCP:

- Crear un EMBED de simulación a partir de un paquete subido (`request_embed_upload` ya existe) con las propiedades de
  4.1.
- Crear y actualizar un brick `CONDITIONAL` con su condición y los bricks de sus dos ramas.
- Marcar una prueba como «solo simulaciones» (o que creator lo deduzca de su contenido).
- Que `list_brick_types` incluya `CONDITIONAL` y las propiedades nuevas del EMBED, para que
  `coursekit directives check` lo detecte.

## 7. Qué cambia en coursekit cuando exista

- `htmlkit/simpackage.py`: el paquete de la simulación sustituye su seguimiento en memoria por el puente de mensajes
  (sección 1), con el mismo motor (`player/simulation.js`).
- `assemble.for_creator`: deja de montar la rama neutra y genera el `CONDITIONAL`; el EMBED lleva `simulationId`,
  `scored` y `weight`.
- `coursekit verify`: deja de avisar de que creator no adapta el contenido.
- Skill `creator-assembly` y documentación (`08-assembly-and-delivery`, `06-content`).

## 8. Criterios de aceptación

Con el curso de prueba montado en creator:

1. En la unidad 1, quien reutiliza la contraseña en la simulación del apartado 2 lee la rama `then` del bloque que la
   sigue; quien no, la neutra; quien no ha jugado, la neutra.
2. Al salir del contenido y volver, cada simulación está donde se dejó y los bloques condicionales siguen igual.
3. La prueba de la unidad 2 formada por la simulación evaluable se califica sola al llegar al final, sin botón, y cuenta
   los intentos; la nota del SCORM coincide con la del backend html para el mismo camino.
4. Cada decisión aparece en `cmi.interactions` con su texto, su resultado y su peso.
5. Las simulaciones se ven enteras, sin barras de desplazamiento, en la vista del alumno y en la compartida.

## 9. Respuestas a las preguntas de creator

**¿Qué es una unidad al montar en creator?** Un contenido. Cada unidad del curso es su propio contenido de creator y su
propio paquete SCORM (`units[].content_id` en `course.yaml`); sus apartados son las lecciones de ese contenido. La nota
de la unidad es la nota del contenido. No hay nota de curso: si hace falta, la combina el LMS a partir de las de cada
paquete.

**¿Identificador corto más descripción en las interacciones?** Sí. La respuesta es la letra de la opción elegida entre
las de su escena (`a`, `b`…, por su orden en el YAML: primero `choices`, después `hotspots`), que es lo que admite SCORM
para una `choice` (en 1.2, un carácter; en 2004, identificadores sin espacios), y el texto va en la descripción. Es lo
que ya manda el backend html. La interacción queda así:

| Campo | Valor |
|---|---|
| `id` | `<simulación>-<n>` (`n`, el número de la decisión en el intento) |
| `type` | `choice` |
| `learner_response` | la letra de la opción elegida |
| `description` | el texto de la decisión (máx. 250 caracteres) |
| `result` | `correct`, `incorrect` (`wrong` en SCORM 1.2) o `neutral` |
| `weighting` | los puntos en valor absoluto (1 si 0) |

`ck:interaction` lleva entonces `response` (la letra) y `description` (el texto); sustituye a la definición de 1.1.

**¿Ramas guardadas en plano dentro del `CONDITIONAL`?** Sí, la representación interna es cosa de creator, con tres
condiciones: el MCP acepta y devuelve la forma anidada `{condition, then: [...], else: [...]}`; el orden de los bricks
de cada rama se conserva; y los ids de los bricks hijos son estables entre lecturas (el montaje compara lo que hay con lo
que quiere y solo cambia lo distinto).

**Pesos: ¿cuál manda si una pregunta tiene peso distinto de 1?** El de creator. coursekit no da peso a las preguntas
(todas pesan 1); si el ajuste de una pregunta en creator tiene otro peso, ese es el que cuenta en la fórmula de 4.2 (en
lugar del 1 de la pregunta). El de una simulación es el `weight` de su EMBED. Mientras creator no exponga el peso por
MCP, coursekit no lo toca.

**¿Basta con guardar el estado solo en SCORM?** Sí. `suspend_data` es la única persistencia, como en el backend html,
con el presupuesto de 2 (4.096 caracteres en SCORM 1.2). Sin almacenamiento propio de creator; en la vista previa de
creator (sin LMS) basta con que el estado dure lo que la sesión.

## 10. Respuesta de creator y lo que cambia

Creator ha respondido a la sección 9. Lo que acuerda, y qué hace coursekit con cada punto:

| # | Creator | coursekit |
|---|---|---|
| 1 | El EMBED y la lección hablan con un **protocolo propio de creator**, versionado, para cualquier paquete subido (también para bloquear el avance hasta que el paquete diga que ha terminado). Sustituye a los `ck:*` de la sección 1; pasarán el contrato. | La sección 1 queda como la lista de lo que el protocolo debe cubrir (preparado, estado, resultado, interacción, altura, restaurar, reiniciar). `htmlkit/simpackage.py` hablará ese protocolo cuando llegue el contrato. Pendiente. |
| 2 | Cada paquete declara en un **manifiesto** la versión del protocolo y lo que sabe hacer (avisar de que ha terminado, nota, estado); el MCP lo lee al subirlo y avisa si se le pide al EMBED algo que el paquete no declara. | `simpackage.py` escribirá el manifiesto; una simulación declara terminar, nota (solo si es evaluable), estado e interacciones. Pendiente del contrato. |
| 3 | Solo paquetes subidos: se ignoran los mensajes de un EMBED con URL externa. | Sin cambios: coursekit siempre sube el paquete (`coursekit media embed`). |
| 4 | Las condiciones solo leen simulaciones **del mismo contenido**; el `simulationId` basta con que sea único en el contenido y el MCP lo comprueba. | Hecho, y para los dos backends (en html cada unidad también es su propio SCORM): `verify` da error si un `:::if` lee una simulación de otra unidad. Los ids siguen siendo únicos en todo el curso (más estricto, compatible). |
| 5 | Id de las interacciones: `<simulación>-<intento>-<n>`. | Hecho también en el backend html: cada vuelta al principio es un intento nuevo, y el contador de decisiones se guarda, así que un id no se repite ni al reanudar. |
| 6 | SCORM 1.2 no tiene `description`: el texto de la decisión solo en 2004; en 1.2 queda el id de la opción. El vocabulario es `correct`, `incorrect`, `neutral`, y creator lo traduce a cada versión. | Ya es así: coursekit manda la letra de la opción y el texto como descripción; el backend html traduce igual (`wrong` en 1.2). |
| 7 | Simulaciones evaluables sueltas en un contenido con pruebas: proponen que **no cuenten**; la nota sale de las pruebas. | **Sí, nos vale**: es lo que ya hace el backend html. `verify` avisa de una simulación evaluable en el contenido de una unidad con prueba (que la mueva a `assessment.md` o quite `scored`). |
| 8 | En la forma anidada del `CONDITIONAL` cada brick hijo lleva su id: con id se actualiza, sin id se crea, y `get_lesson` devuelve la misma forma. | De acuerdo. `assemble applied` guardará los ids de los hijos de cada rama y `diff` los comparará como los de la lección. Pendiente del brick. |
| 9 | Calendario: primero el protocolo con «he terminado», el bloqueo del avance y la altura; después estado, nota e interacciones; lo último, el `CONDITIONAL`. Hasta entonces, la rama neutra. | Seguimos montando la rama neutra. En coursekit, por el mismo orden: (1) protocolo, manifiesto y «terminado» en `simpackage.py` y `for_creator`; (2) estado, nota e interacciones; (3) `CONDITIONAL` en el plan, `diff` y `applied`. |

## 11. Fase 1 del protocolo de creator (contrato del 2026-10-13), aplicada

Creator ha publicado el contrato `slxd-embed`, versión 1 (manifiesto `slxd-embed.json` en la raíz del paquete; mensajes
`{channel: "slxd-embed", version: 1, type}` con `postMessage(…, "*")` desde un iframe sin `allow-same-origin`; en esta
fase atiende `complete` y `resize`, y `ready` no hace nada aún). Lo que hace coursekit (`htmlkit/embedbridge.py`):

| Paquete | Manifiesto | Mensajes |
|---|---|---|
| Simulación (`SIM-<ID>`, `simpackage.py`) | `complete`, `resize` | `ready` al cargar; `resize` con el alto del contenido cada vez que cambia; `complete` una vez, cuando la simulación llega a un final |
| SVG envuelto (`coursekit media embed`) | `resize` | `ready` y `resize` |

- El paquete no usa almacenamiento (el iframe tiene origen opaco): el estado sigue en memoria mientras la página está abierta.
- Las skills suben `slxd-embed.json` con el resto de la carpeta antes de escribirla en el brick, nunca mandan
  `embedPackage` y, tras `add_brick`, comprueban en `get_lesson` que creator lo ha rellenado.
- No se declaran aún `state`, `result` ni `interaction` (reservadas): se añadirán cuando creator las atienda (fase 2),
  junto con `restore` y `reset` y la nota en SCORM.
- Bloqueo: apagado por defecto en creator (decisión del 2026-10-13). En un curso basado en decisiones, el montaje lo
  activa (`blocker_enabled: true`) en el EMBED de la simulación que abre cada apartado de contenido; las demás no bloquean.

## 12. Fase 2 del protocolo (simulaciones: estado, nota y decisiones), aplicada

Contrato de creator del 2026-10-13, fase 2. Lo que hace coursekit (`player/embedsim.js`, `simpackage.py`, `for_creator`):

| Creator pide | coursekit |
|---|---|
| Manifiesto con `state`, `result`, `interaction` | El paquete de una simulación declara `complete`, `resize`, `state`, `result` e `interaction`. |
| `ready` → `restore` | Al cargar espera `restore` (1,5 s; sin lección que conteste, empieza de cero) y arranca donde estaba. |
| `state` (objeto plano ≤ 1.024 caracteres, `done`) | Después de cada paso: `{a: escena, e: variables, s: puntos, d: 0/1, t: intento, n: decisiones}`. |
| `result` (score, maxScore, grade, ending, kind) | Al llegar a un final, antes de cerrar; `ending` normalizado a `[a-z][a-z0-9_]*` (los ids de escena admiten `-`). |
| Cierre (D5): `complete` o `state` con `done` | Orden al final: `result` → `state` con `done` → `complete`. |
| `interaction` (attempt, n, response, description, result, weighting) | Tras cada decisión; `response` = la letra de la opción en su escena (`a`, `b`…, como pide SCORM 1.2 para una `choice`). |
| `reset` | Vuelve a empezar con otro intento (las interacciones no repiten id). |
| Propiedades del brick `simulationId`, `scored`, `weight` | El plan de montaje las pone en el EMBED de cada simulación. |
| Bloqueo solo con `complete` (D1) | Sin cambios: el montaje lo activa en la simulación que abre cada apartado de un curso basado en decisiones. |

- Un EMBED escrito antes de la fase 2 conserva solo `complete` y `resize`: hay que volver a construir el paquete,
  subirlo y escribir de nuevo su carpeta en el brick (la skill de montaje lo dice).
- Probado en Chrome con una lección simulada en un iframe `sandbox="allow-scripts"`: decisiones, nota al final, reanudar
  con `restore` y `reset` con un intento nuevo.
- Pendiente (fase 3): `CONDITIONAL`. Hasta entonces se sigue montando la rama neutra.

## 13. Adelanto del contrato de los bloques condicionales (fase 3), aplicado

| Creator | coursekit |
|---|---|
| Varias ramas: `if` / `elseif`… / `else`, hasta 10 con condición más la neutra; se ve la primera que se cumple, y la neutra si ninguna, si la simulación no ha terminado o si falla la evaluación | `:::elif` en el formato; el plan usa siempre la forma general; el reproductor html muestra la primera rama que se cumple. |
| Forma por MCP: `{branches: [{condition, bricks}], else}` (también la corta `{condition, then, else}`); `get_lesson` devuelve siempre la general | El plan genera la general en los dos backends (`assemble.branch_bricks`, `conditions`); en creator se sigue montando la rama neutra hasta la fase en la que el alumno vea el bloque. |
| Textos entre comillas, solo con `==` y `!=` | En `simulation.py` y `player/expr.js`, con el mismo error si se usan de otro modo; un test comprueba que los dos evalúan igual. |
| Variables: `state.vars` y, del último `result`, `grade`, `score`, `maxScore`, `ending`, `kind`; esos cinco nombres son reservados | El paquete EMBED manda sus variables en `state.vars`; `verify` rechaza esos nombres en `state` y acepta `id.grade`… en las condiciones; el reproductor html y `assemble check` los calculan igual. |
| Límites: 500 caracteres por condición, 8 simulaciones por bloque, un nivel, no leer una simulación de dentro, ninguna evaluable dentro | Errores de `verify`. |
| Nunca en pruebas ni bancos | Error de `verify` si hay un bloque en `assessment.md`. |
| Ids estables en los bricks de cada rama | Pendiente de la fase en que se monte el bloque: `applied` guardará los ids de cada rama. |
| Calendario: montar por MCP → el alumno lo ve → editor | Seguimos con la rama neutra hasta la segunda. |

