"""
data.py — Persistance locale : favoris et recherches sauvegardées.
Les données sont stockées dans des fichiers JSON à côté des scripts.
"""

import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
FAVORIS_FILE    = os.path.join(_DIR, "favoris.json")
RECHERCHES_FILE = os.path.join(_DIR, "recherches.json")
HISTORIQUE_FILE = os.path.join(_DIR, "historique.json")


def _load(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def _save(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Favoris ──────────────────────────────────────────────────────────────────

def charger_favoris() -> list[dict]:
    return _load(FAVORIS_FILE)

def est_favori(id_) -> bool:
    return any(str(f["id"]) == str(id_) for f in charger_favoris())

def toggle_favori(annonce) -> bool:
    """Ajoute ou retire un favori. Retourne True si ajouté, False si retiré."""
    favs = charger_favoris()
    id_  = str(annonce.id)
    if any(f["id"] == id_ for f in favs):
        favs = [f for f in favs if f["id"] != id_]
        _save(FAVORIS_FILE, favs)
        return False
    favs.append({
        "id":        id_,
        "title":     annonce.title,
        "price":     annonce.price,
        "currency":  annonce.currency,
        "url":       annonce.url,
        "image_url": annonce.image_url,
        "brand":     annonce.brand,
        "size":      annonce.size,
    })
    _save(FAVORIS_FILE, favs)
    return True

def supprimer_favori(id_):
    favs = [f for f in charger_favoris() if str(f["id"]) != str(id_)]
    _save(FAVORIS_FILE, favs)


# ─── Recherches sauvegardées ───────────────────────────────────────────────────

def charger_recherches() -> list[dict]:
    return _load(RECHERCHES_FILE)

def sauvegarder_recherche(nom: str, mots_cles: str, prix_min, prix_max):
    recherches = charger_recherches()
    for r in recherches:
        if r["nom"] == nom:
            r.update({"mots_cles": mots_cles, "prix_min": prix_min, "prix_max": prix_max})
            _save(RECHERCHES_FILE, recherches)
            return
    recherches.append({"nom": nom, "mots_cles": mots_cles,
                        "prix_min": prix_min, "prix_max": prix_max})
    _save(RECHERCHES_FILE, recherches)

def supprimer_recherche(nom: str):
    recherches = [r for r in charger_recherches() if r["nom"] != nom]
    _save(RECHERCHES_FILE, recherches)


# ─── Historique des prix ───────────────────────────────────────────────────────

def enregistrer_historique(annonces: list):
    """Snapshot des prix de toutes les annonces en cours. Appelé à chaque recherche."""
    import datetime
    histo = _load(HISTORIQUE_FILE)
    if not isinstance(histo, dict):
        histo = {}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    for a in annonces:
        id_ = str(a.id)
        pts = histo.setdefault(id_, [])
        # N'enregistre que si le prix a changé (ou premier point)
        if not pts or pts[-1]["price"] != a.price:
            pts.append({"date": now, "price": a.price, "title": a.title})
        # Garde au max 60 points par annonce
        if len(pts) > 60:
            histo[id_] = pts[-60:]
    _save(HISTORIQUE_FILE, histo)

def charger_historique(id_: str) -> list:
    """Retourne la liste [{date, price, title}, ...] pour une annonce."""
    histo = _load(HISTORIQUE_FILE)
    if not isinstance(histo, dict):
        return []
    return histo.get(str(id_), [])
