# CHANGELOG — FrigoMalin

## V1 (2026-08-04)
- 2026-08-04 — **V1 initiale** : app web complète « quoi manger avec ce que j'ai dans le frigo ».
  - Inventaire frigo / garde-manger, sauvegardé en JSON (persistant, pas besoin de retaper).
  - Dédoublonnage insensible à la casse + ligatures françaises (œufs/Oeufs).
  - Génération de recettes par DeepSeek selon les ingrédients dispo, le style (healthy/gourmand/gras/sportif) et la durée (rapide/moyen/long).
  - Retour structuré : titre, style, temps, difficulté, ingrédients dispo/manquants, étapes, calories, astuce.
  - Clé API côté serveur uniquement (jamais exposée au navigateur).
  - Backend 100% stdlib Python (zéro dépendance).

## V1.2 (2026-08-04)
- 2026-08-04 — **Mode « Surprise »** : quand on n'a aucune envie précise, le chef choisit tout pour toi.
  - Nouveau bouton 🎲 « Surprise » à côté des styles — le style et la durée sont tirés au hasard et l'IA est poussée à proposer un plat inattendu (laisse-lui la main sur le choix à chaque appel).
  - Fonctionne côté serveur (`mode: "surprise"` dans `/api/recette`), le bouton « Autre idée » re-pioche une nouvelle surprise.

## V1.1 (2026-08-04)
- 2026-08-04 — **Export / import de l'inventaire** : sauvegarde, partage et restauration du frigo au format JSON.
  - `GET /api/inventaire/export` → télécharge l'inventaire (fichier `frigomalin-inventaire.json`).
  - `POST /api/inventaire/import` → remplace l'inventaire depuis une liste `[...]` ou `{"ingredients": [...]}` (validation + normalisation des zones, ignore les éléments vides).
  - Boutons « Exporter / Importer » dans l'interface (l'import propose la confirmation avant de remplacer).
