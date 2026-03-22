"""
main.py — Interface graphique VintedScrap
Fonctionnalités : recherche avancée, favoris, recherches sauvegardées, alertes auto.
"""

import threading, webbrowser, itertools, winsound
from io import BytesIO
from tkinter import messagebox, simpledialog, Menu
import tkinter as tk

import customtkinter as ctk
import requests
from PIL import Image
import win32clipboard

import scraper, data

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

C = {
    "bg":           "#0d1117",
    "sidebar":      "#111827",
    "card":         "#161d2b",
    "card_hover":   "#1e2a3d",
    "border":       "#1f2d40",
    "accent":       "#00c9a7",
    "accent_hover": "#00b090",
    "prix":         "#f0c040",
    "fav":          "#f87171",
    "nouveau":      "#34d399",
    "t1":           "#f0f4f8",
    "t2":           "#8899aa",
    "t3":           "#4a5568",
    "tag_bg":       "#1e3a4a",
    "tag_fg":       "#67d0c0",
    "alerte_on":    "#f6ad55",
}


# ─── Notification banner ──────────────────────────────────────────────────────

class BannerNotif(ctk.CTkToplevel):
    """Petite bannière de notification en bas à droite, disparaît après 6s."""
    def __init__(self, master, titre: str, message: str):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a2333")

        ctk.CTkLabel(self, text=f"🔔  {titre}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C["alerte_on"]).pack(padx=16, pady=(12, 2), anchor="w")
        ctk.CTkLabel(self, text=message,
                     font=ctk.CTkFont(size=11), text_color=C["t2"],
                     wraplength=280).pack(padx=16, pady=(0, 12), anchor="w")

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 310, self.winfo_reqheight()
        self.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 60}")
        self.after(6000, self.destroy)


# ─── Aperçu rapide ────────────────────────────────────────────────────────────

class FenetreApercu(ctk.CTkToplevel):
    """Popup d'aperçu rapide d'une annonce (clic sur l'image)."""
    IMG_W, IMG_H = 360, 360

    def __init__(self, master, annonce: scraper.Annonce):
        super().__init__(master)
        self.title("Aperçu")
        self.resizable(False, False)
        self.configure(fg_color=C["card"])
        self.attributes("-topmost", True)
        self._photo = None
        self._construire(annonce)
        self.update_idletasks()
        # Centrer sur l'écran
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        # Charger l'image + la description en arrière-plan
        if annonce.image_url:
            threading.Thread(target=self._dl_image,
                             args=(annonce.image_url,), daemon=True).start()
        threading.Thread(target=self._dl_description,
                         args=(annonce,), daemon=True).start()

    def _construire(self, a: scraper.Annonce):
        self.grid_columnconfigure(0, weight=1)

        self.lbl_img = ctk.CTkLabel(self, text="…", width=self.IMG_W, height=self.IMG_H,
                                    fg_color="#1a2333", corner_radius=12,
                                    text_color=C["t3"], font=ctk.CTkFont(size=28))
        self.lbl_img.grid(row=0, column=0, padx=20, pady=(20, 12), sticky="ew")

        ctk.CTkLabel(self, text=a.title, font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["t1"], wraplength=360, justify="center"
        ).grid(row=1, column=0, padx=20, pady=(0, 6))

        ctk.CTkLabel(self, text=a.prix_affiche(),
                     font=ctk.CTkFont(size=22, weight="bold"), text_color=C["prix"]
        ).grid(row=2, column=0, pady=(0, 8))

        # Infos : état / marque / taille
        infos = [("État",   a.condition),
                 ("Marque", a.brand),
                 ("Taille", a.size)]
        info_frame = ctk.CTkFrame(self, fg_color="#1a2333", corner_radius=10)
        info_frame.grid(row=3, column=0, padx=20, pady=(0, 12), sticky="ew")
        info_frame.grid_columnconfigure(1, weight=1)
        r = 0
        for label, val in infos:
            if not val: continue
            ctk.CTkLabel(info_frame, text=label, font=ctk.CTkFont(size=11),
                         text_color=C["t3"]).grid(row=r, column=0, padx=12, pady=3, sticky="w")
            ctk.CTkLabel(info_frame, text=val, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C["t1"]).grid(row=r, column=1, padx=12, pady=3, sticky="w")
            r += 1

        ctk.CTkFrame(self, fg_color=C["border"], height=1).grid(
            row=4, column=0, sticky="ew", padx=20, pady=4)

        # Description
        self._slabel_apercu("DESCRIPTION", row=5)
        self.lbl_desc = ctk.CTkLabel(self, text="⏳ Chargement…",
                     font=ctk.CTkFont(size=11), text_color=C["t2"],
                     wraplength=360, justify="left")
        self.lbl_desc.grid(row=6, column=0, padx=20, pady=(0, 8), sticky="w")

        ctk.CTkFrame(self, fg_color=C["border"], height=1).grid(
            row=7, column=0, sticky="ew", padx=20, pady=4)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=8, column=0, padx=20, pady=(4, 20), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(btn_row, text="Voir l'annonce →", height=38, corner_radius=10,
                      fg_color=C["accent"], hover_color=C["accent_hover"], text_color="#000",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=lambda: webbrowser.open(a.url)
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")
        ctk.CTkButton(btn_row, text="✕ Fermer", height=38, corner_radius=10,
                      fg_color=C["border"], hover_color="#2d3a50", text_color=C["t2"],
                      font=ctk.CTkFont(size=13), command=self.destroy
        ).grid(row=0, column=1)

    def _slabel_apercu(self, text, row):
        ctk.CTkLabel(self, text=text, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C["t3"]).grid(row=row, column=0, padx=20, pady=(4, 2), sticky="w")

    def _dl_description(self, annonce: scraper.Annonce):
        desc = annonce.description or scraper.fetch_description(annonce.id, annonce.url)
        if not desc:
            desc = "Aucune description fournie par le vendeur."
        if len(desc) > 500:
            desc = desc[:497] + "…"
        self.after(0, lambda: self.lbl_desc.configure(text=desc))

    def _dl_image(self, url):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).resize(
                (self.IMG_W, self.IMG_H), Image.LANCZOS)
            ci = ctk.CTkImage(light_image=img, dark_image=img,
                              size=(self.IMG_W, self.IMG_H))
            self._photo = ci
            self.after(0, lambda: self.lbl_img.configure(image=ci, text=""))
        except Exception:
            self.after(0, lambda: self.lbl_img.configure(text="✕"))


# ─── Historique des prix ──────────────────────────────────────────────────────

class FenetreHistorique(ctk.CTkToplevel):
    """Graphique d'évolution du prix d'une annonce."""
    W, H   = 560, 340
    PAD_L  = 64    # marge gauche (axe Y)
    PAD_B  = 48    # marge bas   (axe X)
    PAD_T  = 24
    PAD_R  = 24

    def __init__(self, master, annonce_id: str, titre: str):
        super().__init__(master)
        self.title(f"Historique — {titre[:40]}")
        self.resizable(True, True)
        self.configure(fg_color=C["bg"])
        self.attributes("-topmost", True)
        self.geometry(f"{self.W}x{self.H+80}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"📊  Évolution du prix",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["t1"]).grid(row=0, column=0, pady=(16, 4))

        self.canvas = tk.Canvas(self, bg="#0d1117", bd=0, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))

        ctk.CTkButton(self, text="Fermer", height=32, corner_radius=8,
                      fg_color=C["border"], hover_color="#2d3a50", text_color=C["t2"],
                      command=self.destroy).grid(row=2, column=0, pady=(0, 12))

        pts = data.charger_historique(annonce_id)
        self.after(100, lambda: self._dessiner(pts))

    def _dessiner(self, pts: list):
        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width()  or self.W
        ch = self.canvas.winfo_height() or self.H
        self.canvas.delete("all")

        if len(pts) < 2:
            self.canvas.create_text(cw//2, ch//2,
                text="Pas assez de données\n(au moins 2 relevés nécessaires)",
                fill=C["t3"], font=("Segoe UI", 12), justify="center")
            return

        prices = [p["price"] for p in pts]
        dates  = [p["date"]  for p in pts]
        pmin, pmax = min(prices), max(prices)
        if pmin == pmax:
            pmin -= 1; pmax += 1

        gx0 = self.PAD_L
        gx1 = cw - self.PAD_R
        gy0 = self.PAD_T
        gy1 = ch - self.PAD_B
        gw  = gx1 - gx0
        gh  = gy1 - gy0

        def px(i):   return gx0 + i * gw / (len(pts) - 1)
        def py(p):   return gy1 - (p - pmin) / (pmax - pmin) * gh

        # Grille horizontale
        for i in range(5):
            y = gy0 + i * gh / 4
            p = pmax - i * (pmax - pmin) / 4
            self.canvas.create_line(gx0, y, gx1, y, fill="#1f2d40", dash=(4, 4))
            self.canvas.create_text(gx0 - 6, y, text=f"{p:.0f}€",
                                    fill=C["t3"], font=("Segoe UI", 9), anchor="e")

        # Axes
        self.canvas.create_line(gx0, gy0, gx0, gy1, fill=C["border"], width=1)
        self.canvas.create_line(gx0, gy1, gx1, gy1, fill=C["border"], width=1)

        # Dates X (premier + dernier)
        for i, d in [(0, dates[0]), (len(pts)-1, dates[-1])]:
            label = d[5:16] if len(d) >= 16 else d   # "MM-DD HH:MM"
            anchor = "w" if i == 0 else "e"
            self.canvas.create_text(px(i), gy1 + 14, text=label,
                                    fill=C["t3"], font=("Segoe UI", 9), anchor=anchor)

        # Zone remplie sous la courbe
        poly = [gx0, gy1]
        for i, p in enumerate(prices):
            poly += [px(i), py(p)]
        poly += [gx1, gy1]
        self.canvas.create_polygon(poly, fill="#0e3028", outline="")

        # Ligne
        coords = []
        for i, p in enumerate(prices):
            coords += [px(i), py(p)]
        self.canvas.create_line(coords, fill=C["accent"], width=2, smooth=True)

        # Points + tooltips
        for i, p in enumerate(prices):
            x, y = px(i), py(p)
            self.canvas.create_oval(x-4, y-4, x+4, y+4,
                                    fill=C["accent"], outline=C["bg"], width=2)
            if i == 0 or i == len(prices)-1 or p in (pmin, pmax):
                anchor = "sw" if i < len(prices)//2 else "se"
                self.canvas.create_text(x, y - 10, text=f"{p:.2f}€",
                                        fill=C["prix"], font=("Segoe UI", 9, "bold"),
                                        anchor=anchor)


# ─── Carte d'annonce ──────────────────────────────────────────────────────────

class CarteAnnonce(ctk.CTkFrame):
    IMAGE_W = 200
    IMAGE_H = 200

    def __init__(self, parent, annonce: scraper.Annonce, app, nouveau=False, **kwargs):
        border = C["nouveau"] if nouveau else C["border"]
        super().__init__(parent, corner_radius=14, fg_color=C["card"],
                         border_width=1, border_color=border,
                         width=240, height=370,   # taille fixe → pas de reflow au chargement des images
                         **kwargs)
        self.grid_propagate(False)   # empêche les enfants de redimensionner la carte
        self.annonce   = annonce
        self.app       = app
        self._photo    = None   # CTkImage (garde la ref pour tkinter)
        self._pil_img  = None   # PIL Image brut (pour copie clipboard)
        self._construire(nouveau)
        self._charger_image()
        self.bind("<Enter>", lambda _: self.configure(fg_color=C["card_hover"], border_color=C["accent"]))
        self.bind("<Leave>", lambda _: self.configure(fg_color=C["card"], border_color=border))

    def _construire(self, nouveau):
        self.grid_columnconfigure(0, weight=1)

        # Badge NOUVEAU
        if nouveau:
            ctk.CTkLabel(self, text="✦ NOUVEAU", font=ctk.CTkFont(size=10, weight="bold"),
                         text_color="#0d1117", fg_color=C["nouveau"],
                         corner_radius=6, padx=6, pady=2
            ).grid(row=0, column=0, padx=12, pady=(10, 0), sticky="w")

        # Image
        self.lbl_image = ctk.CTkLabel(self, text="…", width=self.IMAGE_W, height=self.IMAGE_H,
                                      fg_color="#1a2333", corner_radius=10,
                                      text_color=C["t3"], font=ctk.CTkFont(size=22))
        self.lbl_image.grid(row=1, column=0, padx=12, pady=(10 if not nouveau else 4, 6), sticky="ew")
        self.lbl_image.bind("<Button-3>", self._menu_image)
        self.lbl_image.bind("<Button-1>", lambda _: FenetreApercu(self.winfo_toplevel(), self.annonce))
        self.lbl_image.configure(cursor="hand2")

        # Titre
        ctk.CTkLabel(self, text=self._trunc(self.annonce.title, 32),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["t1"], wraplength=200, justify="left"
        ).grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")

        # Prix + tags
        row_info = ctk.CTkFrame(self, fg_color="transparent")
        row_info.grid(row=3, column=0, padx=12, pady=(0, 6), sticky="ew")
        row_info.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row_info, text=self.annonce.prix_affiche(),
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=C["prix"]
        ).grid(row=0, column=0, sticky="w")
        tags = [t for t in [self.annonce.brand, self.annonce.size] if t]
        if tags:
            tf = ctk.CTkFrame(row_info, fg_color="transparent")
            tf.grid(row=0, column=1, sticky="e")
            for tag in tags[:2]:
                ctk.CTkLabel(tf, text=tag, font=ctk.CTkFont(size=10),
                             text_color=C["tag_fg"], fg_color=C["tag_bg"],
                             corner_radius=6, padx=6, pady=2).pack(side="left", padx=2)

        # Badge condition
        if self.annonce.condition:
            ctk.CTkLabel(self, text=self.annonce.condition,
                         font=ctk.CTkFont(size=10), text_color=C["tag_fg"],
                         fg_color=C["tag_bg"], corner_radius=6, padx=6, pady=2
            ).grid(row=4, column=0, padx=12, pady=(0, 2), sticky="w")

        # Séparateur
        ctk.CTkFrame(self, fg_color=C["border"], height=1).grid(row=5, column=0, sticky="ew", padx=12, pady=4)

        # Boutons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=6, column=0, padx=12, pady=(2, 12), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(btn_row, text="Voir l'annonce →", height=34, corner_radius=8,
                      fg_color=C["accent"], hover_color=C["accent_hover"],
                      text_color="#000", font=ctk.CTkFont(size=12, weight="bold"),
                      command=lambda: webbrowser.open(self.annonce.url)
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(btn_row, text="📈", width=34, height=34, corner_radius=8,
                      fg_color=C["border"], hover_color="#2d3a50",
                      text_color=C["t2"], font=ctk.CTkFont(size=14),
                      command=lambda: FenetreHistorique(
                          self.winfo_toplevel(), str(self.annonce.id), self.annonce.title)
        ).grid(row=0, column=1, padx=(0, 4), sticky="ew")

        fav_color = C["fav"] if data.est_favori(self.annonce.id) else C["border"]
        self.btn_fav = ctk.CTkButton(btn_row, text="♥", width=34, height=34, corner_radius=8,
                                     fg_color=fav_color, hover_color=C["fav"],
                                     text_color=C["t1"], font=ctk.CTkFont(size=14),
                                     command=self._toggle_fav)
        self.btn_fav.grid(row=0, column=2, sticky="ew")

    def _menu_image(self, event):
        """Affiche le menu contextuel au clic droit sur l'image."""
        menu = Menu(self, tearoff=0,
                    bg="#1a2333", fg="#f0f4f8",
                    activebackground=C["accent"], activeforeground="#000000",
                    font=("Segoe UI", 11), bd=0, relief="flat")
        if self._pil_img:
            menu.add_command(label="📋  Copier l'image",
                             command=self._copier_image)
            menu.add_command(label="💾  Enregistrer l'image…",
                             command=self._enregistrer_image)
            menu.add_separator()
        menu.add_command(label="🔗  Copier le lien de l'annonce",
                         command=self._copier_lien)
        menu.add_command(label="🌐  Ouvrir dans le navigateur",
                         command=lambda: webbrowser.open(self.annonce.url))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copier_image(self):
        """Copie l'image dans le presse-papier Windows (format DIB/BMP)."""
        try:
            buf = BytesIO()
            self._pil_img.save(buf, format="BMP")
            bmp_data = buf.getvalue()[14:]   # On saute le header fichier BMP (14 octets)
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
            win32clipboard.CloseClipboard()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de copier l'image :\n{e}")

    def _enregistrer_image(self):
        """Ouvre une boîte de dialogue pour enregistrer l'image."""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("Tous", "*.*")],
            initialfile=f"{self._trunc(self.annonce.title, 40)}.jpg",
        )
        if path:
            try:
                self._pil_img.save(path)
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible d'enregistrer :\n{e}")

    def _copier_lien(self):
        """Copie l'URL de l'annonce dans le presse-papier."""
        self.clipboard_clear()
        self.clipboard_append(self.annonce.url)

    def _toggle_fav(self):
        ajout = data.toggle_favori(self.annonce)
        self.btn_fav.configure(fg_color=C["fav"] if ajout else C["border"])
        self.app.rafraichir_favoris()

    def _charger_image(self):
        if self.annonce.image_url:
            threading.Thread(target=self._dl_image, daemon=True).start()
        else:
            self.lbl_image.configure(text="📷")

    def _dl_image(self):
        try:
            r = requests.get(self.annonce.image_url, timeout=8)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content))
            self._pil_img = img.convert("RGB")   # sauvegarde l'original pour clipboard
            img_resized = img.resize((self.IMAGE_W, self.IMAGE_H), Image.LANCZOS)
            ci  = ctk.CTkImage(light_image=img_resized, dark_image=img_resized,
                               size=(self.IMAGE_W, self.IMAGE_H))
            self.after(0, lambda: (self.lbl_image.configure(image=ci, text=""),
                                   setattr(self, "_photo", ci)))
        except Exception:
            self.after(0, lambda: self.lbl_image.configure(text="✕"))

    @staticmethod
    def _trunc(s, n): return s if len(s) <= n else s[:n-1] + "…"


# ─── Application principale ───────────────────────────────────────────────────

class AppVinted(ctk.CTk):
    COLONNES = 3

    def __init__(self):
        super().__init__()
        self.title("VintedScrap")
        self.geometry("1300x860")
        self.minsize(1000, 660)
        self.configure(fg_color=C["bg"])

        self._annonces:   list[scraper.Annonce] = []
        self._ordre_tri   = "prix_asc"
        self._etats_actifs: set = set()
        self._anim_job    = None
        self._render_job  = None   # job de rendu par lot en cours
        self._anim_iter   = itertools.cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])
        # Alertes
        self._alerte_active   = False
        self._alerte_job      = None
        self._alerte_ids: set = set()

        self._construire_ui()

    # ══ UI ════════════════════════════════════════════════════════════════════

    def _construire_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._construire_sidebar()
        self._construire_zone_principale()

    @staticmethod
    def _sep(parent, row):
        ctk.CTkFrame(parent, fg_color=C["border"], height=1).grid(
            row=row, column=0, sticky="ew", padx=16, pady=6)

    @staticmethod
    def _slabel(parent, row, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C["t3"]).grid(row=row, column=0, padx=16, pady=(8, 2), sticky="w")

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _construire_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=0, width=290)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(2, weight=1)

        # Logo
        lf = ctk.CTkFrame(sb, fg_color="transparent")
        lf.grid(row=0, column=0, padx=20, pady=(22, 16), sticky="w")
        ctk.CTkLabel(lf, text="VS", font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=C["accent"], fg_color=C["tag_bg"],
                     corner_radius=10, width=46, height=46).pack(side="left", padx=(0,12))
        tc = ctk.CTkFrame(lf, fg_color="transparent")
        tc.pack(side="left")
        ctk.CTkLabel(tc, text="VintedScrap", font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=C["t1"]).pack(anchor="w")
        ctk.CTkLabel(tc, text="Recherche avancée", font=ctk.CTkFont(size=11),
                     text_color=C["t2"]).pack(anchor="w")

        ctk.CTkFrame(sb, fg_color=C["border"], height=1).grid(
            row=1, column=0, sticky="ew", padx=0, pady=0)

        # TabView
        tabs = ctk.CTkTabview(sb, fg_color=C["sidebar"],
                              segmented_button_fg_color=C["bg"],
                              segmented_button_selected_color=C["accent"],
                              segmented_button_selected_hover_color=C["accent_hover"],
                              segmented_button_unselected_color=C["bg"],
                              segmented_button_unselected_hover_color=C["border"],
                              text_color=C["t1"], text_color_disabled=C["t3"])
        tabs.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        tabs.add("🔍 Recherche")
        tabs.add("⭐ Favoris")
        tabs.add("📋 Sauvegardées")

        self._construire_tab_recherche(tabs.tab("🔍 Recherche"))
        self._construire_tab_favoris(tabs.tab("⭐ Favoris"))
        self._construire_tab_sauvegardes(tabs.tab("📋 Sauvegardées"))

        # Stats bas
        self.lbl_stats = ctk.CTkLabel(sb, text="", font=ctk.CTkFont(size=10),
                                      text_color=C["t3"], justify="center")
        self.lbl_stats.grid(row=3, column=0, pady=(4, 14))

    # ── Tab Recherche ──────────────────────────────────────────────────────────

    def _construire_tab_recherche(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        self._slabel(tab, 0, "MOTS-CLÉS")
        self.champ_recherche = ctk.CTkEntry(
            tab, placeholder_text="ex : op12 display, luffy sr...",
            height=40, corner_radius=10, font=ctk.CTkFont(size=13),
            fg_color="#0d1117", border_color=C["accent"], border_width=2, text_color=C["t1"])
        self.champ_recherche.grid(row=1, column=0, padx=16, pady=(4, 2), sticky="ew")
        self.champ_recherche.bind("<Return>", lambda _: self._lancer_recherche())
        ctk.CTkLabel(tab, text="Virgule = plusieurs termes",
                     font=ctk.CTkFont(size=10), text_color=C["t3"]
        ).grid(row=2, column=0, padx=16, pady=(0, 6), sticky="w")

        self._slabel(tab, 3, "PRIX (€)")
        pr = ctk.CTkFrame(tab, fg_color="transparent")
        pr.grid(row=4, column=0, padx=16, pady=(4, 8), sticky="ew")
        pr.grid_columnconfigure((0, 2), weight=1)
        self.champ_prix_min = ctk.CTkEntry(pr, placeholder_text="Min", height=36,
            corner_radius=8, fg_color="#0d1117", border_color=C["border"], text_color=C["t1"])
        self.champ_prix_min.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(pr, text="—", text_color=C["t3"]).grid(row=0, column=1, padx=6)
        self.champ_prix_max = ctk.CTkEntry(pr, placeholder_text="Max", height=36,
            corner_radius=8, fg_color="#0d1117", border_color=C["border"], text_color=C["t1"])
        self.champ_prix_max.grid(row=0, column=2, sticky="ew")

        self._slabel(tab, 5, "TRIER PAR")
        tf = ctk.CTkFrame(tab, fg_color="transparent")
        tf.grid(row=6, column=0, padx=16, pady=(4, 8), sticky="ew")
        tf.grid_columnconfigure((0, 1), weight=1)
        self.btn_tri_asc = ctk.CTkButton(tf, text="Prix ↑", height=34, corner_radius=8,
            fg_color=C["accent"], hover_color=C["accent_hover"], text_color="#000",
            font=ctk.CTkFont(size=12, weight="bold"), command=lambda: self._trier("prix_asc"))
        self.btn_tri_asc.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self.btn_tri_desc = ctk.CTkButton(tf, text="Prix ↓", height=34, corner_radius=8,
            fg_color=C["border"], hover_color="#2d3a50", text_color=C["t2"],
            font=ctk.CTkFont(size=12), command=lambda: self._trier("prix_desc"))
        self.btn_tri_desc.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self._slabel(tab, 7, "ÉTAT")
        etat_frame = ctk.CTkFrame(tab, fg_color="transparent")
        etat_frame.grid(row=8, column=0, padx=16, pady=(4, 4), sticky="ew")
        etat_frame.grid_columnconfigure((0,1,2,3), weight=1)
        self._btns_etat = {}
        etats = [
            ("Neuf",      {4, 6}),
            ("Très bon",  {1}),
            ("Bon",       {2}),
            ("Satisf.",   {3}),
        ]
        for col, (label, ids) in enumerate(etats):
            b = ctk.CTkButton(etat_frame, text=label, height=30, corner_radius=8,
                fg_color=C["border"], hover_color="#2d3a50",
                text_color=C["t2"], font=ctk.CTkFont(size=11),
                command=lambda i=ids, l=label: self._toggle_etat(i, l))
            b.grid(row=0, column=col, padx=2, sticky="ew")
            self._btns_etat[label] = (b, ids)

        self._sep(tab, 9)

        # Boutons action
        self.btn_rechercher = ctk.CTkButton(tab, text="Rechercher", height=44,
            corner_radius=12, fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color="#000", font=ctk.CTkFont(size=14, weight="bold"),
            command=self._lancer_recherche)
        self.btn_rechercher.grid(row=10, column=0, padx=16, pady=(4, 4), sticky="ew")

        ab = ctk.CTkFrame(tab, fg_color="transparent")
        ab.grid(row=11, column=0, padx=16, pady=(0, 4), sticky="ew")
        ab.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(ab, text="↺ Actualiser", height=34, corner_radius=10,
            fg_color="transparent", hover_color=C["border"], text_color=C["t2"],
            border_width=1, border_color=C["border"], font=ctk.CTkFont(size=12),
            command=self._lancer_recherche).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(ab, text="💾 Sauvegarder", height=34, corner_radius=10,
            fg_color="transparent", hover_color=C["border"], text_color=C["t2"],
            border_width=1, border_color=C["border"], font=ctk.CTkFont(size=12),
            command=self._sauvegarder_recherche).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self._sep(tab, 12)

        # Section Alertes
        self._slabel(tab, 13, "ALERTE AUTOMATIQUE")
        al = ctk.CTkFrame(tab, fg_color="transparent")
        al.grid(row=14, column=0, padx=16, pady=(4, 6), sticky="ew")
        al.grid_columnconfigure(0, weight=1)

        self.btn_alerte = ctk.CTkButton(al, text="🔔 Activer l'alerte", height=36,
            corner_radius=10, fg_color=C["border"], hover_color="#2d3a50",
            text_color=C["t2"], font=ctk.CTkFont(size=12),
            command=self._toggle_alerte)
        self.btn_alerte.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        ctk.CTkLabel(al, text="Intervalle :", font=ctk.CTkFont(size=11),
                     text_color=C["t3"]).grid(row=1, column=0, sticky="w")
        self.menu_intervalle = ctk.CTkOptionMenu(al, values=["5 min","10 min","15 min","30 min"],
            fg_color="#0d1117", button_color=C["border"], button_hover_color=C["accent"],
            text_color=C["t1"], font=ctk.CTkFont(size=12))
        self.menu_intervalle.set("10 min")
        self.menu_intervalle.grid(row=1, column=1, sticky="ew", padx=(6, 0))
        al.grid_columnconfigure(1, weight=1)

        self.lbl_alerte_status = ctk.CTkLabel(tab, text="● Inactive",
            font=ctk.CTkFont(size=11), text_color=C["t3"])
        self.lbl_alerte_status.grid(row=15, column=0, padx=16, pady=(0, 8), sticky="w")

    # ── Tab Favoris ────────────────────────────────────────────────────────────

    def _construire_tab_favoris(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        self._tab_favoris = tab
        self.scroll_favoris = ctk.CTkScrollableFrame(tab, fg_color="transparent",
            scrollbar_button_color=C["border"], scrollbar_button_hover_color=C["accent"])
        self.scroll_favoris.grid(row=0, column=0, sticky="nsew")
        self.scroll_favoris.grid_columnconfigure(0, weight=1)
        self.rafraichir_favoris()

    def rafraichir_favoris(self):
        for w in self.scroll_favoris.winfo_children():
            w.destroy()
        favs = data.charger_favoris()
        if not favs:
            ctk.CTkLabel(self.scroll_favoris, text="Aucun favori\npour l'instant.",
                         font=ctk.CTkFont(size=12), text_color=C["t3"],
                         justify="center").pack(pady=40)
            return
        for fav in favs:
            f = ctk.CTkFrame(self.scroll_favoris, fg_color=C["card"],
                             corner_radius=10, border_width=1, border_color=C["border"])
            f.pack(fill="x", padx=8, pady=4)
            f.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(f, text=CarteAnnonce._trunc(fav["title"], 30),
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=C["t1"], wraplength=180, justify="left"
            ).grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")
            prix_sym = {"EUR": "€", "GBP": "£", "USD": "$"}.get(fav.get("currency","EUR"), "€")
            ctk.CTkLabel(f, text=f"{fav['price']:.2f} {prix_sym}",
                         font=ctk.CTkFont(size=13, weight="bold"), text_color=C["prix"]
            ).grid(row=1, column=0, padx=10, pady=(0, 4), sticky="w")
            bf = ctk.CTkFrame(f, fg_color="transparent")
            bf.grid(row=2, column=0, padx=10, pady=(0, 8), sticky="ew")
            bf.grid_columnconfigure(0, weight=1)
            ctk.CTkButton(bf, text="Ouvrir →", height=28, corner_radius=6,
                fg_color=C["accent"], hover_color=C["accent_hover"], text_color="#000",
                font=ctk.CTkFont(size=11), command=lambda u=fav["url"]: webbrowser.open(u)
            ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
            ctk.CTkButton(bf, text="✕", width=28, height=28, corner_radius=6,
                fg_color=C["border"], hover_color=C["fav"], text_color=C["t2"],
                command=lambda i=fav["id"]: (data.supprimer_favori(i), self.rafraichir_favoris())
            ).grid(row=0, column=1)

    # ── Tab Sauvegardées ───────────────────────────────────────────────────────

    def _construire_tab_sauvegardes(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        self.scroll_sauvegardes = ctk.CTkScrollableFrame(tab, fg_color="transparent",
            scrollbar_button_color=C["border"], scrollbar_button_hover_color=C["accent"])
        self.scroll_sauvegardes.grid(row=0, column=0, sticky="nsew")
        self.scroll_sauvegardes.grid_columnconfigure(0, weight=1)
        self._rafraichir_sauvegardes()

    def _rafraichir_sauvegardes(self):
        for w in self.scroll_sauvegardes.winfo_children():
            w.destroy()
        recherches = data.charger_recherches()
        if not recherches:
            ctk.CTkLabel(self.scroll_sauvegardes, text="Aucune recherche\nsauvegardée.",
                         font=ctk.CTkFont(size=12), text_color=C["t3"],
                         justify="center").pack(pady=40)
            return
        for r in recherches:
            f = ctk.CTkFrame(self.scroll_sauvegardes, fg_color=C["card"],
                             corner_radius=10, border_width=1, border_color=C["border"])
            f.pack(fill="x", padx=8, pady=4)
            f.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(f, text=r["nom"], font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=C["accent"]).grid(row=0, column=0, padx=10, pady=(8, 1), sticky="w")
            ctk.CTkLabel(f, text=r["mots_cles"], font=ctk.CTkFont(size=10),
                         text_color=C["t2"], wraplength=180
            ).grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")
            pinfo = ""
            if r.get("prix_min") is not None: pinfo += f"≥{r['prix_min']}€  "
            if r.get("prix_max") is not None: pinfo += f"≤{r['prix_max']}€"
            if pinfo:
                ctk.CTkLabel(f, text=pinfo.strip(), font=ctk.CTkFont(size=10),
                             text_color=C["t3"]).grid(row=2, column=0, padx=10, pady=(0, 4), sticky="w")
            bf = ctk.CTkFrame(f, fg_color="transparent")
            bf.grid(row=3, column=0, padx=10, pady=(0, 8), sticky="ew")
            bf.grid_columnconfigure(0, weight=1)
            ctk.CTkButton(bf, text="▶ Charger", height=28, corner_radius=6,
                fg_color=C["accent"], hover_color=C["accent_hover"], text_color="#000",
                font=ctk.CTkFont(size=11),
                command=lambda rec=r: self._charger_recherche(rec)
            ).grid(row=0, column=0, padx=(0, 4), sticky="ew")
            ctk.CTkButton(bf, text="✕", width=28, height=28, corner_radius=6,
                fg_color=C["border"], hover_color=C["fav"], text_color=C["t2"],
                command=lambda n=r["nom"]: (data.supprimer_recherche(n), self._rafraichir_sauvegardes())
            ).grid(row=0, column=1)

    # ── Zone principale ────────────────────────────────────────────────────────

    def _construire_zone_principale(self):
        main = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        topbar = ctk.CTkFrame(main, fg_color=C["sidebar"], corner_radius=0, height=52)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)
        self.lbl_status = ctk.CTkLabel(topbar, text="Prêt — entrez des mots-clés et lancez une recherche",
            font=ctk.CTkFont(size=12), text_color=C["t2"])
        self.lbl_status.grid(row=0, column=0, padx=20, sticky="w")
        self.lbl_count = ctk.CTkLabel(topbar, text="", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["accent"])
        self.lbl_count.grid(row=0, column=1, padx=20, sticky="e")

        self.zone_scroll = ctk.CTkScrollableFrame(main, fg_color=C["bg"],
            scrollbar_button_color=C["border"], scrollbar_button_hover_color=C["accent"])
        self.zone_scroll.grid(row=1, column=0, sticky="nsew")
        for col in range(self.COLONNES):
            self.zone_scroll.grid_columnconfigure(col, weight=1, uniform="col")

        # Configurer le scroll fluide après que CTk ait fini d'initialiser le canvas
        self.after(200, self._configurer_scroll)

        self.lbl_accueil = ctk.CTkLabel(self.zone_scroll,
            text="🔍\n\nEntrez des mots-clés\ndans la barre de gauche",
            font=ctk.CTkFont(size=18), text_color=C["t3"], justify="center")
        self.lbl_accueil.grid(row=0, column=0, columnspan=self.COLONNES, pady=120)

    # ══ Logique recherche ═════════════════════════════════════════════════════

    def _lire_prix(self, champ):
        v = champ.get().strip().replace(",", ".")
        if not v: return None
        try:
            f = float(v); return f if f >= 0 else None
        except ValueError: return None

    def _lancer_recherche(self, silent=False):
        mots = self.champ_recherche.get().strip()
        if not mots:
            if not silent:
                messagebox.showwarning("Champ vide", "Entrez des mots-clés avant de rechercher.")
            return
        self._set_en_cours(True)
        self._vider_resultats()
        termes = [t.strip() for t in mots.split(",") if t.strip()]
        nb, mp = len(termes), scraper.MAX_PAGES
        self._set_status(f"Recherche de {nb} terme(s) sur {mp} pages…" if nb > 1 else f"Recherche sur {mp} pages…")
        self._demarrer_animation()
        prix_min = self._lire_prix(self.champ_prix_min)
        prix_max = self._lire_prix(self.champ_prix_max)
        threading.Thread(target=self._thread_recherche,
                         args=(mots, prix_min, prix_max, silent), daemon=True).start()

    def _thread_recherche(self, mots, prix_min, prix_max, silent=False):
        try:
            annonces, total = scraper.rechercher_multi(mots, prix_min, prix_max)
            self.after(0, self._afficher_resultats, annonces, total, silent)
        except (ConnectionError, ValueError) as e:
            self.after(0, self._afficher_erreur, str(e))
        except Exception as e:
            self.after(0, self._afficher_erreur, f"Erreur inattendue : {e}")

    def _afficher_resultats(self, annonces, total_brut=0, silent=False):
        self._arreter_animation()
        self._set_en_cours(False)
        filtres = total_brut - len(annonces)

        # Détection nouvelles annonces pour alerte
        nouvelles_ids = set()
        if self._alerte_ids:
            nouvelles_ids = {str(a.id) for a in annonces} - self._alerte_ids
            if nouvelles_ids and silent:
                nb_new = len(nouvelles_ids)
                try:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass
                BannerNotif(self, "Nouvelles annonces !",
                            f"{nb_new} nouvelle(s) annonce(s) trouvée(s).")
        self._alerte_ids = {str(a.id) for a in annonces}
        self._annonces   = annonces

        if not annonces:
            msg = ("0 résultat après filtrage strict\n"
                   f"({total_brut} annonces examinées)\n\nEssayez des termes moins précis."
                   if total_brut > 0 else "Aucun résultat.")
            self._set_status("⚠️  Aucun résultat trouvé.")
            self.lbl_accueil.configure(text=f"😔\n\n{msg}", font=ctk.CTkFont(size=14))
            self.lbl_accueil.grid(row=0, column=0, columnspan=self.COLONNES, pady=100)
            self.lbl_stats.configure(text="")
            return

        self._rendre_cartes(annonces, nouvelles_ids)
        self._set_status("✅  Recherche terminée")
        count = f"{len(annonces)} résultat(s)"
        if filtres > 0: count += f"  •  {filtres} filtrés"
        self.lbl_count.configure(text=count)
        pages = max(1, (total_brut - 1) // 96 + 1)
        self.lbl_stats.configure(text=f"{len(annonces)} annonces  •  {filtres} filtrés  •  {pages} page(s)")
        # Enregistrement historique des prix (en arrière-plan)
        threading.Thread(target=data.enregistrer_historique,
                         args=(annonces,), daemon=True).start()

    def _rendre_cartes(self, annonces, nouvelles_ids=None):
        self._vider_resultats()
        if self._render_job:
            self.after_cancel(self._render_job)
            self._render_job = None

        nouvelles_ids = nouvelles_ids or set()
        affichees     = self._annonces_filtrees(annonces)
        if not affichees:
            return

        # ── Pré-créer TOUTES les cartes d'un coup (rapide, pas d'images encore) ──
        # Les images se chargent de toute façon en arrière-plan via threading.
        # Créer les widgets tkinter est rapide ; c'est le réseau qui est lent.
        # On évite update_idletasks() entre lots pour ne pas forcer de rendu partiel.
        BATCH = self.COLONNES * 2   # 2 lignes par tick = 6 cartes

        def _render_batch(start: int):
            fin = min(start + BATCH, len(affichees))
            for idx in range(start, fin):
                a = affichees[idx]
                ligne, col = divmod(idx, self.COLONNES)
                carte = CarteAnnonce(self.zone_scroll, a, app=self,
                             nouveau=str(a.id) in nouvelles_ids)
                carte.grid(row=ligne, column=col, padx=10, pady=10, sticky="nsew")
                # Binder sur le widget tkinter sous-jacent (pas le wrapper CTk)
                self._bind_scroll_recursif(carte)
            if fin < len(affichees):
                self._render_job = self.after(32, _render_batch, fin)

        _render_batch(0)

    def _annonces_filtrees(self, annonces):
        """Filtre les annonces selon les états actifs (tous si aucun sélectionné)."""
        if not self._etats_actifs:
            return annonces
        return [a for a in annonces if a.condition_id in self._etats_actifs]

    def _toggle_etat(self, ids: set, label: str):
        """Active/désactive un filtre état et re-rend les cartes."""
        b, _ = self._btns_etat[label]
        # Si déjà actif → désactiver
        if ids.issubset(self._etats_actifs):
            self._etats_actifs -= ids
            b.configure(fg_color=C["border"], text_color=C["t2"])
        else:
            self._etats_actifs |= ids
            b.configure(fg_color=C["accent"], text_color="#000")
        if self._annonces:
            self._rendre_cartes(self._annonces)

    def _vider_resultats(self):
        # Stoppe le rendu par lot en cours si besoin
        if self._render_job:
            self.after_cancel(self._render_job)
            self._render_job = None
        for w in self.zone_scroll.winfo_children():
            w.grid_forget(); w.destroy()
        self.lbl_accueil = ctk.CTkLabel(self.zone_scroll, text="",
            font=ctk.CTkFont(size=16), text_color=C["t3"])
        self.lbl_count.configure(text="")

    def _afficher_erreur(self, msg):
        self._arreter_animation()
        self._set_en_cours(False)
        self._set_status(f"❌  {msg}")
        messagebox.showerror("Erreur", msg)

    def _trier(self, ordre):
        if not self._annonces: return
        self._ordre_tri = ordre
        self._rendre_cartes(scraper.trier(self._annonces, ordre))
        self.btn_tri_asc.configure(fg_color=C["accent"] if ordre=="prix_asc" else C["border"],
                                   text_color="#000" if ordre=="prix_asc" else C["t2"])
        self.btn_tri_desc.configure(fg_color=C["accent"] if ordre=="prix_desc" else C["border"],
                                    text_color="#000" if ordre=="prix_desc" else C["t2"])

    # ══ Recherches sauvegardées ═══════════════════════════════════════════════

    def _sauvegarder_recherche(self):
        mots = self.champ_recherche.get().strip()
        if not mots:
            messagebox.showwarning("Champ vide", "Entrez des mots-clés avant de sauvegarder.")
            return
        nom = simpledialog.askstring("Sauvegarder la recherche",
                                     "Nom de la recherche :", parent=self)
        if not nom or not nom.strip():
            return
        data.sauvegarder_recherche(nom.strip(), mots,
                                    self._lire_prix(self.champ_prix_min),
                                    self._lire_prix(self.champ_prix_max))
        self._rafraichir_sauvegardes()
        self._set_status(f"✅  Recherche « {nom.strip()} » sauvegardée.")

    def _charger_recherche(self, rec: dict):
        self.champ_recherche.delete(0, "end")
        self.champ_recherche.insert(0, rec["mots_cles"])
        self.champ_prix_min.delete(0, "end")
        self.champ_prix_max.delete(0, "end")
        if rec.get("prix_min") is not None:
            self.champ_prix_min.insert(0, str(rec["prix_min"]))
        if rec.get("prix_max") is not None:
            self.champ_prix_max.insert(0, str(rec["prix_max"]))
        self._lancer_recherche()

    # ══ Alertes automatiques ══════════════════════════════════════════════════

    def _toggle_alerte(self):
        if self._alerte_active:
            self._arreter_alerte()
        else:
            self._demarrer_alerte()

    def _demarrer_alerte(self):
        mots = self.champ_recherche.get().strip()
        if not mots:
            messagebox.showwarning("Champ vide", "Entrez des mots-clés pour activer l'alerte.")
            return
        self._alerte_active = True
        self._alerte_ids    = set()
        self.btn_alerte.configure(fg_color=C["alerte_on"], text_color="#000",
                                  text="🔔 Alerte active — Arrêter")
        self.lbl_alerte_status.configure(text_color=C["alerte_on"])
        self._lancer_recherche(silent=True)
        self._planifier_prochain_tick()

    def _planifier_prochain_tick(self):
        val = self.menu_intervalle.get().replace(" min", "").strip()
        try:   minutes = int(val)
        except ValueError: minutes = 10
        self.lbl_alerte_status.configure(text=f"● Prochaine vérif. dans {minutes} min")
        self._alerte_job = self.after(minutes * 60_000, self._tick_alerte)

    def _tick_alerte(self):
        if not self._alerte_active: return
        self._lancer_recherche(silent=True)
        self._planifier_prochain_tick()

    def _arreter_alerte(self):
        self._alerte_active = False
        if self._alerte_job:
            self.after_cancel(self._alerte_job)
            self._alerte_job = None
        self.btn_alerte.configure(fg_color=C["border"], text_color=C["t2"],
                                  text="🔔 Activer l'alerte")
        self.lbl_alerte_status.configure(text="● Inactive", text_color=C["t3"])

    # ══ Helpers ═══════════════════════════════════════════════════════════════

    def _set_status(self, txt): self.lbl_status.configure(text=txt)

    def _bind_scroll_recursif(self, widget):
        """
        Binde le scroll fluide sur le widget tkinter SOUS-JACENT et tous ses enfants.
        On passe par ._w (nom interne tkinter) pour éviter le wrapper CTk qui
        interdit add=False.
        """
        try:
            # Récupère le widget tkinter natif sous le wrapper CTk
            tk_widget = widget._w if hasattr(widget, "_w") else widget
            # Binder directement via tkinter (sans passer par CTk)
            self.tk.call("bind", tk_widget, "<MouseWheel>",
                         self.register(self._scroll_fluide))
        except Exception:
            pass
        for child in widget.winfo_children():
            self._bind_scroll_recursif(child)

    def _configurer_scroll(self):
        """Configure le scroll fluide sur le canvas interne de CTkScrollableFrame."""
        try:
            canvas = self.zone_scroll._parent_canvas
            canvas.configure(yscrollincrement=1)
            # Binder via tkinter natif directement sur le canvas
            self.tk.call("bind", canvas._w, "<MouseWheel>",
                         self.register(self._scroll_fluide))
        except Exception:
            pass

    def _scroll_fluide(self, event=None):
        """Scroll fluide ~40px par cran de molette."""
        try:
            canvas = self.zone_scroll._parent_canvas
            delta = getattr(event, "delta", 0)
            canvas.yview_scroll(int(-delta / 3), "units")
        except Exception:
            pass

    def _set_en_cours(self, v):
        self.btn_rechercher.configure(state="disabled" if v else "normal",
                                      text="…" if v else "Rechercher")

    def _demarrer_animation(self):
        def _t():
            self.lbl_count.configure(text=next(self._anim_iter))
            self._anim_job = self.after(80, _t)
        _t()

    def _arreter_animation(self):
        if self._anim_job:
            self.after_cancel(self._anim_job); self._anim_job = None
        self.lbl_count.configure(text="")


if __name__ == "__main__":
    AppVinted().mainloop()
