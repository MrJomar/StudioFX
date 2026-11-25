"""Ventana 'Revisar escenas': cambiar una foto o clip sin DaVinci. Se abre desde StudioFX.pyw."""
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np

from . import cambios as cb

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOWIN = 0x08000000 if os.name == "nt" else 0


def _miniatura(src, t=1.0, ancho=420):
    try:
        if os.path.splitext(src)[1].lower() in cb.IMG:
            im = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_COLOR)
        else:
            cap = cv2.VideoCapture(src)
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, im = cap.read(); cap.release()
            if not ok:
                return None
        h, w = im.shape[:2]
        im = cv2.resize(im, (ancho, int(h * ancho / w)))
        ok, buf = cv2.imencode(".png", im)
        return tk.PhotoImage(data=buf.tobytes())
    except Exception:
        return None


class Revisor(tk.Toplevel):
    def __init__(self, master, raiz, salida_dir, rearmar):
        super().__init__(master)
        self.title("Revisar escenas")
        self.configure(bg="#101820")
        self.geometry("980x560")
        self.raiz, self.sd, self.rearmar = raiz, salida_dir, rearmar
        ruta = os.path.join(raiz, "STUDIOFX", "proyecto_fx.json")
        if not os.path.exists(ruta):
            messagebox.showinfo("StudioFX", "Primero arma el proyecto (Solo armar proyecto).", parent=self)
            self.destroy(); return
        self.p = json.load(open(ruta, encoding="utf-8"))
        self.esc = [e for e in self.p["escenas"] if e.get("id")]
        t, self.ini = 0.0, {}
        for i, e in enumerate(self.p["escenas"]):
            tr = 0.0 if i == 0 else e.get("trans", 0.3)
            st = 0.0 if i == 0 else t - tr
            t = st + e["dur"]; self.ini[id(e)] = st
        izq = ttk.Frame(self); izq.pack(side="left", fill="y", padx=8, pady=8)
        self.lista = tk.Listbox(izq, width=46, height=28, exportselection=False, bg="#17232e", fg="#eef2f5", selectbackground="#e8872b", selectforeground="#1a1a1a", relief="flat", highlightthickness=0)
        self.lista.pack(side="left", fill="y")
        sb = ttk.Scrollbar(izq, command=self.lista.yview); sb.pack(side="left", fill="y")
        self.lista.config(yscrollcommand=sb.set)
        self.lista.bind("<<ListboxSelect>>", lambda e: self.mostrar())
        der = ttk.Frame(self); der.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.img = ttk.Label(der); self.img.pack()
        self.info = ttk.Label(der, wraplength=480, justify="left"); self.info.pack(anchor="w", pady=6)
        for txt, f in (("Cambiar por otro archivo...", self.cambiar), ("Otro tramo del mismo video", self.otro_tramo),
                       ("Deshacer cambio de esta escena", self.deshacer), ("Vista previa de 6 s", self.previa),
                       ("Guardar y rearmar proyecto", self.guardar)):
            ttk.Button(der, text=txt, command=f).pack(fill="x", pady=2)
        self.refrescar()

    def refrescar(self):
        sel = self.lista.curselection()
        self.cam = {c["id"]: c for c in cb.cargar(self.raiz)}
        self.lista.delete(0, "end")
        for e in self.esc:
            m = int(self.ini[id(e)] // 60); s = self.ini[id(e)] % 60
            marca = "  ✎" if e["id"] in self.cam else ""
            self.lista.insert("end", "%d:%04.1f  %s  %s%s" % (m, s, e["id"], os.path.basename(e["src"])[:26], marca))
        if sel:
            self.lista.selection_set(sel[0])

    def actual(self):
        s = self.lista.curselection()
        return self.esc[s[0]] if s else None

    def mostrar(self):
        e = self.actual()
        if not e:
            return
        c = self.cam.get(e["id"], {})
        src = c.get("nuevo") or e["src"]
        ini = c.get("inicio") if c.get("inicio") is not None else e.get("inicio", 0)
        self.foto = _miniatura(src, ini + 0.5)
        self.img.config(image=self.foto or "")
        self.info.config(text="%s · %s · %.1f s\n%s%s" % (e["id"], e["tipo"], e["dur"], src,
                         ("\nEmpieza en el segundo %.1f del video" % ini) if e["tipo"] == "clip" else ""))

    def cambiar(self):
        e = self.actual()
        if not e:
            return
        f = filedialog.askopenfilename(parent=self, initialdir=os.path.dirname(e["src"]),
                                       filetypes=[("Foto o video", "*.jpg *.jpeg *.png *.webp *.mp4 *.mov *.mkv *.webm *.avi"), ("Todos", "*.*")])
        if f:
            cb.poner(self.raiz, e["id"], os.path.basename(e["src"]), nuevo=f, inicio=0.0 if f.lower().endswith(tuple(cb.VID)) else None)
            self.refrescar(); self.mostrar()

    def otro_tramo(self):
        e = self.actual()
        if not e or e["tipo"] != "clip":
            messagebox.showinfo("StudioFX", "Esta escena es una foto. Usa «Cambiar por otro archivo».", parent=self); return
        c = self.cam.get(e["id"], {})
        src = c.get("nuevo") or e["src"]
        cap = cv2.VideoCapture(src); dv = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(1.0, cap.get(cv2.CAP_PROP_FPS)); cap.release()
        act = c.get("inicio") if c.get("inicio") is not None else e.get("inicio", 0)
        nuevo = act + e["dur"] + 0.5
        if nuevo + e["dur"] > dv:
            nuevo = 6.0 if dv > 30 else 0.0
        cb.poner(self.raiz, e["id"], os.path.basename(e["src"]), inicio=round(nuevo, 2))
        self.refrescar(); self.mostrar()

    def deshacer(self):
        e = self.actual()
        if e:
            cb.quitar(self.raiz, e["id"]); self.refrescar(); self.mostrar()

    def previa(self):
        e = self.actual()
        if not e:
            return
        # la previa muestra el proyecto ya armado; para ver un cambio nuevo hay que "Guardar y rearmar" antes
        t0 = max(0.0, self.ini[id(e)] - 1.5)
        tmp = tempfile.mkdtemp()
        pj = os.path.join(tmp, "mini.json"); mp4 = os.path.join(tmp, "previa.mp4")
        try:
            cb.mini_proyecto(self.p, t0, t0 + 6.0, pj)
            subprocess.run([sys.executable, os.path.join(RAIZ, "cli.py"), "render", pj, "-o", mp4, "--res", "960x540",
                            "--sin-actualizar"], creationflags=NOWIN, cwd=RAIZ, check=True)
            if os.name == "nt":
                os.startfile(mp4)
            else:
                subprocess.Popen(["xdg-open", mp4])
        except Exception as ex:
            messagebox.showerror("StudioFX", "No pude hacer la vista previa:\n%s" % ex, parent=self)

    def guardar(self):
        self.destroy()
        self.rearmar()
