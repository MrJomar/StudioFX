"""Mosaicos satelitales (teselas XYZ) con cache en disco. Todo lo de red ocurre AL ARMAR el proyecto, no al renderizar."""
import json
import math
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

R = 6378137.0
PI_R = math.pi * R
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(RAIZ, "mapas.json")
PRESET = {
    "mapbox": "https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}@2x.jpg90?access_token={token}",
}
ATRIB = {"mapbox": "© Mapbox © OpenStreetMap"}


def config():
    c = dict(proveedor="mapbox", token="", plantilla="", atribucion="")
    if os.path.exists(CFG):
        try:
            c.update(json.load(open(CFG, encoding="utf-8")))
        except Exception:
            pass
    c["plantilla"] = c["plantilla"] or PRESET.get(c["proveedor"], "")
    c["atribucion"] = c["atribucion"] or ATRIB.get(c["proveedor"], "")
    return c


def disponible(c=None):
    c = c or config()
    return bool(c["plantilla"]) and ("{token}" not in c["plantilla"] or bool(c["token"]))


def merc(lon, lat):
    return R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def tile_de(X, Y, z):
    n = 2 ** z
    return int((X + PI_R) / (2 * PI_R) * n), int((PI_R - Y) / (2 * PI_R) * n)


def rango(X, Y, radio_m, z):
    """Teselas (x0,x1,y0,y1) que cubren un cuadrado de +-radio_m (metros mercator) alrededor de (X,Y)."""
    n = 2 ** z
    x0, y0 = tile_de(X - radio_m, Y + radio_m, z)
    x1, y1 = tile_de(X + radio_m, Y - radio_m, z)
    return max(0, x0), min(n - 1, x1), max(0, y0), min(n - 1, y1)


def _ruta(cache, prov, z, x, y):
    return os.path.join(cache, prov, str(z), str(x), "%d.jpg" % y)


def _bajar(url, dest, reintentos=2):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    ult = None
    for _ in range(reintentos + 1):
        try:
            rq = urllib.request.Request(url, headers={"User-Agent": "StudioFX/0.12 (video documental; cache local)"})
            datos = urllib.request.urlopen(rq, timeout=20).read()
            if len(datos) < 200:
                raise IOError("respuesta vacia")
            open(dest, "wb").write(datos)
            return True
        except Exception as e:  # noqa
            ult = e
    return ult


def asegurar(cfg, cache, X, Y, radio_m, z):
    """Descarga (si falta) las teselas del nivel z. Devuelve (ok, faltan, total)."""
    x0, x1, y0, y1 = rango(X, Y, radio_m, z)
    jobs = []
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            d = _ruta(cache, cfg["proveedor"], z, x, y)
            if not os.path.exists(d):
                jobs.append((cfg["plantilla"].format(z=z, x=x, y=y, token=cfg["token"]), d))
    falt = 0
    primero = None
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(lambda j: _bajar(*j), jobs):
            if r is not True:
                falt += 1
                primero = primero or r
    return falt == 0, falt, (x1 - x0 + 1) * (y1 - y0 + 1), primero


def mosaico(cache, prov, X, Y, radio_m, z):
    """Imagen BGR del mosaico + (X0, Y0 en metros de su esquina sup-izq, metros por pixel)."""
    x0, x1, y0, y1 = rango(X, Y, radio_m, z)
    tp = None
    tiles = {}
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            p = _ruta(cache, prov, z, x, y)
            if os.path.exists(p):
                im = cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)
                if im is not None:
                    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)   # los cuadros del render son RGB
                    tiles[(x, y)] = im
                    tp = tp or im.shape[0]
    tp = tp or 256
    img = np.full(((y1 - y0 + 1) * tp, (x1 - x0 + 1) * tp, 3), 40, np.uint8)
    for (x, y), im in tiles.items():
        if im.shape[0] != tp:
            im = cv2.resize(im, (tp, tp))
        img[(y - y0) * tp:(y - y0 + 1) * tp, (x - x0) * tp:(x - x0 + 1) * tp] = im
    S = 2 * PI_R / 2 ** z
    return img, x0 * S - PI_R, PI_R - y0 * S, S / tp
