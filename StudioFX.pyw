"""StudioFX - ventana principal. Doble clic para abrir."""
import importlib.util
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
CFG = os.path.join(RAIZ, ".ajustes_gui.json")
NOWIN = 0x08000000 if os.name == "nt" else 0
BG, FG, AC = "#14202b", "#eef2f5", "#e8872b"


def cargar():
    try:
        return json.load(open(CFG, encoding="utf-8"))
    except Exception:
        return {}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("StudioFX - Xolo Explorador")
        self.geometry("820x600")
        self.configure(bg=BG)
        self.aj = cargar()
        self.ocupado = False
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        st.configure("TFrame", background=BG)
        st.configure("TCheckbutton", background=BG, foreground=FG)
        st.configure("TButton", font=("Segoe UI", 10), padding=6)
        st.configure("Big.TButton", font=("Segoe UI", 13, "bold"), padding=12, background=AC, foreground="#1a1a1a")
        st.map("Big.TButton", background=[("active", "#ffa24a")])
        st.configure("Horizontal.TProgressbar", background=AC, troughcolor="#22303d")
        f = ttk.Frame(self, padding=14)
        f.pack(fill="both", expand=True)
        from studiofx import __version__
        cab = ttk.Frame(f)
        cab.pack(fill="x")
        ttk.Label(cab, text="StudioFX", font=("Segoe UI", 20, "bold"), foreground=AC).pack(side="left")
        ttk.Label(cab, text="  v" + __version__).pack(side="left", pady=(10, 0))
        ttk.Button(cab, text="\u27f3  Actualizar StudioFX", command=lambda: self.actualizar(True)).pack(side="right")
        ttk.Label(f, text="Elige la carpeta del proyecto (la que tiene el guion JSON, Audio y las carpetas de B-roll).").pack(anchor="w", pady=(0, 8))
        fila = ttk.Frame(f)
        fila.pack(fill="x")
        self.ruta = tk.StringVar(value=self.aj.get("ruta", ""))
        ttk.Entry(fila, textvariable=self.ruta, font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, ipady=4)
        ttk.Button(fila, text="Elegir carpeta...", command=self.elegir).pack(side="left", padx=(8, 0))
        op = ttk.Frame(f)
        op.pack(fill="x", pady=10)
        ttk.Label(op, text="Modo:").pack(side="left")
        self.modo = tk.StringVar(value=self.aj.get("modo", "Borrador (720p, primeros 2 min)"))
        ttk.Combobox(op, textvariable=self.modo, state="readonly", width=34,
                     values=["Borrador (720p, primeros 2 min)", "Borrador completo (720p)", "Final (1080p)"]).pack(side="left", padx=8)
        self.tema = tk.StringVar(value=self.aj.get("tema", "xolo_oscuro"))
        ttk.Label(op, text="Tema:").pack(side="left", padx=(14, 0))
        ttk.Combobox(op, textvariable=self.tema, state="readonly", width=14,
                     values=["xolo_oscuro", "xolo_claro"]).pack(side="left", padx=8)
        self.btn = ttk.Button(f, text="HACER TODO  (sincronizar + armar + renderizar)", style="Big.TButton", command=self.todo)
        self.btn.pack(fill="x", pady=(4, 8))
        fb = ttk.Frame(f)
        fb.pack(fill="x")
        ttk.Button(fb, text="Solo armar proyecto", command=lambda: self.lanzar(["importar"])).pack(side="left")
        ttk.Button(fb, text="Abrir carpeta de salida", command=self.abrir).pack(side="left", padx=8)
        self.barra = ttk.Progressbar(f, mode="determinate", maximum=100)
        self.barra.pack(fill="x", pady=10)
        self.estado = ttk.Label(f, text="Listo.")
        self.estado.pack(anchor="w")
        self.log = tk.Text(f, height=16, bg="#0d151d", fg="#c9d4dc", font=("Consolas", 9), relief="flat", wrap="word")
        self.log.pack(fill="both", expand=True, pady=(6, 0))
        self.after(600, lambda: self.actualizar(False))

    # ---------- utilidades ----------
    def escribe(self, txt):
        self.log.insert("end", txt)
        self.log.see("end")

    def guardar(self):
        json.dump(dict(ruta=self.ruta.get(), modo=self.modo.get(), tema=self.tema.get()), open(CFG, "w", encoding="utf-8"))

    def elegir(self):
        d = filedialog.askdirectory(title="Carpeta del proyecto", initialdir=self.ruta.get() or "C:\\")
        if d:
            self.ruta.set(os.path.normpath(d))

    def salida_dir(self):
        return os.path.join(self.ruta.get(), "STUDIOFX")

    def abrir(self):
        d = self.salida_dir()
        os.makedirs(d, exist_ok=True)
        if os.name == "nt":
            os.startfile(d)
        else:
            subprocess.Popen(["xdg-open", d])

    def validar(self):
        r = self.ruta.get().strip()
        if not r or not os.path.isdir(r):
            messagebox.showwarning("StudioFX", "Primero elige la carpeta del proyecto.")
            return False
        self.guardar()
        return True

    # ---------- actualizaciones ----------
    def actualizar(self, manual):
        def trabajo():
            try:
                from studiofx import actualizar as act
                if manual:
                    r = act.revisar(forzar=True, silencioso=False)
                else:
                    if not act.config().get("auto", True):
                        return
                    r = act.revisar(silencioso=True)
                if r is None:
                    if manual:
                        self.after(0, lambda: messagebox.showwarning("StudioFX", "No pude consultar GitHub.\nRevisa tu internet, el nombre del repo y el token en actualizacion.json."))
                    return
                hay, sha, msg = r
                if not hay:
                    if manual:
                        self.after(0, lambda: messagebox.showinfo("StudioFX", "StudioFX ya está al día."))
                    return
                self.after(0, lambda: self.estado.config(text="Actualizando: %s ..." % msg))
                if act.actualizar(forzar=True, silencioso=True):
                    self.after(0, self.reiniciar)
            except Exception as e:
                if manual:
                    self.after(0, lambda: self.estado.config(text="Error al actualizar: %s" % e))
        threading.Thread(target=trabajo, daemon=True).start()

    def reiniciar(self):
        messagebox.showinfo("StudioFX", "Se instaló una versión nueva. El programa se reiniciará.")
        subprocess.Popen([sys.executable, os.path.abspath(__file__)])
        self.destroy()

    # ---------- ejecucion ----------
    def cli(self, args, progreso=None):
        cmd = [sys.executable, os.path.join(RAIZ, "cli.py")] + args + ["--sin-actualizar"]
        self.escribe("\n> " + " ".join(os.path.basename(a) if i == 0 else a for i, a in enumerate(cmd[1:])) + "\n")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, creationflags=NOWIN, cwd=RAIZ)
        buf = b""
        while True:
            c = p.stdout.read(1)
            if not c:
                break
            if c in (b"\r", b"\n"):
                linea = buf.decode("utf-8", "replace").strip()
                buf = b""
                if not linea:
                    continue
                m = None
                if "fps de render" in linea and "/" in linea.split()[0]:
                    try:
                        a, b = linea.split()[0].split("/")
                        m = int(a) * 100.0 / int(b)
                    except ValueError:
                        m = None
                if m is not None:
                    self.after(0, lambda v=m, l=linea: (self.barra.config(value=v), self.estado.config(text="Renderizando %.0f%%" % v)))
                else:
                    self.after(0, lambda l=linea: self.escribe(l + "\n"))
            else:
                buf += c
        return p.wait()

    def lanzar(self, pasos):
        if self.ocupado or not self.validar():
            return
        self.ocupado = True
        self.btn.state(["disabled"])
        self.barra.config(value=0)
        threading.Thread(target=self.correr, args=(pasos,), daemon=True).start()

    def todo(self):
        self.lanzar(["sincronizar", "importar", "render"])

    def correr(self, pasos):
        try:
            r = self.ruta.get()
            modo = self.modo.get()
            res = "1920x1080" if modo.startswith("Final") else "1280x720"
            hasta = ["--hasta", "120"] if "2 min" in modo else []
            proyecto = os.path.join(self.salida_dir(), "proyecto_fx.json")
            final = os.path.join(self.salida_dir(), "video_final.mp4" if not hasta and res == "1920x1080" else
                                 ("borrador_2min.mp4" if hasta else "borrador.mp4"))
            for p in pasos:
                self.after(0, lambda p=p: self.estado.config(text={"sincronizar": "Sincronizando audio con el guion...",
                                                                  "importar": "Armando la línea de tiempo...",
                                                                  "render": "Renderizando..."}[p]))
                if p == "sincronizar":
                    args = ["sincronizar", r]
                    if importlib.util.find_spec("faster_whisper") is None:
                        args.append("--estimar")
                        self.after(0, lambda: self.escribe("(faster-whisper no está instalado: tiempos aproximados por pausas)\n"))
                    rc = self.cli(args)
                elif p == "importar":
                    rc = self.cli(["importar", r, "--res", res, "--tema", self.tema.get()] + hasta)
                else:
                    rc = self.cli(["render", proyecto, "-o", final] + hasta)
                if rc != 0:
                    self.after(0, lambda: self.estado.config(text="Hubo un error; revisa el registro."))
                    return
            self.after(0, lambda: (self.barra.config(value=100), self.estado.config(text="¡Listo! " + (final if "render" in pasos else "Proyecto armado."))))
            if "render" in pasos:
                self.after(0, self.abrir)
        finally:
            self.ocupado = False
            self.after(0, lambda: self.btn.state(["!disabled"]))


if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception:
        import traceback
        txt = traceback.format_exc()
        open(os.path.join(RAIZ, "error.log"), "w", encoding="utf-8").write(txt)
        try:
            messagebox.showerror("StudioFX - error al abrir", txt[-1500:] + "\n\n(guardado en error.log)")
        except Exception:
            pass
