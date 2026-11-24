from PIL import ImageDraw
from .base import Component, register
from ..compositing import to_premul, blit, with_shadow, dim_blur, scale_sprite
from ..easing import ease_out_cubic, ease_out_back, fade_env, clamp
from ..textkit import text_w, line_h, new_layer, wrap, tracked_chip, outline_text


@register("ranking_intro")
class RankingIntro(Component):
    """Pantalla de apertura de cada puesto: numero en contorno dorado sobre fondo oscurecido.
    Datos: numero, linea1 (blanco), linea2 (dorado)."""
    layer = 20

    def build(self):
        u, th, d = self.u, self.theme, self.data
        self.num = to_premul(outline_text(th.font("serif_bold", 190 * u), str(d["numero"]),
                                          th.color("dorado"), stroke=max(2, int(2.4 * u))))
        self.l1 = to_premul(tracked_chip(th, d.get("linea1", "EMPEZAMOS CON EL").upper(), "sans_bold",
                                         15 * u, (255, 255, 255, 255), None, 2, 2, 5 * u))
        self.l2 = to_premul(tracked_chip(th, d.get("linea2", "NÚMERO").upper(), "sans_bold",
                                         13 * u, th.color("dorado"), None, 2, 2, 4.5 * u))

    def apply(self, base, lt):
        u = self.u
        env = fade_env(lt, self.dur, 0.35, 0.35)
        dim_blur(base, env * 0.95, 0.42, 7)
        out = clamp((self.dur - lt) / 0.3)
        cx, cy = self.W / 2, self.H / 2
        o1 = clamp((lt - 0.05) / 0.3) * out
        o2 = clamp((lt - 0.15) / 0.3) * out
        blit(base, self.l1, cx - self.l1.shape[1] / 2, cy - 150 * u + (1 - o1) * 8 * u, o1)
        blit(base, self.l2, cx - self.l2.shape[1] / 2, cy - 122 * u + (1 - o2) * 8 * u, o2)
        k = 1.0 + 0.35 * (1 - ease_out_cubic(lt / 0.55))
        spr = scale_sprite(self.num, k) if k > 1.003 else self.num
        o = clamp(lt / 0.25) * out
        blit(base, spr, cx - spr.shape[1] / 2, cy + 20 * u - spr.shape[0] / 2, o)


@register("ranking_entrada")
class RankingEntrada(Component):
    """Entrada de un puesto: numero marca de agua, etiqueta + barra de progreso, titulo y subtitulo.
    Datos: numero, total (10), titulo, sub (opc), etiqueta (opc)."""
    layer = 62

    def build(self):
        u, th, d = self.u, self.theme, self.data
        n, total = int(d["numero"]), int(d.get("total", 10))
        self.wm = to_premul(outline_text(th.font("serif_bold", 82 * u), str(n),
                                         th.color("dorado", 190), stroke=max(2, int(1.8 * u))))
        self.chip = to_premul(tracked_chip(th, d.get("etiqueta", "Número %d" % n).upper(), "sans_black",
                                           9.5 * u, (255, 255, 255, 255), th.color("rojo"), 7 * u, 3 * u, 1.8 * u))
        # Segmentos de la barra: posiciones total..1 (izq->der): pasadas=dorado, actual=rojo, faltan=gris
        self.segs = []
        sw, sh = int(15 * u), max(3, int(6 * u))
        for pos in range(total, 0, -1):
            col = th.color("dorado") if pos > n else th.color("rojo") if pos == n else (255, 255, 255, 70)
            img = new_layer(sw, sh)
            ImageDraw.Draw(img).rectangle([0, 0, sw, sh], fill=col)
            self.segs.append(to_premul(img))
        self.sw = sw
        # Titulo y subtitulo
        ft = th.font("serif_bold", 36 * u)
        lines = wrap(ft, d["titulo"], 0.55 * self.W)
        lh = line_h(ft)
        px, py = 16 * u, 8 * u
        bw = int(max(text_w(ft, ln) for ln in lines) + 2 * px)
        bh = int(lh * len(lines) + 2 * py)
        box = new_layer(bw, bh)
        bd = ImageDraw.Draw(box)
        bd.rectangle([0, 0, bw, bh], fill=th.color("papel"))
        for i, ln in enumerate(lines):
            bd.text((px, py + i * lh), ln, font=ft, fill=th.color("tinta"))
        parts = [box]
        if d.get("sub"):
            fs = th.font("sans_bold", 10.5 * u)
            txt = d["sub"].upper()
            tw = int(text_w(fs, txt, 1.4 * u) + 22 * u)
            sb = tracked_chip(th, txt, "sans_bold", 10.5 * u, (255, 255, 255, 255), (18, 16, 14, 235),
                              11 * u, 5 * u, 1.4 * u)
            parts.append(sb)
        Wb = max(p.size[0] for p in parts)
        Hb = sum(p.size[1] for p in parts)
        blk = new_layer(Wb, Hb)
        y = 0
        for p in parts:
            blk.alpha_composite(p, (0, y))
            y += p.size[1]
        blk, self.pad = with_shadow(blk, blur=7 * u, offset=(0, 4 * u), opacity=0.45, pad=int(16 * u))
        self.blk = to_premul(blk)

    def apply(self, base, lt):
        u = self.u
        out = clamp((self.dur - lt) / 0.3)
        wm_w = self.wm.shape[1]
        bx = 24 * u + wm_w * 0.8 + 12 * u
        bh = self.blk.shape[0] - 2 * self.pad
        by = self.H - 60 * u - bh
        # marca de agua del numero
        o = clamp(lt / 0.4) * out
        blit(base, self.wm, 16 * u - (1 - ease_out_cubic(lt / 0.5)) * 30 * u, self.H - 60 * u - self.wm.shape[0] * 0.95, o)
        # bloque de titulo con wipe
        e = ease_out_cubic((lt - 0.1) / 0.5)
        blit(base, self.blk, bx - self.pad - (1 - e) * 20 * u, by - self.pad, clamp((lt - 0.1) / 0.15) * out,
             clip_w=self.blk.shape[1] * min(1.0, 0.1 + e))
        # fila: etiqueta + barra de progreso
        co = clamp((lt - 0.05) / 0.25) * out
        ch = self.chip.shape[0]
        cy = by - ch - 5 * u
        blit(base, self.chip, bx, cy, co)
        x = bx + self.chip.shape[1] + 12 * u
        sy = cy + (ch - self.segs[0].shape[0]) / 2
        for i, s in enumerate(self.segs):
            so = clamp((lt - 0.3 - i * 0.04) / 0.2) * out
            blit(base, s, x + i * (self.sw + 3 * u), sy + (1 - so) * 4 * u, so)
