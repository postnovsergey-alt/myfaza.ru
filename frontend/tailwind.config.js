/** @type {import('tailwindcss').Config} */
// Tailwind используется как утилиты компоновки — flex, grid, отступы.
// Все цвета, радиусы и длительности — из CSS-переменных из DESIGN-SPEC 2.1,
// подключаются через arbitrary values: bg-[color:var(--surface)] и т.п.
// Кастомная тема Tailwind нам не нужна — она бы дублировала токены.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  corePlugins: {
    // Ограничиваем набор — уменьшаем финальный CSS
    preflight: true,
  },
  plugins: [],
};
