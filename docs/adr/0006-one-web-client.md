# 6. One web client, for the web, the desktop and the mobile

**Status:** accepted

## Context

Three targets, and a temptation to share code carefully rather than
completely.

## Decision

One client, in `packages/client` and `apps/client`. The web build
serves it, the desktop shell wraps it in a web view, and the mobile
build wraps it in a WebView.

The client is the single source of truth for presentation: there is no
second renderer, and no platform-specific screen.

## Alternatives

- **A native mobile client.** A second implementation of the same game,
  which doubles the work and halves the correctness.
- **A thin native shell around a shared web view.** That is what is
  chosen, deliberately: the differences between the targets are the
  window, the input and the packaging, and none of them is the game.

## Consequences

The client is written once and tested once. The cost is that the
platform's own conventions are available only through the web view's
limitations, and that the mobile build's performance depends on the
web view's.
