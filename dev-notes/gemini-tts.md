# Voz de Gemini TTS: lo pendiente

Nota de desarrollo: se borra cuando lo que recoge esté hecho, validado y publicado.

## Hecho (fase 1)

- Proveedor `gemini` (`GEMINI_API_KEY`, `GEMINI_TTS_VOICE`, voz por defecto `Aoede`), llamada síncrona a
  `models/<modelo>:generateContent` de la Gemini API.
- Ajustes en `media.yaml › gemini` (`model`, `style`, `chunk_bytes`); un curso los cambia en `course.yaml › media › gemini`.
  `voice set CODE gemini` fija el modelo en `course.yaml › media.voice.model`.
- El estilo va en `speechMetadata.style` de cada parte (los modelos 3.8 leen el texto tal cual; el 3.1 preview esperaba las
  indicaciones dentro del texto, así que con él el estilo puede no aplicarse).
- Audio: los 3.8 devuelven WAV por defecto; los anteriores, L16 sin cabecera. `gemini_audio` acepta los dos.
- Azure (`raw-24khz-16bit-mono-pcm`), Google (`LINEAR16`) y Gemini piden audio sin comprimir: los fragmentos se unen como
  muestras y se codifican a MP3 una sola vez (`encode_pcm`). `concat_mp3` ya no existe.

Falta: probarlo con una clave real (los tests simulan la API). Comprobar en concreto que `speechMetadata` y `languageCode`
se aceptan en `generateContent` con los 3.8, que el WAV llega a 24 kHz y la calidad del acento de España con `Aoede`.

## Fase 2: diálogos con varios locutores

`speechConfig.multiSpeakerVoiceConfig.speakerVoiceConfigs` (hasta dos locutores por petición, cada uno con su
`voiceConfig`) y `speechMetadata.speaker` en cada parte. Encaja con las conversaciones de las simulaciones
(`media narrate`, `character`): una petición por escena en lugar de una por réplica, con la entonación de un diálogo real.
Decidir: qué pasa con más de dos personajes en una escena (partir la escena, o seguir una petición por réplica).

## Fase 2: modo batch (el 50 % del precio)

### Lo que dice la documentación (octubre de 2026)

- `gemini-3.8-flash-tts` y `gemini-3.8-flash-lite-tts` admiten Batch API (ficha de cada modelo). El batch solo existe con
  `generateContent`, no con la API de interacciones.
- Precio por millón de tokens, texto / audio (25 tokens por segundo de audio):

  | Modelo | Normal | Batch |
  |---|---|---|
  | 3.8 Flash TTS, hasta el 31-12-2026 | 0,50 / 9 $ | 0,25 / 4,50 $ |
  | 3.8 Flash TTS, desde el 1-1-2027 | 1 / 18 $ | 0,50 / 9 $ |
  | 3.8 Flash-Lite TTS, hasta el 31-12-2026 | 0,50 / 6 $ | 0,25 / 3 $ |
  | 3.8 Flash-Lite TTS, desde el 1-1-2027 | 1 / 12 $ | 0,50 / 6 $ |
  | 3.1 Flash TTS preview | 1 / 20 $ | 0,50 / 10 $ |

  Una hora de audio son 90.000 tokens: 3.8 Flash TTS sale a ~0,81 $/h normal y ~0,41 $/h en batch (el doble desde 2027).
- Sin nivel gratuito en batch. En el nivel gratuito normal, Google usa el contenido para mejorar sus productos; en el de pago, no.
- Peticiones en línea (menos de 20 MB en total) o un fichero JSONL subido a la Files API (hasta 2 GB), una línea por
  petición: `{"key": "...", "request": <GenerateContentRequest>}`.
- Crear: `POST v1beta/models/<modelo>:batchGenerateContent` con `{"batch": {"display_name", "input_config": {...}}}`.
  Devuelve `batches/<id>`. Crear no es idempotente: reenviar crea otro trabajo (y se paga dos veces).
- Estado: `GET v1beta/batches/<id>` → `BATCH_STATE_PENDING | RUNNING | SUCCEEDED | FAILED | CANCELLED | EXPIRED`,
  con `batchStats` (`requestCount`, `successfulRequestCount`, `failedRequestCount`, `pendingRequestCount`).
- Plazo objetivo de 24 h; a las 48 h sin terminar pasa a `EXPIRED` sin resultados. Los resultados se guardan 6 semanas.
- Resultados: `inlinedResponses` (en el orden de entrada) o `responsesFile`, que se descarga con
  `GET download/v1beta/<fichero>:download?alt=media` (JSONL: una respuesta o un error por línea, con su `key`).
- Existe también "Flex" (`serviceTier: flex`, el 50 % también, síncrono, de 1 a 15 minutos, puede responder 429/503). La
  ficha de 3.8 Flash TTS dice que lo admite, pero la página de Flex no lista modelos TTS. Probarlo: si funciona, es la
  forma más simple de pagar la mitad, porque no cambia el flujo (una opción `tier: flex` en `media.yaml › gemini`).

### Por qué no es una opción más de `coursekit tts`

`tts` y `media narrate` devuelven el audio al momento, y el agente sigue con él (subtítulos, montaje del vídeo). Con batch
el audio llega horas después, así que el flujo se parte en dos: enviar y recoger. El tamaño también obliga: una hora de
audio en PCM son ~170 MB (más en base64), así que los resultados de un curso entero no caben en una respuesta en línea:
hace falta el fichero de resultados.

### Propuesta

Una cola de locuciones por curso, `courses/<CODE>/media/tts-batch.yaml` (versionada: lo que se envió, con qué modelo, voz
y estilo, y su estado):

```yaml
job: batches/123456789          # vacío hasta que se envía
model: gemini-3.8-flash-tts
state: pending                   # queued | pending | running | succeeded | failed | expired | collected
items:
  - key: U1-S2-M1#0              # recurso#fragmento: un guion largo son varias peticiones
    asset: U1-S2-M1
    script: media/scripts/U1-S2-M1.md
    out: media/files/U1-S2-M1.mp3
    fingerprint: <sha del texto + voz + estilo + modelo>
```

Comandos (nombres por decidir):

- `coursekit tts --course PWD --in … --out … --batch`: en lugar de sintetizar, añade el guion a la cola.
- `coursekit media narrate PWD --batch`: añade a la cola las escenas pendientes.
- `coursekit tts batch send PWD`: sube el JSONL y crea el trabajo; se niega si ya hay uno en curso (no idempotente).
- `coursekit tts batch status PWD`: estado y `batchStats`.
- `coursekit tts batch collect PWD`: descarga los resultados, une los fragmentos de cada recurso (`encode_pcm`), escribe
  los MP3, marca los recursos como producidos y deja en la cola los que fallaron para reenviarlos.

Los recursos en cola tendrían un estado propio en el manifiesto (p. ej. `voicing`) para que `media plan`, `status` y el
handoff no los den por pendientes ni por producidos.

### Decisiones abiertas

1. Qué entra en la cola: solo `media narrate` (escenas de simulaciones), también los guiones de audio y vídeo de
   `coursekit tts`, y las escenas de los montajes de `coursekit video` (que hoy sintetizan dentro de `video.py`).
2. Cómo esperan los agentes: el skill de multimedia encola, termina lo que no depende del audio y pide a la persona que
   ejecute `collect` más tarde; o el handoff lo recoge solo en la siguiente sesión.
3. Batch por curso o por proyecto (un trabajo con todos los cursos pendientes: menos trabajos, pero un fallo afecta a más).
4. Flex primero: si funciona con TTS, puede bastar y ahorrarse la cola.
