# Brief inicial — dataset de audio rioplatense para ASR

## Contexto
Este proyecto nace de una evaluación previa de fine-tunear un modelo de ASR
para que entienda mejor español rioplatense (Argentina + Uruguay: voseo,
entonación, lunfardo, léxico regional). Se concluyó que el verdadero cuello
de botella no es cómputo sino **dataset**: hacen falta horas de audio
rioplatense con transcripción confiable, tanto para entrenar como —sobre
todo— para evaluar (un test set con transcripción de mala calidad da una
métrica de WER que miente).

## Objetivo
Investigar y **armar de verdad** (no sólo listar) un dataset de audio
rioplatense de varios cientos de horas, apto para:
1. Entrenar/fine-tunear un modelo ASR.
2. Evaluar (test set) con confianza — esto necesita transcripción verificada,
   no auto-generada.
3. Publicarse como proyecto open source en algún momento.

## Restricción dura, no negociable
**Sólo contenido de uso público / licencia permisiva**, verificado por fuente
(CC0, CC-BY, dominio público, corpus académicos ya publicados con licencia
abierta, o contenido cuyo propio dueño lo liberó explícitamente para este
uso). Nada de scrapear en volumen transmisiones de TV/radio con copyright,
partidos de fútbol narrados, ni reels/TikToks de influencers sin verificar
que el creador lo haya liberado — eso no se puede redistribuir como parte de
un dataset open source y expone legalmente el proyecto. Ante la duda sobre
la licencia de una fuente, descartarla o marcarla explícitamente como "sin
verificar" y no incluirla en lo que se arma para publicar.

## Puntos de partida sugeridos (no exhaustivo, investigar más)
- **Mozilla Common Voice** — tiene locale es-AR (y puede que es-UY), licencia
  CC0, con voces + transcripción validada por la comunidad. Primer lugar
  obvio para mirar, probablemente la fuente más grande y limpia disponible.
- **LibriVox** — audiolibros de dominio público narrados por voces
  rioplatenses (hay que filtrar por narrador/acento, no todo LibriVox en
  español es rioplatense).
- Corpus académicos publicados (papers de ASR/NLP en español latinoamericano
  con datasets liberados — buscar en Hugging Face Datasets, OpenSLR, Zenodo).
- Archivos abiertos de organismos públicos: TV Pública / Radio Nacional
  Argentina, medios públicos uruguayos (a veces liberan archivo histórico).
- Portales de datos abiertos (datos.gob.ar, catalogodatos.gub.uy) por si hay
  algo de audio/transcripción gubernamental.
- Canales de YouTube que publiquen bajo licencia Creative Commons explícita
  (filtro de licencia de YouTube existe, es distinto de "tiene subtítulos").

## Distinción importante: train vs test
- Para **entrenar** se puede tolerar transcripción más ruidosa (auto-generada
  puede servir como dato de entrenamiento en volumen).
- Para **testear** hace falta transcripción verificada (manual/oficial, o una
  muestra chica revisada a mano por vos). Etiquetá y separá claramente qué
  fuentes van a cada bolsa — no mezclarlas sin marcar.

## Otras cosas a tener en cuenta (sugeridas, usar criterio)
- Diversidad: Argentina y Uruguay, no sólo porteño — pero mantené el foco en
  la zona rioplatense (no diluir con todo el español latinoamericano).
- Metadata por clip: fuente, licencia exacta, duración, y si la transcripción
  es manual/oficial o auto-generada.
- Armar un `LICENSES.md` con la procedencia y licencia de cada fuente
  incorporada — imprescindible antes de publicar nada.
- Ir dejando un `PROGRESS.md`/log con lo que se va encontrando y bajando,
  porque esto corre desatendido y Renzo va a ir revisando de a ratos.
- Como referencia numérica: a bitrate razonable, cientos de horas son del
  orden de decenas de GB, no debería ser un problema de espacio en esta M1 —
  pero si en algún momento el total pasa varias decenas de GB, dejarlo
  anotado en el log en vez de seguir sin más.

## Cómo trabajar
Esta sesión corre con permisos sin restricción (--dangerously-skip-permissions)
y en tmux, así que no hay confirmaciones intermedias — actuá con criterio
propio dado todo lo de arriba, and priorizá dejar rastro escrito (README,
PROGRESS.md, LICENSES.md) por sobre "hacer y no contar", para que alguien
que llega después (Renzo, o vos misma en otra sesión) pueda entender el
estado sin tener que releer todo el historial de shell.

Arrancá por investigar qué hay disponible (Common Voice primero), armar un
plan concreto de cuántas horas se pueden sacar de fuentes confiables, y
después ejecutar la descarga/organización.
