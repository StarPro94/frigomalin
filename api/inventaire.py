#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FrigoMalin — fonction serverless Vercel : inventaire partagé.
L'inventaire est stocké dans le fichier data/inventaire.json du repo GitHub,
donc le MÊME frigo est partagé entre tous les appareils (Patrick & Emeline).
100% stdlib.
"""
import base64
import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "StarPro94/frigomalin")
PATH = "data/inventaire.json"
API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{PATH}"


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


def _gh_request(method, url, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_hdr(), method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read().decode("utf-8") or "{}")


def _read_inventaire():
    """Lit l'inventaire depuis GitHub. Retourne (data, sha)."""
    status, body = _gh_request("GET", API)
    if status == 404:
        return {"ingredients": []}, None
    if status != 200:
        raise RuntimeError(f"GitHub lecture HTTP {status}")
    sha = body.get("sha")
    content = base64.b64decode(body.get("content", "")).decode("utf-8")
    try:
        data = json.loads(content)
    except Exception:
        data = {"ingredients": []}
    if not isinstance(data, dict) or "ingredients" not in data:
        data = {"ingredients": []}
    return data, sha


def _write_inventaire(data, sha):
    """Écrit l'inventaire sur GitHub (commit). Retourne la nouvelle data."""
    payload = {
        "message": "🍳 FrigoMalin: mise à jour inventaire",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii"),
        "sha": sha,
    }
    status, body = _gh_request("PUT", API, payload)
    if status not in (200, 201):
        raise RuntimeError(f"GitHub écriture HTTP {status}: {json.dumps(body)[:200]}")
    return data


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
        if not GITHUB_TOKEN:
            _send(self, 500, {"error": "GITHUB_TOKEN absent sur Vercel"})
            return
        try:
            data, _ = _read_inventaire()
            _send(self, 200, data)
        except Exception as e:
            _send(self, 502, {"error": f"Erreur lecture inventaire : {e}"})

    def do_POST(self):
        if not GITHUB_TOKEN:
            _send(self, 500, {"error": "GITHUB_TOKEN absent sur Vercel"})
            return
        path = self.path.split("?")[0]
        body = _read_body(self)
        nom = str(body.get("nom", "")).strip()
        if not nom:
            _send(self, 400, {"error": "nom manquant"})
            return
        qty = str(body.get("quantite", "")).strip() or ""
        zone = body.get("zone") == "garde-manger" and "garde-manger" or "frigo"
        try:
            data, sha = _read_inventaire()
            key = norm(nom)
            found = None
            for ing in data["ingredients"]:
                if norm(ing.get("nom", "")) == key:
                    found = ing
                    break
            if found:
                found["quantite"] = qty or found.get("quantite", "")
                found["zone"] = zone
            else:
                data["ingredients"].append({"nom": nom, "quantite": qty, "zone": zone})
            _write_inventaire(data, sha)
            _send(self, 200, data)
        except Exception as e:
            _send(self, 502, {"error": f"Erreur ajout : {e}"})

    def do_DELETE(self):
        if not GITHUB_TOKEN:
            _send(self, 500, {"error": "GITHUB_TOKEN absent sur Vercel"})
            return
        path = self.path.split("?")[0]
        try:
            idx = int(path.rsplit("/", 1)[-1])
        except ValueError:
            _send(self, 400, {"error": "index invalide"})
            return
        try:
            data, sha = _read_inventaire()
            if 0 <= idx < len(data["ingredients"]):
                del data["ingredients"][idx]
            _write_inventaire(data, sha)
            _send(self, 200, data)
        except Exception as e:
            _send(self, 502, {"error": f"Erreur suppression : {e}"})

    def log_message(self, fmt, *args):
        pass
