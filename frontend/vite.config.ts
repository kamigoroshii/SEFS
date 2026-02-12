import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    publicDir: 'public',
    server: {
        port: 5173,
        strictPort: false,
        host: 'localhost',
        hmr: {
            protocol: 'ws',
            host: 'localhost',
            port: 5173
        }
    }
})
