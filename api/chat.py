#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FrigoMalin — fonction serverless Vercel : chat de modification de recette.

POST /api/chat : discute avec l'IA de la recette pour la modifier.
Stateless : on passe la recette + l'historique, on reçoit la recette adaptée.
100% stdlib.
"""
import json
import os
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


def _read_body(h):
    try:
        length = int(h.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        return json.loads(h.rfile.read(length).decode("utf-8") or "{}")
    except Exception:
        return {}


def _call(prompt):
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
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def parse_recette(raw):
    raw = raw.strip()
    s = raw.find("{")
    e = raw.rfind("}")
    if s == -1 or e == -1 or e <= s:
        raise ValueError("Réponse IA malformée")
    return json.loads(raw[s:e + 1])


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
        body = _read_body(self)
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
            convo = "\n".join(f"{'Famille' if m.get('role')=='user' else 'Chef'}: {m.get('content','')}" for m in messages[-8:])
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
            raw = _call(prompt)
            r = parse_recette(raw)
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
        except Exception as e:
            _send(self, 500, {"error": f"Erreur : {e}"})

    def log_message(self, fmt, *args):
        pass
