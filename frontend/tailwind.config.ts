import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        mono: ["var(--font-mono)", "monospace"],
        body: ["var(--font-body)", "sans-serif"],
      },
      colors: {
        void: {
          50:  "#f0eeff",
          100: "#d9d4ff",
          200: "#b8afff",
          300: "#9b8fff",
          400: "#7c6cf7",
          500: "#6451e8",
          600: "#4f3dcb",
          700: "#3a2ba0",
          800: "#271d78",
          900: "#170f52",
          950: "#0d0920",
        },
        nebula: {
          50:  "#f5f0ff",
          100: "#ede0ff",
          200: "#d8bfff",
          300: "#be93ff",
          400: "#a060ff",
          500: "#8833ff",
          600: "#7010e0",
          700: "#5a0db8",
          800: "#430a8a",
          900: "#2e0660",
          950: "#1a0340",
        },
        aurora: {
          cyan:    "#00e5ff",
          violet:  "#a855f7",
          rose:    "#f43f5e",
          amber:   "#f59e0b",
          emerald: "#10b981",
          sky:     "#38bdf8",
        },
        glass: {
          white5:  "rgba(255,255,255,0.05)",
          white10: "rgba(255,255,255,0.10)",
          white15: "rgba(255,255,255,0.15)",
          white20: "rgba(255,255,255,0.20)",
          black10: "rgba(0,0,0,0.10)",
          black20: "rgba(0,0,0,0.20)",
          black40: "rgba(0,0,0,0.40)",
        },
        bg: {
          deepest: "#060A0F",
          card:    "#0C1520",
          hover:   "#101E2E",
        },
        line: {
          DEFAULT: "rgba(255,255,255,0.08)",
          strong:  "rgba(255,255,255,0.15)",
        },
        ink: {
          DEFAULT: "#E8F0FE",
          dim:     "rgba(232,240,254,0.70)",
          muted:   "rgba(232,240,254,0.45)",
          faint:   "rgba(232,240,254,0.25)",
        },
        accent: {
          DEFAULT: "#00FFAA",
          soft:    "rgba(0,255,170,0.08)",
          400:     "#33FFB8",
        },
        up:   { DEFAULT: "#00FFAA" },
        down: { DEFAULT: "#FF3B5C" },
        cyan: { DEFAULT: "#00D4FF" },
        warn: { DEFAULT: "#FFB800" },
      },
      backgroundImage: {
        "deep-space":    "radial-gradient(ellipse 120% 80% at 20% -10%, #2d1b69 0%, #0f0a2e 40%, #050318 100%)",
        "nebula-glow":   "radial-gradient(ellipse 60% 50% at 80% 20%, rgba(168,85,247,0.25) 0%, transparent 60%)",
        "aurora-glow":   "radial-gradient(ellipse 40% 40% at 10% 80%, rgba(0,229,255,0.12) 0%, transparent 60%)",
        "card-glass":    "linear-gradient(135deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.04) 100%)",
        "card-glass-hover": "linear-gradient(135deg, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.06) 100%)",
        "profit-glow":   "radial-gradient(ellipse 80% 60% at 50% 100%, rgba(16,185,129,0.15) 0%, transparent 70%)",
        "loss-glow":     "radial-gradient(ellipse 80% 60% at 50% 100%, rgba(244,63,94,0.15) 0%, transparent 70%)",
      },
      boxShadow: {
        glass:        "0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)",
        "glass-lg":   "0 8px 48px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.12)",
        "glass-card": "0 2px 16px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08)",
        glow:         "0 0 20px rgba(168,85,247,0.3)",
        "glow-cyan":  "0 0 20px rgba(0,229,255,0.25)",
        "glow-green": "0 0 16px rgba(16,185,129,0.3)",
        "glow-red":   "0 0 16px rgba(244,63,94,0.3)",
        glowSoft: "0 0 12px rgba(0,255,170,0.15)",

      },
      borderColor: {
        glass: "rgba(255,255,255,0.12)",
        "glass-bright": "rgba(255,255,255,0.20)",
      },
      backdropBlur: {
        glass: "20px",
        "glass-heavy": "40px",
      },
      animation: {
        "fade-in":    "fadeIn 0.4s ease forwards",
        "slide-up":   "slideUp 0.4s ease forwards",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
        "ticker":     "ticker 20s linear infinite",
        "shimmer":    "shimmer 2s linear infinite",
        "float":      "float 6s ease-in-out infinite",
      },
      keyframes: {
        fadeIn:     { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp:    { "0%": { opacity: "0", transform: "translateY(16px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        pulseGlow:  { "0%,100%": { opacity: "0.6" }, "50%": { opacity: "1" } },
        ticker:     { "0%": { transform: "translateX(0)" }, "100%": { transform: "translateX(-50%)" } },
        shimmer:    { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
        float:      { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-8px)" } },
      },
    },
  },
  plugins: [],
};

export default config;
