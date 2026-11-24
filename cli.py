#!/usr/bin/env python3
"""StudioFX - linea de comandos.

  python cli.py render  proyecto.json -o salida.mp4 [--res 1280x720] [--fps 30] [--encoder auto|libx264|h264_amf]
  python cli.py frame   proyecto.json --t 12.5 -o frame.png
  python cli.py hoja    proyecto.json -o hoja.png [--cada 4] [--cols 4]     (vista previa: hoja de contactos)
"""
import argparse
import os
import sys
import cv2
import numpy as np
from studiofx.render import Project, Renderer


def parse_res(s):
    if not s:
        return None
    w, h = s.lower().split("x")
    return int(w), int(h)


def main():
    from studiofx import actualizar as act
    act.al_abrir()
    ap = argparse.ArgumentParser(description="StudioFX")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("auto", help="armar proyecto automaticamente desde una carpeta de imagenes y clips")
    pa.add_argument("carpeta")
    pa.add_argument("-o", "--salida", required=True, help="proyecto .json a crear")
    pa.add_argument("--audio")
    pa.add_argument("--tema", default="xolo_oscuro")
    pa.add_argument("--res", default="1920x1080")
    pa.add_argument("--fps", type=int, default=30)
    pa.add_argument("--dur-imagen", type=float, default=5.0)
    pa.add_argument("--clip-max", type=float, default=4.0)
    pa.add_argument("--segmentos", type=int, default=3, help="max. tramos de 4 s por video")
    pa.add_argument("--barra", help="texto de la barra superior (opcional)")
    ps = sub.add_parser("sincronizar", help="calcular los tiempos de cada palabra del guion en el audio")
    ps.add_argument("proyecto", help="carpeta del proyecto de Xolo Explorador")
    ps.add_argument("--guion"); ps.add_argument("--audio"); ps.add_argument("--modelo", default="small")
    ps.add_argument("--estimar", action="store_true", help="no usar Whisper (tiempos aproximados por pausas)")
    pi = sub.add_parser("importar", help="armar el proyecto StudioFX completo desde el proyecto de Xolo Explorador")
    pi.add_argument("proyecto")
    pi.add_argument("--guion"); pi.add_argument("--audio"); pi.add_argument("--tema", default="xolo_oscuro")
    pi.add_argument("--res", default="1920x1080"); pi.add_argument("--fps", type=int, default=30)
    pi.add_argument("--hasta", type=float); pi.add_argument("-o", "--salida")
    pi.add_argument("--saltar-inicio", type=float, default=12.0, dest="saltar_inicio", help="segundos del inicio de cada video madre que se saltan (intros con titulos)")
    for name in ("render", "frame", "hoja"):
        sp = sub.add_parser(name)
        sp.add_argument("proyecto")
        sp.add_argument("-o", "--salida", required=True)
        sp.add_argument("--res")
        sp.add_argument("--fps", type=int)
        if name == "render":
            sp.add_argument("--encoder", default="auto")
            sp.add_argument("--audio")
            sp.add_argument("--hasta", type=float, help="renderizar solo hasta estos segundos")
        if name == "frame":
            sp.add_argument("--t", type=float, required=True)
        if name == "hoja":
            sp.add_argument("--cada", type=float, default=4.0, help="segundos entre fotogramas")
            sp.add_argument("--cols", type=int, default=4)
            sp.add_argument("--ancho", type=int, default=480)
            sp.add_argument("--tiempos", help="lista de segundos separados por coma (en vez de --cada)")
    sub.add_parser("actualizar", help="buscar e instalar la ultima version desde GitHub").add_argument(
        "--solo-revisar", action="store_true")
    a = ap.parse_args()
    if a.cmd == "actualizar":
        from studiofx import actualizar as act
        act.actualizar(forzar=True, solo_revisar=a.solo_revisar)
        return 0
    if a.cmd == "auto":
        from studiofx.auto import armar
        r = armar(a.carpeta, a.salida, a.audio, a.tema, parse_res(a.res), a.fps, a.dur_imagen,
                  a.clip_max, a.segmentos, barra=a.barra)
        print("Proyecto creado:", a.salida, r)
        return 0
    if a.cmd in ("sincronizar", "importar"):
        from studiofx import flujo
        return flujo.correr(a)
    r = Renderer(Project(a.proyecto, parse_res(a.res), a.fps))
    if a.cmd == "render":
        print("Duracion: %.1fs  |  %dx%d @ %dfps" % (r.duration, r.W, r.H, r.fps))
        st = r.render(a.salida, a.encoder, a.audio, t_to=a.hasta)
        print("Listo: %s  (codificador: %s, %.1fs, %.1f fps de render)" % (a.salida, st["codec"], st["segundos"], st["fps_render"]))
        return 0 if st["ffmpeg_rc"] == 0 else 1
    if a.cmd == "frame":
        fr = r.frame_at(a.t)
        cv2.imencode(os.path.splitext(a.salida)[1] or '.png', cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))[1].tofile(a.salida)
        r.close()
        return 0
    if a.cmd == "hoja":
        ts = [float(x) for x in a.tiempos.split(",")] if a.tiempos else list(np.arange(0, r.duration, a.cada))
        tiles = []
        h = int(a.ancho * r.H / r.W)
        for t in ts:
            fr = cv2.resize(r.frame_at(t), (a.ancho, h), interpolation=cv2.INTER_AREA)
            cv2.putText(fr, "%.1fs" % t, (6, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
            tiles.append(fr)
        while len(tiles) % a.cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + a.cols]) for i in range(0, len(tiles), a.cols)]
        cv2.imencode(os.path.splitext(a.salida)[1] or '.png', cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))[1].tofile(a.salida)
        r.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
