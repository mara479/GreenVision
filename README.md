# GreenVision
Aplicație Descktop Python (CustomTkinter) pentru ghid de reciclare quiz,statisticv, recenzii si harta(Folium+SQLite)
#  oferă:
- **Ghid de reciclare** pe categorii (Plastic / Hârtie / Sticlă / Metal / Baterii)
- **Quiz** educativ cu întrebări random
- **Statistici** (stelute, scoruri quiz)
- **Recenzii** salvate local
- **Hartă interactivă (Folium)** cu puncte de colectare (deschisă în browser)
- **AI Recycle (Machine Learning local)**: introduci un obiect și primești categorie + confidence

> aplicația folosește o bază de date **SQLite locală** (`greenvision.db`) și un model ML local (`recycle_model.pkl`).



##  Structura proiectului

GreenVision/
├── app.py
│ ├─ Interfața grafică principală (CustomTkinter)
│ ├─ Controlul aplicației (tabs, butoane, flux UI)
│ ├─ Integrare bază de date (SQLite – class DB)
│ ├─ Integrare Machine Learning (apel ML local)
│ └─ Generare hartă interactivă (Folium)
│
├── ml_model.py
│ ├─ Logica de Machine Learning
│ ├─ Antrenare model (TF-IDF + Naive Bayes)
│ ├─ Salvare/încărcare model (joblib)
│ └─ Funcții de predicție (predict / predict_proba)
│
├── ml_recycle_data.json
│ └─ Date de antrenare pentru modelul ML
│ (text → categorie de reciclare)
│
├── recycle_model.pkl
│ └─ Model ML antrenat (generat automat la prima rulare)
│
├── collect_points.json
│ └─ Date statice pentru hartă
│ (puncte de colectare + tipuri acceptate)
│
├── map.html
│ └─ Hartă interactivă generată automat cu Folium
│ (Leaflet.js + OpenStreetMap API – rulat în browser)
│
├── greenvision.db
│ └─ Bază de date SQLite locală
│ • stats (steluțe)
│ • recycle (istoric reciclare)
│ • quiz (scoruri)
│ • reviews (recenzii)
│
├── assets/
│ └─ Imagini UI (containere, mascot, iconuri)
│
├── test_map.py
│ └─ Script auxiliar pentru testarea hărții Folium
│
├── .venv/
│ └─ Mediu virtual Python (NU se urcă pe GitHub)
│
├── requirements.txt
│ └─ Dependențe Python necesare proiectului
│
└── README.md
└─ Documentația proiectului


##  Arhitectură logică (pe scurt)

- **UI Layer**: `app.py`  
  Gestionează interfața, evenimentele și afișarea datelor

- **Data Layer**: `greenvision.db` + `class DB`  
  Persistență locală cu SQLite

- **Machine Learning Layer**: `ml_model.py`  
  Clasificare text pentru reciclare (local, fără server)

- **Map Layer**: `collect_points.json` → `map.html`  
  Generare hartă cu Folium, afișare prin browser



##  API-uri utilizate

- **API extern (indirect)**:
  - OpenStreetMap Tiles API (prin Leaflet.js)
- **API intern (local)**:
  - DB API (class DB)
  - ML API local (ml_model.py)

> Aplicația nu folosește un REST API propriu (Flask/FastAPI), ci servicii locale și biblioteci Python.

## Tehnologii utilizate
- Python  
- CustomTkinter (UI)  
- SQLite (persistență date)  
- Folium (hărți interactive)  
- Pillow (procesare imagini)  
- Matplotlib (statistici – opțional)

## Instalare și rulare
1. Clonează repository-ul:
   ```bash
   git clone https://github.com/mara479/GreenVision.git
   cd GreenVision

## Screenshots
![Principal](screenshots/principal.png)
![Ghid](screenshots/ghid.png)
![Statistici](screenshots/statistici.png)
![Review](screenshots/review.png)
![Harta](screenshots/harta1.png)
![Harta](screenshots/harta2.png)
