import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'node:path'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import type { Plugin } from 'vite'

/**
 * Serves files from ../output/data/ at /data/* and ../images/ at /images/*
 * during dev. This lets the Vue frontend fetch capture cycle JSON and camera
 * images from the Python monitor's output directories without a separate server.
 */
function serveOutputData(): Plugin {
  const dataDir = resolve(__dirname, '..', 'output', 'data')
  const imagesDir = resolve(__dirname, '..', 'images')
  return {
    name: 'serve-output-data',
    configureServer(server) {
      server.middlewares.use('/data', async (req, res) => {
        const filePath = resolve(dataDir, (req.url || '/').slice(1))
        if (existsSync(filePath)) {
          const content = await readFile(filePath, 'utf-8')
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.end(content)
        } else {
          res.statusCode = 404
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'No data yet. Run: poe monitor:once' }))
        }
      })

      server.middlewares.use('/images', async (req, res) => {
        const filePath = resolve(imagesDir, (req.url || '/').slice(1))
        if (existsSync(filePath)) {
          const content = await readFile(filePath)
          res.setHeader('Content-Type', 'image/jpeg')
          res.setHeader('Access-Control-Allow-Origin', '*')
          res.setHeader('Cache-Control', 'public, max-age=86400')
          res.end(content)
        } else {
          res.statusCode = 404
          res.end('Image not found')
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
