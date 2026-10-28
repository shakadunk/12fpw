// Makes the lighter copies of one image for the website: a phone size (up to 1200px wide, "-m") and a desktop size
// (up to 2000px wide, "-l"). The original file is never touched or deleted; the page offers the browser all the sizes
// and it downloads only the one it needs. Used by add-post.mjs for new posts and by add-sizes.mjs for existing ones.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const sharp = require('sharp');

export const PHONE_W = 1200, DESK_W = 2000, QUALITY = 88;
const MIN_BYTES = 400 * 1024;   // a small file that is already narrow is left alone

// dir: the post folder; im: an entry of issue.json's images ({file, w, h}); n: "01".."12".
// Returns { m?: {file, w}, l?: {file, w} }. Nothing is returned for animated or transparent images, or when a copy would not be smaller.
export async function makeVariants(dir, im, n) {
  const input = path.join(dir, im.file);
  const meta = await sharp(input, { failOn: 'none' }).metadata();
  if ((meta.pages || 1) > 1) return {};     // animated
  if (meta.hasAlpha) {                      // a real see-through area would turn black on the light theme, so leave those alone;
    const ch = (await sharp(input, { failOn: 'none' }).stats()).channels;   // but many screenshots carry an alpha channel that is fully opaque
    if (ch[ch.length - 1].min < 255) return {};
  }
  const bytes = fs.statSync(input).size;
  if (im.w <= PHONE_W && bytes < MIN_BYTES) return {};
  const out = {};
  for (const [key, maxW, suffix] of [['m', PHONE_W, 'm'], ['l', DESK_W, 'l']]) {
    const width = Math.min(maxW, im.w);
    if (key === 'l' && width <= (out.m ? out.m.w : 0)) continue;   // no wider than the phone copy: not needed
    const file = `${n}-${suffix}.jpg`;
    const info = await sharp(input, { failOn: 'none' }).rotate().flatten({ background: '#000000' })
      .resize({ width, withoutEnlargement: true })
      .jpeg({ quality: QUALITY, mozjpeg: true, chromaSubsampling: '4:4:4' })
      .toFile(path.join(dir, file));
    if (info.size >= bytes) { fs.unlinkSync(path.join(dir, file)); continue; }   // not lighter than the original
    out[key] = { file, w: info.width };
  }
  return out;
}
