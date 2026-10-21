import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * The web client's build.
 *
 * The client is **one** client: the web build serves it, the desktop
 * shell wraps it in a web view, and the mobile build wraps it in a
 * WebView. So the build has to work in all three, and it does not
 * assume a Node runtime.
 *
 * The content bundle is **copied** into the build rather than imported,
 * because it is a large JSON file that the client fetches at runtime -
 * the same way the server serves it. The client and the server then
 * agree on the content by construction, because there is one bundle.
 */
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    target: 'es2022',
    outDir: 'dist',
    emptyOutDir: true,
    assetsInlineLimit: 0,
  },
  server: {
    port: 5173,
    proxy: {
      // The API, the legacy endpoints and the metrics, all on the same
      // origin in development.
      '/api': 'http://127.0.0.1:8080',
      '/command.php': 'http://127.0.0.1:8080',
      '/get_game_config.php': 'http://127.0.0.1:8080',
      '/get_player_info.php': 'http://127.0.0.1:8080',
    },
  },
});
