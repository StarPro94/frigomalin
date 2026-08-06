/* FrigoMalin — service worker : cache de l'app pour un démarrage instantané et un usage hors-ligne.
   L'API (/api/recette) n'est volontairement PAS mise en cache : elle doit toujours être fraîche. */
const CACHE = "frigomalin-v4";
const ASSETS = ["/", "/index.html", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return; // toujours en réseau (fraîcheur)
  if (url.pathname.startsWith("/api")) return; // toujours en réseau (fraîcheur)

  // Cache d'abord, réseau en secours (hors-ligne : on sert la copie).
  e.respondWith(
    caches.match(e.request).then((hit) => {
      if (hit) return hit;
      return fetch(e.request)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copy));
          }
          return res;
        })
        .catch(() => caches.match("/index.html"));
    })
  );
});
