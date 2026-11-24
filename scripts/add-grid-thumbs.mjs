#!/usr/bin/env node
// Adds the V5 grid's small copies (see gridthumbs.mjs) to posts that already exist.
// Usage: node scripts/add-grid-thumbs.mjs [issues/2024-w08 ...]    (no arguments = every post)
// Safe to run again: it rebuilds the copies from the originals and never changes the originals.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { makeGridThumbs } from './gridthumbs.mjs';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const issues = path.join(root, 'issues');
const args = process.argv.slice(2).map((a) => path.basename(a));
const dirs = fs.readdirSync(issues).filter((d) => /^\d{4}-w\d{2}$/.test(d) && (!args.length || args.includes(d))).sort();
let bytes = 0, count = 0;
for (const d of dirs) {
  const dir = path.join(issues, d);
  const metaPath = path.join(dir, 'issue.json');
  const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
  for (const [i, im] of meta.images.entries()) {
    const g = await makeGridThumbs(dir, im, String(i + 1).padStart(2, '0'));
    Object.assign(im, g);
    for (const k of Object.keys(g)) bytes += fs.statSync(path.join(dir, g[k].file)).size;
    count++;
  }
  fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2) + '\n');
}
console.log(`${count} images in ${dirs.length} posts: grid copies total ${(bytes / 1048576).toFixed(1)} MB`);
