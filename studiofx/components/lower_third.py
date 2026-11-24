from PIL import ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow
from ..easing import ease_out_cubic, fade_env
from ..textkit import text_w, draw_tracked, line_h, new_layer, wrap, tracked_chip


@register("lower_third")
class LowerThird(Component):
    """Etiqueta de color + titulo en caja clara + subtitulo opcional.
    Datos: etiqueta, titulo, sub (opc), color (rojo|dorado|azul)."""
    layer = 60

    def build(self):
        u, th, dta = self.u, self.theme, self.data
        col = th.color(dta.get("color", "rojo"))
        chip = tracked_chip(th, dta.get("etiqueta", "").upper(), "sans_black", 9.5 * u,
                            (255, 255, 255, 255), col, 7 * u, 3 * u, 1.8 * u) if dta.get("etiqueta") else None
        ft = th.font("serif_bold", 25 * u)
        lines = wrap(ft, dta["titulo"], 0.62 * self.W)
        lh = line_h(ft)
        pad_x, pad_y = 14 * u, 7 * u
        tw = max(text_w(ft, ln) for ln in lines)
        bw, bh = int(tw + 2 * pad_x), int(lh * len(lines) + 2 * pad_y)
        box = new_layer(bw, bh)
        d = ImageDraw.Draw(box)
        d.rectangle([0, 0, bw, bh], fill=th.color("papel"))
        for i, ln in enumerate(lines):
            d.text((pad_x, pad_y + i * lh), ln, font=ft, fill=th.color("tinta"))
        parts = [chip, box]
        if dta.get("sub"):
            fs = th.font("serif_italic", 15 * u)
            sw = int(text_w(fs, dta["sub"]) + 20 * u)
            sh = int(line_h(fs) + 8 * u)
            sb = new_layer(sw, sh)
            sd = ImageDraw.Draw(sb)
            sd.rectangle([0, 0, sw, sh], fill=(18, 16, 14, 232))
            sd.text((10 * u, 4 * u), dta["sub"], font=fs, fill=(255, 255, 255, 255))
            parts.append(sb)
        parts = [p for p in parts if p is not None]
        W_ = max(p.size[0] for p in parts)
        H_ = sum(p.size[1] for p in parts)
        img = new_layer(W_, H_)
        y = 0
        for p in parts:
            img.alpha_composite(p, (0, y))
            y += p.size[1]
        img, self.pad = with_shadow(img, blur=6 * u, offset=(0, 3 * u), opacity=0.45, pad=int(14 * u))
        self.spr = to_premul(img)

    def apply(self, base, lt):
        u = self.u
        e_in = ease_out_cubic(lt / 0.5)
        o = fade_env(lt, self.dur, 0.12, 0.3)
        w, h = self.spr.shape[1], self.spr.shape[0]
        x = 30 * u - self.pad - (1 - e_in) * 26 * u
        y = self.H - 58 * u - (h - 2 * self.pad) - self.pad
        blit(base, self.spr, x, y, o, clip_w=w * min(1.0, 0.12 + e_in))
