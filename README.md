# FrigoMalin 🍳

**« Quoi manger avec ce que j'ai dans le frigo ? »** — app web pour Patrick & Emeline, accessible au tel comme au PC.

## Fonctionnalités
- 📝 **Inventaire** du frigo / garde-manger, **sauvegardé automatiquement** (localStorage du navigateur → tu ne retapes jamais).
- ✨ **Recettes par IA (DeepSeek)** selon les ingrédients dispo, le **style** (🌿 Healthy / 😋 Gourmand / 🍟 Gras / 💪 Sportif / 🎲 Surprise) et la **durée** (⚡ Rapide / ⏱️ Moyen / 🐢 Long).
- 📤📥 **Export / Import** de l'inventaire (transfert entre appareils).
- 🔒 Clé DeepSeek **côté serveur** (variable d'environnement Vercel), jamais exposée.

## Stack
- **Frontend** : `public/index.html` (HTML/CSS/JS pur, zéro dépendance).
- **Backend** : `api/recette.py` (DeepSeek) + `api/inventaire.py` (stockage partagé).
- **Stockage partagé** : **Vercel KV (Upstash Redis)** — opérations atomiques (`RPUSH`/`LREM`/`DEL`) → MÊME frigo sur tous les appareils, aucune donnée perdue même en écriture simultanée.
- **IA** : DeepSeek (clé en variable d'environnement Vercel, jamais exposée).
- **Hébergement** : Vercel.

## Déploiement
Projet Vercel + GitHub. La clé doit être définie en variable d'environnement sur Vercel :
```
DEEPSEEK_API_KEY=sk-xxx
```

## Structure
```
frigo-malin/
├── vercel.json       # config Vercel (clean URLs)
├── api/recette.py    # fonction serverless : génération de recette DeepSeek
├── public/index.html # interface (inventaire localStorage + appel /api/recette)
├── README.md
└── CHANGELOG.md
```

## Endpoint
| Route | Méthode | Rôle |
|---|---|---|
| `/` | GET | Interface |
| `/api/recette` | POST | `{mode, duree, ingredients}` → recette IA |

## Roadmap (améliorations continues)
- [x] Export / import inventaire
- [x] **Stockage partagé Redis** (même frigo sur tous les appareils, atomique, aucune perte) — V2
- [x] **Mode « Surprise »** (je n'ai envie de rien → le chef choisit tout) — V1.2
- [x] **Zone congélateur** — V2
- [x] **« Je n'ai pas ça »** : exclure un manquant → recette adaptée — V2
- [x] Multi-profils (Patrick / Emeline) — V3.1 : carnet + bases du placard propres à chacun
- [x] **Dictée vocale** (ajout d'ingrédients à la voix, fr-FR) — V3.2
- [x] **Suggestion qui évite les ingrédients presque périmés** — V3.3 : les produits « à finir » sont écartés de la recette du soir (sauvés à part)
- [x] **Dates de péremption & alertes** — V3.4 : date limite à la réservation, badges « à consommer / périmé » dans les réserves, rappel ⚠️ sur « Ce soir »
- [x] **Recherche dans le carnet** — V3.5 : filtre les plats gardés par titre / auteur
- [x] **Export/import conserve les péremptions** — V3.6 : les dates limites de consommation sont gardées d'un appareil à l'autre

_Le projet évolue automatiquement (cron d'amélioration continue)._
