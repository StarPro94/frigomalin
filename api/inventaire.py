#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FrigoMalin — fonction serverless Vercel : inventaire partagé (V2 Redis).
L'inventaire est stocké dans Vercel KV (Upstash Redis) → MÊME frigo sur tous
les appareils (Patrick & Emeline), avec opérations ATOMIQUES (aucune donnée
ne peut se perdre, même en écritures simultanées).

Commandes Redis REST utilisées :
  - LRANGE inventaire 0 -1   → lire la liste
  - RPUSH inventaire <json>  → ajouter (atomique)
  - LREM  inventaire <n> <v> → supprimer (atomique)
  - DEL   inventaire         → vider (atomique)

La clé est une liste d'objets JSON (les ingrédients). 100% stdlib.
"""
import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

KV_URL = os.environ.get("KV_REST_API_URL", "").rstrip("/")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")
KEY = "inventaire"


def _send(h, code, obj):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    h.send_response(code)
    h.send_header("Content-Type", "application/json; charset=utf-8")
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


def _kv(*parts):
    """Exécute une commande Redis REST. Retourne le dict JSON de réponse."""
    url = KV_URL + "/" + "/".join(parts)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + KV_TOKEN,
        "User-Agent": "FrigoMalin",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def _is_ready():
    return bool(KV_URL and KV_TOKEN)


def _read_list():
    """Retourne la liste des ingrédients (objets dict) depuis Redis."""
    try:
        res = _kv("lrange", KEY, "0", "-1")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError("KV_AUTH")
        raise
    raw = res.get("result") or []
    items = []
    for el in raw:
        try:
            v = json.loads(el)
            if isinstance(v, dict):
                items.append(v)
        except Exception:
            continue
    return items


def _get_all():
    return {"ingredients": _read_list()}


def _add(ing):
    """Ajoute un ingrédient. Si un même nom existe déjà, met à jour quantité/zone ;
    sinon RPUSH atomique. Retourne la nouvelle liste."""
    items = _read_list()
    key = norm(ing["nom"])
    replaced = False
    for it in items:
        if norm(it.get("nom", "")) == key:
            it["quantite"] = ing["quantite"] or it.get("quantite", "")
            it["zone"] = ing["zone"]
            replaced = True
            break
    if not replaced:
        # Ajout atomique (RPUSH) — jamais perdu même en simultané
        _kv("rpush", KEY, json.dumps(ing, ensure_ascii=False))
        items = _read_list()
        return items
    # Mise à jour d'un existant : reconstruit toute la liste (rare)
    _kv("del", KEY)
    for it in items:
        _kv("rpush", KEY, json.dumps(it, ensure_ascii=False))
    return items


def _remove(nom):
    """Supprime par nom (LREM atomique). Retourne la nouvelle liste."""
    key = norm(nom)
    items = _read_list()
    to_remove = [it for it in items if norm(it.get("nom", "")) == key]
    for it in to_remove:
        _kv("lrem", KEY, "1", json.dumps(it, ensure_ascii=False))
    return _read_list()


def _clear():
    """Vide tout (DEL atomique)."""
    _kv("del", KEY)
    return []


def norm(s):
    return str(s).lower().replace("œ", "oe").replace("æ", "ae").strip()


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if not _is_ready():
            _send(self, 500, {"error": "KV non configuré (KV_REST_API_URL/TOKEN absents)"})
            return
        try:
            _send(self, 200, _get_all())
        except Exception as e:
            _send(self, 502, {"error": f"Erreur lecture : {e}"})

    def do_POST(self):
        if not _is_ready():
            _send(self, 500, {"error": "KV non configuré (KV_REST_API_URL/TOKEN absents)"})
            return
        body = _read_body(self)
        action = body.get("action", "ajouter")
        try:
            if action == "ajouter":
                nom = str(body.get("nom", "")).strip()
                if not nom:
                    _send(self, 400, {"error": "nom manquant"})
                    return
                ing = {
                    "nom": nom,
                    "quantite": str(body.get("quantite", "")).strip() or "",
                    "zone": body.get("zone") == "garde-manger" and "garde-manger" or "frigo",
                }
                _send(self, 200, {"ingredients": _add(ing)})
            elif action == "supprimer":
                nom = str(body.get("nom", "")).strip()
                if not nom:
                    _send(self, 400, {"error": "nom manquant"})
                    return
                _send(self, 200, {"ingredients": _remove(nom)})
            elif action == "vider":
                _send(self, 200, {"ingredients": _clear()})
            else:
                _send(self, 400, {"error": "action inconnue"})
        except RuntimeError as e:
            if str(e) == "KV_AUTH":
                _send(self, 500, {"error": "Token KV invalide"})
            else:
                _send(self, 502, {"error": f"Erreur : {e}"})
        except Exception as e:
            _send(self, 502, {"error": f"Erreur : {e}"})

    def log_message(self, fmt, *args):
        pass
