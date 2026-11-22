// DisasterOps offline shell: lets the citizen app open with mobile data OFF,
// so GPS can still be read and an SMS with coordinates can be sent to the gateway.
const CACHE = 'disasterops-v1';
const SHELL = [
  '/',
  'https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache =>
      Promise.all(SHELL.map(url =>
        cache.add(new Request(url, { mode: url.startsWith('/') ? 'same-origin' : 'no-cors' })).catch(() => {})
      ))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.pathname.startsWith('/api/')) return;            // live data: never cache
  if (url.hostname.includes('tile.openstreetmap.org')) return;

  // Network first, fall back to cache (keeps the app fresh online, usable offline)
  event.respondWith(
    fetch(req)
      .then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: req.mode === 'navigate' })
        .then(hit => hit || (req.mode === 'navigate' ? caches.match('/') : undefined)))
  );
});
