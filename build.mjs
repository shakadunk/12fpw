// Static site generator for 12 Frames Per Week. No dependencies.
//   node build.mjs   →   dist/
// Posts live in issues/<year>-w<week>/ (issue.json, text.txt, images). Make them with scripts/add-post.mjs.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(root, 'dist');
const issuesDir = path.join(root, 'issues');

const cfg = {
  name: '12 Frames Per Week', short: '12FPW', blurb: '', siteUrl: '', defaultView: 'scroll', subscribeAction: '',
  ...JSON.parse(fs.readFileSync(path.join(root, 'site.config.json'), 'utf8')),
};
if (!cfg.siteUrl) {
  if (process.env.SITE_URL) cfg.siteUrl = process.env.SITE_URL;
  else if (process.env.VERCEL_PROJECT_PRODUCTION_URL) cfg.siteUrl = `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`;
}
cfg.siteUrl = cfg.siteUrl.replace(/\/+$/, '');
if (!['scroll', 'grid', 'calendar'].includes(cfg.defaultView)) cfg.defaultView = 'scroll';
const INITIAL_POSTS = 2; // posts rendered into the Scroll view before infinite scroll takes over

// ---------- helpers ----------
const esc = (s = '') => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const dims = (w, h) => (w && h ? ` width="${w}" height="${h}"` : '');
const write = (rel, html) => { const out = path.join(dist, rel); fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, html); };
const copyDir = (src, dst) => {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dst, e.name);
    e.isDirectory() ? copyDir(s, d) : fs.copyFileSync(s, d);
  }
};
// Thursday of ISO week `week` of `year`, as YYYY-MM-DD (UTC). The Thursday decides which year and month
// a week belongs to (so Week 1 of 2025, which starts Dec 30, files under January 2025).
// Put "date": "YYYY-MM-DD" in a post's issue.json to use the real send date instead.
function isoThursday(year, week) {
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const d = new Date(jan4);
  d.setUTCDate(jan4.getUTCDate() - ((jan4.getUTCDay() + 6) % 7) + (week - 1) * 7 + 3);
  return d.toISOString().slice(0, 10);
}
const monthKey = (iso) => iso.slice(0, 7);
const monthLabel = (iso) => new Date(iso + 'T00:00:00Z').toLocaleDateString('en-US', { timeZone: 'UTC', month: 'long', year: 'numeric' });

// ---------- load posts ----------
function loadPosts() {
  if (!fs.existsSync(issuesDir)) return [];
  const posts = [];
  for (const d of fs.readdirSync(issuesDir, { withFileTypes: true })) {
    const m = d.isDirectory() && d.name.match(/^(\d{4})-w(\d{1,2})$/i);
    if (!m) continue;
    const dir = path.join(issuesDir, d.name);
    const metaPath = path.join(dir, 'issue.json');
    if (!fs.existsSync(metaPath)) { console.warn(`! ${d.name}: no issue.json; skipped`); continue; }
    let meta;
    try { meta = JSON.parse(fs.readFileSync(metaPath, 'utf8')); } catch (e) { console.warn(`! ${d.name}/issue.json is not valid JSON; skipped`); continue; }
    const year = Number(m[1]), week = Number(m[2]);
    const images = (meta.images || []).filter((im) => {
      const ok = im.file && fs.existsSync(path.join(dir, im.file));
      if (!ok) console.warn(`! ${d.name}: missing image ${im.file}; skipped`);
      return ok;
    });
    if (!images.length) { console.warn(`! ${d.name}: no images; skipped`); continue; }
    const textPath = path.join(dir, 'text.txt');
    const text = fs.existsSync(textPath) ? fs.readFileSync(textPath, 'utf8').replace(/\r\n/g, '\n').trim() : '';
    const hero = Math.min(Math.max(Number.isInteger(meta.hero) ? meta.hero : 0, 0), images.length - 1);
    const date = /^\d{4}-\d{2}-\d{2}$/.test(meta.date || '') ? meta.date : isoThursday(year, week);
    posts.push({ slug: d.name, dir, year, week, date, text, images, hero, url: `/${year}/week-${week}/` });
  }
  posts.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : b.week - a.week));
  return posts;
}

// ---------- templates ----------
const paragraphs = (text) => text.split(/\n{2,}/).filter(Boolean).map((p) => `<p>${esc(p).replace(/\n/g, '<br>')}</p>`).join('\n');
const weekLabel = (p) => `Week ${p.week}`;

function postArticle(p, { eager = false, heading = 'h2' } = {}) {
  const h = p.images[0];
  return `<article class="post" id="week-${p.year}-${p.week}">
  <header class="post-head">
    <${heading} class="week"><a href="${p.url}">${esc(weekLabel(p))}</a> <span class="year">${p.year}</span></${heading}>
  </header>
${p.text ? `  <div class="text">\n${paragraphs(p.text)}\n  </div>\n` : ''}${p.images.map((im, i) => `  <figure><img src="${p.url}${esc(im.file)}" alt="${esc(im.alt || `Image ${i + 1} of ${p.images.length}, ${weekLabel(p)} ${p.year}`)}"${dims(im.w, im.h)} loading="${eager && i === 0 ? 'eager' : 'lazy'}" decoding="async"></figure>`).join('\n')}
</article>`;
}

function layout({ title, description, path: urlPath, body, ogImage, page }) {
  const full = title ? `${title} — ${cfg.name}` : cfg.name;
  const desc = description || cfg.blurb || cfg.name;
  const abs = (u) => (cfg.siteUrl ? cfg.siteUrl + u : u);
  return `<!doctype html>
<html lang="en" data-theme="dark" data-view="${cfg.defaultView}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${esc(full)}</title>
<meta name="description" content="${esc(desc)}">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#000000">
<meta property="og:title" content="${esc(full)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:type" content="website">
${cfg.siteUrl ? `<meta property="og:url" content="${esc(abs(urlPath))}">` : ''}
${ogImage && cfg.siteUrl ? `<meta property="og:image" content="${esc(abs(ogImage))}"><meta name="twitter:card" content="summary_large_image">` : ''}
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">
<script>
(function(){var d=document.documentElement;try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark')d.dataset.theme=t;
var h=location.hash.replace('#','');var v=(h==='scroll'||h==='grid'||h==='calendar')?h:localStorage.getItem('archiveView');
if(v==='scroll'||v==='grid'||v==='calendar')d.dataset.view=v;}catch(e){}})();
</script>
</head>
<body data-page="${esc(page || '')}">
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <a class="logo" href="/" aria-label="${esc(cfg.name)}"><img src="/logo.png" alt="12 Frames Per Week" width="120" height="56"></a>
  <nav aria-label="Main">
    <a href="/archive/"${page === 'archive' ? ' aria-current="page"' : ''}>Archive</a>
    <a href="/#subscribe">Subscribe</a>
    <button type="button" class="link-btn" id="theme-toggle"></button>
  </nav>
</header>
<main id="main">
${body}
</main>
${page === 'home'
  ? `<footer class="site-footer site-footer-date">
  <time class="today" id="today"></time>
</footer>`
  : `<footer class="site-footer">
  <span>${esc(cfg.name)}</span>
  <span><a href="/archive/">Archive</a><a href="/#subscribe">Subscribe</a></span>
</footer>`}
<script src="/app.js" defer></script>
</body>
</html>
`;
}

function subscribeForm() {
  const a = cfg.subscribeAction;
  return `<form class="signup" id="subscribe-form" action="${esc(a)}" method="post"${a ? '' : ' data-unconfigured'} novalidate>
    <label class="sr" for="email">Email address</label>
    <input type="email" id="email" name="email" placeholder="Email address" autocomplete="email" required>
    <button type="submit">Subscribe</button>
  </form>
  <p class="form-note" id="form-note" role="status"></p>`;
}

function homePage(posts) {
  const p = posts[0];
  const hero = p ? p.images[p.hero] : null;
  return layout({
    title: '', path: '/', page: 'home', ogImage: hero ? p.url + (hero.thumb || hero.file) : '',
    body: `<section class="home" id="subscribe">
  <p class="display">${esc(cfg.blurb)}</p>
  ${subscribeForm()}
</section>
${p ? `<section class="latest" aria-label="Latest post">
  <a href="${p.url}"><img src="${p.url}${esc(hero.file)}" alt="${esc(hero.alt || `Image ${p.hero + 1} of ${p.images.length}, ${weekLabel(p)} ${p.year}`)}"${dims(hero.w, hero.h)} fetchpriority="high" decoding="async"><span class="cap">Latest: ${esc(weekLabel(p))}, ${p.year}</span></a>
</section>` : ''}`,
  });
}

const thumbCell = (p) => {
  const h = p.images[p.hero];
  return `    <li><a href="${p.url}"><img src="${p.url}${esc(h.thumb || h.file)}" alt="${esc(h.alt || `${weekLabel(p)}, ${p.year}`)}"${dims(h.tw || h.w, h.th || h.h)} loading="lazy" decoding="async"><span class="tag"><b>${esc(weekLabel(p))}</b> ${p.year}</span></a></li>`;
};

function archivePage(posts) {
  const grid = `<ul class="grid">\n${posts.map(thumbCell).join('\n')}\n  </ul>`;
  const months = [];
  for (const p of posts) {
    const k = monthKey(p.date);
    let m = months[months.length - 1];
    if (!m || m.key !== k) { m = { key: k, label: monthLabel(p.date), items: [] }; months.push(m); }
    m.items.push(p);
  }
  const calendar = months.map((m) => `<section class="month">
  <h2 class="label">${esc(m.label)}</h2>
  <ul class="grid">
${m.items.map(thumbCell).join('\n')}
  </ul>
</section>`).join('\n');
  const first = posts.slice(0, INITIAL_POSTS);
  const manifest = JSON.stringify(posts.map((p) => p.url));
  const empty = '<p class="empty">No posts yet.</p>';
  return layout({
    title: 'Archive', path: '/archive/', page: 'archive',
    body: `<div class="archive-bar">
  <h1 class="label">Archive <span class="mute">(${posts.length})</span></h1>
  <div class="view-toggle" role="group" aria-label="Archive view">
    <button type="button" class="link-btn" data-view="scroll">Scroll</button>
    <button type="button" class="link-btn" data-view="grid">Grid</button>
    <button type="button" class="link-btn" data-view="calendar">Calendar</button>
  </div>
</div>
<div class="slimbar" id="slimbar">
  <div class="slim-view">
    <button type="button" class="link-btn" id="slim-view-btn" aria-haspopup="true" aria-expanded="false" aria-controls="slim-menu">View</button>
    <ul class="slim-menu" id="slim-menu" hidden>
      <li><button type="button" class="link-btn" data-view="scroll">Scroll</button></li>
      <li><button type="button" class="link-btn" data-view="grid">Grid</button></li>
      <li><button type="button" class="link-btn" data-view="calendar">Calendar</button></li>
    </ul>
  </div>
  <button type="button" class="link-btn" id="slim-top">Top</button>
</div>
<div class="view view-scroll">
  <div class="col" id="scroll-list" data-loaded="${first.length}">
${first.length ? first.map((p, i) => postArticle(p, { eager: i === 0 })).join('\n') : empty}
  </div>
  <div class="col scroll-end" id="scroll-end"><span id="scroll-status" class="label"></span></div>
  <noscript><p class="col label">Turn on JavaScript to keep scrolling, or use the Grid and Calendar views.</p></noscript>
</div>
<div class="view view-grid">
  <div class="wide">${posts.length ? grid : empty}</div>
</div>
<div class="view view-calendar">
  <div class="wide">${posts.length ? calendar : empty}</div>
</div>
<script type="application/json" id="manifest">${manifest.replace(/</g, '\\u003c')}</script>`,
  });
}

function postPage(p, newer, older) {
  const nav = (q, dir) => (q ? `<a href="${q.url}">${dir === 'older' ? '← ' : ''}${esc(weekLabel(q))}, ${q.year}${dir === 'newer' ? ' →' : ''}</a>` : '<span></span>');
  return layout({
    title: `${weekLabel(p)}, ${p.year}`, path: p.url, page: 'post', ogImage: p.url + (p.images[p.hero].thumb || p.images[p.hero].file),
    body: `<div class="col">
  <p class="back label"><a href="/archive/">← Archive</a></p>
${postArticle(p, { eager: true, heading: 'h1' })}
  <nav class="pager label" aria-label="Posts">
    ${nav(older, 'older')}
    ${nav(newer, 'newer')}
  </nav>
</div>`,
  });
}

// ---------- run ----------
fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });
copyDir(path.join(root, 'static'), dist);

const posts = loadPosts();
const seen = new Set();
for (const p of posts) { if (seen.has(p.url)) console.warn(`! duplicate post URL ${p.url}`); seen.add(p.url); }

write('index.html', homePage(posts));
write('archive/index.html', archivePage(posts));
posts.forEach((p, i) => {
  write(`${p.url.slice(1)}index.html`, postPage(p, posts[i - 1], posts[i + 1]));
  for (const f of fs.readdirSync(p.dir)) {
    if (/\.(jpe?g|png|webp|gif|avif)$/i.test(f)) fs.copyFileSync(path.join(p.dir, f), path.join(dist, p.url.slice(1), f));
  }
});
write('404.html', layout({ title: 'Not found', path: '/404', page: '404', body: `<section class="home"><p class="display">Not found.</p><p><a href="/">Home</a> &nbsp; <a href="/archive/">Archive</a></p></section>` }));

console.log(`Built ${posts.length} post${posts.length === 1 ? '' : 's'}, ${posts.reduce((a, p) => a + p.images.length, 0)} images → dist/`);
if (!cfg.subscribeAction) console.log('Note: subscribeAction is empty in site.config.json, so the signup form is not connected yet.');
