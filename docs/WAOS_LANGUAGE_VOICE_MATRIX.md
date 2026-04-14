# WAOS language voice matrix

## Qué quedó global por default

Todos los bots ahora heredan:
- detección de idioma del contacto (`es`, `en`)
- respuesta en idioma detectado
- matriz de tono por idioma
- entendimiento de tono del cliente
- contexto reciente desde VOX (`voice_notes`)

## Español

La voz en español debe sentirse:
- cercana
- clara
- ágil
- comercial sin sonar intensa
- natural, no corporativa

Tonos base:
- formal -> `con gusto`
- casual -> `va`
- playful -> `jajaja, sí te sigo`
- overwhelmed -> `sí te creo`
- direct -> `de una`

## English

The voice in English should feel:
- native
- clear
- sharp
- friendly
- commercial without sounding pushy

Tone anchors:
- formal -> `happy to help`
- casual -> `got you`
- playful -> `haha, fair`
- overwhelmed -> `I get you`
- direct -> `got it`

## Qué toma VOX para contexto

Prioridad actual:
1. summary
2. detected_language
3. intent
4. urgency_level
5. emotion

## Dónde vive

- `backend/app/domains/language.py`
- `backend/app/ai.py`
- `backend/app/defaults.py`
- `backend/app/verticals.py`
