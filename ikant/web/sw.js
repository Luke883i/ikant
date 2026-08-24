const CACHE='ikant-s10bis-bootstrap-v1-interactive-liveness-hotfix5-ecf1-3-runtime-v30-foundation-v1-s12-public-v1-s13-pairing-recovery-s13bis-browser-liveness-hotfix-enduser-s14-reactive-s15bis-surface-contract-s16-foundation-enforcement-s16bis';
const ASSETS=['/','/styles.css','/foundation.css','/public-v1.css','/app.js','/conversation.js','/foundation.js','/public-v1.js','/manifest.webmanifest'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
