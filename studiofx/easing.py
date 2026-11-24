import math


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out_cubic(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x, s=1.4):
    x = clamp(x)
    c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2


def smooth_kb(x):
    """Curva suave para Ken Burns: mitad lineal, mitad ease (no frena de golpe)."""
    x = clamp(x)
    return 0.5 * x + 0.5 * (0.5 - 0.5 * math.cos(math.pi * x))


def fade_env(lt, dur, fin=0.3, fout=0.3):
    """Opacidad 0..1: entra en `fin` s y sale en los ultimos `fout` s."""
    a = clamp(lt / fin) if fin > 0 else 1.0
    b = clamp((dur - lt) / fout) if fout > 0 else 1.0
    return min(a, b)
