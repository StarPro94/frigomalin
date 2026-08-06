#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FrigoMalin — fonction serverless Vercel : chat de modification de recette.

POST /api/chat : discute avec l'IA de la recette pour la modifier.
Stateless : on passe la recette + l'historique, on reçoit la recette adaptée.
100% stdlib.

V3.37 — robustesse alignée sur api/recette.py :
- entrée validée (JSON malformé, messages/ingredients mal typés, mode inconnu
  → HTTP 400 clair, plus d'appel IA inutile ni de 500) ;
- parsing IA du premier objet JSON équilibré (accolades dans les chaînes ignorées) ;
- retry automatique (×3, backoff court) sur timeout / coupure / 5xx / 429 ;
- budget temporel global (40 s/appel, 48 s au total) → HTTP 504 clair ;
- réponse réassainie (listes toujours des listes, parts bornées 1-24).
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
# quelques dizaines de secondes. On borne génération+retry pour rester sous la
# limite et rendre une 504 claire au lieu d'un échec muet.
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
    "Tu es le chef de l'office de Patrick et Emeline. Tu adaptes la recette selon "
    "les remarques de la famille, en respectant strictement les contraintes "
    "(durée max, difficulté max, style, nombre de parts). "
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
    '"calories_estimees": "...",'
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
    """Vérifie les champs connus : mode connu, listes et types corrects.

    Renvoie 400 avec un message clair plutôt que d'appeler DeepSeek avec
    des valeurs par défaut silencieuses (le bug silencieux coûte un appel IA
    inutile et masque les vrais problèmes).
    """
    mode = body.get("mode", "gourmand")
    if mode not in MODES:
        raise BadRequest(
            "Mode inconnu : %r. Modes possibles : %s."
            % (mode, ", ".join(sorted(MODES)))
        )
    for champ in ("ingredients", "bases", "messages"):
        v = body.get(champ)
        if v is not None and not isinstance(v, list):
            raise BadRequest("Le champ '%s' doit être une liste." % champ)
    if body.get("recette") is not None and not isinstance(body.get("recette"), dict):
        raise BadRequest("Le champ 'recette' doit être un objet.")
    for champ in ("duree_max", "parts"):
        v = body.get(champ)
        if v is not None and not isinstance(v, (int, float)) or isinstance(v, bool):
            raise BadRequest("Le champ '%s' doit être un nombre." % champ)


class BudgetDepasse(Exception):
    """Le budget de temps global est épuisé → réponse HTTP 504."""


def _call(prompt, deadline=None):
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
        "temperature": 0.7,
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
    """Force un champ en liste de chaînes : tolère liste, chaîne unique…"""
    if v is None or v == "":
        return []
    if isinstance(v, str):
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
    """Réassainit la recette renvoyée par l'IA pour que la page ne casse jamais."""
    if not isinstance(r, dict):
        raise ValueError("Réponse IA non objet")
    r["ingredients_dispo_utilises"] = _as_list(r.get("ingredients_dispo_utilises"))
    r["ingredients_manquants"] = _as_list(r.get("ingredients_manquants"))
    r["etapes"] = _as_list(r.get("etapes"), split_phrases=True)
    for champ in ("titre", "style", "temps", "difficulte", "calories_estimees", "astuce"):
        v = r.get(champ)
        r[champ] = (str(v).strip() if v is not None else "")
        if champ == "difficulte" and r["difficulte"]:
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


def build_constraints(mode, duree_max, difficulte_max, parts):
    lines = []
    if mode in MODES:
        lines.append(f"Type de plat : {MODES[mode]}. RESPECTE ce style.")
    if isinstance(duree_max, int) and duree_max > 0:
        lines.append(f"Durée totale MAXIMALE : {duree_max} minutes (ne jamais dépasser).")
    if difficulte_max in DIFFS:
        lines.append(f"Difficulté MAXIMALE : {DIFFS[difficulte_max]}.")
    if isinstance(parts, int) and parts > 0:
        lines.append(f"Recette pour {parts} personne(s), quantités adaptées.")
    return "\n".join(lines) if lines else ""


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
        try:
            body = _read_body(self)
            _valider_entree(body)
        except BadRequest as e:
            _send(self, 400, {"ok": False, "error": str(e)})
            return
        try:
            recette = body.get("recette", {})
            messages = body.get("messages", [])
            ingredients = [str(i).strip() for i in body.get("ingredients", []) if str(i).strip()]
            bases = [str(i).strip() for i in body.get("bases", []) if str(i).strip()]
            mode = str(body.get("mode", "gourmand"))
            duree_max = body.get("duree_max")
            duree_max = int(duree_max) if isinstance(duree_max, (int, float)) and duree_max > 0 else None
            difficulte_max = str(body.get("difficulte_max", "difficile"))
            parts = body.get("parts")
            parts = int(parts) if isinstance(parts, (int, float)) and parts > 0 else 2

            c = build_constraints(mode, duree_max, difficulte_max, parts)
            convo_lines = []
            for m in messages[-8:]:
                if not isinstance(m, dict):
                    continue
                role = m.get("role")
                convo_lines.append(
                    f"{'Famille' if role == 'user' else 'Chef'}: {m.get('content', '')}"
                )
            convo = "\n".join(convo_lines)
            prompt = f"""
Recette actuelle : {json.dumps(recette, ensure_ascii=False)}.

On a à la maison : {', '.join(ingredients)}.
Bases du placard : {', '.join(bases)}.
Contraintes : {c}

Discussion récente :
{convo}

Adapte entièrement la recette selon le dernier message (ingrédient manquant, étape peu claire, plus/moins de parts, changement d'envie…), en gardant le style et en respectant les contraintes.

Réponds en JSON avec EXACTEMENT cette structure (pas de markdown) :
{{{JSON_STRUCT}}}
"""
            raw = _call(prompt, deadline=time.time() + GLOBAL_TIMEOUT)
            r = normalize_recette(parse_recette(raw))
            if not r.get("titre"):
                raise ValueError("Réponse malformée")
            r.setdefault("parts", parts)
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
