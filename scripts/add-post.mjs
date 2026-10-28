// Create (or replace) one weekly post from a folder of images and a text file.
//
//   node scripts/add-post.mjs <folder> --year 2025 --week 3 [--text text.txt] [--hero 1] [--no-lens] [--force] [--push]
//   --no-lens: the week is all original photography, so its images get no Google image-search links
//   links.txt (in the folder): one address per line, in image order, to send each image somewhere specific (e.g. a song);
//     a blank line keeps the default image-search link, a single dash (-) means no link on that image
//   --date 2023-08-06: the real send date (the calendar month and the order come from it; the default is the Thursday of the ISO week)
//
// <folder> holds the 12 images (sorted by filename) and optionally text.txt.
// The images are kept at FULL SIZE: browser-friendly files (JPEG, PNG, WebP, GIF, AVIF) are copied byte for byte,
// with no resizing or re-compressing. Anything else (HEIC, TIFF) is converted to a high-quality full-size JPEG.
// A small thumbnail is also made for the Grid view. Needs `npm install` once (for sharp).
// --hero is the image number (1 to 12) used as the thumbnail. The hero is always image 1, so leave this off.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
import { makeVariants } from './variants.mjs';
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

// failOn none: a slightly damaged file (e.g. a JPEG missing its last few bytes) still gets a thumbnail; browsers display such files fine
let sharp;
try { sharp = require('sharp'); } catch {
  console.error('This script needs sharp. Run `npm install` in the project folder first.');
  process.exit(1);
}

const args = process.argv.slice(2);
const valueFlags = ['--year', '--week', '--text', '--hero', '--links', '--date'];
const opt = (n) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : undefined; };
const flag = (n) => args.includes(`--${n}`);
const folder = args.find((a, i) => !a.startsWith('--') && !valueFlags.includes(args[i - 1]));

const fail = (m) => { console.error(m); process.exit(1); };
if (!folder || !fs.existsSync(folder) || !fs.statSync(folder).isDirectory()) fail('Usage: node scripts/add-post.mjs <folder> --year 2025 --week 3 [--text file] [--hero N] [--force] [--push]');
const year = Number(opt('year')), week = Number(opt('week'));
if (!Number.isInteger(year) || year < 2000 || year > 2100) fail('--year is required, e.g. --year 2025');
if (!Number.isInteger(week) || week < 1 || week > 53) fail('--week is required, 1 to 53');

const files = fs.readdirSync(folder).filter((f) => /\.(jpe?g|png|webp|gif|avif|tiff?)$/i.test(f) && !f.startsWith('.')).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
if (files.length !== 12 && !flag('allow-any')) fail(`Found ${files.length} images in ${folder}; a post has exactly 12. (Use --allow-any to override.)`);
if (!files.length) fail(`No images in ${folder}`);

const textPath = opt('text') || path.join(folder, 'text.txt');
const text = fs.existsSync(textPath) ? fs.readFileSync(textPath, 'utf8').replace(/\r\n/g, '\n').trim() : '';
if (!text) console.warn('Note: no text found (looked for text.txt). The post will have images only.');

const hero = opt('hero') ? Number(opt('hero')) - 1 : 0;
if (!Number.isInteger(hero) || hero < 0 || hero >= files.length) fail(`--hero must be between 1 and ${files.length}`);

const slug = `${year}-w${String(week).padStart(2, '0')}`;
const dest = path.join(root, 'issues', slug);
if (fs.existsSync(dest) && !flag('force')) fail(`issues/${slug} already exists. Use --force to replace it.`);
fs.rmSync(dest, { recursive: true, force: true });
fs.mkdirSync(dest, { recursive: true });

// Optional links.txt in the folder (or --links file): one web address per line, in image order; a blank line keeps the default
// (the Google image-search link). Use it when each image should open something specific, such as a song.
const linksPath = opt('links') || path.join(folder, 'links.txt');
const customLinks = fs.existsSync(linksPath) ? fs.readFileSync(linksPath, 'utf8').replace(/\r\n/g, '\n').split('\n').map((l) => l.trim()) : [];
// a line with just a dash means NO link on that image (e.g. original photography in a week of otherwise-sourced images)
if (customLinks.some((l) => l && l !== '-' && !/^https?:\/\//.test(l))) fail('links.txt: every non-blank line must be a web address starting with http:// or https://, or a single dash for no link');
const date = opt('date');
if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) fail('--date must look like 2023-08-06');
const images = [];
const SAFE = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif']);
const BIG = 8 * 1024 * 1024;
for (const [i, f] of files.entries()) {
  const n = String(i + 1).padStart(2, '0');
  const input = path.join(folder, f);
  const ext = path.extname(f).toLowerCase();
  const info = await sharp(input, { failOn: 'none' }).metadata();
  let file, w, h;
  if (SAFE.has(ext)) {
    file = `${n}${ext === '.jpeg' ? '.jpg' : ext}`;
    fs.copyFileSync(input, path.join(dest, file));
    const turned = (info.orientation || 1) >= 5;   // the browser applies the EXIF rotation, so swap width and height to match
    w = turned ? info.height : info.width; h = turned ? info.width : info.height;
  } else {
    file = `${n}.jpg`;
    const out = await sharp(input, { failOn: 'none' }).rotate().flatten({ background: '#000000' }).jpeg({ quality: 95, mozjpeg: true }).toFile(path.join(dest, file));
    w = out.width; h = out.height;
  }
  const size = fs.statSync(path.join(dest, file)).size;
  if (size > BIG) console.warn(`Note: ${f} is ${(size / 1048576).toFixed(1)} MB. Full-size files this large make the page slow to load; consider a smaller export.`);
  const thumb = await sharp(input, { failOn: 'none' }).rotate().flatten({ background: '#000000' })
    .resize({ width: 700, withoutEnlargement: true })
    .jpeg({ quality: 78, mozjpeg: true }).toFile(path.join(dest, `${n}-t.jpg`));
  const v = await makeVariants(dest, { file, w, h }, n);
  images.push({ file, w, h, thumb: `${n}-t.jpg`, tw: thumb.width, th: thumb.height, ...(v.m ? { m: v.m } : {}), ...(v.l ? { l: v.l } : {}), alt: '', ...(customLinks[i] === '-' ? { href: false } : customLinks[i] ? { href: customLinks[i] } : {}) });
}

fs.writeFileSync(path.join(dest, 'issue.json'), JSON.stringify({ year, week, hero, ...(date ? { date } : {}), ...(flag('no-lens') ? { lens: false } : {}), images }, null, 2) + '\n');
fs.writeFileSync(path.join(dest, 'text.txt'), text + (text ? '\n' : ''));
const kb = Math.round(fs.readdirSync(dest).reduce((a, f) => a + fs.statSync(path.join(dest, f)).size, 0) / 1024);
console.log(`Created issues/${slug}: ${images.length} images, ${kb} KB. Week ${week}, ${year}.`);

if (flag('push')) {
  const git = (...a) => execFileSync('git', a, { cwd: root, stdio: 'inherit' });
  git('add', `issues/${slug}`);
  git('commit', '-m', `Add Week ${week}, ${year}`);
  git('push');
  console.log('Pushed. Vercel will redeploy in about a minute.');
}
