// The offline cache contains only the shared UI shell. Private requests use the network.
const CACHE = "disasterops-phase0-v1";
const SHELL = ["/", "/app.js", "/styles.css"];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith("disasterops-") && key !== CACHE).map(key => caches.delete(key)),
  )).then(() => self.clients.claim()));
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin ||
      url.search || !SHELL.includes(url.pathname)) return;
  event.respondWith(fetch(request).then(async response => {
    if (response.ok) {
      try {
        const cache = await caches.open(CACHE);
        await cache.put(request, response.clone());
      } catch {
        // Storage availability does not affect the online response.
      }
    }
    return response;
  }).catch(async () => (await caches.match(request, { cacheName: CACHE })) || Response.error()));
});
