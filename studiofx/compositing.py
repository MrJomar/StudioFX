"""Mezcla de sprites (RGBA premultiplicado, float32) sobre el frame uint8."""
import numpy as np
import cv2
from PIL import Image, ImageFilter


def to_premul(img):
    arr = np.asarray(img.convert("RGBA"), dtype=np.float32).copy()
    arr[..., :3] *= arr[..., 3:4] / 255.0
    return arr


def with_shadow(img, blur=8, offset=(0, 4), opacity=0.45, pad=None):
    pad = int(pad if pad is not None else blur * 3)
    offset = (int(round(offset[0])), int(round(offset[1])))
    w, h = img.size
    canvas = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    a = img.getchannel("A")
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    sh.putalpha(a.point(lambda v: int(v * opacity)))
    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_layer.paste(sh, (pad + offset[0], pad + offset[1]))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur))
    canvas = Image.alpha_composite(canvas, shadow_layer)
    canvas.alpha_composite(img, (pad, pad))
    return canvas, pad


def _shift(spr, fx, fy):
    """Desplaza un sprite una fraccion de pixel (bilineal) para movimiento suave."""
    h, w = spr.shape[:2]
    pad = cv2.copyMakeBorder(spr, 0, 1, 0, 1, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    M = np.array([[1, 0, fx], [0, 1, fy]], dtype=np.float32)
    return cv2.warpAffine(pad, M, (w + 1, h + 1), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))


def blit(base, spr, x, y, opacity=1.0, clip_w=None, subpixel=True):
    if opacity <= 0.002:
        return
    H, W = base.shape[:2]
    if clip_w is not None:
        spr = spr[:, : max(0, int(clip_w))]
    if spr.shape[0] == 0 or spr.shape[1] == 0:
        return
    xi, yi = int(np.floor(x)), int(np.floor(y))
    fx, fy = float(x - xi), float(y - yi)
    if subpixel and (fx > 0.04 or fy > 0.04):
        spr = _shift(spr, fx, fy)
    h, w = spr.shape[:2]
    x0, y0 = max(xi, 0), max(yi, 0)
    x1, y1 = min(xi + w, W), min(yi + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    s = spr[y0 - yi:y1 - yi, x0 - xi:x1 - xi]
    a = s[..., 3:4] * (opacity / 255.0)
    reg = base[y0:y1, x0:x1].astype(np.float32)
    reg = reg * (1.0 - a) + s[..., :3] * opacity
    base[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)


def scale_sprite(spr, k):
    h, w = spr.shape[:2]
    nw, nh = max(1, int(round(w * k))), max(1, int(round(h * k)))
    return cv2.resize(spr, (nw, nh), interpolation=cv2.INTER_LINEAR)


def dim_blur(base, amount, darken=0.6, blur=9):
    """Oscurece y desenfoca el fondo (amount 0..1). Modifica `base` in situ."""
    if amount <= 0.002:
        return
    H, W = base.shape[:2]
    small = cv2.resize(base, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    k = int(blur) | 1
    small = cv2.GaussianBlur(small, (k, k), 0)
    big = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
    mixed = cv2.addWeighted(base, 1 - amount, big, amount, 0)
    factor = 1.0 - (1.0 - darken) * amount
    base[:] = cv2.convertScaleAbs(mixed, alpha=factor)


def rotate_sprite(spr, deg, k=1.0):
    """Rota/escala un sprite alrededor de su centro (el lienzo debe traer margen)."""
    h, w = spr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, k)
    return cv2.warpAffine(spr, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
