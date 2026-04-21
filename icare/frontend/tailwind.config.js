/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        teal: {
          50: "#E1F5EE",
          100: "#9FE1CB",
          400: "#1D9E75",
          600: "#0F6E56",
          800: "#085041",
        },
        amber: {
          50: "#FAEEDA",
          400: "#EF9F27",
          600: "#BA7517",
        },
        danger: {
          50: "#FCEBEB",
          400: "#E24B4A",
        },
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)",
      },
    },
  },
  plugins: [],
};
