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
        sans: ["var(--font-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        canvas: "#F4F4F0",
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#ECECE6",
        },
        grid: "#D4D4CE",
        ink: {
          DEFAULT: "#111111",
          secondary: "#4A4A45",
          muted: "#73736C",
        },
        amber: {
          signal: "#FF7E00",
          hover: "#E06F00",
          wash: "#FFF5EB",
        },
        status: {
          live: "#15803D",
          reject: "#B91C1C",
        },
      },
    },
  },
  plugins: [],
};

export default config;
