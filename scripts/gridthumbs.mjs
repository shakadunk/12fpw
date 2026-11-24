// Makes the two small copies the V5 archive grid draws: "-g" at 240px on its long side (a desktop cell,
// 12 across, at 2x) and "-g2" at 480px (a phone cell, 3 across, at 3x). The grid shows every photo whole
// inside a square, so the long side is the one that fills the cell, and it is what both copies are sized by.
// The existing "-t" thumbnail (700px wide) stays as it is: the V2 pages show it larger.
// Used by add-post.mjs for new posts and by add-grid-thumbs.mjs for existing ones.
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const sharp = require('sharp');

export const GRID_SIZES = [['g', 240], ['g2', 480]];

// dir: the post folder; im: an entry of issue.json's images ({file}); n: "01".."12".
// Returns { g: {file, w, h}, g2: {file, w, h} }.
export async function makeGridThumbs(dir, im, n) {
  const out = {};
  for (const [key, size] of GRID_SIZES) {
    const file = `${n}-${key}.jpg`;
    const info = await sharp(path.join(dir, im.file), { failOn: 'none', pages: 1 }).rotate().flatten({ background: '#000000' })
      .resize({ width: size, height: size, fit: 'inside', withoutEnlargement: true })
      .jpeg({ quality: 82, mozjpeg: true })
      .toFile(path.join(dir, file));
    out[key] = { file, w: info.width, h: info.height };
  }
  return out;
}
