import cv2
import numpy as np


class FondoScene:
    """Fondo liso de papel con un patron muy tenue de curvas de nivel que deriva despacio.
    Datos: dur, color (opc [r,g,b]), patron (true), fondo_tinte (opc)."""

    def __init__(self, d, W, H, fps, theme):
        self.W, self.H = W, H
        self.dur = float(d.get("dur", 5))
        c = d.get("color") or theme.get("colores", "papel", default=[244, 238, 224])
        self.color = np.array(c[:3], np.float32)
        self.pat = bool(d.get("patron", True))
        self.img = None
        if self.pat:
            rng = np.random.default_rng(int(d.get("semilla", 3)))
            w2, h2 = int(W * 1.25), int(H * 1.25)
            f = np.zeros((h2, w2), np.float32)
            for gw, amp in ((7, 1.0), (15, 0.45), (31, 0.18)):
                g = rng.normal(0, 1, (max(3, int(gw * h2 / w2)), gw)).astype(np.float32)
                f += amp * cv2.resize(g, (w2, h2), interpolation=cv2.INTER_CUBIC)
            ph = f * 3.2
            dist = np.abs(ph - np.round(ph))
            line = np.clip(1 - dist / 0.045, 0, 1) * 0.10
            dark = self.color * 0.55
            self.line = line[..., None]
            self.dark = dark
            full = self.color[None, None, :] * (1 - self.line) + dark[None, None, :] * self.line
            self.img = np.clip(full, 0, 255).astype(np.uint8)
        else:
            self.flat = np.full((H, W, 3), self.color, np.uint8)

    def frame(self, lt):
        if self.img is None:
            return self.flat.copy()
        h2, w2 = self.img.shape[:2]
        mx, my = w2 - self.W, h2 - self.H
        p = (lt / max(self.dur, 1e-6))
        x0 = int(mx * (0.2 + 0.5 * p))
        y0 = int(my * (0.3 + 0.3 * p))
        return np.ascontiguousarray(self.img[y0:y0 + self.H, x0:x0 + self.W])

    def close(self):
        pass
