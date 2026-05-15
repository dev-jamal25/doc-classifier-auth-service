import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#090b12",
          900: "#111827",
          800: "#172033",
        },
        ocean: {
          500: "#0ea5e9",
          600: "#0284c7",
        },
        mint: {
          400: "#34d399",
          500: "#10b981",
        },
        amberline: {
          400: "#f59e0b",
        },
      },
      boxShadow: {
        panel: "0 18px 60px -30px rgba(15, 23, 42, 0.35)",
        glow: "0 20px 70px -38px rgba(14, 165, 233, 0.8)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
