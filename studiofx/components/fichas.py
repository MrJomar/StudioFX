from PIL import ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow, dim_blur
from ..easing import ease_out_back, ease_out_cubic, fade_env, clamp
from ..textkit import text_w, draw_tracked, line_h, new_layer, wrap, tracked_chip


@register("fichas_versiones")
class FichasVersiones(Component):
    """2-3 fichas de papel con cinta de color, valor grande y texto.
    Oscurece y desenfoca el fondo mientras estan en pantalla.
    Datos: titulo, fichas[{etiqueta,color,valor,texto,fuente}], conclusion (opc)."""
    layer = 30

    def build(self):
        u, th, dta = self.u, self.theme, self.data
        fichas = dta["fichas"]
        n = len(fichas)
        gap = 22 * u
        cw = min(0.30 * self.W, (0.82 * self.W - (n - 1) * gap) / n)
        self.cw = int(cw)
        # Dos pasadas: primero medir la altura natural y luego igualar todas las fichas.
        hs = [self._card(f)[2] for f in fichas]
        self.cards = [self._card(f, max(hs))[:2] for f in fichas]
        self.gap = gap
        self.title = None
        if dta.get("titulo"):
            self.title = to_premul(tracked_chip(th, dta["titulo"].upper(), "sans_black", 13 * u,
                                                (255, 255, 255, 255), th.color("rojo"), 14 * u, 6 * u, 4 * u))
        self.concl = None
        if dta.get("conclusion"):
            c = tracked_chip(th, dta["conclusion"].upper(), "sans_black", 12.5 * u,
                             th.color("dorado"), (18, 16, 14, 225), 18 * u, 8 * u, 2.6 * u)
            d = ImageDraw.Draw(c)
            d.rectangle([0, 0, c.size[0] - 1, c.size[1] - 1], outline=th.color("dorado"), width=max(1, int(1.5 * u)))
            self.concl = to_premul(c)

    def _card(self, f, force_h=None):
        u, th = self.u, self.theme
        w = self.cw
        pad = 16 * u
        ribbon = tracked_chip(th, f.get("etiqueta", "").upper(), "sans_black", 10 * u,
                              (255, 255, 255, 255), th.color(f.get("color", "rojo")), 12 * u, 5 * u, 1.8 * u)
        fv = th.font("serif_bold", 56 * u)
        val = f["valor"]
        size = 56 * u
        while text_w(fv, val) > w - 2 * pad and size > 22 * u:
            size -= 2 * u
            fv = th.font("serif_bold", size)
        ft = th.font("serif", 15 * u)
        lines = wrap(ft, f.get("texto", ""), w - 2 * pad, max_lines=4)
        fs = th.font("sans", 8 * u)
        lh = line_h(ft)
        h = int(ribbon.size[1] + 14 * u + line_h(fv) + 8 * u + 3 * u + 10 * u + lh * max(1, len(lines)) + 12 * u + line_h(fs) + 12 * u)
        h = int(force_h) if force_h else h
        natural_h = h
        img = new_layer(w, h)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, w, h], fill=th.color("papel"))
        img.alpha_composite(ribbon, (0, 0))
        y = ribbon.size[1] + 10 * u
        d.text((pad, y), val, font=fv, fill=th.color("tinta"))
        y += line_h(fv) + 6 * u
        d.rectangle([pad, y, pad + 30 * u, y + 3 * u], fill=th.color(f.get("color", "rojo")))
        y += 13 * u
        for ln in lines:
            d.text((pad, y), ln, font=ft, fill=(52, 48, 44, 255))
            y += lh
        if f.get("fuente"):
            d.text((pad, h - line_h(fs) - 10 * u), f["fuente"], font=fs, fill=th.color("gris"))
        img, p = with_shadow(img, blur=10 * u, offset=(0, 8 * u), opacity=0.5, pad=int(26 * u))
        return to_premul(img), p, natural_h

    def apply(self, base, lt):
        u, th = self.u, self.theme
        env = fade_env(lt, self.dur, 0.35, 0.35)
        dim_blur(base, env, th.get("fondo_fichas", "oscurecer", default=0.6), th.get("fondo_fichas", "blur", default=9))
        out = clamp((self.dur - lt) / 0.3)
        n = len(self.cards)
        total_w = n * self.cw + (n - 1) * self.gap
        x0 = (self.W - total_w) / 2
        cy = self.H * 0.50
        if self.title is not None:
            o = clamp((lt - 0.1) / 0.25) * out
            blit(base, self.title, (self.W - self.title.shape[1]) / 2, self.H * 0.17 + (1 - o) * 10 * u, o)
        for i, (spr, pad) in enumerate(self.cards):
            s = 0.2 + i * 0.13
            p = (lt - s) / 0.55
            if p <= 0:
                continue
            e = ease_out_back(p, 1.2)
            o = clamp(p * 2.2) * out
            h = spr.shape[0] - 2 * pad
            x = x0 + i * (self.cw + self.gap) - pad
            y = cy - h / 2 - pad + (1 - e) * 70 * u
            blit(base, spr, x, y, o)
        if self.concl is not None:
            s = 0.2 + n * 0.13 + 0.25
            o = clamp((lt - s) / 0.3) * out
            blit(base, self.concl, (self.W - self.concl.shape[1]) / 2, self.H * 0.84 + (1 - o) * 10 * u, o)
