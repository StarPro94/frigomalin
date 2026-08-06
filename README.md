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
- [x] **Mode Surprise explicite + parsing robuste** — V3.7 : « je n'ai envie de rien » géré côté serveur (chef créatif), réponse IA parsée même en bloc markdown, détection des réponses vides
- [x] **Thème jour/nuit mémorisé** — V3.8 : le choix ☾/☀ est sauvegardé et rétabli automatiquement au prochain chargement
- [x] **Filtre « ⚠️ Péremption » dans les réserves** — V3.9 : affiche uniquement les ingrédients périmés ou à consommer (≤ 2 jours), pour cuisiner en priorité ce qui presse
- [x] **Résilience réseau DeepSeek** — V3.10 : retry automatique (×3, backoff court) sur timeout / coupure / 5xx / 429 — les pannes passagères ne cassent plus la requête
- [x] **Favoris de recettes** — V3.11 : bouton « ❤️ Mettre en favori » dans la fiche, filtre « ❤️ Favoris » au carnet pour ne voir que les plats qu'on adore
- [x] **Tri urgent dans le filtre Péremption** — V3.12 : dans « ⚠️ Péremption », ce qui presse (périmé → à consommer → par date) remonte en haut de liste, fini l'ordre alphabétique illisible
- [x] **Validation d'entrée & erreurs HTTP propres** — V3.13 : mode inconnu, JSON malformé ou champ mal typé → réponse **HTTP 400** claire avant d'appeler DeepSeek (plus d'erreur avalée ni d'appel IA gaspillé)
- [x] **Ajout d'un manquant en un geste (＋)** — V3.14 : dans la fiche recette, un appui sur le ＋ d'un « Il manque » l'ajoute directement aux réserves (frigo), sans doublon
- [x] **Partager une recette (↗)** — V3.15 : bouton dans la fiche → partage natif mobile ou copie de la recette (titre, ingrédients, étapes, astuce) dans le presse-papiers, pour envoyer le menu du soir
- [x] **Budget temporel serveur** — V3.16 : appel DeepSeek borné dans le temps (40 s/tentative, 48 s au total), arrêt anticipé des retry, et **HTTP 504** claire au lieu d'une fonction tuée par la limite Vercel en plein milieu d'une génération
- [x] **Vider les périmés** — V3.17 : bouton « 🗑️ Vider les périmés » dans les réserves dès qu'un ingrédient est périmé → confirmation avec le décompte + la liste, puis suppression de tout le périmé en un geste (plus de ménage ingrédient par ingrédient)
- [x] **Recherche intelligente dans les réserves** — V3.18 : la recherche ignore accents et casse (« creme » → « Crème », « oeuf » → « Œufs »), matche aussi la quantité/état (« fond » → « un fond de crème »), et la déduplication des doublons tolère les accents
- [x] **Liste de courses** — V3.19 : bouton « 🛒 Liste de courses » dans la fiche recette → copie tous les ingrédients manquants en une liste prête pour les courses (« ✓ Tout est là ! » si rien ne manque)
- [x] **« Une autre idée » vraiment différente** — V3.20 : le bouton « Une autre idée » exclut côté serveur les plats déjà proposés (param `eviter_plats`), fini de retomber deux fois sur la même recette
- [x] **Mode « Sans courses »** — V3.21 : toggle « 🚫 Sans courses » dans « Changer l'envie » → recette composée uniquement avec ce qu'on a (liste « Il manque » vide, seuls sel/poivre/huile/épices tolérés), vérifié et régénéré côté serveur si l'IA propose un achat, choix mémorisé

_Le projet évolue automatiquement (cron d'amélioration continue)._
