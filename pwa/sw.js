const CACHE='dongnae-shell-v1';
const STATIC=['/offline.html','/pwa/icon-192.png','/pwa/icon-512.png','/pwa/icon-180.png','/pwa/icon-maskable.png'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(STATIC)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('dongnae-shell-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);if(url.origin!==self.location.origin||event.request.method!=='GET')return;
 if(event.request.mode==='navigate'){event.respondWith(fetch(event.request).catch(()=>caches.match('/offline.html')));return;}
 if(STATIC.includes(url.pathname)){event.respondWith(caches.match(event.request).then(hit=>hit||fetch(event.request)));}
 // Never store sessions, uploads, generated media, login pages, or API responses.
});
