self.addEventListener("install", e => {
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  // nothing needed
});

self.addEventListener("fetch", e => {
  // Netzwerk first – kein offline caching nötig
  return fetch(e.request);
});
