"""Utilidades de dibujo para componentes infograficos (formas con antialiasing e iconos)."""
import math
from PIL import Image, ImageDraw
from .textkit import text_w, line_h, new_layer

SS = 4


def rrect(w, h, r, fill, outline=None, ow=0):
    w, h = int(w), int(h)
    img = Image.new("RGBA", (w * 3, h * 3), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, w * 3 - 1, h * 3 - 1], radius=r * 3, fill=fill,
                                          outline=outline, width=int(ow * 3))
    return img.resize((w, h), Image.LANCZOS)


def circle(d, fill):
    return rrect(d, d, d / 2, fill)


def lerp_col(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def icon(theme, kind, size, color, bg=(255, 255, 255, 255)):
    """Icono cuadrado `size` px. kind: ok|no|alerta|calendario|pin|reloj|moneda|metro|estrella."""
    s = int(size) * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = tuple(color[:3]) + (255,)
    w = bg
    lw = max(2, int(s * 0.085))
    if kind in ("ok", "no", "moneda", "metro", "estrella"):
        d.ellipse([0, 0, s - 1, s - 1], fill=c)
    if kind == "ok":
        d.line([(s * .26, s * .52), (s * .43, s * .68), (s * .75, s * .33)], fill=w, width=lw, joint="curve")
    elif kind == "no":
        a, b = s * .31, s * .69
        d.line([(a, a), (b, b)], fill=w, width=lw)
        d.line([(a, b), (b, a)], fill=w, width=lw)
    elif kind == "alerta":
        d.polygon([(s * .5, s * .04), (s * .97, s * .92), (s * .03, s * .92)], fill=c)
        d.rounded_rectangle([s * .46, s * .34, s * .54, s * .64], radius=s * .03, fill=w)
        d.ellipse([s * .455, s * .72, s * .545, s * .81], fill=w)
    elif kind == "calendario":
        d.rounded_rectangle([s * .08, s * .16, s * .92, s * .92], radius=s * .12, outline=c, width=lw)
        d.rounded_rectangle([s * .08, s * .16, s * .92, s * .40], radius=s * .12, fill=c)
        d.rectangle([s * .08, s * .30, s * .92, s * .40], fill=c)
        for x in (.30, .70):
            d.rounded_rectangle([s * (x - .04), s * .04, s * (x + .04), s * .26], radius=s * .03, fill=c)
        for i in range(3):
            for j in range(2):
                d.ellipse([s * (.24 + i * .22), s * (.52 + j * .19), s * (.34 + i * .22), s * (.62 + j * .19)], fill=c)
    elif kind == "pin":
        d.ellipse([s * .2, s * .06, s * .8, s * .66], fill=c)
        d.polygon([(s * .27, s * .52), (s * .73, s * .52), (s * .5, s * .96)], fill=c)
        d.ellipse([s * .39, s * .25, s * .61, s * .47], fill=w)
    elif kind == "reloj":
        d.ellipse([s * .06, s * .06, s * .94, s * .94], outline=c, width=lw)
        d.line([(s * .5, s * .5), (s * .5, s * .24)], fill=c, width=lw)
        d.line([(s * .5, s * .5), (s * .70, s * .60)], fill=c, width=lw)
    elif kind in ("moneda", "metro", "estrella"):
        ch = {"moneda": "$", "metro": "M", "estrella": "★"}[kind]
        f = theme.font("sans_black", s * .56)
        d.text((s / 2 - text_w(f, ch) / 2, s / 2 - line_h(f) / 2 - s * .02), ch, font=f, fill=w)
    return img.resize((int(size), int(size)), Image.LANCZOS)


def pill(theme, text, font_key, size, fg, bg, padx, pady, tracking=0.0):
    from .textkit import draw_tracked
    f = theme.font(font_key, size)
    tw = text_w(f, text, tracking)
    h = int(line_h(f) + 2 * pady)
    w = int(tw + 2 * padx)
    img = rrect(w, h, h / 2, bg)
    draw_tracked(ImageDraw.Draw(img), (padx, pady), text, f, fg, tracking)
    return img
