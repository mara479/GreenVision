import os #cai/fisiere/foldere, join, exists, dirname, etc.
import json # citire/scriere fisiere .json (liste/dict-uri)
import random #alegeri random (quiz random, nickname random)
import sqlite3 #baza de date locala (fisier .db) fara server, SQL direct din Python
import datetime as dt #data/ora curenta
import webbrowser #deschide browserul implicit (ex: map.html)
import customtkinter as ctk #UI modern cu Tkinter
import tkinter.messagebox as mb #mesaje pop-up (Tkinter) (yes/no, warning, info)
from PIL import Image, ImageTk #manipulare(lucrat cu ) imagini(Pillow) & pt afisare in Tkinter(ImageTk)
from functools import partial #intr-un fel lipeste param intr-o functie ex util pt butoane
# ML (local) - predictor reciclare
from ml_model import load_or_train, predict_proba


try:
    import matplotlib #librarie de grafice (fol pt acele bare de la statistici)
    matplotlib.use("TkAgg") #pentru a merge graficele in Tkinter
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg #pune figura matplotlib in Tkinter
    MPL = True
except Exception:
    #daca nu e instalat sau nu merge aplicatia doar dezactiveaza graficele
    MPL = False

try:
    import folium #harta interactiva (html)
    FOLIUM_OK = True
except Exception:
    #daca lipseste ,harta iti spune sa dai pip install folium
    FOLIUM_OK = False

APP_TITLE = "GreenVision"
DB_PATH = "greenvision.db"
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MAP_HTML = os.path.join(BASE_DIR, "map.html")
COLLECT_JSON = os.path.join(BASE_DIR, "collect_points.json")
#print("CWD (de unde ruleaza):", os.getcwd())

#print("DB absolute path:", os.path.abspath(DB_PATH))


FONT_TITLE = ("Segoe UI", 26, "bold")
FONT_SUB   = ("Segoe UI", 20, "bold")
FONT_BODY  = ("Segoe UI", 16)
FONT_BODY_B= ("Segoe UI", 16, "bold")
TEXT_DARK  = "#1B4332"  


class DB:
# param: none
# constructor, seteaza calea db-ului si initializeaza tabelele daca nu exista
    def __init__(self):
        self.path = DB_PATH
        self._init_db()
# returneaza un connection sqlite catre fisierul db (folosit cu "with")
    def _conn(self):
        return sqlite3.connect(self.path)
#creeaza tabelele necesare (stats, recycle, quiz, reviews) + seed pt stats (id=1)
    def _init_db(self):
        with self._conn() as con:
            con.execute("CREATE TABLE IF NOT EXISTS stats(id INTEGER PRIMARY KEY CHECK (id=1), stars INTEGER DEFAULT 0)")
            con.execute("INSERT OR IGNORE INTO stats(id, stars) VALUES (1, 0)")
            con.execute("CREATE TABLE IF NOT EXISTS recycle(category TEXT, created_at TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS quiz(score INT, total INT, created_at TEXT)")
            con.execute("""
                CREATE TABLE IF NOT EXISTS reviews(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nickname TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                    comment TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

# param: n=1 (int)->cate stelute adauga
#  creste numarul de stelute din stats (id=1)
    def add_star(self, n=1):
        with self._conn() as con:
            con.execute("UPDATE stats SET stars = stars + ? WHERE id=1", (n,))
# param: none
# citeste cate stelute ai strans pana acum (fallback 0 daca nu gaseste randul)
    def get_stars(self):
        with self._conn() as con:
            row = con.execute("SELECT stars FROM stats WHERE id=1").fetchone()
            return row[0] if row else 0

# param: cat (str)->categoria reciclata (ex: "Plastic")
# salveaza un log in tabelul recycle cu timestamp
    def log_recycle(self, cat):
        with self._conn() as con:
            con.execute("INSERT INTO recycle VALUES (?, ?)", (cat, dt.datetime.now().isoformat()))

# param: score (int), total (int)
# salveaza un log in tabelul quiz cu scor + total + timestamp
    def log_quiz(self, score, total):
        with self._conn() as con:
            con.execute("INSERT INTO quiz VALUES (?, ?, ?)", (score, total, dt.datetime.now().isoformat()))
    # param: none
    # calculeaza statistici quiz:
    # - best = cel mai mare scor
    # - avg = media procentuala (scor/total)
    # - count = cate quizuri s-au dat
    def quiz_stats(self):
        with self._conn() as con:
            rows = con.execute("SELECT score, total FROM quiz").fetchall()
        if not rows:
            return 0, 0.0, 0
        best = max((s for s, _ in rows))
        avg = sum(s/t for s, t in rows) / len(rows) * 100
        count = len(rows)
        return best, avg, count

# param: nickname (str), rating (int 1..5), comment (str)
#  adauga o recenzie in tabela reviews cu timestamp
    def add_review(self, nickname, rating, comment):
        with self._conn() as con:
            con.execute(
                "INSERT INTO reviews(nickname, rating, comment, created_at) VALUES (?,?,?,?)",
                (nickname, rating, comment, dt.datetime.now().isoformat()),
            )
# param: none
# ia lista de recenzii (cele mai noi primele)
    def get_reviews(self):
        with self._conn() as con:
            return con.execute(
                "SELECT nickname, rating, comment, created_at FROM reviews ORDER BY id DESC"
            ).fetchall()


GUIDE = {
    "Plastic": ("Container galben", ["PET-uri curate", "Doze aluminiu", "Folie curată"], ["Plastic murdar", "Jucării"], "Strivește și clătește înainte de reciclare."),
    "Hârtie": ("Container albastru", ["Ziare, cutii carton", "Caiete"], ["Hârtie cerată", "Șervețele murdare"], "Îndepărtează capsele și pliază cartonul."),
    "Sticlă": ("Container verde", ["Sticle, borcane"], ["Oglinzi, porțelan"], "Clătește sticla și scoate capacele."),
    "Metal": ("Container galben", ["Doze curate", "Conserve"], ["Sprayuri pline"], "Tasează dozele pentru economie de spațiu."),
    "Baterii": ("Puncte colectare speciale", ["Toate tipurile uzate"], ["Nu la menajer!"], "Depune la centre specializate periodic."),
}


IMG_MAP = {
    "Plastic": "10f3ae10-7fdb-44ef-98b6-63421d11a7f2.png",  
    "Metal":   "10f3ae10-7fdb-44ef-98b6-63421d11a7f2.png",  
    "Hârtie":  "albastru.png",                               
    "Sticlă":  "06ed436b-2b05-4dbb-bf7a-32409c66a82b.png",  
    "Baterii": "dc42bea2-657a-427f-8cbf-ac33b19801b5.png",  
}


QUIZ_POOL = [
    ("Unde arunci PET-urile?", ["La containerul galben", "La containerul verde", "La containerul albastru"], 0),
    ("Cum pregătești o doză de aluminiu?", ["O strivești și o clătești", "O arunci plină", "O tai în două"], 0),
    ("Bateriile uzate merg la...", ["Gunoi menajer", "Puncte speciale de colectare", "Containerul galben"], 1),
    ("Cartonul corect pregătit este...", ["Îl pliezi ca să ocupe mai puțin", "Îl uzi ca să se descompună", "Îl arunci cu tot cu plastic"], 0),
    ("Sticla corectă este...", ["Cu capac la sticlă", "Clătită, capac separat", "Oricum"], 1),
    ("Șervețelele murdare...", ["La hârtie", "Nu se reciclează", "La plastic"], 1),
    ("Uleiul alimentar uzat...", ["La chiuvetă", "La puncte dedicate", "La canalizare cu apă fierbinte"], 1),
    ("Becurile economice/LED...", ["La containerul verde", "La puncte speciale", "La menajer"], 1),
    ("Electronicele mici (telefon vechi)...", ["La menajer", "La centre DEEE", "La plastic"], 1),
    ("Ambalaj Tetra Pak...", ["La carton/metal (depinde de oraș)", "La sticlă", "Nu se reciclează deloc"], 0),
    ("Plasticul murdar...", ["Se spală sau NU se reciclează", "Se aruncă la plastic oricum", "Se arde în curte"], 0),
    ("Dozele de aluminiu...", ["Se strivesc", "Se lasă voluminoase", "Se pun la sticlă"], 0),
    ("Capacele metalice de la borcane...", ["La metal/plastic", "La sticlă", "La menajer"], 0),
    ("Bateriile litiu...", ["La puncte speciale", "La plastic", "La sticlă"], 0),
    ("Cutiile de iaurt...", ["Clătite la plastic", "La hârtie", "La menajer obligatoriu"], 0),
    ("Cartonul cerat/lucios...", ["La hârtie mereu", "În general NU se reciclează", "La sticlă"], 1),
    ("Oglinda spartă...", ["La sticlă", "La menajer/alt tip, nu la sticlă", "La carton"], 1),
    ("Sprayurile goale...", ["La metal (dacă sunt goale)", "La menajer", "La hârtie"], 0),
    ("Medicamente expirate...", ["Farmacii/colectare specială", "Menajer", "La plastic"], 0),
    ("Textile uzate...", ["Containere textile/ONG", "La plastic", "La hârtie"], 0),
    ("Pungi curate...", ["La plastic", "La hârtie", "La sticlă"], 0),
    ("Capsule cafea metalice...", ["La metal (curățate)", "La menajer", "La sticlă"], 0),
    ("Sticlele trebuie...", ["Aruncate cu capacul pus", "Clătite și capac separat", "Sparte înainte"], 1),
    ("Cartușe imprimantă...", ["La DEEE / puncte speciale", "La plastic", "La menajer"], 0),
    ("Ambalaje din plastic cu resturi...", ["Se clătesc sau NU se reciclează", "La plastic oricum", "La sticlă"], 0),
]
QUIZ_LENGTH = 8
# ML labels (fara diacritice) -> categories din UI (cu diacritice unde ai in GUIDE)
ML_TO_UI_CAT = {
    "Plastic": "Plastic",
    "Hartie": "Hârtie",
    "Sticla": "Sticlă",
    "Metal": "Metal",
    "Electronice": "Electronice",   # atentie: GUIDE nu are Electronice (doar harta are)
    "Ulei uzat": "Ulei uzat",       # GUIDE nu are Ulei uzat
    "Baterii": "Baterii",
    "Nereciclabil": "Nereciclabil"  # nu exista in GUIDE
}


class SplashScreen(ctk.CTkToplevel):
 # param: master (root app), on_close (functie callback)
# ecran de start (splash) cu mascot + buton care inchide splash-ul si porneste app-ul
    def __init__(self, master, on_close):
        super().__init__(master)
        self.on_close = on_close
        self.geometry("640x420")
        self.title("Bine ai venit la GreenVision!")
        self.configure(fg_color="#F2F7F2")
        self.resizable(False, False)

        mascot = os.path.join(ASSETS_DIR, "144294ed-a719-4caf-b446-6de72ac4e46c.png")
        self.img_label = ctk.CTkLabel(self, text="")
        self.img_label.pack(pady=(30,10))
        if os.path.exists(mascot):
            self._img = Image.open(mascot)
            self._zoom_scale = 0.30
            self.after(40, self._animate_zoom)

        ctk.CTkLabel(self, text="GreenVision", font=FONT_TITLE, text_color=TEXT_DARK).pack(pady=(4,2))
        ctk.CTkLabel(self, text="Ghid inteligent de reciclare", font=FONT_BODY, text_color=TEXT_DARK).pack(pady=(0,8))
        ctk.CTkButton(self, text="🌱 Intră în aplicație", fg_color="#52B788", hover_color="#2D6A4F",
                      corner_radius=14, command=self._close).pack(pady=10)
# param: none
#  animatie zoom-in la imaginea mascot (creste treptat marimea)
    def _animate_zoom(self):
        if self._zoom_scale < 1.0:
            self._zoom_scale += 0.015
            size = max(40, int(260 * self._zoom_scale))
            frame = self._img.resize((size, size), Image.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(frame)
            self.img_label.configure(image=self.tk_img)
            self.after(40, self._animate_zoom)
# param: none
#  inchide splash-ul si apeleaza callback-ul (porneste ecranul principal)
    def _close(self):
        self.destroy()
        self.on_close()


class GreenVision(ctk.CTk):
# param: none
#  fereastra principala a aplicatiei (setup db, tema, splash, etc)
    def __init__(self):
        super().__init__()
        self.db = DB()
        # incarca modelul ML (daca nu exista, il antreneaza din json)
        self.ml_bundle = load_or_train()

        self.title(APP_TITLE)
        self.geometry("1120x740")
        self.configure(fg_color="#F2F7F2")
        ctk.set_default_color_theme("green")
        ctk.set_appearance_mode("light")
        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)

        self.withdraw()
        self.after(300, self._show_splash)
# param: none
#  arata fereastra de splash
    def _show_splash(self):
        SplashScreen(self, self._start_main)
# param: none
# porneste UI-ul principal (header + tabs + update stats)
   # def _start_main(self):
    #    self.deiconify()
     #   self.update(); self.update_idletasks()
      #  self._build_header()
       # self._build_tabs()
        #self._update_stats()
    def _start_main(self):
    # params: none
    # ce face: porneste UI-ul; daca pica ceva, iti arata eroarea in popup
     try:
        self.deiconify()
        self.update(); self.update_idletasks()
        self._build_header()
        self._build_tabs()
        self._update_stats()
     except Exception as e:
        mb.showerror("Eroare la start", repr(e))
        raise

# param: none
# confirmare la iesire (popup yes/no). daca da -> inchide app
    def _confirm_exit(self):
        if mb.askyesno("Ieșire", "Sigur vrei să părăsești aplicația GreenVision?"):
            self.destroy()
# param: none
# adauga 1 steluta (scurtatura pt buton)
    def _add_star(self):
        self.db.add_star(1)
        self._update_stats()
# param: none
#  construieste bara de sus (titlu, stelute, buton iesire)
    def _build_header(self):
        header = ctk.CTkFrame(self, height=92, fg_color="#EAF6EA")
        header.pack(fill="x")

        ctk.CTkLabel(header, text="GreenVision", font=FONT_TITLE, text_color=TEXT_DARK).pack(side="left", padx=16)
        self.star_label = ctk.CTkLabel(header, text="* 0", font=("Segoe UI", 18, "bold"), text_color=TEXT_DARK)
        self.star_label.pack(side="right", padx=14)
        ctk.CTkButton(header, text="🚪 Ieșire", fg_color="#95D5B2", hover_color="#74C69D",
                      corner_radius=16, command=self._confirm_exit).pack(side="right", padx=8)

# param: none
#  creeaza tab-urile (ghid, quiz, statistici, recenzii, harta) si le populeaza
    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self.guide_tab   = self.tabs.add(" Ghid")
        self.quiz_tab    = self.tabs.add(" Quiz")
        self.stats_tab   = self.tabs.add(" Statistici")
        self.reviews_tab = self.tabs.add(" Recenzii")
        self.map_tab     = self.tabs.add(" Harta")
        self.ai_tab      = self.tabs.add(" AI")

        self._build_guide()
        self._build_quiz()
        self._build_stats()
        self._build_reviews()
        self._build_map()
        self._build_ai()
    def _build_ai(self):
      # params: none
      # ce face: construieste tab-ul AI (input text + predict + afisare rezultat)
      frame = ctk.CTkFrame(self.ai_tab, fg_color="#FFFFFF")
      frame.pack(fill="both", expand=True, padx=10, pady=10)

      ctk.CTkLabel(frame, text=" AI Recycle - spune-mi ce arunci",
                 font=FONT_SUB, text_color=TEXT_DARK).pack(pady=(10, 6))

      hint = "Exemple: pet de apa, borcan gem, doza aluminiu, telefon vechi, pizza murdara"
      ctk.CTkLabel(frame, text=hint, font=FONT_BODY, text_color=TEXT_DARK).pack(pady=(0, 10))

      self.ai_entry = ctk.CTkEntry(frame, width=680, height=40, placeholder_text="Scrie aici obiectul...")
      self.ai_entry.pack(pady=8)

      ctk.CTkButton(frame, text="🔎 Analizeaza",
                  fg_color="#74C69D", hover_color="#52B788",
                  corner_radius=16,
                  command=self._ai_predict).pack(pady=8)

      self.ai_result = ctk.CTkLabel(frame, text="", font=FONT_BODY_B, text_color=TEXT_DARK, wraplength=900)
      self.ai_result.pack(pady=(12, 6))

      self.ai_tip = ctk.CTkLabel(frame, text="", font=FONT_BODY, text_color=TEXT_DARK, wraplength=900)
      self.ai_tip.pack(pady=(0, 10))


    def _ai_predict(self):
    # params: none
    # ce face: ia textul userului, ruleaza ML, afiseaza categoria + confidence
      text = self.ai_entry.get().strip()
      if not text:
        mb.showwarning("AI Recycle", "Scrie ceva (ex: 'pet de apa') ca sa pot prezice.")
        return

      label, conf = predict_proba(text, self.ml_bundle)
      ui_cat = ML_TO_UI_CAT.get(label, label)

      pct = int(conf * 100)
      self.ai_result.configure(text=f"Predictie: {ui_cat} (confidence ~ {pct}%)")

    # daca exista in GUIDE, folosim ghidul tau ca raspuns "oficial"
      if ui_cat in GUIDE:
        # reuse: arata info + log + stelute (ai deja logica in _show_info)
        self.ai_tip.configure(text="Am gasit categoria in ghid. Ti-am deschis recomandarea din Ghid.")
        self.tabs.set(" Ghid")
        self._show_info(ui_cat)
        return

    # fallback daca nu exista in GUIDE (Electronice / Ulei uzat / Nereciclabil)
      if ui_cat == "Electronice":
        self.ai_tip.configure(text="Tip: du-le la centre DEEE (electronice). In harta ai filtru 'Electronice'.")
      elif ui_cat == "Ulei uzat":
        self.ai_tip.configure(text="Tip: uleiul uzat se duce la puncte dedicate (nu in chiuveta). In harta ai filtru 'Ulei uzat'.")
      elif ui_cat == "Nereciclabil":
        self.ai_tip.configure(text="Tip: pare nereciclabil (murdar / amestecat). Daca e murdar, ori il cureti ori il dai la menajer.")
      else:
        self.ai_tip.configure(text="Nu am regula in ghid pentru asta, dar poti incerca sa reformulezi (ex: 'doza aluminiu').")

    # bonus: ii dam o steluta daca foloseste AI-ul (optional, dar e fun)
      self.db.add_star(1)
      self._update_stats()

# param: none
# UI pt ghid (lista categorii stanga + info si imagine dreapta)
    def _build_guide(self):
        frame = ctk.CTkFrame(self.guide_tab, fg_color="#FFFFFF")
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        left = ctk.CTkFrame(frame, fg_color="#E9F5E9")
        left.pack(side="left", fill="y", padx=10, pady=10)

        right = ctk.CTkFrame(frame, fg_color="#FFFFFF")
        right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(left, text="Alege materialul:", font=FONT_BODY_B, text_color=TEXT_DARK).pack(pady=10)
        for cat in GUIDE:
            ctk.CTkButton(left, text=cat, fg_color="#52B788", hover_color="#40916C",
                          corner_radius=16, command=lambda c=cat: self._show_info(c)).pack(pady=6, fill="x")

        self.info_label = ctk.CTkLabel(right, text="Selectează o categorie pentru recomandări.",
                                       font=FONT_BODY, text_color=TEXT_DARK, wraplength=760)
        self.info_label.pack(pady=(4,10))

        self.img_shadow = ctk.CTkFrame(right, fg_color="#D8F3DC", corner_radius=20)
        self.img_label = ctk.CTkLabel(self.img_shadow, text="")
        self.img_label.pack(padx=6, pady=6)
        self.img_shadow.pack(pady=8)

        self.star_btn = ctk.CTkButton(right, text="* Am reciclat corect!", fg_color="#95D5B2",
                                      hover_color="#74C69D", corner_radius=16, command=self._add_star)
        self.star_btn.pack(pady=8)
 # param: cat (str) -> categoria selectata
# afiseaza informatia din GUIDE pt categoria aleasa, arata imagine, log in db, adauga stelute
    def _show_info(self, cat):
        data = GUIDE[cat]
        self.info_label.configure(text=(f"{cat}\nContainer: {data[0]}\n\n"
                                        f" Reciclabil: {', '.join(data[1])}\n"
                                        f" Nu se reciclează: {', '.join(data[2])}\n"
                                        f" Sfaturi: {data[3]}"),
                                  text_color=TEXT_DARK)

        img_path = os.path.join(ASSETS_DIR, IMG_MAP[cat])
        if os.path.exists(img_path):
            self._animate_container(img_path)

        self.db.log_recycle(cat)
        self.db.add_star(1)
        self._update_stats()
# param: path (str) -> calea catre imagine
#  face un mic "efect" pe imagine: apare mare, apoi se micsoreaza si se aseaza sub text
    def _animate_container(self, path):
        img = Image.open(path)
        big  = ImageTk.PhotoImage(img.resize((420, 420), Image.LANCZOS))
        small= ImageTk.PhotoImage(img.resize((240, 240), Image.LANCZOS))

        self.img_label.configure(image=big)
        self.img_label.image = big
        self.img_shadow.pack_forget()
        self.img_shadow.pack(before=self.info_label, pady=8)

        def shrink_and_place_below():
            self.img_label.configure(image=small)
            self.img_label.image = small
            self.img_shadow.pack_forget()
            self.img_shadow.pack(after=self.info_label, pady=8)

        self.after(500, shrink_and_place_below)
# param: none
#  construieste UI-ul pentru quiz (label intrebare, optiuni, feedback, next)
   
    def _build_quiz(self):
        self.quiz_frame = ctk.CTkFrame(self.quiz_tab, fg_color="#F6FFF2")
        self.quiz_frame.pack(fill="both", expand=True)

        self.q_index = 0
        self.score = 0
        self.current_quiz = self._new_quiz_set()  

        ctk.CTkLabel(self.quiz_frame, text=" Quiz: Reciclare inteligentă",
                     font=FONT_SUB, text_color=TEXT_DARK).pack(pady=(14, 10))

        self.q_label = ctk.CTkLabel(self.quiz_frame, text="", font=FONT_BODY_B,
                                    text_color=TEXT_DARK, wraplength=820, justify="left")
        self.q_label.pack(pady=(8, 4))

        self.feedback = ctk.CTkLabel(self.quiz_frame, text="", font=FONT_BODY, text_color=TEXT_DARK)
        self.feedback.pack(pady=(0, 8))

        self.options_wrap = ctk.CTkFrame(self.quiz_frame, fg_color="#F6FFF2")
        self.options_wrap.pack(pady=6)

        self.next_btn = ctk.CTkButton(self.quiz_frame, text="➡ Următoarea",
                                      fg_color="#74C69D", hover_color="#52B788",
                                      corner_radius=16, state="disabled",
                                      command=self._next_q)
        self.next_btn.pack(pady=10)

        self._load_q()
 # param: none
 # alege random un set de intrebari din QUIZ_POOL (max QUIZ_LENGTH)
   
    def _new_quiz_set(self):
        return random.sample(QUIZ_POOL, k=min(QUIZ_LENGTH, len(QUIZ_POOL)))
# param: options (list[str]), correct_idx (int)
# deseneaza butoanele de raspuns, gestioneaza click-ul (corect/gresit), blocheaza restul
    
    def _render_options(self, options, correct_idx):
        for w in self.options_wrap.winfo_children():
            w.destroy()

        self.option_buttons = []

        def on_pick(opt_idx, btn):
            for b in self.option_buttons:
                b.configure(state="disabled")
            if opt_idx == correct_idx:
                self.score += 1
                self.feedback.configure(text="✔ Corect!", text_color="#1B4332")
                btn.configure(fg_color="#74C69D")
            else:
                self.feedback.configure(text=f"✖ Răspuns corect: {options[correct_idx]}", text_color="#B00020")
                btn.configure(fg_color="#C94F4F")
            self.next_btn.configure(state="normal")

        for i, opt in enumerate(options):
            b = ctk.CTkButton(self.options_wrap, text=opt, width=560, height=44,
                              fg_color="#95D5B2", hover_color="#74C69D",
                              corner_radius=18)
            b.configure(command=partial(on_pick, i, b))
            b.pack(pady=6)
            self.option_buttons.append(b)
# param: none
# incarca intrebarea curenta; daca s-a terminat quiz-ul -> log in db + stelute + ecran rezultat
   
    def _load_q(self):
        if self.q_index >= len(self.current_quiz):
            total = len(self.current_quiz)
            stars_gained = 2 + self.score
            self.db.log_quiz(self.score, total)
            self.db.add_star(stars_gained)
            self._update_stats()
            self._show_result(stars_gained)
            return

        text, options, ans = self.current_quiz[self.q_index]
        self.q_label.configure(text=f"{self.q_index + 1}/{len(self.current_quiz)}  —  {text}")
        self.feedback.configure(text="")
        self.next_btn.configure(state="disabled")
        self._render_options(options, ans)
# param: none
# trece la urmatoarea intrebare
   
    def _next_q(self):
        self.q_index += 1
        self._load_q()
# param: stars_gained (int)
# afiseaza ecran de final quiz (scor + mesaj + butoane restart/ghid)
    
    def _show_result(self, stars_gained):
        for w in self.quiz_frame.winfo_children():
            w.destroy()

        wrap = ctk.CTkFrame(self.quiz_frame, fg_color="#E9F5E9", corner_radius=20)
        wrap.pack(pady=30, padx=30, fill="x")

        pct = int(self.score / QUIZ_LENGTH * 100)
        msg = " Minunat!" if pct >= 80 else (" Bine! Mai exersează puțin." if pct >= 50 else " Hai că poți mai bine data viitoare!")

        ctk.CTkLabel(wrap, text=f" Ai terminat!\nScor: {self.score}/{QUIZ_LENGTH}  ({pct}%)",
                     font=FONT_SUB, text_color=TEXT_DARK, justify="center").pack(padx=20, pady=(20, 6))
        ctk.CTkLabel(wrap, text=msg, font=FONT_BODY, text_color=TEXT_DARK).pack(pady=(0, 6))
        ctk.CTkLabel(wrap, text=f"* Ai câștigat {stars_gained} steluțe!", font=FONT_BODY_B, text_color=TEXT_DARK).pack(pady=(0, 14))

        btns = ctk.CTkFrame(wrap, fg_color="#E9F5E9")
        btns.pack(pady=10)

        ctk.CTkButton(btns, text=" Reia quizul (alte întrebări)",
                      fg_color="#95D5B2", hover_color="#74C69D",
                      corner_radius=16, command=self._restart_quiz).pack(side="left", padx=8)
        ctk.CTkButton(btns, text=" Înapoi la Ghid",
                      fg_color="#B7E4C7", hover_color="#95D5B2",
                      corner_radius=16, command=lambda: self.tabs.set(" Ghid")).pack(side="left", padx=8)
# param: none
# reseteaza quiz-ul (scor/index) + reconstruieste UI-ul (practic refresh complet)
    
    def _restart_quiz(self):
        self.q_index = 0
        self.score = 0
        self.current_quiz = self._new_quiz_set()

        for w in self.quiz_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.quiz_frame, text=" Quiz: Reciclare inteligentă",
                     font=FONT_SUB, text_color=TEXT_DARK).pack(pady=(14, 10))

        self.q_label = ctk.CTkLabel(self.quiz_frame, text="", font=FONT_BODY_B,
                                    text_color=TEXT_DARK, wraplength=820, justify="left")
        self.q_label.pack(pady=(8, 4))

        self.feedback = ctk.CTkLabel(self.quiz_frame, text="", font=FONT_BODY, text_color=TEXT_DARK)
        self.feedback.pack(pady=(0, 8))

        self.options_wrap = ctk.CTkFrame(self.quiz_frame, fg_color="#F6FFF2")
        self.options_wrap.pack(pady=6)

        self.next_btn = ctk.CTkButton(self.quiz_frame, text="➡ Următoarea",
                                      fg_color="#74C69D", hover_color="#52B788",
                                      corner_radius=16, state="disabled",
                                      command=self._next_q)
        self.next_btn.pack(pady=10)

        self._load_q()
# param: none
# construieste UI pentru statistici (kpi + chart holder + buton refresh)
   
    def _build_stats(self):
        self.stats_frame = ctk.CTkFrame(self.stats_tab, fg_color="#F1FFF1")
        self.stats_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.kpi_lbl = ctk.CTkLabel(self.stats_frame, text="", font=FONT_BODY_B, text_color=TEXT_DARK)
        self.kpi_lbl.pack(pady=8)

        self.chart_holder = ctk.CTkFrame(self.stats_frame)
        self.chart_holder.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkButton(self.stats_frame, text=" Reîmprospătează statistici",
                      fg_color="#95D5B2", hover_color="#74C69D",
                      corner_radius=16, command=self._update_stats).pack(pady=6)
# param: none
# actualizeaza stelutele + KPI si (daca exista matplotlib) afiseaza un grafic simplu
   
    def _update_stats(self):
        stars = self.db.get_stars()
        best, avg, count = self.db.quiz_stats()

        if hasattr(self, 'star_label'):
            self.star_label.configure(text=f"* {stars}")
        if hasattr(self, 'kpi_lbl'):
            self.kpi_lbl.configure(text=f"Quizuri: {count} • Cel mai bun: {best}/{QUIZ_LENGTH} • Medie: {avg:.1f}% • Steluțe: {stars}")

        if hasattr(self, 'chart_holder'):
            for w in self.chart_holder.winfo_children():
                w.destroy()
            if MPL and count > 0:
                fig = Figure(figsize=(5.6, 2.6), dpi=100)
                ax = fig.add_subplot(111)
                ax.bar(["Quizuri", "Steluțe"], [count, stars], color="#40916C")
                ax.set_title("Evoluția ta verde", fontsize=10)
                canvas = FigureCanvasTkAgg(fig, master=self.chart_holder)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
            else:
                ctk.CTkLabel(self.chart_holder, text="Nicio statistică încă sau Matplotlib indisponibil.").pack(pady=10)

# param: none
# construieste UI pentru recenzii (rating + textbox + lista scroll)
    
    def _build_reviews(self):
        wrap = ctk.CTkFrame(self.reviews_tab, fg_color="#FFFFFF")
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(wrap, text=" Recenzii & Feedback", font=FONT_SUB, text_color=TEXT_DARK).pack(pady=8)

        form = ctk.CTkFrame(wrap, fg_color="#F6FFF2")
        form.pack(fill="x", padx=8, pady=8)

        self.rating_var = ctk.IntVar(value=5)
        ctk.CTkLabel(form, text="Alege rating:", font=FONT_BODY).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        rate_row = ctk.CTkFrame(form, fg_color="transparent")
        rate_row.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        for i in range(1, 6):
            ctk.CTkRadioButton(rate_row, text="★"*i, variable=self.rating_var, value=i).pack(side="left", padx=4)

        ctk.CTkLabel(form, text="Comentariu:", font=FONT_BODY).grid(row=1, column=0, padx=10, pady=(4,8), sticky="nw")
        self.comment_box = ctk.CTkTextbox(form, height=80)
        self.comment_box.grid(row=1, column=1, padx=6, pady=(4,8), sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(form, text="Trimite recenzia", fg_color="#74C69D", hover_color="#52B788",
                      corner_radius=16, command=self._submit_review).grid(row=2, column=1, padx=6, pady=8, sticky="e")

        self.list_holder = ctk.CTkScrollableFrame(wrap, fg_color="#F8FFF8")
        self.list_holder.pack(fill="both", expand=True, padx=8, pady=8)

        self._refresh_reviews()
 # param: none
#  genereaza un nickname random simpatic (emoji + animal eco)
    
    def _random_nickname(self):
        animals = ["Ecoturtle", "MissRecycle", "GreenFairy", "EcoHero", "PlasticBuster", "LeafLover", "BottleBuddy", "CanCrusher", "GreenBee", "TreeHugger"]
        emojis  = ["*","*)",":)",":0"]
        return f"{random.choice(emojis)} {random.choice(animals)}"
# param: none
# ia rating + text, valideaza, salveaza recenzia in db, reset form, refresh lista, +1 steluta
    
    def _submit_review(self):
        rating = self.rating_var.get()
        comment = self.comment_box.get("1.0", "end").strip()
        if not comment:
            mb.showwarning("Recenzie", "Te rog scrie un scurt comentariu.")
            return
        nick = self._random_nickname()
        self.db.add_review(nick, rating, comment)
        self.comment_box.delete("1.0", "end")
        self.rating_var.set(5)
        self._refresh_reviews()
        self.db.add_star(1)
        self._update_stats()
# param: none
# reincarca lista de recenzii in UI; daca nu exista niciuna, baga una default
    
    def _refresh_reviews(self):
        for w in self.list_holder.winfo_children():
            w.destroy()
        rows = self.db.get_reviews()
        if not rows:
            self.db.add_review(" MissRecycle", 5, "Super utilă și elegantă! Îmi place ghidul pe categorii.")
            rows = self.db.get_reviews()
        for nick, rating, comment, created_at in rows:
            card = ctk.CTkFrame(self.list_holder, fg_color="#FFFFFF", corner_radius=14)
            card.pack(fill="x", expand=True, padx=8, pady=6)
            ctk.CTkLabel(card, text=f"{nick} – {'*'*rating}{'☆'*(5-rating)}",
                         font=FONT_BODY_B, text_color=TEXT_DARK).pack(anchor="w", padx=10, pady=(8,2))
            ctk.CTkLabel(card, text=comment, justify="left", wraplength=900,
                         font=FONT_BODY).pack(anchor="w", padx=10, pady=(0,10))

# param: none
# UI pt harta (filtre + buton reload + buton deschidere browser) si genereaza map.html
       
    def _build_map(self):
        frame = ctk.CTkFrame(self.map_tab, fg_color="#FFFFFF")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text=" Puncte de colectare în Timișoara",
                     font=FONT_SUB, text_color=TEXT_DARK).pack(pady=(10, 6))

       
        filters = ctk.CTkFrame(frame, fg_color="#F6FFF2")
        filters.pack(fill="x", padx=6, pady=(0, 6))

        self.current_filter = ctk.StringVar(value="Toate")

        def make_btn(txt):
            return ctk.CTkButton(filters, text=txt,
                                 fg_color="#95D5B2", hover_color="#74C69D",
                                 corner_radius=14,
                                 command=lambda t=txt: self._set_map_filter(t))

        for txt in ["Toate", "Plastic", "Hârtie", "Sticlă", "Electronice", "Ulei uzat"]:
            b = make_btn(txt)
            b.pack(side="left", padx=6, pady=8)

        ctk.CTkButton(filters, text=" Reîncarcă harta",
                      fg_color="#B7E4C7", hover_color="#95D5B2",
                      corner_radius=14,
                      command=lambda: self._set_map_filter(self.current_filter.get())
                      ).pack(side="right", padx=8, pady=8)

        self.map_status = ctk.CTkLabel(frame, text="Se pregătește harta...",
                                       font=FONT_BODY, text_color=TEXT_DARK)
        self.map_status.pack(pady=(0, 6))

        # Buton pentru deschiderea hartii in browser
        ctk.CTkButton(frame, text=" Deschide harta în browser",
                      fg_color="#74C69D", hover_color="#40916C",
                      corner_radius=16,
                      command=self._load_map_html_safe).pack(pady=10)

        if not FOLIUM_OK:
            self.map_status.configure(
                text=" Modulul folium nu este instalat.\nInstalează-l cu: pip install folium"
            )
            return

        
        self._generate_map(filter_type="Toate")
        self.map_status.configure(text=" Harta este generată. Apasă butonul pentru a o deschide.")
# param: category (str)->filtrul selectat (ex: "Plastic", "Toate")
#seteaza filtrul curent,regenereaza harta si update la status
   
    def _set_map_filter(self, category):
        
        if not FOLIUM_OK:
            self.map_status.configure(text=" folium nu este instalat.")
            return
        self.current_filter.set(category)
        self.map_status.configure(text=f" Se regenerează harta pentru filtrul: {category}...")
        self._generate_map(filter_type=category)
        self.map_status.configure(
            text=f" Harta a fost regenerată pentru filtrul '{category}'. Apasă butonul pentru a o deschide în browser."
        )
# param: none
# deschide map.html in browser-ul implicit (cu protectie try/except)
    
    def _load_map_html_safe(self):
        
        try:
            if os.path.exists(MAP_HTML):
                webbrowser.open(f"file:///{MAP_HTML.replace('\\', '/')}")
                self.map_status.configure(
                    text=f" Harta a fost deschisă în browser (filtru: {self.current_filter.get()})"
                )
            else:
                self.map_status.configure(text=" Fișierul map.html nu există.")
        except Exception as e:
            self.map_status.configure(text=f" Eroare la deschiderea hărții: {e}")
# param: filter_type="Toate" (str)
# citeste punctele din collect_points.json,filtreaza dupa categorie si salveaza map.html cu markere
   
    def _generate_map(self, filter_type="Toate"):
      
        if not FOLIUM_OK:
            return

        try:
            with open(COLLECT_JSON, "r", encoding="utf-8") as f:
                points = json.load(f)
        except Exception:
            points = []

        
        m = folium.Map(location=[45.75, 21.23], zoom_start=13, tiles="OpenStreetMap")

        show_all = (filter_type == "Toate")
        count = 0
        for p in points:
            types = [t.strip() for t in p.get("types", [])]
            if show_all or filter_type in types:
                lat, lon = p["lat"], p["lon"]
                gmaps_url = f"https://www.google.com/maps?q={lat},{lon}"

                html = (
                    f"<b>{p.get('name','')}</b><br/>{', '.join(types)}"
                    f"<br/><a href='{gmaps_url}' "
                    f"style='color:#2D6A4F; text-decoration:none; font-weight:bold;'>"
                    f" Deschide în Google Maps</a>"
                )

                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(html, max_width=280),
                    tooltip=p.get("name", "")
                ).add_to(m)
                count += 1

        if count == 0:
            folium.Marker(
                [45.753, 21.225],
                popup=folium.Popup("<b>Nu s-au găsit puncte pentru filtrul ales.</b><br/>Încearcă 'Toate'.", max_width=260),
                tooltip="Nicio locație pentru acest filtru"
            ).add_to(m)

        m.save(MAP_HTML)


if __name__ == "__main__":
     # param: none
    # porneste aplicatia (creeaza fereastra si intra in loop-ul tkinter)
    app = GreenVision()
    app.mainloop()



