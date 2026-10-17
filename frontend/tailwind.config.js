/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Saffron — primary accent, CTAs
        saffron: {
          DEFAULT: "#FF9933",
          dark: "#E07B00",
          50: "#FFF4E6",
        },
        // Green — success, resolved, secondary CTAs
        green: {
          DEFAULT: "#138808",
          dark: "#0B5E05",
          50: "#E8F5E6",
        },
        // Navy — headings, links, logo, footer bg
        navy: {
          DEFAULT: "#000080",
          900: "#0B1033",
          50: "#EEF0FA",
        },
        // Status colours
        status: {
          reported: "#FF9933",
          assigned: "#000080",
          "in-progress": "#F5B301",
          resolved: "#138808",
          reopened: "#C62828",
        },
      },
      fontFamily: {
        heading: ["Poppins", "Noto Sans Devanagari", "sans-serif"],
        body: ["Inter", "Noto Sans Devanagari", "sans-serif"],
      },
      borderRadius: {
        card: "12px",
        badge: "9999px",
        input: "8px",
      },
      boxShadow: {
        card: "0 2px 8px rgba(0,0,0,0.06)",
        "card-hover": "0 4px 16px rgba(0,0,0,0.10)",
      },
      spacing: {
        "safe-bottom": "env(safe-area-inset-bottom)",
      },
    },
  },
  plugins: [],
};
