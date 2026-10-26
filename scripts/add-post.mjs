// Create (or replace) one weekly post from a folder of images and a text file.
//
//   node scripts/add-post.mjs <folder> --year 2025 --week 3 [--text text.txt] [--hero 1] [--force] [--push]
//
// <folder> holds the 12 images (sorted by filename) and optionally text.txt.
// Images are resized (long edge 1600px, JPEG) and a thumbnail is made for the Grid view,
// so the repo stays small. Needs `npm install` once (for sharp).
// --hero is the image number (1 to 12) used as the thumbnail. Default is 1.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

let sharp;
try { sharp = require('sharp'); } catch {
  console.error('This script needs sharp. Run `npm install` in the project folder first.');
  process.exit(1);
}

const args = process.argv.slice(2);
const valueFlags = ['--year', '--week', '--text', '--hero'];
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

const images = [];
for (const [i, f] of files.entries()) {
  const n = String(i + 1).padStart(2, '0');
  const input = path.join(folder, f);
  const full = await sharp(input).rotate().flatten({ background: '#000000' })
    .resize({ width: 1600, height: 1600, fit: 'inside', withoutEnlargement: true })
    .jpeg({ quality: 82, mozjpeg: true }).toFile(path.join(dest, `${n}.jpg`));
  const thumb = await sharp(input).rotate().flatten({ background: '#000000' })
    .resize({ width: 700, withoutEnlargement: true })
    .jpeg({ quality: 78, mozjpeg: true }).toFile(path.join(dest, `${n}-t.jpg`));
  images.push({ file: `${n}.jpg`, w: full.width, h: full.height, thumb: `${n}-t.jpg`, tw: thumb.width, th: thumb.height, alt: '' });
}

fs.writeFileSync(path.join(dest, 'issue.json'), JSON.stringify({ year, week, hero, images }, null, 2) + '\n');
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
