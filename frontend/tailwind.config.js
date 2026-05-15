/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202a",
        panel: "#f7f9fb",
        line: "#d8e0e7",
        signal: "#0f766e",
        amber: "#b7791f"
      }
    }
  },
  plugins: []
};
