import math
from PIL import Image, ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow, dim_blur, rotate_sprite
from ..easing import ease_out_cubic, fade_env, clamp
from ..textkit import text_w, line_h, new_layer


@register("polaroid")
class Polaroid(Component):
    """Foto con marco blanco que entra girando y se asienta; fondo oscurecido y desenfocado.
    Datos: src, pie (opc), angulo (opc), pos (centro|izq|der)."""
    layer = 25

    def build(self):
        u, th, d = self.u, self.theme, self.data
        img = Image.open(d["src"]).convert("RGB")
        maxw, maxh = 0.42 * self.W, 0.56 * self.H
        k = min(maxw / img.width, maxh / img.height)
        img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
        b = int(12 * u)
        cap = bool(d.get("pie"))
        bottom = int(46 * u) if cap else b
        w, h = img.width + 2 * b, img.height + b + bottom
        fr = new_layer(w, h)
        fd = ImageDraw.Draw(fr)
        fd.rectangle([0, 0, w, h], fill=(247, 245, 240, 255))
        fr.paste(img, (b, b))
        if cap:
            f = th.font("serif_italic", 19 * u)
            fd.text(((w - text_w(f, d["pie"])) / 2, b + img.height + (bottom - line_h(f)) / 2), d["pie"],
                    font=f, fill=th.color("tinta"))
        pad = int(0.18 * max(w, h))
        fr, self.pad = with_shadow(fr, blur=14 * u, offset=(0, 10 * u), opacity=0.55, pad=pad)
        self.spr = to_premul(fr)
        self.angle = float(d.get("angulo", -3))
        self.pos = d.get("pos", "centro")

    def apply(self, base, lt):
        u = self.u
        env = fade_env(lt, self.dur, 0.35, 0.35)
        dim_blur(base, env * 0.85, 0.5, 9)
        e = ease_out_cubic(lt / 0.65)
        ang = self.angle + (1 - e) * 10 + 0.45 * math.sin(lt * 1.4)
        kz = 1.0 + 0.035 * clamp(lt / self.dur)
        spr = rotate_sprite(self.spr, ang, kz)
        cx = {"centro": 0.5, "izq": 0.30, "der": 0.70}.get(self.pos, 0.5) * self.W
        cy = self.H / 2 + (1 - e) * 90 * u
        o = clamp(lt / 0.25) * clamp((self.dur - lt) / 0.3)
        blit(base, spr, cx - spr.shape[1] / 2, cy - spr.shape[0] / 2, o)
