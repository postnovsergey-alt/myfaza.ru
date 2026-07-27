/// <reference lib="webworker" />
/**
 * Service Worker для Web Push. VitePWA работает в injectManifest-режиме
 * и подставляет прекеш через precacheAndRoute.
 *
 * Тексты в payload приходят с бэкенда — уже с учётом discreet_mode.
 */
import { precacheAndRoute } from "workbox-precaching";

declare const self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: Array<{ url: string; revision: string | null }>;
};

precacheAndRoute(self.__WB_MANIFEST);

interface PushPayload {
  title?: string;
  body?: string;
  url?: string;
}

self.addEventListener("push", (event: PushEvent) => {
  let data: PushPayload = { title: "Моя фаза", body: "" };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch {
    /* payload не JSON — используем defaults */
  }
  event.waitUntil(
    self.registration.showNotification(data.title ?? "Моя фаза", {
      body: data.body ?? "",
      badge: "/icon-192.svg",
      icon: "/icon-192.svg",
      data: { url: data.url ?? "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();
  const url = (event.notification.data as { url?: string })?.url ?? "/";
  event.waitUntil(
    (async () => {
      const clients = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      for (const c of clients) {
        if ("focus" in c) {
          await c.focus();
          if ("navigate" in c) await (c as WindowClient).navigate(url);
          return;
        }
      }
      await self.clients.openWindow(url);
    })(),
  );
});

export {};
