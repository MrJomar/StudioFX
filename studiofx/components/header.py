from PIL import ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow
from ..easing import fade_env
from ..textkit import text_w, draw_tracked, line_h, new_layer, tracked_chip


@register("barra_superior")
class BarraSuperior(Component):
    """Texto pequeno fijo arriba a la izquierda (todo el video)."""
    layer = 100

    def build(self):
        u, th = self.u, self.theme
        f = th.font("sans_bold", 10 * u)
        txt = self.data["texto"].upper()
        tr = 1.8 * u
        sq = int(6 * u)
        w = int(text_w(f, txt, tr) + sq + 10 * u + 6)
        h = int(line_h(f) + 4)
        img = new_layer(w, h)
        d = ImageDraw.Draw(img)
        cy = h // 2
        d.rectangle([0, cy - sq // 2, sq, cy + sq // 2], fill=th.color("rojo"))
        draw_tracked(d, (sq + 8 * u, 1), txt, f, (255, 255, 255, 235), tr)
        img, self.pad = with_shadow(img, blur=3 * u, offset=(0, 1), opacity=0.7, pad=int(6 * u))
        self.spr = to_premul(img)

    def apply(self, base, lt):
        blit(base, self.spr, 22 * self.u - self.pad, 15 * self.u - self.pad, 0.85)


@register("credito")
class Credito(Component):
    """Credito de la imagen, abajo a la derecha."""
    layer = 90

    def build(self):
        u, th = self.u, self.theme
        f = th.font("sans", 8.5 * u)
        txt = self.data["texto"]
        w, h = int(text_w(f, txt) + 4), int(line_h(f) + 4)
        img = new_layer(w, h)
        ImageDraw.Draw(img).text((2, 1), txt, font=f, fill=(255, 255, 255, 255))
        img, self.pad = with_shadow(img, blur=2 * u, offset=(0, 1), opacity=0.8, pad=int(5 * u))
        self.spr = to_premul(img)

    def apply(self, base, lt):
        o = fade_env(lt, self.dur, 0.4, 0.4) * 0.6
        w = self.spr.shape[1] - 2 * self.pad
        blit(base, self.spr, self.W - 14 * self.u - w - self.pad, self.H - 12 * self.u - (self.spr.shape[0] - 2 * self.pad) - self.pad, o)


@register("etiqueta_sup")
class EtiquetaSup(Component):
    """Etiqueta arriba a la derecha (ej. 'IMAGEN ILUSTRATIVA', 'CENTRO HISTORICO')."""
    layer = 90

    def build(self):
        u, th = self.u, self.theme
        chip = tracked_chip(th, self.data["texto"].upper(), "sans_bold", 8.5 * u,
                            (255, 255, 255, 255), (20, 18, 16, 215), 7 * u, 3 * u, 1.6 * u)
        self.spr = to_premul(chip)

    def apply(self, base, lt):
        o = fade_env(lt, self.dur, 0.4, 0.4)
        w = self.spr.shape[1]
        blit(base, self.spr, self.W - 18 * self.u - w, 15 * self.u, o)
