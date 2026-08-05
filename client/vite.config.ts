import { defineConfig, loadEnv } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'


function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id: string) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    base: env.VITE_BASE_PATH || '/ndc/',
    plugins: [
      figmaAssetResolver(),
      // The React and Tailwind plugins are both required for Make, even if
      // Tailwind is not being actively used – do not remove them
      react(),
      tailwindcss(),
    ],
    build: {
      // Always output to client/dist regardless of where the build command is run from
      outDir: path.resolve(__dirname, 'dist'),
      emptyOutDir: true,
    },
    server: {
      port: 7002,
      open: '/ndc/ndc-reporting/overview',
      proxy: {
        "/ndc/api": {
          target: "http://127.0.0.1:8010",
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/ndc/, ''),
        },
      },
    },
    resolve: {
      alias: {
        // Alias @ to the src directory
        '@': path.resolve(__dirname, './src'),
      },
    },

    // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
    assetsInclude: ['**/*.svg', '**/*.csv'],
  };
})
