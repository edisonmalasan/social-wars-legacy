/**
 * Capacitor configuration for the mobile shell — **config only**.
 *
 * ADR 6: this wraps the one shared web client; it is not a second renderer
 * and there is no platform-specific screen. ADR 19: the product is pure
 * online, so the WebView loads the client from the **same remote server**
 * the browser and the desktop shell use. No Node server is bundled into
 * the app.
 *
 * This file is deliberately a plain object: capacitor.config.ts is read by
 * the Capacitor CLI, which is only installed when native work begins. There
 * are no native projects here — `cap add android` / `cap add ios` generate
 * them, and they are not run as part of this scaffold.
 */

/** The deployed game server. Replace before generating a native project. */
const serverUrl = 'https://REPLACE-WITH-YOUR-SERVER.example';

const config = {
  appId: 'com.socialwarslegacy.app',
  appName: 'Social Wars Legacy',
  // The one shared client's build output. `cap sync` copies it; at runtime
  // the WebView loads `server.url` instead, because the client's API paths
  // are relative and must resolve against the real server.
  webDir: '../client/dist',
  server: {
    url: serverUrl,
    // The game talks to a real, authenticated server; never downgrade it.
    cleartext: false,
  },
};

export default config;
