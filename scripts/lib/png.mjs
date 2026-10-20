/**
 * A minimal PNG codec.
 *
 * The asset pipeline needs to read the frames FFDec exports, find each one's
 * alpha bounding box, trim it, and pack the trimmed images into atlases. That
 * needs a PNG decoder and an encoder, and the repository has no runtime
 * dependencies by design — so here they are, on top of Node's built-in zlib.
 *
 * Scope: 8-bit depth, non-interlaced, colour types 0 (grey), 2 (RGB), 3
 * (palette), 4 (grey+alpha) and 6 (RGBA). That is what JPEXS writes, and it is
 * what a modern GPU wants to upload.
 */
import { deflateSync, inflateSync } from 'node:zlib';

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

/** The channels per PNG colour type. */
const CHANNELS = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 };

export class PngError extends Error {
  constructor(message) {
    super(message);
    this.name = 'PngError';
  }
}

/**
 * Decode a PNG into raw RGBA.
 *
 * @param {Buffer} buffer
 * @returns {{width: number, height: number, data: Buffer}} `data` is RGBA, 4 bytes per pixel.
 */
export function decodePng(buffer) {
  if (!buffer.subarray(0, 8).equals(SIGNATURE)) {
    throw new PngError('not a PNG');
  }

  let offset = 8;
  let header = null;
  let palette = null;
  let transparency = null;
  const idat = [];

  while (offset + 8 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString('latin1', offset + 4, offset + 8);
    const data = buffer.subarray(offset + 8, offset + 8 + length);
    offset += 12 + length; // length + type + data + crc

    if (type === 'IHDR') {
      header = {
        width: data.readUInt32BE(0),
        height: data.readUInt32BE(4),
        bitDepth: data[8],
        colorType: data[9],
        compression: data[10],
        filter: data[11],
        interlace: data[12],
      };
    } else if (type === 'PLTE') {
      palette = Buffer.from(data);
    } else if (type === 'tRNS') {
      transparency = Buffer.from(data);
    } else if (type === 'IDAT') {
      idat.push(Buffer.from(data));
    } else if (type === 'IEND') {
      break;
    }
  }

  if (!header) throw new PngError('no IHDR chunk');
  if (header.bitDepth !== 8) {
    throw new PngError(`unsupported bit depth ${header.bitDepth} (only 8 is supported)`);
  }
  if (header.interlace !== 0) {
    throw new PngError('interlaced PNGs are not supported');
  }

  const channels = CHANNELS[header.colorType];
  if (!channels) throw new PngError(`unsupported colour type ${header.colorType}`);

  const raw = inflateSync(Buffer.concat(idat));
  const { width, height } = header;
  const stride = width * channels;
  const pixels = Buffer.alloc(stride * height);

  // Undo the per-scanline filters.
  let pos = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[pos++];
    const line = raw.subarray(pos, pos + stride);
    pos += stride;
    const out = pixels.subarray(y * stride, (y + 1) * stride);
    const prior = y > 0 ? pixels.subarray((y - 1) * stride, y * stride) : null;

    for (let x = 0; x < stride; x++) {
      const rawByte = line[x];
      const a = x >= channels ? out[x - channels] : 0;
      const b = prior ? prior[x] : 0;
      const c = prior && x >= channels ? prior[x - channels] : 0;
      let value;
      switch (filter) {
        case 0:
          value = rawByte;
          break;
        case 1:
          value = rawByte + a;
          break;
        case 2:
          value = rawByte + b;
          break;
        case 3:
          value = rawByte + ((a + b) >> 1);
          break;
        case 4:
          value = rawByte + paeth(a, b, c);
          break;
        default:
          throw new PngError(`unknown scanline filter ${filter}`);
      }
      out[x] = value & 0xff;
    }
  }

  // Normalise everything to RGBA.
  const rgba = Buffer.alloc(width * height * 4);
  for (let i = 0, n = width * height; i < n; i++) {
    const s = i * channels;
    const d = i * 4;
    switch (header.colorType) {
      case 0:
        rgba[d] = rgba[d + 1] = rgba[d + 2] = pixels[s];
        rgba[d + 3] = 255;
        break;
      case 2:
        rgba[d] = pixels[s];
        rgba[d + 1] = pixels[s + 1];
        rgba[d + 2] = pixels[s + 2];
        rgba[d + 3] = 255;
        break;
      case 3: {
        const index = pixels[s] * 3;
        rgba[d] = palette[index];
        rgba[d + 1] = palette[index + 1];
        rgba[d + 2] = palette[index + 2];
        rgba[d + 3] = transparency && pixels[s] < transparency.length ? transparency[pixels[s]] : 255;
        break;
      }
      case 4:
        rgba[d] = rgba[d + 1] = rgba[d + 2] = pixels[s];
        rgba[d + 3] = pixels[s + 1];
        break;
      case 6:
        rgba[d] = pixels[s];
        rgba[d + 1] = pixels[s + 1];
        rgba[d + 2] = pixels[s + 2];
        rgba[d + 3] = pixels[s + 3];
        break;
      default:
        throw new PngError(`unsupported colour type ${header.colorType}`);
    }
  }

  return { width, height, data: rgba };
}

function paeth(a, b, c) {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  if (pb <= pc) return b;
  return c;
}

/** CRC-32, for the PNG chunk checksum. */
const CRC_TABLE = (() => {
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c;
  }
  return table;
})();

function crc32(buffer) {
  let c = 0xffffffff;
  for (let i = 0; i < buffer.length; i++) {
    c = CRC_TABLE[(c ^ buffer[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const out = Buffer.alloc(data.length + 12);
  out.writeUInt32BE(data.length, 0);
  out.write(type, 4, 'latin1');
  data.copy(out, 8);
  out.writeUInt32BE(crc32(out.subarray(4, 8 + data.length)), 8 + data.length);
  return out;
}

/**
 * Encode raw RGBA as a PNG.
 *
 * @param {{width: number, height: number, data: Buffer}} image
 * @returns {Buffer}
 */
export function encodePng({ width, height, data }) {
  const stride = width * 4;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (stride + 1)] = 0; // filter: none
    data.copy(raw, y * (stride + 1) + 1, y * stride, (y + 1) * stride);
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // colour type: RGBA
  ihdr[10] = 0; // compression
  ihdr[11] = 0; // filter
  ihdr[12] = 0; // interlace

  return Buffer.concat([
    SIGNATURE,
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

/**
 * The bounding box of the non-transparent pixels.
 *
 * A frame exported from a SWF is the whole stage, so most of it is
 * transparent padding. Trimming to the alpha bounds is what makes atlasing
 * worth doing at all.
 *
 * @param {{width: number, height: number, data: Buffer}} image RGBA
 * @returns {{x: number, y: number, width: number, height: number} | null} null when fully transparent
 */
export function alphaBounds({ width, height, data }) {
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;

  for (let y = 0; y < height; y++) {
    const row = y * width * 4;
    for (let x = 0; x < width; x++) {
      if (data[row + x * 4 + 3] !== 0) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }

  if (maxX < 0) return null;
  return { x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1 };
}

/** Cut a rectangle out of an RGBA image. */
export function crop({ width, height, data }, rect) {
  const out = Buffer.alloc(rect.width * rect.height * 4);
  for (let y = 0; y < rect.height; y++) {
    const from = ((rect.y + y) * width + rect.x) * 4;
    data.copy(out, y * rect.width * 4, from, from + rect.width * 4);
  }
  return { width: rect.width, height: rect.height, data: out };
}

/** The size of a PNG without decoding it. */
export function pngSize(buffer) {
  if (buffer.length < 24 || !buffer.subarray(0, 8).equals(SIGNATURE)) {
    throw new PngError('not a PNG');
  }
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}
