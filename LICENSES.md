# LICENSES — procedencia y licencia por fuente

Cada fuente incorporada al dataset final (carpeta `data/`) tiene que tener
una entrada acá antes de considerarse "publicable". Fuentes evaluadas pero
descartadas o sin verificar también se listan, para no re-investigarlas.

## Incorporadas

### Mozilla Common Voice (locale `es`, filtrado por accent Rioplatense)
- **Licencia:** CC0 1.0 (dominio público / sin restricciones).
- **Fuente exacta:** mirror `bookbot/common_voice_23_0_es` en Hugging Face
  (README declara `license: cc0-1.0`), derivado de Common Voice 23.0 de
  Mozilla (commonvoice.mozilla.org, también CC0).
- **Transcripción:** validada por la comunidad de Common Voice (voto
  positivo/negativo por clip). Se considera apta para test set; igual se
  revisa a mano una submuestra antes de confiar en el WER medido sobre ella.
- **Filtro aplicado:** campo `accents` conteniendo "Rioplatense" (cubre
  hablantes de Argentina y Uruguay autorreportados; Common Voice no separa
  ambos países dentro de esta etiqueta).
- **Estado:** ver PROGRESS.md por conteo exacto de horas/clips una vez
  corrido el filtro.

### OpenSLR SLR61 — Crowdsourced Argentinian Spanish speech data set
- **Licencia:** CC-BY-SA 4.0.
- **Fuente:** https://www.openslr.org/61/ — Copyright 2018-2019 Google, Inc.
- **Contenido:** oraciones cortas leídas por voluntarios en Buenos Aires +
  90 mensajes meteorológicos en español argentino.
- **Transcripción:** manual/exacta (texto que se le pidió leer al hablante,
  revisado por calidad) — apta tanto para train como test.
- **Atribución requerida (CC-BY-SA):** al redistribuir, citar "Google, Inc.
  — Crowdsourced high-quality Argentinian Spanish speech data set (OpenSLR
  61)" y mantener la misma licencia CC-BY-SA 4.0 en la redistribución.

## Evaluadas, no incorporadas todavía / pendientes

- **LibriVox** — dominio público, pero sin metadata de nacionalidad de
  narrador. Pendiente curación manual (ver PROGRESS.md). No incorporado aún.
- **Corpus de Uruguay dedicado** — no se encontró ninguno con licencia
  abierta verificable (buscado en OpenSLR, HF, Zenodo). Pendiente revisar
  portales gubernamentales.
- **Archivos de medios públicos (TV Pública/Radio Nacional AR, medios
  públicos UY)** — no investigado todavía. No descargar sin verificar
  licencia explícita de reuso/redistribución (no alcanza con "es de un
  organismo público", tiene que decir explícitamente qué licencia aplica).
- **YouTube con licencia CC** — no investigado todavía. Requiere verificar
  licencia por canal/video individualmente (el filtro de licencia de
  YouTube existe pero hay que confirmarlo video por video antes de incluir).

## Descartadas explícitamente (no usar, por restricción dura del brief)

- Transmisiones de TV/radio con copyright estándar (no liberadas
  explícitamente).
- Partidos de fútbol narrados.
- Reels/TikToks/contenido de influencers sin verificación explícita de que
  el creador lo liberó para este uso.
