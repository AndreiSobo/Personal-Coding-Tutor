import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: 'class',
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./utils/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            height: {
                dvh: '100dvh',
            },
        },
    },
    plugins: [],
};
export default config;