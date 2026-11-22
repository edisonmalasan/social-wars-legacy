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
 * are no committed native projects — `cap add android` / `cap add ios`
 * generate them locally and they are gitignored. A real Android debug APK
 * build was verified with the placeholder URL below; the APK is a build
 * artifact, not a runnable client, until the URL names a real deployment.
 */

/** The deployed game server. Replace before shipping a runnable native app. */
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
