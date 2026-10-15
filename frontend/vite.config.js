import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_TARGET || 'http://localhost:5000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/auth': target,
        '/health': target,
        '/messages': target,
        '/conversations': target,
        '/users': target,
        '/ws': {
          target,
          ws: true,
        },
      },
    },
  }
})
