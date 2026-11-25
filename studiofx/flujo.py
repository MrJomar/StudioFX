import json
import os

from . import sincronizar as S
from .importar import importar


def _buscar_guion(raiz):
    for dp, dn, fn in os.walk(raiz):
        if dp[len(raiz):].count(os.sep) > 3:
            dn[:] = []
        for f in fn:
            if f.lower().endswith(".json"):
                try:
                    d = json.load(open(os.path.join(dp, f), encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(d, dict) and {"segmentos", "xolo_estudio", "hook_visual"} <= set(d):
                    return os.path.join(dp, f)
    raise SystemExit("No encontre el guion JSON en la carpeta; usa --guion")


def _buscar_audio(raiz):
    for dp, dn, fn in os.walk(raiz):
        for f in fn:
            if f.lower() == "audio_completo.wav":
                return os.path.join(dp, f)
    raise SystemExit("No encontre Audio/audio_completo.wav; usa --audio")


def _buscar_marcadores(raiz):
    for dp, dn, fn in os.walk(raiz):
        for f in fn:
            if f.lower().startswith("marcadores") and f.lower().endswith(".json"):
                return os.path.join(dp, f)
    return None


def _informe(d, informe):
    nuevos = sum(1 for r in informe if r["origen"] == "nuevo")
    malos = [r for r in informe if r["avisos"]]
    L = ["# Validación de visuales (StudioFX)", "", "Visuales: %d (nuevos %d). Con avisos: %d." % (len(informe), nuevos, len(malos)), ""]
    for r in malos:
        L.append("- **%s** (bloque %d, %s, %s)" % (r["id"], r["bloque"], r["kind"], r["origen"]))
        for a in r["avisos"]:
            L.append("  - %s" % a)
    open(os.path.join(d, "validacion.md"), "w", encoding="utf-8").write("\n".join(L))
    print("Validación:", "todo respaldado por el guion" if not malos else "%d visual(es) con avisos (ver STUDIOFX\\validacion.md)" % len(malos))


def correr(a):
    raiz = os.path.abspath(a.proyecto)
    gj = a.guion or _buscar_guion(raiz)
    au = a.audio or _buscar_audio(raiz)
    guion = json.load(open(gj, encoding="utf-8"))
    d = os.path.join(raiz, "STUDIOFX")
    os.makedirs(d, exist_ok=True)
    tp = os.path.join(d, "tiempos.json")
    if a.cmd == "sincronizar":
        if a.estimar:
            t = S.estimar(guion, au)
        else:
            try:
                pal = S.transcribir(au, a.modelo)
                t = S.alinear(guion, pal, S.duracion(au))
            except ImportError:
                raise SystemExit("Falta faster-whisper: pip install faster-whisper  (o usa --estimar)")
        json.dump(t, open(tp, "w", encoding="utf-8"), ensure_ascii=False)
        print("Tiempos (%s) guardados en %s" % (t["origen"], tp), t.get("aviso", ""))
        return 0
    if not os.path.exists(tp):
        print("Aun no hay tiempos; usando estimacion (corre 'sincronizar' para mayor precision)")
        t = S.estimar(guion, au)
        json.dump(t, open(tp, "w", encoding="utf-8"), ensure_ascii=False)
    t = json.load(open(tp, encoding="utf-8"))
    from .enriquecer import enriquecer
    guion_e, informe = enriquecer(guion)
    json.dump(guion_e, open(os.path.join(d, "guion_enriquecido.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    marc = _buscar_marcadores(raiz)
    marcadores = json.load(open(marc, encoding="utf-8")) if marc else None
    w, h = a.res.lower().split("x")
    salida = a.salida or os.path.join(d, "proyecto_fx.json")
    r = importar(raiz, guion_e, t, salida, audio=au, tema=a.tema, res=(int(w), int(h)), fps=a.fps, hasta=a.hasta,
                 marcadores=marcadores, saltar_ini=getattr(a, "saltar_inicio", 12.0),
                 cambios=__import__("studiofx.cambios", fromlist=["x"]).cargar(raiz),
                 solo_imagenes=not getattr(a, "con_videos", False))
    _informe(d, informe)
    print("Proyecto:", salida, {k: v for k, v in r.items() if k != "avisos"})
    for x in r["avisos"]:
        print("  AVISO:", x)
    return 0
