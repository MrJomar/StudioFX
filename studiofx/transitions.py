"""Transiciones entre escenas. Cada una recibe (fa, fb, a, idx): frames RGB uint8, avance a (0..1)
y numero de fotograma (para efectos con azar reproducible)."""
import math
import cv2
import numpy as np
from .easing import ease_in_out_cubic


def whip(fa, fb, a, idx=0):
    """Barrido rapido de camara: A sale a la izquierda y B entra por la derecha, con desenfoque de movimiento."""
    W = fa.shape[1]
    e = ease_in_out_cubic(a)
    off = int(round(e * W))
    out = np.concatenate([fa, fb], axis=1)[:, off:off + W]
    k = int(70 * math.sin(math.pi * a)) | 1
    if k > 1:
        out = cv2.blur(out, (k, 1))
    return np.ascontiguousarray(out)


def glitch(fa, fb, a, idx=0):
    """Corte con fallas digitales: franjas desplazadas y canales RGB separados."""
    H, W = fa.shape[:2]
    src = fa if a < 0.5 else fb
    env = math.sin(math.pi * a)
    out = src.copy()
    rng = np.random.default_rng(1000 + idx)
    for _ in range(int(3 + 11 * env)):
        h = int(rng.integers(6, max(8, int(H * 0.12))))
        y0 = int(rng.integers(0, max(1, H - h)))
        dx = int(rng.choice([-1, 1]) * rng.uniform(10, 140) * env)
        out[y0:y0 + h] = np.roll(src[y0:y0 + h], dx, axis=1)
    sh = int(16 * env)
    if sh:
        out[..., 0] = np.roll(out[..., 0], sh, axis=1)
        out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    return out


def zoom(fa, fb, a, idx=0):
    """Zoom a traves: A se acerca y se funde, B llega desde mas cerca hasta su tamano."""
    H, W = fa.shape[:2]
    e = ease_in_out_cubic(a)

    def scl(img, k):
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, k)
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    mix = cv2.addWeighted(scl(fa, 1 + 0.9 * e), 1 - e, scl(fb, 1.7 - 0.7 * e), e, 0)
    k = int(33 * math.sin(math.pi * a)) | 1
    if k > 1:
        mix = cv2.GaussianBlur(mix, (k, k), 0)
    return mix


REGISTRY = {"whip": whip, "glitch": glitch, "zoom": zoom}


def xolo_lens(fa, fb, a, idx=0):
    """Transicion de lente (10 fotogramas): empuje de zoom con desenfoque radial, aberracion cromatica y destello."""
    H, W = fa.shape[:2]
    e = ease_in_out_cubic(a)
    env = math.sin(math.pi * a)

    def scl(img, k):
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, k)
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    mix = cv2.addWeighted(scl(fa, 1 + 0.35 * e), 1 - e, scl(fb, 1.35 - 0.35 * e), e, 0)
    k = int(21 * env) | 1
    if k > 1:
        mix = cv2.GaussianBlur(mix, (k, k), 0)
    sh = int(10 * env)
    if sh:
        mix[..., 0] = np.roll(mix[..., 0], sh, axis=1)
        mix[..., 2] = np.roll(mix[..., 2], -sh, axis=1)
    return np.clip(mix.astype(np.int16) + int(34 * env), 0, 255).astype(np.uint8)


REGISTRY["xolo_lens"] = xolo_lens
REGISTRY["lente"] = xolo_lens
