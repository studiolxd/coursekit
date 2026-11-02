# Revisión del cliente

Opcional: el cliente revisa el curso montado y lo comenta antes de la entrega. Que sea obligatoria es un ajuste, `client_review.required` de la configuración de entrega (por defecto `false`; por proyecto en `config/delivery.yaml`, por curso en `course.yaml › delivery › client_review`: mira [04-configuration.md](04-configuration.md#delivery-exportación-scorm-y-revisión-del-cliente)). El proceso y sus estados están en [02-workflow.md](02-workflow.md#revisión-del-cliente-opcional).

Con el backend html no hay enlaces de plataforma que crear ni anotar: la persona aloja el paquete (el zip en un LMS de pruebas, o la carpeta de vista previa en un servidor web) y da el enlace al abrir la ronda: `coursekit client PWD send --where URL`. Las rondas, `changes`, `approve` y `skip` funcionan como se describe más abajo; para aplicar los comentarios del cliente, edita el `.md`, ejecuta `coursekit verify` y vuelve a construir (`coursekit assemble build`), y después aloja el paquete nuevo.

## Los enlaces de cada unidad

Este apartado trata del backend creator. Al final de `/assemble`, el agente de montaje crea para cada unidad (cada una es un contenido propio de creator) dos enlaces y los anota con `coursekit assemble link`:

| Enlace | Herramienta de creator | Para quién |
|---|---|---|
| Vista previa en vivo (`links.preview`) | `share_content` (activado, con actualizaciones en vivo) | El equipo. Muestra el contenido tal como está, sin comentarios |
| Revisión (`links.review`) | `enable_review` (sin contraseña salvo que la pidas) | El cliente. Publica la versión `v1` de la revisión y deja que el cliente comente sin cuenta. `get_review` la vuelve a leer |

```bash
coursekit assemble link PWD --unit 1 --preview https://acme.example.com/p/abc --review https://acme.example.com/r/xyz
# unidad 1 -> preview https://acme.example.com/p/abc; enlace de revisión https://acme.example.com/r/xyz
```

## Rondas

Una ronda es el ciclo «se envía al cliente, el cliente responde». Solo una persona ejecuta `coursekit client`; a los agentes se les deniega.

```bash
coursekit client PWD send --to "equipo de formación de ACME"     # ronda 1: el curso pasa a client_review
```

`send` necesita el curso en `assembly`, ninguna ronda abierta y los enlaces de revisión de las unidades anotados (o un solo enlace dado con `--where URL`, que los sustituye). Anota en `course.yaml › client_review` el número de ronda, quién la envió y cuándo, `--to` y los enlaces. Los enlaces se los envías tú al cliente.

Mientras el cliente comenta, el agente de montaje trata los comentarios con `/client-feedback PWD` (o `/client-feedback PWD 2` para una sola unidad). Usa la skill `client-review` y estas herramientas de creator:

| Paso | Herramienta de creator |
|---|---|
| Leer el estado y los hilos pendientes | `get_review`, `list_review_comments` (estado `pending`; `since` para leer solo lo nuevo). Cada hilo indica la lección, el texto y, si lo hay, una captura de pantalla |
| Aplicar lo acordado | edita el `.md` (nunca creator), `coursekit verify`, y después `assemble plan`, `diff` y aplicar como en [el flujo de montaje](08-assembly.md#el-flujo-de-montaje) |
| Publicar lo que cambió | `publish_review_version` con una etiqueta (`v1.1`, `v1.2`...). Solo la última versión admite comentarios |
| Responder | `reply_review_comment` en cada hilo y después `set_review_comment_status` con `resolved`. `verified` lo marca el cliente |

Antes de cambiar nada, el agente te muestra una tabla con cada comentario, el apartado al que se refiere y lo que propone (aplicar, no aplicar y por qué, o te lo deja a ti), y espera tu decisión; sin interfaz, aplica solo correcciones de texto claras que encajen con el diseño. Un comentario que cambia objetivos, horas, actividades o estructura es un cambio de diseño (`/design-change`), no una edición de contenido. Una unidad editada después de su firma vuelve a `verified` y necesita nueva revisión con IA y nueva firma.

Después cierras la ronda:

| Comando | Cuándo |
|---|---|
| `coursekit client PWD changes --note "..."` | El cliente quiere cambios. La ronda se cierra (resultado `changes`) y el curso vuelve a `assembly`. Aplica, vuelve a montar y ejecuta `send` otra vez: es la ronda 2 |
| `coursekit client PWD approve --by "Nombre" --note "..."` | El cliente está conforme. La ronda se cierra (resultado `approved`) con el nombre del cliente y la fecha, y el curso se puede entregar |
| `coursekit client PWD skip --reason "..."` | Entregas sin la aprobación del cliente. Anota una ronda con resultado `skipped` y el motivo; necesita el curso en `assembly` o `client_review` sin ronda abierta |

Al cerrar una ronda, el agente puede exportar los comentarios de la ronda con `export_review_comments`: devuelve un CSV mediante un enlace firmado válido durante 24 horas, y el fichero se guarda como `.cache/client-review/PWD-round-N.csv`, que git ignora y `coursekit publish` nunca copia. El CSV contiene los correos de los invitados que comentaron: no lo pegues en ningún sitio ni lo muevas al curso.

`coursekit status PWD` muestra la última ronda y su resultado (`abierta`, `pidió cambios`, `aprobada` u `omitida`), y el siguiente paso en `client_review` es anotar la respuesta del cliente.

Siguiente: [Resolución de problemas](11-troubleshooting.md)
