/**
 * Service Worker for SecureGuard Fraud Detection PWA
 * Provides offline functionality and push notifications
 */

const CACHE_NAME = 'secureguard-fraud-detection-v1';
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/css/professional.css',
    '/static/css/dashboard.css',
    '/static/css/forms.css',
    '/static/css/results.css',
    '/static/css/enhanced-modern.css',
    '/static/css/enterprise-grade.css',
    '/static/js/real_time_analytics.js',
    '/form_basic',
    '/form_advanced',
    '/analytics',
    '/health'
];

// Install event
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch event
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                if (response) {
                    return response;
                }

                // Important: Clone the request
                const fetchRequest = event.request.clone();

                return fetch(fetchRequest).then((response) => {
                    // Check if valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }

                    // Important: Clone the response
                    const responseToCache = response.clone();

                    caches.open(CACHE_NAME)
                        .then((cache) => {
                            cache.put(event.request, responseToCache);
                        });

                    return response;
                });
            })
    );
});

// Activate event
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Push notification event
self.addEventListener('push', (event) => {
    const options = {
        body: event.data ? event.data.text() : 'New fraud alert detected!',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View Details',
                icon: '/static/images/checkmark.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/images/xmark.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('SecureGuard Fraud Alert', options)
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'explore') {
        // Open the app to analytics page
        event.waitUntil(
            clients.openWindow('/analytics')
        );
    } else if (event.action === 'close') {
        // Just close the notification
        event.notification.close();
    } else {
        // Default action - open the app
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Background sync event
self.addEventListener('sync', (event) => {
    if (event.tag === 'fraud-analysis-sync') {
        event.waitUntil(syncFraudAnalysis());
    }
});

async function syncFraudAnalysis() {
    try {
        // Sync any pending fraud analysis data
        const cache = await caches.open('fraud-data-cache');
        const pendingRequests = await cache.keys();

        for (const request of pendingRequests) {
            try {
                await fetch(request);
                await cache.delete(request);
            } catch (error) {
                console.log('Sync failed for request:', request.url);
            }
        }
    } catch (error) {
        console.log('Background sync failed:', error);
    }
}