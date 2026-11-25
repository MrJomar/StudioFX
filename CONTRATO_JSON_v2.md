# Contrato JSON — reemplaza la sección «Contrato JSON» completa de tu prompt (esquema `xolo.visual.v2`)

Esta sección es el contrato técnico de StudioFX. El JSON es solo dirección visual: **nunca modifica el guion**.

## A. Raíz (sin cambios respecto a lo que ya tienes)
Exactamente seis claves: `version` (1), `canal` ("Xolo Explorador"), `titulo`, `segmentos`, `hook_visual`, `xolo_estudio`.
`segmentos`, `hook_visual`, nombres de bloque ("12. Nombre — Municipio"), CTA y reglas de texto: igual que hoy.
**Nuevo en `nombre`:** usa el formato `N. Lugar — Municipio` (con guion largo). El municipio se usa en la etiqueta de cada capítulo.

## B. `xolo_estudio`
```json
{
  "schema": "xolo.visual.v2",
  "configuracion": { "fps": 30, "perfil_ritmo": "documental_dinamico", "solo_fotos": true },
  "hook_efectos": [ /* mismos campos que `efectos`, ancla dentro del HOOK. 3-5 */ ],
  "bloques": [ { "numero": 10, "nombre": "…", "efectos": [ … ], "fotos": [ … ] } ]
}
```
Ya NO hay `broll`, `medio_preferido`, clips de video ni `bin_sugerido`: **StudioFX usa solo fotos**. La lista `fotos` reemplaza a `broll`.

## C. `efectos` — campos de cada entrada
`id` (único, `fx_<bloque>_<nn>`; en el hook `fx_h_<nn>`), `kind`, `anchor_text`, `title`, `subtitle`, `duration`, `asset_requirement` ("none"|"optional"|"required"), `asset_hint`, y **`datos`** (objeto, ver tabla).

- `anchor_text`: cita literal y continua del texto del bloque, 5–14 palabras, tildes y signos idénticos. Es el momento en que aparece el visual.
- `datos.evid`: lista de fragmentos **literales** del texto del bloque que respaldan cada cifra, nombre o fecha mostrados. Obligatorio salvo en `etiqueta` y `palabra`.
- Todo número o nombre propio visible tiene que salir del texto del bloque. Nada inventado, ni coordenadas, ni años, ni fuentes.

| `kind` | title | subtitle | `datos` (obligatorio salvo lo marcado opcional) |
|---|---|---|---|
| `cifra` | el número ("57", "≈ 500 m") | qué cuenta | `etiqueta` (opc., 1-2 palabras), `contar` (true/false), `evid` |
| `fecha` | el año | qué pasó | `evid` |
| `tarjeta` | dato central | explicación breve | `etiqueta` (ej. "DATO"), `color` ("rojo"/"azul"/"dorado"), `evid` |
| `etiqueta` | texto corto (3 palabras) | "" | — |
| `sello` | 1–2 palabras | frase corta | `evid` |
| `frase` | frase literal del bloque, ≤ 14 palabras | "" | `destacar`: 1–2 palabras clave, `evid` |
| `lista` | título | "" | `titulo`, `items`: `[["texto","ok"],["texto","no"]]` (ok = ✔, no = ✘; 2–4 ítems), `evid` |
| `comparacion` | título | "" | `titulo`, `fichas`: `[["ETIQUETA","rojo","valor","texto"],["ETIQUETA","azul","valor","texto"]]` (dos lados realmente distintos), `evid` |
| `cronologia` | título | "" | `titulo`, `eventos`: `[["1897","qué pasó"],…]` (2–5, en orden real), `evid` |
| `palabra` | UNA palabra clave (≤ 14 letras) | "" | `etiqueta` (línea pequeña de arriba), `fondo` ("azul"/"oscuro"/"rojo"/"verde"/"tierra") |
| `libro` | título de la obra | "" | `autor`, `anio`, `color` ("rojo"/"azul"/"verde"/"tierra"); solo si el guion nombra obra y autor |
| `mapa` | nombre del sitio | municipio | `lugar`, `municipios` (lista), `lon`, `lat`, `foco_km` (3–12), `foco_sat_km` (0.8–3), `evid` |
| `documento` / `foto_cine` | pie de foto | "" | pide una foto específica: `asset_requirement` + `asset_hint` (qué foto buscar); opcional `sin_imagen`: `{"kind":"tarjeta","title":…,"subtitle":…}` para cuando no haya foto |

Compatibilidad: si llega un `kind` antiguo (`numero`, `cita`, `misterio`, `sello_editorial`, `expediente`, `marco`, `foto_lateral`, `revelado`, `capas`) StudioFX lo convierte al más cercano, pero **usa solo la tabla de arriba**.

**Mapas:** hoy solo existen mapas para **Jalisco**. Fuera de Jalisco no uses `mapa`; usa `etiqueta` o `tarjeta`. Las coordenadas deben ser del sitio real: StudioFX las comprueba contra el municipio y avisa si no coinciden.

## D. Cantidad y ritmo de visuales
- Un visual cada **20–35 s** de narración (para 2 min de bloque: 4–6), mezclando tipos. No más de 1 `palabra` por bloque y 1 `mapa` por bloque. Nunca dos visuales grandes (`mapa`, `lista`, `comparacion`, `cronologia`, `palabra`, `frase`) con menos de 6 s entre sus anclas.
- Hook: 3–5 `hook_efectos` (tarjetas, sello, cifra) con anclas dentro del hook.
- Textos legibles en TV: `title` 2–6 palabras (≤ 45 caracteres), `subtitle` ≤ 90.
- `duration`: 3–6 s (mapa y listas 5–6; palabra y sello 3–3.5).
- Si hay conflicto entre efecto y narración o veracidad, gana la narración; elimina el efecto.

## E. `fotos` — lista por bloque (reemplaza a `broll`)
```json
{ "id": "foto_12_01", "que": "…", "titulo": "…", "fecha": "…", "fuente": "…" }
```
- **12–18 fotos por cada 2 min** de bloque, **horizontales** cuando existan, en el orden en que se cuentan. Con menos, StudioFX repite con acercamientos.
- `que`: qué se ve, concreto y buscable. `titulo`: 1–4 palabras para la etiqueta. `fecha`: solo si el guion o la foto la respaldan (si no, omitir la clave). `fuente`: crédito corto real; si no se sabe, omitir la clave.
- `id`: `foto_<bloque>_<nn>`; ese es el nombre del `.jpg` que se guardará.
- Un visual `documento`/`foto_cine` con `asset_requirement: "required"` se reserva para pruebas que sin la imagen correcta serían engañosas.

## F. Validación del modelo antes de entregar
1. Cada `anchor_text` y cada `evid` aparece literalmente en el texto de **su** bloque (o del hook).
2. `kind` ∈ tabla C; `id` únicos; `duration` numérica; `datos` con todos los campos obligatorios de su `kind`.
3. Cifras, años y nombres visibles ⊂ texto del bloque.
4. `fotos`: ids únicos y consecutivos; sin duplicar título + fecha.
5. Sin `null`, comentarios ni puntos suspensivos; `xolo_estudio.bloques` con los mismos N bloques y orden que `segmentos`.
