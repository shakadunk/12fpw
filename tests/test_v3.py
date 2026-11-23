"""V4 preview page (/v3/). Desktop: a sunken landing sized to ~1.5 rows that scrolls away, a hover preview
centred on the screen over a frosted grid, click opens the week centred on the clicked image, and the week
number opens it at the top where the writing is. Phones: no sunken landing, 4 rows of 3 per week with
uncropped ratios, tap to open.   Run after building:  python3 tests/test_v3.py"""
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

# Once the preview is up it covers the screen and takes the mouse, so thumbnails are no longer clickable:
# the way into a week from there is the preview photo itself.
def click_preview_photo(page):
    r = page.evaluate("""() => { const b = document.getElementById('previewImg').getBoundingClientRect();
        return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }""")
    page.mouse.click(r["x"], r["y"])

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
      const arc = document.getElementById('archive').getBoundingClientRect();
      const r0 = rows[0].getBoundingClientRect();
      const cell0 = rows[0].querySelector('.grid-cell').getBoundingClientRect();
      return {rows: rows.length, cells: cells.length,
              sections: [...document.querySelectorAll('.year-section')].map(s => s.dataset.year),
              perRow: rows.map(r => r.querySelectorAll('.grid-cell').length),
              archiveTop: arc.top, vh: innerHeight, row0Top: r0.top, row0H: r0.height,
              rowAlign: getComputedStyle(rows[0]).alignItems,
              cellMid: cell0.top + cell0.height / 2, rowMid: r0.top + r0.height / 2,
              headStatic: getComputedStyle(document.querySelector('.site-head')).position,
              overflow: document.documentElement.scrollWidth > innerWidth + 1};
    }""")
    check("61 week rows", g["rows"] == N, g["rows"])
    check("732 grid cells", g["cells"] == N * 12, g["cells"])
    check("one section per year, newest first", g["sections"] == [str(y) for y in years], g["sections"])
    check("every week has 12 images", set(g["perRow"]) == {12}, set(g["perRow"]))
    check("the header is in the flow, so it scrolls away", g["headStatic"] == "static", g["headStatic"])
    nothing_pinned = pg.evaluate("""() => {
      // Nothing fixed covers the grid any more: a point in the sunken landing hits the page, not a panel.
      const el = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
      return !el || !el.closest('.top-overlay'); }""")
    check("no fixed panel over the grid", nothing_pinned)
    visible = g["vh"] - g["archiveTop"]
    check("about 1.5 rows show on arrival", 1.2 * g["row0H"] <= visible <= 1.9 * g["row0H"], (visible, g["row0H"]))
    check("the landing grid is at most 45% of the screen", visible <= g["vh"] * 0.45 + 2, (visible, g["vh"]))
    check("thumbnails are centred in their row", g["rowAlign"] == "center", g["rowAlign"])
    check("and sit on the row's middle line", abs(g["cellMid"] - g["rowMid"]) <= 1.5, (g["cellMid"], g["rowMid"]))
    check("no sideways scrolling at 1440", not g["overflow"])
    check("the window is the scroller, not <body>", pg.evaluate("() => document.documentElement.scrollHeight - innerHeight > 100"))
    pg.screenshot(path=os.path.join(shots, "v3-desktop-landing.png"))

    # Resting on a thumbnail shows the full-size copy, not the 700px thumbnail. Opening takes the dwell
    # (500ms) plus the flight out of the thumbnail (550ms), so waits here allow for both.
    HOVER_MS = 1300
    first = pg.locator(".grid-cell img").first
    first.hover()
    pg.wait_for_timeout(HOVER_MS)
    hv = pg.evaluate("""() => {
      const p = document.getElementById('hoverPreview'), i = document.getElementById('previewImg');
      const s = document.getElementById('previewScrim');
      const b = i.getBoundingClientRect();
      return {visible: p.classList.contains('visible'), src: i.getAttribute('src'), nw: i.naturalWidth,
              box: b.height, cx: b.left + b.width / 2, cy: b.top + b.height / 2,
              vw: innerWidth, vh: innerHeight,
              scrim: s.classList.contains('visible'),
              blur: getComputedStyle(s).backdropFilter || getComputedStyle(s).webkitBackdropFilter,
              passes: getComputedStyle(s).pointerEvents};
    }""")
    check("resting on a thumbnail shows the preview", hv["visible"])
    check("preview uses a full-size copy, not the -t thumbnail", hv["src"] and not hv["src"].endswith("-t.jpg"), hv["src"])
    check("the preview is centred on the screen", abs(hv["cx"] - hv["vw"] / 2) <= 1 and abs(hv["cy"] - hv["vh"] / 2) <= 1, (hv["cx"], hv["cy"]))
    check("the grid behind it is frosted", hv["scrim"] and "blur" in (hv["blur"] or ""), (hv["scrim"], hv["blur"]))
    check("the frosted layer never takes the mouse", hv["passes"] == "none", hv["passes"])
    # The whole point of centring: it is in the same place on the landing as deep in the archive.
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    pg.evaluate("window.scrollTo(0, 3000)")
    pg.wait_for_timeout(400)
    pg.locator('.grid-cell img').nth(60).hover()
    pg.wait_for_timeout(HOVER_MS)
    deep = pg.evaluate("""() => { const b = document.getElementById('previewImg').getBoundingClientRect();
      return {cx: b.left + b.width / 2, cy: b.top + b.height / 2}; }""")
    check("and stays in that same place once you have scrolled down", abs(deep["cx"] - hv["cx"]) <= 1 and abs(deep["cy"] - hv["cy"]) <= 1, (deep, hv["cx"], hv["cy"]))
    pg.screenshot(path=os.path.join(shots, "v3-desktop-hover.png"))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    pg.evaluate("window.scrollTo(0, 0)")
    pg.wait_for_timeout(400)

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
    pg.wait_for_timeout(HOVER_MS)
    before = pg.evaluate("""() => {
      const i = document.getElementById('previewImg'), b = i.getBoundingClientRect();
      const s = Math.min(b.width / i.naturalWidth, b.height / i.naturalHeight);
      return {w: i.naturalWidth * s, h: i.naturalHeight * s, boxW: b.width, boxH: b.height, vh: innerHeight};
    }""")
    click_preview_photo(pg)   # the preview is up by now, so that is the way in
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
    check("and well short of the old full column (816px wide)", after["w"] < 760, after)
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
    # Leaving a post: the photo you are on flies back down into its own thumbnail, on a mouse as on a
    # phone. It used to land in the preview on a desktop, but the preview now covers the screen and takes
    # the mouse, so coming out of a week would drop you behind a photo you then had to dismiss.
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
      const th = document.querySelector('.grid-cell img[data-k="2024-5"][data-n="10"]');
      return {open: document.getElementById('postView').classList.contains('open'),
              visible: document.getElementById('hoverPreview').classList.contains('visible'),
              thumbShown: getComputedStyle(th).visibility === 'visible',
              fly: !!document.querySelector('.post-fly'), hash: location.hash}; }""")
    check("the post is closed afterwards", not land["open"], land)
    check("it lands back on image 10's own thumbnail", land["thumbShown"], land)
    check("and leaves no photo covering the grid", not land["visible"], land)
    check("the flying copy is cleaned up", not land["fly"])
    seat = pg.evaluate("""() => {
      const th = document.querySelector('.grid-cell img[data-k="2024-5"][data-n="10"]');
      const b = th.getBoundingClientRect();
      return {ok: b.top >= -1 && b.bottom <= innerHeight + 1, top: Math.round(b.top), bottom: Math.round(b.bottom), vh: innerHeight}; }""")
    check("that image's own thumbnail has been brought on screen", seat["ok"], seat)
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
      const th = document.querySelector('.grid-cell img[data-k="2024-3"][data-n="8"]');
      const b = th.getBoundingClientRect();
      return {open: document.getElementById('postView').classList.contains('open'),
              visible: document.getElementById('hoverPreview').classList.contains('visible'),
              thumbShown: getComputedStyle(th).visibility === 'visible',
              onScreen: b.top >= -1 && b.bottom <= innerHeight + 1}; }""")
    check("and lands on image 8's thumbnail", not dl2["open"] and dl2["thumbShown"] and dl2["onScreen"], dl2)
    check("with nothing left covering the grid", not dl2["visible"], dl2)

    # the browser Back button does the same
    t4 = pg.locator('.grid-cell img[data-k="2023-40"][data-n="4"]')
    t4.scroll_into_view_if_needed(); t4.hover(); pg.wait_for_timeout(400); t4.click(); pg.wait_for_timeout(1300)
    pg.evaluate("() => document.getElementById('postStack').children[6].scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(500)
    pg.go_back()
    pg.wait_for_timeout(1400)
    b2 = pg.evaluate("""() => {
      const th = document.querySelector('.grid-cell img[data-k="2023-40"][data-n="7"]');
      const b = th.getBoundingClientRect();
      return {open: document.getElementById('postView').classList.contains('open'),
              visible: document.getElementById('hoverPreview').classList.contains('visible'),
              thumbShown: getComputedStyle(th).visibility === 'visible',
              onScreen: b.top >= -1 && b.bottom <= innerHeight + 1}; }""")
    check("browser Back also zooms out onto image 7's thumbnail",
          not b2["open"] and b2["thumbShown"] and b2["onScreen"], b2)
    check("and you are left on the grid, not behind a photo", not b2["visible"], b2)

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
      return {preview: getComputedStyle(document.getElementById('hoverPreview')).display,
              scrim: getComputedStyle(document.getElementById('previewScrim')).display,
              archiveTop: document.getElementById('archive').getBoundingClientRect().top,
              cols: getComputedStyle(ul).gridTemplateColumns.split(' ').length,
              rows: tops.length, count: cells.length, square: sq,
              label: row.querySelector('.week-num').innerText.replace(/\\s+/g, ' ').trim(),
              yearHeader: getComputedStyle(document.querySelector('.year-header')).display,
              overflow: document.documentElement.scrollWidth > innerWidth + 1}; }""")
    check("no hover preview on a phone", m["preview"] == "none", m["preview"])
    check("and no frosted layer either", m["scrim"] == "none", m["scrim"])
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

    # the years and the theme stay reachable down a very long page: the header scrolls away and the
    # scroll-up bar brings them back. Park the pointer off the bar first, or resting on it holds it open.
    ph.mouse.move(195, 600)
    ph.mouse.wheel(0, 4000); ph.wait_for_timeout(2000)
    down = ph.evaluate("() => ({show: document.getElementById('slimbar').classList.contains('show'), scrolled: Math.round(scrollY)})")
    check("heading down, nothing sits over the photos", not down["show"] and down["scrolled"] > 1000, down)
    ph.mouse.wheel(0, -600); ph.wait_for_timeout(500)
    bar = ph.evaluate("""() => {
      const s = document.getElementById('slimbar'), b = s.getBoundingClientRect();
      return {show: s.classList.contains('show'), top: Math.round(b.top),
              opaque: getComputedStyle(s).backgroundColor,
              years: s.querySelectorAll('.year-filters button').length,
              hasTop: !!s.querySelector('#slimTop')}; }""")
    check("heading back up brings the controls back", bar["show"] and bar["top"] <= 1, bar)
    check("and the bar is opaque, so photos do not show through", "rgba(0, 0, 0, 0)" != bar["opaque"], bar)
    check("it carries every year plus ALL", bar["years"] == len(years) + 1, bar["years"])
    check("and a way back to the top", bar["hasTop"])
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
      // Nothing is pinned over the grid now, so "centred" means centred on the screen itself.
      return {centre: tr.top + tr.height / 2, screenCentre: innerHeight / 2,
              onScreen: tr.top >= 0 && tr.bottom <= innerHeight,
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
          label: document.querySelector('.site-head .theme-toggle').textContent.trim(),
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
        tp.click(".site-head .theme-toggle")
        tp.wait_for_timeout(200)
        other = "dark" if want == "light" else "light"
        o = tp.evaluate("() => ({theme: document.documentElement.dataset.theme, saved: localStorage.getItem('theme')})")
        check("tapping it switches and is remembered (" + scheme + ")", o["theme"] == other and o["saved"] == other, o)
        tp.reload(wait_until="load")
        tp.wait_for_timeout(400)
        check("the choice survives a reload (" + scheme + ")",
              tp.evaluate("() => document.documentElement.dataset.theme") == other)

        # setting it back to what the device is doing goes back to following the device
        tp.click(".site-head .theme-toggle")
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
    tp.click(".site-head .theme-toggle"); tp.wait_for_timeout(200)          # explicitly choose dark
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
    check("and aims inside its own thumbnail",
          aim["fly"] and aim["thumbTop"] - 2 <= aim["flyTop"] <= aim["thumbBottom"] + 2, aim)
    zp.wait_for_timeout(1200)
    check("the preview zone stays hidden after landing", zp.evaluate(
        "() => getComputedStyle(document.getElementById('hoverPreview')).display") == "none")
    zp.close()

    # ---------------- hovering has to be meant ----------------
    # The grid fills the screen, so the cursor is nearly always over a photo. Passing through, or merely
    # scrolling with the cursor parked, must not keep throwing big photos up.
    hp = br.new_page(viewport={"width": 1440, "height": 900})
    hp.goto(B + "/v3/", wait_until="load")
    hp.wait_for_timeout(1500)
    hp.evaluate("window.scrollTo(0, 2500)")
    hp.wait_for_timeout(900)
    CELLS = """() => [...document.querySelectorAll('.grid-cell img')]
        .map(e => { const b = e.getBoundingClientRect();
          return {x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2), w: b.width, h: b.height}; })
        .filter(c => c.y > 150 && c.y < innerHeight - 150 && c.w > 40 && c.h > 40)"""
    OPEN = "() => document.getElementById('hoverPreview').classList.contains('visible')"
    SRC = "() => (document.getElementById('previewImg').getAttribute('src') || '').split('/').pop()"
    cells = hp.evaluate(CELLS)

    for c in cells[:8]:                       # crossing the grid on the way somewhere else
        hp.mouse.move(c["x"], c["y"]); hp.wait_for_timeout(45)
    check("passing over thumbnails opens nothing", not hp.evaluate(OPEN))

    a, nxt = cells[5], cells[6]
    hp.mouse.move(a["x"], a["y"])
    hp.wait_for_timeout(300)
    check("and it is still shut part way through the dwell", not hp.evaluate(OPEN))
    hp.wait_for_timeout(320)
    check("the dwell ends in a flight, not a pop", hp.evaluate("() => !!document.querySelector('.post-fly')"))
    hp.wait_for_timeout(800)
    check("which lands as the open preview", hp.evaluate(OPEN))
    check("and tidies the flying copy away", not hp.evaluate("() => !!document.querySelector('.post-fly')"))

    # Open, it is a thing you are looking at, not a thing that follows the mouse. The thumbnails it would
    # otherwise pick up are the ones lying underneath it, so swapping on hover is browsing blind.
    held_src = hp.evaluate(SRC)
    for c in (nxt, cells[8], cells[2]):
        hp.mouse.move(c["x"], c["y"]); hp.wait_for_timeout(300)
    check("moving over other thumbnails does not change the photo", hp.evaluate(SRC) == held_src,
          (held_src, hp.evaluate(SRC)))
    check("and does not put it away", hp.evaluate(OPEN))

    for _ in range(5):                        # a zoom reflows and scrolls the page: it must survive that
        hp.mouse.wheel(0, 200); hp.wait_for_timeout(60)
    hp.wait_for_timeout(500)
    check("scrolling leaves it alone too", hp.evaluate(OPEN) and hp.evaluate(SRC) == held_src)

    hp.keyboard.press("Escape"); hp.wait_for_timeout(300)
    check("Escape puts it away", not hp.evaluate(OPEN))
    under = hp.evaluate("""() => { const e = document.elementFromPoint(%d, %d);
        return !!(e && e.closest && e.closest('.grid-cell img')); }""" % (cells[2]["x"], cells[2]["y"]))
    if under:
        hp.mouse.move(cells[2]["x"] + 1, cells[2]["y"] + 1); hp.wait_for_timeout(900)
        check("and that one stays shut while the cursor is still on it", not hp.evaluate(OPEN))

    cs2 = hp.evaluate(CELLS)
    hp.mouse.move(cs2[6]["x"], cs2[6]["y"]); hp.wait_for_timeout(1300)
    check("another thumbnail opens as usual", hp.evaluate(OPEN))

    # Clicking the photo goes into its week at that photo; clicking beside it goes back to the grid
    hp.mouse.click(8, 450); hp.wait_for_timeout(400)
    check("clicking beside the photo returns to the grid", not hp.evaluate(OPEN))
    check("without opening a week", not hp.evaluate("() => document.getElementById('postView').classList.contains('open')"))

    target = hp.query_selector('.grid-cell img[data-k="2024-5"][data-n="7"]')
    target.scroll_into_view_if_needed(); hp.wait_for_timeout(500)
    tb = target.bounding_box()
    hp.mouse.move(tb["x"] + tb["width"] / 2, tb["y"] + tb["height"] / 2)
    hp.wait_for_timeout(1300)
    check("resting on image 7 of a week opens it", hp.evaluate(OPEN))
    click_preview_photo(hp)
    hp.wait_for_timeout(150)
    check("clicking the photo starts the flight into the week",
          hp.evaluate("() => !!document.querySelector('.post-fly')"))
    hp.wait_for_timeout(1400)
    into = hp.evaluate("""() => { const st = document.getElementById('postStack');
      const b = st.children[6].getBoundingClientRect();
      return {open: document.getElementById('postView').classList.contains('open'),
              hash: location.hash, off: Math.round((b.top + b.height / 2) - innerHeight / 2),
              preview: document.getElementById('hoverPreview').classList.contains('visible')}; }""")
    check("the week opens at that photo", into["open"] and into["hash"] == "#2024-w5-i7", into)
    check("with image 7 centred on the screen", abs(into["off"]) < 60, into["off"])
    check("and the preview is out of the way", not into["preview"], into)
    hp.close()

    # the archive keeps its place too
    gp = br.new_page(viewport={"width": 1440, "height": 800})
    gp.goto(B + "/v3/", wait_until="load"); gp.wait_for_timeout(1200)
    gp.add_style_tag(content="*{overflow-anchor:none!important}")
    gp.evaluate("document.querySelectorAll('.week-row')[9].scrollIntoView({block: 'center'})"); gp.wait_for_timeout(500)
    # The same line v3.js anchors on (gridProbeY): nothing is pinned over the grid on any width now,
    # so it is just inside the top of the screen.
    ROW = """() => { const y = 12;
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
