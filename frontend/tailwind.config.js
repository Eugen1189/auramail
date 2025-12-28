/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'aura-blue': '#4A90E2',
                'aura-purple': '#9D4EDD',
                'aura-teal': '#00D4AA',
            }
        },
    },
    plugins: [],
}
