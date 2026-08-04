# CHANGELOG — FrigoMalin

## V3.1 — Multi-profils (2026-08-04)
- **Carnet et bases du placard désormais propres à chacun** : Patrick et Emeline ont chacun leur carnet de plats gardés et leurs bases cochables — le profil actif (chip P/E) charge/sauvegarde ses propres données (localStorage par profil).

## V3 — « L'Office » (2026-08-04)
Refonte en profondeur, sortie totale du « slop IA » :
- **VRAIE structure d'app** : SPA à 4 écrans (Ce soir / Réserves / Carnet / Nous) avec bottom nav mobile + rail latéral desktop — plus une page qui scrolle.
- **Concept « L'Office »** : le poste de cuisine partagé. Palette papier/tomate/persil, typo Barlow Condensed + Literata, texture papier, filigrane « L'OFFICE », tickets/étiquettes, ombres chaudes.
- **Ce soir** : suggestion du jour avec justification concrète + « À sauver d'abord » (détection produits à finir).
- **Réserves** : onglets classeur Frigo/Placard/Congélo, comptes, recherche, filtre « à finir », ajout rapide.
- **Carnet** : historique des plats gardés (localStorage).
- **Nous** : profils Patrick (ardoise) / Emeline (tomate), préférences, bases du placard cochables, thème nuit, export/import.
- **Fiche recette** : « j'ai pas ça » (adapte), minuteur de cuisson, « garder au carnet ».
- Microcopie humaine (plus aucun terme « générer/IA/optimiser »).

## V2 (2026-08-04)
- Zone congélateur, feature « je n'ai pas ça », relooking, stockage Redis atomique, 36 ingrédients chargés.

## V1 (2026-08-04)
- Inventaire, génération de recettes DeepSeek, export/import, backend 100% stdlib.
