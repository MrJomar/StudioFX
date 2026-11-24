"""Mapa animado a partir de poligonos (GeoJSON o listas lon/lat): zona resaltada, zoom, marcadores, rutas."""
import json
import math
import cv2
import numpy as np
from PIL import ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow
from ..easing import ease_in_out_cubic, ease_out_cubic, ease_out_back, fade_env, clamp
from ..textkit import text_w, line_h, new_layer, draw_tracked
from ..infokit import pill, rrect

SH = 4  # bits de subpixel en cv2


def _rings(geom):
    t = geom["type"]
    if t == "Polygon":
        return [geom["coordinates"][0]]
    if t == "MultiPolygon":
        return [p[0] for p in geom["coordinates"]]
    return []


@register("mapa_zona")
class MapaZona(Component):
    """Datos: titulo, geojson (ruta) o contexto[[ [lon,lat],...]], resaltar (poligono) o resaltar_nombre (si geojson),
    puntos[{nombre,lon,lat}], ruta (true: une los puntos en orden), color (acento), modo (claro|oscuro)."""
    layer = 30

    def build(self):
        u, th, d = self.u, self.theme, self.data
        self.oscuro = d.get("modo", "claro") == "oscuro"
        ctx, hi = [], []
        if d.get("geojson"):
            gj = json.load(open(d["geojson"], encoding="utf-8"))
            name = str(d.get("resaltar_nombre", "")).lower()
            for ft in gj.get("features", []):
                rs = _rings(ft["geometry"])
                vals = [str(v).lower() for v in (ft.get("properties") or {}).values()]
                (hi if name and name in vals else ctx).extend(rs)
        for p in d.get("contexto", []):
            ctx.append(p)
        if d.get("resaltar"):
            hi.append(d["resaltar"])
        for r in d.get("resaltar_multi", []):
            hi.append(r)
        self.pts = d.get("puntos", [])
        allr = ctx + hi
        lons = [c[0] for r in allr for c in r]
        lats = [c[1] for r in allr for c in r]
        for p in self.pts:
            lons.append(p["lon"]); lats.append(p["lat"])
        self.lon0 = (min(lons) + max(lons)) / 2
        self.lat0 = (min(lats) + max(lats)) / 2
        self.kx = 111.32 * math.cos(math.radians(self.lat0))
        self.ky = 110.57
        proj = lambda r: np.array([[(c[0] - self.lon0) * self.kx, -(c[1] - self.lat0) * self.ky] for c in r], np.float64)
        self.ctx = [proj(r) for r in ctx]
        self.hi = [proj(r) for r in hi]
        self.P = np.array([[(p["lon"] - self.lon0) * self.kx, -(p["lat"] - self.lat0) * self.ky] for p in self.pts]) \
            if self.pts else np.zeros((0, 2))
        allp = np.vstack(self.ctx + self.hi + ([self.P] if len(self.P) else []))
        self.b_all = (allp.min(0), allp.max(0))
        focus = np.vstack(self.hi + ([self.P] if len(self.P) else [])) if (self.hi or len(self.P)) else allp
        self.b_foc = (focus.min(0), focus.max(0))
        self.v1 = self._fit(self.b_all, 0.84, 0.72)
        self.v2 = self._fit(self.b_foc, 0.50, 0.50)
        # colores
        self.bg = (20, 32, 43) if self.oscuro else (239, 232, 216)
        self.c_ctx = (58, 55, 52) if self.oscuro else (219, 211, 191)
        self.c_line = (110, 106, 98) if self.oscuro else (160, 150, 128)
        self.acc = th.color(d.get("color", "naranja"))[:3]
        self.pin = (255, 255, 255) if self.oscuro else (38, 36, 33)
        # sprites
        self.title = None
        if d.get("titulo"):
            f = th.font("sans_black", 32 * u)
            t = d["titulo"].upper()
            img = new_layer(int(text_w(f, t, 4 * u)) + 8, line_h(f) + 6)
            draw_tracked(ImageDraw.Draw(img), (2, 2), t, f, th.color("blanco") if self.oscuro else th.color("tinta"), 4 * u)
            self.title = to_premul(img)
            bar = rrect(int(70 * u), max(3, int(6 * u)), 3 * u, th.color(d.get("color", "naranja")))
            self.bar = to_premul(bar)
        self.labels = []
        for p in self.pts:
            pl = pill(th, p["nombre"], "sans_bold", 22 * u, (38, 36, 33, 255), (255, 255, 255, 255), 16 * u, 7 * u)
            img, pad = with_shadow(pl, blur=6 * u, offset=(0, 3 * u), opacity=0.35, pad=int(10 * u))
            self.labels.append((to_premul(img), pad))
        self.north = self._north(u)

    def _fit(self, b, fw, fh):
        lo, hi = b
        w, h = max(hi[0] - lo[0], 1e-6), max(hi[1] - lo[1], 1e-6)
        s = min(fw * self.W / w, fh * self.H / h)
        return ((lo + hi) / 2, s)

    def _north(self, u):
        s = int(46 * u)
        img = new_layer(s, int(s * 1.25))
        d = ImageDraw.Draw(img)
        col = (240, 240, 240, 255) if self.oscuro else (38, 36, 33, 255)
        d.polygon([(s / 2, 2), (s * 0.82, s * 0.95), (s / 2, s * 0.72), (s * 0.18, s * 0.95)], fill=col)
        f = self.theme.font("sans_black", s * 0.34)
        d.text(((s - text_w(f, "N")) / 2, s * 0.98), "N", font=f, fill=col)
        return to_premul(img)

    def _cam(self, lt):
        p = ease_in_out_cubic(clamp((lt - 1.2) / 1.8))
        c = self.v1[0] * (1 - p) + self.v2[0] * p
        s = math.exp(math.log(self.v1[1]) * (1 - p) + math.log(self.v2[1]) * p)
        return c, s

    def _px(self, pts, c, s):
        a = (pts - c) * s + np.array([self.W / 2, self.H / 2])
        return np.round(a * (1 << SH)).astype(np.int32)

    def apply(self, base, lt):
        u, W, H = self.u, self.W, self.H
        env = fade_env(lt, self.dur, 0.5, 0.5)
        c, s = self._cam(lt)
        cv = np.empty_like(base)
        cv[:] = self.bg
        for r in self.ctx:
            q = self._px(r, c, s)
            cv2.fillPoly(cv, [q], self.c_ctx, lineType=cv2.LINE_AA, shift=SH)
            cv2.polylines(cv, [q], True, self.c_line, max(1, int(1.6 * u)), cv2.LINE_AA, SH)
        ha = ease_out_cubic(clamp((lt - 0.6) / 1.0))
        if self.hi and ha > 0:
            ov = cv.copy()
            for r in self.hi:
                cv2.fillPoly(ov, [self._px(r, c, s)], self.acc, lineType=cv2.LINE_AA, shift=SH)
            cv = cv2.addWeighted(cv, 1 - 0.85 * ha, ov, 0.85 * ha, 0)
            for r in self.hi:
                cv2.polylines(cv, [self._px(r, c, s)], True, (255, 255, 255), max(2, int(3 * u)), cv2.LINE_AA, SH)
        n = len(self.P)
        # ruta entre puntos
        if self.data.get("ruta") and n > 1:
            pr = clamp((lt - 3.2) / (0.9 * (n - 1)))
            q = self._px(self.P, c, s) / (1 << SH)
            segl = np.linalg.norm(np.diff(q, axis=0), axis=1)
            tot = segl.sum() * pr
            pts = [q[0]]
            for i, L in enumerate(segl):
                if tot >= L:
                    pts.append(q[i + 1]); tot -= L
                else:
                    pts.append(q[i] + (q[i + 1] - q[i]) * (tot / max(L, 1e-6))); break
            pa = np.round(np.array(pts) * (1 << SH)).astype(np.int32)
            cv2.polylines(cv, [pa], False, (255, 255, 255), max(5, int(9 * u)), cv2.LINE_AA, SH)
            cv2.polylines(cv, [pa], False, self.pin if not self.data.get("color_ruta") else tuple(self.data["color_ruta"]),
                          max(3, int(5 * u)), cv2.LINE_AA, SH)
        base[:] = cv2.addWeighted(base, 1 - env, cv, env, 0) if env < 0.999 else cv
        # titulo, escala, norte
        if self.title is not None and self.data.get("velo_titulo", True):
            hh = int(170 * u)
            g = np.linspace(0.62, 0.0, hh, dtype=np.float32)[:, None, None] * clamp(lt / 0.4) * env
            base[:hh] = (base[:hh] * (1 - g)).astype(np.uint8)
        if self.title is not None:
            o = clamp(lt / 0.4) * env
            blit(base, self.title, 90 * u, 62 * u + (1 - o) * 10 * u, o)
            blit(base, self.bar, 92 * u, 62 * u + self.title.shape[0] + 8 * u, o)
        o = clamp((lt - 0.5) / 0.5) * env
        blit(base, self.north, W - 90 * u - self.north.shape[1], 60 * u, o)
        self._escala(base, s, o)
        # marcadores
        qp = self._px(self.P, c, s) / (1 << SH) if n else []
        for i in range(n):
            t0 = 2.4 + i * 0.7
            l2 = lt - t0
            if l2 <= 0:
                continue
            x, y = qp[i]
            k = ease_out_back(clamp(l2 / 0.5), 2.0)
            r = max(1.0, 11 * u * k)
            ph = (l2 * 0.9) % 1.0
            ring = np.zeros_like(base)
            ov = base.copy()
            cv2.circle(ov, (int(x * 16), int(y * 16)), int((r + 26 * u * ph) * 16), self.pin, max(2, int(3 * u)), cv2.LINE_AA, 4)
            a = (1 - ph) * 0.8 * env
            base[:] = cv2.addWeighted(base, 1 - a, ov, a, 0)
            cv2.circle(base, (int(x * 16), int(y * 16)), int((r + 3 * u) * 16), (255, 255, 255) if not self.oscuro else (30, 28, 26), -1, cv2.LINE_AA, 4)
            cv2.circle(base, (int(x * 16), int(y * 16)), int(r * 16), self.pin, -1, cv2.LINE_AA, 4)
            spr, pad = self.labels[i]
            lo = clamp((l2 - 0.15) / 0.3) * env
            blit(base, spr, x - spr.shape[1] / 2, y - 24 * u - spr.shape[0] + (1 - lo) * 8 * u, lo)

    def _escala(self, base, s, o):
        u = self.u
        km = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20]
        L = next((k for k in km if k * s >= 90 * u), km[-1])
        w = int(L * s)
        x0, y0 = int(90 * u), int(self.H - 60 * u)
        col = (240, 240, 240) if self.oscuro else (38, 36, 33)
        ov = base.copy()
        cv2.line(ov, (x0, y0), (x0 + w, y0), col, max(2, int(3 * u)), cv2.LINE_AA)
        cv2.line(ov, (x0, y0 - 6), (x0, y0 + 6), col, max(2, int(3 * u)), cv2.LINE_AA)
        cv2.line(ov, (x0 + w, y0 - 6), (x0 + w, y0 + 6), col, max(2, int(3 * u)), cv2.LINE_AA)
        txt = ("%g km" % L) if L >= 1 else ("%d m" % int(L * 1000))
        cv2.putText(ov, txt, (x0, y0 - int(12 * u)), cv2.FONT_HERSHEY_SIMPLEX, 0.6 * u, col, max(1, int(2 * u)), cv2.LINE_AA)
        base[:] = cv2.addWeighted(base, 1 - o, ov, o, 0)


DATOS_MUNI = None


def _cargar_munis():
    global DATOS_MUNI
    if DATOS_MUNI is None:
        import os
        ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            "datos", "jalisco_municipios.json")
        DATOS_MUNI = json.load(open(ruta, encoding="utf-8"))["municipios"]
    return DATOS_MUNI


def _norm(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")


@register("mapa_ubicacion")
class MapaUbicacion(MapaZona):
    """Mapa de un lugar sobre los municipios de Jalisco (INEGI): resalta municipio(s) y marca el punto.
    Datos: titulo, municipios[nombres a resaltar], lon, lat, lugar (etiqueta del pin), radio_km (contexto, 24),
    foco_km (zoom final, 9), modo (oscuro|claro), color."""

    def build(self):
        d = dict(self.data)
        lon, lat = float(d["lon"]), float(d["lat"])
        rkm = float(d.get("radio_km", 24))
        dlat, dlon = rkm / 110.57, rkm / (111.32 * math.cos(math.radians(lat)))
        quiere = [_norm(m) for m in d.get("municipios", [])]
        ctx, hi = [], []
        for m in _cargar_munis():
            esta = _norm(m["nombre"]) in quiere
            for r in m["anillos"]:
                xs = [c[0] for c in r]; ys = [c[1] for c in r]
                if max(xs) < lon - dlon or min(xs) > lon + dlon or max(ys) < lat - dlat or min(ys) > lat + dlat:
                    if not esta:
                        continue
                (hi if esta else ctx).append(r)
        d.update(contexto=ctx, resaltar_multi=hi, puntos=[dict(nombre=d.get("lugar", ""), lon=lon, lat=lat)])
        d.setdefault("modo", "oscuro")
        self.data = d
        super().build()
        # zoom final: el municipio resaltado completo con su pin (se ven los limites y los vecinos)
        self.v2 = self._fit(self.b_foc, 0.66, 0.62)
        self.v1 = self._fit(self.b_all, 0.84, 0.72)


@register("mapa_satelite")
class MapaSatelite(Component):
    """Mapa sobre imagen satelital REAL (teselas descargadas al armar el proyecto y guardadas en cache).
    Datos: titulo, municipios[], lon, lat, lugar, foco_km (medio ancho del encuadre final), cache (carpeta),
    radio_m (medio ancho del encuadre inicial), niveles[z...], atribucion."""
    layer = 30

    def build(self):
        from .. import teselas as T
        d, u, th = self.data, self.u, self.theme
        self.T = T
        self.cfg = T.config()
        self.cache = d["cache"]
        self.lon, self.lat = float(d["lon"]), float(d["lat"])
        self.X, self.Y = T.merc(self.lon, self.lat)
        self.k_lat = math.cos(math.radians(self.lat))
        self.niveles = d["niveles"]
        self.radios = d["radios_m"]
        self.foco = float(d.get("foco_km", 1.5)) * 1000 / self.k_lat          # mercator m
        self.ancho0 = float(d["ancho0_m"])                                     # medio ancho inicial (mercator m)
        quiere = [_norm(m) for m in d.get("municipios", [])]
        self.rings = []
        for m in _cargar_munis():
            if _norm(m["nombre"]) in quiere:
                for r in m["anillos"]:
                    self.rings.append(np.array([T.merc(c[0], c[1]) for c in r], np.float64))
        self.mos = None
        self.acc = th.color(d.get("color", "naranja"))[:3]
        if d.get("titulo"):
            f = th.font("sans_black", 32 * u)
            t = d["titulo"].upper()
            img = new_layer(int(text_w(f, t, 4 * u)) + 8, line_h(f) + 6)
            draw_tracked(ImageDraw.Draw(img), (2, 2), t, f, th.color("blanco"), 4 * u)
            self.title = to_premul(img)
            self.bar = to_premul(rrect(int(70 * u), max(3, int(6 * u)), 3 * u, th.color(d.get("color", "naranja"))))
        else:
            self.title = None
        pl = pill(th, d.get("lugar", ""), "sans_bold", 22 * u, (38, 36, 33, 255), (255, 255, 255, 255), 16 * u, 7 * u)
        img, pad = with_shadow(pl, blur=6 * u, offset=(0, 3 * u), opacity=0.35, pad=int(10 * u))
        self.label = (to_premul(img), pad)
        self.attr = None
        a = d.get("atribucion") or self.cfg["atribucion"]
        if a:
            f = th.font("sans_bold", 15 * u)
            im = new_layer(int(text_w(f, a)) + 10, line_h(f) + 6)
            ImageDraw.Draw(im).text((5, 3), a, font=f, fill=(255, 255, 255, 230))
            self.attr = to_premul(im)
        self.oscuro = True
        self.north = MapaZona._north(self, u)

    def _cargar(self):
        T = self.T
        self.mos = []
        for z, r in zip(self.niveles, self.radios):
            img, X0, Y0, mpp = T.mosaico(self.cache, self.cfg["proveedor"], self.X, self.Y, r, z)
            self.mos.append((img, X0, Y0, mpp))

    def _cam(self, lt):
        p = ease_in_out_cubic(clamp((lt - 1.2) / 2.2))
        w0, w1 = self.ancho0, self.foco
        w = math.exp(math.log(w0) * (1 - p) + math.log(w1) * p)
        return w, self.W / (2 * w)       # medio ancho visible (m), escala px/m

    def apply(self, base, lt):
        u, W, H = self.u, self.W, self.H
        if lt >= self.dur:
            self.mos = None
            return
        if self.mos is None:
            self._cargar()
        env = fade_env(lt, self.dur, 0.5, 0.5)
        w, sc = self._cam(lt)
        mpp_v = 1.0 / sc
        cv = np.full_like(base, 30)
        for i, (img, X0, Y0, mpp) in enumerate(self.mos):
            if i == 0:
                a = 1.0
            else:
                a = clamp((mpp * 2.2 - mpp_v) / (mpp * 0.9))
            if a <= 0:
                continue
            k = mpp * sc
            M = np.float32([[k, 0, (X0 - self.X) * sc + W / 2], [0, k, (self.Y - Y0) * sc + H / 2]])
            warp = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_AREA if k < 0.5 else cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
            if i == 0:
                cv = warp
            else:
                # mascara: donde el mosaico fino realmente cubre
                m = np.zeros((H, W), np.uint8)
                m[:] = 255
                msk = cv2.warpAffine(np.full(img.shape[:2], 255, np.uint8), M, (W, H), flags=cv2.INTER_NEAREST)
                al = (msk.astype(np.float32) / 255.0 * a)[:, :, None]
                cv = (cv * (1 - al) + warp * al).astype(np.uint8)
        # contorno del municipio
        ha = ease_out_cubic(clamp((lt - 0.4) / 0.9))
        if self.rings and ha > 0:
            ov = cv.copy()
            for r in self.rings:
                q = np.round(np.column_stack([(r[:, 0] - self.X) * sc + W / 2, (self.Y - r[:, 1]) * sc + H / 2]) * (1 << SH)).astype(np.int32)
                cv2.fillPoly(ov, [q], self.acc, lineType=cv2.LINE_AA, shift=SH)
            cv = cv2.addWeighted(cv, 1 - 0.22 * ha, ov, 0.22 * ha, 0)
            for r in self.rings:
                q = np.round(np.column_stack([(r[:, 0] - self.X) * sc + W / 2, (self.Y - r[:, 1]) * sc + H / 2]) * (1 << SH)).astype(np.int32)
                cv2.polylines(cv, [q], True, (255, 255, 255), max(2, int(3 * u * ha)), cv2.LINE_AA, SH)
        base[:] = cv2.addWeighted(base, 1 - env, cv, env, 0) if env < 0.999 else cv
        # velo del titulo, titulo, norte, escala, atribucion
        if self.title is not None:
            hh = int(170 * u)
            g = np.linspace(0.62, 0.0, hh, dtype=np.float32)[:, None, None] * clamp(lt / 0.4) * env
            base[:hh] = (base[:hh] * (1 - g)).astype(np.uint8)
            o = clamp(lt / 0.4) * env
            blit(base, self.title, 90 * u, 62 * u + (1 - o) * 10 * u, o)
            blit(base, self.bar, 92 * u, 62 * u + self.title.shape[0] + 8 * u, o)
        o = clamp((lt - 0.5) / 0.5) * env
        blit(base, self.north, W - 90 * u - self.north.shape[1], 60 * u, o)
        self._escala(base, sc, o)
        if self.attr is not None:
            blit(base, self.attr, W - 24 * u - self.attr.shape[1], H - 20 * u - self.attr.shape[0], env)
        # pin
        l2 = lt - 2.4
        if l2 > 0:
            x, y = W / 2, H / 2
            k = ease_out_back(clamp(l2 / 0.5), 2.0)
            r = max(1.0, 11 * u * k)
            ph = (l2 * 0.9) % 1.0
            ov = base.copy()
            cv2.circle(ov, (int(x * 16), int(y * 16)), int((r + 26 * u * ph) * 16), (255, 255, 255), max(2, int(3 * u)), cv2.LINE_AA, 4)
            a = (1 - ph) * 0.8 * env
            base[:] = cv2.addWeighted(base, 1 - a, ov, a, 0)
            cv2.circle(base, (int(x * 16), int(y * 16)), int((r + 3 * u) * 16), (255, 255, 255), -1, cv2.LINE_AA, 4)
            cv2.circle(base, (int(x * 16), int(y * 16)), int(r * 16), self.acc, -1, cv2.LINE_AA, 4)
            spr, pad = self.label
            lo = clamp((l2 - 0.15) / 0.3) * env
            blit(base, spr, x - spr.shape[1] / 2, y - 24 * u - spr.shape[0] + (1 - lo) * 8 * u, lo)

    def _escala(self, base, sc, o):
        u = self.u
        km = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20]
        pxkm = 1000 / self.k_lat * sc          # px por km de suelo
        L = next((k for k in km if k * pxkm >= 90 * u), km[-1])
        wpx = int(L * pxkm)
        x0, y0 = int(90 * u), int(self.H - 60 * u)
        ov = base.copy()
        cv2.line(ov, (x0, y0), (x0 + wpx, y0), (255, 255, 255), max(2, int(3 * u)), cv2.LINE_AA)
        cv2.line(ov, (x0, y0 - 6), (x0, y0 + 6), (255, 255, 255), max(2, int(3 * u)), cv2.LINE_AA)
        cv2.line(ov, (x0 + wpx, y0 - 6), (x0 + wpx, y0 + 6), (255, 255, 255), max(2, int(3 * u)), cv2.LINE_AA)
        cv2.putText(ov, ("%g km" % L) if L >= 1 else ("%d m" % int(L * 1000)), (x0, y0 - int(12 * u)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6 * u, (255, 255, 255), max(1, int(2 * u)), cv2.LINE_AA)
        base[:] = cv2.addWeighted(base, 1 - o, ov, o, 0)
