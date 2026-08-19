/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: {
          darkest: "#090d13",
          dark: "#0d1117",
          card: "#161b22",
          elevated: "#21262d",
          hover: "#2b313a",
        },
        border: {
          subtle: "#30363d",
          muted: "#21262d",
          glow: "#388bfd44",
        },
        accent: {
          DEFAULT: "#388bfd",
          blue: "#58a6ff",
          purple: "#a371f7",
          green: "#3fb950",
          amber: "#d29922",
          red: "#f85149",
        },
        text: {
          primary: "#f0f6fc",
          secondary: "#8b949e",
          muted: "#6e7681",
        }
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Consolas", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow": "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 5px rgba(56, 139, 253, 0.2)" },
          "100%": { boxShadow: "0 0 20px rgba(56, 139, 253, 0.6)" },
        }
      }
    },
  },
  plugins: [],
}
