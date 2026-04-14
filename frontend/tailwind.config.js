module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0f172a",
          light: "#1e293b",
          lighter: "#334155"
        },
        amber: {
          DEFAULT: "#f59e0b",
          light: "#fbbf24",
          dark: "#d97706"
        }
      },
      boxShadow: {
        glow: "0 20px 45px -25px rgba(15, 23, 42, 0.35)"
      },
      fontFamily: {
        sans: ["Sora", "ui-sans-serif", "system-ui"]
      }
    }
  },
  plugins: [require("@tailwindcss/forms")]
};
