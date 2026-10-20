# 4. The client is a PixiJS v8 world with a React DOM interface

**Status:** accepted

## Context

The game has two kinds of interface: a world of thousands of sprites
that scrolls, sorts and animates, and sixty to eighty text-heavy panels
with forms, lists and tooltips.

## Decision

**PixiJS v8** (WebGL2) draws the world, and **React DOM** draws the
interface.

## Alternatives

- **Everything on a canvas.** The panels would have to be reimplemented as
  canvas drawing, and text layout, scrolling and focus would be far
  worse than the browser's.
- **Everything in the DOM.** Thousands of sprites in the DOM would not
  hold a frame rate.
- **A UI framework over Pixi** (Pixi-compatible React, for instance).
  It removes the DOM's text handling for no gain, and the DOM's text
  handling is most of the value.

## Consequences

The world and the interface can be developed separately, and the
interface is testable without a GPU. The cost is two rendering models to
reason about, and a boundary between them.
