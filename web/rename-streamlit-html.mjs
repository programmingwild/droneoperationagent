// Vite names the emitted HTML after its source file. Streamlit custom
// components require `index.html`, so normalize the output after the build.
import { renameSync } from 'node:fs'

renameSync(
  new URL('../frontend/spa_component/build/streamlit.html', import.meta.url),
  new URL('../frontend/spa_component/build/index.html', import.meta.url),
)
