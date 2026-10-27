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
home = open(os.path.join(root, "dist", "index.html"), encoding="utf8").read()
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
print(f"{4 - len(bad)}/4 passed"); sys.exit(1 if bad else 0)
