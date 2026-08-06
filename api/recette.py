#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FrigoMalin — fonctions serverless Vercel : génération et chat recette.

- POST /api/recette : génère une recette avec des CONTRAINTES IMPÉRATIVES
  (durée max en minutes, difficulté max, style, nombre de parts) et les VÉRIFIE
  (re-génère si dépassement).
- POST /api/chat    : discute avec l'IA de la recette pour la modifier
  (ingrédient manquant, étape peu claire, envie…) — stateless, l'historique
  est passé par le client.

La clé DeepSeek est lue depuis l'env Vercel. 100% stdlib.
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Budget temporel global : Vercel serverless peut tuer la fonction au-delà de
# quelques dizaines de secondes (limit GC). On borne l'ensemble génération+retry
# pour rester sous la limite et rendre une 504 claire au lieu d'un échec muet.
GLOBAL_TIMEOUT = 48.0
CALL_TIMEOUT = 40.0

MODES = {
    "healthy": "healthy : léger, équilibré, peu calorique",
    "gourmand": "gourmand : réconfortant, savoureux, généreux",
    "gras": "gras : indulgente, riche, réconfortante",
    "sportif": "sportif : riche en protéines, adapté à l'effort",
    "veggie": "végétarien : sans viande ni poisson, à base de légumes, œufs, "
              "produits laitiers et légumineuses (respecte STRICTEMENT : aucun "
              "ingrédient carné, ni utilisé ni manquant)",
    "surprise": "surprise : laisse-toi guider, sois créatif et original, "
                 "varie totalement selon les ingrédients (aucune contrainte de style)",
}
DIFFS = {"facile": "Facile", "moyen": "Moyenne", "difficile": "Difficile"}

SYSTEM = (
    "Tu es le chef de l'office de Patrick et Emeline. Tu proposes des recettes "
    "réalistes avec les ingrédients disponibles. Tu respectes STRICTEMENT les "
    "contraintes demandées (durée max, difficulté max, style, nombre de parts). "
    "Tu réponds TOUJOURS en JSON valide, sans texte avant ni après."
)

JSON_STRUCT = (
    '"titre": "Nom",'
    '"style": "une ligne",'
    '"temps": "XX minutes",'
    '"difficulte": "Facile | Moyenne | Difficile",'
    '"parts": N,'
    '"ingredients_dispo_utilises": ["..."],'
    '"ingredients_manquants": ["..."],'
    '"etapes": ["..."],'
    '"calories_estimees": "..." ,'
    '"astuce": "..."'
)


def _send(h, code, obj):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    h.send_response(code)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Access-Control-Allow-Origin", "*")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


class BadRequest(Exception):
    """Entrée invalide côté client → réponse HTTP 400."""


def _read_body(h):
    try:
        length = int(h.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = h.rfile.read(length).decode("utf-8") or "{}"
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise BadRequest("Le corps de la requête doit être un objet JSON.")
        return data
    except BadRequest:
        raise
    except Exception:
        raise BadRequest("Corps de requête JSON invalide.")


def _valider_entree(body):
    """Vérifie les champs connus : mode connu, listes typées.

    Renvoie 400 avec un message clair plutôt que de générer une recette
    avec des valeurs par défaut silencieuses (le bug silencieux coûte
    un appel DeepSeek inutile et masque les vrais problèmes).
    """
    mode = body.get("mode", "gourmand")
    if mode not in MODES:
        raise BadRequest(
            "Mode inconnu : %r. Modes possibles : %s."
            % (mode, ", ".join(sorted(MODES)))
        )
    for champ in ("ingredients", "bases", "exclusions", "messages", "eviter_plats", "prioriser"):
        v = body.get(champ)
        if v is not None and not isinstance(v, list):
            raise BadRequest("Le champ '%s' doit être une liste." % champ)
    for champ in ("duree_max", "parts"):
        v = body.get(champ)
        if v is not None and not isinstance(v, (int, float)):
            raise BadRequest("Le champ '%s' doit être un nombre." % champ)
    if body.get("sans_courses") is not None and not isinstance(body.get("sans_courses"), bool):
        raise BadRequest("Le champ 'sans_courses' doit être un booléen.")


class BudgetDepasse(Exception):
    """Le budget de temps global est épuisé → réponse HTTP 504 (au lieu d'un échec muet)."""


def _call(prompt, temperature=0.8, deadline=None):
    """Appelle DeepSeek avec retry automatique (fiabilité au quotidien).

    On retente jusqu'à 3 fois sur les erreurs transitoires : timeout réseau,
    erreur de connexion ou réponses 5xx/429 de l'API — les pannes passagères
    de DeepSeek ne font plus échouer la requête de l'utilisateur.

    `deadline` (epoch, optionnel) borne le temps total : on s'arrête tôt si le
    budget temporel est épuisé, pour ne pas dépasser la limite Vercel.
    """
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "max_tokens": 2200,
        "temperature": temperature,
        "stream": False,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + DEEPSEEK_API_KEY},
        method="POST",
    )
    last = None
    for attempt in range(3):
        if deadline is not None and time.time() >= deadline:
            raise BudgetDepasse()
        try:
            with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                last = e  # surcharge / panne passagère → on retente
            else:
                raise  # erreur durable (410, 401…) → on la remonte tout de suite
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # erreur transitoire : réseau coupé, timeout, connexion refusée → on retente
            last = e
        if attempt < 2 and (deadline is None or time.time() < deadline - 2):
            time.sleep(min(1 + attempt, 2))  # backoff court : 1s puis 2s
    raise last if last else Exception("Échec de l'appel DeepSeek")


def _extraire_json(texte):
    """Extrait le premier objet JSON {...} d'une réponse IA.

    Parcourt caractère par caractère en ignorant les accolades à l'intérieur
    des chaînes (l'IA peut écrire « 1/2 } de citron » ou une émoticône) et
    s'arrête à l'accolade fermante correspondante. Beaucoup plus fiable que
    découper entre le premier `{` et le dernier `}` : du texte après le JSON,
    deux objets, ou une accolade dans une phrase ne cassent plus la recette.
    """
    debut = texte.find("{")
    if debut == -1:
        raise ValueError("Réponse IA malformée")
    profondeur = 0
    dans_chaine = False
    echappe = False
    for i in range(debut, len(texte)):
        c = texte[i]
        if dans_chaine:
            if echappe:
                echappe = False
            elif c == "\\":
                echappe = True
            elif c == '"':
                dans_chaine = False
            continue
        if c == '"':
            dans_chaine = True
        elif c == "{":
            profondeur += 1
        elif c == "}":
            profondeur -= 1
            if profondeur == 0:
                return texte[debut:i + 1]
    raise ValueError("Réponse IA malformée")


def parse_recette(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Réponse IA vide")
    raw2 = raw.strip()
    # retire un éventuel bloc de code markdown ```json ... ```
    if raw2.startswith("```"):
        raw2 = re.sub(r"^```[a-zA-Z]*\s*", "", raw2)
        raw2 = re.sub(r"\s*```\s*$", "", raw2)
    # 1) essai direct : réponse propre → aucun découpage nécessaire
    try:
        return json.loads(raw2)
    except Exception:
        pass
    # 2) extraction du premier objet JSON équilibré (accolades dans les chaînes ignorées)
    return json.loads(_extraire_json(raw2))


def _as_list(v, split_phrases=False):
    """Force un champ en liste de chaînes : tolère liste, chaîne unique,
    tuple… afin qu'un format légèrement déviant de l'IA ne casse pas la carte."""
    if v is None or v == "":
        return []
    if isinstance(v, str):
        # l'IA a pu renvoyer un texte au lieu d'une liste → on découpe intelligemment
        # (points de fin de phrase pour les étapes, ; / virgules pour les ingrédients)
        if split_phrases:
            items = [x.strip() for x in re.split(r"[;.]+ |[;.]+$|\n", v) if x.strip()]
        else:
            items = [x.strip() for x in re.split(r"[;\n]+|,(?=\s)", v) if x.strip()]
        if not items:
            items = [v.strip()]
        return [x for x in items if x and not x.isspace()]
    if isinstance(v, (list, tuple)):
        out = []
        for x in v:
            if isinstance(x, str):
                out.append(x.strip())
            elif x is not None:
                out.append(str(x).strip())
        return [x for x in out if x]
    return [str(v).strip()]


def normalize_recette(r):
    """Réassainit la recette renvoyée par l'IA pour que la page ne casse jamais :
    les listes sont toujours des listes, les chaînes des chaînes, parts un entier."""
    if not isinstance(r, dict):
        raise ValueError("Réponse IA non objet")
    r["ingredients_dispo_utilises"] = _as_list(r.get("ingredients_dispo_utilises"))
    r["ingredients_manquants"] = _as_list(r.get("ingredients_manquants"))
    r["etapes"] = _as_list(r.get("etapes"), split_phrases=True)
    for champ in ("titre", "style", "temps", "difficulte", "calories_estimees", "astuce"):
        v = r.get(champ)
        r[champ] = (str(v).strip() if v is not None else "")
        if champ == "difficulte" and r["difficulte"]:
            # harmonise la casse/typo des niveaux de difficulté connus
            for kk, vv in DIFFS.items():
                if vv.lower() == r["difficulte"].lower():
                    r["difficulte"] = vv
                    break
    try:
        r["parts"] = int(r.get("parts", 2))
    except (TypeError, ValueError):
        r["parts"] = 2
    r["parts"] = max(1, min(r["parts"], 24))
    return r


def minutes_from(temps):
    """Extrait le nombre de minutes d'une chaîne de temps. Retourne None si inconnu.

    Gère « 1 h 15 min », « 1h30 », « 1h30min », « 1,5 h », « 2 heures », « 45 min »…
    (le minuteur et la vérification « durée max » se calent dessus)."""
    t = str(temps or "").lower().strip()
    if not t:
        return None
    # « 1 h 15 min » / « 1h30 » / « 1h30min » → heures + minutes
    hm = (re.search(r"(?:^|\D)(\d{1,2})\s*h\s*(\d{1,2})\s*min(?:utes)?\b", t)
          or re.search(r"(?:^|\D)(\d{1,2})\s*h\s*(\d{1,2})(?![.,\d])", t))
    if hm:
        return int(hm.group(1)) * 60 + int(hm.group(2))
    # « 2 h » / « 1,5 h » / « 1h » / « 2 heures »
    h = re.search(r"(\d+(?:[.,]\d+)?)\s*h", t)
    if h:
        return int(float(h.group(1).replace(",", ".")) * 60)
    m = re.search(r"(\d+)\s*min", t)
    if m:
        return int(m.group(1))
    return None


def build_constraints(mode, duree_max, difficulte_max, parts):
    lines = []
    if mode in MODES:
        lines.append(f"Type de plat : {MODES[mode]}. RESPECTE ce style.")
    if isinstance(duree_max, int) and duree_max > 0:
        lines.append(f"Durée totale de préparation MAXIMALE : {duree_max} minutes. "
                     f"Il est STRICTEMENT INTERDIT de dépasser {duree_max} minutes au total. "
                     f"Aucune recette longue. Le champ 'temps' doit être <= {duree_max} minutes.")
    if difficulte_max in DIFFS:
        lines.append(f"Difficulté MAXIMALE : {DIFFS[difficulte_max]}. Ne dépasse pas ce niveau.")
    if isinstance(parts, int) and parts > 0:
        lines.append(f"Recette pour {parts} personne(s). Ajuste les quantités en conséquence.")
    return "\n".join(lines) if lines else ""


# Assaisonnements de base qu'on a presque toujours : en mode « sans courses »,
# ils ne comptent pas comme « ingrédients manquants » à acheter.
BASES_TOLEREES = (
    "sel", "poivre", "huile", "vinaigre", "moutarde", "sucre", "farine",
    "beurre", "ail", "oignon", "échalote", "echalote", "épice", "epice",
    "herbe", "laurier", "thym", "romarin", "origan", "bouillon", "citron",
)


def norm_alim(s):
    """Normalise un nom d'ingrédient pour la comparaison (accent, casse,
    ligatures et quantités retirés) : « 200g de Riz » ≈ « riz »."""
    t = str(s or "").lower()
    t = t.replace("œ", "oe").replace("æ", "ae")
    t = "".join(c for c in t if c.isalnum() or c.isspace())
    t = t.replace("de ", " ").replace("d'", " ").replace("des ", " ")
    t = re.sub(r"^\d+(?:[.,]\d+)?\s*(?:g|kg|cl|l|ml|dl|gr|litre|litres)?\s*", "", t).strip()
    return " ".join(t.split())


def est_assaisonnement(m):
    mm = str(m or "").lower().strip()
    return any(k in mm for k in BASES_TOLEREES)


def build_generate_prompt(ingredients, bases, exclusions, mode, duree_max, difficulte_max, parts, eviter_plats=None, sans_courses=False, prioriser=None):
    dispo = ", ".join(ingredients) if ingredients else "AUCUN renseigné"
    tout = ", ".join(bases) if bases else ""
    excl = ""
    if exclusions:
        excl = (f"\nIMPORTANT : on n'a PAS à la maison (ne les cite ni comme utilisé ni comme manquant) : "
                f"{', '.join(exclusions)}. Adapte complètement.")
    evite = ""
    if eviter_plats:
        evite = (f"\nIMPORTANT : ne propose SURTOUT PAS ces plats (déjà proposés tout à l'heure, on n'en veut pas) : "
                 f"{', '.join(eviter_plats)}. Trouve une idée vraiment différente.")
    prior = ""
    if prioriser:
        prior = (f"\nIMPORTANT : on veut ABSOLUMENT utiliser en priorité : {', '.join(prioriser)}. "
                 f"Compose le plat AUTOUR de ces ingrédients, en les mettant en valeur. "
                 f"Chacun d'eux doit apparaître dans 'ingredients_dispo_utilises'.")
    sc = ""
    if sans_courses:
        sc = ("\nIMPORTANT : mode SANS COURSES — utilise UNIQUEMENT les ingrédients disponibles, "
              "ne propose AUCUN ingrédient à acheter. La liste 'ingredients_manquants' doit être VIDE "
              "(seuls les assaisonnements de base comme sel, poivre, huile ou épices sont tolérés, "
              "car on les a presque toujours). Compose avec ce qu'on a, même si c'est simple.")
    bases_s = f"\nBases qu'on a presque toujours (à utiliser si besoin, sans les lister comme manquants) : {tout}." if tout else ""
    c = build_constraints(mode, duree_max, difficulte_max, parts)
    return f"""
Contexte : je cuisine pour ma famille avec ce que j'ai.
Ingrédients disponibles : {dispo}.{bases_s}{excl}{evite}{prior}{sc}

Contraintes (à respecter IMPÉRATIVEMENT) : {c}

Réponds en JSON avec EXACTEMENT cette structure (pas de markdown, pas de texte autour) :
{{{JSON_STRUCT}}}
"""


def generate(body):
    ingredients = [str(i).strip() for i in body.get("ingredients", []) if str(i).strip()]
    bases = [str(i).strip() for i in body.get("bases", []) if str(i).strip()]
    exclusions = [str(i).strip() for i in body.get("exclusions", []) if str(i).strip()]
    eviter_plats = [str(i).strip() for i in body.get("eviter_plats", []) if str(i).strip()]
    mode = str(body.get("mode", "gourmand"))
    duree_max = body.get("duree_max")
    duree_max = int(duree_max) if isinstance(duree_max, (int, float)) and duree_max > 0 else None
    difficulte_max = str(body.get("difficulte_max", "difficile"))
    parts = body.get("parts")
    parts = int(parts) if isinstance(parts, (int, float)) and parts > 0 else 2
    sans_courses = body.get("sans_courses") is True
    prioriser = [str(i).strip() for i in body.get("prioriser", []) if str(i).strip()]

    # on essaie jusqu'à 3 fois, en durcissant la consigne durée si dépassé
    deadline = time.time() + GLOBAL_TIMEOUT
    prompt = build_generate_prompt(ingredients, bases, exclusions, mode, duree_max, difficulte_max, parts, eviter_plats, sans_courses, prioriser)
    for attempt in range(3):
        raw = _call(prompt, deadline=deadline)
        r = normalize_recette(parse_recette(raw))
        # Priorité : chaque ingrédient « à sauver » doit être dans le plat.
        # Si l'IA n'a pas tenu compte, on insiste d'un ton ferme et on régénère.
        if prioriser:
            dispo_norm = set(norm_alim(x) for x in (r.get("ingredients_dispo_utilises") or []))
            manquants_norm = set(norm_alim(x) for x in (r.get("ingredients_manquants") or []))
            ignores = [p for p in prioriser if norm_alim(p) not in dispo_norm and norm_alim(p) not in manquants_norm]
            if ignores:
                prompt = prompt + (
                    "\n\nATTENTION : tu n'as PAS utilisé ce qu'on veut sauver : "
                    + ", ".join(ignores)
                    + ". Refais la recette AUTOUR de ces ingrédients : ils doivent figurer "
                    "dans 'ingredients_dispo_utilises' (adaptés, par ex. '200g de riz')."
                )
                continue
        if duree_max:
            mn = minutes_from(r.get("temps"))
            if mn is not None and mn > duree_max:
                prompt = build_generate_prompt(ingredients, bases, exclusions, mode, duree_max, difficulte_max, parts, eviter_plats, sans_courses, prioriser) + (
                    f"\n\nATTENTION : la recette précedente durait {r.get('temps')}, ce qui dépasse la limite de "
                    f"{duree_max} min. Réponds avec une recette VRAIMENT plus courte, simple et rapide. "
                    f"Le 'temps' doit être <= {duree_max} minutes (par exemple {max(5, duree_max // 3)}-{duree_max} minutes)."
                )
                continue
        if sans_courses:
            manquants = [m for m in (r.get("ingredients_manquants") or []) if not est_assaisonnement(m)]
            if manquants:
                prompt = build_generate_prompt(ingredients, bases, exclusions, mode, duree_max, difficulte_max, parts, eviter_plats, sans_courses, prioriser) + (
                    "\n\nATTENTION : en mode SANS COURSES tu as proposé d'acheter : "
                    + ", ".join(manquants[:5])
                    + ". C'est interdit. Refais une recette avec UNIQUEMENT les ingrédients disponibles, "
                    "et mets 'ingredients_manquants' à une liste VIDE."
                )
                continue
        if not r.get("titre"):
            prompt = prompt + "\n\nLa réponse était incomplète. Fournis une recette complète avec un titre."
            continue
        r.setdefault("parts", parts)
        return r
    raise ValueError("Impossible de générer une recette valide sous les contraintes.")


def chat(body):
    recette = body.get("recette", {})
    messages = body.get("messages", [])  # [{role, content}]
    ingredients = [str(i).strip() for i in body.get("ingredients", []) if str(i).strip()]
    bases = [str(i).strip() for i in body.get("bases", []) if str(i).strip()]
    mode = str(body.get("mode", "gourmand"))
    duree_max = body.get("duree_max")
    duree_max = int(duree_max) if isinstance(duree_max, (int, float)) and duree_max > 0 else None
    difficulte_max = str(body.get("difficulte_max", "difficile"))
    parts = body.get("parts")
    parts = int(parts) if isinstance(parts, (int, float)) and parts > 0 else 2

    c = build_constraints(mode, duree_max, difficulte_max, parts)
    convo = "\n".join(f"{'Utilisateur' if m.get('role')=='user' else 'Chef'}: {m.get('content','')}" for m in messages[-8:])

    prompt = f"""
Recette actuelle : {json.dumps(recette, ensure_ascii=False)}.

On a à la maison : {', '.join(ingredients)}.
Bases du placard : {', '.join(bases)}.
Contraintes : {c}

Discussion récente avec la famille :
{convo}

Le dernier message de l'utilisateur demande une modification de la recette (ingrédient manquant, étape pas claire, plus/moins de parts, changement d'envie…). Adapte entièrement la recette en conséquence, en gardant le même style et en respectant les contraintes.

Réponds en JSON avec EXACTEMENT cette structure (pas de markdown) :
{{{JSON_STRUCT}}}
"""
    raw = _call(prompt, temperature=0.7, deadline=time.time() + GLOBAL_TIMEOUT)
    r = normalize_recette(parse_recette(raw))
    if not r.get("titre"):
        raise ValueError("Réponse malformée")
    return r


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if not DEEPSEEK_API_KEY:
            _send(self, 500, {"error": "Clé DeepSeek absente"})
            return
        path = self.path.split("?")[0]
        try:
            body = _read_body(self)
            _valider_entree(body)
        except BadRequest as e:
            _send(self, 400, {"ok": False, "error": str(e)})
            return
        try:
            if path == "/api/chat":
                r = chat(body)
                _send(self, 200, {"ok": True, "recette": r})
            else:  # /api/recette
                r = generate(body)
                _send(self, 200, {"ok": True, "recette": r})
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8")[:300]
            except Exception:
                pass
            _send(self, 502, {"error": f"DeepSeek HTTP {e.code}: {detail}"})
        except BudgetDepasse:
            _send(self, 504, {"error": "Le temps de génération a dépassé la limite. Réessaie."})
        except Exception as e:
            _send(self, 500, {"error": f"Erreur : {e}"})

    def log_message(self, fmt, *args):
        pass
