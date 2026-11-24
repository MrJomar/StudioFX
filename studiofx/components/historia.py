"""Componentes de historia y datos: recorte de periodico, linea de tiempo, comparador, barras."""
import re
import cv2
import numpy as np
from PIL import Image, ImageDraw
from .base import register
from .infografia import Stack
from ..compositing import to_premul, blit, with_shadow
from ..easing import ease_out_cubic, ease_in_out_cubic, clamp
from ..textkit import text_w, line_h, new_layer, wrap, draw_tracked
from ..infokit import rrect, circle


@register("recorte_periodico")
class RecortePeriodico(Stack):
    """Recorte de periodico viejo; las palabras entre *asteriscos* se subrayan con marcador.
    Datos: cabecera, texto, ancho (fraccion 0.3-0.8)."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        fw = float(d.get("ancho", 0.66))
        w = int(fw * self.W)
        f = th.font("serif", 34 * u)
        fb = th.font("serif_bold", 34 * u)
        fh = th.font("serif_bold", 21 * u)
        m = int(34 * u)
        # tokenizar palabras con bandera de resaltado
        toks = []
        for part in re.split(r"(\*[^*]+\*)", d["texto"]):
            if not part:
                continue
            hi = part.startswith("*")
            for wd in part.strip("*").split():
                toks.append((wd, hi))
        sp = text_w(f, " ")
        lines, cur, cw_ = [], [], 0.0
        for wd, hi in toks:
            ww = text_w(fb if hi else f, wd)
            if cur and cw_ + sp + ww > w - 2 * m:
                lines.append(cur)
                cur, cw_ = [], 0.0
            cur.append((wd, hi, ww))
            cw_ += (sp if len(cur) > 1 else 0) + ww
        if cur:
            lines.append(cur)
        lh = int(line_h(f) * 1.12)
        head_h = int(88 * u)
        h = int(head_h + len(lines) * lh + m)
        paper = Image.new("RGBA", (w, h), (233, 222, 192, 255))
        arr = np.array(paper).astype(np.float32)
        rng = np.random.default_rng(4)
        noise = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 1.2)
        arr[..., :3] += noise[..., None] * 9
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        edge = np.minimum(np.minimum(xx, w - xx), np.minimum(yy, h - yy))
        arr[..., :3] *= (0.80 + 0.20 * np.clip(edge / (28 * u), 0, 1))[..., None]
        paper = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        dd = ImageDraw.Draw(paper)
        ink = (44, 38, 30, 255)
        cab = d.get("cabecera", "").upper()
        fc = th.font("serif_bold", 26 * u)
        draw_tracked(dd, ((w - text_w(fc, cab, 2 * u)) / 2, 20 * u), cab, fc, ink, 2 * u)
        dd.line([(m, 62 * u), (w - m, 62 * u)], fill=ink, width=max(2, int(2 * u)))
        dd.line([(m, 68 * u), (w - m, 68 * u)], fill=ink, width=max(1, int(1 * u)))
        # texto sobre capa propia (los marcadores van debajo)
        txt = new_layer(w, h)
        td = ImageDraw.Draw(txt)
        hl = []
        for li, ln in enumerate(lines):
            x = m
            y = head_h + li * lh
            for wd, hi, ww in ln:
                td.text((x, y), wd, font=fb if hi else f, fill=ink)
                if hi:
                    hl.append((x - 4 * u, y + lh * 0.22, ww + 8 * u, lh * 0.66))
                x += ww + sp
        x0 = (self.W - w) / 2
        y0 = (self.H - h) / 2
        self.add(paper, x0, y0, 0.0, "slide", dy=40 * u)
        for k, (hx, hy, hw, hh) in enumerate(hl):
            mk = rrect(int(hw), int(hh), 4 * u, (255, 214, 40, 150))
            self.items.append(dict(spr=to_premul(mk), x=x0 + hx, y=y0 + hy, delay=0.9 + k * 0.45, mode="wipe", dx=0, dy=0))
        self.items.append(dict(spr=to_premul(txt), x=x0, y=y0, delay=0.0, mode="slide", dx=0, dy=40 * u))


@register("linea_tiempo")
class LineaTiempo(Stack):
    """Linea de tiempo horizontal animada. Datos: titulo (opc), eventos[{fecha,texto}]."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d["titulo"]) if d.get("titulo") else 0
        ev = d["eventos"]
        n = len(ev)
        mx = 120 * u
        ym = self.H * 0.56
        span = self.W - 2 * mx
        acc = th.color(d.get("acento", "naranja"))
        line_w = int(span)
        base = rrect(line_w, max(4, int(6 * u)), 3 * u, th.color("gris", 150) if not self.foto else (255, 255, 255, 120))
        self.add(base, mx, ym - 3 * u, 0.2, "wipe", shadow=False)
        fill = rrect(line_w, max(4, int(6 * u)), 3 * u, acc)
        self.items.append(dict(spr=to_premul(fill), x=mx, y=ym - 3 * u, delay=0.5, mode="wipe", dx=0, dy=0, t=0.9 * max(1, n - 1)))
        ff = th.font("serif_bold", 50 * u)
        ft = th.font("sans_bold", 27 * u)
        for i, e in enumerate(ev):
            cx = mx + span * (i / max(1, n - 1))
            t0 = 0.5 + i * (0.9)
            dot = circle(int(30 * u), (255, 255, 255, 255))
            dot.alpha_composite(circle(int(18 * u), acc), (int(6 * u), int(6 * u)))
            self.add(dot, cx - 15 * u, ym - 15 * u, t0, "pop")
            up = i % 2 == 0
            fg = th.color("blanco") if self.foto else th.color("tinta")
            lines = wrap(ft, e["texto"], 290 * u, max_lines=4)
            wcard = int(max(text_w(ft, ln) for ln in lines) + 8)
            wcard = max(wcard, int(text_w(ff, e["fecha"])) + 8)
            hcard = int(line_h(ff) + len(lines) * line_h(ft) + 10 * u)
            img = new_layer(wcard, hcard)
            dd = ImageDraw.Draw(img)
            dd.text((4, 0), e["fecha"], font=ff, fill=acc)
            for j, ln in enumerate(lines):
                dd.text((4, line_h(ff) + 6 * u + j * line_h(ft)), ln, font=ft, fill=fg)
            ty = ym - 40 * u - hcard if up else ym + 40 * u
            tx = min(max(cx - wcard / 2, 40 * u), self.W - 40 * u - wcard)
            self.add(img, tx, ty, t0 + 0.15, dy=(18 * u if up else -18 * u) * -1, shadow=self.foto)


@register("comparador")
class Comparador(Stack):
    """Antes / despues con barra deslizante. Datos: src_a, src_b, etiqueta_a, etiqueta_b, titulo (opc)."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d["titulo"]) if d.get("titulo") else 40 * u
        mw, mh = 0.78 * self.W, self.H - y0 - 50 * u
        self.box = None
        a = Image.open(d["src_a"]).convert("RGB")
        k = min(mw / a.width, mh / a.height)
        w, h = int(a.width * k), int(a.height * k)
        self.A = np.array(a.resize((w, h), Image.LANCZOS))
        self.B = np.array(Image.open(d["src_b"]).convert("RGB").resize((w, h), Image.LANCZOS))
        self.bx, self.by = int((self.W - w) / 2), int(y0 + (self.H - y0 - h) / 2 - 10 * u)
        fr = rrect(w + int(20 * u), h + int(20 * u), 8 * u, (255, 255, 255, 255))
        self.frame_spr, self.fpad = with_shadow(fr, blur=14 * u, offset=(0, 8 * u), opacity=0.35, pad=int(24 * u))
        self.frame_spr = to_premul(self.frame_spr)
        self.w, self.h = w, h
        hd = int(46 * u)
        handle = circle(hd, (255, 255, 255, 255))
        dd = ImageDraw.Draw(handle)
        c_, t_ = hd / 2, hd * 0.16
        tc = th.color("tinta")
        dd.polygon([(c_ - t_ * 0.6, c_ - t_), (c_ - t_ * 0.6, c_ + t_), (c_ - t_ * 2.0, c_)], fill=tc)
        dd.polygon([(c_ + t_ * 0.6, c_ - t_), (c_ + t_ * 0.6, c_ + t_), (c_ + t_ * 2.0, c_)], fill=tc)
        self.handle = to_premul(with_shadow(handle, blur=5 * u, offset=(0, 2 * u), opacity=0.5, pad=int(8 * u))[0])
        self.hpad = int(8 * u)
        self.hd = hd
        self.tags = []
        for key, defv, side in (("etiqueta_a", "ANTES", 0), ("etiqueta_b", "DESPUÉS", 1)):
            from ..infokit import pill
            p = pill(th, d.get(key, defv).upper(), "sans_black", 17 * u, (255, 255, 255, 255), (30, 28, 26, 220),
                     16 * u, 7 * u, 3 * u)
            self.tags.append((to_premul(p), side))

    def apply(self, base, lt):
        u = self.u
        from ..easing import fade_env
        o = fade_env(lt, self.dur, 0.4, 0.35)
        blit(base, self.frame_spr, self.bx - 10 * u - self.fpad, self.by - 10 * u - self.fpad, o)
        p = ease_in_out_cubic(clamp((lt - 0.7) / max(0.5, self.dur - 1.6)))
        dx = int(self.w * (0.08 + 0.84 * p))
        reg = base[self.by:self.by + self.h, self.bx:self.bx + self.w]
        mix = np.concatenate([self.A[:, :dx], self.B[:, dx:]], axis=1)
        reg[:] = cv2.addWeighted(reg, 1 - o, mix, o, 0)
        reg[:, max(0, dx - 2):dx + 2] = (255 * o + reg[:, max(0, dx - 2):dx + 2] * (1 - o)).astype(np.uint8)
        blit(base, self.handle, self.bx + dx - self.hd / 2 - self.hpad, self.by + self.h / 2 - self.hd / 2 - self.hpad, o)
        for spr, side in self.tags:
            x = self.bx + 16 * u if side == 0 else self.bx + self.w - spr.shape[1] - 16 * u
            blit(base, spr, x, self.by + 16 * u, o * (1.0 if (side == 0) == (dx > 70 * u) or side == 1 and dx < self.w - 70 * u else 0.0))
        super().apply(base, lt)


@register("barras")
class Barras(Stack):
    """Grafica de barras horizontal animada. Datos: titulo, datos[{etiqueta,valor}], sufijo (opc), formato."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d.get("titulo", ""))
        rows = d["datos"]
        n = len(rows)
        vmax = max(float(r["valor"]) for r in rows)
        sufijo = d.get("sufijo", "")
        rh = min(70 * u, (self.H - y0 - 60 * u) / n - 14 * u)
        lw = 0.22 * self.W
        bw = 0.52 * self.W
        y = y0 + max(0.0, (self.H - y0 - 40 * u - n * (rh + 14 * u)) / 2)
        fl = th.font("sans_bold", rh * 0.42)
        fv = th.font("sans_black", rh * 0.46)
        fg = th.color("blanco") if self.foto else th.color("tinta")
        cols = [th.color(c) for c in ("naranja", "verde", "azul", "amarillo", "rojo")]
        for i, r in enumerate(rows):
            t0 = 0.4 + i * 0.35
            lab = new_layer(int(lw), int(rh))
            lines = wrap(fl, r["etiqueta"], lw - 8 * u, max_lines=2)
            ImageDraw.Draw(lab).multiline_text((0, (rh - len(lines) * line_h(fl)) / 2), "\n".join(lines), font=fl,
                                                fill=fg, align="left")
            self.add(lab, 90 * u, y + i * (rh + 14 * u), t0, dx=-20 * u, dy=0, shadow=False)
            wbar = max(8, int(bw * float(r["valor"]) / vmax))
            bar = rrect(wbar, int(rh * 0.78), rh * 0.2, cols[i % len(cols)] if d.get("multicolor") else th.color(d.get("acento", "naranja")))
            self.items.append(dict(spr=to_premul(bar), x=90 * u + lw, y=y + i * (rh + 14 * u) + rh * 0.11,
                                   delay=t0, mode="wipe", dx=0, dy=0))
            val = ("{:,}".format(int(r["valor"])) if float(r["valor"]).is_integer() else str(r["valor"])) + sufijo
            vt = new_layer(int(text_w(fv, val)) + 10, line_h(fv) + 4)
            ImageDraw.Draw(vt).text((4, 0), val, font=fv, fill=fg)
            self.add(vt, 90 * u + lw + wbar + 14 * u, y + i * (rh + 14 * u) + (rh - line_h(fv)) / 2, t0 + 0.6, dx=-14 * u,
                     dy=0, shadow=False)
