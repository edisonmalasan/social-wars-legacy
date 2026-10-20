/**
 * A minimal JPEG size reader.
 *
 * The asset manifest needs the pixel dimensions of every image so the client
 * can size its placeholders and so the atlas packer can reason about them. A
 * JPEG's size is in the SOF marker, which is a short scan from the start of
 * the file — no decoding needed.
 */

/**
 * @param {Buffer} buffer
 * @returns {{width: number, height: number} | null}
 */
export function jpegSize(buffer) {
  if (buffer.length < 4 || buffer[0] !== 0xff || buffer[1] !== 0xd8) {
    return null; // not a JPEG
  }

  let offset = 2;
  while (offset + 4 <= buffer.length) {
    if (buffer[offset] !== 0xff) {
      offset += 1;
      continue;
    }
    const marker = buffer[offset + 1];
    // Standalone markers have no length field.
    if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) {
      offset += 2;
      continue;
    }
    const length = buffer.readUInt16BE(offset + 2);
    // SOF0..SOF15, except the DHT/JPG/DAC markers in that range.
    if (
      marker >= 0xc0 &&
      marker <= 0xcf &&
      marker !== 0xc4 && // DHT
      marker !== 0xc8 && // JPG
      marker !== 0xcc // DAC
    ) {
      return {
        height: buffer.readUInt16BE(offset + 5),
        width: buffer.readUInt16BE(offset + 7),
      };
    }
    offset += 2 + length;
  }
  return null;
}
