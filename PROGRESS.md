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
