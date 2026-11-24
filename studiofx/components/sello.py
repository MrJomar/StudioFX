import math
from PIL import ImageDraw, Image
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow, scale_sprite
from ..easing import ease_out_cubic, fade_env, clamp
from ..textkit import text_w, draw_tracked, line_h, new_layer, tracked_chip


@register("sello")
class Sello(Component):
    """Sello inclinado tipo 'NO NACIO AQUI' que 'cae' con impacto.
    Datos: sello, pretitulo (opc), sub (opc), angulo (opc, default -4)."""
    layer = 70

    def build(self):
        u, th, dta = self.u, self.theme, self.data
        rojo = th.color("rojo")
        f = th.font("sans_black", 34 * u)
        txt = dta["sello"].upper()
        tr = 1.2 * u
        px, py = 18 * u, 11 * u
        w = int(text_w(f, txt, tr) + 2 * px)
        h = int(line_h(f) + 2 * py)
        st = new_layer(w, h)
        d = ImageDraw.Draw(st)
        d.rectangle([0, 0, w - 1, h - 1], fill=th.color("papel"))
        d.rectangle([0, 0, w - 1, h - 1], outline=rojo, width=max(2, int(3 * u)))
        ins = int(6 * u)
        d.rectangle([ins, ins, w - 1 - ins, h - 1 - ins], outline=rojo, width=max(1, int(1.2 * u)))
        draw_tracked(d, (px, py - 1 * u), txt, f, rojo, tr)
        ang = float(dta.get("angulo", -4))
        st = st.rotate(-ang, resample=Image.BICUBIC, expand=True)
        st, self.pad = with_shadow(st, blur=7 * u, offset=(0, 5 * u), opacity=0.5, pad=int(16 * u))
        self.stamp = to_premul(st)
        self.pre = None
        self.sub = None
        if dta.get("pretitulo"):
            self.pre = to_premul(tracked_chip(th, dta["pretitulo"].upper(), "sans_bold", 11.5 * u,
                                              (255, 255, 255, 255), None, 2, 2, 3.5 * u))
        if dta.get("sub"):
            fs = th.font("serif_italic", 17 * u)
            sw, sh = int(text_w(fs, dta["sub"]) + 22 * u), int(line_h(fs) + 9 * u)
            sb = new_layer(sw, sh)
            sd = ImageDraw.Draw(sb)
            sd.rectangle([0, 0, sw, sh], fill=(18, 16, 14, 235))
            sd.text((11 * u, 4.5 * u), dta["sub"], font=fs, fill=(255, 255, 255, 255))
            self.sub = to_premul(sb)

    def apply(self, base, lt):
        u = self.u
        out = fade_env(lt, self.dur, 0.01, 0.3)
        right = self.W - 72 * u
        cy = self.H * 0.50
        sh, sw = self.stamp.shape[:2]
        # Impacto: escala 1.55 -> 1 en 0.17 s + temblor que decae.
        p = clamp(lt / 0.17)
        k = 1.0 + 0.55 * (1 - ease_out_cubic(p))
        o = clamp(lt / 0.09) * out
        spr = scale_sprite(self.stamp, k) if k > 1.003 else self.stamp
        shake = 0.0
        if lt > 0.17:
            shake = 5 * u * math.exp(-(lt - 0.17) * 16) * math.sin((lt - 0.17) * 70)
        w2, h2 = spr.shape[1], spr.shape[0]
        cx = right - sw / 2          # el sello escala alrededor de su centro
        x = cx - w2 / 2 + shake
        y = cy - h2 / 2
        blit(base, spr, x, y, o)
        inner_h = sh
        if self.pre is not None:
            po = clamp((lt - 0.22) / 0.25) * out
            blit(base, self.pre, right - self.pre.shape[1] - 4 * u, cy - inner_h / 2 + 4 * u + (1 - po) * 8 * u, po)
        if self.sub is not None:
            so = clamp((lt - 0.32) / 0.25) * out
            blit(base, self.sub, right - self.sub.shape[1] - 14 * u, cy + inner_h / 2 - 6 * u + (1 - so) * 8 * u, so)
