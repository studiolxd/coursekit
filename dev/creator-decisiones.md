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
