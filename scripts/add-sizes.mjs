#!/usr/bin/env node
// Adds the lighter phone / desktop copies (see variants.mjs) to posts that already exist.
// Usage: node scripts/add-sizes.mjs [issues/2024-w08 ...]    (no arguments = every post)
// Safe to run again: it rebuilds the copies from the originals and never changes the originals.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { makeVariants } from './variants.mjs';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const issues = path.join(root, 'issues');
const args = process.argv.slice(2).map((a) => path.basename(a));
const dirs = fs.readdirSync(issues).filter((d) => /^\d{4}-w\d{2}$/.test(d) && (!args.length || args.includes(d))).sort();
let before = 0, after = 0;
for (const d of dirs) {
  const dir = path.join(issues, d);
  const metaPath = path.join(dir, 'issue.json');
  const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
  let b = 0, a = 0, made = 0;
  for (const [i, im] of meta.images.entries()) {
    const n = String(i + 1).padStart(2, '0');
    for (const k of ['m', 'l']) { if (im[k]) fs.rmSync(path.join(dir, im[k].file), { force: true }); delete im[k]; }
    const v = await makeVariants(dir, im, n);
    if (v.m) im.m = v.m;
    if (v.l) im.l = v.l;
    const orig = fs.statSync(path.join(dir, im.file)).size;
    b += orig;
    // what a phone (m) and a desktop (l) would download for this image
    a += v.m ? fs.statSync(path.join(dir, v.m.file)).size : orig;
    if (v.m || v.l) made++;
  }
  fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2) + '\n');
  before += b; after += a;
  console.log(`${d}: ${made}/${meta.images.length} images got lighter copies; phone download ${(b / 1048576).toFixed(1)} MB -> ${(a / 1048576).toFixed(1)} MB`);
}
console.log(`TOTAL phone download: ${(before / 1048576).toFixed(0)} MB -> ${(after / 1048576).toFixed(0)} MB`);
