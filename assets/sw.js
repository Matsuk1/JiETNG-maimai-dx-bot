// JiETNG Admin Panel Service Worker
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));

// 收到 Web Push 时显示系统通知
self.addEventListener('push', e => {
    let data = { title: 'JiETNG Admin', body: '' };
    if (e.data) {
        try { data = e.data.json(); } catch (_) { data.body = e.data.text(); }
    }
    e.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            tag: 'jietng-error',
            renotify: true
        })
    );
});

// 点击通知时打开 admin panel 的 notifications tab
self.addEventListener('notificationclick', e => {
    e.notification.close();
    e.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
            const target = '/admin/panel#notifications';
            for (const client of list) {
                if (client.url.includes('/admin/panel')) {
                    client.focus();
                    client.postMessage({ type: 'OPEN_TAB', tab: 'notifications' });
                    return;
                }
            }
            clients.openWindow(target);
        })
    );
});
