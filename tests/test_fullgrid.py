"""GRID view (FULL only; the WEEKLY toggle was removed 2026-10-28).  Every image, newest week first, one week per row: 12 across on screens 900px and up
(week number + year in the left margin), 3 across (4 rows per week, label above) on smaller screens. Each image links to that image
inside its week's page.   Run after building:  python3 tests/test_fullgrid.py"""
import subprocess, time, os, sys, re
from playwright.sync_api import sync_playwright

proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=proj, env={**os.environ, "PORT": "3269"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3269"
res = []
def check(name, cond):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name)
slugs = sorted((d for d in os.listdir(os.path.join(proj, "issues")) if d[:4].isdigit()), key=lambda s: (int(s[:4]), int(s.split("-w")[1])), reverse=True)
N = len(slugs)
newest = (int(slugs[0][:4]), int(slugs[0].split("-w")[1]))

def geo(page):
    return page.evaluate("""() => {
      const weeks = [...document.querySelectorAll('.fg-week')];
      const row = (w) => w.querySelector('.fg-row');
      const a0 = weeks[0].querySelector('.fg-row a').getBoundingClientRect(), a1 = weeks[0].querySelectorAll('.fg-row a')[1].getBoundingClientRect();
      const r0 = row(weeks[0]).getBoundingClientRect(), r1 = row(weeks[1]).getBoundingClientRect();
      const lab = weeks[0].querySelector('.fg-label').getBoundingClientRect();
      const cols = getComputedStyle(row(weeks[0])).gridTemplateColumns.split(' ').length;
      return {weeks: weeks.length, cols, cell: [a0.width, a0.height], hgap: a1.left - a0.right, vgap: r1.top - r0.bottom,
              labelRight: lab.right, labelBottom: lab.bottom, rowLeft: r0.left, rowTop: r0.top, rowRight: r0.right,
              imgs: weeks.map(w => w.querySelectorAll('img').length), labels: weeks.map(w => w.querySelector('.fg-label').innerText.replace(/\\s+/g, ' ').trim()),
              rowHeight: r0.height, over: document.documentElement.scrollWidth > innerWidth + 1, vw: innerWidth};
    }""")

try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        # ---------- desktop 1440 ----------
        ctx = br.new_context(viewport={"width": 1440, "height": 900}); ctx.add_init_script("try{history.scrollRestoration='manual'}catch(e){}")
        pg = ctx.new_page(); pg.goto(B + "/archive/#grid"); pg.wait_for_load_state("networkidle")
        check("the GRID view shows the full grid, and there is no toggle or weekly grid any more", pg.is_visible(".fullgrid") and pg.locator(".grid-mode").count() == 0 and pg.locator(".view-grid .grid").count() == 0)
        g = geo(pg)
        check(f"one row per week ({N})", g["weeks"] == N)
        check("every week has 12 images", all(n == 12 for n in g["imgs"]))
        check("12 across on desktop", g["cols"] == 12)
        check("thumbnails are square and about 95 to 115px at 1440", abs(g["cell"][0] - g["cell"][1]) < 1 and 95 <= g["cell"][0] <= 115)
        check("3px between images, 14px between weeks", abs(g["hgap"] - 3) < 0.6 and abs(g["vgap"] - 14) < 1.5)
        check("labels are number and year only (no word Week), newest first", g["labels"][0] == f"{newest[1]} {newest[0]}" and all("week" not in l.lower() for l in g["labels"]) and g["labels"][-1].split()[0] == "1")
        check("label sits in the left margin of the row", g["labelRight"] <= g["rowLeft"] and g["rowLeft"] < 170)
        check("grid uses the full width (right edge about 40px from the screen edge)", 1440 - g["rowRight"] < 50)
        check("no sideways scrolling", not g["over"])
        check("no left inset any more (the corner LIGHT/DARK label is gone): the week labels start at the page margin", pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.fullgrid')).paddingLeft)") == 0)
        # click an image: lands on that image inside its week
        import json
        ims = json.load(open(os.path.join(proj, "issues", slugs[0], "issue.json")))["images"]
        k = next(i for i, im in enumerate(ims) if im["h"] / im["w"] <= 1.2) + 1   # the first image of the newest week that fits on screen (not a tall one)
        pg.locator(".fg-week").first.locator(".fg-row li").nth(k - 1).locator("a").click(); pg.wait_for_load_state("load"); pg.wait_for_timeout(800)
        check("click opens that week's page at that image (URL anchor)", pg.url.endswith(f"/{newest[0]}/week-{newest[1]}/#img-{newest[0]}-{newest[1]}-{k}"))
        def pos(pg, n):
            return pg.evaluate(f"(() => {{ const r = document.getElementById('img-{newest[0]}-{newest[1]}-{n}').getBoundingClientRect(); return {{top: r.top, bottom: r.bottom, h: r.height, vh: innerHeight, y: scrollY}}; }})()")
        q = pos(pg, k)
        check("that image is centred vertically on the screen after the click-through", q["h"] < q["vh"] - 40 and abs((q["top"] + q["bottom"]) / 2 - q["vh"] / 2) <= 3 and q["y"] > 500)
        # an image taller than the screen lines up just under the top edge instead
        import json
        tall = None   # newest week that has an image taller than the 900px screen at 640px wide
        for sl in slugs:
            for i, im in enumerate(json.load(open(os.path.join(proj, "issues", sl, "issue.json")))["images"]):
                if im["h"] / im["w"] > 1.5: tall = (int(sl[:4]), int(sl.split("-w")[1]), i + 1); break
            if tall: break
        pg.goto(f"{B}/{tall[0]}/week-{tall[1]}/#img-{tall[0]}-{tall[1]}-{tall[2]}"); pg.wait_for_load_state("load"); pg.wait_for_timeout(800)
        q = pg.evaluate(f"(() => {{ const r = document.getElementById('img-{tall[0]}-{tall[1]}-{tall[2]}').getBoundingClientRect(); return {{top: r.top, bottom: r.bottom, h: r.height, vh: innerHeight}}; }})()")
        check("an image taller than the screen starts near the top (about 16px down)", q["h"] > q["vh"] and 8 <= q["top"] <= 24)
        pg.goto(B + "/archive/#grid"); pg.wait_for_load_state("networkidle")
        # deep in the list: an older week
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(400)
        last = pg.locator(".fg-week").last
        href = last.locator(".fg-row li").nth(11).locator("a").get_attribute("href")
        check("image 12 of the oldest week links to its own anchor", href.endswith("/week-1/#img-2023-1-12") or re.search(r"/week-\d+/#img-\d{4}-\d+-12$", href))
        # switch back
        pg.evaluate("window.scrollTo(0, 0)")
        ctx.close()

        # ---------- breakpoint ----------
        for width, want in ((900, 12), (1200, 12), (899, 3), (768, 3)):
            ctx = br.new_context(viewport={"width": width, "height": 900}); pg = ctx.new_page()
            pg.add_init_script("try{localStorage.setItem('gridMode','weekly')}catch(e){}")   # an old saved WEEKLY choice must be ignored
            pg.goto(B + "/archive/#grid"); pg.wait_for_load_state("networkidle")
            g = geo(pg)
            check(f"{width}px wide: {want} across, no sideways scrolling", g["cols"] == want and not g["over"])
            ctx.close()

        # ---------- phone ----------
        ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = ctx.new_page(); pg.goto(B + "/archive/#grid"); pg.wait_for_load_state("networkidle")
        check("phone: the full grid shows and there is no toggle", pg.is_visible(".fullgrid") and pg.locator(".grid-mode").count() == 0)
        g = geo(pg)
        check("phone: 3 across, 4 rows of 3 per week", g["cols"] == 3 and abs(g["rowHeight"] - (4 * g["cell"][1] + 3 * g["hgap"])) < 2)
        check("phone: thumbnails about 118px, 2px apart", 112 <= g["cell"][0] <= 122 and abs(g["hgap"] - 2) < 0.6)
        check("phone: week number and year sit above each week", g["labelBottom"] <= g["rowTop"] and g["labels"][0] == f"{newest[1]} {newest[0]}")
        check("phone: 22px between weeks, no sideways scrolling", abs(g["vgap"] - (22 + 6 + 13)) < 8 and not g["over"])
        pg.locator(".fg-week").first.locator(".fg-row li").nth(2).locator("a").tap(); pg.wait_for_load_state("load"); pg.wait_for_timeout(800)
        check("phone: tapping an image jumps to it in the week", pg.url.endswith(f"#img-{newest[0]}-{newest[1]}-3") and pg.evaluate("window.scrollY") > 300)
        q = pos(pg, 3)
        check("phone: the tapped image is centred vertically on the screen", q["h"] < q["vh"] - 40 and abs((q["top"] + q["bottom"]) / 2 - q["vh"] / 2) <= 3)
        ctx.close()
        br.close()
finally:
    srv.terminate()
print(f"{sum(res)}/{len(res)} passed"); sys.exit(0 if all(res) else 1)
