# Arquitectura de StudioFX

Flujo: `JSON -> Renderer -> frames (numpy) -> ffmpeg (pipe) -> MP4`

| Archivo | Qué hace |
|---|---|
| `studiofx/render.py` | `Project` (carga JSON) y `Renderer` (línea de tiempo, mezcla, postproceso, render) |
| `studiofx/scenes.py` | `ImageScene` (zoom/pan con warpAffine, sin temblor) y `ClipScene` (clips ≤ `clip_max` s vía ffmpeg) |
| `studiofx/components/` | Un archivo por componente. Interfaz: `build()` una vez y `apply(base, lt)` por frame |
| `studiofx/compositing.py` | Mezcla de sprites RGBA premultiplicados, sombras, oscurecer+desenfocar fondo |
| `studiofx/theme.py` + `temas/*.json` | Colores, fuentes y postproceso (viñeta, grano, tinte) |
| `studiofx/encoder.py` | Elige AMF/NVENC/x264 y escribe a ffmpeg por pipe |
| `studiofx/easing.py`, `textkit.py` | Curvas de animación y utilidades de texto |

## Reglas para poder unir con Vertical Studio después
- Cada componente es independiente de la interfaz: recibe datos + tema + tamaño y dibuja sobre un frame.
- El JSON describe *qué* es cada cosa (tipo), no cómo se anima; el estilo sale del tema.
- Unidad de diseño `u = alto/720`: los tamaños escalan a cualquier resolución.
- Para agregar un componente: nuevo archivo en `components/`, decorador `@register("nombre")`, importarlo en `components/__init__.py`.

## Decisiones medidas
- El grano de película a intensidad 5 multiplicaba el peso del archivo por ~25 (41 MB vs 1.6 MB por 12 s); por defecto es 2.
