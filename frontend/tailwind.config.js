/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        plum: {
          950: "#270E20",
          900: "#3B1730",
          800: "#4A1F3F",
          700: "#5F2B52",
        },
        burgundy: {
          DEFAULT: "#5A1538",
          dark: "#47102C",
          light: "#73204A",
        },
        cream: {
          50: "#FBF3EC",
          100: "#F5EBDD",
          150: "#EFE2CE",
        },
        sand: {
          200: "#E8D9C3",
          300: "#D8C3A5",
        },
        gold: {
          DEFAULT: "#C9A06A",
          light: "#DFBE8E",
          amber: "#B8862B",
        },
        ink: {
          DEFAULT: "#2A1424",
          muted: "#5A4252",
          soft: "#7C6474",
        },
        verdict: {
          supported: "#3B7D3A",
          partly: "#B8741A",
          unsupported: "#A63030",
          missing: "#5A5A5A",
          contradictory: "#5B4FC4",
          outdated: "#2E9E7E",
        },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "Georgia", "serif"],
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        journal: "0 10px 30px -12px rgba(42, 20, 36, 0.14), 0 2px 8px -2px rgba(42, 20, 36, 0.06)",
        "journal-lg": "0 22px 50px -16px rgba(42, 20, 36, 0.25), 0 6px 16px -4px rgba(42, 20, 36, 0.10)",
        card: "0 6px 20px -8px rgba(59, 23, 48, 0.12)",
      },
    },
  },
  plugins: [],
};
