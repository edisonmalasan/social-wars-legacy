extends RefCounted
## Shared presentation layout for the first-render verification.
##
## Layout is presentation only: the verification scene and the independent
## reference compositor both place entities with these constants so that the
## capture and the reference occupy the same canvas. The canvas size and
## anchors are deliberately integer pixel positions; entity textures are drawn
## at integer positions with nearest-neighbour filtering so texels map 1:1.

const CANVAS_SIZE := Vector2i(448, 224)
const BACKGROUND_COLOR := Color8(64, 64, 64)
const PADDING := 16
const GAP := 16

## Returns the top-left anchor for each entity, laid out left to right on a
## single row starting at (PADDING, PADDING). `entity_sizes` are the rendered
## pixel sizes of each entity (Vector2i width/height).
static func anchors_for(entity_sizes: Array) -> Array:
	var anchors: Array = []
	var x := PADDING
	for size in entity_sizes:
		anchors.append(Vector2i(x, PADDING))
		x += int(size.x) + GAP
	return anchors
