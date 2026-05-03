import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Paleta Minsait oficial
        pruno: {
          DEFAULT: '#4F062A',
          dark: '#260717',
        },
        ceramica: '#E3E2DA',
        magenta: '#FF0054',
        lila: '#8661F5',
        amazonico: '#00B0BD',
        verde: '#44B757',
        naranja: '#E56813',
        rosa: '#EF659D',
        link: '#FF0054',
        linkVisited: '#A40037',
      },
      fontFamily: {
        sans: ['var(--font-forfuture)', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        chamfer: '0.5rem',  // chaflán uniforme inspirado en brandbook
      },
    },
  },
  plugins: [],
};

export default config;
