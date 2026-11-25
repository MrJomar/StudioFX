import subprocess
import cv2
import numpy as np
from .easing import smooth_kb, clamp


class ImageScene:
    """Imagen con movimiento de camara (zoom/pan) suave y sin temblor."""

    EFFECTS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "static"]

    def __init__(self, d, W, H, fps, auto_effect="zoom_in"):
        self.W, self.H = W, H
        self.dur = float(d.get("dur", 5))
        self.effect = d.get("efecto") or auto_effect
        if self.effect not in self.EFFECTS:
            raise ValueError("efecto desconocido: %s (validos: %s)" % (self.effect, self.EFFECTS))
        self.k = float(d.get("intensidad", 0.14))
        self.temblor = float(d.get("temblor", 0.0))  # 0-1: camara en mano
        self.ph = (abs(hash(d["src"])) % 1000) / 159.0
        try:  # np.fromfile: cv2.imread no abre rutas con acentos/"—" en Windows
            img = cv2.imdecode(np.fromfile(d["src"], np.uint8), cv2.IMREAD_COLOR)
        except OSError:
            img = None
        if img is None:
            raise FileNotFoundError("No pude abrir la imagen: " + d["src"])
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ih, iw = img.shape[:2]
        # Escalar para que cubra el lienzo con 20% de margen (evita agrandar de mas).
        s = max(W * 1.2 / iw, H * 1.2 / ih)
        interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
        self.img = cv2.resize(img, (int(round(iw * s)), int(round(ih * s))), interpolation=interp)
        ih, iw = self.img.shape[:2]
        self.iw, self.ih = iw, ih
        if iw / ih > W / H:
            self.bh, self.bw = ih, ih * W / H
        else:
            self.bw, self.bh = iw, iw * H / W
        # foco (0-1) y zoom base: recorte de detalle de una foto que se reutiliza
        self.foco = d.get("foco")
        self.zb = float(d.get("zoom_base", 1.0))
        # marco: foto verticale/cuadrada (o pedida) sobre fondo desenfocado, como los documentales de referencia
        orig_ar = img.shape[1] / img.shape[0]
        self.marco = d.get("modo") == "marco" or (d.get("modo") != "lleno" and orig_ar < 1.45)
        if self.marco:
            oh, ow = img.shape[:2]
            fh = H * 0.74
            fw = fh * orig_ar
            if fw > W * 0.80:
                fw = W * 0.80; fh = fw / orig_ar
            self.fg = cv2.resize(img, (int(fw), int(fh)), interpolation=cv2.INTER_AREA)
            b = max(4, int(H * 0.012))
            self.fg = cv2.copyMakeBorder(self.fg, b, b * 3, b, b, cv2.BORDER_CONSTANT, value=(238, 234, 224))
            bg = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
            bg = cv2.resize(bg, (int(W * 1.1), int(H * 1.1)), interpolation=cv2.INTER_CUBIC)
            self.bg = cv2.GaussianBlur((bg * 0.38).astype(np.uint8), (0, 0), max(8, H * 0.02))
            sh = np.zeros(self.fg.shape[:2], np.float32); sh[:] = 1
            self.sombra = cv2.GaussianBlur(cv2.copyMakeBorder(sh, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=0), (0, 0), 14)

    def _frame_marco(self, lt):
        p = smooth_kb(lt / self.dur)
        W, H = self.W, self.H
        bh, bw = self.bg.shape[:2]
        z = 1.0 + 0.04 * p
        w, h = bw / z, bh / z
        x0, y0 = (bw - w) / 2, (bh - h) / 2
        M = np.array([[W / w, 0, -x0 * W / w], [0, H / h, -y0 * H / h]], dtype=np.float32)
        out = cv2.warpAffine(self.bg, M, (W, H), flags=cv2.INTER_LINEAR)
        zf = 1.0 + 0.06 * p
        fg = cv2.resize(self.fg, None, fx=zf, fy=zf, interpolation=cv2.INTER_LINEAR)
        fh, fw = fg.shape[:2]
        x, y = (W - fw) // 2, int((H - fh) / 2 - H * 0.02)
        sh = cv2.resize(self.sombra, (fw + 60, fh + 60))
        x1, y1 = max(0, x - 30), max(0, y - 30 + 14)
        sx0, sy0 = x1 - (x - 30), y1 - (y - 30 + 14)
        x2, y2 = min(W, x - 30 + fw + 60), min(H, y - 30 + 14 + fh + 60)
        if x2 > x1 and y2 > y1:
            m = sh[sy0:sy0 + (y2 - y1), sx0:sx0 + (x2 - x1)][..., None] * 0.55
            out[y1:y2, x1:x2] = (out[y1:y2, x1:x2] * (1 - m)).astype(np.uint8)
        xa, ya = max(0, x), max(0, y)
        xb, yb = min(W, x + fw), min(H, y + fh)
        out[ya:yb, xa:xb] = fg[ya - y:yb - y, xa - x:xb - x]
        return out

    def frame(self, lt):
        if self.marco:
            return self._frame_marco(lt)
        p = smooth_kb(lt / self.dur)
        k = self.k
        z, sx, sy = 1.0, 0.0, 0.0
        e = self.effect
        if e == "zoom_in":
            z = 1 + k * p
        elif e == "zoom_out":
            z = 1 + k * (1 - p)
        elif e in ("pan_left", "pan_right", "pan_up", "pan_down"):
            z = 1 + k
        z *= self.zb
        w, h = self.bw / z, self.bh / z
        cx, cy = self.iw / 2, self.ih / 2
        if self.foco:
            cx, cy = self.foco[0] * self.iw, self.foco[1] * self.ih
        if e.startswith("pan"):
            tx = (self.iw - w) / 2 * 0.9
            ty = (self.ih - h) / 2 * 0.9
            q = p * 2 - 1
            if e == "pan_left":
                sx = -q * tx
            elif e == "pan_right":
                sx = q * tx
            elif e == "pan_up":
                sy = -q * ty
            elif e == "pan_down":
                sy = q * ty
        if self.temblor > 0:  # vaiven suave y irregular, como camara en mano
            import math
            amp = self.temblor * 0.006 * self.bw
            ph = self.ph
            sx += amp * (math.sin(6.28 * 0.9 * lt + ph) + 0.6 * math.sin(6.28 * 2.3 * lt + 2 * ph))
            sy += amp * (math.sin(6.28 * 1.1 * lt + 1.7 * ph) + 0.5 * math.sin(6.28 * 2.9 * lt + ph))
        x0 = clamp(cx - w / 2 + sx, 0, self.iw - w)
        y0 = clamp(cy - h / 2 + sy, 0, self.ih - h)
        fx, fy = self.W / w, self.H / h
        M = np.array([[fx, 0, -x0 * fx], [0, fy, -y0 * fy]], dtype=np.float32)
        return cv2.warpAffine(self.img, M, (self.W, self.H), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)

    def close(self):
        pass


class ClipScene:
    """Clip de video recortado (max. `clip_max` s) leido con ffmpeg."""

    def __init__(self, d, W, H, fps, clip_max=4.0):
        self.W, self.H, self.fps = W, H, fps
        self.src = d["src"]
        self.start = float(d.get("inicio", 0))
        self.dur = min(float(d.get("dur", clip_max)), clip_max)
        self.proc = None
        self.last_idx = -1
        self.last = None

    def _open(self, idx):
        self.close()
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%s"
              % (self.W, self.H, self.W, self.H, self.fps))
        cmd = ["ffmpeg", "-v", "error", "-ss", "%.4f" % (self.start + idx / self.fps), "-i", self.src,
               "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.last_idx = idx - 1

    def frame(self, lt):
        idx = max(0, int(round(lt * self.fps)))
        if self.proc is None or idx < self.last_idx:
            self._open(idx)
        n = self.W * self.H * 3
        while self.last_idx < idx:
            buf = self.proc.stdout.read(n)
            if len(buf) < n:  # fin del clip: congelar ultimo frame
                if self.last is None:
                    raise RuntimeError("No pude leer el clip: " + self.src)
                self.last_idx = idx
                break
            self.last = np.frombuffer(buf, np.uint8).reshape(self.H, self.W, 3)
            self.last_idx += 1
        return self.last

    def close(self):
        if self.proc is not None:
            try:
                self.proc.stdout.close()
                self.proc.kill()
                self.proc.wait(timeout=5)
            except Exception:
                pass
            self.proc = None
