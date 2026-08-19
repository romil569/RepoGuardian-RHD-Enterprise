import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        panel: "#F7F8FA",
        line: "#D9E0E7",
        signal: "#0F766E",
        amber: "#B7791F"
      }
    }
  },
  plugins: []
};

export default config;
