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

MODES = {
    "healthy": "healthy : léger, équilibré, peu calorique",
    "gourmand": "gourmand : réconfortant, savoureux, généreux",
    "gras": "gras : indulgente, riche, réconfortante",
    "sportif": "sportif : riche en protéines, adapté à l'effort",
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
    for champ in ("ingredients", "bases", "exclusions", "messages"):
        v = body.get(champ)
        if v is not None and not isinstance(v, list):
            raise BadRequest("Le champ '%s' doit être une liste." % champ)
    for champ in ("duree_max", "parts"):
        v = body.get(champ)
        if v is not None and not isinstance(v, (int, float)):
            raise BadRequest("Le champ '%s' doit être un nombre." % champ)


def _call(prompt, temperature=0.8):
    """Appelle DeepSeek avec retry automatique (fiabilité au quotidien).

    On retente jusqu'à 3 fois sur les erreurs transitoires : timeout réseau,
    erreur de connexion ou réponses 5xx/429 de l'API — les pannes passagères
    de DeepSeek ne font plus échouer la requête de l'utilisateur.
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
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
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
        if attempt < 2:
            time.sleep(1 + attempt)  # backoff court : 1s puis 2s
    raise last if last else Exception("Échec de l'appel DeepSeek")


def parse_recette(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Réponse IA vide")
    raw2 = raw.strip()
    # retire un éventuel bloc de code markdown ```json ... ```
    if raw2.startswith("```"):
        raw2 = re.sub(r"^```[a-zA-Z]*\s*", "", raw2)
        raw2 = re.sub(r"\s*```\s*$", "", raw2)
    s = raw2.find("{")
    e = raw2.rfind("}")
    if s == -1 or e == -1 or e <= s:
        raise ValueError("Réponse IA malformée")
    return json.loads(raw2[s:e + 1])


def minutes_from(temps):
    """Extrait le nombre de minutes d'une chaîne de temps. Retourne None si inconnu."""
    t = str(temps or "").lower()
    if "heure" in t or "h " in t or t.endswith("h"):
        h = re.search(r"(\d+(?:[.,]\d+)?)\s*h", t)
        if h:
            return int(float(h.group(1).replace(",", ".")) * 60)
    m = re.search(r"(\d+)\s*min", t)
    if m:
        return int(m.group(1))
    d = re.search(r"(\d+)\s*[hdj]", t)
    if d:
        return int(d.group(1)) * 60
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


def build_generate_prompt(ingredients, bases, exclusions, mode, duree_max, difficulte_max, parts):
    dispo = ", ".join(ingredients) if ingredients else "AUCUN renseigné"
    tout = ", ".join(bases) if bases else ""
    excl = ""
    if exclusions:
        excl = (f"\nIMPORTANT : on n'a PAS à la maison (ne les cite ni comme utilisé ni comme manquant) : "
                f"{', '.join(exclusions)}. Adapte complètement.")
    bases_s = f"\nBases qu'on a presque toujours (à utiliser si besoin, sans les lister comme manquants) : {tout}." if tout else ""
    c = build_constraints(mode, duree_max, difficulte_max, parts)
    return f"""
Contexte : je cuisine pour ma famille avec ce que j'ai.
Ingrédients disponibles : {dispo}.{bases_s}{excl}

Contraintes (à respecter IMPÉRATIVEMENT) : {c}

Réponds en JSON avec EXACTEMENT cette structure (pas de markdown, pas de texte autour) :
{{{JSON_STRUCT}}}
"""


def generate(body):
    ingredients = [str(i).strip() for i in body.get("ingredients", []) if str(i).strip()]
    bases = [str(i).strip() for i in body.get("bases", []) if str(i).strip()]
    exclusions = [str(i).strip() for i in body.get("exclusions", []) if str(i).strip()]
    mode = str(body.get("mode", "gourmand"))
    duree_max = body.get("duree_max")
    duree_max = int(duree_max) if isinstance(duree_max, (int, float)) and duree_max > 0 else None
    difficulte_max = str(body.get("difficulte_max", "difficile"))
    parts = body.get("parts")
    parts = int(parts) if isinstance(parts, (int, float)) and parts > 0 else 2

    # on essaie jusqu'à 3 fois, en durcissant la consigne durée si dépassé
    prompt = build_generate_prompt(ingredients, bases, exclusions, mode, duree_max, difficulte_max, parts)
    for attempt in range(3):
        raw = _call(prompt)
        r = parse_recette(raw)
        if duree_max:
            mn = minutes_from(r.get("temps"))
            if mn is not None and mn > duree_max:
                prompt = build_generate_prompt(ingredients, bases, exclusions, mode, duree_max, difficulte_max, parts) + (
                    f"\n\nATTENTION : la recette précedente durait {r.get('temps')}, ce qui dépasse la limite de "
                    f"{duree_max} min. Réponds avec une recette VRAIMENT plus courte, simple et rapide. "
                    f"Le 'temps' doit être <= {duree_max} minutes (par exemple {max(5, duree_max // 3)}-{duree_max} minutes)."
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
    raw = _call(prompt, temperature=0.7)
    r = parse_recette(raw)
    if not r.get("titre"):
        raise ValueError("Réponse malformée")
    r.setdefault("parts", parts)
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
        except Exception as e:
            _send(self, 500, {"error": f"Erreur : {e}"})

    def log_message(self, fmt, *args):
        pass
