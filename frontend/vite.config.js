import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import basicSsl from '@vitejs/plugin-basic-ssl'

const PROXY_API = {
  '/api': {
    target: 'http://localhost:8000', // [H] port de l'API
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}

// `npm run dev:telephone` (mode « telephone ») sert l'application en https sur le réseau local,
// avec un certificat créé sur place : le micro (note vocale) et la caméra ne marchent qu'en https.
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    ...(mode === 'telephone' ? [basicSsl({ name: 'yilgmde-local' })] : []),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Yilgamdé',
        short_name: 'Yilgamdé',
        description: 'Signaler et cartographier les dépotoirs de Ouagadougou',
        lang: 'fr',
        theme_color: '#1b6b4a',
        background_color: '#faf6ee',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff,woff2,json,geojson,bin}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api/],
        runtimeCaching: [
          {
            // Tuiles deja vues : disponibles hors ligne (pas de telechargement en masse)
            urlPattern: /^https:\/\/tile\.openstreetmap\.org\/.*/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'tuiles-osm',
              expiration: { maxEntries: 300, maxAgeSeconds: 60 * 60 * 24 * 14 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  // Même relais vers l'API pour `npm run dev` et pour `vite preview` (version construite, installable).
  server: { proxy: PROXY_API },
  preview: { proxy: PROXY_API },
}))
