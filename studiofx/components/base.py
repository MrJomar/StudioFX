REGISTRY = {}


def register(name):
    def deco(cls):
        REGISTRY[name] = cls
        cls.tipo = name
        return cls
    return deco


class Component:
    """Interfaz comun. Cada componente:
       - se construye una sola vez (sprites pre-dibujados),
       - `apply(base, lt)` modifica el frame `base` (uint8 HxWx3) in situ,
         donde `lt` es el tiempo local en segundos desde que aparece.
       `layer` ordena el apilado (menor = mas al fondo)."""

    layer = 50

    def __init__(self, data, theme, size):
        self.data = data
        self.theme = theme
        self.W, self.H = size
        self.u = self.H / 720.0  # unidad de diseno: 1u = 1px a 720p
        self.t0 = float(data.get("t", 0))
        self.dur = float(data.get("dur", 3))
        self.build()

    def build(self):
        pass

    def apply(self, base, lt):
        raise NotImplementedError
