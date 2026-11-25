"""Piezas al estilo documental: palabra grande a pantalla completa y tarjeta de libro/obra."""
import numpy as np
from PIL import ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow, rotate_sprite
from ..easing import ease_out_cubic, fade_env, clamp
from ..textkit import text_w, draw_tracked, line_h, new_layer, wrap

FONDOS = {"azul": (14, 34, 52), "oscuro": (12, 14, 18), "rojo": (52, 16, 18), "verde": (14, 40, 32), "tierra": (46, 32, 22)}


@register("palabra_grande")
class PalabraGrande(Component):
    """Pantalla completa con una palabra enorme (p. ej. «AGUA»), una linea pequena arriba y un subrayado que se dibuja.
    Datos: texto, kicker (opc), fondo (azul|oscuro|rojo|verde|tierra), sub (opc)."""
    layer = 27

    def build(self):
        u, th, d = self.u, self.theme, self.data
        self.fondo = np.array(FONDOS.get(d.get("fondo", "oscuro"), FONDOS["oscuro"]), np.float32)
        txt = d["texto"].upper()
        size = 120 * u
        f = th.font("display", size)
        while text_w(f, txt) > 0.84 * self.W and size > 40 * u:
            size *= 0.92
            f = th.font("display", size)
        w, h = int(text_w(f, txt) + 40 * u), int(line_h(f) + 20 * u)
        img = new_layer(w, h)
        ImageDraw.Draw(img).text((20 * u, 8 * u), txt, font=f, fill=(250, 246, 238, 255))
        img, self.pad = with_shadow(img, blur=10 * u, offset=(0, 4 * u), opacity=0.5, pad=int(20 * u))
        self.spr = to_premul(img)
        self.tw = text_w(f, txt)
        if d.get("kicker"):
            fk = th.font("sans_bold", 12.5 * u)
            kt = d["kicker"].upper()
            kw = int(text_w(fk, kt, 4.5 * u) + 16 * u)
            k = new_layer(kw, int(line_h(fk) + 8 * u))
            draw_tracked(ImageDraw.Draw(k), (8 * u, 4 * u), kt, fk, (232, 176, 80, 255), 4.5 * u)
            self.kick = to_premul(k)
        else:
            self.kick = None
        if d.get("sub"):
            fs = th.font("serif_italic", 22 * u)
            st = d["sub"]
            sw = int(text_w(fs, st) + 20 * u)
            s = new_layer(sw, int(line_h(fs) + 10 * u))
            ImageDraw.Draw(s).text((10 * u, 4 * u), st, font=fs, fill=(225, 225, 225, 235))
            self.subspr = to_premul(s)
        else:
            self.subspr = None

    def apply(self, base, lt):
        u = self.u
        env = fade_env(lt, self.dur, 0.35, 0.35)
        base[:] = (base * (1 - env) + self.fondo * env).astype(np.uint8)
        e = ease_out_cubic(lt / 0.8)
        cx, cy = self.W / 2, self.H / 2
        sw, sh = self.spr.shape[1], self.spr.shape[0]
        blit(base, self.spr, cx - sw / 2, cy - sh / 2 + (1 - e) * 22 * u, env * clamp(lt / 0.45))
        if self.kick is not None:
            kw = self.kick.shape[1]
            blit(base, self.kick, cx - kw / 2, cy - sh / 2 - 34 * u, env * clamp((lt - 0.1) / 0.4))
        # subrayado dorado que se dibuja
        ln = self.tw * 0.18 * ease_out_cubic((lt - 0.3) / 0.7)
        y = int(cy + sh / 2 - 6 * u)
        x0 = int(cx - ln / 2); x1 = int(cx + ln / 2)
        if x1 > x0:
            t = max(2, int(3 * u))
            reg = base[y:y + t, x0:x1].astype(np.float32)
            base[y:y + t, x0:x1] = (reg * (1 - env) + np.array([232, 176, 80], np.float32) * env).astype(np.uint8)
        if self.subspr is not None:
            w = self.subspr.shape[1]
            blit(base, self.subspr, cx - w / 2, y + 22 * u, env * clamp((lt - 0.7) / 0.4))


COL_LIBRO = {"rojo": (112, 40, 38), "azul": (34, 58, 92), "verde": (40, 74, 52), "tierra": (96, 70, 44)}


@register("tarjeta_libro")
class TarjetaLibro(Component):
    """Tarjeta tipo portada de libro/obra al lado de una foto (autor, titulo, anio).
    Datos: autor, titulo, anio, color (rojo|azul|verde|tierra), pos (der|izq)."""
    layer = 33

    def build(self):
        u, th, d = self.u, self.theme, self.data
        w, h = int(0.17 * self.W), int(0.46 * self.H)
        col = COL_LIBRO.get(d.get("color", "rojo"), COL_LIBRO["rojo"])
        img = new_layer(w, h)
        dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, w, h], fill=col + (255,))
        dr.rectangle([0, 0, int(4 * u), h], fill=(0, 0, 0, 70))
        fa = th.font("sans_bold", 8.5 * u)
        for i, ln in enumerate(wrap(fa, d.get("autor", "").upper(), w - 24 * u, 1.6 * u)):
            draw_tracked(dr, (14 * u, 16 * u + i * line_h(fa)), ln, fa, (255, 255, 255, 190), 1.6 * u)
        ft = th.font("serif_bold", 22 * u)
        lines = wrap(ft, d.get("titulo", ""), w - 28 * u)
        y0 = h * 0.42
        dr.rectangle([int(14 * u), int(y0 - 12 * u), int(14 * u + 26 * u), int(y0 - 10 * u)], fill=(255, 255, 255, 200))
        for i, ln in enumerate(lines):
            dr.text((14 * u, y0 + i * line_h(ft)), ln, font=ft, fill=(255, 255, 255, 255))
        if d.get("anio"):
            fy = th.font("sans", 9 * u)
            dr.text((14 * u, h - 24 * u), str(d["anio"]), font=fy, fill=(255, 255, 255, 170))
        img, self.pad = with_shadow(img, blur=12 * u, offset=(0, 8 * u), opacity=0.55, pad=int(30 * u))
        self.spr = to_premul(img)
        self.pos = d.get("pos", "der")

    def apply(self, base, lt):
        u = self.u
        e = ease_out_cubic(lt / 0.6)
        o = clamp(lt / 0.25) * clamp((self.dur - lt) / 0.3)
        spr = rotate_sprite(self.spr, 3 + (1 - e) * 8, 1.0)
        cx = (0.80 if self.pos == "der" else 0.20) * self.W
        blit(base, spr, cx - spr.shape[1] / 2 + (1 - e) * 60 * u, self.H / 2 - spr.shape[0] / 2 + 8 * u, o)
