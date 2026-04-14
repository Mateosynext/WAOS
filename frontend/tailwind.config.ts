import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        waos: {
          black: "#0A0A0A",
          white: "#F5F2EE",
          green: "#00E676",
          greenDim: "#00B85A",
          red: "#FF3C3C",
          gold: "#F5C842",
          blue: "#5BC8FF",
          graphite: "#1C1C1C",
          graphite2: "#2A2A2A",
          muted: "#888888",
          line: "#222222",
        },
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        mono: ["var(--font-mono)"],
      },
      borderRadius: {
        waos: "16px",
      },
      boxShadow: {
        waos: "0 22px 60px rgba(0, 0, 0, 0.32)",
      },
    },
  },
  plugins: [],
} satisfies Config;
