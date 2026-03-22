# VintedScrap 🛍️

> Application de bureau Python pour rechercher, filtrer et surveiller les annonces Vinted — avec interface graphique moderne.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-teal)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Fonctionnalités

### 🔍 Recherche avancée
- Recherche par mots-clés sur l'API publique de Vinted France
- **Multi-termes** : sépare tes recherches par une virgule (`op12 display, luffy sr`)
- **Filtrage strict** : tous les mots doivent être présents dans le titre (plus de résultats hors-sujet)
- Normalisation intelligente : `OP-12`, `Op 12`, `op12` sont traités identiquement
- **Pagination automatique** : jusqu'à 5 pages (≈480 annonces) par recherche
- Filtre par prix min/max
- Tri dynamique par prix (sans relancer la recherche)
- **Filtre par état** : Neuf / Très bon état / Bon état / Satisfaisant

### 🃏 Affichage
- Grille de cartes 3 colonnes avec chargement progressif
- Image, titre, prix, marque, taille, badge état sur chaque carte
- Badge **✦ NOUVEAU** sur les nouvelles annonces (mode alerte)
- **Aperçu rapide** : clic sur une image → popup avec photo HD, description et infos complètes
- Scroll fluide pixel-par-pixel
- Clic droit sur une image → copier, enregistrer, copier le lien


### 🔔 Alertes automatiques
- Relance la recherche toutes les **5 / 10 / 15 / 30 minutes** en arrière-plan
- Notification Windows + bannière visuelle si de nouvelles annonces apparaissent
- Indicateur du prochain check dans la sidebar

### ⭐ Favoris
- Bouton ♥ sur chaque carte pour épingler une annonce
- Sauvegardé dans `favoris.json` (persistant entre les sessions)
- Onglet dédié dans la sidebar avec accès rapide et suppression

### 📋 Recherches sauvegardées
- Sauvegarde une recherche (mots-clés + filtres prix) sous un nom personnalisé
- Rechargement en un clic depuis l'onglet dédié

### 📊 Historique des prix
- Enregistre automatiquement le prix de chaque annonce à chaque recherche
- Bouton 📈 sur chaque carte pour afficher un graphique d'évolution du prix dans le temps

---

## 📁 Structure du projet

```
VintedScrap/
├── main.py           ← Interface graphique (CustomTkinter)
├── scraper.py        ← Scraping & logique API Vinted
├── data.py           ← Persistance (favoris, recherches, historique)
├── requirements.txt  ← Dépendances Python
├── installer.bat     ← Installation automatique des dépendances
└── lancer.bat        ← Lancer l'application
```

Les fichiers suivants sont générés automatiquement au premier usage (non versionnés) :
- `favoris.json` — annonces mises en favoris
- `recherches.json` — recherches sauvegardées
- `historique.json` — historique des prix

---

## 🚀 Installation

### Prérequis
- **Python 3.10+** → [python.org/downloads](https://www.python.org/downloads/)
- Cocher **"Add Python to PATH"** lors de l'installation
- **Windows uniquement** (utilise `winsound` et `pywin32` pour les notifications et le presse-papier)

### 1. Cloner le dépôt
```bash
git clone https://github.com/Zxldrok/VintedScrap.git
cd VintedScrap
```

### 2. Installer les dépendances
Double-clic sur **`installer.bat`**, ou :
```bash
pip install -r requirements.txt
```

### 3. Lancer l'application
Double-clic sur **`lancer.bat`**, ou :
```bash
python main.py
```

---

## 🎮 Utilisation

| Action | Comment |
|--------|---------|
| Recherche simple | Taper un mot-clé → Entrée ou bouton Rechercher |
| Multi-recherche | Séparer par des virgules : `op12 display, luffy sr` |
| Aperçu rapide | Cliquer sur une image de carte |
| Copier une image | Clic droit sur l'image → Copier l'image |
| Mettre en favori | Bouton ♥ sur la carte |
| Sauvegarder une recherche | Bouton 💾 Sauvegarder → donner un nom |
| Historique des prix | Bouton 📈 sur une carte |
| Alerte automatique | Onglet Recherche → section "Alerte automatique" |

---

## 📦 Dépendances

| Bibliothèque | Usage |
|---|---|
| `customtkinter` | Interface graphique moderne |
| `requests` | Requêtes HTTP / API Vinted |
| `Pillow` | Chargement et affichage des images |
| `pywin32` | Copie image dans le presse-papier Windows |

---

## ⚠️ Avertissements

- Ce projet utilise l'**API publique non-officielle** de Vinted France. Il peut cesser de fonctionner si Vinted modifie son API.
- Aucun compte Vinted n'est nécessaire.
- Respecte les conditions d'utilisation de Vinted. Ce projet est à des fins éducatives uniquement.

---

## 📄 Licence

MIT — libre d'utilisation, de modification et de distribution.
