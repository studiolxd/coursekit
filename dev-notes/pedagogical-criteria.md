# Criterio pedagógico: lo pendiente

El ciclo de la sección expositiva, la carga cognitiva, la práctica espaciada, las ayudas de trabajo y las crucetas están
publicados y documentados (`docs/*/06-content.md › Expository courses`, `07-media.md › Job aids` e `Images with points`,
`defaults/rules.yaml`, las skills de diseño, redacción y revisión). Esta nota guarda lo que falta por validar y el
fundamento de las reglas.

## Pendiente de validar

- Un curso expositivo completo escrito y revisado con el ciclo.
- Una ayuda de trabajo subida a creator (`request_asset_upload` de tipo `attachment`) y el paquete html con una. El PDF
  con el Chrome de Windows y de Linux: solo se ha probado en macOS.
- Las crucetas en una imagen generada por API y en un fondo de simulación real.

## Abierto

- La contigüidad pedía que el recurso dijera qué parte del texto ilustra. La skill solo pide que el texto que explica un
  recurso vaya junto a él: decidir si se añade al recurso o se descarta.

## Fundamento de las reglas

Objetivo: que el diseño, la redacción y la revisión apliquen criterios con respaldo (aprendizaje de adultos, carga
cognitiva, primeros principios de instrucción, motivación) sin nombrarlos ante la persona.

- **Ciclo expositivo:** primeros principios de Merrill (problema, activación, demostración, aplicación, integración).
  Recoge la andragogía (necesidad de saber, experiencia previa, orientación a problemas), el aprendizaje significativo
  (activar lo previo), los eventos de Gagné y la relevancia de ARCS sin nombrar cinco marcos.
- **Carga cognitiva y principios multimedia:** Sweller y Mayer (segmentación, señalización, coherencia, contigüidad,
  redundancia, inversión de la pericia).
- **Motivación:** ARCS, en la revisión (relevancia y confianza del criterio 11).
- **Ya estaba antes:** Bloom revisada y alineación constructiva (diseño instruccional y criterio 2 de la revisión), cambio
  conceptual (`design/misconceptions.yaml`), aprendizaje experiencial (el ciclo de `decision_based`), feedback y
  transferencia (Gagné 7 y 9).
- **Descartado:** VARK (estilos de aprendizaje: sin respaldo empírico); los modelos de proceso (ADDIE, Dick y Carey, Kemp,
  ASSURE, SAM, Design Thinking: el flujo de coursekit ya cumple ese papel y no cambian la redacción); conectivismo y teoría
  sociocultural (poco aplicables a un paquete autoformativo). Del aprendizaje social se aprovecha solo el modelado, que ya
  permite `:::dialog`.
- Que una sección abra con un problema no lo comprueba `verify` (no hay marca mecánica fiable): lo mira la revisión.
