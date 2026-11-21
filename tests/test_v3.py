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
    hidden = pg.evaluate("""() => {
      const el = document.elementFromPoint(innerWidth / 2, 120);
      return !(el && el.closest && el.closest('.grid-cell')); }""")
    check("the blank zone does not pass the mouse to thumbnails hidden behind it", hidden)
    visible = g["vh"] - g["overlay"]
    check("grid zone is about 1.5 rows", 1.2 * g["row0H"] <= visible <= 1.9 * g["row0H"], (visible, g["row0H"]))
    check("grid zone at most 45% of the screen", visible <= g["vh"] * 0.45 + 2, (visible, g["vh"]))
    check("year label pinned below the blank zone", g["yearTop"] >= g["overlay"] - 1, (g["yearTop"], g["overlay"]))
    check("no sideways scrolling at 1440", not g["overflow"])
    check("the window is the scroller, not <body>", pg.evaluate("() => document.documentElement.scrollHeight - innerHeight > 100"))
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

    # every photo gets the same width, a gentle step from the preview; a typical portrait still fits the screen
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(1000)   # closing is animated now
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
      return {w: b.width, h: b.height, maxH: Math.max(...all.map(x => x.height)), maxW: Math.max(...all.map(x => x.width)), minW: Math.min(...all.map(x => x.width)),
              ratioOk: Math.abs(b.width / b.height - img.naturalWidth / img.naturalHeight) < 0.01};
    }""")
    check("portrait is tall in the preview (taller than wide)", before["h"] > before["w"], before)
    check("every post image has the same width (portraits and landscapes alike)", after["maxW"] - after["minW"] < 1, after)
    check("that width sits between the preview's height and width (a gentle zoom)", before["boxH"] - 1 <= after["w"] <= before["boxW"] + 1, (before, after))
    check("and well short of the old full column (816px wide)", after["w"] < 700, after)
    check("a typical 4:5 portrait still fits on the screen", after["h"] <= before["vh"], (after, before))
    check("no post image wider than the 816px column", after["maxW"] <= 817, after)
    check("post image keeps its true proportions", after["ratioOk"], after)
    pg.screenshot(path=os.path.join(shots, "v3-desktop-portrait-post.png"))

    # a stray second click right after opening must not fire the image link
    guard = pg.evaluate("() => document.getElementById('postStack').classList.contains('guard')")
    check("link guard has lifted by now (600ms)", not guard)

    pg.keyboard.press("Escape")
    pg.wait_for_timeout(1000)   # closing is animated now
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
    # leaving a post: the photo you are on flies back into the preview zone and stays there
    pg.goto(B + "/v3/", wait_until="load")
    pg.wait_for_timeout(1200)
    t2 = pg.locator('.grid-cell img[data-k="2024-5"][data-n="2"]')
    t2.hover(); pg.wait_for_timeout(400); t2.click(); pg.wait_for_timeout(1300)
    pg.evaluate("() => document.getElementById('postStack').children[9].scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(500)
    on = pg.evaluate("""() => {
      const st = document.getElementById('postStack'), mid = innerHeight / 2;
      let best = 0, bd = 1e9;
      [...st.children].forEach((c, i) => { const r = c.getBoundingClientRect(); const d = Math.abs(r.top + r.height / 2 - mid); if (d < bd) { bd = d; best = i; } });
      return best + 1; }""")
    check("scrolled down to image 10 inside the post", on == 10, on)
    pg.click("#postBack")
    pg.wait_for_timeout(300)
    mid = pg.evaluate("""() => ({fly: !!document.querySelector('.post-fly'),
      leaving: document.getElementById('postView').classList.contains('leaving'),
      scrim: document.getElementById('postScrim').classList.contains('fx')})""")
    check("ARCHIVE starts the zoom back", mid["fly"] and mid["leaving"], mid)
    check("the page comes back into focus on the way out", not mid["scrim"])
    pg.wait_for_timeout(1300)
    land = pg.evaluate("""() => {
      const d = JSON.parse(document.getElementById('v3data').textContent);
      const i = document.getElementById('previewImg');
      return {open: document.getElementById('postView').classList.contains('open'),
              visible: document.getElementById('hoverPreview').classList.contains('visible'),
              match: i.src === new URL(d['2024-5'].i[9].u, location.href).href, src: i.getAttribute('src'),
              fly: !!document.querySelector('.post-fly'), hash: location.hash}; }""")
    check("the post is closed afterwards", not land["open"], land)
    check("it lands back on image 10, enlarged in the preview zone", land["visible"] and land["match"], land)
    check("the flying copy is cleaned up", not land["fly"])
    seat = pg.evaluate("""() => {
      const th = document.querySelector('.grid-cell img[data-k="2024-5"][data-n="10"]');
      const b = th.getBoundingClientRect(), ov = document.getElementById('hoverPreview').getBoundingClientRect().bottom;
      return {ok: b.top >= ov - 1 && b.bottom <= innerHeight + 1, top: Math.round(b.top), ov: Math.round(ov)}; }""")
    check("that image's own thumbnail is on screen below the blank zone", seat["ok"], seat)
    check("the address is back at the archive", land["hash"] in ("", "#"), land["hash"])
    pg.screenshot(path=os.path.join(shots, "v3-desktop-landed-back.png"))

    # the same on a post opened from a shared link (no grid click behind it)
    pg.goto(B + "/v3/#2024-w3-i1", wait_until="load")
    pg.wait_for_timeout(1500)
    pg.evaluate("() => document.getElementById('postStack').children[7].scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(500)
    pg.click("#postBack")
    pg.wait_for_timeout(250)
    check("a shared link also zooms back out", pg.evaluate("() => !!document.querySelector('.post-fly')"))
    pg.wait_for_timeout(1300)
    dl2 = pg.evaluate("""() => {
      const d = JSON.parse(document.getElementById('v3data').textContent);
      const i = document.getElementById('previewImg');
      return {open: document.getElementById('postView').classList.contains('open'),
              visible: document.getElementById('hoverPreview').classList.contains('visible'),
              match: i.src === new URL(d['2024-3'].i[7].u, location.href).href}; }""")
    check("and lands on image 8 in the preview zone", not dl2["open"] and dl2["visible"] and dl2["match"], dl2)

    # the browser Back button does the same, and hovering another thumbnail takes over again
    t4 = pg.locator('.grid-cell img[data-k="2023-40"][data-n="4"]')
    t4.scroll_into_view_if_needed(); t4.hover(); pg.wait_for_timeout(400); t4.click(); pg.wait_for_timeout(1300)
    pg.evaluate("() => document.getElementById('postStack').children[6].scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(500)
    pg.go_back()
    pg.wait_for_timeout(1400)
    b2 = pg.evaluate("""() => {
      const d = JSON.parse(document.getElementById('v3data').textContent);
      const i = document.getElementById('previewImg');
      return {open: document.getElementById('postView').classList.contains('open'),
              visible: document.getElementById('hoverPreview').classList.contains('visible'),
              match: i.src === new URL(d['2023-40'].i[6].u, location.href).href}; }""")
    check("browser Back also zooms out and lands on image 7", not b2["open"] and b2["visible"] and b2["match"], b2)
    pg.mouse.move(720, 180); pg.wait_for_timeout(350)
    pg.mouse.move(690, 300); pg.wait_for_timeout(350)
    held = pg.evaluate("""() => {
      const d = JSON.parse(document.getElementById('v3data').textContent);
      const i = document.getElementById('previewImg');
      return {visible: document.getElementById('hoverPreview').classList.contains('visible'),
              match: i.src === new URL(d['2023-40'].i[6].u, location.href).href}; }""")
    check("moving the mouse without hovering a thumbnail leaves it up", held["visible"] and held["match"], held)

    other = pg.locator('.grid-cell img[data-k="2023-40"][data-n="1"]')
    other.hover(); pg.wait_for_timeout(500)
    sw = pg.evaluate("""() => {
      const d = JSON.parse(document.getElementById('v3data').textContent);
      return document.getElementById('previewImg').src === new URL(d['2023-40'].i[0].u, location.href).href; }""")
    check("hovering another thumbnail takes the preview back over", sw)
    pg.mouse.move(690, 300); pg.wait_for_timeout(400)
    check("after that, leaving a thumbnail hides the preview as usual",
          not pg.evaluate("() => document.getElementById('hoverPreview').classList.contains('visible')"))

    pg.close()

    # ---------------- phone ----------------
    # Its own layout: one tap opens the week, and the archive is the 3x4 square block used elsewhere.
    ph = br.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    ph.goto(B + "/v3/", wait_until="load")
    ph.wait_for_timeout(1200)
    m = ph.evaluate("""() => {
      const row = document.querySelector('.week-row'), ul = row.querySelector('.week-images');
      const cells = [...ul.querySelectorAll('.grid-cell')].map(c => c.getBoundingClientRect());
      const tops = [...new Set(cells.map(c => Math.round(c.top)))];
      const sq = cells.every(c => Math.abs(c.width - c.height) < 1.5);
      return {topOverlay: getComputedStyle(document.querySelector('.top-overlay')).display,
              preview: getComputedStyle(document.getElementById('hoverPreview')).display,
              archiveTop: document.getElementById('archive').getBoundingClientRect().top,
              cols: getComputedStyle(ul).gridTemplateColumns.split(' ').length,
              rows: tops.length, count: cells.length, square: sq,
              label: row.querySelector('.week-num').innerText.replace(/\\s+/g, ' ').trim(),
              yearHeader: getComputedStyle(document.querySelector('.year-header')).display,
              overflow: document.documentElement.scrollWidth > innerWidth + 1}; }""")
    check("no blank zone on a phone", m["topOverlay"] == "none", m["topOverlay"])
    check("no preview zone on a phone either", m["preview"] == "none", m["preview"])
    check("grid starts near the top", m["archiveTop"] < 300, m["archiveTop"])
    check("3 across", m["cols"] == 3, m["cols"])
    check("4 rows of 3 per week", m["rows"] == 4 and m["count"] == 12, (m["rows"], m["count"]))
    check("square cells, like the rest of the site on a phone", m["square"], m)
    check("each week's label carries its week and year", m["label"] == "9 2024", m["label"])
    check("so the sticky year label is not needed", m["yearHeader"] == "none", m["yearHeader"])
    check("no sideways scrolling at 390", not m["overflow"])
    check("the page places itself rather than letting the browser restore scroll",
          ph.evaluate("() => history.scrollRestoration") == "manual")
    ph.screenshot(path=os.path.join(shots, "v3-phone-landing.png"))

    # the years and the theme stay reachable down a very long page
    ph.mouse.wheel(0, 4000); ph.wait_for_timeout(600)
    bar = ph.evaluate("""() => {
      const b = document.querySelector('.header-right').getBoundingClientRect();
      return {top: Math.round(b.top), scrolled: Math.round(scrollY),
              opaque: getComputedStyle(document.querySelector('.header-right')).backgroundColor}; }""")
    check("the year filter stays at the top while you scroll", bar["scrolled"] > 1000 and bar["top"] <= 1, bar)
    check("and is opaque, so photos do not show through", "rgba(0, 0, 0, 0)" != bar["opaque"], bar)
    ph.evaluate("() => scrollTo(0, 0)"); ph.wait_for_timeout(400)

    # one tap opens the week at that image: no preview step
    t5 = ph.locator('.grid-cell img[data-k="2024-5"][data-n="5"]')
    t5.scroll_into_view_if_needed(); ph.wait_for_timeout(300)
    t5.tap()
    ph.wait_for_timeout(250)
    check("the zoom starts straight away", ph.evaluate("() => !!document.querySelector('.post-fly')"))
    ph.wait_for_timeout(1300)
    mp = ph.evaluate("""() => {
      const st = document.getElementById('postStack');
      const r = st.children[4].getBoundingClientRect();
      const w = [...st.querySelectorAll('img')].map(i => Math.round(i.getBoundingClientRect().width));
      return {open: document.getElementById('postView').classList.contains('open'),
              head: document.getElementById('postHead').innerText.replace(/\\s+/g, ' ').trim(),
              off: (r.top + r.height / 2) - innerHeight / 2, hash: location.hash,
              scrim: document.getElementById('postScrim').classList.contains('fx'),
              preview: document.getElementById('hoverPreview').classList.contains('visible'),
              widths: [...new Set(w)], col: Math.round(document.getElementById('postStack').clientWidth)}; }""")
    check("one tap opens that week", mp["open"] and mp["head"] == "Week 5 2024", mp)
    check("opened at the image that was tapped", abs(mp["off"]) < 60, mp["off"])
    check("address hash set", mp["hash"] == "#2024-w5-i5", mp["hash"])
    check("same blur/fade on a phone", mp["scrim"])
    check("no preview appears on the way", not mp["preview"], mp)
    check("post photos fill the column, all one width", len(mp["widths"]) == 1 and mp["widths"][0] == mp["col"], mp)
    ph.screenshot(path=os.path.join(shots, "v3-phone-post.png"))

    # leaving flies back down into the thumbnail it came from
    ph.evaluate("() => document.getElementById('postStack').children[9].scrollIntoView({block: 'center'})")
    ph.wait_for_timeout(500)
    ph.go_back()
    ph.wait_for_timeout(280)
    aim = ph.evaluate("""() => {
      const f = document.querySelector('.post-fly');
      const th = document.querySelector('.grid-cell img[data-k="2024-5"][data-n="10"]');
      const tr = th.getBoundingClientRect();
      const bar = document.querySelector('.header-right').getBoundingClientRect().bottom;
      const im = JSON.parse(document.getElementById('v3data').textContent)['2024-5'].i[9];
      const s = Math.min(tr.width / im.w, tr.height / im.h);   // the photo shown whole inside its box
      // the returning copy is pinned to the document, so take its screen position off its page position
      const pinned = f && f.classList.contains('on-page');
      return {fly: !!f,
              targetTop: f ? parseFloat(f.style.top) - (pinned ? pageYOffset : 0) : null,
              targetH: f ? parseFloat(f.style.height) : null,
              coverTop: tr.top + (tr.height - im.h * s) / 2, coverH: im.h * s,
              thumbCentre: tr.top + tr.height / 2, screenCentre: bar + (innerHeight - bar) / 2,
              bottomEdge: innerHeight}; }""")
    check("going back starts the zoom home", aim["fly"], aim)
    check("it aims at the photo where it floats in its cell, not at the cell",
          abs(aim["targetTop"] - aim["coverTop"]) < 2 and abs(aim["targetH"] - aim["coverH"]) < 2, aim)
    check("and lands well clear of the bottom edge, not flush against it",
          aim["targetTop"] + aim["targetH"] < aim["bottomEdge"] - 60, aim)
    ph.wait_for_timeout(1400)
    ml = ph.evaluate("""() => {
      const th = document.querySelector('.grid-cell img[data-k="2024-5"][data-n="10"]');
      const b = th.getBoundingClientRect();
      const bar = document.querySelector('.header-right').getBoundingClientRect().bottom;
      return {open: document.getElementById('postView').classList.contains('open'),
              preview: document.getElementById('hoverPreview').classList.contains('visible'),
              thumbShown: getComputedStyle(th).visibility === 'visible',
              onScreen: b.top >= bar - 1 && b.bottom <= innerHeight + 1,
              leftovers: document.querySelectorAll('.post-fly').length, hash: location.hash}; }""")
    check("phone: Back closes the post", not ml["open"], ml)
    check("phone: it lands on that image's own thumbnail", ml["onScreen"] and ml["thumbShown"], ml)
    check("phone: no preview is left hanging over the grid", not ml["preview"], ml)
    check("phone: the flying copy is cleaned up", ml["leftovers"] == 0, ml)
    ph.screenshot(path=os.path.join(shots, "v3-phone-landed-back.png"))

    # when the photo's thumbnail is nowhere near the screen, the grid centres it rather than nudging it to an edge
    ph.goto(B + "/v3/#2023-w20-i7", wait_until="load")
    ph.wait_for_timeout(1500)
    ph.locator("#postBack").tap()
    ph.wait_for_timeout(1700)
    far = ph.evaluate("""() => {
      const th = document.querySelector('.grid-cell img[data-k="2023-20"][data-n="7"]');
      const tr = th.getBoundingClientRect();
      const bar = document.querySelector('.header-right').getBoundingClientRect().bottom;
      return {centre: tr.top + tr.height / 2, screenCentre: bar + (innerHeight - bar) / 2,
              onScreen: tr.top >= bar && tr.bottom <= innerHeight,
              shown: getComputedStyle(th).visibility === 'visible'}; }""")
    check("a thumbnail that was off screen is centred on return",
          abs(far["centre"] - far["screenCentre"]) < 20 and far["onScreen"] and far["shown"], far)

    # the flight home stays on its thumbnail even if something scrolls the page mid-flight
    # (a phone browser can restore the scroll of a history entry after the page has already placed itself)
    ph.goto(B + "/v3/", wait_until="load"); ph.wait_for_timeout(1200)
    jolt = ph.locator('.grid-cell img[data-k="2024-7"][data-n="2"]')
    jolt.scroll_into_view_if_needed(); ph.wait_for_timeout(400)
    jolt.tap(); ph.wait_for_timeout(1400)
    ph.evaluate("() => document.getElementById('postStack').children[8].scrollIntoView({block: 'center'})")
    ph.wait_for_timeout(400)
    ph.go_back()
    ph.wait_for_timeout(160)
    ph.evaluate("() => scrollBy(0, -140)")       # the browser changing its mind about where the page sits
    ph.wait_for_timeout(330)
    stuck = ph.evaluate("""() => {
      const f = document.querySelector('.post-fly');
      const th = document.querySelector('.grid-cell img[data-k="2024-7"][data-n="9"]');
      const tr = th.getBoundingClientRect();
      const im = JSON.parse(document.getElementById('v3data').textContent)['2024-7'].i[8];
      const s = Math.min(tr.width / im.w, tr.height / im.h);   // the photo shown whole inside its box
      const fr = f ? f.getBoundingClientRect() : null;
      return {fly: !!f, flyTop: fr ? fr.top : null, flyH: fr ? fr.height : null,
              coverTop: tr.top + (tr.height - im.h * s) / 2, coverH: im.h * s}; }""")
    check("the photo is still in the air after the jolt", stuck["fly"], stuck)
    check("and is still tracking its thumbnail, not the screen",
          abs((stuck["flyTop"] + stuck["flyH"]) - (stuck["coverTop"] + stuck["coverH"])) < 90, stuck)
    ph.wait_for_timeout(900)
    rest = ph.evaluate("""() => {
      const th = document.querySelector('.grid-cell img[data-k="2024-7"][data-n="9"]');
      const tr = th.getBoundingClientRect();
      return {shown: getComputedStyle(th).visibility === 'visible',
              onScreen: tr.bottom > 0 && tr.top < innerHeight,
              flies: document.querySelectorAll('.post-fly').length}; }""")
    check("it lands on a thumbnail that is on screen and visible again",
          rest["shown"] and rest["onScreen"] and rest["flies"] == 0, rest)

    # coming straight back out of a photo that was already on screen leaves the grid where it was
    target = ph.locator('.grid-cell img[data-k="2024-5"][data-n="10"]')
    target.scroll_into_view_if_needed()
    ph.evaluate("""() => {
      const r = document.querySelector('.grid-cell img[data-k="2024-5"][data-n="10"]').getBoundingClientRect();
      const bar = document.querySelector('.header-right').offsetHeight;
      scrollBy(0, (r.top + r.height / 2) - (bar + (innerHeight - bar) / 2)); }""")
    ph.wait_for_timeout(500)
    settle = ph.evaluate("() => Math.round(scrollY)")
    target.tap()
    ph.wait_for_timeout(1400)
    ph.go_back()
    ph.wait_for_timeout(1600)
    moved = ph.evaluate("() => Math.round(scrollY)")
    check("returning to a photo already in view does not move the grid", abs(moved - settle) < 2, (settle, moved))

    # the ARCHIVE button does the same
    ph.locator('.grid-cell img[data-k="2023-30"][data-n="2"]').tap()
    ph.wait_for_timeout(1300)
    ph.locator("#postBack").tap()
    ph.wait_for_timeout(1500)
    check("phone: the ARCHIVE button also returns to the grid",
          not ph.evaluate("() => document.getElementById('postView').classList.contains('open')"))
    ph.close()

    # ---------------- light / dark follows the device ----------------
    for scheme, want in (("light", "light"), ("dark", "dark")):
        tp = br.new_page(viewport={"width": 1280, "height": 800}, color_scheme=scheme)
        tp.goto(B + "/v3/", wait_until="load")
        tp.wait_for_timeout(500)
        t = tp.evaluate("""() => ({theme: document.documentElement.dataset.theme,
          label: document.getElementById('themeToggle').textContent.trim(),
          bar: document.querySelector('meta[name=theme-color]').content,
          bg: getComputedStyle(document.body).backgroundColor,
          saved: localStorage.getItem('theme')})""")
        check("a device set to " + scheme + " opens in " + want, t["theme"] == want, t)
        check("nothing is saved until the person chooses (" + scheme + ")", t["saved"] is None, t)
        check("the browser bar colour matches (" + scheme + ")",
              t["bar"] == ("#ffffff" if want == "light" else "#000000"), t)
        check("the toggle offers the other one (" + scheme + ")",
              t["label"] == ("DARK" if want == "light" else "LIGHT"), t)

        # choosing the other one sticks across a reload
        tp.click("#themeToggle")
        tp.wait_for_timeout(200)
        other = "dark" if want == "light" else "light"
        o = tp.evaluate("() => ({theme: document.documentElement.dataset.theme, saved: localStorage.getItem('theme')})")
        check("tapping it switches and is remembered (" + scheme + ")", o["theme"] == other and o["saved"] == other, o)
        tp.reload(wait_until="load")
        tp.wait_for_timeout(400)
        check("the choice survives a reload (" + scheme + ")",
              tp.evaluate("() => document.documentElement.dataset.theme") == other)

        # setting it back to what the device is doing goes back to following the device
        tp.click("#themeToggle")
        tp.wait_for_timeout(200)
        b2 = tp.evaluate("() => ({theme: document.documentElement.dataset.theme, saved: localStorage.getItem('theme')})")
        check("setting it back to the device's own mode follows the device again (" + scheme + ")",
              b2["theme"] == want and b2["saved"] is None, b2)
        tp.close()

    # a device that changes on its own is followed, until the person has chosen
    tp = br.new_page(viewport={"width": 1280, "height": 800}, color_scheme="dark")
    tp.goto(B + "/v3/", wait_until="load"); tp.wait_for_timeout(400)
    tp.emulate_media(color_scheme="light"); tp.wait_for_timeout(400)
    check("the page follows the device when it changes",
          tp.evaluate("() => document.documentElement.dataset.theme") == "light")
    tp.click("#themeToggle"); tp.wait_for_timeout(200)          # explicitly choose dark
    tp.emulate_media(color_scheme="dark"); tp.wait_for_timeout(400)
    tp.emulate_media(color_scheme="light"); tp.wait_for_timeout(400)
    check("but a chosen theme is not overridden by the device",
          tp.evaluate("() => document.documentElement.dataset.theme") == "dark")
    tp.close()
    # ---------------- browser zoom on a laptop ----------------
    # Zooming narrows the window in CSS pixels (200% on a 1440 window is 720 wide, 300% is 480) and shrinks its
    # height too. Safari has no scroll anchoring, so emulate that: the page has to keep your place itself.
    def zoom_to(pg, z):
        pg.set_viewport_size({"width": round(1440 / z), "height": round(800 / z)}); pg.wait_for_timeout(700)

    zp = br.new_page(viewport={"width": 1440, "height": 800})
    zp.goto(B + "/v3/", wait_until="load"); zp.wait_for_timeout(1200)
    zp.add_style_tag(content="*{overflow-anchor:none!important}")
    POSTAT = """() => { const v = document.getElementById('postView'), st = document.getElementById('postStack');
      const cy = v.getBoundingClientRect().top + v.clientHeight / 2;
      for (let i = 0; i < st.children.length; i++) { const r = st.children[i].getBoundingClientRect();
        if (r.bottom >= cy) return {img: i + 1, at: Math.round((cy - r.top) / r.height * 100) / 100}; } }"""
    zp.evaluate("document.querySelector('.grid-cell img[data-k=\"2024-5\"][data-n=\"1\"]').click()"); zp.wait_for_timeout(1500)
    zp.evaluate("""() => { const v = document.getElementById('postView'), r = document.getElementById('postStack').children[7].getBoundingClientRect();
      v.scrollTop += (r.top + r.height / 2) - (v.getBoundingClientRect().top + v.clientHeight / 2); }""")
    zp.wait_for_timeout(400)
    held = []
    for z in (1.25, 1.5, 2, 2.5, 3, 4, 1):
        zoom_to(zp, z); a = zp.evaluate(POSTAT); held.append((z, a))
    check("zooming in and out keeps the same photo in the middle of the post",
          all(a["img"] == 8 and abs(a["at"] - 0.5) < 0.05 for z, a in held), held)

    # back at 300% (a mouse, but the phone layout): the photo must fly to its thumbnail, not to a zone that is hidden
    zoom_to(zp, 3)
    zp.evaluate("""() => { const v = document.getElementById('postView'), r = document.getElementById('postStack').children[9].getBoundingClientRect();
      v.scrollTop += (r.top + r.height / 2) - (v.getBoundingClientRect().top + v.clientHeight / 2); }""")
    zp.wait_for_timeout(300)
    zp.mouse.move(200, 150)
    zp.keyboard.press("Escape"); zp.wait_for_timeout(250)
    aim = zp.evaluate("""() => { const f = document.querySelector('.post-fly');
      const th = document.querySelector('.grid-cell img[data-k="2024-5"][data-n="10"]').getBoundingClientRect();
      return {fly: !!f, inZone: f ? getComputedStyle(document.getElementById('hoverPreview')).display : null,
              flyTop: f ? parseFloat(f.style.top) - (f.classList.contains('on-page') ? pageYOffset : 0) : null,
              thumbTop: th.top, thumbBottom: th.bottom}; }""")
    check("zoomed past the phone breakpoint, going back starts a flight", aim["fly"], aim)
    check("and aims inside its own thumbnail, not at the hidden preview zone",
          aim["fly"] and aim["thumbTop"] - 2 <= aim["flyTop"] <= aim["thumbBottom"] + 2, aim)
    zp.wait_for_timeout(1200)
    check("the preview zone stays hidden after landing", zp.evaluate(
        "() => getComputedStyle(document.getElementById('hoverPreview')).display") == "none")
    zp.close()

    # the archive keeps its place too
    gp = br.new_page(viewport={"width": 1440, "height": 800})
    gp.goto(B + "/v3/", wait_until="load"); gp.wait_for_timeout(1200)
    gp.add_style_tag(content="*{overflow-anchor:none!important}")
    gp.evaluate("document.querySelectorAll('.week-row')[9].scrollIntoView({block: 'center'})"); gp.wait_for_timeout(500)
    ROW = """() => { const wide = innerWidth >= 720;
      const y = (wide ? document.getElementById('hoverPreview').getBoundingClientRect().bottom
                      : document.querySelector('.header-right').offsetHeight) + 12;
      const rows = [...document.querySelectorAll('.week-row')];
      for (let i = 0; i < rows.length; i++) { const r = rows[i].getBoundingClientRect();
        if (r.height && r.bottom >= y) return {row: i, f: Math.round((y - r.top) / r.height * 100) / 100,
                                                h: document.documentElement.scrollWidth > innerWidth + 1}; } }"""
    gp.mouse.move(700, 500)
    base = gp.evaluate(ROW); rows_seen = []
    for z in (1.25, 1.5, 2, 2.5, 3, 1):
        zoom_to(gp, z); rows_seen.append((z, gp.evaluate(ROW)))
    check("zooming keeps the same archive row in view",
          all(r["row"] == base["row"] and abs(r["f"] - base["f"]) < 0.08 for z, r in rows_seen), (base, rows_seen))
    check("and never sideways-scrolls", not any(r["h"] for z, r in rows_seen), rows_seen)
    gp.close()
    br.close()

srv.terminate()
print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
