import os
import json
import joblib # type: ignore

from sklearn.feature_extraction.text import TfidfVectorizer # type: ignore
from sklearn.naive_bayes import MultinomialNB # type: ignore

BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "ml_recycle_data.json")
MODEL_FILE = os.path.join(BASE_DIR, "recycle_model.pkl")


def train_model(data_file=DATA_FILE, model_file=MODEL_FILE):
    # params: data_file (str), model_file (str)
    # ce face: antreneaza modelul (TF-IDF + Naive Bayes) si il salveaza ca .pkl
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = [d["text"].strip().lower() for d in data]
    labels = [d["label"].strip() for d in data]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)

    model = MultinomialNB()
    model.fit(X, labels)

    joblib.dump((model, vectorizer), model_file)


def load_or_train(model_file=MODEL_FILE, data_file=DATA_FILE):
    # params: model_file (str), data_file (str)
    # ce face: incarca modelul daca exista; daca nu, il antreneaza rapid si apoi il incarca
    if not os.path.exists(model_file):
        train_model(data_file=data_file, model_file=model_file)
    return joblib.load(model_file)


def predict(text, model_bundle):
    # params: text (str), model_bundle (tuple(model, vectorizer))
    # ce face: prezice label-ul (categoria) pentru textul userului
    model, vectorizer = model_bundle
    clean = (text or "").strip().lower()
    X = vectorizer.transform([clean])
    return model.predict(X)[0]


def predict_proba(text, model_bundle):
    # params: text (str), model_bundle (tuple(model, vectorizer))
    # ce face: returneaza (label, confidence) daca modelul suporta predict_proba
    model, vectorizer = model_bundle
    clean = (text or "").strip().lower()
    X = vectorizer.transform([clean])

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[0]
        idx = int(proba.argmax())
        return model.classes_[idx], float(proba[idx])
    else:
        # fallback: daca nu are proba, dam 1.0 by default
        return model.predict(X)[0], 1.0
