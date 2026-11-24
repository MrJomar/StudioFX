"""Cambios manuales del usuario sobre el B-roll (sustituyen a 'arrastrar y soltar en DaVinci').

Se guardan en  <proyecto>\\STUDIOFX\\cambios.json  y se vuelven a aplicar cada vez que se arma el proyecto:
  [{"id": "B12-03", "original": "foto.jpg", "nuevo": "C:\\\\ruta\\\\otra.jpg" | null, "inicio": 12.5 | null}]
`id` identifica la pieza (B12-03 = bloque 12, pieza 3; H-02 = gancho, pieza 2); `original` evita aplicar un cambio a la
pieza equivocada si cambiaron los archivos de la carpeta.
"""
import json
import os

IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VID = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def ruta(raiz):
    return os.path.join(raiz, "STUDIOFX", "cambios.json")


def cargar(raiz):
    try:
        return json.load(open(ruta(raiz), encoding="utf-8"))
    except Exception:
        return []


def guardar(raiz, lista):
    os.makedirs(os.path.dirname(ruta(raiz)), exist_ok=True)
    json.dump(lista, open(ruta(raiz), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def poner(raiz, id, original, nuevo=None, inicio=None):
    """Agrega o reemplaza el cambio de una pieza. nuevo/inicio None = sin cambio de ese campo."""
    lst = [c for c in cargar(raiz) if c["id"] != id]
    prev = next((c for c in cargar(raiz) if c["id"] == id), {})
    lst.append(dict(id=id, original=original, nuevo=nuevo if nuevo is not None else prev.get("nuevo"),
                    inicio=inicio if inicio is not None else prev.get("inicio")))
    guardar(raiz, lst)


def quitar(raiz, id):
    guardar(raiz, [c for c in cargar(raiz) if c["id"] != id])


def mini_proyecto(proyecto, t0, t1, destino):
    """Recorta un proyecto a la ventana [t0, t1] (sin audio) para ver rapido como queda un momento."""
    esc = proyecto["escenas"]
    cur, starts = 0.0, []
    for i, s in enumerate(esc):
        tr = 0.0 if i == 0 else s.get("trans", 0.3)
        st = 0.0 if i == 0 else cur - tr
        cur = st + s["dur"]
        starts.append(st)
    ids = [i for i, s in enumerate(esc) if starts[i] + esc[i]["dur"] > t0 and starts[i] < t1]
    if not ids:
        raise ValueError("ese momento no tiene escenas")
    a, b = ids[0], ids[-1]
    off = starts[a]
    sub = []
    for k, i in enumerate(range(a, b + 1)):
        s = dict(esc[i])
        if k == 0:
            s.pop("transicion", None); s.pop("trans", None)
        sub.append(s)
    fin = starts[b] + esc[b]["dur"]
    ov = []
    for o in proyecto.get("overlays", []):
        if o["t"] + o["dur"] > off and o["t"] < fin:
            o2 = dict(o); o2["t"] = round(o["t"] - off, 3); ov.append(o2)
    p = {k: v for k, v in proyecto.items() if k not in ("escenas", "overlays", "audio")}
    p.update(escenas=sub, overlays=ov)
    json.dump(p, open(destino, "w", encoding="utf-8"), ensure_ascii=False)
    return off, fin
