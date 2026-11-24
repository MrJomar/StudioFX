"""Armado automatico de escenas a partir de una carpeta (reemplaza el script de DaVinci)."""
import json
import os
import re
import subprocess

IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VID = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
EFECTOS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "zoom_in", "pan_up", "zoom_out", "pan_down"]
TRANS = ["fundido", "fundido", "whip", "fundido", "zoom", "fundido", "fundido", "glitch", "fundido", "destello"]


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def duracion(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def armar(carpeta, salida, audio=None, tema="xolo_oscuro", res=(1920, 1080), fps=30, dur_img=5.0, clip_max=4.0,
          segmentos=3, transicion=0.5, barra=None, intercalar=False):
    files = sorted((f for f in os.listdir(carpeta) if os.path.splitext(f)[1].lower() in IMG | VID), key=natural)
    if not files:
        raise SystemExit("No encontre imagenes ni videos en " + carpeta)
    units = []  # (tipo, src, inicio, dur, fija)
    for f in files:
        p = os.path.abspath(os.path.join(carpeta, f))
        if os.path.splitext(f)[1].lower() in IMG:
            units.append(dict(tipo="imagen", src=p, dur=dur_img, fija=False))
        else:
            total, t, n = duracion(p), 0.0, 0
            while total - t >= 0.8 and n < segmentos:
                d = min(clip_max, total - t)
                units.append(dict(tipo="clip", src=p, inicio=round(t, 3), dur=round(d, 3), fija=True))
                t += d; n += 1
            if n == 0:
                units.append(dict(tipo="clip", src=p, inicio=0.0, dur=max(0.8, total), fija=True))
    objetivo = duracion(audio) if audio else None
    sobre = lambda us: sum(u["dur"] for u in us) - transicion * (len(us) - 1)
    if objetivo:
        # usar TODO el material; solo repetir si cada imagen pasaria de 8 s, o recortar si bajaria de 3 s
        i = 0
        while True:
            imgs = [u for u in units if not u["fija"]]
            fijo = sum(u["dur"] for u in units if u["fija"])
            d = (objetivo + transicion * (len(units) - 1) - fijo) / len(imgs) if imgs else 5.0
            if imgs and d > 8.0 and i < 2000:
                units.append(dict(units[i % len(units)])); i += 1
            elif imgs and d < 3.0 and len(units) > 1:
                units.pop()
            elif not imgs and sobre(units) < objetivo - 1.0 and i < 2000:
                units.append(dict(units[i % len(units)])); i += 1
            else:
                break
        imgs = [u for u in units if not u["fija"]]
        if imgs:
            for u in imgs:
                u["dur"] = round(min(9.0, max(2.5, d)), 3)
        resto = objetivo - sobre(units)
        if abs(resto) > 0.05:  # ultimo ajuste en la ultima escena de imagen (o la ultima)
            tgt = imgs[-1] if imgs else units[-1]
            tgt["dur"] = round(max(1.0, tgt["dur"] + resto), 3)
    escenas, n_img = [], 0
    for i, u in enumerate(units):
        e = dict(tipo=u["tipo"], src=u["src"], dur=u["dur"])
        if u["tipo"] == "imagen":
            e["efecto"] = EFECTOS[n_img % len(EFECTOS)]
            n_img += 1
        else:
            e["inicio"] = u["inicio"]
        if i > 0:
            e["transicion"] = TRANS[i % len(TRANS)]
            e["trans"] = transicion
        escenas.append(e)
    proyecto = dict(nombre=os.path.basename(os.path.abspath(carpeta)), resolucion=list(res), fps=fps, tema=tema,
                    transicion=transicion, clip_max=clip_max, escenas=escenas, overlays=[])
    if barra:
        proyecto["barra_superior"] = barra
    if audio:
        proyecto["audio"] = os.path.abspath(audio)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(proyecto, f, ensure_ascii=False, indent=2)
    tot = sobre(units)
    return dict(escenas=len(escenas), imagenes=n_img, clips=len(escenas) - n_img, duracion=round(tot, 1),
                audio=round(objetivo, 1) if objetivo else None)
