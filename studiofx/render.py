import json
import os
import time
import cv2
import numpy as np

from .theme import Theme
from .scenes import ImageScene, ClipScene
from .scenes_fondo import FondoScene
from .components import build_component
from .encoder import pick_encoder, FFmpegWriter
from .easing import clamp
from .transitions import REGISTRY as TRANS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Project:
    def __init__(self, path, size=None, fps=None):
        self.path = os.path.abspath(path)
        self.base_dir = os.path.dirname(self.path)
        with open(path, encoding="utf-8") as f:
            self.d = json.load(f)
        res = self.d.get("resolucion", [1920, 1080])
        self.W, self.H = (size if size else (int(res[0]), int(res[1])))
        self.fps = fps or int(self.d.get("fps", 30))
        self.theme = Theme.load(self.d.get("tema", "oscuro_editorial"), ROOT)

    def resolve(self, p):
        if os.path.isabs(p):
            return p
        for base in (self.base_dir, os.path.dirname(self.base_dir), ROOT, os.getcwd()):
            c = os.path.join(base, p)
            if os.path.exists(c):
                return c
        return os.path.join(self.base_dir, p)


class Renderer:
    def __init__(self, project):
        self.p = project
        W, H, fps = project.W, project.H, project.fps
        self.W, self.H, self.fps = W, H, fps
        theme = project.theme
        d = project.d
        self.trans_default = float(d.get("transicion", 0.5))
        clip_max = float(d.get("clip_max", 4.0))

        # --- Escenas y linea de tiempo ---
        self.scenes = []  # dicts: obj, start, end, trans, ttype
        cur = 0.0
        auto = ImageScene.EFFECTS[:4]
        n_img = 0
        for i, sd in enumerate(d["escenas"]):
            sd = dict(sd)
            if sd.get("src"):
                sd["src"] = project.resolve(sd["src"])
            if sd.get("tipo") == "fondo":
                obj = FondoScene(sd, W, H, fps, theme)
            elif sd.get("tipo", "imagen") == "clip":
                obj = ClipScene(sd, W, H, fps, clip_max)
            else:
                obj = ImageScene(sd, W, H, fps, auto_effect=auto[n_img % len(auto)])
                n_img += 1
            trans = 0.0 if i == 0 else float(sd.get("trans", self.trans_default))
            start = 0.0 if i == 0 else cur - trans
            end = start + obj.dur
            cur = end
            self.scenes.append(dict(obj=obj, start=start, end=end, trans=trans,
                                    ttype=sd.get("transicion", "fundido"), raw=sd))
        self.duration = cur

        # --- Componentes ---
        self.comps = []
        if d.get("barra_superior"):
            self.comps.append(build_component(dict(tipo="barra_superior", texto=d["barra_superior"], t=0, dur=1e9),
                                              theme, (W, H)))
        for s in self.scenes:
            raw = s["raw"]
            dur = s["end"] - s["start"]
            if raw.get("credito"):
                self.comps.append(build_component(dict(tipo="credito", texto=raw["credito"], t=s["start"], dur=dur),
                                                  theme, (W, H)))
            if raw.get("etiqueta"):
                self.comps.append(build_component(dict(tipo="etiqueta_sup", texto=raw["etiqueta"], t=s["start"], dur=dur),
                                                  theme, (W, H)))
        for od in d.get("overlays", []):
            od = dict(od)
            od["t"] = self._parse_t(od["t"])
            if "src" in od:
                od["src"] = project.resolve(od["src"])
            self.comps.append(build_component(od, theme, (W, H)))
        self.comps.sort(key=lambda c: c.layer)

        # --- Postproceso: color, vineta, grano ---
        post = theme.get("post", default={})
        self.lut = self._make_lut(post.get("mult", [1, 1, 1]), post.get("gamma", 1.0))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 1.414
        v = 1.0 - float(post.get("vineta", 0.5)) * np.clip(r, 0, 1) ** 2.2
        self.vig = np.repeat((v * 255).astype(np.uint8)[:, :, None], 3, axis=2)
        gr = float(post.get("grano", 0))
        rng = np.random.default_rng(7)
        self.grain = []
        if gr > 0:
            for _ in range(6):
                n = rng.normal(0, gr, (H, W, 1)).astype(np.int16)
                n = np.repeat(n, 3, axis=2)
                self.grain.append((np.clip(n, 0, 255).astype(np.uint8), np.clip(-n, 0, 255).astype(np.uint8)))

    @staticmethod
    def _parse_t(t):
        if isinstance(t, (int, float)):
            return float(t)
        parts = [float(x) for x in str(t).split(":")]
        sec = 0.0
        for x in parts:
            sec = sec * 60 + x
        return sec

    @staticmethod
    def _make_lut(mult, gamma):
        x = np.arange(256, dtype=np.float32) / 255.0
        luts = []
        for m in mult:
            y = np.clip((x ** (1.0 / gamma)) * m, 0, 1) * 255
            luts.append(y.astype(np.uint8))
        return np.stack(luts, axis=1).reshape(256, 1, 3)

    def _base(self, t):
        self._idx = int(round(t * self.fps))
        act = [s for s in self.scenes if s["start"] <= t < s["end"]]
        if not act:
            act = [self.scenes[-1]] if t >= self.duration else [self.scenes[0]]
        if len(act) == 1:
            s = act[0]
            fr = s["obj"].frame(t - s["start"])
            a = 1.0
            if s is self.scenes[0] and t < 0.4:
                a = t / 0.4
            return fr if a >= 1.0 else cv2.convertScaleAbs(fr, alpha=a)
        prev, new = act[0], act[1]
        a = clamp((t - new["start"]) / max(new["trans"], 1e-6))
        fa = prev["obj"].frame(t - prev["start"])
        fb = new["obj"].frame(t - new["start"])
        tt = new["ttype"]
        if tt == "negro":
            if a < 0.5:
                return cv2.convertScaleAbs(fa, alpha=1 - 2 * a)
            return cv2.convertScaleAbs(fb, alpha=2 * a - 1)
        if tt == "destello":  # a blanco y de regreso
            white = np.full_like(fa, 255)
            if a < 0.5:
                return cv2.addWeighted(fa, 1 - 2 * a, white, 2 * a, 0)
            return cv2.addWeighted(white, 2 - 2 * a, fb, 2 * a - 1, 0)
        if tt in TRANS:
            return TRANS[tt](fa, fb, a, self._idx)
        if tt == "barrido":  # cortina con borde suave de izquierda a derecha
            soft = 0.22 * self.W
            front = a * (self.W + soft)
            m = np.clip((front - np.arange(self.W, dtype=np.float32)) / soft, 0, 1)[None, :, None]
            return (fa * (1 - m) + fb * m).astype(np.uint8)
        return cv2.addWeighted(fa, 1 - a, fb, a, 0)

    def frame_at(self, t, idx=None):
        base = self._base(t)
        base = cv2.LUT(base, self.lut)
        base = cv2.multiply(base, self.vig, scale=1 / 255.0)
        if self.grain:
            i = int(round(t * self.fps)) if idx is None else idx
            pos, neg = self.grain[i % len(self.grain)]
            base = cv2.subtract(cv2.add(base, pos), neg)
        base = np.ascontiguousarray(base)
        for c in self.comps:
            if c.t0 <= t < c.t0 + c.dur:
                c.apply(base, t - c.t0)
        return base

    def render(self, out, encoder="auto", audio=None, t_from=0.0, t_to=None, progress=True):
        codec = pick_encoder(encoder)
        aud = audio or self.p.d.get("audio")
        aud = self.p.resolve(aud) if aud else None
        total = self.duration if t_to is None else min(t_to, self.duration)
        n0, n1 = int(t_from * self.fps), int(total * self.fps)
        w = FFmpegWriter(out, self.W, self.H, self.fps, codec, aud)
        t_start = time.time()
        stats = dict(codec=codec, frames=n1 - n0)
        try:
            for i in range(n0, n1):
                w.write(self.frame_at(i / self.fps, i))
                if progress and (i - n0) % 60 == 0:
                    el = time.time() - t_start
                    fps_r = (i - n0 + 1) / el if el > 0 else 0
                    print("\r  %d/%d  %.1f fps de render  %.0fs" % (i - n0 + 1, n1 - n0, fps_r, el), end="", flush=True)
        finally:
            rc = w.close()
            self.close()
        stats["segundos"] = time.time() - t_start
        stats["fps_render"] = stats["frames"] / stats["segundos"] if stats["segundos"] else 0
        stats["ffmpeg_rc"] = rc
        if progress:
            print()
        return stats

    def close(self):
        for s in self.scenes:
            s["obj"].close()
