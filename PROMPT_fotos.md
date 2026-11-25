# Sección para el prompt maestro: fotos y visuales nuevos

Agrega esto a las instrucciones que generan el JSON `xolo.visual.v1`. Todo es **opcional**: si no viene, StudioFX funciona como antes.

## 1. Lista de fotos por bloque (`fotos`)

Dentro de cada elemento de `xolo_estudio.bloques[]`, junto a `efectos` y `broll`, agrega:

```json
"fotos": [
  {
    "id": "foto_12_01",
    "que": "Vista del río humeante entre pinos",
    "titulo": "Río Caliente",
    "fecha": "2026",
    "fuente": "Foto: Universidad de Guadalajara",
    "orientacion": "horizontal"
  }
]
```

Reglas para el modelo:
- Entre **20 y 25 fotos por cada 2 minutos de bloque** (una foto cada ~4-5 s). Todas **horizontales** si existen.
- `id`: `foto_<bloque>_<nn>` (ese es el nombre del archivo `.jpg` que se guardará en la carpeta del bloque).
- `que`: qué se ve, concreto y buscable (sirve para que tú sepas qué descargar). Una línea.
- `titulo`: 1-4 palabras para la etiqueta en pantalla (lugar, persona u objeto). Sin inventar: debe salir del guion.
- `fecha`: año o fecha que muestra la etiqueta roja. Solo si el guion la menciona o la foto es de ese año; si no, omítela.
- `fuente`: crédito corto («Foto: Fototeca INAH»). No inventar fuentes: si no se sabe, omitirla.
- Las fotos van **en el orden en que se cuentan** en el bloque.

## 2. Visuales nuevos dentro de `efectos`

- **Palabra grande a pantalla completa** (una palabra clave del momento):
  `"kind": "palabra"`, `"title": "Agua"`, `"etiqueta": "Lo que la ciudad quería"` (línea pequeña de arriba), `"fondo": "azul|oscuro|rojo|verde|tierra"`.
  Máximo 1 cada ~2 minutos. `anchor_text` y la evidencia deben ser frases literales del guion.
- **Tarjeta de libro/obra junto a una foto** (solo si el guion nombra la obra y su autor):
  `"kind": "libro"`, `"autor": "…"`, `"title": "…"`, `"anio": 1967`, `"color": "rojo|azul|verde|tierra"`.
