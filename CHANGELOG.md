# CHANGELOG — FrigoMalin

## V2 (2026-08-04) — Le jeu se corse ✨
- **Zone congélateur** ajoutée (frigo / placard / congélateur), backend + 3 onglets.
- **Feature « je n'ai pas ça »** : sur chaque ingrédient manquant d'une recette, bouton pour l'exclure → l'IA régénère une recette adaptée qui l'évite totalement.
- **Relooking complet** : design éditorial chaleureux (Fraunces serif + Inter, palette papier/terracotta/vert profond, grain papier) — sorti du « slop IA ».
- **Stockage partagé Redis** (Vercel KV) : opérations atomiques, même frigo sur tous les appareils, aucune perte même en écriture simultanée.
- Inventaire réel chargé : 36 ingrédients (frigo 12 / placard 12 / congélateur 12).
- (hérité) Mode « surprise » + export/import + DeepSeek.

## V1 (2026-08-04)
- 2026-08-04 — **V1 initiale** : app « quoi manger avec ce que j'ai ».
  - Inventaire frigo / garde-manger, génération de recettes par DeepSeek (style + durée).
  - Export/import, dédoublonnage, backend 100% stdlib.
