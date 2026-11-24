"""Componentes de estilo infografia (fondo claro de papel o sobre foto oscurecida)."""
import math
import numpy as np
from PIL import Image, ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow, dim_blur, scale_sprite, rotate_sprite
from ..easing import ease_out_cubic, ease_out_back, fade_env, clamp
from ..textkit import text_w, line_h, new_layer, wrap, draw_tracked
from ..infokit import rrect, circle, icon, pill, lerp_col


class Stack(Component):
    """Base: lista de elementos con entrada escalonada. Cada item:
       spr (premultiplicado), x, y (esquina visible), pad, delay, mode (slide|pop|wipe|wipe_v|sello), dx, dy."""
    layer = 40

    def build(self):
        self.items = []
        self.foto = bool(self.data.get("sobre_foto", False))
        self.layout()

    def col(self, c):
        return self.theme.color(c) if isinstance(c, str) else tuple(c[:3]) + (255,)

    def add(self, img, x, y, delay=0.0, mode="slide", shadow=True, dx=0.0, dy=None):
        u = self.u
        pad = 0
        if shadow:
            img, pad = with_shadow(img, blur=9 * u, offset=(0, 5 * u), opacity=0.22 if not self.foto else 0.45,
                                   pad=int(18 * u))
        self.items.append(dict(spr=to_premul(img), x=x - pad, y=y - pad, delay=delay, mode=mode, dx=dx,
                               dy=(14 * u if dy is None else dy)))

    def titulo(self, text, y=62, color=None):
        u, th = self.u, self.theme
        color = color or (th.color("blanco") if self.foto else th.color("tinta"))
        f = th.font("sans_black", 32 * u)
        tr = 4 * u
        txt = text.upper()
        w = int(text_w(f, txt, tr)) + 8
        img = new_layer(w, line_h(f) + 6)
        draw_tracked(ImageDraw.Draw(img), (2, 2), txt, f, color, tr)
        self.add(img, 90 * u, y * u, 0.0, "slide", shadow=self.foto)
        bar = rrect(int(70 * u), max(3, int(6 * u)), 3 * u, self.col(self.data.get("acento", "naranja")))
        self.add(bar, 92 * u, y * u + line_h(f) + 10 * u, 0.15, "wipe", shadow=False)
        return y * u + line_h(f) + 30 * u

    def apply(self, base, lt):
        u = self.u
        env = fade_env(lt, self.dur, 0.3, 0.35)
        if self.foto:
            dim_blur(base, env * 0.92, 0.38, 9)
        out = clamp((self.dur - lt) / 0.3)
        for it in self.items:
            l2 = lt - it["delay"]
            if l2 <= 0:
                continue
            spr, x, y = it["spr"], it["x"], it["y"]
            m = it["mode"]
            e = ease_out_cubic(l2 / 0.5)
            o = clamp(l2 / 0.3) * out
            if m == "pop":
                k = 0.55 + 0.45 * ease_out_back(clamp(l2 / 0.5), 1.8)
                s2 = scale_sprite(spr, k) if abs(k - 1) > 0.004 else spr
                x += (spr.shape[1] - s2.shape[1]) / 2
                y += (spr.shape[0] - s2.shape[0]) / 2
                blit(base, s2, x, y, o)
            elif m == "wipe":
                blit(base, spr, x, y, out, clip_w=spr.shape[1] * ease_out_cubic(l2 / it.get("t", 0.7)))
            elif m == "wipe_v":
                h = int(spr.shape[0] * ease_out_cubic(l2 / it.get("t", 0.8)))
                if h > 0:
                    blit(base, spr[:h], x, y, out)
            elif m == "sello":
                k = 1.0 + 0.9 * (1 - ease_out_cubic(l2 / 0.22))
                s2 = scale_sprite(spr, k) if k > 1.004 else spr
                x += (spr.shape[1] - s2.shape[1]) / 2
                y += (spr.shape[0] - s2.shape[0]) / 2
                blit(base, s2, x, y, clamp(l2 / 0.12) * out * 0.95)
            else:
                blit(base, spr, x + (1 - e) * it["dx"], y + (1 - e) * it["dy"], o)

    # --- piezas comunes ---
    def centrar(self, y0, n, alto, sep=14):
        """Y inicial para centrar un bloque de n filas en el espacio bajo el titulo."""
        u = self.u
        total = n * alto + (n - 1) * sep * u
        avail = self.H - y0 - 30 * u
        return y0 + max(0.0, (avail - total) / 2) - 10 * u

    def fila(self, text, ancho, alto, icono_img, delay, tcolor=None):
        """Tarjeta blanca con icono a la izquierda y texto (se reduce hasta caber)."""
        u, th = self.u, self.theme
        card = rrect(ancho, alto, 14 * u, (255, 255, 255, 255))
        isz = icono_img.width if icono_img is not None else 0
        left = 18 * u + (isz + 16 * u if icono_img is not None else 8 * u)
        maxw = ancho - left - 20 * u
        size = alto * 0.46
        while size > 13 * u:
            f = th.font("sans_bold", size)
            lines = wrap(f, text, maxw, max_lines=2)
            if len(lines) * line_h(f) <= alto - 12 * u and all(text_w(f, ln) <= maxw for ln in lines):
                break
            size -= 1.5 * u
        d = ImageDraw.Draw(card)
        lh = line_h(f)
        y0 = (alto - lh * len(lines)) / 2
        for i, ln in enumerate(lines):
            d.text((left, y0 + i * lh), ln, font=f, fill=tcolor or th.color("tinta"))
        if icono_img is not None:
            card.alpha_composite(icono_img, (int(18 * u), int((alto - isz) / 2)))
        return card

    def imagen_lateral(self, src, cx, cy, ancho, delay, angulo=3):
        u = self.u
        img = Image.open(src).convert("RGB")
        k = ancho / img.width
        img = img.resize((int(ancho), max(1, int(img.height * k))), Image.LANCZOS)
        b = int(10 * u)
        fr = Image.new("RGBA", (img.width + 2 * b, img.height + 2 * b), (255, 255, 255, 255))
        fr.paste(img, (b, b))
        mask = rrect(fr.width, fr.height, 10 * u, (255, 255, 255, 255)).split()[3]
        fr.putalpha(mask)
        spr_img, pad = with_shadow(fr, blur=12 * u, offset=(0, 8 * u), opacity=0.35, pad=int(0.2 * max(fr.size)))
        spr = rotate_sprite(to_premul(spr_img), angulo)
        self.items.append(dict(spr=spr, x=cx - spr.shape[1] / 2, y=cy - spr.shape[0] / 2, delay=delay,
                               mode="pop", dx=0, dy=0))


@register("lista_video")
class ListaVideo(Stack):
    """'EN ESTE VIDEO': filas numeradas que aparecen una a una, con insignias en degradado verde.
    Datos: titulo, items[], paso (s), src (imagen lateral opc), sobre_foto (opc)."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d.get("titulo", "En este video"))
        items = d["items"]
        n = len(items)
        con_img = bool(d.get("src"))
        cw = int((0.52 if con_img else 0.66) * self.W)
        rh = int(min(100 * u, (self.H - y0 - 50 * u) / n - 14 * u))
        paso = float(d.get("paso", 0.55))
        y0 = self.centrar(y0, n, rh)
        v1, v2 = (120, 200, 120), th.color("verde")
        for i, t in enumerate(items):
            bd = int(rh * 0.62)
            badge = circle(bd, lerp_col(v1, v2, i / max(1, n - 1)))
            dd = ImageDraw.Draw(badge)
            f = th.font("sans_black", bd * 0.55)
            s = str(i + 1)
            dd.text(((bd - text_w(f, s)) / 2, (bd - line_h(f)) / 2 - bd * 0.02), s, font=f, fill=(255, 255, 255, 255))
            self.add(self.fila(t, cw, rh, badge, 0.5 + i * paso), 90 * u, y0 + i * (rh + 14 * u), 0.5 + i * paso,
                     dx=-40 * u, dy=0)
        if con_img:
            self.imagen_lateral(d["src"], 0.80 * self.W, 0.50 * self.H, 0.28 * self.W, 0.6)


@register("checklist")
class Checklist(Stack):
    """Lista con iconos ✓ / ✗ / !. Datos: titulo, items[{texto,tipo:ok|no|alerta}] o textos, paso, src (opc)."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d.get("titulo", "Revisión honesta"))
        items = [i if isinstance(i, dict) else dict(texto=i, tipo="ok") for i in d["items"]]
        n = len(items)
        con_img = bool(d.get("src"))
        cw = int((0.52 if con_img else 0.66) * self.W)
        rh = int(min(100 * u, (self.H - y0 - 50 * u) / n - 14 * u))
        paso = float(d.get("paso", 0.6))
        y0 = self.centrar(y0, n, rh)
        cols = {"ok": th.color("verde"), "no": th.color("rojo"), "alerta": th.color("naranja")}
        for i, it in enumerate(items):
            tp = it.get("tipo", "ok")
            ic = icon(th, tp, rh * 0.56, cols[tp])
            t0 = 0.5 + i * paso
            self.add(self.fila(it["texto"], cw, rh, ic, t0), 90 * u, y0 + i * (rh + 14 * u), t0, dx=-40 * u, dy=0)
        if con_img:
            self.imagen_lateral(d["src"], 0.80 * self.W, 0.50 * self.H, 0.28 * self.W, 0.6, angulo=-3)


REGISTRY_ALIAS = None


@register("revision_honesta")
class RevisionHonesta(Checklist):
    pass


@register("tarjetas_precio")
class TarjetasPrecio(Stack):
    """'¿CUÁNTO CUESTA?': tarjetas que saltan una a una. Datos: titulo, tarjetas[{nombre,precio,nota,color}]."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d.get("titulo", "¿Cuánto cuesta?"))
        cards = d["tarjetas"]
        n = len(cards)
        gap = 30 * u
        cw = int(min(340 * u, (self.W - 180 * u - (n - 1) * gap) / n))
        ch = int(min(400 * u, self.H - y0 - 70 * u))
        total = n * cw + (n - 1) * gap
        x0 = (self.W - total) / 2
        for i, c in enumerate(cards):
            precio = str(c["precio"])
            gratis = precio.strip().upper() == "GRATIS"
            acc = th.color(c.get("color", "verde" if gratis else "naranja"))
            img = rrect(cw, ch, 18 * u, (255, 255, 255, 255))
            band = rrect(cw, int(14 * u), 7 * u, acc)
            img.alpha_composite(band, (0, 0))
            d_ = ImageDraw.Draw(img)
            fn = th.font("sans_black", 21 * u)
            nom = c["nombre"].upper()
            draw_tracked(d_, ((cw - text_w(fn, nom, 3 * u)) / 2, 44 * u), nom, fn, th.color("gris"), 3 * u)
            size = 92 * u
            fp = th.font("display", size)
            while text_w(fp, precio) > cw - 36 * u and size > 20 * u:
                size -= 3 * u
                fp = th.font("display", size)
            d_.text(((cw - text_w(fp, precio)) / 2, ch * 0.36), precio, font=fp, fill=acc)
            if c.get("nota"):
                fnote = th.font("sans", 23 * u)
                lines = wrap(fnote, c["nota"], cw - 40 * u, max_lines=3)
                yy = ch * 0.36 + line_h(fp) + 14 * u
                for ln in lines:
                    d_.text(((cw - text_w(fnote, ln)) / 2, yy), ln, font=fnote, fill=th.color("tinta"))
                    yy += line_h(fnote)
            self.add(img, x0 + i * (cw + gap), y0 + max(10 * u, (self.H - y0 - ch) / 2 - 10 * u), 0.5 + i * 0.28, "pop")


@register("saltalo_elige")
class SaltaloElige(Stack):
    """Dos columnas: lo que conviene saltarse y lo que conviene elegir.
    Datos: titulo (opc), izq{titulo,items[]}, der{titulo,items[]}."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d["titulo"]) if d.get("titulo") else 70 * u
        cw = int(0.40 * self.W)
        gap = 0.04 * self.W
        x0 = (self.W - 2 * cw - gap) / 2
        specs = [("izq", "SÁLTALO", "rojo", "no", -60 * u), ("der", "ELÍGELO", "verde", "ok", 60 * u)]
        fi = th.font("sans_bold", 29 * u)
        for k, (key, tit, cc, ik, dx) in enumerate(specs):
            col = d.get(key, {})
            acc = th.color(col.get("color", cc))
            rows = []
            for t in col.get("items", []):
                rows.append(wrap(fi, t, cw - 120 * u, max_lines=3))
            hh = int(72 * u)
            hb = hh + 24 * u + sum(len(r) * line_h(fi) + 30 * u for r in rows) + 8 * u
            hb = int(min(hb, self.H - y0 - 40 * u))
            img = rrect(cw, hb, 18 * u, (255, 255, 255, 255))
            head = rrect(cw, hh + int(18 * u), 18 * u, acc)
            img.alpha_composite(head.crop((0, 0, cw, hh)), (0, 0))
            dd = ImageDraw.Draw(img)
            ft = th.font("sans_black", 30 * u)
            tt = col.get("titulo", tit).upper()
            draw_tracked(dd, ((cw - text_w(ft, tt, 4 * u)) / 2, (hh - line_h(ft)) / 2), tt, ft, (255, 255, 255, 255), 4 * u)
            y = hh + 22 * u
            isz = int(38 * u)
            for r in rows:
                ic = icon(th, ik, isz, acc)
                img.alpha_composite(ic, (int(26 * u), int(y)))
                for j, ln in enumerate(r):
                    dd.text((26 * u + isz + 18 * u, y + j * line_h(fi) - 1 * u), ln, font=fi, fill=th.color("tinta"))
                y += len(r) * line_h(fi) + 30 * u
            self.add(img, x0 + k * (cw + gap), y0 + max(0.0, (self.H - y0 - hb) / 2 - 10 * u), 0.4 + 0.2 * k, dx=dx, dy=0)


@register("como_llegar")
class ComoLlegar(Stack):
    """Ruta paso a paso con insignias de linea. Datos: titulo, pasos[{linea,color,texto,sub,medio}]."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d.get("titulo", "Cómo llegar"))
        pasos = d["pasos"]
        n = len(pasos)
        step = min(128 * u, (self.H - y0 - 60 * u) / n)
        bd = int(min(78 * u, step * 0.72))
        cx = 90 * u + bd / 2
        top = y0 + max(0.0, (self.H - y0 - 30 * u - (n - 1) * step - bd) / 2) - 5 * u
        # linea conectora que crece
        lh = int(step * (n - 1))
        if n > 1:
            ln = rrect(int(8 * u), lh, 4 * u, th.color("gris", 150))
            self.items.append(dict(spr=to_premul(ln), x=cx - 4 * u, y=top + bd / 2, delay=0.4, mode="wipe_v",
                                   dx=0, dy=0, t=0.5 + 0.55 * (n - 1)))
        for i, p in enumerate(pasos):
            t0 = 0.5 + i * 0.55
            cc = self.col(p.get("color", "azul"))
            badge = circle(bd, cc)
            dd = ImageDraw.Draw(badge)
            lab = str(p.get("linea", ""))
            if lab:
                f = th.font("sans_black", bd * (0.52 if len(lab) < 3 else 0.36))
                dd.text(((bd - text_w(f, lab)) / 2, (bd - line_h(f)) / 2 - bd * 0.02), lab, font=f, fill=(255, 255, 255, 255))
            else:
                bi = icon(th, "pin", bd * 0.6, (255, 255, 255))
                badge.alpha_composite(bi, (int(bd * 0.2), int(bd * 0.2)))
            ring = Image.new("RGBA", (bd + int(10 * u), bd + int(10 * u)), (0, 0, 0, 0))
            ring.alpha_composite(circle(bd + int(10 * u), (244, 238, 224, 255)), (0, 0))
            ring.alpha_composite(badge, (int(5 * u), int(5 * u)))
            self.add(ring, cx - bd / 2 - 5 * u, top + i * step - 5 * u, t0, "pop", shadow=False)
            f1 = th.font("sans_bold", 38 * u)
            f2 = th.font("sans", 24 * u)
            w = int(max(text_w(f1, p["texto"]), text_w(f2, p.get("sub", ""))) + 20 * u)
            tag = None
            if p.get("medio"):
                tag = pill(th, p["medio"].upper(), "sans_black", 16 * u, (255, 255, 255, 255), cc, 12 * u, 4 * u, 2 * u)
            img = new_layer(w + (tag.width + 14 * u if tag else 0), line_h(f1) + (line_h(f2) if p.get("sub") else 0) + 6)
            dd = ImageDraw.Draw(img)
            dd.text((2, 0), p["texto"], font=f1, fill=(th.color("blanco") if self.foto else th.color("tinta")))
            if p.get("sub"):
                dd.text((2, line_h(f1)), p["sub"], font=f2, fill=(220, 220, 220, 255) if self.foto else th.color("gris"))
            if tag:
                img.alpha_composite(tag, (int(text_w(f1, p["texto"]) + 18 * u), int((line_h(f1) - tag.height) / 2)))
            self.add(img, cx + bd / 2 + 24 * u, top + i * step + (bd - img.height) / 2, t0 + 0.1, dx=-26 * u, dy=0,
                     shadow=self.foto)


@register("ficha_datos")
class FichaDatos(Stack):
    """Filas con icono (calendario, pin, reloj, moneda) y sello opcional.
    Datos: titulo, filas[{icono,etiqueta,valor}], sello (texto opc)."""

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        y0 = self.titulo(d.get("titulo", "Datos para ir"))
        filas = d["filas"]
        n = len(filas)
        cw = int(0.60 * self.W)
        rh = int(min(104 * u, (self.H - y0 - 60 * u) / n - 14 * u))
        y0 = self.centrar(y0, n, rh)
        for i, r in enumerate(filas):
            card = rrect(cw, rh, 14 * u, (255, 255, 255, 255))
            isz = int(rh * 0.5)
            bgc = rrect(int(rh * 0.74), int(rh * 0.74), rh * 0.2, (th.color("naranja")[0], th.color("naranja")[1],
                                                                     th.color("naranja")[2], 40))
            card.alpha_composite(bgc, (int(14 * u), int(rh * 0.13)))
            ic = icon(th, r.get("icono", "pin"), isz, th.color("naranja"))
            card.alpha_composite(ic, (int(14 * u + (rh * 0.74 - isz) / 2), int((rh - isz) / 2)))
            dd = ImageDraw.Draw(card)
            fe = th.font("sans_black", rh * 0.19)
            fv = th.font("sans_bold", rh * 0.34)
            while text_w(fv, r["valor"]) > cw - rh - 50 * u and fv.size > 14 * u:
                fv = th.font("sans_bold", fv.size - 2)
            xt = 14 * u + rh * 0.74 + 20 * u
            et = r["etiqueta"].upper()
            ty = (rh - line_h(fe) - line_h(fv) - 2 * u) / 2
            draw_tracked(dd, (xt, ty), et, fe, th.color("gris"), 2.5 * u)
            dd.text((xt, ty + line_h(fe) + 2 * u), r["valor"], font=fv, fill=th.color("tinta"))
            self.add(card, 90 * u, y0 + i * (rh + 14 * u), 0.5 + i * 0.4, dx=-40 * u, dy=0)
        if d.get("sello"):
            f = th.font("sans_black", 40 * u)
            txt = d["sello"].upper()
            tr = 5 * u
            w = int(text_w(f, txt, tr) + 64 * u)
            h = int(line_h(f) + 38 * u)
            col = self.col(d.get("color_sello", "verde"))
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            img.alpha_composite(rrect(w, h, 12 * u, (0, 0, 0, 0), outline=col, ow=max(3, 5 * u)), (0, 0))
            inner = rrect(w - int(18 * u), h - int(18 * u), 8 * u, (0, 0, 0, 0), outline=col, ow=max(2, 2 * u))
            img.alpha_composite(inner, (int(9 * u), int(9 * u)))
            draw_tracked(ImageDraw.Draw(img), (32 * u, 19 * u), txt, f, col, tr)
            canvas = new_layer(w + int(80 * u), h + int(120 * u))
            canvas.alpha_composite(img, (int(40 * u), int(60 * u)))
            spr = rotate_sprite(to_premul(canvas), 8)
            cxs = 90 * u + cw + (self.W - 90 * u - cw) / 2 - 20 * u
            self.items.append(dict(spr=spr, x=cxs - spr.shape[1] / 2, y=y0 + (n * (rh + 14 * u)) / 2 - spr.shape[0] / 2,
                                   delay=0.5 + n * 0.4 + 0.3, mode="sello", dx=0, dy=0))


class _Centrado(Stack):
    fuente = "titulo"
    tam = 128
    tracking = 3

    def layout(self):
        u, th, d = self.u, self.theme, self.data
        oscuro = d.get("modo", "claro") == "oscuro"
        self.foto = oscuro
        fg = th.color("blanco") if oscuro else th.color("tinta")
        acc = self.col(d.get("acento", "naranja"))
        lines = [(d["linea1"], fg)]
        if d.get("linea2"):
            lines.append((d["linea2"], acc))
        size = self.tam * u
        f = th.font(self.fuente, size)
        while max(text_w(f, t.upper() if self.fuente == "titulo" else t) for t, _ in lines) > 0.84 * self.W and size > 20 * u:
            size -= 3 * u
            f = th.font(self.fuente, size)
        lh = line_h(f)
        chip = None
        if d.get("chip"):
            c = d["chip"]
            chip = pill(th, c["texto"].upper(), "sans_black", 18 * u, (255, 255, 255, 255),
                        self.col(c.get("color", "rojo")), 20 * u, 8 * u, 3 * u)
        total = len(lines) * lh * 0.96 + (chip.height + 26 * u if chip else 0)
        y = (self.H - total) / 2
        if chip:
            self.add(chip, (self.W - chip.width) / 2, y, 0.0, "pop", shadow=False)
            y += chip.height + 26 * u
        for i, (t, c) in enumerate(lines):
            tx = t.upper() if self.fuente == "titulo" else t
            w = int(text_w(f, tx)) + 20
            img = new_layer(w, lh + 8)
            ImageDraw.Draw(img).text((10, 2), tx, font=f, fill=c)
            self.add(img, (self.W - w) / 2, y, 0.25 + i * 0.18, dy=34 * u, shadow=oscuro)
            y += lh * 0.96


@register("titulo_grande")
class TituloGrande(_Centrado):
    """Titulo centrado enorme (Anton), segunda linea en color de acento y chip opcional.
    Datos: linea1, linea2 (opc), chip{texto,color} (opc), acento, modo (claro|oscuro)."""


@register("texto_centrado")
class TextoCentrado(_Centrado):
    """Frase centrada en serif, mismas opciones que titulo_grande."""
    fuente = "serif_bold"
    tam = 64
