"""Lista de proyectos de StudioFX y su estado (sin interfaz: la usa la ventana y se puede probar sola)."""
import json
import os
import re
import shutil

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTA = os.path.join(RAIZ, "proyectos.json")
IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VID = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def cargar_lista():
    try:
        return [p for p in json.load(open(LISTA, encoding="utf-8")) if isinstance(p, str)]
    except Exception:
        return []


def _guardar(lst):
    json.dump(lst, open(LISTA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def agregar(ruta):
    ruta = os.path.normpath(ruta)
    lst = [p for p in cargar_lista() if os.path.normcase(p) != os.path.normcase(ruta)]
    lst.insert(0, ruta)
    _guardar(lst)


def quitar(ruta):
    _guardar([p for p in cargar_lista() if os.path.normcase(p) != os.path.normcase(os.path.normpath(ruta))])


def es_guion(ruta):
    try:
        d = json.load(open(ruta, encoding="utf-8"))
    except Exception:
        return None
    if isinstance(d, dict) and {"segmentos", "xolo_estudio", "hook_visual"} <= set(d):
        return d
    return None


def buscar_guion(raiz):
    for dp, dn, fn in os.walk(raiz):
        if dp[len(raiz):].count(os.sep) > 2 or os.path.basename(dp) in ("STUDIOFX", "__pycache__"):
            dn[:] = []
            continue
        for f in sorted(fn):
            if f.lower().endswith(".json") and not f.lower().startswith("marcadores"):
                p = os.path.join(dp, f)
                if es_guion(p):
                    return p
    return None


def bloques_del_guion(guion):
    out = []
    for s in guion.get("segmentos", []):
        m = re.match(r"^(\d+)\.\s", s.get("nombre", ""))
        if s.get("tipo") == "bloque" and m:
            out.append((int(m.group(1)), s["nombre"]))
    return out


def _contar(carpeta):
    f = v = 0
    if carpeta and os.path.isdir(carpeta):
        for x in os.listdir(carpeta):
            e = os.path.splitext(x)[1].lower()
            f += e in IMG; v += e in VID
    return f, v


def estado(ruta):
    """Resumen del proyecto: que tiene, que le falta y en que etapa va."""
    r = dict(ruta=ruta, nombre=os.path.basename(ruta.rstrip("\\/")), existe=os.path.isdir(ruta))
    if not r["existe"]:
        r.update(etapa="No encontrado", color="rojo", faltan=["La carpeta ya no existe"], bloques=[], pendientes=[])
        return r
    g = buscar_guion(ruta)
    r["guion"] = g
    gd = es_guion(g) if g else None
    r["titulo"] = (gd or {}).get("titulo") or r["nombre"]
    au = None
    for dp, dn, fn in os.walk(ruta):
        if os.path.basename(dp) == "STUDIOFX":
            dn[:] = []; continue
        if "audio_completo.wav" in [x.lower() for x in fn]:
            au = os.path.join(dp, "audio_completo.wav"); break
    r["audio"] = au
    r["marcadores"] = any(f.lower().startswith("marcadores") and f.lower().endswith(".json")
                          for dp, dn, fn in os.walk(os.path.join(ruta, "Audio")) for f in fn) if os.path.isdir(os.path.join(ruta, "Audio")) else False
    ad = os.path.dirname(au) if au else os.path.join(ruta, "Audio")
    from .sincronizar import candidatos_transcripcion
    c = candidatos_transcripcion(ad)
    r["transcripcion"] = c[0] if c else None
    carp = {}
    for d in os.listdir(ruta):
        m = re.match(r"^(\d+)\.\s", d)
        if m and os.path.isdir(os.path.join(ruta, d)):
            carp[int(m.group(1))] = os.path.join(ruta, d)
    bl = []
    for n, nombre in bloques_del_guion(gd) if gd else []:
        f, v = _contar(carp.get(n))
        bl.append(dict(n=n, nombre=nombre, carpeta=carp.get(n), fotos=f, videos=v))
    r["bloques"] = bl
    sd = os.path.join(ruta, "STUDIOFX")
    r["sincronizado"] = os.path.exists(os.path.join(sd, "tiempos.json"))
    r["armado"] = os.path.exists(os.path.join(sd, "proyecto_fx.json"))
    r["videos_finales"] = sorted([os.path.join(sd, x) for x in os.listdir(sd) if x.lower().endswith(".mp4")]) if os.path.isdir(sd) else []
    r["renderizado"] = r["videos_finales"][-1] if r["videos_finales"] else None
    try:
        pend = json.load(open(os.path.join(sd, "pendientes.json"), encoding="utf-8"))
    except Exception:
        pend = []
    r["pendientes"] = pend
    faltan = []
    if not g:
        faltan.append("Falta el guion JSON")
    if not au:
        faltan.append("Falta Audio\\audio_completo.wav")
    sin = [b["n"] for b in bl if b["carpeta"] is None]
    if sin:
        faltan.append("Sin carpeta de fotos: bloque(s) " + ", ".join(map(str, sin)))
    r["faltan"] = faltan
    vis = [p for p in pend if p["tipo"] in ("visual", "foto")]
    r["n_visuales_sin_foto"] = len(vis)
    if faltan:
        r["etapa"], r["color"] = "Falta material", "amarillo"
    elif r["renderizado"]:
        r["etapa"], r["color"] = "Renderizado", "verde"
    elif r["armado"]:
        r["etapa"], r["color"] = "Armado", "azul"
    elif r["sincronizado"]:
        r["etapa"], r["color"] = "Sincronizado", "azul"
    else:
        r["etapa"], r["color"] = "Listo para empezar", "gris"
    return r


def parece_proyecto(d):
    """True si la carpeta ya es un proyecto (tiene Audio, STUDIOFX o carpetas de bloque numeradas)."""
    if not os.path.isdir(d):
        return False
    return any(x in ("Audio", "STUDIOFX") or (re.match(r"^\d+\.\s", x) and os.path.isdir(os.path.join(d, x))) for x in os.listdir(d))


def crear(carpeta_padre, nombre, guion_json=None):
    """Prepara la carpeta del proyecto. Si la carpeta elegida YA es un proyecto, se usa tal cual (no se crea otra dentro)."""
    ruta = carpeta_padre if parece_proyecto(carpeta_padre) else os.path.join(carpeta_padre, nombre)
    os.makedirs(os.path.join(ruta, "Audio"), exist_ok=True)
    if guion_json:
        poner_guion(ruta, guion_json)
    agregar(ruta)
    return ruta


def poner_guion(ruta, guion_json):
    """Copia el guion JSON al proyecto y crea las carpetas de fotos que falten."""
    gd = es_guion(guion_json)
    if gd is None:
        raise ValueError("Ese archivo no es un guion de Xolo Estudio (le faltan segmentos / xolo_estudio / hook_visual).")
    dest = os.path.join(ruta, os.path.basename(guion_json))
    if os.path.normcase(os.path.abspath(guion_json)) != os.path.normcase(os.path.abspath(dest)):
        shutil.copy2(guion_json, dest)
    existentes = {int(m.group(1)) for d in os.listdir(ruta) if (m := re.match(r"^(\d+)\.\s", d)) and os.path.isdir(os.path.join(ruta, d))}
    for n, nombre in bloques_del_guion(gd):
        if n not in existentes:
            os.makedirs(os.path.join(ruta, re.sub(r'[<>:"/\\|?*]', "", nombre)), exist_ok=True)
    return gd


def guardar_foto_visual(ruta, bloque, id_fx, archivo):
    """Copia una foto a la carpeta del bloque con el nombre del visual (fx_11_02.jpg), que es como StudioFX la reconoce."""
    est = estado(ruta)
    b = next((b for b in est["bloques"] if b["n"] == bloque and b["carpeta"]), None)
    if b is None:
        raise ValueError("No encuentro la carpeta del bloque %s" % bloque)
    ext = os.path.splitext(archivo)[1].lower() or ".jpg"
    for e in IMG:
        viejo = os.path.join(b["carpeta"], id_fx + e)
        if os.path.exists(viejo):
            os.remove(viejo)
    dest = os.path.join(b["carpeta"], id_fx + ext)
    shutil.copy2(archivo, dest)
    return dest
