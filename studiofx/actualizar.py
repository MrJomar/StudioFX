"""Auto-actualizacion desde GitHub.

Configuracion (opcional) en  actualizacion.json  junto a cli.py:
  {"repo": "MrJomar/StudioFX", "rama": "main", "token": "", "auto": true}
Si el repo es privado hace falta un token (GitHub > Settings > Developer settings >
Fine-grained tokens, permiso de solo lectura "Contents" sobre ese repo).
Nunca falla el programa: sin internet o con error simplemente sigue con la version instalada.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(RAIZ, "actualizacion.json")
MARCA = os.path.join(RAIZ, ".version_instalada")
CACHE = os.path.join(RAIZ, ".ultima_revision")
# se reemplaza el codigo y los recursos; lo del usuario se conserva
PROTEGIDOS = {"salida", "actualizacion.json", "mapas.json", ".version_instalada", ".ultima_revision", "__pycache__", ".git"}


def config():
    c = dict(repo="MrJomar/StudioFX", rama="main", token="", auto=True)
    if os.path.exists(CFG):
        try:
            c.update(json.load(open(CFG, encoding="utf-8")))
        except Exception:
            pass
    return c


def _get(url, c, timeout=8):
    h = {"User-Agent": "StudioFX", "Accept": "application/vnd.github+json"}
    if c.get("token"):
        h["Authorization"] = "Bearer " + c["token"]
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout).read()


def sha_remoto(c):
    d = json.loads(_get("https://api.github.com/repos/%s/commits/%s" % (c["repo"], c["rama"]), c))
    return d["sha"], d["commit"]["message"].splitlines()[0]


def sha_local():
    return open(MARCA).read().strip() if os.path.exists(MARCA) else ""


def aplicar_zip(datos, destino=RAIZ):
    """Copia el contenido del zip (carpeta raiz unica de GitHub) sobre `destino`, sin tocar lo protegido."""
    tmp = tempfile.mkdtemp()
    try:
        zipfile.ZipFile(io.BytesIO(datos)).extractall(tmp)
        base = os.path.join(tmp, os.listdir(tmp)[0])
        n = 0
        for dp, dn, fn in os.walk(base):
            rel = os.path.relpath(dp, base)
            top = rel.split(os.sep)[0]
            if top in PROTEGIDOS or "__pycache__" in rel:
                dn[:] = []
                continue
            for f in fn:
                if rel == "." and f in PROTEGIDOS:
                    continue
                d = os.path.join(destino, "" if rel == "." else rel)
                os.makedirs(d, exist_ok=True)
                shutil.copy2(os.path.join(dp, f), os.path.join(d, f))
                n += 1
        return n
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def revisar(forzar=False, silencioso=True):
    """Devuelve (hay_nueva, sha, mensaje). None si no se pudo consultar."""
    c = config()
    if not forzar and os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < 3600:
        return None  # ya se reviso hace menos de 1 hora
    try:
        sha, msg = sha_remoto(c)
        open(CACHE, "w").write(str(time.time()))
    except Exception as e:
        if not silencioso:
            print("No pude consultar actualizaciones (%s)" % e)
        return None
    return (sha != sha_local(), sha, msg)


def actualizar(forzar=False, solo_revisar=False, silencioso=False):
    """True si se instalo una version nueva."""
    r = revisar(forzar=forzar, silencioso=silencioso)
    if r is None:
        if not silencioso:
            print("Sin cambios que revisar por ahora.")
        return False
    hay, sha, msg = r
    if not hay:
        if not silencioso:
            print("StudioFX ya esta al dia.")
        return False
    print("Hay una version nueva: %s" % msg)
    if solo_revisar:
        return False
    c = config()
    try:
        datos = _get("https://api.github.com/repos/%s/zipball/%s" % (c["repo"], c["rama"]), c, timeout=60)
        n = aplicar_zip(datos)
        open(MARCA, "w").write(sha)
    except Exception as e:
        print("No pude actualizar (%s). Sigo con la version actual." % e)
        return False
    print("Actualizado (%d archivos)." % n)
    return True


def al_abrir():
    """Se llama al inicio de cada comando: revisa y, si hay version nueva, la instala y relanza."""
    if os.environ.get("STUDIOFX_SIN_ACTUALIZAR") or not config().get("auto", True):
        return
    if "--sin-actualizar" in sys.argv:
        sys.argv.remove("--sin-actualizar")
        return
    if actualizar(silencioso=True):
        os.environ["STUDIOFX_SIN_ACTUALIZAR"] = "1"
        os.execv(sys.executable, [sys.executable] + sys.argv)
