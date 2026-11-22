/**
 * The SVG primitives the icon family is built from.
 *
 * Every number is formatted with `String(Math.round(x * 100) / 100)` so the
 * serialised bytes are the same on every platform. No trigonometry is used:
 * the geometry comes from fixed coordinate tables and integer arithmetic.
 */

/** An original palette, chosen for this family and not taken from the game. */
export const PALETTE = {
  ink: '#16242d',
  slate: '#2c4654',
  teal: '#2f7d78',
  aqua: '#86cdbd',
  amber: '#e9a63f',
  cream: '#f7ecd7',
  rust: '#b65340',
} as const;

export type Point = readonly [number, number];

/** Format a coordinate deterministically. */
export function n(value: number): string {
  return String(Math.round(value * 100) / 100);
}

/** Escape a string for use in an XML text node or attribute. */
export function escapeXml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export function rect(x: number, y: number, w: number, h: number, fill: string, rx = 0): string {
  return `    <rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}" rx="${n(rx)}" fill="${fill}"/>\n`;
}

export function circle(cx: number, cy: number, r: number, fill: string): string {
  return `    <circle cx="${n(cx)}" cy="${n(cy)}" r="${n(r)}" fill="${fill}"/>\n`;
}

export function ellipse(cx: number, cy: number, rx: number, ry: number, fill: string): string {
  return `    <ellipse cx="${n(cx)}" cy="${n(cy)}" rx="${n(rx)}" ry="${n(ry)}" fill="${fill}"/>\n`;
}

export function polygon(points: readonly Point[], fill: string): string {
  const list = points.map(([x, y]) => `${n(x)},${n(y)}`).join(' ');
  return `    <polygon points="${list}" fill="${fill}"/>\n`;
}

export function line(x1: number, y1: number, x2: number, y2: number, stroke: string, width: number): string {
  return `    <line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}" stroke="${stroke}" stroke-width="${n(width)}" stroke-linecap="round"/>\n`;
}

export function path(d: string, fill: string, stroke?: string, width = 2): string {
  const strokePart = stroke ? ` stroke="${stroke}" stroke-width="${n(width)}" stroke-linecap="round" stroke-linejoin="round"` : '';
  return `    <path d="${d}" fill="${fill}"${strokePart}/>\n`;
}

export function group(body: string, transform: string): string {
  return `    <g transform="${escapeXml(transform)}">\n${body}    </g>\n`;
}

/** A standalone 64x64 SVG document. */
export function svgDocument(title: string, description: string, body: string): string {
  return (
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" ' +
    'role="img" aria-labelledby="swl-title swl-desc">\n' +
    `  <title id="swl-title">${escapeXml(title)}</title>\n` +
    `  <desc id="swl-desc">${escapeXml(description)}</desc>\n` +
    body +
    '</svg>\n'
  );
}
