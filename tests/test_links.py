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
import json
def uses_lens(slug):   # a week whose images use the default Google Lens link (not original photography, no custom links)
    d = json.load(open(os.path.join(root, "issues", slug, "issue.json")))
    return d.get("lens") is not False and not any(im.get("href") for im in d["images"])
y, w = next(sl for sl in slugs if uses_lens(sl)).split("-w")
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
check("without a site address there are no Google Lens links (they would not work)", "lens.google.com" not in home)

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
    if i == 3: im["href"] = False       # "-" in links.txt: no link at all on this image
    elif i != 2: im["href"] = f"https://www.youtube.com/watch?v=TEST{i + 1:02d}"
json.dump(meta, open(os.path.join(tmp, "issues", "2023-w27", "issue.json"), "w"))
subprocess.run(["node", "build.mjs"], cwd=tmp, env={**os.environ, "SITE_URL": "https://example.test"}, check=True, stdout=subprocess.DEVNULL)
pg = open(os.path.join(tmp, "dist", "2023", "week-27", "index.html"), encoding="utf8").read()
check("custom image links: each image opens its own address in a new tab", 'href="https://www.youtube.com/watch?v=TEST01" target="_blank" rel="noopener" title="Open link"' in pg and pg.count("youtube.com/watch?v=TEST") == 10)
check("custom image links: an image without one keeps the image-search link", "lens.google.com" in pg and pg.count("lens.google.com") == 1)
fig4 = re.search(r'<figure id="img-2023-27-4">(.*?)</figure>', pg, re.S).group(1)
check("an image marked with a dash has no link at all (just the picture)", "<img" in fig4 and "<a " not in fig4)
shutil.rmtree(tmp, ignore_errors=True)

# the real Week 30: its first two images are original photography (no link), the rest keep the image-search link
build("https://example.test")
w30 = open(os.path.join(root, "dist", "2023", "week-30", "index.html"), encoding="utf8").read()
f30 = re.findall(r'<figure id="img-2023-30-\d+">(.*?)</figure>', w30, re.S)
check("Week 30: images 1 and 2 have no link, images 3 to 12 keep the Lens link", len(f30) == 12 and all("<a " not in f for f in f30[:2]) and all("lens.google.com" in f for f in f30[2:]))

# links inside the text (Week 6 and Week 9 carry YouTube links; write [words](https://...) in text.txt)
build(None)
w6 = open(os.path.join(root, "dist", "2023", "week-6", "index.html"), encoding="utf8").read()
w9 = open(os.path.join(root, "dist", "2023", "week-9", "index.html"), encoding="utf8").read()
check("Week 6 text has its link: 'that one news clip' -> youtu.be", '<a class="text-link" href="https://youtu.be/eeE17aUFWvg?t=73" target="_blank" rel="noopener">that one news clip</a>' in w6)
check("Week 9 text has its link: 'video' -> youtube", '<a class="text-link" href="https://www.youtube.com/watch?v=zrqqrQmeQS4" target="_blank" rel="noopener">video</a>' in w9)
check("no raw [words](address) markup is left on any page", not any(re.search(r"\]\(https?://", open(os.path.join(dp, f), encoding="utf8").read()) for dp, _, fs in os.walk(os.path.join(root, "dist")) for f in fs if f.endswith(".html")))
w33 = open(os.path.join(root, "dist", "2023", "week-33", "index.html"), encoding="utf8").read()
check("Week 33: the 'Archive' link goes to this site's archive in the same tab (no new tab, not the old 12fps.com)", '<a class="text-link" href="/archive/">Archive</a>' in w33 and "12fps.com" not in w33)
w52 = open(os.path.join(root, "dist", "2023", "week-52", "index.html"), encoding="utf8").read()
check("Week 52: the email link is a mailto link in the same tab", re.search(r'<a class="text-link" href="mailto:[^"]+">my personal inbox</a>', w52) is not None)
css = open(os.path.join(root, "static", "style.css"), encoding="utf8").read()
check("link style: underlined and slightly heavier (weight 500)", re.search(r"\.text a\.text-link\s*\{[^}]*font-weight:\s*500[^}]*underline", css) is not None)
print(f"{16 - len(bad)}/16 passed"); sys.exit(1 if bad else 0)
