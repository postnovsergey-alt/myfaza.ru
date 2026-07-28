/**
 * Локальное хранилище ПИН-кода и проверка.
 *
 * Хеш = SHA-256(salt || pin), соль — 16 случайных байт, генерируется
 * при первой установке. Криптографической стойкости для 4-значного PIN
 * это не даёт (перебор на устройстве занимает миллисекунды), но соль
 * защищает от готовых rainbow-таблиц, а хеш — от кражи «в лоб» из
 * localStorage. По сути это UX-барьер, а не защита данных: сами данные
 * лежат на сервере и защищены refresh-токеном.
 */

const KEY_HASH = "myfaza.pin.hash";
const KEY_SALT = "myfaza.pin.salt";
const KEY_ATTEMPTS = "myfaza.pin.attempts";
const KEY_BG_AT = "myfaza.pin.bg_at";

export const PIN_LENGTH = 4;
export const MAX_ATTEMPTS = 5;
/** После стольких минут в фоне снова спрашиваем ПИН. */
export const BG_LOCK_MINUTES = 5;

const toHex = (buf: ArrayBuffer): string =>
  Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

const fromHex = (hex: string): Uint8Array => {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
};

async function hashPin(pin: string, saltHex: string): Promise<string> {
  const salt = fromHex(saltHex);
  const pinBytes = new TextEncoder().encode(pin);
  const combined = new Uint8Array(salt.length + pinBytes.length);
  combined.set(salt);
  combined.set(pinBytes, salt.length);
  const digest = await crypto.subtle.digest("SHA-256", combined);
  return toHex(digest);
}

export function hasPin(): boolean {
  return !!localStorage.getItem(KEY_HASH);
}

export async function setPin(pin: string): Promise<void> {
  if (!/^\d{4}$/.test(pin)) throw new Error("PIN должен быть 4 цифры");
  const saltBytes = crypto.getRandomValues(new Uint8Array(16));
  const salt = toHex(saltBytes.buffer);
  const hash = await hashPin(pin, salt);
  localStorage.setItem(KEY_SALT, salt);
  localStorage.setItem(KEY_HASH, hash);
  localStorage.removeItem(KEY_ATTEMPTS);
}

export function clearPin(): void {
  localStorage.removeItem(KEY_HASH);
  localStorage.removeItem(KEY_SALT);
  localStorage.removeItem(KEY_ATTEMPTS);
  localStorage.removeItem(KEY_BG_AT);
}

/** true — ПИН верный. Обновляет счётчик попыток. */
export async function verifyPin(pin: string): Promise<boolean> {
  const salt = localStorage.getItem(KEY_SALT);
  const stored = localStorage.getItem(KEY_HASH);
  if (!salt || !stored) return false;
  const hash = await hashPin(pin, salt);
  if (hash === stored) {
    localStorage.removeItem(KEY_ATTEMPTS);
    return true;
  }
  const attempts = getAttempts() + 1;
  localStorage.setItem(KEY_ATTEMPTS, String(attempts));
  return false;
}

export function getAttempts(): number {
  const v = localStorage.getItem(KEY_ATTEMPTS);
  return v ? parseInt(v, 10) || 0 : 0;
}

export function attemptsLeft(): number {
  return Math.max(0, MAX_ATTEMPTS - getAttempts());
}

export function markBackgrounded(): void {
  localStorage.setItem(KEY_BG_AT, String(Date.now()));
}

export function clearBackgrounded(): void {
  localStorage.removeItem(KEY_BG_AT);
}

/** true — с момента ухода в фон прошло больше BG_LOCK_MINUTES. */
export function needsLockAfterBackground(): boolean {
  const raw = localStorage.getItem(KEY_BG_AT);
  if (!raw) return false;
  const bgAt = parseInt(raw, 10);
  if (!bgAt) return false;
  const elapsedMin = (Date.now() - bgAt) / 60000;
  return elapsedMin >= BG_LOCK_MINUTES;
}
