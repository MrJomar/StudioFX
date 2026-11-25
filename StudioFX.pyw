"""StudioFX - ventana principal. Doble clic para abrir."""
import importlib.util
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
CFG = os.path.join(RAIZ, ".ajustes_gui.json")
NOWIN = 0x08000000 if os.name == "nt" else 0
BG, PAN, FG, SUAVE, AC = "#101820", "#17232e", "#eef2f5", "#8fa1b0", "#e8872b"
COLORES = {"verde": "#4cc38a", "azul": "#5aa9ff", "amarillo": "#f0c040", "rojo": "#ef6461", "gris": "#8fa1b0"}
MODOS = ["Borrador (720p, primeros 2 min)", "Borrador completo (720p)", "Final (1080p)"]


def cargar():
    try:
        return json.load(open(CFG, encoding="utf-8"))
    except Exception:
        return {}


def abrir_en_so(ruta):
    if os.name == "nt":
        os.startfile(ruta)
    else:
        subprocess.Popen(["xdg-open", ruta])


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        from studiofx import __version__, proyectos
        self.P = proyectos
        self.title("StudioFX %s - Xolo Explorador" % __version__)
        self.geometry("1180x740")
        self.minsize(980, 620)
        self.configure(bg=BG)
        self.aj = cargar()
        self.ocupado = False
        self.actual = None      # ruta del proyecto elegido
        self.est = None
        self.estilos()
        self.construir(__version__)
        self.refrescar_lista(self.aj.get("ruta"))
        self.after(300, lambda: self.actualizar(False))

    # ---------- estilos ----------
    def estilos(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        base = ("Segoe UI", 10)
        st.configure(".", background=BG, foreground=FG, font=base, fieldbackground=PAN, bordercolor=PAN)
        st.configure("TLabel", background=BG, foreground=FG)
        st.configure("Suave.TLabel", foreground=SUAVE)
        st.configure("Panel.TFrame", background=PAN)
        st.configure("Panel.TLabel", background=PAN, foreground=FG)
        st.configure("TFrame", background=BG)
        st.configure("TCheckbutton", background=BG, foreground=FG)
        st.configure("TButton", padding=(10, 6), background="#22323f", foreground=FG, borderwidth=0)
        st.map("TButton", background=[("active", "#2d4152"), ("disabled", "#1a2630")], foreground=[("disabled", "#5d6e7c")])
        st.configure("Acento.TButton", background=AC, foreground="#1a1a1a", font=("Segoe UI", 11, "bold"), padding=(14, 9))
        st.map("Acento.TButton", background=[("active", "#ffa24a"), ("disabled", "#6b4a26")])
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", background="#1a2630", foreground=SUAVE, padding=(16, 8))
        st.map("TNotebook.Tab", background=[("selected", PAN)], foreground=[("selected", FG)])
        st.configure("Treeview", background=PAN, fieldbackground=PAN, foreground=FG, rowheight=30, borderwidth=0)
        st.configure("Treeview.Heading", background="#1a2630", foreground=SUAVE, relief="flat", font=("Segoe UI", 9, "bold"))
        st.map("Treeview", foreground=[e for e in st.map("Treeview", query_opt="foreground") if e[:2] != ("!disabled", "!selected")],
               background=[e for e in st.map("Treeview", query_opt="background") if e[:2] != ("!disabled", "!selected")] + [("selected", "#2d4152")])
        st.map("TCombobox", fieldbackground=[("readonly", PAN)], foreground=[("readonly", FG)], background=[("readonly", "#22323f")],
               selectbackground=[("readonly", PAN)], selectforeground=[("readonly", FG)])
        self.option_add("*TCombobox*Listbox.background", PAN)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", AC)
        st.configure("Horizontal.TProgressbar", background=AC, troughcolor="#22303d", borderwidth=0)

    # ---------- construccion ----------
    def construir(self, version):
        top = ttk.Frame(self, padding=(16, 12))
        top.pack(fill="x")
        ttk.Label(top, text="StudioFX", font=("Segoe UI", 20, "bold"), foreground=AC).pack(side="left")
        ttk.Label(top, text="  v" + version, style="Suave.TLabel").pack(side="left", pady=(10, 0))
        ttk.Button(top, text="\u27f3  Actualizar", command=lambda: self.actualizar(True)).pack(side="right")
        ttk.Button(top, text="Agregar existente...", command=self.agregar_existente).pack(side="right", padx=8)
        ttk.Button(top, text="+  Nuevo proyecto", style="Acento.TButton", command=self.nuevo).pack(side="right")

        # --- barra de acciones
        ab = ttk.Frame(self, padding=(16, 4, 16, 14))
        ab.pack(fill="x", side="bottom")
        op = ttk.Frame(ab)
        op.pack(fill="x", pady=(0, 8))
        ttk.Label(op, text="Modo:").pack(side="left")
        self.modo = tk.StringVar(value=self.aj.get("modo", MODOS[0]))
        ttk.Combobox(op, textvariable=self.modo, state="readonly", width=32, values=MODOS).pack(side="left", padx=(6, 14))
        ttk.Label(op, text="Tema:").pack(side="left")
        self.tema = tk.StringVar(value=self.aj.get("tema", "xolo_oscuro"))
        ttk.Combobox(op, textvariable=self.tema, state="readonly", width=12, values=["xolo_oscuro", "xolo_claro"]).pack(side="left", padx=(6, 14))
        self.con_videos = tk.BooleanVar(value=self.aj.get("con_videos", False))
        ttk.Checkbutton(op, text="Usar también videos de las carpetas", variable=self.con_videos).pack(side="left")
        bb = ttk.Frame(ab)
        bb.pack(fill="x")
        self.btn = ttk.Button(bb, text="HACER TODO", style="Acento.TButton", command=self.todo)
        self.btn.pack(side="left")
        self.botones = [self.btn]
        for tx, f in (("1  Sincronizar", lambda: self.lanzar(["sincronizar"])), ("2  Armar proyecto", lambda: self.lanzar(["importar"])),
                      ("Revisar escenas", self.revisar), ("3  Renderizar", lambda: self.lanzar(["render"])),
                      ("Abrir salida", lambda: self.abrir(os.path.join(self.actual or "", "STUDIOFX")))):
            b = ttk.Button(bb, text=tx, command=f); b.pack(side="left", padx=(8, 0)); self.botones.append(b)
        self.barra = ttk.Progressbar(ab, mode="determinate", maximum=100)
        self.barra.pack(fill="x", pady=(10, 4))
        self.estado = ttk.Label(ab, text="Listo.", style="Suave.TLabel")
        self.estado.pack(anchor="w")

        cuerpo = ttk.Frame(self, padding=(16, 0, 16, 8))
        cuerpo.pack(fill="both", expand=True)
        izq = ttk.Frame(cuerpo, style="Panel.TFrame", padding=8)
        izq.pack(side="left", fill="y")
        ttk.Label(izq, text="PROYECTOS", style="Panel.TLabel", foreground=SUAVE, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=4, pady=(2, 6))
        self.arbol = ttk.Treeview(izq, columns=("etapa",), show="tree", height=18, selectmode="browse")
        self.arbol.column("#0", width=215); self.arbol.column("etapa", width=125, stretch=False)
        self.arbol.pack(fill="y", expand=True)
        for k, c in COLORES.items():
            self.arbol.tag_configure(k, foreground=c)
        self.arbol.bind("<<TreeviewSelect>>", lambda e: self.elegir())
        ttk.Button(izq, text="Quitar de la lista", command=self.quitar).pack(fill="x", pady=(8, 0))

        der = ttk.Frame(cuerpo, padding=(14, 0, 0, 0))
        der.pack(side="left", fill="both", expand=True)
        self.titulo = ttk.Label(der, text="Elige o crea un proyecto", font=("Segoe UI", 15, "bold"))
        self.titulo.pack(anchor="w")
        self.subtitulo = ttk.Label(der, text="", style="Suave.TLabel")
        self.subtitulo.pack(anchor="w", pady=(0, 8))
        self.nb = ttk.Notebook(der)
        self.nb.pack(fill="both", expand=True)

        # --- Resumen
        t1 = ttk.Frame(self.nb, style="Panel.TFrame", padding=12)
        self.nb.add(t1, text="  Resumen  ")
        self.lista_req = ttk.Frame(t1, style="Panel.TFrame")
        self.lista_req.pack(fill="x")
        bt = ttk.Frame(t1, style="Panel.TFrame")
        bt.pack(fill="x", pady=8)
        ttk.Button(bt, text="Agregar guion JSON...", command=self.agregar_guion).pack(side="left")
        ttk.Button(bt, text="Elegir audio...", command=self.elegir_audio).pack(side="left", padx=6)
        ttk.Button(bt, text="Abrir carpeta del proyecto", command=lambda: self.abrir(self.actual)).pack(side="left")
        self.t_bloques = ttk.Treeview(t1, columns=("fotos", "ideal", "estado"), show="headings", height=10)
        for c, tx, w in (("fotos", "Fotos", 60), ("ideal", "Ideal", 60), ("estado", "Estado", 200)):
            self.t_bloques.heading(c, text=tx); self.t_bloques.column(c, width=w, anchor="w")
        self.t_bloques["show"] = "tree headings"
        self.t_bloques.heading("#0", text="Bloque"); self.t_bloques.column("#0", width=380)
        self.t_bloques.pack(fill="both", expand=True)
        self.t_bloques.bind("<Double-1>", lambda e: self.abrir_bloque())
        ttk.Label(t1, text="«Ideal» = fotos para un cambio cada ~4 s. Si faltan, se reutilizan con acercamientos. Doble clic abre la carpeta.", style="Panel.TLabel", foreground=SUAVE).pack(anchor="w", pady=(4, 0))

        # --- Imagenes que faltan
        t2 = ttk.Frame(self.nb, style="Panel.TFrame", padding=12)
        self.nb.add(t2, text="  Imágenes que faltan  ")
        self.t2 = t2
        self.lbl_falta = ttk.Label(t2, text="", style="Panel.TLabel", wraplength=760, justify="left")
        self.lbl_falta.pack(anchor="w", pady=(0, 6))
        self.t_falta = ttk.Treeview(t2, columns=("min", "que", "archivo", "estado"), show="headings", height=12)
        for c, tx, w in (("min", "Minuto", 70), ("que", "Qué foto necesita", 430), ("archivo", "Nombre del archivo", 130), ("estado", "", 70)):
            self.t_falta.heading(c, text=tx); self.t_falta.column(c, width=w, anchor="w")
        self.t_falta.pack(fill="both", expand=True)
        self.t_falta.bind("<Double-1>", lambda e: self.poner_foto())
        bf = ttk.Frame(t2, style="Panel.TFrame")
        bf.pack(fill="x", pady=8)
        ttk.Button(bf, text="Agregar foto a este visual...", command=self.poner_foto).pack(side="left")
        ttk.Button(bf, text="Volver a revisar", command=self.recargar).pack(side="left", padx=6)
        ttk.Label(bf, text="Se copia al bloque con el nombre correcto.", style="Panel.TLabel", foreground=SUAVE).pack(side="left", padx=8)

        # --- Registro
        t3 = ttk.Frame(self.nb, style="Panel.TFrame", padding=8)
        self.nb.add(t3, text="  Registro  ")
        self.log = tk.Text(t3, bg="#0b1218", fg="#cfe0ec", insertbackground=FG, relief="flat", font=("Consolas", 9), wrap="word")
        self.log.pack(fill="both", expand=True)

    def escribe(self, txt):
        self.log.insert("end", txt)
        self.log.see("end")

    def guardar(self):
        json.dump(dict(ruta=self.actual, modo=self.modo.get(), tema=self.tema.get(), con_videos=self.con_videos.get()),
                  open(CFG, "w", encoding="utf-8"))

    # ---------- proyectos ----------
    def refrescar_lista(self, elegir=None):
        sel = elegir or self.actual
        self.arbol.delete(*self.arbol.get_children())
        self.ests = {}
        for r in self.P.cargar_lista():
            e = self.P.estado(r)
            self.ests[r] = e
            pend = "  ⚠ %d" % e["n_visuales_sin_foto"] if e.get("n_visuales_sin_foto") else ""
            self.arbol.insert("", "end", iid=r, text="●  " + e["nombre"][:26], values=(e["etapa"] + pend,), tags=(e["color"],))
        if sel and sel in self.ests:
            self.arbol.selection_set(sel)
        elif self.ests:
            self.arbol.selection_set(next(iter(self.ests)))
        else:
            self.mostrar(None)

    def elegir(self):
        s = self.arbol.selection()
        if s:
            self.actual = s[0]
            self.mostrar(self.ests.get(s[0]) or self.P.estado(s[0]))

    def recargar(self):
        self.refrescar_lista(self.actual)

    def mostrar(self, e):
        self.est = e
        for w in self.lista_req.winfo_children():
            w.destroy()
        self.t_bloques.delete(*self.t_bloques.get_children())
        self.t_falta.delete(*self.t_falta.get_children())
        if not e:
            self.titulo.config(text="Elige o crea un proyecto"); self.subtitulo.config(text="")
            self.lbl_falta.config(text="")
            return
        self.titulo.config(text=e["titulo"])
        self.subtitulo.config(text="%s  ·  %s" % (e["etapa"], e["ruta"]), foreground=COLORES[e["color"]])
        def req(ok, txt):
            ttk.Label(self.lista_req, text=("✔  " if ok else "✘  ") + txt, style="Panel.TLabel",
                      foreground=COLORES["verde"] if ok else COLORES["rojo"]).pack(anchor="w")
        req(bool(e.get("guion")), "Guion JSON" + (": " + os.path.basename(e["guion"]) if e.get("guion") else " (usa «Agregar guion JSON»)"))
        req(bool(e.get("audio")), "Audio\\audio_completo.wav" if e.get("audio") else "Falta Audio\\audio_completo.wav")
        req(bool(e.get("marcadores")), "marcadores_davinci.json" if e.get("marcadores") else "marcadores_davinci.json (opcional: sin él los bloques se estiman por la voz)")
        req(bool(e.get("transcripcion")), "Transcripción con tiempos: " + e["transcripcion"] if e.get("transcripcion") else "Transcripción con tiempos (opcional: sin ella se usa Whisper o una estimación)")
        req(e["sincronizado"], "Sincronizado con la voz")
        req(e["armado"], "Proyecto armado")
        req(bool(e["renderizado"]), "Video renderizado" + (": " + os.path.basename(e["renderizado"]) if e["renderizado"] else ""))
        from studiofx.importar import IDEAL_FOTO
        pend_b = {p["etiqueta"]: p for p in e["pendientes"] if p["tipo"] == "bloque"}
        for b in e["bloques"]:
            p = pend_b.get("Bloque %d" % b["n"])
            ideal = p["ideal"] if p else "-"
            if b["carpeta"] is None:
                est = "Sin carpeta de fotos"
            elif b["fotos"] == 0:
                est = "Sin fotos"
            elif p and p["faltan"] > 0:
                est = "Faltan ~%d" % p["faltan"]
            elif p:
                est = "Completo"
            else:
                est = "Arma el proyecto para calcular"
            self.t_bloques.insert("", "end", text=b["nombre"], values=(b["fotos"], ideal, est))
        vis = [p for p in e["pendientes"] if p["tipo"] in ("visual", "foto")]
        for p in vis:
            m, s = divmod(int(p["t"]), 60)
            self.t_falta.insert("", "end", iid=p["id"], values=("%d:%02d" % (m, s), p["pedir"] or "(foto para el visual %s)" % p["efecto"], p["archivo"], "OBLIGAT." if p["obligatoria"] else ("foto" if p["tipo"] == "foto" else "sugerida")))
        if vis:
            self.lbl_falta.config(text="⚠  %d visual(es) necesitan una foto específica (un personaje, documento o lugar concreto). Sin ella se usa una versión sin imagen o se omite." % len(vis),
                                  foreground=COLORES["amarillo"])
        else:
            self.lbl_falta.config(text="✔  No hay visuales pendientes de foto." if e["armado"] else "Arma el proyecto para saber qué visuales necesitan foto.",
                                  foreground=COLORES["verde"] if e["armado"] else SUAVE)

    def nuevo(self):
        g = filedialog.askopenfilename(title="1/2  Elige el guion JSON del video", filetypes=[("Guion JSON", "*.json")])
        if not g:
            return
        gd = self.P.es_guion(g)
        if gd is None:
            messagebox.showerror("StudioFX", "Ese JSON no es un guion de Xolo Estudio (le faltan segmentos / xolo_estudio / hook_visual).")
            return
        padre = filedialog.askdirectory(title="2/2  ¿Dónde guardo la carpeta del proyecto?", initialdir=self.aj.get("padre") or os.path.expanduser("~"))
        if not padre:
            return
        nombre = simpledialog.askstring("StudioFX", "Nombre de la carpeta del proyecto:", initialvalue=(gd.get("titulo") or "Proyecto")[:70], parent=self)
        if not nombre:
            return
        nombre = "".join(c for c in nombre if c not in '<>:"/\\|?*').strip()
        try:
            ruta = self.P.crear(padre, nombre, g)
        except Exception as ex:
            messagebox.showerror("StudioFX", str(ex)); return
        self.aj["padre"] = padre
        self.refrescar_lista(ruta)
        messagebox.showinfo("StudioFX", "Proyecto creado con una carpeta de fotos por bloque.\n\nMete tus fotos en cada carpeta (de preferencia horizontales) y el audio en Audio\\audio_completo.wav. Luego pulsa HACER TODO.")
        self.abrir(ruta)

    def agregar_existente(self):
        d = filedialog.askdirectory(title="Carpeta del proyecto (con el guion JSON, Audio y carpetas de fotos)", initialdir=self.aj.get("padre") or "C:\\")
        if d:
            self.P.agregar(os.path.normpath(d))
            self.refrescar_lista(os.path.normpath(d))

    def quitar(self):
        if self.actual and messagebox.askyesno("StudioFX", "¿Quitar este proyecto de la lista?\n(No se borra ningún archivo.)"):
            self.P.quitar(self.actual); self.actual = None
            self.refrescar_lista()

    def agregar_guion(self):
        if not self.actual:
            return
        g = filedialog.askopenfilename(title="Guion JSON", filetypes=[("Guion JSON", "*.json")])
        if g:
            try:
                self.P.poner_guion(self.actual, g)
            except ValueError as ex:
                messagebox.showerror("StudioFX", str(ex)); return
            self.recargar()

    def elegir_audio(self):
        if not self.actual:
            return
        a = filedialog.askopenfilename(title="Audio del video (wav/mp3)", filetypes=[("Audio", "*.wav *.mp3 *.m4a *.flac")])
        if a:
            import shutil
            os.makedirs(os.path.join(self.actual, "Audio"), exist_ok=True)
            if a.lower().endswith(".wav"):
                shutil.copy2(a, os.path.join(self.actual, "Audio", "audio_completo.wav"))
            else:
                r = subprocess.run(["ffmpeg", "-y", "-i", a, os.path.join(self.actual, "Audio", "audio_completo.wav")], capture_output=True, creationflags=NOWIN)
                if r.returncode != 0:
                    messagebox.showerror("StudioFX", "No pude convertir el audio a WAV (¿está ffmpeg instalado?). Conviértelo y vuelve a intentar.")
                    return
            self.recargar()

    def abrir(self, ruta):
        if ruta:
            os.makedirs(ruta, exist_ok=True)
            abrir_en_so(ruta)

    def abrir_bloque(self):
        s = self.t_bloques.selection()
        if s and self.est:
            i = self.t_bloques.index(s[0])
            c = self.est["bloques"][i]["carpeta"]
            if c:
                abrir_en_so(c)

    def poner_foto(self):
        s = self.t_falta.selection()
        if not s or not self.est:
            messagebox.showinfo("StudioFX", "Elige primero un visual de la lista.")
            return
        idx = s[0]
        p = next(x for x in self.est["pendientes"] if x.get("id") == idx)
        f = filedialog.askopenfilename(title="Foto para: " + (p["pedir"] or idx), filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if f:
            try:
                dest = self.P.guardar_foto_visual(self.actual, p["bloque"], idx, f)
            except Exception as ex:
                messagebox.showerror("StudioFX", str(ex)); return
            self.t_falta.set(idx, "estado", "✔ lista")
            self.escribe("Foto agregada: %s\n" % dest)
            self.estado.config(text="Foto agregada. Pulsa «Armar proyecto» para que se use.")

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

    def revisar(self):
        if not self.actual:
            return
        from studiofx.revisor import Revisor
        Revisor(self, self.actual, os.path.join(self.actual, "STUDIOFX"), lambda: self.lanzar(["importar"]))

    def lanzar(self, pasos):
        if self.ocupado or not self.actual:
            if not self.actual:
                messagebox.showinfo("StudioFX", "Primero elige o crea un proyecto.")
            return
        if self.est and not self.est.get("guion") and "sincronizar" in pasos + ["importar"]:
            messagebox.showwarning("StudioFX", "Al proyecto le falta el guion JSON (usa «Agregar guion JSON» en la pestaña Resumen).")
            return
        self.guardar()
        self.ocupado = True
        for b in self.botones:
            b.state(["disabled"])
        self.barra.config(value=0)
        self.nb.select(self.nb.tabs()[-1])
        threading.Thread(target=self.correr, args=(pasos,), daemon=True).start()

    def todo(self):
        self.lanzar(["sincronizar", "importar", "render"])

    def preguntar_faltantes(self, vis):
        """Pausa antes de renderizar si hay visuales que piden una foto especifica."""
        ev = threading.Event(); resp = {}
        def dialogo():
            txt = "Estos visuales piden una foto específica:\n\n" + "\n".join(
                "  •  min %d:%02d  %s" % (int(p["t"]) // 60, int(p["t"]) % 60, (p["pedir"] or p["efecto"])[:70]) for p in vis[:8])
            if len(vis) > 8:
                txt += "\n  ... y %d más" % (len(vis) - 8)
            txt += "\n\n¿Renderizar así (usará la versión sin imagen) o prefieres agregarlas primero?"
            resp["seguir"] = messagebox.askyesno("StudioFX - faltan imágenes", txt + "\n\nSí = renderizar así\nNo = agregar fotos primero", parent=self)
            ev.set()
        self.after(0, dialogo); ev.wait()
        return resp["seguir"]

    def correr(self, pasos):
        try:
            r = self.actual
            modo = self.modo.get()
            res = "1920x1080" if modo.startswith("Final") else "1280x720"
            hasta = ["--hasta", "120"] if "2 min" in modo else []
            sd = os.path.join(r, "STUDIOFX")
            proyecto = os.path.join(sd, "proyecto_fx.json")
            final = os.path.join(sd, "video_final.mp4" if not hasta and res == "1920x1080" else ("borrador_2min.mp4" if hasta else "borrador.mp4"))
            nombres = {"sincronizar": "Sincronizando audio con el guion...", "importar": "Armando la línea de tiempo...", "render": "Renderizando..."}
            for p in pasos:
                self.after(0, lambda p=p: self.estado.config(text=nombres[p]))
                if p == "sincronizar":
                    args = ["sincronizar", r]
                    if importlib.util.find_spec("faster_whisper") is None:
                        args.append("--estimar")
                        self.after(0, lambda: self.escribe("(faster-whisper no está instalado: tiempos aproximados por pausas)\n"))
                    rc = self.cli(args)
                elif p == "importar":
                    rc = self.cli(["importar", r, "--res", res, "--tema", self.tema.get()] + hasta + (["--con-videos"] if self.con_videos.get() else []))
                else:
                    try:
                        vis = [x for x in json.load(open(os.path.join(sd, "pendientes.json"), encoding="utf-8")) if x["tipo"] in ("visual", "foto")]
                    except Exception:
                        vis = []
                    if vis and len(pasos) > 1 and not self.preguntar_faltantes(vis):
                        self.after(0, lambda: (self.recargar(), self.nb.select(self.t2),
                                               self.estado.config(text="Agrega las fotos que faltan y pulsa HACER TODO otra vez.")))
                        return
                    rc = self.cli(["render", proyecto, "-o", final] + hasta)
                if rc != 0:
                    self.after(0, lambda: self.estado.config(text="Hubo un error; revisa el registro."))
                    return
            self.after(0, lambda: (self.barra.config(value=100), self.estado.config(text="¡Listo! " + (final if "render" in pasos else "Hecho."))))
            if "render" in pasos:
                self.after(0, lambda: abrir_en_so(sd))
        finally:
            self.ocupado = False
            def fin():
                for b in self.botones:
                    b.state(["!disabled"])
                self.recargar()
            self.after(0, fin)


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
