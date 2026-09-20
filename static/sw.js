const CACHE_NAME = "sportbit-pwa-v1";

const STATIC_FILES = [
    "/static/manifest.json",
    "/static/icon.svg"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_FILES))
            .then(() => self.skipWaiting())
    );
});


self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            )
        ).then(() => self.clients.claim())
    );
});


self.addEventListener("fetch", event => {
    /*
     * SportBit-pagina's niet cachen.
     *
     * Hierdoor blijven:
     * - statussen
     * - inschrijvingen
     * - events
     *
     * altijd live.
     */

    if (event.request.method !== "GET") {
        return;
    }

    const url = new URL(event.request.url);

    if (url.pathname.startsWith("/static/")) {
        event.respondWith(
            caches.match(event.request).then(cached => {
                return cached || fetch(event.request);
            })
        );
    }
});
