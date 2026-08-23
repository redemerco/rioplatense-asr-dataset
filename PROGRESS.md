# PROGRESS — dataset de audio rioplatense para ASR

Log cronológico. Entradas nuevas al final. Formato: `## AAAA-MM-DD HH:MM`.

## 2026-08-21 21:00 — Arranque de sesión

Leído BRIEF.md. Arranca investigación + ejecución desatendida.

### ⚠️ Bloqueante de espacio en disco — leer antes de asumir "cientos de horas"

Esta M1 tiene **un solo disco de 245GB, con sólo ~15GB libres** en este
momento (`df -h` → `/System/Volumes/Data` 93% usado, 15Gi disponibles). El
brief asume que "cientos de horas ≈ decenas de GB" no es problema de espacio,
pero acá el margen real es mucho más chico que eso. Decisión: avanzar
igual, pero con un techo duro de uso de disco bien por debajo del límite
(ver "Presupuesto de disco" abajo), documentar todo lo que se descarta por
este motivo, y dejar explícito que **para llegar a las "varias centenas de
horas" del objetivo del brief hace falta más disco** (disco externo o correr
esto en otra máquina) — no es algo que se resuelva con más criterio de
selección de fuentes, es un límite físico.

**Presupuesto de disco para esta sesión: tope de 8GB en `data/` + `raw_cache/`.**
Se va a ir chequeando `df -h` antes y después de cada descarga grande y
anotando acá. Si en algún momento el disco libre baja de 3GB, se para todo
y se anota como bloqueante.

### Investigación de fuentes (resumen — detalle de licencias en LICENSES.md)

1. **Mozilla Common Voice (es)** — El locale `es` de Common Voice agrupa
   TODOS los acentos hispanohablantes en un solo dataset (no hay `es-AR` /
   `es-UY` como locale separado). Tiene un campo `accent` autorreportado por
   el hablante, con una taxonomía armonizada (post-2022) que incluye
   **"Rioplatense"** como categoría — cubre Argentina + Uruguay, que es
   exactamente el recorte que buscamos. Licencia **CC0** (dominio público).
   Mirror conveniente en Hugging Face: `bookbot/common_voice_23_0_es`
   (CC0-1.0 explícito en su README, evita el gate de login/términos de
   commonvoice.mozilla.org). Dataset completo es→ ~449h validadas / >1.6M
   clips — mucho más grande que nuestro presupuesto de disco, así que la
   estrategia es: bajar sólo metadata (parquet, liviano) primero, filtrar
   por `accent` conteniendo "Rioplatense"/Argentina/Uruguay, y de ahí bajar
   sólo el audio de las filas que matchean.
   - **Transcripción: validada por comunidad → apta para test set**, con
     revisión manual adicional de una muestra si se quiere confianza extra.

2. **OpenSLR SLR61 — "Crowdsourced high-quality Argentinian Spanish speech
   data set"** — grabado por voluntarios en Buenos Aires. Licencia
   **CC-BY-SA 4.0**. 5,739 grabaciones (oraciones cortas + 90 mensajes
   meteorológicos), ~1.7GB en zips (es_ar_female.zip 1.2G + es_ar_male.zip
   551M). Habla leída, no espontánea — buen material de train, la
   transcripción es la oración leída (exacta) así que también sirve como
   test de alta confianza para esas oraciones puntuales.
   - No existe (buscado, no encontrado) un equivalente para Uruguay en
     OpenSLR. Los corpus hermanos de este mismo proyecto (Google
     crowdsourcing LRE 2020) cubren Argentina, Chile, Colombia, Perú,
     Puerto Rico, Venezuela — Uruguay no está.

3. **LibriVox** — catálogo público dominio-público (grabaciones caen en
   dominio público en EEUU), pero LibriVox no tiene metadata de
   nacionalidad/acento del narrador — hay que identificar narradores
   argentinos/uruguayos a mano (por nombre conocido, o escuchando muestras).
   Pendiente: catálogo completo en español ronda ~400 títulos; falta
   cruzar con narradores rioplatenses conocidos. **No ejecutado todavía en
   esta sesión** — queda como próximo paso, prioridad media (volumen
   incierto y curación manual cara).

4. **Corpus de Uruguay dedicado**: no se encontró ninguno con licencia
   abierta en la búsqueda (Zenodo, HF, OpenSLR). Uruguay va a quedar
   sub-representado salvo lo que aparezca con accent=Rioplatense en Common
   Voice (que sí incluye hablantes uruguayos, sin distinguir de argentinos
   dentro de esa etiqueta) o algo que aparezca después en portales de datos
   abiertos gubernamentales (catalogodatos.gub.uy — todavía no revisado).

5. **Medios públicos (TV Pública / Radio Nacional AR, medios públicos UY),
   datos.gob.ar, catalogodatos.gub.uy, YouTube CC** — todavía no
   investigados en esta sesión (quedan para la siguiente pasada). No
   descargar nada de estas fuentes sin verificar licencia primero, por la
   restricción dura del brief.

### Plan concreto (versión inicial, se va a ir ajustando)

1. Bajar metadata (parquet liviano) de `bookbot/common_voice_23_0_es`,
   filtrar por accent Rioplatense, medir cuántas horas hay realmente antes
   de comprometer disco.
2. Bajar el audio de esas filas nomás, split train/dev/test tal como viene
   de Common Voice (ya separa test con criterio propio — igual conviene
   revisar a mano una submuestra del test antes de confiar 100%).
3. Bajar SLR61 completo (Argentina, CC-BY-SA 4.0) — chico, cabe en el
   presupuesto de disco.
4. Con lo que sobre de presupuesto de disco: catálogo LibriVox rioplatense
   (curado a mano) y/o exploración de portales gubernamentales.
5. Registrar todo en LICENSES.md a medida que se incorpora, con metadata
   por clip (fuente, licencia, si transcripción es manual/oficial o
   auto-generada) en un manifest CSV/JSONL en `data/`.

Próxima entrada: resultado del filtrado de metadata de Common Voice.

## 2026-08-21 21:35 — Resuelto el bloqueante de disco: NAS

Renzo sugirió usar el NAS de casa (`ssh nas`, alias ya configurado en
`~/.ssh/config` → `pi@100.121.47.10` vía Tailscale) en vez de comprometer
los ~15GB libres de esta Mac. Confirmado:
- NAS tiene **221GB libres** en `/srv/dev-disk-by-uuid-.../` (disco de
  datos de 240GB, 6% usado). Mucho margen para las "cientos de horas"
  del objetivo.
- `ssh nas` tiene un `RemoteCommand` fijo en la config (te deja en
  `Proyectos/` con un shell interactivo) — para correr comandos puntuales
  o rsync hay que pisarlo: `ssh -o RemoteCommand=none -o RequestTTY=no nas
  '<comando>'`. rsync probado y funcionando igual, con
  `-e "ssh -o RemoteCommand=none -o RequestTTY=no"`.
- **Decisión de arquitectura**: el procesamiento (descarga, filtrado,
  decodificación) corre acá en la Mac (tiene mejor CPU que el Raspberry Pi
  del NAS); el resultado final (clips + manifest) se sincroniza por rsync
  al NAS en `Remoto/Proyectos/rioplatense-asr-dataset/data/...`, y la copia
  local se borra lote por lote. Así el disco de la Mac nunca acumula más
  que un shard a la vez (~350MB) — el techo de 8GB que puse antes ya no es
  necesario como límite duro, pero lo dejo como chequeo de seguridad en el
  script (para si el NAS se cae a mitad de camino).
- Este repo (`~/Desktop/rioplatense-asr-dataset`) sigue viviendo en la Mac
  con git — es sólo el dataset (`data/`) el que vive espejado en el NAS.
  `raw_cache/` y `.venv/` quedan sólo locales (están en `.gitignore`).

### Common Voice — confirmado el campo de acento y arrancada la descarga

Bajé el shard 0 de test (349MB, vía la API REST directa de HF —
`huggingface_hub` como librería Python se me colgaba sin motivo aparente
en `HfApi().dataset_info(...)`, así que lo abandoné y pego directo a
`https://huggingface.co/api/datasets/.../parquet/...`, que anda bien).

Inspeccionado localmente: el valor exacto de la categoría armonizada es
`"Rioplatense: Argentina, Uruguay, este de Bolivia, Paraguay"` — 153 de
7947 filas en ese shard (~1.9%). El 78% de las filas no tiene `accents`
(nadie lo autorreportó), así que la proporción real sobre el total del
dataset es baja pero real. Con esa tasa, estimación gruesa sobre las 449h
totales validadas de `es`: **del orden de 8-10 horas** de audio
Rioplatense en todo Common Voice — bastante menos que "cientos de horas"
pero es limpio, con transcripción validada por comunidad, y sirve
particularmente bien como base del **test set** (que es lo que más
importa tener confiable, según el brief).

El audio viene como mp3 embebido en el parquet (`audio.bytes`, con
`audio.path` tipo `common_voice_es_XXXXXXXX.mp3`) — se guarda tal cual,
sin recodificar.

Escribí `scripts/01_common_voice_rioplatense.py`: recorre los 33 shards de
train + 2 de test del mirror `bookbot/common_voice_23_0_es` (CC0), baja
cada shard completo (~330MB), filtra por `accents` conteniendo
"Rioplatense", escribe clips + manifest (`data/{split}/manifest_common_voice.jsonl`),
sincroniza ese lote al NAS por rsync, y borra la copia local antes de
pasar al siguiente shard. Corta solo si el disco libre baja de 3GB.

**Corriendo en background ahora** (`nohup`, PID visible en
`logs/01_common_voice.log`), va a tardar bastante (33+2 shards a
~1.4MB/s de descarga cada uno ronda los 4-5 min → un par de horas en
total). Update de resultado final en la próxima entrada.

### OpenSLR SLR61 — también arrancado en paralelo

Confirmé formato: `line_index_*.tsv` es `<fileid>\t<transcripción>` y los
wav están en zips bajo `es-ar/<fileid>.wav`. Escribí
`scripts/02_openslr_slr61.py` (baja los 3 zips ~1.8GB, cruza contra los
tsv, arma manifest, sincroniza al NAS, borra local). Corriendo en
background (`logs/02_openslr_slr61.log`).

### LibriVox — evaluado, no es automatizable en esta sesión

Investigué cómo identificar narradores argentinos/uruguayos en el catálogo
de LibriVox en español (~400+ títulos). Conclusión: **LibriVox no expone
metadata de nacionalidad/acento del narrador** — ni en su API ni en el
foro hay un listado estructurado. La única forma confiable de curar esto
es escuchando muestras de cada narrador para confirmar acento rioplatense,
y esta sesión no tiene una tool de audio para escuchar clips. Automatizarlo
por nombre de narrador sería adivinar (un nombre no dice de dónde es la
persona ni qué acento tiene) y arriesgaría meter narradores no-rioplatenses
en el dataset con la etiqueta mal puesta — inaceptable sobre todo para el
test set. **Decisión: LibriVox queda pendiente para una sesión con
capacidad de escuchar audio (Renzo a mano, o un modelo con audio), no
para esta.** No se descarga nada de LibriVox por ahora.

## 2026-08-21 21:40 — SLR61 completo; caída transitoria del NAS

**SLR61 terminado y sincronizado: 5,829 clips, 8.13 horas** (corregido
más abajo a 5,739 clips / 8.03h — encontré 90 duplicados exactos). Manual,
transcripción exacta (oración leída) — va a `data/train/manifest_slr61.jsonl`,
audio en el NAS bajo `data/train/clips_slr61/`.

En el medio el rsync final falló (`unexpected end of file`, código 255) y
justo después until el NAS se volvió completamente inalcanzable — ni SSH
ni las tools MCP conectaban (`ping` a la IP de Tailscale, 100% packet
loss). No fue algo que yo pudiera arreglar desde acá (si el NAS no
responde, no hay forma de entrar a reiniciar nada). Esperé y reintenté cada
tanto; a los pocos minutos volvió solo (probablemente un blip de Tailscale
o de la wifi del Raspberry Pi). Cuando volvió, sincronicé SLR61 a mano y
confirmé los 5,829 clips + manifest en el NAS.

**Cambio hecho por esta caída**: `01_common_voice_rioplatense.py` (que
en ese momento seguía bajando shards de HF sin problema, ya que eso no
depende del NAS) tenía el riesgo de que su próximo rsync fallara y tirara
abajo el script entero, perdiendo el progreso de shards restantes. Le
agregué:
- reintentos con espera antes de darse por vencido en cada rsync,
- si el NAS sigue caído tras los reintentos, no aborta: deja el lote local
  sin sincronizar y sigue con el próximo shard (no se pierde nada, sólo
  queda pendiente de un rsync posterior),
- un marker file por shard ya procesado (`raw_cache/.done_cv_<split>_<i>`)
  para no reprocesar/duplicar en el manifest si hay que reiniciar el
  script a mano.

El proceso que ya estaba corriendo tiene el código viejo cargado en
memoria (no se actualiza solo) — si llega a crashear por esto, reiniciar
con `python scripts/01_common_voice_rioplatense.py` ya retoma bien gracias
a los markers (creé a mano el marker del shard test/0, que ya había
sincronizado antes de este incidente).

**Test set de Common Voice Rioplatense completo: 257 clips, ~24.5 min**
(0.41h). Chico — son clips cortos (Common Voice ronda 4-6s por clip) y el
split de test del dataset ya viene fijado por Mozilla. Sigue siendo el
material más confiable que tenemos para medir WER (validado por
comunidad), pero antes de publicar conviene que Renzo escuche una
muestra a mano para confirmar. Arrancando ahora los 33 shards de train
(en curso, va a tardar un buen rato — cada shard son ~330MB a ritmo
lento de red).

## 2026-08-21 23:20 — Checkpoint a mitad de camino de train (17/33 shards)

Un timeout de curl (código 28) tiró abajo el script una vez en el medio
(shard train/4) — reinicio limpio gracias a los markers, sin duplicar
nada (verificado contando líneas de manifest antes/después). Le agregué
reintentos también a la descarga (además de los del rsync) para no tener
que reiniciar a mano de nuevo.

Estado en este checkpoint: **8,214 clips / 12.67h de train** +
**257 clips / 0.41h de test**, ambos ya en el NAS. Un par de shards
(15 y 16) dieron 0 filas Rioplatense — no es un error, la metadata de
`accents` es dispareja entre shards del dataset original, hay tramos con
poco o nulo autorreporte de acento. Sigue corriendo, faltan ~16 shards de
train.

## 2026-08-22 00:50 — Hallazgo: la metadata de acento viene en tandas, no distribuida parejo

Confirmado con más shards: del 15 al 27 (salvo uno), casi todos dieron
**0 filas Rioplatense** — pero el shard 21 solo aportó **2,938 filas de
una** (27% del shard, muy por encima del ~2% típico de los primeros
shards). El conteo del manifest cuadra exacto con esto (8,214 antes +
2,938 = 11,152 ahora), así que no es un bug del filtro, es que el mirror
de HF agrupa los shards por algún criterio de origen/importación y la
metadata `accents` (autorreportada) sólo está presente en algunas tandas
de clips, no en todas. Práctico: no sirve estimar el total lineal a
partir de los primeros shards, hay que esperar a que termine para saber
el número real. Quedan 5 shards (28 a 33).

## 2026-08-22 01:30 — Common Voice Rioplatense: COMPLETO

Terminaron los 33 shards de train. Sin más caídas de red ni del NAS desde
el reinicio de train/4. Total final:

| | clips | horas |
|---|---|---|
| Common Voice train (validado) | 11,152 | 17.27h |
| Common Voice test (validado) | 257 | 0.41h |
| SLR61 train (manual/exacto) | 5,829 | 8.13h |
| **Total dataset hasta ahora** | **17,238** | **25.81h** |

Todo sincronizado y verificado en el NAS
(`Remoto/Proyectos/rioplatense-asr-dataset/data/`), copia local ya
limpiada (18GB libres en la Mac, sin comprometer nada).

### Nueva fuente encontrada: VoxForge (subset Argentina)

Investigando más, apareció `ciempiess/voxforge_spanish` en HF — mirror de
VoxForge curado por el proyecto académico CIEMPIESS (Carlos Daniel
Hernández Mena), **49h42min, 21,692 clips**, con un campo `country`
explícito (`argentina`/`chile`/`latinamerica`/`mexico`/`spain`/`unknown`)
— mucho más limpio de filtrar que el `accents` de Common Voice. Licencia
**GPLv3** (copyleft, no CC0/CC-BY, pero es una licencia abierta de un
corpus académico publicado — entra dentro de lo que permite el brief;
igual hay que mantener el aviso de licencia y atribución al
redistribuir, y no se puede re-licenciar como CC0/CC-BY, sólo agregar
como colección con licencia propia declarada por-clip). El texto viene
"normalizado" (minúsculas) pero conserva tildes.

Lancé `scripts/03_voxforge_argentina.py` (mismo patrón que Common
Voice: 8 shards ~450MB, filtro `country == "argentina"`, sync a NAS con
reintentos, markers para reinicios seguros). Corriendo en background
(`logs/03_voxforge.log`). Con 6 categorías de país, si Argentina es una
fracción pareja del total podría aportar ~8h más, pero hay que esperar
el número real (mismo aprendizaje que con Common Voice: no estimar
lineal antes de tiempo).

**Contraste con el objetivo del brief ("varios cientos de horas"):**
25.8h es un buen arranque limpio y 100% verificado por licencia, pero
está lejos del objetivo final. Los candidatos obvios para escalar más
(Common Voice completo sin filtrar por acento, LibriVox, medios públicos)
tienen trade-offs ya documentados arriba: bajar todo `es` de Common Voice
sin filtro de acento diluiría el foco rioplatense (viola el criterio del
brief de "no diluir con todo el español latinoamericano"); LibriVox
necesita curación por oído que esta sesión no puede hacer; medios
públicos necesitan verificación de licencia explícita fuente por fuente
antes de tocar nada.

### Próximo paso: mergear manifests + próxima fuente

Voy a: (1) armar un manifest único por split que una las fuentes ya
incorporadas (más fácil de consumir), (2) actualizar LICENSES.md con los
números definitivos, (3) seguir investigando fuentes adicionales
(portales de datos abiertos, YouTube con licencia CC explícita) para ver
si hay más volumen real y verificable antes de considerar cerrada esta
fase.

## 2026-08-22 01:45 — VoxForge Argentina completo; checkpoint consolidado

VoxForge terminó rápido (shards de ~450MB, mucho más veloces que los de
Common Voice — probablemente porque son más chicos). Todo el contenido
Argentina estaba concentrado en el shard 1 (1,735 de 2,712 filas, 64%);
los otros 7 shards dieron 0 — VoxForge agrupa cada shard por tanda de
hablantes/envío, no vienen mezclados. **1,735 clips, 4.22h.**

### Estado consolidado del dataset (esta sesión)

| Fuente | Split | Clips | Horas | Licencia | Transcripción |
|---|---|---|---|---|---|
| Common Voice 23.0 (accent=Rioplatense) | train | 11,152 | 17.27h | CC0 | validada (comunidad) |
| Common Voice 23.0 (accent=Rioplatense) | test | 257 | 0.41h | CC0 | validada (comunidad) |
| OpenSLR 61 (Argentina) | train | 5,739 | 8.03h | CC-BY-SA-4.0 | manual (exacta) |
| VoxForge (country=argentina) | train | 1,735 | 4.22h | GPLv3 | manual (normalizada) |
| **Total train** | | **18,626** | **29.52h** | | |
| **Total test** | | **257** | **0.41h** | | |
| **Total dataset** | | **18,883** | **29.93h** | | |

**Corrección posterior a este checkpoint:** al verificar conteos contra
el NAS encontré que el manifest de SLR61 tenía 90 filas de más (5,829 en
vez de 5,739). Causa: el zip de mensajes meteorológicos duplica ~90 ids
que ya estaban en el corpus general femenino (mismo audio, mismo texto
exacto — confirmé que las 90 duplicadas tienen texto idéntico letra por
letra, no es un mismatch de contenido). Dedupliqué el manifest por
`path` y agregué una guarda (`seen_fids`) al script para que no vuelva a
pasar si se re-corre. Los números de la tabla de arriba ya están
corregidos.

Todo sincronizado y verificado en el NAS, manifest unificado por split en
`data/{split}/manifest.jsonl` (via `scripts/merge_manifests.py`), detalle
de licencia por fuente en `LICENSES.md`. Disco de la Mac: ~18GB libres,
sin comprometer nada (todo el peso real vive en el NAS).

### Balance honesto vs. el objetivo del brief

30 horas es un dataset limpio, 100% trazable por licencia, con buena
diversidad de tipo de habla (espontánea validada de CV, lectura
controlada de SLR61/VoxForge) — pero está a un orden de magnitud de las
"varias centenas de horas" que pide el brief. Las fuentes que faltan para
cerrar esa brecha (LibriVox curado a mano, medios públicos con licencia
verificada, YouTube CC) requieren o bien capacidad de escuchar audio
(que esta sesión no tiene) o verificación legal fuente-por-fuente que no
se puede automatizar de forma segura sin más tiempo de investigación
dedicado. No las fuerzo con este toolset para no arriesgar meter algo mal
etiquetado.

### Qué sigue (para que Renzo decida, no algo que vaya a asumir solo)

1. **Revisar a mano una muestra del test set** (257 clips CC0 validados
   por comunidad) antes de confiar en el WER que dé sobre él — es chico,
   se puede escuchar entero en una sentada.
2. **LibriVox rioplatense**: si a Renzo le interesa, necesita curación
   por oído (identificar narradores AR/UY) — no lo puedo hacer yo en
   esta sesión de texto. Si él (u otra sesión con audio) arma una lista
   de narradores confirmados, vuelvo y automatizo la descarga de esos
   audiolibros puntuales.
3. **Medios públicos / YouTube CC / portales gubernamentales**: quedan
   como pendientes de investigación más profunda (verificar licencia
   caso por caso) — no encontré nada concreto y verificable en las
   búsquedas de esta sesión, pero no es una investigación exhaustiva.
4. Si Renzo quiere, puedo seguir buscando más corpus académicos
   publicados (HuggingFace/Zenodo/OpenSLR) con el mismo patrón usado acá
   — es el camino de mayor confianza aunque de retorno decreciente.

No voy a seguir escalando fuentes de forma autónoma más allá de esto sin
que Renzo revise el balance licencia/esfuerzo — quedo a la espera de que
mire este checkpoint.

## 2026-08-22 09:00 — Hallazgo grande: YouTube CC-BY, canal Snac Podcast

Renzo confirmó que con 10-40h ya se ven mejoras reales de WER en
fine-tuning de este tipo, y me pidió seguir escalando fuentes sin frenar
a pedir permiso en cada paso. Retomé la búsqueda de YouTube con filtro
de licencia Creative Commons (usando el filtro real de YouTube, no
adivinando por búsqueda).

**Snac Podcast** (Argentina, entrevistas/charlas, @SnacPodcast) — **875
videos**, la mayoría de 60-100 minutos. Verifiqué licencia real (no sólo
el filtro de búsqueda, sino el campo `license` de la metadata de cada
video vía yt-dlp) en una muestra de 30 episodios: **30/30 confirmados
"Creative Commons Attribution license"**. Idioma original `es`/`es-US`
(no doblaje). Si el canal entero sostiene esta licencia, y asumiendo un
promedio de ~75min/episodio, estamos hablando de **potencialmente 700-900
horas** — un salto de orden de magnitud vs. lo que teníamos.

Encontré también "Un Podcast Uruguayo" pero es **CC BY-ND** (no derivados)
— lo descarté, segmentar/transcribir para ASR probablemente cuenta como
obra derivada y el brief pide descartar ante la duda.

### Pipeline nuevo: YouTube CC → clips

Los auto-captions de YouTube vienen en formato "rolling caption" (texto
acumulado de a poco, se repite con cada cue) — armé
`scripts/vtt_segment.py` para parsear eso a nivel palabra (usando los
timestamps `<c>` inline) y cortarlo en segmentos de unos pocos segundos
(por pausas largas o fin de oración). Probado sobre un episodio de 65
min: 706 segmentos, ~4.6s de duración media — comparable a la
distribución de clips de Common Voice.

`scripts/05_youtube_cc_channel.py` hace todo el pipeline por video:
chequea licencia (salteando si no es CC-BY, doble verificación aunque ya
haya pasado el filtro de búsqueda), baja audio (`worstaudio`, para no
gastar de más — la resolución de audio no importa tanto para ASR) +
auto-captions, decodifica el episodio **una sola vez** a un array numpy
(en vez de un ffmpeg por clip — con potencialmente cientos de miles de
clips en todo el canal, eso sería demasiado lento), corta los segmentos
en memoria, escribe manifest con `transcript_type: auto` (son
auto-captions, no transcripción manual — sólo sirve para train, no para
test) y `license: CC-BY-3.0`. Sincroniza al NAS cada 10 videos.

**Corriendo ahora sobre la muestra de 30 episodios ya validados**
(`logs/05_snac_sample.log`) para confirmar que todo el pipeline funciona
de punta a punta antes de plantearme correrlo sobre los 875 videos
completos (o buscar más canales similares en paralelo). Primeros
episodios: 596-1108 clips cada uno, pipeline funcionando bien.

También encontré **"Vertice"** (@Vertice_uy, Uruguay, 2.200 videos de
entrevistas) — pero verificado por metadata real, la mayoría de sus
videos **NO** son CC-BY (licencia `NA` = standard YouTube license en 5/5
muestreados). Sólo el que salió en el buscador filtrado por CC tenía la
licencia puesta a mano en ese video puntual. Descartado como fuente
masiva (mi pipeline ya chequea licencia por video de todas formas, así
que no habría hecho daño correrlo, pero el rendimiento sería bajísimo).

## 2026-08-22 09:30 — Cambio de objetivo: benchmark real fine-tuned vs. genérico

Renzo redefinió el objetivo final: en unos días quiere un **benchmark
concreto** comparando Qwen3-ASR-1.7B genérico (el que ya está en
producción en `~/Desktop/zoom-recorder`) contra una versión fine-tuneada
con este dataset, evaluados ambos contra el mismo test set held-out. Y
dos reglas adicionales:
1. **No conformarse con una corrida.** Si la mejora no es notoria (no
   ruido), iterar (más datos/épocas/hiperparámetros) hasta 3 intentos
   serios; si no se logra, frenar y reportar diagnóstico en vez de seguir
   a ciegas.
2. **Set de métricas propio**, no sólo WER global.

Pido no pedir visto bueno en cada paso — sigo a criterio propio, y sólo
freno si hay algo genuinamente ambiguo/riesgoso (como hice con la escala
de Snac Podcast).

### Investigación del setup técnico (zoom-recorder)

- Producción usa `mlx-community/Qwen3-ASR-1.7B-bf16` vía **MLX** nativo
  (`mlx_audio.stt.generate`), no PyTorch — así corre inferencia rápido en
  Apple Silicon. El venv `.venv-asr` de zoom-recorder NO tiene PyTorch
  instalado (a propósito, es sólo-inferencia).
- Encontré el checkpoint **`Qwen/Qwen3-ASR-1.7B-hf`** — la versión nativa
  de 🤗 Transformers del mismo modelo (no la conversión MLX). Ese es el
  que hay que usar para fine-tunear, porque `modeling_qwen3_asr.py` ya
  soporta `labels` y computa loss estándar (cross-entropy sobre el texto)
  — es un modelo HF normal (encoder de audio → proyector → LLM decoder),
  así que `transformers` + `peft` (LoRA) es el camino recto, no hace
  falta reinventar un loop de entrenamiento a mano ni pelearla en MLX
  (que no tiene soporte de training listo para este modelo específico,
  sólo para un modelo distinto "mega_asr" que vi de paso en `mlx_audio`).
- Plan: **entrenar con LoRA vía transformers+peft** (venv nuevo, separado
  del `.venv-asr` de zoom-recorder — no quiero tocar ni arriesgar el
  entorno de producción de otro proyecto), y para evaluar de forma
  consistente con producción, convertir/fusionar el LoRA resultante y
  correrlo vía el mismo `mlx_audio.stt.generate` que usa producción —
  así el benchmark compara peras con peras (mismo motor de inferencia
  para ambos modelos, sólo cambian los pesos).
- Reuso el `wer.py` de zoom-recorder como base para el cálculo de WER
  (normaliza a minúsculas, saca puntuación, conserva acentos/ñ — mismo
  criterio que ya usaron ahí, no reinvento la métrica).

### Set de métricas elegido (y por qué)

- **WER** (word error rate) — la métrica estándar del campo, y la que ya
  usa zoom-recorder; necesaria para comparabilidad directa con ese
  shootout previo.
- **CER** (character error rate) — WER trata "vos tenés" vs "vos tenes"
  como 100% mal en esa palabra; CER es más fino para captar mejoras
  chicas en acentuación/ortografía que WER no distingue bien, y el
  español rioplatense tiene mucho de eso (tildes, voseo). Sin CER,
  una mejora real en calidad de transcripción podría no reflejarse en el
  WER si el error sigue siendo "una palabra distinta" a nivel de token.
- **Desglose por dificultad** (habla normal vs. rápida/con jerga) — mismo
  criterio que el shootout de zoom-recorder (ahí "audio C2, denso en
  jerga a ritmo forzado" fue el caso límite que reveló la debilidad real
  de Qwen3-ASR). Un WER global puede esconder que el fine-tuning ayuda en
  el caso común pero no en el difícil (o viceversa) — reporto ambos por
  separado, no sólo el promedio.
- **Tiempo de inferencia** — no es criterio de decisión (zoom-recorder ya
  estableció que acá prioridad es calidad, no velocidad), pero lo mido y
  reporto igual: un fine-tuning que empeorara mucho la latencia sería un
  dato que Renzo debería conocer aunque no cambie la decisión.

### Próximos pasos (en orden)
1. Ampliar el test set held-out más allá de los 257 clips de Common Voice
   (son pocos para medir una mejora "notoria" con confianza) — reservar
   también algunos episodios enteros de Snac Podcast y algunos hablantes
   de SLR61/VoxForge que NUNCA entren a train, sin overlap.
2. Seguir juntando volumen de train (Snac Podcast a más escala + buscar
   más fuentes) mientras se arma el resto.
3. Armar el venv de entrenamiento (torch+transformers+peft+accelerate),
   separado del de zoom-recorder.
4. Script de fine-tuning LoRA + script de evaluación (WER/CER/desglose/
   tiempo) reutilizando `wer.py` como base.
5. Correr, medir, iterar si hace falta (máx 3 intentos serios), reportar.

### Condición de cierre: autocrítica obligatoria (no negociable)

Renzo agregó una condición dura: aunque logre una mejora "notoria", el
proyecto **no se da por terminado** hasta pasar una ronda de autocrítica
real — un prompt exigente que busque activamente: fugas de datos entre
train/test, fallas metodológicas, sesgos, benchmark poco honesto,
cualquier problema real. Si encuentra algo, arreglar y repetir el ciclo
completo (incluida la autocrítica) hasta que no quede nada que objetar.

**Aclaración importante de Renzo:** no alcanza con que yo me autocritique
dentro de esta misma sesión (mismo contexto, mismo sesgo de haber hecho
el trabajo). Tiene que ser **otra instancia de Claude Code totalmente
independiente** — un `claude -p "<prompt>" --dangerously-skip-permissions`
nuevo, sin mi contexto de sesión, apuntado a los archivos reales del
proyecto (no un resumen mío), sin saber que yo lo armé. Sólo si ese
evaluador externo no encuentra fallas reales se puede cerrar. Documentar
acá el prompt exacto dado al evaluador y su veredicto completo, cada
ronda. Esto lo hago al final, una vez que haya un resultado real que
evaluar — no tiene sentido antes.

### Repo público en GitHub

A pedido de Renzo, este proyecto ahora vive también en un repo público:
**https://github.com/redemerco/rioplatense-asr-dataset** — voy a pushear
a medida que avanzo (no un solo push al final). Va todo el código,
PROGRESS.md, LICENSES.md, y los manifests (metadata/texto, sin audio). El
audio real (varios GB, licencias mixtas por fuente) se queda en el NAS —
no tiene sentido en un repo git normal, ni hace falta Git LFS; el
manifest con paths alcanza para referenciarlo.

### Split de test held-out armado

`scripts/06_build_test_split.py` — reservé hablantes completos (nunca
overlap de audio, y nunca el mismo hablante en train y test) de las
fuentes con transcripción manual/verificada:
- **SLR61**: 9 de 44 hablantes (~20%) → **1,091 clips** a test.
- **VoxForge**: 13 de 174 hablantes → **130 clips** a test.
- **Common Voice**: se mantiene su split oficial (257 clips, ya estaba
  separado).

**Snac Podcast (y cualquier fuente de YouTube CC futura) queda 100% en
train, nunca en test** — decisión deliberada: su transcripción es
auto-caption de YouTube, no verificada. Si la usara como test, estaría
midiendo qué tan parecido es el modelo al ASR de YouTube, no midiendo
transcripción correcta — mezclaría los errores de esa referencia con los
del modelo evaluado. El test set sólo usa fuentes con transcripción
manual/validada por humanos.

**Test set consolidado: 1,478 clips** (257 CV + 1,091 SLR61 + 130
VoxForge). Selección de hablantes held-out determinística por hash (no
random con seed) — reproducible sin guardar estado aparte.

Hubo un bache al mover los archivos en el NAS (el comando de `mv` para
los 1,091 archivos de SLR61 en un solo `ssh` se cortó por "broken pipe" —
la línea de comando era demasiado larga) — lo arreglé mandándolo en
tandas de 150 archivos por vez. Verificado conteo final en el NAS
(train/test suman el total original, sin pérdidas ni duplicados).

### Setup técnico confirmado

- Checkpoint: `Qwen/Qwen3-ASR-1.7B-hf` (Apache-2.0, 4.08GB safetensors,
  arquitectura `Qwen3ASRForConditionalGeneration`).
- **Fine-tuning está documentado oficialmente** en el model card: pasar
  `output_labels=True` al processor, transcripción objetivo en el turno
  del asistente como `"language Spanish<asr_text>{transcript}"` — el
  processor enmascara automáticamente audio/padding en las labels. No
  hay que inventar un collator desde cero para eso.
- Venv nuevo `.venv-train/` en este proyecto (no toco el `.venv-asr` de
  zoom-recorder): `torch` (MPS confirmado disponible), `transformers`
  5.15.1, `accelerate`, `peft`, `datasets`, `soundfile`, `librosa`.

### Hallazgo crítico: esta Mac tiene sólo 8GB de RAM

`sysctl hw.memsize` → 8GB total. Para un modelo de 1.7B en bf16 (~3.4GB
sólo de pesos) eso es MUY ajustado. Probé el pipeline completo end-to-end
con un clip real:
- `processor.apply_chat_template` + `processor(..., output_labels=True)`
  arma bien los inputs (labels enmascaradas en audio/padding, confirmado
  contando tokens no-enmascarados).
- Forward + loss: **funciona** en MPS con el modelo en bf16.
- Forward + backward + optimizer step con LoRA (r=8, `target_modules`
  las proyecciones de atención/MLP del decoder, ~9.9M params entrenables
  de 2.05B totales = 0.48%) + gradient checkpointing: **funciona sin
  crashear**, primer step ~35s.

Memoria es el recurso crítico acá, no cómputo — por eso LoRA +
`gradient_checkpointing_enable()` no son optimizaciones opcionales, son
lo que hace que esto entre en 8GB. Un intento de medir tiempo por step en
steady-state (5 steps seguidos) se contaminó porque lo corrí en paralelo
con el pipeline de Snac Podcast (yt-dlp + ffmpeg decodificando el
episodio completo a numpy) — con 8GB totales, correr las dos cosas juntas
generó swapping severo (confirmé con `vm_stat`: sólo ~60MB de páginas
libres en ese momento). **Lección: en esta máquina, entrenamiento y
pipeline de datos no pueden correr en paralelo** — hay que serializar.
Maté ese test contaminado; voy a remedir en limpio una vez que termine la
muestra de Snac Podcast.

## 2026-08-22 10:15 — Muestra de Snac Podcast completa: 31.26h de un tirón

Los 30 episodios de la muestra terminaron: **22,878 clips, 31.26 horas**,
sin errores ni licencias rechazadas. Con esto el dataset total pasa a:

| Fuente | Split | Clips | Horas |
|---|---|---|---|
| Common Voice (Rioplatense) | train | 11,152 | 17.27h |
| Common Voice (Rioplatense) | test | 257 | 0.41h |
| OpenSLR 61 | train | 4,648 | ~6.8h |
| OpenSLR 61 | test (held-out) | 1,091 | ~1.6h |
| VoxForge Argentina | train | 1,605 | ~3.9h |
| VoxForge Argentina | test (held-out) | 130 | ~0.3h |
| Snac Podcast (YouTube CC-BY) | train | 22,878 | 31.26h |
| **Total train** | | **40,283** | **58.94h** |
| **Total test** | | **1,478** | **2.24h** |
| **Total dataset** | | **41,761** | **61.18h** |

**61h totales, bien por encima del umbral de 10-40h que Renzo confirmó
que ya muestra mejoras reales.** Decisión: no escalo a los 875 videos
completos del canal por ahora — con esto alcanza según el criterio que
dio Renzo, y cada episodio más son minutos de descarga/procesamiento que
compiten por la misma RAM escasa que necesito para el fine-tuning
(ver hallazgo de 8GB abajo). Si el benchmark final no muestra mejora
notoria, escalar Snac Podcast (o sumar más canales) es la primera
palanca obvia para la iteración 2.

## 2026-08-22 10:40 — Timing limpio y decisión de tamaño del subset de entrenamiento

Con la muestra de Snac ya terminada (sin contención de RAM), remedí el
forward+backward+step: **steady-state ≈ 45-55s por ejemplo** (batch_size=1,
LoRA r=8, gradient checkpointing). Un pico de 278s en medio del test fue
por un rsync que estaba bajando los clips a disco local en paralelo —
confirma otra vez que en esta máquina de 8GB, I/O pesado y GPU/MPS
compiten en serio por memoria.

**Esto cambia el plan de volumen de entrenamiento.** A ~50s/ejemplo,
entrenar sobre las 40,283 clips completas (aunque sea 1 época) son
~560 horas (~23 días) — no entra en "unos días". LoRA no necesita el
dataset completo para adaptar bien un modelo ya preentrenado (a
diferencia de entrenar desde cero); la literatura y la práctica estándar
de LoRA funcionan con conjuntos bastante más chicos que full fine-tuning.

**Decisión: subset curado de ~2,000 ejemplos, muestreo aleatorio del
train combinado (las 4 fuentes), tope de duración 12s, 2 épocas.**
2,000 × 2 épocas × ~50s ≈ 55.6h (~2.3 días) — corre en background de
forma continua durante el resto de la sesión, que es justamente el modo
en que está corriendo todo esto. Si el resultado no es suficiente en la
iteración 1, subir a más ejemplos o más épocas es la primera palanca
(documentado en el plan de iteración de arriba).

Bajé los clips de train (4.8GB) y test (533MB) a disco local
(`local_clips/`) — entrenar leyendo del NAS por sample hubiera sido un
cuello de botella de red constante encima de todo lo demás.

## 2026-08-22 11:00 — Corrección de Renzo: tiempo no es restricción

Renzo aclaró que el tiempo de entrenamiento no importa nada — la M1 está
específicamente para esto, y si tarda semanas no hay problema. Maté el
run de 2,000 ejemplos y **relancé con el dataset de train completo:
40,283 ejemplos, 2 épocas**, tope de duración subido a 20s (el máximo
real del dataset es 19.1s, así que en la práctica no descarta nada).
A ~50s/ejemplo, esto son semanas de cómputo — corriendo en background de
forma continua. Checkpoint cada 50 steps de optimizer (400 ejemplos,
~5.5h) para no perder mucho progreso si hay que reiniciar por un crash.

Mismo criterio de LoRA + gradient checkpointing que antes (necesarios por
la RAM de 8GB, no por el tiempo). Sigo evaluando otros pasos del proyecto
(repo público, documentación) sin correr nada más pesado de MPS/RAM en
paralelo al training.

### Fix: checkpoints numerados, no uno solo que se pisa

Renzo marcó un problema real: el script guardaba siempre en el mismo
`output_dir`, pisando el checkpoint anterior — no había forma de volver
a un checkpoint intermedio si el final resultaba peor (overfitting) ni de
recuperar progreso si algo fallaba a mitad de camino. Corregido: cada
guardado periódico va a `checkpoint-<step>/`, cada fin de época a
`checkpoint-epoch<N>-step<M>/`, y el final a `checkpoint-final-step<M>/`
— todos conviven, nada se pisa. Cada checkpoint LoRA es chico (~9.9M
params, r=8, bf16 ≈ 20MB) así que guardar muchos no es problema de disco.
Maté el run (recién había arrancado, sin pérdida real) y relancé con el
fix. **Cuando llegue el momento de evaluar, voy a correr el benchmark
contra varios checkpoints (no sólo el último) y reportar cuál generaliza
mejor, no asumir que más steps = mejor resultado.**

### Fix: bug real en el resume (`start_step=-1` corrompía epoch/posición)

Al agregar `--auto-resume`, `find_latest_checkpoint()` devuelve `-1` como
sentinela de "no hay checkpoint" — pero yo estaba usando ese `-1` como
`start_step` real cuando no había checkpoint (en vez de resetear a `0`),
lo que rompía `epoch = start_step // steps_per_epoch` (daba `-1` por
floor division) y la posición inicial en el dataset (arrancaba casi al
final del array por el módulo con un número negativo). Lo agarré porque
el primer log mostró `[epoch -1 step 0/10070]` con loss sospechosamente
baja apenas arrancado — no cuadraba. Maté el proceso, arreglé (guardar
`start_step=0` explícitamente cuando no hay checkpoint), verifiqué la
función aislada, y relancé limpio. Sin este chequeo cruzado el bug
hubiera corrompido silenciosamente cualquier reinicio automático futuro.

### Chequeo de salud automático cada 12hs — bloqueado por TCC de macOS

Renzo pidió un mecanismo de chequeo periódico durable (no atado a que
esta sesión siga abierta) para las semanas que va a durar el training.
Investigué la ruta de "rutina en la nube" de `/schedule` — no sirve, esos
agentes corren aislados en la nube de Anthropic sin acceso a esta Mac.

Probé dos rutas locales, ambas con evidencia de que pegan contra el mismo
límite real de macOS (no un bug mío, un límite de seguridad de Apple):
1. **crontab**: cuelga esperando un diálogo de autorización TCC que
   nunca puede aparecer sin sesión gráfica (confirmado 3 veces seguidas,
   nunca fue transitorio).
2. **LaunchAgent** (`~/Library/LaunchAgents/com.rioplatense-asr.health-check.plist`,
   cada 12hs vía `StartInterval`): carga y corre sin colgarse, pero
   falla leyendo archivos dentro de `~/Desktop/...` con
   "Operation not permitted". Confirmé la causa exacta: `~/Desktop` tiene
   el atributo extendido `com.apple.macl` (el marcador de TCC para
   carpetas protegidas — Desktop/Documents/Downloads). Los permisos Unix
   están perfectos; el bloqueo es 100% TCC, que Apple diseñó
   deliberadamente para no poder saltearse por script ni con sudo/root —
   requiere aprobación humana única desde System Settings.

**El LaunchAgent queda instalado y armado** (script real en
`~/.local/bin/rioplatense-health-check.sh`, fuera de Desktop para poder
ejecutarse; el prompt que corre está en
`scripts/train/health_check_prompt.md`) — en cuanto Renzo dé el permiso
de "Files and Folders: Desktop" a Terminal en System Settings (30
segundos, una sola vez), empieza a funcionar solo sin que yo toque nada
más. Mientras tanto sigo haciendo estos chequeos yo misma dentro de la
sesión interactiva, como ya venía.

## 2026-08-22 11:28 — Chequeo automático (cron)

Primer chequeo automático real (el LaunchAgent ya tiene permiso y corrió
solo). Proceso **no estaba corriendo** y no había ningún checkpoint (0
steps completados, `train_log.jsonl` vacío) — lejos del objetivo de
~10070 steps, así que lo relancé.

⚠️ El comando de relanzamiento indicado (`source .venv-train/bin/activate
&& nohup python3 ...`) **falló** en este entorno de cron/LaunchAgent:
`python3` resolvía vía PATH pero tiraba `ModuleNotFoundError:
No module named 'soundfile'` pese a que el paquete sí está instalado en
el venv — probablemente porque LaunchAgent no carga el perfil de shell
completo (PATH mínimo, sin `/opt/homebrew/bin`). Confirmé que invocar el
binario directo (`.venv-train/bin/python3 scripts/train/finetune_lora.py
...`, sin `source activate`) funciona de forma confiable. Relancé así y
el proceso quedó estable (PID vivo, RSS creciendo, sin crash en el primer
minuto). **Recomendación para próximos chequeos automáticos: usar la
ruta directa al intérprete del venv, no `source activate`.**

Disco: 40GB libres, sin problema. No hay `results/baseline.json` ni
`results/finetuned.json` todavía (esperado, entrenamiento recién
relanzado desde 0 steps). No cuento esto como "crash de entrenamiento"
en sí (loss no llegó a evaluarse, no hubo NaN) sino como falla del
comando de relanzamiento — dejo la corrección de arriba para que no se
repita.

## 2026-08-22 11:30 — Proyecto movido fuera de Desktop; venvs recreados

Renzo dio con la causa raíz mejor que mi diagnóstico anterior: el
bloqueo de TCC no es específico de crontab/launchd, es que `~/Desktop`
(igual que Documents/Downloads) está protegido por TCC para CUALQUIER
proceso sin Full Disk Access — y darle Full Disk Access a Terminal es
demasiado amplio (cualquier script con acceso a Terminal podría leer todo
el disco). La solución mejor: **mover el proyecto entero fuera de las
carpetas protegidas**, a `~/rioplatense-asr-dataset` (directo en el
home). Confirmé que la nueva ubicación no tiene el atributo extendido
`com.apple.macl` (el marcador de TCC) que sí tenía Desktop.

Pasos:
1. Maté el training (no había checkpoint todavía, sin pérdida real).
2. `mv ~/Desktop/rioplatense-asr-dataset ~/rioplatense-asr-dataset`.
3. Reapunté el LaunchAgent (`~/Library/LaunchAgents/com.rioplatense-asr.health-check.plist`)
   directo al script del repo (`scripts/train/health_check.sh`) — ya no
   hace falta el wrapper en `~/.local/bin/` que había armado como
   workaround para el problema de exec-en-Desktop (ese problema
   desaparece por completo al no estar más en Desktop). Borré el wrapper
   viejo.
4. Actualicé la ruta hardcodeada en `health_check_prompt.md`.
5. Recargué el LaunchAgent — **corrió limpio, sin el error de TCC.**

**Hallazgo adicional (no relacionado a TCC): los venvs de Python no son
relocables.** `.venv-train/bin/activate` tiene la ruta absoluta de
creación hardcodeada (`VIRTUAL_ENV=.../Desktop/...`) — después del `mv`,
`source activate` prendía un `PATH` que apuntaba a un directorio
inexistente, y `python3` caía silenciosamente al intérprete de sistema
(sin los paquetes). Recreé `.venv` y `.venv-train` desde cero en la nueva
ubicación. El proceso de training que el chequeo automático ya había
relanzado (con el workaround de invocar el binario del venv directo, ver
entrada anterior) **sobrevivió sin problema** al `rm -rf` + recreación
del venv — ya tenía todos los módulos cargados en memoria antes de que yo
tocara los archivos, Python no vuelve a leer del disco lo ya importado.

**Confirmado el chequeo automático funcionando de punta a punta**: el
LaunchAgent lo disparó, `claude -p` diagnosticó un problema real
(training caído por el bug de PATH), lo arregló, y dejó todo documentado
y pusheado — sin que yo tuviera que intervenir. Corrigá la ruta del
`activate` roto en la instrucción del prompt (arriba) para que los
próximos chequeos usen el binario directo del venv desde el arranque.

## 2026-08-22 13:33 — ⚠️ Loss en NaN al primer log (step 20)

El primer log real del training relanzado (post-move) dio
`{"epoch": 0, "step": 20, "loss": NaN}`. Esto es serio: una vez que un
gradiente NaN se aplica con `opt.step()`, los pesos LoRA quedan
permanentemente corrompidos (NaN + cualquier operación = NaN, no se
autocorrige entrenando más). Maté el proceso de inmediato — no había
checkpoint guardado todavía (save cada 50 steps, sólo llegamos a 20), así
que no se perdió ningún checkpoint válido, sólo hay que re-arrancar una
vez encontrada y arreglada la causa.

Armé `scripts/train/diagnose_nan.py`: reproduce el mismo shuffle (seed=0,
igual que el training) y corre sólo forward (sin backward) sobre los
primeros ~170 ejemplos para encontrar cuál produce loss NaN/Inf.
Corriendo ahora. Actualizo esta entrada con la causa raíz apenas salga.

**No voy a reiniciar el training hasta encontrar y arreglar la causa** —
reiniciar a ciegas sólo repetiría el mismo problema en cuanto se tope de
nuevo con el ejemplo/patrón que lo dispara.

### Causa raíz encontrada: faltaba gradient clipping

El diagnóstico (170 ejemplos, sólo forward, sin backward) **no encontró
ningún ejemplo individual con loss NaN** — todos entre 2.6 y 4.7,
razonable para un modelo recién cargado. Esto descarta un dato corrupto
puntual: la inestabilidad es del **backward/optimizer**, no de un clip
específico.

Causa real: el script no tenía `gradient clipping`, algo estándar en
fine-tuning con LoRA/bf16 precisamente para evitar que una explosión de
gradiente puntual (agravada por gradient checkpointing + bf16) corrompa
los pesos de forma permanente y silenciosa (NaN + cualquier operación =
NaN para siempre, no se autocorrige). Con `grad_accum=8` y ~160 ejemplos
antes del primer log, bastó con que un solo paso de acumulación tuviera
un gradiente inestable para que TODO el promedio reportado saliera NaN.

**Fix aplicado**: `torch.nn.utils.clip_grad_norm_(trainable_params,
max_norm=1.0)` antes de cada `opt.step()`, y si la norma resultante no es
finita, se saltea ese update por completo (no se aplica nada corrupto,
sólo se pierde ese paso de acumulación) en vez de aplicarlo a ciegas.
Reentrené desde cero (no había checkpoint válido que conservar).
Relanzado limpio, mismos hiperparámetros salvo el clipping agregado.
Voy a vigilar de cerca los primeros logs para confirmar que no vuelve a
pasar.

**Confirmado: primer log post-fix (step 20) dio `loss=1.4945`** — número
normal, ya no NaN. El gradient clipping resolvió el problema. Sigo
vigilando los próximos logs para confirmar que la loss desciende de
forma razonable y no vuelve a aparecer ningún "grad_norm no finito".

## 2026-08-22 23:29 — Chequeo automático (cron)

Proceso vivo (PID 61050, RSS ~80MB, corriendo desde 13:43). Progreso:
epoch 0, step 100/10070, loss=0.7294 (bajó de 1.4945 en step 20 a 0.6622
en step 80, con leve rebote a 0.7294 en step 100 — dentro de la
variabilidad esperada, no es tendencia sostenida al alza). Sin ningún
"grad_norm no finito" en el log — el fix de gradient clipping sigue
sosteniéndose. Checkpoints en step50 y step100, ambos guardados OK.
Disco: 33GB libres, sin problema. No reinicié nada. Sin novedades.
