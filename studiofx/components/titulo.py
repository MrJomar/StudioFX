import cv2
import numpy as np
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow
from ..easing import ease_out_cubic, fade_env, clamp
from ..textkit import text_w, line_h, new_layer, outline_text, wrap


def font_for_cap(theme, key, cap):
    """Fuente cuya altura de mayuscula mide `cap` px."""
    f = theme.font(key, 100)
    b = f.getbbox("H")
    return theme.font(key, cap / ((b[3] - b[1]) / 100.0))


@register("titulo_capitulo")
class TituloCapitulo(Component):
    """Tarjeta de capitulo/barrio: etiqueta con linea roja, numero en contorno translucido y titulo
    condensado en bloque (cada renglon ajustado al mismo ancho), sobre sombra lateral.
    Animacion: sombra -> letras de la etiqueta una a una -> linea roja se dibuja -> numero se traza
    de abajo hacia arriba y se rellena -> renglones del titulo suben desde una mascara.
    Datos: etiqueta, numero (opc), titulo."""
    layer = 40

    def build(self):
        u, th, d = self.u, self.theme, self.data
        W, H = self.W, self.H
        crema = th.color("crema")
        words = d["titulo"].upper().split()
        # --- reparto en renglones: el corte que minimiza el renglon mas largo ---
        total_chars = len(" ".join(words))
        n_lines = 1 if (total_chars <= 12 or len(words) == 1) else (2 if total_chars <= 30 or len(words) == 2 else 3)
        n_lines = min(n_lines, len(words))
        import itertools
        best, best_cost = None, None
        for cuts in itertools.combinations(range(1, len(words)), n_lines - 1):
            idx = (0,) + cuts + (len(words),)
            cand = [" ".join(words[idx[i]:idx[i + 1]]) for i in range(n_lines)]
            cost = max(len(c) for c in cand)
            if best_cost is None or cost < best_cost:
                best, best_cost = cand, cost
        lines = best
        # --- tamano: el bloque ocupa ~50% del ancho (58% si es un solo renglon) y max 40% del alto ---
        from PIL import ImageDraw
        base_cap = 0.165 * H
        f0 = font_for_cap(th, "titulo", base_cap)
        widths = [text_w(f0, ln) for ln in lines]
        maxw = max(widths)
        frac = 0.50 if len(lines) > 1 else 0.58
        kfit = frac * W / maxw
        caps = [base_cap * kfit * min(1.28, maxw / w0) for w0 in widths]
        gap = 0.03 * H
        tot = sum(caps) + gap * (len(lines) - 1)
        if tot > 0.40 * H:
            s_ = 0.40 * H / tot
            caps = [c * s_ for c in caps]
            gap *= s_
        self.lines = []
        total_h = 0
        for ln, cap in zip(lines, caps):
            f = font_for_cap(th, "titulo", cap)
            img = new_layer(int(text_w(f, ln)) + 12, line_h(f) + 12)
            ImageDraw.Draw(img).text((6, 6), ln, font=f, fill=crema)
            bbox = f.getbbox("H")
            cap_h = bbox[3] - bbox[1]
            sh, pad = with_shadow(img, blur=9 * u, offset=(0, 5 * u), opacity=0.55, pad=int(16 * u))
            self.lines.append(dict(spr=to_premul(sh), pad=pad, cap=cap_h, top=bbox[1] + 6, w=img.size[0], h=img.size[1]))
            total_h += cap_h
        total_h += gap * (len(lines) - 1)
        self.gap = gap
        self.block_h = total_h
        self.x0 = 0.257 * W
        self.top = 0.50 * H - total_h / 2 + 0.02 * H
        # --- numero en contorno ---
        self.num = None
        if d.get("numero") not in (None, ""):
            fnum = font_for_cap(th, "titulo", total_h)
            txt = str(d["numero"])
            st = max(2, int(3 * u))
            self.num_out = to_premul(outline_text(fnum, txt, (crema[0], crema[1], crema[2], 235), stroke=st))
            self.num_fill = to_premul(outline_text(fnum, txt, crema, stroke=st, fill_alpha=46, outline=False))
            b = fnum.getbbox("H")
            self.num_cap_top = b[1] + st + 3
            self.num_w = self.num_out.shape[1]
            self.num = True
        # --- etiqueta: letras sueltas con tracking ---
        fl = font_for_cap(th, "titulo", 0.043 * H)
        tr = 8 * u
        self.letters = []
        x = 0
        lab = d["etiqueta"].upper()
        for ch in lab:
            wch = fl.getlength(ch)
            if ch != " ":
                img = new_layer(int(wch) + 8, line_h(fl) + 8)
                ImageDraw.Draw(img).text((4, 4), ch, font=fl, fill=crema)
                s, p = with_shadow(img, blur=4 * u, offset=(0, 2 * u), opacity=0.6, pad=int(8 * u))
                self.letters.append((to_premul(s), p, x))
            x += wch + tr
        self.label_w = x - tr
        b = fl.getbbox("H")
        self.label_cap = b[3] - b[1]
        self.label_cap_top = b[1] + 4
        # --- linea roja ---
        lw = int(0.70 * W - (self.x0 + self.label_w + 26 * u))
        self.line_w = max(10, lw)
        ln = new_layer(self.line_w, max(2, int(3.2 * u)))
        ImageDraw.Draw(ln).rectangle([0, 0, self.line_w, int(3.2 * u) + 1], fill=th.color("rojo"))
        self.line = to_premul(ln)
        # --- sombra lateral ---
        xx = np.linspace(0, 1, W, dtype=np.float32)
        t = np.clip(1.0 - xx / 0.72, 0, 1)
        a = (t * t * (3 - 2 * t)) * 0.62
        sc = np.repeat(((1 - a) * 255).astype(np.uint8)[None, :, None], H, axis=0)
        self.scrim = np.repeat(sc, 3, axis=2)

    def apply(self, base, lt):
        u, W, H = self.u, self.W, self.H
        env = clamp(lt / 0.4) * clamp((self.dur - lt) / 0.35)
        dark = cv2.multiply(base, self.scrim, scale=1 / 255.0)
        base[:] = cv2.addWeighted(base, 1 - env, dark, env, 0)
        out = clamp((self.dur - lt) / 0.35)
        drift = -(1 - out) * 26 * u  # sin deriva en reposo: el texto queda quieto
        x0 = self.x0 + drift
        # etiqueta: letras escalonadas
        ly = self.top - 0.06 * H - self.label_cap
        for i, (spr, p, lx) in enumerate(self.letters):
            o = clamp((lt - 0.15 - i * 0.04) / 0.22) * out
            blit(base, spr, x0 + lx - p, ly - self.label_cap_top * 0 - p + (1 - o) * 12 * u, o)
        # linea roja se dibuja
        e = ease_out_cubic((lt - 0.35) / 0.7)
        lcy = ly + self.label_cap / 2 - self.line.shape[0] / 2 + 3 * u
        blit(base, self.line, x0 + self.label_w + 26 * u, lcy, out, clip_w=self.line_w * e)
        # numero: se traza de abajo hacia arriba y luego se rellena
        if self.num:
            h = self.num_out.shape[0]
            vis = int(h * ease_out_cubic((lt - 0.25) / 0.7))
            nx = x0 - 34 * u - self.num_w + 10
            ny = self.top - self.num_cap_top
            if vis > 0:
                blit(base, self.num_out[h - vis:], nx, ny + (h - vis), out)
            fo = clamp((lt - 0.8) / 0.5) * out
            blit(base, self.num_fill, nx, ny, fo)
        # renglones del titulo: suben desde una mascara
        y = self.top
        for i, L in enumerate(self.lines):
            e = ease_out_cubic((lt - 0.5 - i * 0.13) / 0.55)
            spr, pad = L["spr"], L["pad"]
            band = L["cap"] + 2 * pad  # ventana visible de la linea
            shift = (1 - e) * (L["cap"] + 10 * u)
            top_pad = pad + L["top"] - 6  # fila donde empieza la mayuscula dentro del sprite
            cut_bottom = int(top_pad + L["cap"] + pad * 0.6)  # no mostrar nada por debajo de la linea
            vis_h = int(max(0, cut_bottom - shift))
            if vis_h > 0:
                blit(base, spr[:vis_h], x0 - pad + 0, y - top_pad + shift, out * clamp(e * 3))
            y += L["cap"] + self.gap
