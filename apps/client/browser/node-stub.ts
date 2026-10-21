/**
 * The stub for the node built-ins.
 *
 * The browser has no `fs` and no `path`, and the offline mode's
 * database — PGlite, which is PostgreSQL compiled to WebAssembly —
 * ships a node filesystem module alongside its browser one. That module
 * is only **loaded** when the database is asked for a node directory,
 * which never happens in a browser, but a bundler still has to be able
 * to resolve its imports.
 *
 * So the build points `fs` and `path` here: an empty module, which
 * satisfies the import without pretending to be a filesystem.
 *
 * The browser's own filesystem is IndexedDB, and that is what the
 * offline mode uses.
 */

export {};
