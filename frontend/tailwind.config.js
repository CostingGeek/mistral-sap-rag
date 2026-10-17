/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors
        mistral: "#fa520f",
        flame: "#fb6424",
        blockOrange: "#ff8105",
        sun: {
          300: "#ffd06a",
          500: "#ffb83e",
          700: "#ffa110",
          900: "#ff8a00",
        },
        gold: "#ffe295",
        brandYellow: "#ffd900",
        crimson: "#c00018",
        
        // Surfaces & text
        ivory: "#fffaeb",
        cream: "#fff0c2",
        ink: {
          DEFAULT: "#1f1f1f",
          2: "#3d3d3d",
        },
        borderWarm: "#f0e8c8",
        
        // Semantic
        success: "#17a34a",
        warn: "#eab308",
        danger: "#dc2626",
      },
      fontFamily: {
        display: ["Inter", "Arial", "ui-sans-serif", "system-ui", "sans-serif"],
        body: ["Inter", "Arial", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SF Mono", "JetBrains Mono", "Menlo", "monospace"],
      },
      fontSize: {
        display: ["5.13rem", { lineHeight: "1", letterSpacing: "-0.025em" }],
        h2: ["2.5rem", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        h3: ["1.75rem", { lineHeight: "1.15" }],
        lead: ["1.5rem", { lineHeight: "1.5" }],
      },
      borderRadius: {
        sm: "2px",
        md: "2px",
        lg: "4px",
      },
      transitionTimingFunction: {
        standard: "cubic-bezier(0.2, 0, 0, 1)",
      },
      boxShadow: {
        warm: "-8px 16px 39px rgba(127, 99, 21, 0.12)",
        "warm-sm": "0 6px 20px rgba(127, 99, 21, 0.10)",
      },
      ringWidth: {
        3: "3px",
      },
      ringOpacity: {
        30: "0.3",
      },
    },
  },
  plugins: [],
}
