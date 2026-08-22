const CACHE='ikant-s10bis-bootstrap-v1-interactive-liveness-hotfix5-ecf1-3-runtime-v30';
const ASSETS=['/','/styles.css','/app.js','/conversation.js','/manifest.webmanifest'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
