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

**SLR61 terminado y sincronizado: 5,829 clips, 8.13 horas.** Manual,
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
