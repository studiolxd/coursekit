# Evaluaciones: dentro de cada unidad o aparte, y en bancos de preguntas

Nota de trabajo de la funcionalidad en curso. Se borra cuando esté validada y publicada (lo que dure va a `docs/` y a los READMEs).

## Decisiones

- `delivery › assessment › placement`: `unit` (por defecto, como hasta ahora) o `separate`: todas las evaluaciones del curso van en un
  paquete propio después de las unidades (una «unidad de paquete» más, la N+1, titulada con `assessment_unit_title` del idioma).
- `delivery › assessment › format`: `platform` (por defecto: lecciones de evaluación en creator o en el paquete html), `aiken`, `gift`,
  `moodle-xml`: los cuestionarios salen de los paquetes como banco de preguntas para importar en el LMS; las simulaciones puntuables
  siguen en un paquete (el de su unidad o el de evaluación).
- Un curso cambia los dos en `course.yaml › delivery › assessment`.
- Las evaluaciones se siguen escribiendo en el `assessment.md` de cada unidad (la redacción, la revisión y `verify` no cambian de
  sitio). Solo el montaje y la entrega las mueven.
- La unidad de paquete de evaluación no está en `course.yaml › units`: la construye `course.assessment_unit()` y su `content_id` y sus
  enlaces van en `course.yaml › assessment_unit`. `course.package_units()` = unidades + esa, para el montaje y la entrega.
- Con `separate`, los paquetes de las unidades informan del avance (`lessonProgress`) y el de evaluación de la nota (`quiz`): el plan
  lo dice en `score_source`.
- Tipos de pregunta por formato: aiken solo `single-choice`; gift y moodle-xml `single-choice`, `multi-select`, `true-false`,
  `match`, `sorting-groups` (como emparejamiento), `short-answer`, `fill-in-the-blank` (gift: un hueco; moodle-xml: cloze con
  varios). `sorting` y `order-words` no se exportan. `verify` da error si `assessment.md` usa otro tipo con un formato de banco.
- Ficheros: gift y moodle-xml, uno por curso con una categoría por actividad; aiken, uno por actividad (no tiene categorías).
  `coursekit delivery questions CODE --version X.Y` los escribe en `delivery/` y los registra en `deliveries` (`kind: questions`).
  El curso pasa a `delivered` cuando están todos los paquetes y, si hay banco, el banco de esa versión.

## Pendiente de validar

- Montaje real en creator con `separate` (un contenido de evaluación creado con `create_content`, y borrar las lecciones de evaluación
  que `design_matrix_generate_course` crea en cada unidad).
- Importación real de los tres formatos en un Moodle.
