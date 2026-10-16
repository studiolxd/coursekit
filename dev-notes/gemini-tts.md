# Voz de Gemini TTS: lo pendiente

Nota de desarrollo: se borra cuando lo que recoge esté hecho, validado y publicado.

## Hecho

- Proveedor `gemini` con `generateContent`, estilo en `speechMetadata.style`, modelo fijado en el curso, WAV o L16.
  Probado con clave real (octubre de 2026): `gemini-3.8-flash-tts` responde WAV a 24 kHz.
- Flex (`media.yaml › gemini.tier: flex`, por defecto): `serviceTier: "flex"` en minúsculas (`FLEX` da 400). Probado:
  Google lo sirve en flex (cabecera `X-Gemini-Service-Tier: flex`, `usageMetadata.serviceTier`). Reintentos ante 429/503
  (5, 20 y 60 s) y después nivel estándar, salvo `flex_fallback: false`.
- Batch (`coursekit tts-batch`, `--batch` en `tts`, `video voice` y `media narrate`; el handoff envía y recoge). Probado
  con clave real un trabajo de una petición: subida resumable a la Files API, `batchGenerateContent`, estado en
  `metadata.state`, resultados en `metadata.output.responsesFile` (también `response.responsesFile`), JSONL con `key` y
  `response`. Una petición tardó 3 minutos.

Falta: un curso entero en batch (varias decenas de locuciones, guiones largos en varias partes) y escuchar la calidad
del acento de España con `Aoede` en flex y en batch.

## Fase 2: diálogos con varios locutores

`speechConfig.multiSpeakerVoiceConfig.speakerVoiceConfigs` (hasta dos locutores por petición, cada uno con su
`voiceConfig`) y `speechMetadata.speaker` en cada parte. Encaja con las conversaciones de las simulaciones
(`media narrate`, `character`): una petición por escena en lugar de una por réplica, con la entonación de un diálogo real.
Decidir: qué pasa con más de dos personajes en una escena (partir la escena, o seguir una petición por réplica).
