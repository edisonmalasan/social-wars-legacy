import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vite';

/**
 * The stub for the node built-ins.
 *
 * The browser has no `fs` and no `path`. The offline mode's database
 * ships a node filesystem module alongside its browser one, and that
 * module is only *loaded* when the database is asked for a node
 * directory - which never happens in a browser - but the bundler still
 * has to resolve its imports.
 */
const nodeStub = fileURLToPath(new URL('./browser/node-stub.ts', import.meta.url));

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
  resolve: {
    alias: [
      // Exactly `fs` and exactly `path`, and nothing else: a bundler
      // that maps `node:fs` as well would break the packages that check
      // for the platform at runtime.
      { find: /^fs$/, replacement: nodeStub },
      { find: /^path$/, replacement: nodeStub },
    ],
  },
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
