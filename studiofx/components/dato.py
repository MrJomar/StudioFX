import re
import cv2
import numpy as np
from PIL import ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow
from ..easing import ease_out_cubic, fade_env, clamp
from ..textkit import text_w, line_h, new_layer, wrap


@register("dato_grande")
class DatoGrande(Component):
    """Cifra enorme con descripcion; la cifra puede CONTAR desde 0 (efecto nuevo).
    Datos: valor ("≈ 270"), texto, sub (opc), fuente (opc), contar (default true)."""
    layer = 35

    def build(self):
        u, th, d = self.u, self.theme, self.data
        self.val = str(d["valor"])
        m = re.search(r"\d[\d.,]*", self.val)
        self.contar = bool(d.get("contar", True)) and m is not None
        if m:
            raw = m.group(0)
            self.pre, self.suf = self.val[:m.start()], self.val[m.end():]
            self.target = float(raw.replace(",", ""))
            self.thousands = "," in raw
            self.decimals = len(raw.split(".")[1]) if "." in raw and not self.thousands else 0
        self.fv = th.font("serif_bold", 118 * u)
        self._cache = {}
        ft = th.font("sans_bold", 27 * u)
        lines = wrap(ft, d["texto"], 0.42 * self.W)
        lh = line_h(ft)
        w = int(max(text_w(ft, ln) for ln in lines)) + 8
        img = new_layer(w, lh * len(lines) + 6)
        dd = ImageDraw.Draw(img)
        for i, ln in enumerate(lines):
            dd.text((2, 2 + i * lh), ln, font=ft, fill=(255, 255, 255, 255))
        y = lh * len(lines) + 6
        extra = []
        if d.get("sub"):
            fs = th.font("sans", 16 * u)
            extra.append((d["sub"], fs, (255, 255, 255, 215)))
        if extra:
            img2 = new_layer(max(w, int(text_w(extra[0][1], extra[0][0])) + 8), y + line_h(extra[0][1]) + 8)
            img2.alpha_composite(img, (0, 0))
            ImageDraw.Draw(img2).text((2, y + 4), extra[0][0], font=extra[0][1], fill=extra[0][2])
            img = img2
        img, self.pad = with_shadow(img, blur=5 * u, offset=(0, 2 * u), opacity=0.75, pad=int(10 * u))
        self.desc = to_premul(img)
        self.src = None
        if d.get("fuente"):
            fs = th.font("sans", 9 * u)
            s = new_layer(int(text_w(fs, d["fuente"])) + 6, line_h(fs) + 4)
            ImageDraw.Draw(s).text((2, 1), d["fuente"], font=fs, fill=(255, 255, 255, 255))
            s, p = with_shadow(s, blur=2 * u, offset=(0, 1), opacity=0.8, pad=int(5 * u))
            self.src, self.src_pad = to_premul(s), p
        # velo lateral para dar contraste (degradado izquierda -> derecha)
        xx = np.linspace(0, 1, self.W, dtype=np.float32)
        a = np.clip(1.0 - xx / 0.75, 0, 1) ** 1.4 * 0.78
        self.scrim = np.repeat(((1 - a) * 255).astype(np.uint8)[None, :, None], self.H, axis=0)
        self.scrim = np.repeat(self.scrim, 3, axis=2)

    def _value_text(self, p):
        if not self.contar:
            return self.val
        v = self.target * p
        if self.decimals:
            n = "%.*f" % (self.decimals, v)
        else:
            n = "{:,}".format(int(round(v))) if self.thousands else str(int(round(v)))
        return self.pre + n + self.suf

    def _sprite(self, text):
        if text not in self._cache:
            u = self.u
            w = int(text_w(self.fv, text)) + 12
            img = new_layer(w, line_h(self.fv) + 8)
            ImageDraw.Draw(img).text((4, 2), text, font=self.fv, fill=(255, 255, 255, 255))
            img, p = with_shadow(img, blur=6 * u, offset=(0, 3 * u), opacity=0.7, pad=int(12 * u))
            self._cache[text] = (to_premul(img), p)
            if len(self._cache) > 400:
                self._cache.pop(next(iter(self._cache)))
        return self._cache[text]

    def apply(self, base, lt):
        u = self.u
        env = fade_env(lt, self.dur, 0.4, 0.35)
        dark = cv2.multiply(base, self.scrim, scale=1 / 255.0)
        base[:] = cv2.addWeighted(base, 1 - env, dark, env, 0)
        out = clamp((self.dur - lt) / 0.3)
        p = ease_out_cubic(lt / 1.1)
        spr, pad = self._sprite(self._value_text(p))
        o = clamp(lt / 0.25) * out
        x = 58 * u - pad
        ycent = self.H * 0.47
        blit(base, spr, x, ycent - 105 * u - pad + (1 - o) * 10 * u, o)
        o2 = clamp((lt - 0.25) / 0.3) * out
        blit(base, self.desc, 58 * u - self.pad, ycent + 38 * u - self.pad + (1 - o2) * 10 * u, o2)
        if self.src is not None:
            blit(base, self.src, 58 * u - self.src_pad, self.H - 38 * u - self.src_pad, 0.7 * o2)


@register("ano_esquina")
class AnoEsquina(Component):
    """Ano o cifra grande y tenue en una esquina. Datos: texto, pos (sup_der|sup_izq)."""
    layer = 80

    def build(self):
        u, th = self.u, self.theme
        f = th.font("serif_bold", 70 * u)
        t = self.data["texto"]
        img = new_layer(int(text_w(f, t)) + 12, line_h(f) + 8)
        ImageDraw.Draw(img).text((4, 2), t, font=f, fill=(255, 255, 255, 255))
        img, self.pad = with_shadow(img, blur=6 * u, offset=(0, 3 * u), opacity=0.7, pad=int(12 * u))
        self.spr = to_premul(img)

    def apply(self, base, lt):
        u = self.u
        o = fade_env(lt, self.dur, 0.6, 0.5) * 0.85
        w = self.spr.shape[1] - 2 * self.pad
        left = self.data.get("pos", "sup_der") == "sup_izq"
        x = (48 * u if left else self.W - 48 * u - w) - self.pad
        blit(base, self.spr, x, 44 * u - self.pad + (1 - clamp(lt / 0.6)) * 12 * u, o)
