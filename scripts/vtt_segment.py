"""
Parsea un .vtt de auto-captions de YouTube (formato "rolling caption" con
timestamps por palabra tipo <00:00:01.120><c>palabra</c>) y lo corta en
segmentos de unos pocos segundos, cada uno con su texto. Los cues de
YouTube se repiten con el texto acumulado de a poco (scroll-style), así
que hay que deduplicar por timestamp creciente en vez de tomar cada cue
tal cual.

Uso como módulo: from vtt_segment import parse_words, make_segments
"""
import re

TS_RE = re.compile(r"<(\d\d):(\d\d):(\d\d)\.(\d\d\d)>")
CUE_START_RE = re.compile(
    r"^(\d\d):(\d\d):(\d\d)\.(\d\d\d) --> (\d\d):(\d\d):(\d\d)\.(\d\d\d)"
)


def _ts_to_s(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_words(vtt_text):
    """Devuelve lista de (word, timestamp_s) en orden, sin duplicados
    del estilo rolling-caption de YouTube."""
    words = []
    last_ts = -1.0
    cue_start = None
    for line in vtt_text.splitlines():
        m = CUE_START_RE.match(line)
        if m:
            cue_start = _ts_to_s(*m.groups()[:4])
            continue
        if "<c>" not in line and "<" not in line:
            continue
        # separar por tags de timestamp inline; la primera palabra de la
        # línea no tiene tag propio, usa el timestamp de inicio del cue
        parts = TS_RE.split(line)
        # parts alterna: [texto_antes_del_primer_tag, h,m,s,ms, texto, h,m,s,ms, texto, ...]
        first_chunk = parts[0]
        for w in first_chunk.replace("<c>", "").replace("</c>", "").split():
            if cue_start is not None and cue_start > last_ts:
                words.append((w, cue_start))
                last_ts = cue_start
        i = 1
        while i < len(parts) - 4:
            h, m_, s, ms = parts[i:i + 4]
            ts = _ts_to_s(h, m_, s, ms)
            text = parts[i + 4].replace("<c>", "").replace("</c>", "")
            for w in text.split():
                if ts > last_ts:
                    words.append((w, ts))
                    last_ts = ts
            i += 5
    return words


def make_segments(words, max_gap=1.2, max_dur=15.0, min_dur=2.0):
    """Agrupa la lista de (word, ts) en segmentos: corta en pausas largas,
    en fin de oración, o al llegar a max_dur. Devuelve lista de dicts
    {text, start, end}."""
    if not words:
        return []
    segments = []
    cur = [words[0]]
    for (w, ts), (w_next, ts_next) in zip(words, words[1:]):
        gap = ts_next - ts
        dur = ts_next - cur[0][1]
        ends_sentence = w.rstrip()[-1:] in ".?!" if w.rstrip() else False
        if gap > max_gap or dur > max_dur or (ends_sentence and dur > min_dur):
            # cur ya termina en (w, ts) por el append del final del loop anterior
            segments.append(cur)
            cur = []
        cur.append((w_next, ts_next))
    if cur:
        segments.append(cur)

    out = []
    for seg in segments:
        if not seg:
            continue
        text = " ".join(w for w, _ in seg)
        start = seg[0][1]
        end = seg[-1][1] + 0.4  # buffer para no cortar la última palabra
        if end - start < 0.5:
            continue
        out.append({"text": text, "start": start, "end": end})
    return out
