# CHANGELOG — FrigoMalin

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
