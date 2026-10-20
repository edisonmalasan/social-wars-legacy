# The bundled server

The desktop shell ships the project's own server, so a player needs
nothing installed.

The build copies the **built** server into this directory before the
shell is packaged:

```
node scripts/build-desktop-server.mjs
```

which runs the server's own build and copies the result here. The shell
then starts it as a **sidecar** — a binary beside the executable — so
the app works offline and the player never has to install Node.

In development the shell runs the server from the repository instead
(`node apps/server/src/main.ts`), so the two paths are exercised by the
same code with a different command.
