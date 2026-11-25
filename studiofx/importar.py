"""Importa un proyecto de Xolo Explorador (guion JSON + tiempos + marcadores + carpetas de B-roll) y arma el proyecto StudioFX."""
import json
import math
import os
import re
import subprocess

from .sincronizar import buscar

IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VID = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
EFECTOS = {"zoom_suave": ["zoom_in", "zoom_out"], "paneo_horizontal": ["pan_left", "pan_right"],
           "paneo_vertical": ["pan_up", "pan_down"], "estatico": ["static"],
           "automatico": ["zoom_in", "pan_right", "zoom_out", "pan_left"]}
INTENS = {"impacto": 0.20, "dinamico": 0.14, "tranquilo": 0.09}
TR_RITMO = {"impacto": ("zoom", 0.30), "dinamico": ("fundido", 0.30), "tranquilo": ("fundido", 0.45)}
LENTE = ("xolo_lens", 10 / 30.0)


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def dur_video(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 4.0


def carpetas_bloques(raiz):
    out = {}
    for d in os.listdir(raiz):
        m = re.match(r"^(\d+)\.\s", d)
        if m and os.path.isdir(os.path.join(raiz, d)):
            out[int(m.group(1))] = os.path.join(raiz, d)
    return out


def nombre_corto(nombre):
    n = re.sub(r"^\d+\.\s*", "", nombre)
    return re.split(r"\s+[—–-]\s+", n)[0].strip()


def municipio(nombre):
    p = re.split(r"\s+[—–]\s+", nombre)
    return p[1].strip() if len(p) > 1 else ""


class Pool:
    """Material de una carpeta de bloque."""

    def __init__(self, carpeta, saltar_ini=12.0, solo_imagenes=True):
        self.imgs, self.vids = [], []
        self.videos_ignorados = 0
        self.reservados = {}
        if carpeta and os.path.isdir(carpeta):
            for f in sorted(os.listdir(carpeta), key=natural):
                e = os.path.splitext(f)[1].lower()
                p = os.path.join(carpeta, f)
                ident = os.path.splitext(f)[0]
                if e in IMG:
                    self.imgs.append(dict(p=p, id=ident, usos=0))
                elif e in VID and solo_imagenes:
                    self.videos_ignorados += 1
                elif e in VID:
                    d = dur_video(p)
                    # los videos descargados suelen traer intro con titulos: se salta el inicio y el final
                    s0 = saltar_ini if d > 60 else (6.0 if d > 30 else (2.0 if d > 12 else 0.0))
                    s1 = 5.0 if d > 60 else (2.0 if d > 20 else 0.0)
                    self.vids.append(dict(p=p, id=ident, dur=d, pos=s0, fin=max(s0 + 1.0, d - s1), usos=0, s0=s0))

    def por_id(self, ident):
        for it in self.imgs + self.vids:
            if it["id"].lower().startswith(ident.lower()):
                return it
        return None

    def ventana(self, v, largo):
        """Siguiente ventana de `largo` s de un video sin solapar; None si ya no hay."""
        if v["pos"] + 1.0 > v["fin"]:
            return None
        ini = v["pos"]
        largo = min(largo, v["fin"] - ini)
        v["pos"] = ini + largo
        v["usos"] += 1
        return round(ini, 3), round(largo, 3)

    def reiniciar_video(self, v):
        v["pos"] = v["s0"]


def _secuencia(k, m):
    """Orden de k imagenes y m clips con los clips repartidos parejo (Bresenham)."""
    seq, acc, n = [], 0, k + m
    for _ in range(n):
        acc += m
        if acc >= n:
            seq.append("c"); acc -= n
        else:
            seq.append("i")
    return seq


_PEND = []
IDEAL_FOTO = 4.0      # s por foto en el ritmo documental de referencia (cambio de composicion cada 3-6 s)
DETALLES = [(0.30, 0.35), (0.72, 0.40), (0.50, 0.72), (0.25, 0.70), (0.76, 0.70), (0.50, 0.30)]


def _solo_fotos(pool, T, avisos, etiqueta):
    I = pool.imgs
    n = max(1, int(round(T / IDEAL_FOTO)))
    d = T / n
    if len(I) < n:
        avisos.append("%s: tiene %d foto(s) y para este ritmo conviene ~%d; las demas toman de nuevo tus fotos con un acercamiento a un detalle (agrega %d foto(s) para que se vea mejor)" % (etiqueta, len(I), n, n - len(I)))
    _PEND.append(dict(tipo="bloque", etiqueta=etiqueta, tiene=len(I), ideal=n, faltan=max(0, n - len(I)), duracion=round(T, 1)))
    piezas = []
    for j in range(n):
        it = I[j % len(I)]; it["usos"] += 1
        ciclo = j // len(I)
        pz = dict(tipo="imagen", media=it, dur=d)
        if ciclo:
            pz["foco"] = DETALLES[(ciclo - 1 + j) % len(DETALLES)]; pz["zoom_base"] = 1.45
        piezas.append(pz)
    return piezas


def plan_bloque(pool, T, avisos, etiqueta):
    """Lista de piezas [(tipo, media, ventana, dur)] que llena T segundos: TODAS las imagenes primero (<=5 s),
    clips de <=4 s repartidos entre ellas, y nunca dos clips seguidos del mismo video madre."""
    I, V = pool.imgs, pool.vids
    if not I and not V:
        avisos.append("%s: carpeta sin fotos" % etiqueta)
        _PEND.append(dict(tipo="bloque", etiqueta=etiqueta, tiene=0, ideal=max(1, int(round(T / IDEAL_FOTO))), faltan=max(1, int(round(T / IDEAL_FOTO))), duracion=round(T, 1)))
        return []
    if I and not V:
        return _solo_fotos(pool, T, avisos, etiqueta)
    # 1) imagenes
    if I:
        d = 5.0 if len(I) * 5.0 <= T else max(2.5, T / len(I))
        k = min(len(I), int(T / d + 1e-6))
        if k < len(I):
            avisos.append("%s: no caben %d foto(s) en %.0f s (minimo 2.5 s por foto)" % (etiqueta, len(I) - k, T))
    else:
        d, k = 0.0, 0
    R = T - k * d
    # 2) clips para el resto
    if V and R >= 1.5:
        m = max(1, int(round(R / 3.6)))
        while R / m > 4.0:
            m += 1
        seg = R / m
    elif R > 0 and k:
        d = T / k; R = 0; m = 0; seg = 0   # lo que sobra se reparte entre las fotos (no mas de 8 s cada una)
        if d > 8.0 and I:
            n = int(math.ceil(T / 6.5))
            avisos.append("%s: pocas fotos y ningun video; se repiten %d foto(s)" % (etiqueta, n - k))
            k, d = n, T / n
    elif not k:
        m = max(1, int(math.ceil(T / 4.0))); seg = T / m
    else:
        m, seg = 0, 0
    seq = _secuencia(k, m)
    piezas, ii, ultima_fuente = [], 0, None
    cont = dict(reuso=0, seguidos=0)
    for tipo in seq:
        if tipo == "i":
            it = I[ii % len(I)]; ii += 1; it["usos"] += 1
            piezas.append(dict(tipo="imagen", media=it, dur=d)); ultima_fuente = None
        else:
            cand = sorted(V, key=lambda v: (v["p"] == ultima_fuente, v["usos"]))
            elegido = None
            for v in cand:
                if v["p"] == ultima_fuente and len(V) > 1:
                    continue
                w = pool.ventana(v, seg)
                if w is None:
                    pool.reiniciar_video(v)
                    cont["reuso"] += 1
                    w = pool.ventana(v, seg)
                if w:
                    elegido = (v, w); break
            if elegido is None:
                v = V[0]; pool.reiniciar_video(v); w = pool.ventana(v, seg); elegido = (v, w)
            v, w = elegido
            if v["p"] == ultima_fuente:
                cont["seguidos"] += 1
            piezas.append(dict(tipo="clip", media=v, ventana=w, dur=w[1])); ultima_fuente = v["p"]
    if cont["reuso"]:
        avisos.append("%s: el material no alcanza para %.0f s; se repiten %d recorte(s) de video (agrega mas fotos o videos a la carpeta)" % (etiqueta, T, cont["reuso"]))
    if cont["seguidos"]:
        avisos.append("%s: %d vez(ces) quedan 2 recortes seguidos del mismo video porque la carpeta tiene un solo video y pocas fotos" % (etiqueta, cont["seguidos"]))
    # ajusta la ultima pieza para que sumen exacto T
    suma = sum(p["dur"] for p in piezas)
    if piezas:
        piezas[-1]["dur"] += T - suma
        if piezas[-1]["tipo"] == "clip":
            piezas[-1]["ventana"] = (piezas[-1]["ventana"][0], piezas[-1]["ventana"][1])
    return piezas


def importar(raiz, guion, tiempos, salida, audio=None, tema="xolo_oscuro", res=(1920, 1080), fps=30, hasta=None,
             marcadores=None, saltar_ini=12.0, etiqueta_cap="LUGAR", cambios=None, solo_imagenes=True, primer_bloque=False):
    toks = tiempos["tokens"]
    D = tiempos["duracion"]
    carp = carpetas_bloques(raiz)
    avisos = []
    bloques = {int(b["numero"]): b for b in guion["xolo_estudio"]["bloques"]}
    seg_de = {}
    for si, s in enumerate(guion["segmentos"]):
        m = re.match(r"^(\d+)\.", s.get("nombre", "") or "")
        if s["tipo"] == "bloque" and m:
            seg_de[int(m.group(1))] = si
    seg_ini, seg_fin = {}, {}
    for t in toks:
        seg_ini.setdefault(t["seg"], t["t0"]); seg_fin[t["seg"]] = t["t1"]
    orden = sorted(seg_de, key=lambda n: seg_ini[seg_de[n]])
    # ---- limites de bloque: marcadores de DaVinci si existen; si no, fin de la voz previa + 0.4 s
    marc = {}
    if marcadores:
        for b in marcadores.get("blocks", []):
            m = re.match(r"^(\d+)\.", b["name"])
            if m:
                marc[int(m.group(1))] = (float(b["start_seconds"]), float(b["end_seconds"]))
    ini, fin = {}, {}
    for i, n in enumerate(orden):
        si = seg_de[n]
        if n in marc:
            ini[n], fin[n] = marc[n]
        else:
            prev = seg_fin.get(si - 1, 0.0)
            ini[n] = prev + 0.4
            fin[n] = ini[n]
    if not marc:
        for i, n in enumerate(orden):
            fin[n] = ini[orden[i + 1]] if i + 1 < len(orden) else D
    else:
        fin[orden[-1]] = D
    avisos_marc = "marcadores_davinci.json" if marc else "estimados de la voz (no hay marcadores)"
    if primer_bloque and not hasta:
        hasta = round(fin[orden[0]], 2)      # hook + primer bloque
    _PEND.clear()
    pools = {n: Pool(carp.get(n), saltar_ini, solo_imagenes) for n in bloques}
    for n in bloques:
        if n not in carp:
            avisos.append("Bloque %d: no encontre su carpeta de B-roll" % n)
    for n, b in bloques.items():   # archivos con el id de un efecto o de una toma se reservan para ellos
        for x in b["efectos"]:
            it = pools[n].por_id(x["id"])
            if it and it in pools[n].imgs:
                pools[n].imgs.remove(it); pools[n].reservados[x["id"]] = it
    # ---- planes de B-roll por bloque
    piezas_t = []   # (t_inicio, pieza, bloque, ritmo, mov, es_inicio)
    for n in orden:
        T = fin[n] - ini[n]
        pl = plan_bloque(pools[n], T, avisos, "Bloque %d" % n)
        si = seg_de[n]
        brs = []
        for br in bloques[n]["broll"]:
            i = buscar(tiempos, si, br["anchor_text"])
            if i is not None:
                brs.append((toks[i]["t0"] - 0.12, br))
        brs.sort(key=lambda x: x[0])
        t = ini[n]
        for j, p in enumerate(pl):
            gob = None
            for tt, br in brs:
                if tt <= t + 0.01:
                    gob = br
            gob = gob or (brs[0][1] if brs else dict(ritmo="dinamico", movimiento="automatico"))
            piezas_t.append(dict(t=t, p=p, n=n, ritmo=gob.get("ritmo", "dinamico"), mov=gob.get("movimiento", "automatico"),
                                 inicio_bloque=(j == 0), id="B%02d-%02d" % (n, j + 1)))
            t += p["dur"]
    # ---- gancho: usa lo que sobra de cada carpeta
    hook = []
    for h in guion.get("hook_visual", []):
        i = buscar(tiempos, 0, h["frase"].strip())
        if i is None:
            avisos.append("gancho: no encontre «%s»" % h["frase"].strip()); continue
        hook.append((toks[i]["t0"], int(h["bloque_numero"])))
    hook.sort()
    t_fin_hook = ini[orden[0]]
    if hook:
        hook[0] = (0.0, hook[0][1])
    ghook, ult = [], None
    for k, (t, n) in enumerate(hook):
        t1 = hook[k + 1][0] if k + 1 < len(hook) else t_fin_hook
        L = t1 - t
        trozos = 2 if L > 4.5 else 1
        for z in range(trozos):
            c = _pieza_gancho(pools[n], L / trozos, ult)
            if c is None:
                avisos.append("gancho: la carpeta del bloque %d no tiene material" % n); continue
            ghook.append(dict(t=t + z * L / trozos, p=c, n=n, ritmo="impacto", mov="automatico", inicio_bloque=False,
                              id="H-%02d" % (len(ghook) + 1)))
            ult = c["media"]["p"]
    todas = sorted(ghook + piezas_t, key=lambda e: e["t"])
    _aplicar_cambios(todas, cambios or [], avisos, saltar_ini)
    if hasta:
        todas = [e for e in todas if e["t"] < hasta]
    # ---- escenas (cada una dura hasta la siguiente + el solape de la transicion)
    fin_total = hasta if hasta else D + 0.2
    escenas, cuenta = [], {}
    def trans_de(x):
        if x["inicio_bloque"]:
            return LENTE
        return TR_RITMO.get(x["ritmo"], TR_RITMO["dinamico"])
    # la transicion se CENTRA en el corte: la escena nueva empieza media transicion antes del corte
    starts = [0.0 if i == 0 else max(0.0, e["t"] - trans_de(e)[1] / 2) for i, e in enumerate(todas)]
    for i, e in enumerate(todas):
        p = e["p"]
        if i + 1 < len(todas):
            dur = starts[i + 1] - starts[i] + trans_de(todas[i + 1])[1]
        else:
            dur = fin_total - starts[i]
        sc = dict(tipo=p["tipo"], src=p["media"]["p"], dur=round(dur, 3), id=e["id"], bloque=e["n"])
        if p["tipo"] == "imagen":
            # nunca "estatico": una foto sin movimiento se ve muerta; se usa un zoom lento
            efs = EFECTOS["zoom_suave"] if e["mov"] == "estatico" else EFECTOS.get(e["mov"], EFECTOS["automatico"])
            c = cuenta.get(e["n"], 0); cuenta[e["n"]] = c + 1
            sc["efecto"] = efs[c % len(efs)]
            sc["intensidad"] = 0.08 if e["mov"] == "estatico" else INTENS.get(e["ritmo"], 0.14)
            if p.get("foco"):
                sc["foco"], sc["zoom_base"] = list(p["foco"]), p.get("zoom_base", 1.45)
        else:
            sc["inicio"] = p["ventana"][0]
        if i > 0:
            tt = trans_de(e)
            sc["transicion"], sc["trans"] = tt[0], round(tt[1], 4)
        escenas.append(sc)
    # ---- overlays: capitulos, municipio, efectos, mascota
    ov = []
    for n in orden:
        si = seg_de[n]
        gap = max(0.0, seg_ini[si] - ini[n])
        dcap = min(5.5, max(3.2, gap - 0.1))
        ov.append(dict(tipo="titulo_capitulo", t=round(ini[n] + 0.45, 3), dur=round(dcap, 2), etiqueta=etiqueta_cap,
                       numero=str(n), titulo=nombre_corto(bloques[n]["nombre"]), _pri=9))
        mu = municipio(bloques[n]["nombre"])
        if mu:
            ov.append(dict(tipo="etiqueta_sup", t=round(ini[n] + 0.45 + dcap + 0.1, 3), dur=3.5, texto=(mu + " · JALISCO").upper(), _pri=3))
        for fx in bloques[n]["efectos"]:
            i = buscar(tiempos, si, fx["anchor_text"])
            if i is None:
                avisos.append("%s: no encontre el ancla del efecto" % fx["id"]); continue
            o = _efecto(fx, pools[n], toks[i]["t0"], avisos)
            if o:
                ov.append(o)
    for fx in (guion.get("hook_efectos") or guion.get("xolo_estudio", {}).get("hook_efectos", [])):
        i = buscar(tiempos, 0, fx["anchor_text"])
        if i is None:
            avisos.append("%s: no encontre el ancla del efecto del gancho" % fx["id"]); continue
        o = _efecto(fx, None, toks[i]["t0"], avisos)
        if o:
            ov.append(o)
    ult = seg_de[orden[-1]]
    i = buscar(tiempos, ult, "Cuéntanos y suscríbete")
    if i is not None:
        ov.append(dict(tipo="mascota", t=round(toks[i]["t0"] - 0.3, 3), dur=min(6.0, D + 0.2 - toks[i]["t0"]),
                       pose="feliz", pos="der", tam=0.46, movimiento="rebote", _pri=1))
    ov += _etiquetas_fotos(todas, bloques, pools, ini, avisos)
    ov = _sin_choques(ov, avisos)
    ov = _subtitulos_en_huecos(ov, guion, tiempos, ini, fin, orden, seg_de)
    if hasta:
        ov = [o for o in ov if o["t"] < hasta]
    ov = _satelitales(ov, os.path.join(raiz, "STUDIOFX", "mapas_cache"), avisos, res[0])
    proyecto = dict(nombre=guion.get("titulo", "Xolo Explorador"), resolucion=list(res), fps=fps, tema=tema,
                    transicion=0.3, clip_max=60.0, barra_superior=(guion.get("titulo") or "XOLO EXPLORADOR").upper()[:64], escenas=escenas, overlays=ov)
    if audio:
        proyecto["audio"] = audio
    # ---- control: la duracion que va a tener el render DEBE coincidir con lo planeado
    cur = 0.0
    for i, s in enumerate(escenas):
        tr = 0.0 if i == 0 else s.get("trans", 0.3)
        st = 0.0 if i == 0 else cur - tr
        cur = st + s["dur"]
    esperado = fin_total
    if abs(cur - esperado) > 0.1:
        avisos.append("DESFASE: el render duraria %.2f s y se esperaban %.2f s" % (cur, esperado))
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    json.dump(_PEND, open(os.path.join(os.path.dirname(salida), "pendientes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if hasta:
        proyecto["hasta"] = hasta
    json.dump(proyecto, open(salida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return dict(escenas=len(escenas), overlays=len(ov), duracion_render=round(cur, 2), esperada=round(esperado, 2),
                limites=avisos_marc, avisos=avisos, origen=tiempos.get("origen"),
                imagenes=sum(1 for s in escenas if s["tipo"] == "imagen"), clips=sum(1 for s in escenas if s["tipo"] == "clip"))


def _pieza_gancho(pool, largo, ultima):
    """Elige lo menos usado de la carpeta, sin repetir el video madre anterior si hay otro."""
    cands = [("imagen", x) for x in pool.imgs] + [("clip", x) for x in pool.vids]
    cands += [("imagen", x) for x in pool.reservados.values()] if not cands else []
    if not cands:
        return None
    cands.sort(key=lambda c: (c[1]["p"] == ultima, c[1]["usos"], 0 if c[0] == "clip" else 1))
    tipo, it = cands[0]
    it["usos"] += 1
    if tipo == "imagen":
        return dict(tipo="imagen", media=it, dur=largo)
    w = pool.ventana(it, min(largo, 4.0))
    if w is None:
        pool.reiniciar_video(it); w = pool.ventana(it, min(largo, 4.0))
    return dict(tipo="clip", media=it, ventana=w, dur=largo)


def _efecto(fx, pool, t, avisos):
    k = fx["kind"]
    dur = float(fx.get("duration", 3.5))
    base = dict(t=round(t, 3), dur=dur, _id=fx["id"], _pri=5)
    d = fx.get("datos") or {}
    k = d.get("kind", k)
    asset = (pool.por_id(fx["id"]) or pool.reservados.get(fx["id"])) if pool else None
    # si el efecto pide imagen y no esta, se usa su version sin imagen (o se avisa)
    k = ALIAS.get(k, k)
    if k in ("documento", "foto_cine") and not asset:
        _PEND.append(dict(tipo="visual", id=fx["id"], efecto=k, t=round(t, 1), pedir=fx.get("asset_hint", ""),
                          archivo=fx["id"] + ".jpg", obligatoria=fx.get("asset_requirement") == "required",
                          bloque=int(fx["id"].split("_")[1]) if fx["id"].count("_") >= 2 and fx["id"].split("_")[1].isdigit() else None))
        if fx.get("asset_requirement") == "required":
            avisos.append("%s (%s): falta la imagen «%s». Pon un archivo llamado %s.jpg en la carpeta del bloque." % (
                fx["id"], k, fx.get("asset_hint", ""), fx["id"]))
        if fx.get("sin_imagen"):
            return _desde(dict(fx["sin_imagen"], duration=dur), base, fx["sin_imagen"].get("kind", "tarjeta"))
        base["_pri"] = 1
    if k in ("documento", "foto_cine") and asset:
        return dict(base, tipo="polaroid", src=asset["p"], pie=fx["title"])
    src = dict(fx)
    src.update(d)
    return _desde(src, base, k)


ALIAS = {"numero": "cifra", "cita": "frase", "misterio": "frase", "sello_editorial": "sello", "expediente": "documento",
         "marco": "documento", "foto_lateral": "documento", "revelado": "documento", "capas": "documento"}


def _desde(f, base, k):
    k = ALIAS.get(k, k)
    try:
        return _desde2(f, base, k)
    except (KeyError, IndexError, TypeError, ValueError):
        # datos incompletos: se cae a una tarjeta sencilla con lo que si hay
        if f.get("title"):
            return dict(base, tipo="lower_third", etiqueta=(f.get("etiqueta") or "DATO"), titulo=f["title"], sub=f.get("subtitle", ""), color="azul", _pri=3)
        return None


def _desde2(f, base, k):
    ti, su = f.get("title", ""), f.get("subtitle", "")
    if k == "mapa":
        return dict(base, tipo="mapa_ubicacion", titulo=ti, municipios=f["municipios"], lon=f["lon"], lat=f["lat"],
                    lugar=f.get("lugar", ""), foco_km=f.get("foco_km", 9), foco_sat_km=f.get("foco_sat_km", 1.5), modo="oscuro", _pri=7)
    if k == "cifra":
        return dict(base, tipo="dato_grande", valor=ti, texto=su, sub=f.get("etiqueta", ""), contar=bool(f.get("contar", False)), _pri=6)
    if k == "fecha":
        return dict(base, tipo="dato_grande", valor=ti, texto=su, contar=False, _pri=6)
    if k == "tarjeta":
        return dict(base, tipo="lower_third", etiqueta=f.get("etiqueta", "DATO"), titulo=ti, sub=su, color=f.get("color", "azul"))
    if k == "etiqueta":
        return dict(base, tipo="etiqueta_sup", texto=ti.upper())
    if k == "sello":
        return dict(base, tipo="sello", sello=ti.upper(), sub=su)
    if k == "frase":
        pal = f.get("destacar") or [w for w in re.split(r"\s+", ti) if len(w) > 5][:2]
        return dict(base, tipo="frase_destacada", texto=ti, destacar=pal, _pri=6)
    if k in ("revision", "lista"):
        its = [dict(texto=a, tipo=b) for a, b in f["items"]]
        return dict(base, tipo="checklist", titulo=f.get("titulo", ""), items=its, sobre_foto=True, _pri=6)
    if k in ("versiones", "comparacion"):
        fich = f.get("fichas")
        if not fich:
            partes = [x.strip() for x in su.split("/")]
            fich = [(partes[0], "rojo", "", ""), (partes[1] if len(partes) > 1 else "", "azul", "", "")]
        return dict(base, tipo="fichas_versiones", titulo=f.get("titulo", ti),
                    fichas=[dict(etiqueta=a, color=b, valor=c, texto=d) for a, b, c, d in fich], _pri=6)
    if k in ("linea", "cronologia"):
        ev = f.get("eventos")
        if not ev:
            ev = [(str(i + 1), p.strip()) for i, p in enumerate(re.split(r"→|->", su))]
        return dict(base, tipo="linea_tiempo", titulo=f.get("titulo", ti), sobre_foto=True,
                    eventos=[dict(fecha=a, texto=b) for a, b in ev], _pri=6)
    if k in ("palabra", "palabra_grande"):
        return dict(base, tipo="palabra_grande", texto=ti, kicker=f.get("etiqueta", ""), sub=su, fondo=f.get("fondo", "azul"), _pri=5)
    if k == "libro":
        return dict(base, tipo="tarjeta_libro", autor=f.get("autor", ""), titulo=ti, anio=f.get("anio", ""), color=f.get("color", "rojo"),
                    pos=f.get("pos", "der"), _pri=4)
    if k == "documento":
        return dict(base, tipo="lower_third", etiqueta="DOCUMENTO", titulo=ti, sub=su, color="dorado", _pri=1)
    return None


GRANDES = {"mapa_ubicacion", "fichas_versiones", "linea_tiempo", "checklist", "revision_honesta", "frase_destacada",
           "dato_grande", "polaroid", "titulo_capitulo", "palabra_grande"}


def _carril(tipo):
    if tipo in GRANDES:
        return "todo"
    if tipo in ("lower_third", "sello"):
        return "bajo"
    if tipo == "etiqueta_sup":
        return "alto"
    return "libre"


def _sin_choques(ov, avisos, espera_max=2.5):
    """Los visuales no se encilman: los grandes ocupan toda la pantalla, los de abajo/arriba comparten carril."""
    ov = sorted(ov, key=lambda o: (o["t"], -o.get("_pri", 5)))
    out = []
    def choca(c, a, b):
        for o in out:
            ca, cb = _carril(c["tipo"]), _carril(o["tipo"])
            if "libre" in (ca, cb):
                continue
            if ca == cb or "todo" in (ca, cb):
                if a < o["t"] + o["dur"] + 0.15 and b + 0.15 > o["t"]:
                    return o["t"] + o["dur"] + 0.15
        return None
    for o in ov:
        a = o["t"]
        for _ in range(12):
            r = choca(o, a, a + o["dur"])
            if r is None:
                break
            a = r
        else:
            a = None
        lim = espera_max + (1.5 if o.get("_pri", 5) >= 6 else 0.0)
        if a is None or a - o["t"] > lim:
            if o.get("_pri", 5) >= 5:
                avisos.append("Visual «%s» en %.1fs omitido: se encimaba con otro" % (o.get("_id", o["tipo"]), o["t"]))
            continue
        o["t"] = round(a, 3)
        out.append(o)
    for o in out:
        o.pop("_pri", None); o.pop("_id", None)
    return sorted(out, key=lambda o: o["t"])


def _satelitales(ov, cache, avisos, ancho_px):
    """Cambia cada mapa de poligonos por uno satelital si hay proveedor configurado y las teselas bajan bien."""
    from . import teselas as T
    from .components.mapa import _cargar_munis, _norm
    cfg = T.config()
    mapas = [o for o in ov if o["tipo"] == "mapa_ubicacion"]
    if not mapas:
        return ov
    if not T.disponible(cfg):
        avisos.append("MAPAS: no hay llave de satélite (mapas.json); los mapas salen sin imagen satelital. Ver README > Mapas satelitales.")
        return ov
    munis = _cargar_munis()
    for o in mapas:
        X, Y = T.merc(o["lon"], o["lat"])
        k = math.cos(math.radians(o["lat"]))
        xs, ys = [X], [Y]
        quiere = [_norm(m) for m in o["municipios"]]
        for m in munis:
            if _norm(m["nombre"]) in quiere:
                for r in m["anillos"]:
                    for lo, la in r:
                        a, b = T.merc(lo, la); xs.append(a); ys.append(b)
        hx, hy = (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
        ancho0 = max(hx, hy * 16 / 9) * 1.25 + 300
        radio0 = ancho0 * 1.15
        w1 = o.get("foco_sat_km", 1.5) * 1000 / k
        ref = 1920.0
        z0 = int(math.floor(math.log2(40075016.0 * 4 / radio0)))
        zc = min(18, int(math.ceil(math.log2(40075016.0 * ref / (512 * 2 * w1)))))
        niveles = [z0]
        z = z0 + 2
        while z < zc:
            niveles.append(z); z += 2
        if zc not in niveles and zc > z0:
            niveles.append(zc)
        radios = [radio0]
        for zz in niveles[1:]:
            mpp = (40075016.0 / 2 ** zz) / 512
            radios.append(1.3 * mpp * ref / 2 * 1.3)
        ok, total_falt, ult = True, 0, None
        for zz, rr in zip(niveles, radios):
            g, falt, tot, err = T.asegurar(cfg, cache, X, Y, rr, zz)
            if not g:
                ok = False; total_falt += falt; ult = ult or err
        if ok:
            o.update(tipo="mapa_satelite", niveles=niveles, radios_m=[round(r) for r in radios], ancho0_m=round(ancho0),
                     foco_km=o.get("foco_sat_km", 1.5), cache=cache, atribucion=cfg["atribucion"])
        else:
            avisos.append("MAPA «%s»: no pude bajar %d tesela(s) (%s); se usa el mapa sin satélite" % (o.get("lugar", ""), total_falt, str(ult)[:80]))
    return ov


def _aplicar_cambios(todas, cambios, avisos, saltar_ini):
    """Aplica los cambios manuales (cambios.json) a las piezas de B-roll."""
    from .cambios import IMG as CI, VID as CV
    por_id = {e["id"]: e for e in todas}
    for c in cambios:
        e = por_id.get(c["id"])
        if e is None:
            avisos.append("Cambio %s: esa pieza ya no existe (cambiaron los archivos de la carpeta); se ignora" % c["id"]); continue
        actual = os.path.basename(e["p"]["media"]["p"])
        if c.get("original") and c["original"] != actual and not c.get("nuevo"):
            avisos.append("Cambio %s: la pieza ahora usa «%s», no «%s»; se ignora" % (c["id"], actual, c["original"])); continue
        d = e["p"]["dur"]
        nuevo = c.get("nuevo") or e["p"]["media"]["p"]
        ext = os.path.splitext(nuevo)[1].lower()
        if not os.path.exists(nuevo):
            avisos.append("Cambio %s: no encuentro «%s»" % (c["id"], nuevo)); continue
        if ext in CI:
            e["p"] = dict(tipo="imagen", media=dict(p=nuevo, id=os.path.splitext(os.path.basename(nuevo))[0], usos=1), dur=d)
        elif ext in CV:
            dv = dur_video(nuevo)
            ini = c.get("inicio")
            if ini is None:
                ini = e["p"].get("ventana", (None,))[0] if (e["p"]["tipo"] == "clip" and not c.get("nuevo")) else (saltar_ini if dv > 60 else (6.0 if dv > 30 else 0.0))
            ini = max(0.0, min(float(ini), max(0.0, dv - 1.0)))
            e["p"] = dict(tipo="clip", media=dict(p=nuevo, id=os.path.splitext(os.path.basename(nuevo))[0], dur=dv, usos=1),
                          ventana=(round(ini, 3), round(d, 3)), dur=d)
        else:
            avisos.append("Cambio %s: tipo de archivo no soportado" % c["id"])


def _subtitulos_en_huecos(ov, guion, tiempos, ini, fin, orden, seg_de, hueco=8.0):
    """Rellena con subtitulos karaoke (frases del propio guion) los huecos largos sin visuales."""
    from .sincronizar import tokens_guion
    gt = tokens_guion(guion)
    toks = tiempos["tokens"]
    if len(gt) != len(toks):
        return ov
    # frases: (t0, t1, texto, seg)
    frases, cur = [], []
    for g, t in zip(gt, toks):
        cur.append((g["w"], t))
        if g["sent_end"]:
            frases.append(cur); cur = []
    ocup = sorted((o["t"], o["t"] + o["dur"]) for o in ov if o["tipo"] not in ("etiqueta_sup", "mascota"))
    def libre(a, b):
        return all(b + 0.3 <= x or a >= y + 0.3 for x, y in ocup)
    nuevos = []
    for n in orden:
        a_blk, b_blk = ini[n], fin[n]
        ult = a_blk + 4.5      # la tarjeta de capitulo ya ocupa el arranque
        for fr in frases:
            t0 = fr[0][1]["t0"]
            if fr[0][1]["seg"] != seg_de[n] or t0 < ult + hueco - 3.0 or t0 > b_blk - 4:
                continue
            ws = [w for w, _ in fr]
            if len(ws) > 16:
                corte = next((i for i, w in enumerate(ws[:16]) if w[-1] in ",;:" and i >= 5), None)
                if corte is None:
                    continue
                ws = ws[:corte + 1]
            if len(ws) < 5:
                continue
            t1 = fr[len(ws) - 1][1]["t1"]
            dur = max(3.0, min(5.2, t1 - t0 + 0.9))
            # sólo si realmente hay hueco antes y no tapa otro visual
            previos = [y for x, y in ocup if y <= t0 + 0.2 and y > a_blk]
            ultimo = max(previos + [ult])
            if t0 - ultimo < hueco - 3.0:
                continue
            if not libre(t0, t0 + dur):
                continue
            texto = " ".join(ws).rstrip(",;:")
            nuevos.append(dict(tipo="subtitulo", t=round(t0, 3), dur=round(dur, 2), texto=texto, palabra_a_palabra=True,
                               reveal=round(max(1.0, t1 - t0), 2)))
            ocup.append((t0, t0 + dur)); ocup.sort()
            ult = t0 + dur
    return sorted(ov + nuevos, key=lambda o: o["t"])


def _etiquetas_fotos(todas, bloques, pools, ini, avisos):
    """Campo opcional `fotos` de cada bloque del guion: etiqueta (fecha + titulo) y credito de fuente sobre cada foto,
    y lista de las fotos que aun no estan en la carpeta."""
    out = []
    specs = {}
    for n, b in bloques.items():
        for f in b.get("fotos", []) or []:
            specs[(n, str(f.get("id", "")).lower())] = f
            if not any(it["id"].lower() == str(f.get("id", "")).lower() for it in pools[n].imgs + list(pools[n].reservados.values())):
                _PEND.append(dict(tipo="foto", id=f["id"], bloque=n, efecto="foto", t=round(ini.get(n, 0), 1),
                                  pedir=f.get("que") or f.get("titulo", ""), archivo=str(f["id"]) + ".jpg", obligatoria=False))
                avisos.append("Falta la foto %s (%s)" % (f["id"], (f.get("que") or f.get("titulo", ""))[:70]))
    visto = set()
    for e in todas:
        p = e["p"]
        if p["tipo"] != "imagen" or p.get("foco"):
            continue
        f = specs.get((e["n"], p["media"]["id"].lower()))
        if not f or (e["n"], p["media"]["id"]) in visto:
            continue
        visto.add((e["n"], p["media"]["id"]))
        d = max(1.8, min(4.2, p["dur"] - 0.9))
        if f.get("titulo"):
            que = f.get("que", "")
            out.append(dict(tipo="lower_third", t=round(e["t"] + 0.5, 3), dur=round(d, 2), etiqueta=str(f.get("fecha") or "FOTO"),
                            titulo=f["titulo"], sub=que if 0 < len(que) <= 64 else "", color="rojo", _pri=2))
        if f.get("fuente"):
            out.append(dict(tipo="credito", t=round(e["t"] + 0.3, 3), dur=round(max(2.0, p["dur"] - 0.6), 2), texto=str(f["fuente"]), _pri=1))
    return out
