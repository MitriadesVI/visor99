import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      boxShadow: {
        glow: "0 24px 80px rgba(11, 15, 26, 0.45)",
      },
    },
  },
  plugins: [],
} satisfies Config;
