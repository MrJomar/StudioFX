from PIL import Image, ImageDraw, ImageChops


def text_w(font, text, tracking=0.0):
    if tracking == 0:
        return font.getlength(text)
    return sum(font.getlength(ch) for ch in text) + tracking * max(0, len(text) - 1)


def draw_tracked(draw, xy, text, font, fill, tracking=0.0):
    """Dibuja texto con espaciado entre letras. xy = esquina sup-izq."""
    if tracking == 0:
        draw.text(xy, text, font=font, fill=fill)
        return
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + tracking


def wrap(font, text, max_w, tracking=0.0, max_lines=None):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_w(font, trial, tracking) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,; ") + "…"
    return lines


def line_h(font):
    a, d = font.getmetrics()
    return a + d


def new_layer(w, h):
    return Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))


def tracked_chip(theme, text, font_key, size, fg, bg, padx, pady, tracking=0.0):
    """Etiqueta con fondo solido y texto con tracking."""
    f = theme.font(font_key, size)
    tw = text_w(f, text, tracking)
    lh = line_h(f)
    w, h = int(tw + 2 * padx), int(lh + 2 * pady)
    img = new_layer(w, h)
    d = ImageDraw.Draw(img)
    if bg is not None:
        d.rectangle([0, 0, w, h], fill=bg)
    draw_tracked(d, (padx, pady), text, f, fg, tracking)
    return img


def outline_text(font, text, color, stroke=2, fill_alpha=0, outline=True):
    """Texto en contorno (sin relleno) o solo relleno translucido, como los numeros del ranking.
    outline=False devuelve solo el relleno con alfa `fill_alpha` (0-255)."""
    pad = stroke + 3
    size = (int(font.getlength(text)) + 2 * pad, line_h(font) + 2 * pad)
    m_out = Image.new("L", size, 0)
    ImageDraw.Draw(m_out).text((pad, pad), text, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
    m_fill = Image.new("L", size, 0)
    ImageDraw.Draw(m_fill).text((pad, pad), text, font=font, fill=255)
    img = Image.new("RGBA", size, color[:3] + (0,))
    if outline:
        mask = ImageChops.subtract(m_out, m_fill)
        a = color[3] if len(color) > 3 else 255
        img.putalpha(mask.point(lambda v: int(v * a / 255)))
    else:
        img.putalpha(m_fill.point(lambda v: int(v * fill_alpha / 255)))
    return img
