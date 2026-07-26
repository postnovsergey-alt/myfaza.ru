/**
 * Минимальный i18n без библиотеки.
 *
 * Поддержка ICU-like плюралов вида
 *   "{n, plural, one {# день} few {# дня} other {# дней}}"
 * — небольшой парсер вручную. Русские правила: one|few|many|other.
 *
 * Никакие строки интерфейса не должны появляться в коде компонентов.
 */

import ru from "./ru.json";

type Dict = Record<string, string>;

const catalogs: Record<string, Dict> = { ru };
let current = "ru";

const RU_PLURAL = new Intl.PluralRules("ru");

function pluralize(n: number, forms: Record<string, string>): string {
  const cat = RU_PLURAL.select(n);
  const chosen = forms[cat] ?? forms.other ?? "";
  return chosen.replace("#", String(n));
}

/**
 * Разбор ICU-подобного шаблона руками. Плюрал имеет вложенные фигурные
 * скобки, поэтому регулярку через простой lookahead написать нельзя —
 * бежим по строке с учётом баланса скобок.
 */
function applyIcu(template: string, vars: Record<string, unknown>): string {
  let out = "";
  let i = 0;
  while (i < template.length) {
    const ch = template[i];
    if (ch !== "{") {
      out += ch;
      i++;
      continue;
    }
    // ищем парную закрывающую с учётом вложенности
    let depth = 1;
    let j = i + 1;
    while (j < template.length && depth > 0) {
      if (template[j] === "{") depth++;
      else if (template[j] === "}") depth--;
      if (depth > 0) j++;
    }
    const inner = template.slice(i + 1, j);
    out += renderPlaceholder(inner, vars);
    i = j + 1;
  }
  return out;
}

function renderPlaceholder(inner: string, vars: Record<string, unknown>): string {
  const comma = inner.indexOf(",");
  if (comma === -1) {
    const value = vars[inner.trim()];
    return value === undefined || value === null ? "" : String(value);
  }
  const name = inner.slice(0, comma).trim();
  const rest = inner.slice(comma + 1).trim();
  if (rest.startsWith("plural")) {
    const body = rest.slice("plural".length).replace(/^,\s*/, "");
    const forms: Record<string, string> = {};
    let i = 0;
    while (i < body.length) {
      // читаем ключ
      while (i < body.length && /\s/.test(body[i])) i++;
      const keyStart = i;
      while (i < body.length && /[a-z]/.test(body[i])) i++;
      const key = body.slice(keyStart, i);
      while (i < body.length && /\s/.test(body[i])) i++;
      if (body[i] !== "{") break;
      let depth = 1;
      const contentStart = ++i;
      while (i < body.length && depth > 0) {
        if (body[i] === "{") depth++;
        else if (body[i] === "}") depth--;
        if (depth > 0) i++;
      }
      forms[key] = body.slice(contentStart, i);
      i++;
    }
    return pluralize(Number(vars[name] ?? 0), forms);
  }
  const value = vars[name];
  return value === undefined || value === null ? "" : String(value);
}

export function t(key: string, vars?: Record<string, unknown>): string {
  const dict = catalogs[current];
  const raw = dict?.[key];
  if (!raw) {
    if (import.meta.env.DEV) {
      console.warn("[i18n] missing key:", key);
    }
    return key;
  }
  return vars ? applyIcu(raw, vars) : raw;
}

export function setLocale(locale: string) {
  if (catalogs[locale]) current = locale;
}

export function getLocale(): string {
  return current;
}
