from .base import Component, REGISTRY, register
from . import header, lower_third, sello, fichas, ranking, polaroid, dato, texto, titulo, ambiente, infografia, historia, mapa, mascota  # noqa: F401  (registran sus tipos)


def build_component(data, theme, size):
    tipo = data["tipo"]
    if tipo not in REGISTRY:
        raise ValueError("Componente desconocido '%s'. Disponibles: %s" % (tipo, sorted(REGISTRY)))
    return REGISTRY[tipo](data, theme, size)
