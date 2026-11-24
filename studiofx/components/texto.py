import math
from PIL import ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow, dim_blur, scale_sprite
from ..easing import ease_out_cubic, ease_out_back, fade_env, clamp
from ..textkit import text_w, line_h, new_layer, wrap


@register("subtitulo")
class Subtitulo(Component):
    """Subtitulo narrativo en cursiva sobre banda oscura. Con palabra_a_palabra=true el texto se
    'ilumina' de izquierda a derecha como karaoke (efecto nuevo; luego se amarra a Whisper).
    Datos: texto, palabra_a_palabra (opc), reveal (opc, seg)."""
    layer = 65

    def build(self):
        u, th, d = self.u, self.theme, self.data
        f = th.font("serif_italic", 24 * u)
        self.lines = wrap(f, d["texto"], 0.72 * self.W)
        self.karaoke = bool(d.get("palabra_a_palabra", False))
        px, py = 13 * u, 5 * u
        self.bright, self.dim = [], []
        for ln in self.lines:
            w, h = int(text_w(f, ln) + 2 * px), int(line_h(f) + 2 * py)
            for lst, alpha in ((self.bright, 255), (self.dim, 105)):
                img = new_layer(w, h)
                dd = ImageDraw.Draw(img)
                dd.rectangle([0, 0, w, h], fill=(18, 16, 14, 165))
                dd.text((px, py), ln, font=f, fill=(255, 255, 255, alpha))
                lst.append(to_premul(img))
        self.lens = [max(1, len(ln)) for ln in self.lines]

    def apply(self, base, lt):
        u = self.u
        env = fade_env(lt, self.dur, 0.3, 0.3)
        n = len(self.lines)
        lh = self.bright[0].shape[0]
        y0 = self.H - 70 * u - n * lh + (1 - clamp(lt / 0.3)) * 10 * u
        total = sum(self.lens)
        rev = float(self.data.get("reveal", 0.75 * self.dur))
        done = clamp((lt - 0.2) / max(rev, 0.1)) * total
        start = 0
        for i in range(n):
            w = self.bright[i].shape[1]
            x = (self.W - w) / 2
            y = y0 + i * lh
            if self.karaoke:
                blit(base, self.dim[i], x, y, env)
                frac = clamp((done - start) / self.lens[i])
                blit(base, self.bright[i], x, y, env, clip_w=w * frac)
            else:
                blit(base, self.bright[i], x, y, env)
            start += self.lens[i]


@register("callout")
class Callout(Component):
    """Rombo dorado con anillo pulsante, linea y etiqueta que senala un punto de la imagen.
    Datos: x, y (0..1), texto, lado (der|izq)."""
    layer = 66

    def build(self):
        u, th, d = self.u, self.theme, self.data
        from PIL import Image
        s = int(13 * u)
        dia = new_layer(s * 2, s * 2)
        dd = ImageDraw.Draw(dia)
        c = s
        dd.polygon([(c, c - s * 0.7), (c + s * 0.7, c), (c, c + s * 0.7), (c - s * 0.7, c)], fill=th.color("dorado"),
                   outline=(18, 16, 14, 255))
        self.dia = to_premul(dia)
        r = int(16 * u)
        ring = new_layer(r * 2 + 4, r * 2 + 4)
        ImageDraw.Draw(ring).ellipse([2, 2, r * 2 + 2, r * 2 + 2], outline=th.color("dorado"), width=max(2, int(2 * u)))
        self.ring = to_premul(ring)
        f = th.font("sans_bold", 13 * u)
        t = d["texto"]
        w, h = int(text_w(f, t) + 22 * u), int(line_h(f) + 10 * u)
        lab = new_layer(w, h)
        ld = ImageDraw.Draw(lab)
        ld.rectangle([0, 0, w, h], fill=th.color("papel"))
        ld.text((11 * u, 5 * u), t, font=f, fill=th.color("tinta"))
        lab, self.lpad = with_shadow(lab, blur=5 * u, offset=(0, 3 * u), opacity=0.5, pad=int(10 * u))
        self.lab = to_premul(lab)
        self.llen = int(38 * u)
        ln = new_layer(self.llen, max(2, int(2 * u)))
        ImageDraw.Draw(ln).rectangle([0, 0, self.llen, 4 * u], fill=th.color("dorado"))
        self.line = to_premul(ln)
        self.right = d.get("lado", "der") != "izq"

    def apply(self, base, lt):
        u = self.u
        px, py = self.data["x"] * self.W, self.data["y"] * self.H
        out = clamp((self.dur - lt) / 0.3)
        e = ease_out_back(lt / 0.3, 1.5)
        d = scale_sprite(self.dia, max(0.01, e)) if e < 0.999 or e > 1.001 else self.dia
        o = clamp(lt / 0.12) * out
        # anillo pulsante
        if lt > 0.15:
            ph = ((lt - 0.15) / 1.3) % 1.0
            rg = scale_sprite(self.ring, 0.6 + 1.7 * ph)
            blit(base, rg, px - rg.shape[1] / 2, py - rg.shape[0] / 2, (1 - ph) * 0.85 * out)
        blit(base, d, px - d.shape[1] / 2, py - d.shape[0] / 2, o)
        # linea + etiqueta
        gl = ease_out_cubic((lt - 0.2) / 0.3)
        dx = 10 * u
        if self.right:
            blit(base, self.line, px + dx, py - self.line.shape[0] / 2, out, clip_w=self.llen * gl)
            lo = clamp((lt - 0.45) / 0.3) * out
            blit(base, self.lab, px + dx + self.llen - self.lpad - (1 - lo) * 12 * u,
                 py - (self.lab.shape[0] - 2 * self.lpad) / 2 - self.lpad, lo)
        else:
            lw = int(self.llen * gl)
            blit(base, self.line[:, self.llen - lw:], px - dx - lw, py - self.line.shape[0] / 2, out)
            lo = clamp((lt - 0.45) / 0.3) * out
            wl = self.lab.shape[1] - 2 * self.lpad
            blit(base, self.lab, px - dx - self.llen - wl - self.lpad + (1 - lo) * 12 * u,
                 py - (self.lab.shape[0] - 2 * self.lpad) / 2 - self.lpad, lo)


@register("frase_destacada")
class FraseDestacada(Component):
    """Frase grande centrada con marcador dorado que se 'pinta' sobre las palabras clave (efecto nuevo).
    Datos: texto, destacar (lista de palabras)."""
    layer = 28

    def build(self):
        u, th, d = self.u, self.theme, self.data
        f = th.font("display", 46 * u)
        words = d["texto"].split()
        maxw = 0.74 * self.W
        sp = f.getlength(" ")

        def greedy(mw):
            out, cur, cw = [], [], 0
            for w in words:
                ww = f.getlength(w)
                if cur and cw + sp + ww > mw:
                    out.append(cur)
                    cur, cw = [], 0
                cur.append(w)
                cw += (sp if len(cur) > 1 else 0) + ww
            if cur:
                out.append(cur)
            return out

        lines = greedy(maxw)
        # Balancear: mismo numero de renglones pero lo mas parejos posible (evita palabras sueltas).
        lo, hi = 0.3 * maxw, maxw
        for _ in range(14):
            mid = (lo + hi) / 2
            if len(greedy(mid)) <= len(lines):
                hi = mid
            else:
                lo = mid
        lines = greedy(hi)
        lh = line_h(f)
        gap = 8 * u
        hl = [x.lower().strip(".,;:!?¿¡\"'«»") for x in d.get("destacar", [])]
        placed = []  # (word, x, y)
        y = 0
        maxlw = 0
        for ln in lines:
            lw = sum(f.getlength(w) for w in ln) + sp * (len(ln) - 1)
            maxlw = max(maxlw, lw)
        self.bw, self.bh = int(maxlw + 40), int(len(lines) * (lh + gap) + 20)
        base_img = new_layer(self.bw, self.bh)
        bd = ImageDraw.Draw(base_img)
        self.marks = []
        for ln in lines:
            lw = sum(f.getlength(w) for w in ln) + sp * (len(ln) - 1)
            x = (self.bw - lw) / 2
            for w in ln:
                bd.text((x, y + 10), w, font=f, fill=(255, 255, 255, 255))
                key = w.lower().strip(".,;:!?¿¡\"'«»")
                if key in hl:
                    ww = int(f.getlength(w)) + int(14 * u)
                    mk = new_layer(ww, lh)
                    md = ImageDraw.Draw(mk)
                    md.rectangle([0, int(lh * 0.14), ww, int(lh * 0.98)], fill=th.color("dorado"))
                    md.text((7 * u, 10 - 2 * u), w, font=f, fill=th.color("tinta"))
                    self.marks.append((to_premul(mk), x - 7 * u, y))
                x += f.getlength(w) + sp
            y += lh + gap
        sh, self.pad = with_shadow(base_img, blur=6 * u, offset=(0, 3 * u), opacity=0.7, pad=int(14 * u))
        self.base = to_premul(sh)

    def apply(self, base, lt):
        u = self.u
        env = fade_env(lt, self.dur, 0.35, 0.35)
        dim_blur(base, env * 0.6, 0.5, 7)
        out = clamp((self.dur - lt) / 0.3)
        x = (self.W - (self.base.shape[1] - 2 * self.pad)) / 2 - self.pad
        y = (self.H - (self.base.shape[0] - 2 * self.pad)) / 2 - self.pad
        o = clamp(lt / 0.35) * out
        yy = y + (1 - ease_out_cubic(lt / 0.5)) * 14 * u
        blit(base, self.base, x, yy, o)
        for i, (spr, mx, my) in enumerate(self.marks):
            s = 0.55 + i * 0.5
            p = ease_out_cubic((lt - s) / 0.4)
            if p > 0:
                blit(base, spr, x + self.pad + mx - 0, yy + self.pad + my - 10 + 10, out, clip_w=spr.shape[1] * p)
