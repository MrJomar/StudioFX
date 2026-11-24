import math
import os
from PIL import Image
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow
from ..easing import ease_out_back, ease_out_cubic, clamp

POSES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "mascota")


@register("mascota")
class Mascota(Component):
    """Xolo Explorador animado. Datos: pose (front|tres_cuartos|camina|mapa|senala|linterna|feliz|sorpresa),
    pos (izq|der|centro), tam (alto como fraccion de la pantalla, 0.2-0.6), movimiento (rebote|respira|camina)."""
    layer = 70

    def build(self):
        u, d = self.u, self.data
        img = Image.open(os.path.join(POSES_DIR, d.get("pose", "front") + ".png")).convert("RGBA")
        h = min(float(d.get("tam", 0.42)) * self.H, img.height * 1.6)
        k = h / img.height
        img = img.resize((max(1, int(img.width * k)), int(h)), Image.LANCZOS)
        img, self.pad = with_shadow(img, blur=8 * u, offset=(0, 5 * u), opacity=0.45, pad=int(16 * u))
        self.spr = to_premul(img)
        self.pos = d.get("pos", "der")
        self.mov = d.get("movimiento", "respira")

    def apply(self, base, lt):
        u, W, H = self.u, self.W, self.H
        w, h = self.spr.shape[1], self.spr.shape[0]
        m = 40 * u
        xr = {"izq": m - self.pad, "der": W - w + self.pad - m, "centro": (W - w) / 2}[self.pos]
        ybase = H - h + self.pad + 6 * u
        e = ease_out_back(clamp(lt / 0.7), 1.5)
        out = clamp((self.dur - lt) / 0.4)
        out_e = ease_out_cubic(1 - out)
        x, y = xr, ybase
        if self.pos == "centro":
            y += (1 - e) * h * 0.9
        else:
            side = -1 if self.pos == "izq" else 1
            x += side * (1 - e) * (w + m)
        y += out_e * h * 0.9
        t = lt
        if self.mov == "rebote":
            y -= abs(math.sin(t * 5.0)) * 9 * u
        elif self.mov == "camina":
            y -= abs(math.sin(t * 7.0)) * 7 * u
            x += math.sin(t * 3.5) * 5 * u
        else:  # respira
            y -= (math.sin(t * 2.2) * 0.5 + 0.5) * 4 * u
        blit(base, self.spr, x, y, clamp(lt / 0.2) * (1.0 if out > 0 else 0.0))
