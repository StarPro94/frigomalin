# CHANGELOG — FrigoMalin

## V3.14 (2026-08-05) — « C'est à la maison » : ajouter un manquant en un geste
- Dans la fiche recette, chaque ingrédient de la liste **« Il manque »** a désormais un petit **＋** : un appui l'ajoute directement aux **réserves (frigo)**, en évitant les doublons. Plus besoin de recopier ou de ranger à la main ce qui manque — on clique et c'est rayé du manquant.
- 2026-08-05 21:50 — Ajout rapide d'un manquant depuis la fiche recette + déploiement Vercel.

## V3.13 (2026-08-05) — Validation des entrées & erreurs HTTP propres
- Backend : les requêtes sont désormais **validées** avant d'appeler DeepSeek. Mode inconnu, JSON malformé, corps non-objet ou champ mal typé → réponse **HTTP 400** claire en français, au lieu de générer discrètement une recette avec des valeurs par défaut ou d'avaler silencieusement l'erreur. Plus d'appel IA gaspillé sur une entrée invalide.
- 2026-08-05 21:26 — Validation d'entrée + erreurs 400 propres côté `/api/recette` + déploiement Vercel.

## V3.12 (2026-08-04) — Tri urgent dans le filtre Péremption
- Réserves : dans le filtre « ⚠️ Péremption », les ingrédients s'affichent désormais par ordre d'urgence (périmés d'abord, puis « à consommer », puis par date limite) au lieu de l'ordre alphabétique — on voit en un coup d'œil ce qu'il faut cuisiner en priorité.
- 2026-08-04 19:57 — Tri par urgence dans le filtre Péremption + déploiement Vercel.

## V3.11 (2026-08-04) — Favoris de recettes ❤️
- Nouveau : bouton **« ❤️ Mettre en favori »** directement dans la fiche recette pour marquer un plat qu'on adore.
- Dans **Le carnet**, filtre **« ❤️ Favoris »** pour ne voir que les plats en favori ; chaque plat gardé a un bouton ♥/💔 pour l'ajouter/retirer, et un ♥ s'affiche à côté du titre. Les favoris sont enregistrés dans le navigateur.
- 2026-08-04 20:10 — Favoris de recettes (♥ dans la fiche + filtre Favoris au carnet) + déploiement Vercel.

## V3.10 (2026-08-04) — Résilience réseau côté serveur
- Backend : l'appel à DeepSeek réessaie automatiquement (jusqu'à 3 fois, avec court backoff) en cas de panne passagère — timeout, coupure réseau ou réponse 5xx/429 de l'API. Fini la requête qui échoue juste parce qu'DeepSeek bafouille un instant.
- 2026-08-04 — Retry automatique sur pannes transitoires DeepSeek + déploiement Vercel.

## V3.9 (2026-08-04) — Filtre « ⚠️ Péremption » dans les réserves
- Réserves : nouveau filtre **« ⚠️ Péremption »** à côté de « Tout » et « À finir » — affiche uniquement les ingrédients périmés ou à consommer (≤ 2 jours), pratique pour savoir quoi cuisiner en priorité.
- 2026-08-04 — Filtre péremption dans les réserves + déploiement Vercel.

## V3.8 (2026-08-04) — Thème jour/nuit mémorisé
- Frontend : le choix du thème Jour/Nuit est désormais **enregistré** (localStorage) et rétabli automatiquement au prochain chargement — plus besoin de re-cliquer sur ☾ à chaque visite. S'applique dès l'ouverture de l'app.
- 2026-08-04 — Thème jour/nuit persistant + déploiement Vercel.

## V3.7 (2026-08-04) — Mode Surprise explicite + parsing robuste
- Backend : le mode **Surprise** (« je n'ai envie de rien ») est désormais un mode à part entière côté serveur — le chef reçoit une consigne « créatif et original, aucune contrainte de style » au lieu d'aucune instruction.
- Backend : parsing JSON plus robuste — gère les blocs markdown ```json``` autour de la réponse et détecte proprement les réponses vides/malformées.
- 2026-08-04 — Mode Surprise côté serveur + parsing markdown/JSON robuste + déploiement Vercel.

## V3.6 (2026-08-04) — Export/import conserve les dates de péremption
- Correction : l'export/import des réserves ne perdait plus la date limite de consommation (date_peremption) — elle est désormais conservée au transfert entre appareils.

## V3.5 (2026-08-04) — Recherche dans le carnet
- Champ de recherche dans **Le carnet** : filtre les plats gardés par titre (ou par auteur Patrick/Emeline), même quand la liste s'allonge.
- 2026-08-04 — Recherche dans le carnet (filtre par titre/auteur) + déploiement Vercel.

## V3.4 (2026-08-04) — Dates de péremption & alertes
- À la réservation d'un ingrédient (ou en le modifiant), on peut indiquer une **date limite de consommation** (champ date).
- **Badges dans les réserves** : « à consommer » (≤ 2 jours) en moutarde, « périmé » en rouge à côté de l'ingrédient.
- **Rappel sur « Ce soir »** : alerte ⚠️ quand quelque chose est périmé (à jeter), toujours en plus des « à finir ».
- Backend `/api/inventaire` : stocke et restitue `date_peremption` (rétrocompatible, champ facultatif).

## V3.2 (2026-08-04) — Contraintes strictes + chat + gestion réserves
- **Contraintes RESPECTÉES** : durée max en minutes, difficulté max, style, nombre de parts — le backend les impose et les VÉRIFIE (re-génère si dépassement). Fini le "rapide" qui sortait une recette de 60 min.
- **Chat avec l'IA de la recette** (`/api/chat`) : dis "on n'a plus de X / l'étape 2 n'est pas claire / pour 4 personnes" → la recette s'adapte.
- **Parts ajustables** (+/−) dans la fiche, par défaut 2.
- **Menu ⋯ sur chaque ingrédient** : Modifier / compléter / Supprimer (remplace le buggy "c'est fini").
- **Bases du placard exhaustives** : épices variées (paprika, cumin, curry, curcuma…), 6 types de pâtes, riz, blé, semoule, lentilles, pois chiches…
- **Sauvegarde claire** : bouton "⭐ Garder ce plat" visible → carnet.
- **Icônes SVG corrigées** (plus d'icônes noires), refonte mobile compacte.

## V3 — « L'Office » (2026-08-04)
SPA 4 écrans (Ce soir/Réserves/Carnet/Nous), bottom nav mobile + rail desktop, concept carnet de chef (palette papier/tomate/persil, Barlow Condensed + Literata), minuteur, profils Patrick/Emeline, thème nuit, microcopie humaine.

## V2 (2026-08-04)
Zone congélateur, « je n'ai pas ça », relooking, stockage Redis atomique, 36 ingrédients chargés.

## V1 (2026-08-04)
Inventaire, recettes DeepSeek, export/import.
