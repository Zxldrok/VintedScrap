"""
scraper.py — Module de scraping pour Vinted
Utilise l'API publique non-officielle de Vinted France.
"""

import requests
import json
from typing import Optional


# ─── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://www.vinted.fr"
API_URL  = f"{BASE_URL}/api/v2/catalog/items"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer":         BASE_URL,
    "Origin":          BASE_URL,
}


# ─── Session & Cookie ──────────────────────────────────────────────────────────

def _get_session() -> requests.Session:
    """
    Crée une session avec les cookies nécessaires en visitant d'abord
    la page d'accueil de Vinted (requis pour obtenir le cookie CSRF).
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get(BASE_URL, timeout=10)
    except requests.RequestException:
        pass  # On continue même si la page d'accueil échoue
    return session



# ─── Modèle de données ─────────────────────────────────────────────────────────

# Mapping status Vinted → libellé lisible (par id entier)
_CONDITIONS_BY_ID = {
    6: "Neuf avec étiquette",
    4: "Neuf sans étiquette",
    1: "Très bon état",
    2: "Bon état",
    3: "Satisfaisant",
}
# Mapping status Vinted → libellé (par texte, pour les API qui renvoient une string)
_CONDITIONS_BY_STR = {v.lower(): v for v in _CONDITIONS_BY_ID.values()}
# Condition id normalisé par texte
_CONDITION_ID_BY_STR = {
    "neuf avec étiquette": 6,
    "neuf sans étiquette": 4,
    "très bon état":        1,
    "bon état":             2,
    "satisfaisant":         3,
}

class Annonce:
    """Représente une annonce Vinted."""

    def __init__(self, data: dict):
        self.id           = data.get("id", "")
        self.title        = data.get("title", "Sans titre")
        self.price        = self._parse_price(data)
        self.currency     = self._parse_currency(data)
        self.url          = self._parse_url(data)
        self.image_url    = self._parse_image(data)
        self.size         = data.get("size_title", "")
        self.brand        = data.get("brand_title", "")
        self.condition_id = self._parse_condition_id(data)
        self.condition    = _CONDITIONS_BY_ID.get(self.condition_id, "")
        self.description  = data.get("description", "")   # vide si non fourni par l'API liste

    def _parse_condition_id(self, data: dict) -> int:
        """Extrait l'id de condition — l'API peut renvoyer un int OU une string."""
        raw = data.get("status", 0)
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            # Essai conversion numérique directe ("1", "4"…)
            try:
                return int(raw)
            except ValueError:
                pass
            # Sinon recherche par libellé
            return _CONDITION_ID_BY_STR.get(raw.lower().strip(), 0)
        return 0

    def _parse_price(self, data: dict) -> float:
        """Extrait et convertit le prix en float.

        L'API Vinted peut retourner le prix sous deux formes :
          - un objet : {"amount": "15.00", "currency_code": "EUR"}
          - une valeur simple (str ou float) : "15.00" / 15.0
        On gère aussi le champ de secours "price_numeric".
        """
        try:
            price = data.get("price", 0)
            if isinstance(price, dict):
                # Format objet — ex : {"amount": "15.00", ...}
                return float(price.get("amount", 0))
            if price:
                return float(price)
            # Fallback sur price_numeric si présent
            return float(data.get("price_numeric", 0))
        except (ValueError, TypeError):
            return 0.0

    def _parse_currency(self, data: dict) -> str:
        """Extrait la devise depuis l'objet price ou la racine."""
        price = data.get("price", {})
        if isinstance(price, dict):
            return price.get("currency_code", "EUR")
        return data.get("currency", "EUR")

    def _parse_url(self, data: dict) -> str:
        """Construit l'URL de l'annonce de façon robuste.

        L'API peut retourner dans 'url' :
          - Une URL complète  : "https://www.vinted.fr/items/123-titre"
          - Un chemin absolu  : "/items/123-titre"
          - Un slug seul      : "123-titre"
          - Rien du tout      : "" / None
        """
        raw = data.get("url", "") or ""
        if raw.startswith("http"):
            return raw
        if raw.startswith("/"):
            return f"{BASE_URL}{raw}"
        if raw:
            return f"{BASE_URL}/items/{raw}"
        # Fallback minimaliste avec l'id seul
        return f"{BASE_URL}/items/{self.id}"

    def _parse_image(self, data: dict) -> Optional[str]:
        """Extrait l'URL de la première image."""
        photos = data.get("photos", [])
        if photos:
            # On préfère la version 'full_size' ou à défaut 'url'
            p = photos[0]
            return p.get("full_size_url") or p.get("url") or p.get("src", "")
        return None

    def prix_affiche(self) -> str:
        """Retourne le prix formaté avec symbole monétaire."""
        symboles = {"EUR": "€", "GBP": "£", "USD": "$"}
        sym = symboles.get(self.currency, self.currency)
        return f"{self.price:.2f} {sym}"

    def __repr__(self):
        return f"<Annonce '{self.title}' — {self.prix_affiche()}>"



# ─── Fonctions principales ─────────────────────────────────────────────────────

MAX_PAGES = 5   # Nombre de pages maximum à parcourir par recherche


def rechercher(
    mots_cles: str,
    prix_min: Optional[float] = None,
    prix_max: Optional[float] = None,
    par_page: int = 96,
) -> tuple[list, int]:
    """
    Lance une recherche paginée sur Vinted (jusqu'à MAX_PAGES pages).
    S'arrête dès qu'une page est vide ou que le quota est atteint.

    Returns:
        (list[Annonce] filtrées, int total_brut)

    Raises:
        ConnectionError : Problème réseau
        ValueError      : Réponse inattendue de l'API
    """
    if not mots_cles.strip():
        raise ValueError("Les mots-clés ne peuvent pas être vides.")

    query   = mots_cles.strip().lower()
    session = _get_session()

    tous_items: list[dict] = []

    for page in range(1, MAX_PAGES + 1):
        params: dict = {
            "search_text": query,
            "per_page":    par_page,
            "page":        page,
            "order":       "newest_first",
        }
        if prix_min is not None:
            params["price_from"] = prix_min
        if prix_max is not None:
            params["price_to"]   = prix_max

        try:
            response = session.get(API_URL, params=params, timeout=15)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Impossible de se connecter à Vinted. Vérifiez votre connexion Internet.")
        except requests.exceptions.Timeout:
            raise ConnectionError("La requête a expiré. Réessayez dans quelques instants.")
        except requests.exceptions.HTTPError as e:
            raise ConnectionError(f"Erreur HTTP {e.response.status_code} : {e}")

        try:
            data = response.json()
        except json.JSONDecodeError:
            raise ValueError("La réponse de Vinted n'est pas un JSON valide. L'API a peut-être changé.")

        items = data.get("items", [])
        if not items:
            break  # Plus de résultats, on arrête
        tous_items.extend(items)
        # Si la page est incomplète, c'est la dernière
        if len(items) < par_page:
            break

    if not tous_items:
        return [], 0

    annonces   = [Annonce(item) for item in tous_items]
    total_brut = len(annonces)
    annonces   = _filtrer_tous_mots(annonces, mots_cles)
    return annonces, total_brut


def _normaliser(texte: str) -> str:
    """
    Normalise une chaîne pour comparaison souple :
      - minuscules
      - suppression des accents (é→e, ü→u…)
      - suppression des séparateurs courants (-, _, ., espace)
        → "OP-12", "OP 12", "op12", "Op.12" donnent tous "op12"
    """
    import unicodedata, re
    texte = texte.lower()
    # Décompose les caractères accentués puis supprime les diacritiques
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    # Supprime les séparateurs courants pour fusionner les variantes
    texte = re.sub(r"[-_.\s]+", "", texte)
    return texte


def _filtrer_tous_mots(annonces: list, mots_cles: str) -> list:
    """
    Ne conserve que les annonces dont le titre contient TOUS les tokens
    de la recherche, après normalisation complète.

    Exemples :
      "op12 display"  → titre doit contenir "op12" ET "display"
      "OP-12 Display" → identique au cas ci-dessus
      "op 12 display" → identique (l'espace dans "op 12" est absorbé → "op12")
    """
    # On normalise chaque mot de la requête séparément
    mots = [_normaliser(m) for m in mots_cles.split() if m.strip()]
    if not mots:
        return annonces

    resultat = []
    for a in annonces:
        titre_norm = _normaliser(a.title)
        if all(mot in titre_norm for mot in mots):
            resultat.append(a)
    return resultat


def rechercher_multi(
    mots_cles: str,
    prix_min: Optional[float] = None,
    prix_max: Optional[float] = None,
    par_page: int = 96,
) -> tuple[list, int]:
    """
    Recherche sur plusieurs mots-clés séparés par des virgules.
    Returns (annonces_filtrées, total_brut).
    """
    import concurrent.futures

    termes = [t.strip() for t in mots_cles.split(",") if t.strip()]
    if not termes:
        raise ValueError("Les mots-clés ne peuvent pas être vides.")

    if len(termes) == 1:
        return rechercher(termes[0], prix_min, prix_max, par_page)

    resultats: list = []
    vus: set = set()
    total_brut = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(termes)) as executor:
        futures = {
            executor.submit(rechercher, terme, prix_min, prix_max, par_page): terme
            for terme in termes
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                annonces, brut = future.result()
                total_brut += brut
                for a in annonces:
                    if a.id not in vus:
                        vus.add(a.id)
                        resultats.append(a)
            except Exception:
                pass

    return resultats, total_brut


def fetch_description(annonce_id, annonce_url: str = "") -> str:
    """
    Récupère la description d'une annonce.
    L'API JSON /items/{id} est bloquée par Vinted, on parse donc la page HTML
    et on extrait la balise <meta name="description" content="...">.
    """
    import re
    url = annonce_url or f"{BASE_URL}/items/{annonce_id}"
    try:
        session = _get_session()
        r = session.get(url, timeout=12)
        r.raise_for_status()
        # Extraction via meta description (contient le texte complet du vendeur)
        m = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            r.text, re.IGNORECASE
        )
        if not m:
            # Ordre alternatif des attributs
            m = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
                r.text, re.IGNORECASE
            )
        if m:
            return m.group(1).strip()
        return ""
    except Exception:
        return ""


def trier(annonces: list[Annonce], ordre: str = "prix_asc") -> list[Annonce]:
    """
    Trie une liste d'annonces.

    Args:
        annonces : Liste à trier
        ordre    : "prix_asc"  → du moins cher au plus cher
                   "prix_desc" → du plus cher au moins cher

    Returns:
        Nouvelle liste triée (l'originale n'est pas modifiée)
    """
    reverse = (ordre == "prix_desc")
    return sorted(annonces, key=lambda a: a.price, reverse=reverse)
