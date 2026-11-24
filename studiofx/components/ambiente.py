import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .base import Component, register
from ..compositing import to_premul, blit
from ..easing import fade_env


def _dot(r, color):
    """Punto suave (gaussiana) de radio r px."""
    s = int(r * 6) | 1
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    c = s // 2
    g = np.exp(-(((xx - c) ** 2 + (yy - c) ** 2) / (2 * (r * 0.9) ** 2)))
    spr = np.zeros((s, s, 4), np.float32)
    spr[..., 3] = g * 255
    for i in range(3):
        spr[..., i] = color[i] * g
    return spr


@register("particulas")
class Particulas(Component):
    """Particulas flotantes que dan vida a imagenes fijas.
    Datos: estilo (polvo | luciernagas | nieve), cantidad (opc), intensidad (opc 0-1)."""
    layer = 12

    def build(self):
        u, d = self.u, self.data
        self.estilo = d.get("estilo", "polvo")
        n = int(d.get("cantidad", {"polvo": 70, "luciernagas": 28, "nieve": 110}.get(self.estilo, 60)))
        self.k = float(d.get("intensidad", 0.8))
        rng = np.random.default_rng(int(d.get("semilla", 5)))
        col = {"polvo": (255, 236, 200), "luciernagas": (255, 226, 120), "nieve": (255, 255, 255)}[self.estilo]
        rad = {"polvo": (1.0, 2.6), "luciernagas": (2.2, 4.2), "nieve": (1.2, 3.2)}[self.estilo]
        self.sprites = [_dot(r * u, col) for r in np.linspace(rad[0], rad[1], 4)]
        self.p = []
        for _ in range(n):
            self.p.append(dict(
                x=rng.uniform(0, self.W), y=rng.uniform(0, self.H),
                sp=rng.uniform(0.4, 1.0), b=int(rng.integers(0, 4)),
                ph=rng.uniform(0, 6.28), tw=rng.uniform(0.6, 2.2), wob=rng.uniform(8, 40) * u,
                al=rng.uniform(0.35, 1.0)))

    def apply(self, base, lt):
        u, W, H = self.u, self.W, self.H
        env = fade_env(lt, self.dur, 0.8, 0.8) * self.k
        for q in self.p:
            sp = q["sp"]
            if self.estilo == "polvo":
                x = q["x"] + (9 * u * sp) * lt + math.sin(lt * 0.5 + q["ph"]) * q["wob"]
                y = q["y"] - (6 * u * sp) * lt + math.cos(lt * 0.4 + q["ph"]) * q["wob"] * 0.6
                a = q["al"] * 0.55
            elif self.estilo == "luciernagas":
                x = q["x"] + math.sin(lt * 0.35 * sp + q["ph"]) * q["wob"] * 5
                y = q["y"] + math.cos(lt * 0.28 * sp + q["ph"] * 1.3) * q["wob"] * 3.5
                a = q["al"] * max(0.0, math.sin(lt * q["tw"] + q["ph"])) ** 2
            else:  # nieve
                x = q["x"] + math.sin(lt * 0.6 + q["ph"]) * q["wob"] + 14 * u * lt * 0.3
                y = q["y"] + (40 * u * sp) * lt
                a = q["al"] * 0.8
            x, y = x % W, y % H
            spr = self.sprites[q["b"]]
            blit(base, spr, x - spr.shape[1] / 2, y - spr.shape[0] / 2, a * env)
