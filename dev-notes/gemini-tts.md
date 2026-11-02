# Voz de Gemini TTS: lo pendiente

El proveedor `gemini`, el nivel `flex` y el batch por curso están publicados y documentados (`docs/*/07-media.md › The
Gemini voice` y `The batch of the Gemini voice`, `03-commands.md › coursekit tts-batch`).

## Por validar

- Un curso entero en batch (varias decenas de locuciones, guiones largos en varias partes).
- Escuchar la calidad del acento de España con `Aoede` en flex y en batch.

Registro de la prueba con clave real (octubre de 2026): `gemini-3.8-flash-tts` responde WAV a 24 kHz; una petición tardó
3 minutos; `serviceTier` va en minúsculas (`FLEX` da 400).

## Fase 2: diálogos con varios locutores

`speechConfig.multiSpeakerVoiceConfig.speakerVoiceConfigs` (hasta dos locutores por petición, cada uno con su
`voiceConfig`) y `speechMetadata.speaker` en cada parte. Encaja con las conversaciones de las simulaciones
(`media narrate`, `character`): una petición por escena en lugar de una por réplica, con la entonación de un diálogo real.
Decidir: qué pasa con más de dos personajes en una escena (partir la escena, o seguir una petición por réplica).
