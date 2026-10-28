"""Checks the per-image Google reverse-image-search links and the italic preface style (static HTML, no browser).
Run:  python3 tests/test_links.py   (it builds the site twice into dist/; the last build is the normal one)"""
import os, re, subprocess, sys, urllib.parse
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def build(site_url):
    env = dict(os.environ); env.pop("VERCEL_PROJECT_PRODUCTION_URL", None)
    if site_url: env["SITE_URL"] = site_url
    else: env.pop("SITE_URL", None)
    subprocess.run(["node", "build.mjs"], cwd=root, env=env, check=True, stdout=subprocess.DEVNULL)
bad = []
def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok: bad.append(name)

build("https://example.test")
slugs = sorted((d for d in os.listdir(os.path.join(root, "issues")) if d[:4].isdigit()), key=lambda s: (int(s[:4]), int(s.split("-w")[1])), reverse=True)
y, w = slugs[0].split("-w")
home = open(os.path.join(root, "dist", y, f"week-{int(w)}", "index.html"), encoding="utf8").read()   # the newest week's own page
links = re.findall(r'<a class="img-link" href="([^"]+)" target="_blank" rel="noopener"', home)
check("every one of the 12 images has a link", len(links) == 12)
ok = True
for h in links:
    h = h.replace("&amp;", "&")
    u = urllib.parse.urlparse(h)
    img = urllib.parse.parse_qs(u.query).get("url", [""])[0]
    path = urllib.parse.urlparse(img).path
    ok &= u.netloc == "lens.google.com" and u.path == "/uploadbyurl" and img.startswith("https://example.test/") and os.path.exists(os.path.join(root, "dist", path.lstrip("/")))
check("each link is a Google Lens search of that image's public address, and the file exists", ok)

build(None)
home = open(os.path.join(root, "dist", "index.html"), encoding="utf8").read()
check("without a site address there are no image links (they would not work)", "img-link" not in home)

# the preface style
sys.path.insert(0, root)
html = open(os.path.join(root, "build.mjs"), encoding="utf8").read()
check("preface rule present in build.mjs and style.css", "class=\"preface\"" in html and "p.preface" in open(os.path.join(root, "static", "style.css"), encoding="utf8").read())
# a week marked lens:false in its issue.json (all original photography, e.g. 2023 Week 21) gets no image-search links
build("https://example.test")
w21 = open(os.path.join(root, "dist", "2023", "week-21", "index.html"), encoding="utf8").read()
w20 = open(os.path.join(root, "dist", "2023", "week-20", "index.html"), encoding="utf8").read()
check("Week 21 (original photography, lens:false) has no image-search links", "img-link" not in w21 and w21.count("<figure") == 12)
check("Week 20 still has all 12 image-search links", w20.count('class="img-link"') == 12)

# custom per-image links (links.txt, e.g. songs): built in a throwaway copy so the real site is untouched
import shutil, tempfile
tmp = tempfile.mkdtemp()
subprocess.run(f"tar --exclude=.git --exclude=dist --exclude=node_modules --exclude=issues -cf - . | tar -xf - -C {tmp}", shell=True, cwd=root, check=True)
os.makedirs(os.path.join(tmp, "issues"))
shutil.copytree(os.path.join(root, "issues", "2023-w27"), os.path.join(tmp, "issues", "2023-w27"))
import json
meta = json.load(open(os.path.join(tmp, "issues", "2023-w27", "issue.json")))
for i, im in enumerate(meta["images"]):
    if i != 2: im["href"] = f"https://www.youtube.com/watch?v=TEST{i + 1:02d}"
json.dump(meta, open(os.path.join(tmp, "issues", "2023-w27", "issue.json"), "w"))
subprocess.run(["node", "build.mjs"], cwd=tmp, env={**os.environ, "SITE_URL": "https://example.test"}, check=True, stdout=subprocess.DEVNULL)
pg = open(os.path.join(tmp, "dist", "2023", "week-27", "index.html"), encoding="utf8").read()
check("custom image links: each image opens its own address in a new tab", 'href="https://www.youtube.com/watch?v=TEST01" target="_blank" rel="noopener" title="Open link"' in pg and pg.count("youtube.com/watch?v=TEST") == 11)
check("custom image links: an image without one keeps the image-search link", "lens.google.com" in pg and pg.count("lens.google.com") == 1)
shutil.rmtree(tmp, ignore_errors=True)

# links inside the text (Week 6 and Week 9 carry YouTube links; write [words](https://...) in text.txt)
build(None)
w6 = open(os.path.join(root, "dist", "2023", "week-6", "index.html"), encoding="utf8").read()
w9 = open(os.path.join(root, "dist", "2023", "week-9", "index.html"), encoding="utf8").read()
check("Week 6 text has its link: 'that one news clip' -> youtu.be", '<a class="text-link" href="https://youtu.be/eeE17aUFWvg?t=73" target="_blank" rel="noopener">that one news clip</a>' in w6)
check("Week 9 text has its link: 'video' -> youtube", '<a class="text-link" href="https://www.youtube.com/watch?v=zrqqrQmeQS4" target="_blank" rel="noopener">video</a>' in w9)
check("no raw [words](address) markup is left on any page", not any(re.search(r"\]\(https?://", open(os.path.join(dp, f), encoding="utf8").read()) for dp, _, fs in os.walk(os.path.join(root, "dist")) for f in fs if f.endswith(".html")))
css = open(os.path.join(root, "static", "style.css"), encoding="utf8").read()
check("link style: underlined and slightly heavier (weight 500)", re.search(r"\.text a\.text-link\s*\{[^}]*font-weight:\s*500[^}]*underline", css) is not None)
print(f"{12 - len(bad)}/12 passed"); sys.exit(1 if bad else 0)
