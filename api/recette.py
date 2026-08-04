#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FrigoMalin — fonction serverless Vercel : génération de recette par DeepSeek.

Sert UNIQUEMENT l'endpoint POST /api/recette. La clé DeepSeek est lue depuis
les variables d'environnement Vercel (jamais exposée au navigateur).
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
    "healthy": "healthy / léger, équilibré, peu calorique",
    "gourmand": "gourmand / réconfortant, savoureux, généreux",
    "gras": "gras / gras, indulgente, junk sympa",
    "sportif": "sportif / riche en protéines et énergie, adapté à l'effort",
}
DURATIONS = {"rapide": "~15 min", "moyen": "~30 min", "long": "~60 min et plus"}


def _send(handler, code, obj):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_body(handler):
    try:
        length = int(handler.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        return json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
    except Exception:
        return {}


def build_prompt(ingredients, mode, duration):
    dispo = ", ".join(ingredients) if ingredients else "AUCUN (propose un plat à partir de rien / bases de placard classiques)"
    return f"""
Contexte : je dois cuisiner avec ce que j'ai. Ingrédients disponibles : {dispo}.

Style souhaité : {MODES.get(mode, MODES['gourmand'])}.
Temps de préparation souhaité : {DURATIONS.get(duration, DURATIONS['moyen'])}.

Réponds en JSON avec EXACTEMENT cette structure (pas de markdown, pas de texte autour) :
{{
  "titre": "Nom de la recette",
  "style": "une ligne décrivant le style",
  "temps": "durée estimée",
  "difficulte": "Facile | Moyen | Difficile",
  "ingredients_dispo_utilises": ["liste des ingrédients utilisés"],
  "ingredients_manquants": ["liste des ingrédients à prévoir/ajouter", "ou liste vide"],
  "etapes": ["étape 1", "étape 2", "..."],
  "calories_estimees": "estimation en kcal",
  "astuce": "un petit conseil de chef"
}}
"""


def call_deepseek(prompt):
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": (
                "Tu es un chef cuisinier français créatif et pragmatique. "
                "Tu proposes des recettes réalisables avec les ingrédients disponibles. "
                "Tu réponds TOUJOURS en JSON valide, sans texte avant ni après."
            )},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2000,
        "temperature": 0.8,
        "stream": False,
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + DEEPSEEK_API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def parse_recette(raw):
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Réponse IA malformée (pas de JSON trouvé)")
    return json.loads(raw[start:end + 1])


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if not DEEPSEEK_API_KEY:
            _send(self, 500, {"error": "Clé DeepSeek absente. Configure DEEPSEEK_API_KEY sur Vercel."})
            return
        body = _read_body(self)
        ingredients = body.get("ingredients")
        if not isinstance(ingredients, list):
            ingredients = []
        ingredients = [str(i).strip() for i in ingredients if str(i).strip()]
        mode = str(body.get("mode", "gourmand"))
        duration = str(body.get("duree", "moyen"))
        try:
            raw = call_deepseek(build_prompt(ingredients, mode, duration))
            recette = parse_recette(raw)
            _send(self, 200, {"ok": True, "recette": recette})
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8")[:300]
            except Exception:
                pass
            _send(self, 502, {"error": f"DeepSeek HTTP {e.code}: {detail}"})
        except Exception as e:
            _send(self, 500, {"error": f"Erreur génération : {e}"})

    def log_message(self, fmt, *args):
        pass
