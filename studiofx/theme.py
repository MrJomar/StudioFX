import json
import os
from PIL import ImageFont


class Theme:
    """Tema visual: colores, fuentes y ajustes de postproceso (JSON en temas/)."""

    def __init__(self, data, root):
        self.d = data
        self.root = root
        self._fonts = {}

    @classmethod
    def load(cls, name, root):
        path = os.path.join(root, "temas", name + ".json")
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f), root)

    def color(self, name, alpha=255):
        c = self.d["colores"][name] if isinstance(name, str) else name
        return (int(c[0]), int(c[1]), int(c[2]), int(alpha))

    def font(self, key, size):
        size = max(1, int(round(size)))
        k = (key, size)
        if k not in self._fonts:
            fname = self.d["fuentes"][key]
            self._fonts[k] = ImageFont.truetype(os.path.join(self.root, "fonts", fname), size)
        return self._fonts[k]

    def get(self, *path, default=None):
        cur = self.d
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur
