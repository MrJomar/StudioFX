# Changelog

## 0.17.1
- «Nuevo proyecto»: si eliges una carpeta que ya es un proyecto (tiene Audio, STUDIOFX o carpetas de bloque), se usa tal cual y no crea otra con el mismo nombre dentro.

## 0.17.0
- Modo de prueba «hook + primer bloque» (--primer-bloque): arma y renderiza solo el hook y el primer bloque; el render respeta ese límite solo.

## 0.16.0
- Guiones de otros temas: la biblioteca de visuales de Guadalajara ya no se aplica ni rompe un guion distinto. Los visuales vienen del propio JSON (`datos`); ver CONTRATO_JSON_v2.md.
- hook_efectos puede ir dentro de xolo_estudio. Datos incompletos en un visual caen a una tarjeta en vez de fallar.

## 0.15.1
- Sincronizar usa la transcripción con tiempos que deje tu otro programa en la carpeta Audio (JSON con palabras en segundos o milisegundos, estilo Whisper, o SRT/VTT); si no hay, usa Whisper.

## 0.15.0
- Nuevos visuales: palabra grande a pantalla completa (kind "palabra") y tarjeta de libro (kind "libro"). 6 palabras agregadas al guion actual.
- Campo opcional `fotos` por bloque: etiqueta (fecha + título) y crédito de fuente sobre cada foto; las fotos que no están en la carpeta salen en "Imágenes que faltan". Ver PROMPT_fotos.md.
- La barra superior ahora muestra el título del video.

## 0.14.0
- Solo fotos por defecto (los videos de las carpetas se ignoran; casilla "Usar también videos" para volver a usarlos). Ritmo de referencia: una foto cada ~4 s; si faltan fotos, se reutilizan con acercamientos a un detalle.
- Fotos verticales/cuadradas se muestran enmarcadas sobre fondo desenfocado (estilo documental).
- Pendientes: STUDIOFX\\pendientes.json lista los visuales que piden una foto específica y cuántas fotos faltan por bloque; antes de renderizar el programa pregunta.
- Interfaz nueva: lista de proyectos con estado, Nuevo proyecto (desde el guion JSON crea las carpetas de fotos), Agregar guion/audio, pestaña "Imágenes que faltan" con botón para agregar la foto correcta.

## 0.13.0
- Las fotos ya nunca quedan estáticas (zoom lento).
- Se quitó el título inventado "La revisión honesta"; las listas usan frases del guion.
- Subtítulos karaoke automáticos (frases del guion) en los huecos largos sin visuales.
- Revisar escenas: ventana para cambiar una foto/clip o elegir otro tramo del mismo video, con vista previa de 6 s. Los cambios se guardan en STUDIOFX\\cambios.json y se reaplican al rearmar.

## 0.9.0
- Comando `auto`: arma el proyecto desde una carpeta (imagenes 5 s con zoom/paneo, clips en tramos de 4 s, transiciones variadas, ajuste a la duracion del audio).

## 0.8.0
- Mascota Xolo Explorador: 8 poses recortadas (`mascota/*.png`) y componente `mascota` (entrada, respiracion/rebote/camina, salida).
- Temas `xolo_oscuro` / `xolo_claro` con los colores medidos de la hoja de personaje.

## 0.7.0
- Identidad propia: temas `explorador_oscuro` y `explorador_claro` (azul noche, ambar, rosa mexicano, turquesa, verde selva). Proyectos `*_explorador.json` de ejemplo.

## 0.6.0
- Componente `mapa_zona`: poligonos (GeoJSON o listas lon/lat), zona resaltada, zoom de camara, marcadores con pulso,
  ruta animada entre puntos, escala y norte. Probado con poligonos sinteticos.

## 0.5.0
- Tema `claro_infografia` (papel + verde/naranja/amarillo) y escena `fondo` (papel con curvas de nivel tenues).
- Componentes infografia: `lista_video`, `tarjetas_precio`, `checklist` (alias `revision_honesta`), `saltalo_elige`,
  `como_llegar`, `ficha_datos` (con sello), `titulo_grande`, `texto_centrado`. Opcion `sobre_foto` para usarlos sobre imagenes.
- Componentes historia/datos: `recorte_periodico`, `linea_tiempo`, `comparador`, `barras`.

## 0.4.0
- Nuevo componente `particulas` (estilo polvo | luciernagas | nieve).
- Nuevas transiciones: `whip` (barrido con desenfoque), `glitch`, `zoom` (modulo `transitions.py`).
- Escenas de imagen: `temblor` 0-1 (camara en mano).
- `titulo_capitulo`: tamano adaptativo (titulos de una linea mas grandes) y sin deriva (sin temblor lateral).
## 0.3.0
- Nuevo componente `titulo_capitulo` (tarjeta de barrio): letras escalonadas, línea roja que se dibuja, número que se traza y se rellena, renglones que suben desde una máscara, sombra lateral.
- Fuente Anton (titulares condensados) y color `crema` en el tema oscuro.
## 0.2.0 - lote 1
- Nuevos componentes: ranking_intro, ranking_entrada, polaroid, dato_grande (contador animado),
  ano_esquina, subtitulo (karaoke), callout, frase_destacada (marcador).
- Nuevas transiciones: destello (a blanco) y barrido (cortina suave).
- Los componentes pueden recibir `src` (ruta de imagen).
- Frase destacada con renglones balanceados.
## 0.1.0 - prueba de concepto
- Motor base: imágenes con zoom/pan, clips ≤4 s, fundido cruzado y transición a negro.
- Postproceso: tinte de color, viñeta y grano.
- Componentes: barra superior, crédito, etiqueta superior, lower third, sello, fichas de versiones.
- CLI: render, frame, hoja (vista previa en hoja de contactos).
- Pendiente: mapas, ranking, polaroid, dato grande, lista, tarjetas de precio, checklist, CTA,
  sincronía con Whisper, planificador con LLM, interfaz gráfica.

## 0.10.0
- `sincronizar`: tiempos por palabra del guion (Whisper si está instalado; `--estimar` por pausas, aproximado).
- `importar`: arma el proyecto completo (capítulos, B-roll por ancla, efectos, transición `xolo_lens`, mascota en el cierre) desde la carpeta del proyecto.
- Transición nueva `xolo_lens`.

## 0.11.0
- FIX desfase: los clips se recortaban a `clip_max` y el video salía más corto que el audio; ahora importar verifica que la duración del render = audio.
- Los bloques arrancan en los marcadores de DaVinci (`marcadores_davinci.json`); tarjeta de capítulo en el silencio del marcador y `xolo_lens` centrado en el corte.
- B-roll: todas las fotos primero (≤5 s), clips ≤4 s repartidos entre ellas, nunca 2 recortes seguidos del mismo video madre; se salta la intro de cada video madre.
- `enriquecer`: +60 visuales derivados del guion (mapa por municipio, cifras, listas, versiones, revisión honesta, líneas de tiempo, frases, gancho) con validación literal contra el texto; coordenadas con fuente.
- Componente `mapa_ubicacion` (municipios INEGI en `datos/`).
- Bitrate del borrador según resolución.

## 0.12.0
- Mapas con imagen SATELITAL real (`mapa_satelite`): las teselas se descargan al armar el proyecto (`importar`), se guardan en `STUDIOFX\mapas_cache` y el render no necesita internet. Zoom que cambia de nivel de detalle, contorno del municipio, pin, escala y atribución.
- Configuración en `mapas.json` (proveedor, token, plantilla). Sin token, o si falla la descarga, se usa el mapa de polígonos de antes.
