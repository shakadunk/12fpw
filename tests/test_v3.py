"""V3 preview page (/v3/). Desktop: blank top zone sized to ~1.5 rows, hover preview, click opens the week
centred on the clicked image. Phones: no blank zone, 4 rows of 3 per week with uncropped ratios, tap to bring
a photo forward over the blurred grid, tap again to open.   Run after building:  python3 tests/test_v3.py"""
import subprocess, time, os, sys
from playwright.sync_api import sync_playwright

proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
shots = os.path.join(proj, "tests", "shots")
os.makedirs(shots, exist_ok=True)
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=proj, env={**os.environ, "PORT": "3277"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3277"
res = []
def check(name, cond, extra=""):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))

slugs = sorted((d for d in os.listdir(os.path.join(proj, "issues")) if d[:4].isdigit()), key=lambda s: (int(s[:4]), int(s.split("-w")[1])), reverse=True)
N = len(slugs)
years = sorted({int(s[:4]) for s in slugs}, reverse=True)

with sync_playwright() as pw:
    br = pw.chromium.launch()

    # ---------------- desktop ----------------
    pg = br.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(B + "/v3/", wait_until="load")
    pg.wait_for_timeout(1200)

    g = pg.evaluate("""() => {
      const rows = [...document.querySelectorAll('.week-row')];
      const cells = document.querySelectorAll('.grid-cell img');
      const ov = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--overlay-h'));
      const yh = document.querySelector('.year-header').getBoundingClientRect();
      const r0 = rows[0].getBoundingClientRect();
      return {rows: rows.length, cells: cells.length,
              sections: [...document.querySelectorAll('.year-section')].map(s => s.dataset.year),
              perRow: rows.map(r => r.querySelectorAll('.grid-cell').length),
              overlay: ov, vh: innerHeight, row0Top: r0.top, row0H: r0.height,
              yearTop: yh.top, overflow: document.documentElement.scrollWidth > innerWidth + 1,
              topOverlayShown: getComputedStyle(document.querySelector('.top-overlay')).display !== 'none'};
    }""")
    check("61 week rows", g["rows"] == N, g["rows"])
    check("732 grid cells", g["cells"] == N * 12, g["cells"])
    check("one section per year, newest first", g["sections"] == [str(y) for y in years], g["sections"])
    check("every week has 12 images", set(g["perRow"]) == {12}, set(g["perRow"]))
    check("blank top zone present", g["topOverlayShown"])
    visible = g["vh"] - g["overlay"]
    check("grid zone is about 1.5 rows", 1.2 * g["row0H"] <= visible <= 1.9 * g["row0H"], (visible, g["row0H"]))
    check("grid zone at most 45% of the screen", visible <= g["vh"] * 0.45 + 2, (visible, g["vh"]))
    check("year label pinned below the blank zone", g["yearTop"] >= g["overlay"] - 1, (g["yearTop"], g["overlay"]))
    check("no sideways scrolling at 1440", not g["overflow"])
    pg.screenshot(path=os.path.join(shots, "v3-desktop-landing.png"))

    # hover shows the full-size copy, not the 700px thumbnail
    first = pg.locator(".grid-cell img").first
    first.hover()
    pg.wait_for_timeout(600)
    hv = pg.evaluate("""() => {
      const p = document.getElementById('hoverPreview'), i = document.getElementById('previewImg');
      return {visible: p.classList.contains('visible'), src: i.getAttribute('src'), nw: i.naturalWidth,
              box: i.getBoundingClientRect().height, overlay: parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--overlay-h'))};
    }""")
    check("hover shows the preview", hv["visible"])
    check("preview uses a full-size copy, not the -t thumbnail", hv["src"] and not hv["src"].endswith("-t.jpg"), hv["src"])
    check("preview sits inside the blank zone", hv["box"] <= hv["overlay"] + 1, (hv["box"], hv["overlay"]))
    pg.screenshot(path=os.path.join(shots, "v3-desktop-hover.png"))

    # click image 5 of a week: the post opens with that image centred
    row = pg.locator('.week-row:has(.grid-cell img[data-k="2024-5"])')
    img5 = pg.locator('.grid-cell img[data-k="2024-5"][data-n="5"]')
    img5.hover()
    pg.wait_for_timeout(400)
    img5.click()
    pg.wait_for_timeout(1400)
    po = pg.evaluate("""() => {
      const v = document.getElementById('postView'), st = document.getElementById('postStack');
      const n5 = st.children[4];
      const r = n5.getBoundingClientRect();
      const imgs = [...st.querySelectorAll('img')];
      return {open: v.classList.contains('open'), shown: v.classList.contains('shown'),
              head: document.getElementById('postHead').innerText.replace(/\\s+/g,' ').trim(),
              count: imgs.length, hash: location.hash,
              centreOff: (r.top + r.height/2) - innerHeight/2,
              linked: [...st.children].filter(c => c.tagName === 'A').length,
              href: n5.tagName === 'A' ? n5.getAttribute('href') : '',
              target: n5.tagName === 'A' ? n5.getAttribute('target') : '',
              text: document.getElementById('postText').innerText.trim().slice(0, 40),
              scrim: document.getElementById('postScrim').classList.contains('fx')};
    }""")
    check("click opens the week", po["open"] and po["shown"])
    check("heading names the week", po["head"] == "Week 5 2024", po["head"])
    check("post shows 12 images", po["count"] == 12, po["count"])
    check("address hash set", po["hash"] == "#2024-w5-i5", po["hash"])
    check("clicked image is centred", abs(po["centreOff"]) < 60, po["centreOff"])
    check("post images carry the reverse-image link", po["linked"] == 12, po["linked"])
    check("link goes to Google Lens in a new tab", "lens.google.com" in (po["href"] or "") and po["target"] == "_blank", po["href"])
    check("the week's own text is shown", len(po["text"]) > 0, po["text"])
    check("page behind is blurred and darkened", po["scrim"])
    pg.screenshot(path=os.path.join(shots, "v3-desktop-post.png"))

    # a tall portrait must land at the size it had in the preview: no scaling, never taller than the screen
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(600)
    portrait = pg.locator('.grid-cell img[data-k="2024-9"][data-n="1"]')
    portrait.hover()
    pg.wait_for_timeout(500)
    before = pg.evaluate("""() => {
      const i = document.getElementById('previewImg'), b = i.getBoundingClientRect();
      const s = Math.min(b.width / i.naturalWidth, b.height / i.naturalHeight);
      return {w: i.naturalWidth * s, h: i.naturalHeight * s, boxW: b.width, boxH: b.height, vh: innerHeight};
    }""")
    portrait.click()
    pg.wait_for_timeout(1500)
    after = pg.evaluate("""() => {
      const r = document.getElementById('postStack').children[0];
      const img = r.tagName === 'IMG' ? r : r.querySelector('img');
      const b = img.getBoundingClientRect();
      const all = [...document.querySelectorAll('#postStack img')].map(i => i.getBoundingClientRect());
      return {w: b.width, h: b.height, maxH: Math.max(...all.map(x => x.height)), maxW: Math.max(...all.map(x => x.width)),
              ratioOk: Math.abs(b.width / b.height - img.naturalWidth / img.naturalHeight) < 0.01};
    }""")
    check("portrait is tall in the preview (taller than wide)", before["h"] > before["w"], before)
    check("post image has the same width as in the preview", abs(after["w"] - before["w"]) < 2, (before, after))
    check("post image has the same height as in the preview", abs(after["h"] - before["h"]) < 2, (before, after))
    check("no post image taller than the preview box", after["maxH"] <= before["boxH"] + 1, (after, before))
    check("no post image wider than the preview box", after["maxW"] <= before["boxW"] + 1, (after, before))
    check("no post image taller than the screen", after["maxH"] <= before["vh"], (after, before))
    check("post image keeps its true proportions", after["ratioOk"], after)
    pg.screenshot(path=os.path.join(shots, "v3-desktop-portrait-post.png"))

    # a stray second click right after opening must not fire the image link
    guard = pg.evaluate("() => document.getElementById('postStack').classList.contains('guard')")
    check("link guard has lifted by now (600ms)", not guard)

    pg.keyboard.press("Escape")
    pg.wait_for_timeout(600)
    cl = pg.evaluate("() => ({open: document.getElementById('postView').classList.contains('open'), hash: location.hash})")
    check("Esc closes the post", not cl["open"], cl)

    # a direct link opens straight to that image
    pg.goto(B + "/v3/#2023-w40-i9", wait_until="load")
    pg.wait_for_timeout(1200)
    dl = pg.evaluate("""() => {
      const st = document.getElementById('postStack');
      const r = st.children[8].getBoundingClientRect();
      return {open: document.getElementById('postView').classList.contains('open'),
              head: document.getElementById('postHead').innerText.replace(/\\s+/g,' ').trim(),
              off: (r.top + r.height/2) - innerHeight/2};
    }""")
    check("direct link opens the right week", dl["open"] and dl["head"] == "Week 40 2023", dl)
    check("direct link centres the right image", abs(dl["off"]) < 60, dl["off"])

    # weeks of original photography have no reverse-image links
    pg.goto(B + "/v3/#2023-w21-i1", wait_until="load")
    pg.wait_for_timeout(900)
    nl = pg.evaluate("() => [...document.getElementById('postStack').children].filter(c => c.tagName === 'A').length")
    check("all-original week has no image links", nl == 0, nl)
    pg.close()

    # ---------------- phone ----------------
    ph = br.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    ph.goto(B + "/v3/", wait_until="load")
    ph.wait_for_timeout(1200)
    m = ph.evaluate("""() => {
      const row = document.querySelector('.week-row');
      const ul = row.querySelector('.week-images');
      const cs = getComputedStyle(ul);
      const cells = [...ul.querySelectorAll('img')].map(i => i.getBoundingClientRect());
      const tops = [...new Set(cells.map(c => Math.round(c.top)))];
      return {topOverlay: getComputedStyle(document.querySelector('.top-overlay')).display,
              archiveTop: document.getElementById('archive').getBoundingClientRect().top,
              cols: cs.gridTemplateColumns.split(' ').length,
              rows: tops.length, count: cells.length,
              heights: cells.slice(0, 6).map(c => Math.round(c.height)),
              widths: cells.slice(0, 3).map(c => Math.round(c.width)),
              overflow: document.documentElement.scrollWidth > innerWidth + 1};
    }""")
    check("no blank zone on a phone", m["topOverlay"] == "none", m["topOverlay"])
    check("grid starts near the top", m["archiveTop"] < 300, m["archiveTop"])
    check("3 across", m["cols"] == 3, m["cols"])
    check("4 rows of 3 per week", m["rows"] == 4 and m["count"] == 12, (m["rows"], m["count"]))
    check("ratios kept uncropped (heights differ)", len(set(m["heights"])) > 1, m["heights"])
    check("no sideways scrolling at 390", not m["overflow"])
    ph.screenshot(path=os.path.join(shots, "v3-phone-landing.png"))

    # first tap brings the photo forward over the blurred grid
    t5 = ph.locator('.grid-cell img[data-k="2024-5"][data-n="5"]')
    t5.scroll_into_view_if_needed()
    ph.wait_for_timeout(300)
    t5.tap()
    ph.wait_for_timeout(600)
    tp = ph.evaluate("""() => {
      const p = document.getElementById('hoverPreview'), i = document.getElementById('previewImg');
      const s = document.getElementById('tapScrim');
      return {visible: p.classList.contains('visible'), scrim: s.classList.contains('on'),
              blur: getComputedStyle(s).backdropFilter, src: i.getAttribute('src'),
              post: document.getElementById('postView').classList.contains('open')};
    }""")
    check("first tap brings the photo forward", tp["visible"])
    check("grid behind it is blurred", tp["scrim"] and "blur" in (tp["blur"] or ""), tp["blur"])
    check("first tap does not open the week", not tp["post"])
    check("phone preview uses the phone copy", tp["src"] and not tp["src"].endswith("-t.jpg"), tp["src"])
    ph.screenshot(path=os.path.join(shots, "v3-phone-tapped.png"))

    # second tap opens the week at that image
    ph.locator("#previewImg").tap()
    ph.wait_for_timeout(1400)
    mp = ph.evaluate("""() => {
      const st = document.getElementById('postStack');
      const r = st.children[4].getBoundingClientRect();
      return {open: document.getElementById('postView').classList.contains('open'),
              head: document.getElementById('postHead').innerText.replace(/\\s+/g,' ').trim(),
              off: (r.top + r.height/2) - innerHeight/2, hash: location.hash,
              scrim: document.getElementById('postScrim').classList.contains('fx')};
    }""")
    check("second tap opens the week", mp["open"] and mp["head"] == "Week 5 2024", mp)
    check("opens centred on the tapped image", abs(mp["off"]) < 60, mp["off"])
    check("same blur/fade on a phone", mp["scrim"])
    ph.screenshot(path=os.path.join(shots, "v3-phone-post.png"))

    ph.go_back()
    ph.wait_for_timeout(700)
    bk = ph.evaluate("() => ({open: document.getElementById('postView').classList.contains('open'), hash: location.hash})")
    check("Back returns to the grid", not bk["open"], bk)
    ph.close()
    br.close()

srv.terminate()
print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
