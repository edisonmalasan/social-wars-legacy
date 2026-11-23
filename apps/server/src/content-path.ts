import { fileURLToPath } from 'node:url';

/**
 * Resolve the content bundle next to the server's own source file.
 *
 * `pnpm --filter @swl/app-server dev` runs the entry point with its working
 * directory set to `apps/server`, not the workspace root. A cwd-relative path
 * therefore points at `apps/server/packages/content/dist/...`, which does not
 * exist. The packaged sidecar keeps the same `apps/server/src` ->
 * `packages/content/dist` layout, so resolving from the module's own URL works
 * in both the development tree and the shipped app, whatever the cwd.
 */
export function contentPathFrom(moduleUrl: string | URL): string {
  return fileURLToPath(
    new URL('../../../packages/content/dist/content-bundle.json', moduleUrl),
  );
}
