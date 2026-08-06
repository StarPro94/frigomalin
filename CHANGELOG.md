- 2026-08-06 14:38 — Parsing JSON des réponses IA vraiment robuste : plus de découpage « premier { → dernier } » (une accolade dans une phrase, un second objet parasite ou du texte après le JSON faisaient tomber la recette) — le serveur extrait désormais le premier objet JSON équilibré en ignorant les accolades à l'intérieur des chaînes, avec essai direct avant découpage. 9 cas de test passent. + déploiement Vercel (vérifié : `/` 200, `/api/recette` répond une recette).
- 2026-08-06 15:02 — Minuteur fiable même téléphone en poche : le décompte se cale sur un horodatage au lieu de soustraire seconde par seconde — plus de sonnerie en retard ni de temps fantôme quand le navigateur ralentit ou gèle (onglet en arrière-plan, écran verrouillé) ; au retour sur l'onglet, l'affichage se rattrape immédiatement. + déploiement Vercel (vérifié : `/` 200, `/api/recette` répond une recette).

## V3.34 (2026-08-06) — Barre de statut teinte au rythme du thème 🎨
- 2026-08-06 12:50 — Le `theme-color` (barre de statut du téléphone, PWA) suit désormais réellement le thème choisi : bascule jour ☀ / nuit ☾ sur l'appli → la barre de statut passe du vert clair au brun foncé au même instant (avant, elle restait figée sur le clair, seul le `prefers-color-scheme` comptait). + correction serveur : lors d'une régénération (durée dépassée ou mode sans courses), la liste « ⭐ à sauver d'abord » était perdue — elle est désormais retransmise au chef dans le prompt de relance, les priorités sont conservées jusqu'au plat final. + déploiement Vercel.

## V3.33 (2026-08-06) — « ⭐ À sauver d'abord » : le chef compose le plat autour de ce qui presse 🧺
- 2026-08-06 12:42 — Nouveau : marquer un ingrédient « ⭐ à sauver » directement dans les réserves (étoile sur chaque ligne) ou depuis la fiche recette (« ⭐ À sauver d'abord »). Le serveur reçoit la liste `prioriser` et impose au chef d'utiliser ces ingrédients (consigne stricte dans le prompt + **vérification** : si un prioritaire n'apparaît ni dans le dispo ni dans les manquants, il est repris et la recette est régénérée, jusqu'à 3 essais). La liste « À sauver d'abord » sur Ce soir affiche les priorités choisies (ou les urgences auto périmés/à finir) ; les priorités sont mémorisées et purgées quand l'ingrédient disparaît des réserves. + déploiement Vercel.

## V3.32 (2026-08-06) — Robustesse serveur & PWA en nuit 🛠️
- 2026-08-06 12:37 — `api/recette.py` : la garde « impossible de générer une recette valide » est désormais atteignable (elle était placée après un `return`, donc jamais levée) → après 3 essais infructueux, le serveur répond une vraie erreur 500 explicite au lieu de renvoyer `None` ; barre d'outils de la fiche recette en mode nuit (fond sombre, pas de bloc clair) ; PWA : `theme-color` suit le thème (jour ☀ / nuit ☾) et le cache du service worker est rafraîchi (v2). + déploiement Vercel.

## V3.31 (2026-08-06) — « À finir » trié par urgence 🧊
- 2026-08-06 14:15 — Le filtre « À finir » des réserves et la liste « À sauver d'abord » classent désormais par urgence réelle : ce qui est vide/fini passe devant ce qui est juste entamé (vide > fond/½ > peu > entamé, puis alphabétique). Fini de chercher le fond de crème au milieu de la liste. + déploiement Vercel.

## V3.30 (2026-08-06) — Nettoyage serveur 🧹
- 2026-08-06 13:05 — Correction du code mort dans `api/recette.py` : `raise ValueError` placé après un `return` (jamais atteignable) → supprimé la confusion, le flux reste explicite et compilable. + déploiement Vercel (vérifié : `/` 200, `/api/recette` répond une recette).

## V3.29 (2026-08-06) — Durées « 1 h 15 » enfin comptées juste ⏱️
- 2026-08-06 12:15 — Le minuteur et la vérification « durée max » savent désormais lire les durées composées (« 1 h 15 min », « 1h30 », « 1h30min » → 75/90 min) au lieu de ne retenir que l'heure. Auparavant, une recette annoncée « 1 h 15 » lançait un minuteur d'1 h seulement et la durée max était contrôlée sur 60 min au lieu de 75. + déploiement Vercel.

## V3.28 (2026-08-06) — Installable sur le téléphone 📲
- 2026-08-06 11:10 — PWA : manifest + icône + service worker (cache de l'app) → FrigoMalin s'installe sur l'écran d'accueil du téléphone comme une vraie app, démarre plus vite et fonctionne même sans réseau (l'API reste toujours fraîche). + déploiement Vercel.

## V3.27 (2026-08-06) — Envie de cuisine mémorisée par profil 🧂
- 2026-08-06 10:52 — Chaque profil (Patrick / Emeline) garde en mémoire sa propre envie de cuisine : mode, durée max, difficulté max et parts par défaut se rétablissent automatiquement au changement de profil et à la prochaine visite. + déploiement Vercel.

## V3.26 (2026-08-06) — Mode « Végétarien » 🥬
- 2026-08-06 10:38 — Nouveau mode « 🥬 Végétarien » (sans viande ni poisson) dans « Changer l'envie », appliqué strictement par le chef (aucun ingrédient carné ni utilisé ni manquant) + déploiement Vercel.

## V3.25 (2026-08-06) — Recette robuste face aux réponses IA 🛡️
- 2026-08-06 10:23 — Normalisation serveur des réponses IA (listes/parts/difficulté bornées) + déploiement Vercel.
- Backend : chaque recette renvoyée par l'IA est **réassainie** avant d'atteindre l'écran — les listes (`étapes`, `ingrédients dispo`, `manquants`) sont toujours des listes (l'IA a pu les renvoyer en texte ou en virgules → elles sont découpées), le nombre de `parts` est forcé en entier borné (1-24) et les niveaux de difficulté harmonisés (« moyenne » → « Moyenne »). Fini la fiche recette qui peut casser si le modèle dévie du format attendu.

## V3.24 (2026-08-06) — Minuteur qui sonne 🔔
- À la fin du décompte, le minuteur **sonne et vibre** : 3 bips (WebAudio, aucun fichier à charger) + vibration sur mobile, et le bloc passe en pulsation rouge « Terminé ! » — impossible de rater la fin de cuisson, même téléphone en poche.
- 2026-08-06 09:35 — Alarme sonore + vibration + pulsation visuelle en fin de minuteur, déploiement Vercel.

## V3.23 (2026-08-06) — Étapes de cuisson cochables ✅
- Dans la fiche recette, chaque **étape** de la recette est désormais **cochable** : un appui la barre (✓) quand elle est faite, un second appui la décoche. Un **compteur de progression** (« 3/7 ») suit votre avancement et un bouton **« ↺ réinitialiser »** remet toutes les cases à zéro. Pratique en cuisine pour ne plus perdre le fil de la recette.
- 2026-08-06 06:40 — Étapes cochables (checklist + compteur de progression + réinitialisation) + déploiement Vercel.

- Le bouton **« Minuteur »** se cale automatiquement sur la durée de la recette : si le plat annonce « 30 minutes », le bouton affiche « Minuteur 30 min » et le décompte part de 30 min (10 min par défaut si la durée est inconnue). Avant de lancer, on peut ajuster de **+5 / −5 min** en un appui. Quand c'est fini, « Terminé ! » s'affiche.
- 2026-08-06 06:10 — Minuteur réglable calé sur la durée de la recette (label + décompte auto, ajustement ±5 min) + déploiement Vercel.

## V3.21 (2026-08-06) — Mode « Sans courses » 🚫
- Dans « Changer l'envie », nouveau toggle **« 🚫 Sans courses — uniquement ce qu'on a »** : le chef doit composer la recette **uniquement avec les ingrédients disponibles**, liste « Il manque » vide (seuls sel, poivre, huile et épices de base sont tolérés). S'il propose quand même un achat, le serveur le reprend et régénère. Badge « 🚫 sans courses » dans la fiche, rappel « rien à acheter » sur Ce soir. Le choix est mémorisé sur le téléphone.
- 2026-08-06 05:57 — Mode « Sans courses » (contrainte stricte côté serveur + toggle mémorisé + vérification/régénération) + déploiement Vercel.

## V3.20 (2026-08-06) — « Une autre idée » vraiment différente 🔄
- Bouton **« Une autre idée »** sur « Ce soir » : le plat déjà proposé (et les suivants) est désormais **exclu côté serveur** — plus de risque de retomber deux fois sur la même recette. Le backend accepte une liste `eviter_plats` et interdit explicitement à l'IA de les reproposer.
- 2026-08-06 04:40 — « Une autre idée » exclut les plats déjà proposés (param `eviter_plats`) + déploiement Vercel.

## V3.19 (2026-08-06) — Liste de courses 🛒
- Dans la fiche recette, nouveau bouton **« 🛒 Liste de courses »** : un appui copie d'un coup tous les ingrédients manquants en liste prête pour les courses (avec le titre du plat en entête). Si tout est à la maison, le bouton affiche « ✓ Tout est là ! ». Pratique pour faire les courses sans recopier.
- 2026-08-06 03:50 — Liste de courses (copie des manquants depuis la fiche) + déploiement Vercel.

## V3.18 (2026-08-06) — Recherche intelligente dans les réserves 🔍
- Réserves : la recherche ignore désormais les **accents et la casse** (« creme » trouve « Crème fraîche », « oeuf » trouve « Œufs », « EPINARDS » trouve « Épinards ») et cherche aussi dans la **quantité/état** (« fond » trouve « un fond de crème »). Au passage, la déduplication des doublons (ajout d'un ingrédient déjà présent) tolère elle aussi les accents.
- 2026-08-06 02:05 — Recherche insensible aux accents/ligatures + recherche dans la quantité + dédup corrigée, déploiement Vercel.

## V3.17 (2026-08-06) — Vider les périmés 🗑️
- Réserves : nouveau bouton **« 🗑️ Vider les périmés »** qui apparaît dès qu'un ingrédient est périmé (toutes zones confondues). Un appui affiche le décompte + la liste des produits à jeter, on confirme, et tout ce qui est périmé est enlevé d'un coup — plus besoin de supprimer ingrédient par ingrédient après une absence.
- 2026-08-06 01:40 — Vider les périmés en un geste (avec confirmation) + déploiement Vercel.

## V3.16 (2026-08-06) — Budget temporel serveur ⏱️
- Backend : l'appel DeepSeek est désormais borné dans le temps (timeout par tentative réduit à 40 s, budget global de 48 s pour l'ensemble génération + retry). Fini la fonction tuée silencieusement par la limite Vercel en plein milieu : si le temps manque, on répond une **HTTP 504** claire (« Réessaie ») au lieu d'un échec muet. On arrête tôt les nouvelles tentatives quand le budget est épuisé.
- 2026-08-06 00:40 — Budget temporel global (timeout 40 s/tentative, 48 s au total, 504 propre) + déploiement Vercel.

## V3.15 (2026-08-05) — Partager une recette ↗
- Dans la fiche recette, nouveau bouton **« ↗ Partager »** : sur mobile, ouvre le menu de partage natif (messages, mail, etc.) ; sur ordinateur (ou si partage natif indisponible), copie la recette en texte dans le presse-papiers — titre, style, durées, ingrédients dispo/manquants, étapes et astuce, avec l'entête « proposé par FrigoMalin ». Pratique pour envoyer le menu du soir à l'autre.
- 2026-08-05 22:28 — Bouton Partager (partage natif mobile + copie presse-papiers en secours) + déploiement Vercel.

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

- 2026-08-06 22:20 — **Robustesse du chat recette (V3.37)** : `api/chat.py` aligné sur `api/recette.py` — entrée validée (JSON malformé, `messages`/`ingredients`/`recette` mal typés, mode inconnu → **HTTP 400** clair au lieu dun