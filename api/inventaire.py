#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FrigoMalin — fonction serverless Vercel : inventaire partagé.
L'inventaire est stocké dans le fichier data/inventaire.json du repo GitHub,
donc le MÊME frigo est partagé entre tous les appareils (Patrick & Emeline).

Concurrence : chaque écriture relit le dernier sha et réessaie en cas de
conflit (409) pour éviter de perdre une modification concurrente.
100% stdlib.
"""
import base64
import json
import os
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "StarPro94/frigomalin")
PATH = "data/inventaire.json"
API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{PATH}"
MAX_RETRY = 10


def _hdr():
    return {
        "Authorization": "token " + GITHUB_TOKEN,
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "FrigoMalin",
    }


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


def _gh(method, url, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_hdr(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") or "{}"
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def _read():
    status, body = _gh("GET", API)
    if status == 404:
        return {"ingredients": []}, None
    if status != 200:
        raise RuntimeError(f"GitHub lecture HTTP {status}")
    sha = body.get("sha")
    try:
        content = base64.b64decode(body.get("content", "")).decode("utf-8")
        data = json.loads(content)
    except Exception:
        data = {"ingredients": []}
    if not isinstance(data, dict) or not isinstance(data.get("ingredients"), list):
        data = {"ingredients": []}
    return data, sha


def _write(data, sha):
    payload = {
        "message": "🍳 FrigoMalin: mise à jour inventaire",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii"),
        "sha": sha,
    }
    status, body = _gh("PUT", API, payload)
    if status not in (200, 201):
        raise RuntimeError(status)
    return data


def update(fn):
    """Applique fn(ingredients)->ingredients avec retry sur conflit (409)."""
    if not GITHUB_TOKEN:
        raise RuntimeError("NO_TOKEN")
    last_err = None
    for _ in range(MAX_RETRY):
        data, sha = _read()
        new_list = fn(data["ingredients"])
        data["ingredients"] = new_list
        try:
            return _write(data, sha)
        except RuntimeError as e:
            code = str(e)
            if code == "409":
                last_err = "conflit, on relit et on réessaie"
                time.sleep(0.3)
                continue
            raise RuntimeError(f"GitHub écriture : {code}")
    raise RuntimeError(f"Conflits répétés : {last_err}")


def norm(s):
    return str(s).lower().replace("œ", "oe").replace("æ", "ae").strip()


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            data, _ = _read()
            _send(self, 200, data)
        except RuntimeError as e:
            if str(e) == "NO_TOKEN":
                _send(self, 500, {"error": "GITHUB_TOKEN absent sur Vercel"})
            else:
                _send(self, 502, {"error": f"Erreur lecture inventaire : {e}"})
        except Exception as e:
            _send(self, 502, {"error": f"Erreur lecture : {e}"})

    def do_POST(self):
        body = _read_body(self)
        action = body.get("action", "ajouter")

        # --- Ajout / mise à jour ---
        if action == "ajouter":
            nom = str(body.get("nom", "")).strip()
            if not nom:
                _send(self, 400, {"error": "nom manquant"})
                return
            qty = str(body.get("quantite", "")).strip() or ""
            zone = body.get("zone") == "garde-manger" and "garde-manger" or "frigo"
            key = norm(nom)

            def apply(items):
                for ing in items:
                    if norm(ing.get("nom", "")) == key:
                        ing["quantite"] = qty or ing.get("quantite", "")
                        ing["zone"] = zone
                        return items
                items.append({"nom": nom, "quantite": qty, "zone": zone})
                return items

            try:
                res = update(apply)
                _send(self, 200, res)
            except RuntimeError as e:
                if str(e) == "NO_TOKEN":
                    _send(self, 500, {"error": "GITHUB_TOKEN absent sur Vercel"})
                else:
                    _send(self, 502, {"error": f"Erreur ajout : {e}"})
            except Exception as e:
                _send(self, 502, {"error": f"Erreur ajout : {e}"})
            return

        # --- Suppression par nom ---
        if action == "supprimer":
            nom = str(body.get("nom", "")).strip()
            if not nom:
                _send(self, 400, {"error": "nom manquant"})
                return
            key = norm(nom)
            def apply(items):
                return [i for i in items if norm(i.get("nom", "")) != key]
            try:
                res = update(apply)
                _send(self, 200, res)
            except RuntimeError as e:
                _send(self, 502, {"error": f"Erreur suppression : {e}"})
            except Exception as e:
                _send(self, 502, {"error": f"Erreur suppression : {e}"})
            return

        # --- Vider tout ---
        if action == "vider":
            def apply(items):
                return []
            try:
                res = update(apply)
                _send(self, 200, res)
            except RuntimeError as e:
                _send(self, 502, {"error": f"Erreur vidage : {e}"})
            except Exception as e:
                _send(self, 502, {"error": f"Erreur vidage : {e}"})
            return

        _send(self, 400, {"error": "action inconnue"})

    def log_message(self, fmt, *args):
        pass
