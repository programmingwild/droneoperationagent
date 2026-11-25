import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Same React app, but built into the Streamlit custom component with relative
// asset paths so Streamlit Cloud can serve it at /component/nightwatch_spa.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: '../frontend/spa_component/build',
    emptyOutDir: true,
    // Streamlit custom components must load `index.html`; the input key names it.
    rollupOptions: { input: { index: 'streamlit.html' } },
  },
})
