/**
 * Клиент Web Push. Знает, как подписаться и отписаться от пушей,
 * а также детектирует ограничения iOS Safari (см. DESIGN-SPEC 9.3).
 */

import { api } from "@/api/client";

export type PushCapability =
  | "unsupported"      // браузер вообще без Push API
  | "ios-needs-pwa"    // Safari iOS, не установлено как PWA
  | "denied"           // разрешение отклонено
  | "supported";       // всё готово к подписке

export function detectCapability(): PushCapability {
  if (typeof window === "undefined") return "unsupported";
  const isIOS =
    /iPad|iPhone|iPod/.test(navigator.userAgent) &&
    !("MSStream" in window);
  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    // @ts-expect-error — Safari navigator.standalone
    Boolean(window.navigator.standalone);

  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    if (isIOS && !isStandalone) return "ios-needs-pwa";
    return "unsupported";
  }
  if (Notification.permission === "denied") return "denied";
  return "supported";
}

function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const buffer = new ArrayBuffer(raw.length);
  const arr = new Uint8Array(buffer);
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr as Uint8Array<ArrayBuffer>;
}

export async function subscribe(): Promise<PushSubscription | null> {
  const reg = await navigator.serviceWorker.ready;
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return null;

  const { public_key } = await api.get<{ public_key: string }>("/push/vapid-key");
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key),
  });
  const json = sub.toJSON();
  await api.post("/push/subscribe", {
    endpoint: json.endpoint,
    keys: json.keys,
  });
  return sub;
}

export async function unsubscribe(): Promise<void> {
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  if (!sub) return;
  await api.post("/push/unsubscribe", { endpoint: sub.endpoint });
  await sub.unsubscribe();
}

export async function isSubscribed(): Promise<boolean> {
  if (!("serviceWorker" in navigator)) return false;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  return sub !== null;
}
