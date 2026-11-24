# StudioFX

Motor de video local que arma videos tipo documental (imágenes con zoom, clips cortos,
transiciones y gráficos animados) a partir de un **JSON**. Sin DaVinci, sin costo.

## Instalar (Windows)
1. Instala Python 3.10+ y ffmpeg (`winget install Gyan.FFmpeg`).
2. `pip install -r requirements.txt`

## Usar
```
python tools/make_test_assets.py                     # crea material de prueba (una vez)
python cli.py hoja    proyectos_ejemplo/prueba_60s.json -o hoja.png --cada 4   # vista previa rápida
python cli.py frame   proyectos_ejemplo/prueba_60s.json --t 14.4 -o f.png      # un fotograma
python cli.py render  proyectos_ejemplo/prueba_60s.json -o salida/video.mp4     # video completo
python cli.py render  ... --res 1920x1080 --encoder h264_amf                    # 1080p con tu Radeon
```
El codificador se elige solo (AMF -> NVENC -> x264). `--audio pista.mp3` agrega el audio.

## Componentes disponibles (v0.2)
Automáticos desde las escenas: `barra_superior`, `credito`, `etiqueta_sup`.

| Tipo | Para qué |
|---|---|
| `lower_third` | Etiqueta de color + título + subtítulo |
| `sello` | Sello inclinado que cae con impacto ("NO NACIÓ AQUÍ") |
| `fichas_versiones` | 2-3 fichas de papel (fecha, fuente) sobre fondo desenfocado |
| `ranking_intro` | Pantalla "EMPEZAMOS CON EL NÚMERO" con número en contorno dorado |
| `ranking_entrada` | Título del puesto + marca de agua + barra de progreso de 10 casillas |
| `polaroid` | Foto con marco blanco que entra girando |
| `dato_grande` | Cifra enorme con descripción; **la cifra cuenta desde 0** |
| `ano_esquina` | Año o cifra tenue en una esquina |
| `subtitulo` | Cursiva sobre banda oscura; `palabra_a_palabra` la ilumina como karaoke |
| `callout` | Rombo dorado con anillo pulsante, línea y etiqueta |
| `frase_destacada` | Frase grande con marcador dorado sobre palabras clave |
| `titulo_capitulo` | Tarjeta de barrio/capítulo: etiqueta con línea roja, número en contorno y título condensado en bloque |

Transiciones por escena (`"transicion"` + `"trans"` en segundos): `fundido` (default), `negro`, `destello`, `barrido`.
Ejemplos: `proyectos_ejemplo/prueba_60s.json` y `prueba_lote1.json`.

## Armado automatico (reemplaza el script de DaVinci)

    python cli.py auto MI_CARPETA -o proyecto.json --audio narracion.mp3 --tema xolo_oscuro --res 1920x1080 --barra "Xolo Explorador"
    python cli.py render proyecto.json -o video.mp4

- Lee imagenes y videos en orden natural de nombre (01, 02, 10...).
- Imagenes: 5 s con zoom/paneo que se alternan. Videos: tramos de maximo 4 s (hasta `--segmentos` por video).
- Transiciones variadas (fundido, whip, zoom, glitch, destello). Con `--audio`, ajusta las duraciones para que el video termine justo con la narracion.
- Luego se agregan efectos (titulos, listas, mapas, mascota) en la lista `overlays` del JSON.

## Mapas satelitales
1. Crea una cuenta en el proveedor de imágenes (por defecto Mapbox) y copia tu *access token*.
2. Pégalo en `mapas.json` (campo `token`). El archivo no se sube a GitHub ni lo pisa la actualización.
3. Corre HACER TODO o `importar`: baja las teselas una vez (se guardan en `STUDIOFX\mapas_cache`).
4. Revisa los términos del proveedor para video monetizado y pon la atribución que pida (campo `atribucion`; se dibuja en pantalla).
Para otro proveedor usa `"plantilla"`: una URL con `{z}`, `{x}`, `{y}` y `{token}`.
