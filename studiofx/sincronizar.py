"""Tiempos por palabra del guion: con Whisper (preciso) o estimados desde las pausas del audio (aproximado)."""
import difflib
import json
import os
import re
import subprocess
import unicodedata

import numpy as np


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", s)


def tokens_guion(guion):
    toks = []
    for si, seg in enumerate(guion["segmentos"]):
        paras = [p for p in seg["texto"].split("\n\n") if p.strip()]
        for p in paras:
            ws = p.split()
            for wi, w in enumerate(ws):
                last = wi == len(ws) - 1
                toks.append(dict(w=w, n=norm(w), seg=si, par_end=last,
                                 sent_end=last or bool(re.search(r'[.!?…]["”»)]*$', w))))
    return toks


def duracion(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def pausas(path, db=-38, minimo=0.45):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        "silencedetect=noise=%ddB:d=%s" % (db, minimo), "-f", "null", "-"],
                       capture_output=True, text=True)
    st = re.findall(r"silence_start: ([\d.]+)", r.stderr)
    du = re.findall(r"silence_duration: ([\d.]+)", r.stderr)
    return [(float(a), float(b)) for a, b in zip(st, du)]


def estimar(guion, audio):
    """Reparte las palabras del guion en el audio: cada pausa se empareja con un final de oracion (programacion
    dinamica) y entre pausas las palabras se reparten segun su longitud."""
    toks = tokens_guion(guion)
    D = duracion(audio)
    P = pausas(audio)
    w = np.array([max(1, len(t["n"])) + 3 for t in toks], float)
    cum = np.cumsum(w)
    W = cum[-1]
    durs = np.array([p[1] for p in P])
    S = np.array([p[0] for p in P]) - np.concatenate([[0], np.cumsum(durs)[:-1]])  # tiempo de voz acumulado
    V = D - durs.sum()
    B = np.array([i for i, t in enumerate(toks) if t["sent_end"]])
    par = np.array([toks[i]["par_end"] for i in B])
    wb = cum[B]
    xs = np.array([0.0, W])
    ys = np.array([0.0, V])
    resid = None
    for _ in range(5):
        sj = np.interp(wb, xs, ys)
        m, n = len(S), len(B)
        INF = 1e9
        cost = np.minimum(np.abs(sj[None, :] - S[:, None]), 8.0) - 0.8 * par[None, :]
        dp = np.full((m, n), INF)
        arg = np.zeros((m, n), int)
        dp[0] = cost[0]
        for i in range(1, m):
            pm = np.minimum.accumulate(dp[i - 1])
            pa = np.zeros(n, int)
            best, bi = INF, 0
            for j in range(n):
                if dp[i - 1][j] < best:
                    best, bi = dp[i - 1][j], j
                pm[j], pa[j] = best, bi
            dp[i, 1:] = cost[i, 1:] + pm[:-1]
            arg[i, 1:] = pa[:-1]
            dp[i, 0] = INF
        j = int(np.argmin(dp[-1]))
        match = [0] * m
        for i in range(m - 1, -1, -1):
            match[i] = j
            j = arg[i][j]
        xs = np.concatenate([[0.0], wb[match], [W]])
        ys = np.concatenate([[0.0], S, [V]])
        o = np.argsort(xs, kind="stable")
        xs, ys = xs[o], ys[o]
        resid = np.abs(np.interp(wb[match], xs, ys) - S)
    starts = np.interp(np.concatenate([[0], cum[:-1]]), xs, ys)
    ends = np.interp(cum, xs, ys)
    S0 = S
    pre = np.concatenate([[0], np.cumsum(durs)])
    out = []
    for t, s0, s1 in zip(toks, starts, ends):
        a = s0 + durs[:np.searchsorted(S0, s0 + 1e-6, side="right")].sum()
        b = s1 + durs[:np.searchsorted(S0, s1 - 1e-6, side="left")].sum()
        out.append(dict(w=t["w"], seg=t["seg"], t0=round(float(a), 3), t1=round(float(max(b, a + 0.05)), 3)))
    return dict(origen="estimado", duracion=D, tokens=out, aviso="Tiempos ESTIMADOS desde las pausas; usa Whisper para precision")


def transcribir(audio, modelo="small", idioma="es"):
    from faster_whisper import WhisperModel
    m = WhisperModel(modelo, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(audio, language=idioma, word_timestamps=True, vad_filter=True, beam_size=5)
    return [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]


def alinear(guion, palabras, D):
    """Empareja las palabras de Whisper con las del guion (difflib) e interpola las que no coinciden."""
    toks = tokens_guion(guion)
    g = [t["n"] for t in toks]
    wn = [norm(p[0]) for p in palabras]
    sm = difflib.SequenceMatcher(None, g, wn, autojunk=False)
    t0 = [None] * len(toks)
    t1 = [None] * len(toks)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            t0[a + k], t1[a + k] = palabras[b + k][1], palabras[b + k][2]
    idx = [i for i, v in enumerate(t0) if v is not None]
    if not idx:
        raise SystemExit("No pude emparejar el audio con el guion")
    xi = np.array(idx, float)
    t0i = np.interp(np.arange(len(toks)), xi, [t0[i] for i in idx])
    t1i = np.interp(np.arange(len(toks)), xi, [t1[i] for i in idx])
    out = [dict(w=t["w"], seg=t["seg"], t0=round(float(a), 3), t1=round(float(max(b, a + 0.05)), 3))
           for t, a, b in zip(toks, t0i, t1i)]
    return dict(origen="whisper", duracion=D, tokens=out, cobertura=round(len(idx) / len(toks), 3))


def buscar(tiempos, seg, frase, desde=0):
    """Indice del primer token (en el segmento) donde empieza `frase`; None si no aparece."""
    toks = tiempos["tokens"]
    f = [norm(x) for x in frase.split() if norm(x)]
    cand = [(i, norm(t["w"])) for i, t in enumerate(toks) if t["seg"] == seg and norm(t["w"])]
    seq = [c[1] for c in cand]
    for k in range(max(0, desde), len(seq) - len(f) + 1):
        if seq[k:k + len(f)] == f:
            return cand[k][0]
    return None
