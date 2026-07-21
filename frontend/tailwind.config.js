/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#2563EB",
        secondary: "#1E293B",
        accent: "#38BDF8",
        background: "#0F172A",
        card: "#1E293B",
        border: "#2A3A54",
        muted: "#94A3B8",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 4px 24px -4px rgba(0,0,0,0.35)",
        soft: "0 2px 12px -2px rgba(0,0,0,0.25)",
      },
      borderRadius: {
        xl: "0.875rem",
      },
    },
  },
  plugins: [],
};
