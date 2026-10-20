# 17. The substitute fonts are scaled to the original's metrics

**Status:** accepted

## Context

The client's two faces — Arial Rounded MT Bold and Komika Axis — are
proprietary, and the game has to ship without them. The game fits its
text into boxes that were sized for the **original** fonts.

## Decision

The substitutes are **Nunito** and **Rubik Mono One**, both under the
SIL Open Font License 1.1, and they are **scaled** so that the text
occupies the same width as the original. The scale is a **parameter**,
measured against the real font files, not a constant baked in.

## Alternatives

- **Use the substitutes at their own size.** The layout would not fit:
  the text would overflow boxes that were sized for another face.
- **Keep the original fonts.** They cannot be redistributed.

## Consequences

The game's layout still fits, and the metrics are measured rather than
guessed. The cost is that the scale has to be re-measured whenever a
substitute changes.
