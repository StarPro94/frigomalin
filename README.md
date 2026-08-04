# FrigoMalin 🍳

**« Quoi manger avec ce que j'ai dans le frigo ? »** — app web pour Patrick & Emeline, accessible au tel comme au PC.

## Fonctionnalités
- 📝 **Inventaire** du frigo / garde-manger, **sauvegardé automatiquement** (localStorage du navigateur → tu ne retapes jamais).
- ✨ **Recettes par IA (DeepSeek)** selon les ingrédients dispo, le **style** (🌿 Healthy / 😋 Gourmand / 🍟 Gras / 💪 Sportif) et la **durée** (⚡ Rapide / ⏱️ Moyen / 🐢 Long).
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
- [ ] Multi-profils (Patrick / Emeline)
- [ ] Suggestion qui évite les ingrédients presque périmés
- [ ] Mode « je n'ai envie de rien » → surprise

_Le projet évolue automatiquement (cron d'amélioration continue)._
