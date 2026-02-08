import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'node:path'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import type { Plugin } from 'vite'

/**
 * Serves files from ../output/data/ at /data/* during dev.
 * This lets the Vue frontend fetch capture cycle JSON from the
 * Python monitor's output directory without a separate server.
 */
function serveOutputData(): Plugin {
  const dataDir = resolve(__dirname, '..', 'output', 'data')
  return {
    name: 'serve-output-data',
    configureServer(server) {
      server.middlewares.use('/data', async (req, res, next) => {
        const filePath = resolve(dataDir, (req.url || '/').slice(1))
        if (existsSync(filePath)) {
          const content = await readFile(filePath, 'utf-8')
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.end(content)
        } else {
          next()
        }
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    serveOutputData(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
