/**
 * This is a minimal config.
 *
 * If you need the full config, get it from here:
 * https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
 */

module.exports = {
    content: [
        /**
         * HTML. Paths to Django template files that will contain Tailwind CSS classes.
         */

        /*  Templates within theme app (<tailwind_app_name>/templates), e.g. base.html. */
        '../templates/**/*.html',

        /*
         * Main templates directory of the project (BASE_DIR/templates).
         * Adjust the following line to match your project structure.
         */
        '../../templates/**/*.html',

        /*
         * Templates in other django apps (BASE_DIR/<any_app_name>/templates).
         * Adjust the following line to match your project structure.
         */
        '../../**/templates/**/*.html',

        /**
         * JS: If you use Tailwind CSS in JavaScript, uncomment the following lines and make sure
         * patterns match your project structure.
         */
        /* JS 1: Ignore any JavaScript in node_modules folder. */
        // '!../../**/node_modules',
        /* JS 2: Process all JavaScript files in the project. */
        // '../../**/*.js',

        /**
         * Python: If you use Tailwind CSS classes in Python, uncomment the following line
         * and make sure the pattern below matches your project structure.
         */
        // '../../**/*.py'
    ],
    theme: {
        extend: {
            colors: {
                primary: '#0a6640',
                primaryD: '#0c1a0f',
                primaryLight: '#0d8c55',
                accent: '#c8752e',
                green: '#0a6640',
                greenSat: '#0d8c55',
                amber: '#c8752e',
                rule: '#d6dfd9',
                surface: '#f4f7f5',
                white: '#ffffff',
                muted: '#607568',
                ink: '#0c1a0f',
                inkMid: '#1e3324',
                danger: '#b91c1c',
                dangerLight: '#fef2f2',
                dangerBorder: '#fecaca',
                error: '#c0392b',
                errorLight: '#fee2e2',
                info: '#0ea5e9',
                sky: '#93c5fd',
                cobalt: '#1e40af',
                emerald: '#10b981',
                brandDark: '#065f46',
                dark: '#101d14',
                slate: '#2f4f4f',
                'forest-green': 'var(--forest-green)',
                'ocean-teal': 'var(--ocean-teal)',
                'solar-amber': 'var(--solar-amber)',
                'neutral-50': 'var(--neutral-50)',
                'neutral-100': 'var(--neutral-100)',
                'neutral-200': 'var(--neutral-200)',
                'neutral-300': 'var(--neutral-300)',
                'neutral-700': 'var(--neutral-700)',
                'neutral-800': 'var(--neutral-800)',
                'neutral-900': 'var(--neutral-900)',
            },
            fontFamily: {
                brand: ['Fraunces', 'serif'],
                sans: ['Inter', 'sans-serif'],
                body: ['Outfit', 'sans-serif'],
                display: ['Space Grotesk', 'sans-serif'],
                serif: ['Georgia', 'serif'],
                system: ['Segoe UI', 'system-ui', 'sans-serif'],
                mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
            },
        },
    },
    plugins: [
        /**
         * '@tailwindcss/forms' is the forms plugin that provides a minimal styling
         * for forms. If you don't like it or have own styling for forms,
         * comment the line below to disable '@tailwindcss/forms'.
         */
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
