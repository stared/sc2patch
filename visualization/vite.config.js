import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import seoConfig from './src/seoConfig.json'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'html-transform',
      transformIndexHtml(html) {
        return html
          .replace(/%SEO_TITLE%/g, seoConfig.defaultTitle)
          .replace(/%SEO_DESCRIPTION%/g, seoConfig.defaultDescription)
          .replace(/%SEO_IMAGE%/g, seoConfig.defaultImage)
          .replace(/%SEO_URL%/g, seoConfig.baseUrl)
      },
    },
  ],
  base: '/sc2-balance-timeline/',
})
