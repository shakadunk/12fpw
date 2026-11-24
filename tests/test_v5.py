"""V5 preview page (/v5/). V2's archive and reading column with V3's motion, and one gesture at every
width: touch a photo and its week opens in place, the photo zooming out of the thumbnail; leave and it
flies home. No hover step and no preview layer on either a mouse or a finger.
Run after building:  python3 tests/test_v5.py"""
import subprocess, time, os, sys
from playwright.sync_api import sync_playwright

proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
shots = os.path.join(proj, "tests", "shots")
os.makedirs(shots, exist_ok=True)
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=proj, env={**os.environ, "PORT": "3279"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3279"
res = []
def check(name, cond, extra=""):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))

slugs = sorted((d for d in os.listdir(os.path.join(proj, "issues")) if d[:4].isdigit()), key=lambda s: (int(s[:4]), int(s.split("-w")[1])), reverse=True)
N = len(slugs)
years = sorted({int(s[:4]) for s in slugs}, reverse=True)

OPEN = "() => document.getElementById('postView').classList.contains('open')"
FLY = "() => !!document.querySelector('.post-fly')"

with sync_playwright() as pw:
    br = pw.chromium.launch()

    # ---------------- the grid, V2's measurements ----------------
    pg = br.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
    pg.goto(B + "/v5/", wait_until="load")
    pg.wait_for_timeout(1800)

    g = pg.evaluate("""() => {
      const weeks = [...document.querySelectorAll('.fg-week')];
      const row = document.querySelector('.fg-row');
      const cell = document.querySelector('.fg-cell');
      const img = cell.querySelector('img');
      const cb = cell.getBoundingClientRect(), ib = img.getBoundingClientRect();
      return {weeks: weeks.length, cells: document.querySelectorAll('.fg-cell img').length,
              perWeek: [...new Set(weeks.map(w => w.querySelectorAll('.fg-cell').length))],
              cols: getComputedStyle(row).gridTemplateColumns.split(' ').length,
              gap: getComputedStyle(row).gap,
              square: Math.abs(cb.width - cb.height) < 1.5,
              fit: getComputedStyle(img).objectFit,
              insideCell: ib.left >= cb.left - 0.5 && ib.right <= cb.right + 0.5,
              headStatic: getComputedStyle(document.querySelector('.site-head')).position,
              archTop: Math.round(document.getElementById('archive').getBoundingClientRect().top),
              overflow: document.documentElement.scrollWidth > innerWidth + 1,
              noPreview: !document.querySelector('.hover-preview, .preview-scrim, .top-overlay')}; }""")
    check("61 weeks", g["weeks"] == N, g["weeks"])
    check("732 photos", g["cells"] == N * 12, g["cells"])
    check("12 to a week", g["perWeek"] == [12], g["perWeek"])
    check("12 across on a desktop, one whole week to a row (V2)", g["cols"] == 12, g["cols"])
    check("V2's 3px gap between them", g["gap"].startswith("3px"), g["gap"])
    check("square cells", g["square"], g)
    check("photos shown whole, never cropped", g["fit"] == "contain", g["fit"])
    check("and sitting inside their square", g["insideCell"], g)
    check("the header is in the flow, so it scrolls away", g["headStatic"] == "static", g["headStatic"])
    check("the grid starts at the top: no blank landing to scroll past", g["archTop"] < 200, g["archTop"])
    check("no hover preview layer exists at all", g["noPreview"])

    # The title is centred on the screen, not in whatever gap the toggle and the years leave between them
    ttl = pg.evaluate("""() => { const b = document.querySelector('.site-head .site-name').getBoundingClientRect();
      return Math.abs((b.left + b.width / 2) - innerWidth / 2); }""")
    check("the title is centred on the screen", ttl <= 1.5, ttl)

    # The year stands in its own column and stays put while its weeks go by; the week number travels
    # with its own line of photos.
    # Resolve --mute and --text in whatever theme is running, rather than assuming one
    yr = pg.evaluate("""() => { const s = document.querySelector('.fg-sticky'), l = document.querySelector('.fg-label');
      const probe = document.createElement('span'); document.body.appendChild(probe);
      probe.style.color = 'var(--mute)'; const mute = getComputedStyle(probe).color;
      probe.style.color = 'var(--text)'; const text = getComputedStyle(probe).color;
      probe.remove();
      return {pos: getComputedStyle(s).position,
              year: getComputedStyle(s).color, week: getComputedStyle(l.querySelector('b')).color,
              mute: mute, text: text,
              inlineYearHidden: getComputedStyle(l.querySelector('.fg-yr')).display === 'none',
              yearLeftOfWeek: s.getBoundingClientRect().left < l.getBoundingClientRect().left,
              sections: document.querySelectorAll('.fg-year').length}; }""")
    check("the year sits to the left of the week number", yr["yearLeftOfWeek"], yr)
    check("one section per year", yr["sections"] == len(years), yr)
    check("the year is grey and sticky", yr["pos"] == "sticky" and yr["year"] == yr["mute"], yr)
    check("the week number keeps the text colour, not the grey", yr["week"] == yr["text"] and yr["week"] != yr["mute"], yr)
    check("and the year is not repeated on every line", yr["inlineYearHidden"], yr)

    # The space either side of the week number should read as the same gap. Measured on the painted
    # glyphs, not the boxes, and at both a one-digit and a two-digit week: left-aligning the number
    # would pile a one-digit week's slack onto the photo side, right-aligning it onto the year side.
    GAPS = """(wk) => {
      const lbl = document.querySelector('.fg-label[data-k="' + wk + '"]');
      const week = lbl.closest('.fg-week');
      const sticky = week.closest('.fg-year').querySelector('.fg-sticky');
      const ink = (el) => { const r = document.createRange(); r.selectNodeContents(el);
                            const b = r.getBoundingClientRect(); r.detach(); return b; };
      const y = ink(sticky), n = ink(lbl.querySelector('b'));
      const photos = week.querySelector('.fg-row').getBoundingClientRect();
      return {afterYear: n.left - y.right, beforePhotos: photos.left - n.right}; }"""
    for wk in ("2024-9", "2023-52"):
        gp = pg.evaluate(GAPS, wk)
        check("week %s sits evenly between the year and the photos" % wk.split("-")[1],
              abs(gp["afterYear"] - gp["beforePhotos"]) <= 1, gp)

    bounds = pg.evaluate("""() => [...document.querySelectorAll('.fg-year')].map(s => {
      const b = s.getBoundingClientRect(); return Math.round(b.top + scrollY); })""")
    pg.evaluate("window.scrollTo(0, %d)" % (bounds[1] - 400)); pg.wait_for_timeout(400)
    mid = pg.evaluate("() => Math.round(document.querySelector('.fg-sticky').getBoundingClientRect().top)")
    check("it stays put while that year's weeks scroll past", abs(mid - 12) <= 2, mid)
    pg.evaluate("window.scrollTo(0, %d)" % (bounds[1] + 40)); pg.wait_for_timeout(400)
    over = pg.evaluate("""() => [...document.querySelectorAll('.fg-sticky')].map(s =>
      Math.round(s.getBoundingClientRect().top))""")
    check("until the next year pushes it up into its place", over[0] < 0 and abs(over[1] - 12) <= 2, over)
    pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(400)
    check("no sideways scrolling at 1440", not g["overflow"])
    pg.screenshot(path=os.path.join(shots, "v5-desktop-landing.png"))

    # Hovering is feedback, never navigation: nothing opens, nothing covers the grid
    pg.locator(".fg-cell img").first.hover()
    pg.wait_for_timeout(900)
    check("resting on a photo opens nothing", not pg.evaluate(OPEN) and not pg.evaluate(FLY))
    check("and nothing is covering the grid", pg.evaluate(
        "() => !document.querySelector('[class*=preview]') && getComputedStyle(document.getElementById('archive')).visibility === 'visible'"))

    # ---------------- one gesture: a photo opens its week, at that photo ----------------
    th = pg.locator('.fg-cell img[data-k="2024-5"][data-n="7"]')
    th.scroll_into_view_if_needed(); pg.wait_for_timeout(400)
    start = pg.evaluate("""() => { const b = document.querySelector('.fg-cell img[data-k="2024-5"][data-n="7"]').getBoundingClientRect();
      return {w: b.width, cx: b.left + b.width / 2, cy: b.top + b.height / 2}; }""")
    th.click()
    pg.wait_for_timeout(140)
    air = pg.evaluate("""() => { const f = document.querySelector('.post-fly');
      if (!f) return null;
      const b = f.getBoundingClientRect();
      return {w: b.width, cx: b.left + b.width / 2, cy: b.top + b.height / 2}; }""")
    check("clicking a photo starts a flight", air is not None)
    if air:
        check("which begins on the thumbnail it came from",
              abs(air["cx"] - start["cx"]) < 90 and abs(air["cy"] - start["cy"]) < 90, (air, start))
    # The photo must be seen lifting off the archive. Taking the grid out of view while the copy is in
    # the air leaves it crossing a blank page, which is what it used to do.
    check("and the grid is still there underneath it, not blanked out",
          pg.evaluate("() => getComputedStyle(document.getElementById('archive')).visibility") == "visible")
    pg.wait_for_timeout(1400)
    po = pg.evaluate("""() => { const st = document.getElementById('postStack');
      const b = st.children[6].getBoundingClientRect();
      const ws = [...st.querySelectorAll('img')].map(i => Math.round(i.getBoundingClientRect().width));
      const a = st.querySelector('a');
      return {open: document.getElementById('postView').classList.contains('open'), hash: location.hash,
              head: document.getElementById('postHead').innerText.replace(/\\s+/g, ' ').trim(),
              off: Math.round((b.top + b.height / 2) - innerHeight / 2),
              scrim: document.getElementById('postScrim').classList.contains('fx'),
              text: document.getElementById('postText').innerText.length,
              widths: [...new Set(ws)], col: Math.round(st.clientWidth),
              ratioOk: [...st.querySelectorAll('img')].every(i => !i.naturalWidth ||
                 Math.abs(i.getBoundingClientRect().width / i.getBoundingClientRect().height - i.naturalWidth / i.naturalHeight) < 0.02),
              href: a && a.getAttribute('href'), target: a && a.getAttribute('target'),
              gridHidden: document.getElementById('archive').style.visibility,
              fly: !!document.querySelector('.post-fly')}; }""")
    check("the week opens", po["open"] and po["head"] == "WEEK 5 2024", po)
    check("at the photo that was clicked", abs(po["off"]) < 60, po["off"])
    check("the address carries the photo", po["hash"] == "#2024-w5-i7", po["hash"])
    check("the page behind is blurred and darkened", po["scrim"])
    check("the week's own writing is shown", po["text"] > 0, po["text"])
    check("every photo is the width of V2's column", len(po["widths"]) == 1 and po["widths"][0] == po["col"], po)
    check("V2's column is about 640px of content", 600 <= po["col"] <= 680, po["col"])
    check("and each keeps its own proportions", po["ratioOk"])
    check("photos carry the reverse-image link", "lens.google.com" in (po["href"] or "") and po["target"] == "_blank", po["href"])
    check("the grid is hidden while the week covers it", po["gridHidden"] == "hidden", po["gridHidden"])
    check("the flying copy is tidied away", not po["fly"])
    # The week ends where its photos end: a margin after the last one, not half a screen of nothing
    tail = pg.evaluate("""() => { const v = document.getElementById('postView'), st = document.getElementById('postStack');
      const last = st.children[st.children.length - 1];
      const was = v.scrollTop; v.scrollTop = v.scrollHeight;
      const gap = v.getBoundingClientRect().bottom - last.getBoundingClientRect().bottom;
      v.scrollTop = was;
      return {gap: Math.round(gap), vh: Math.round(v.getBoundingClientRect().height)}; }""")
    check("no dead space after the last photo", tail["gap"] < tail["vh"] * 0.25, tail)
    pg.screenshot(path=os.path.join(shots, "v5-desktop-post.png"))

    # ---------------- leaving: it flies home to its own thumbnail ----------------
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)
    check("leaving starts the flight back", pg.evaluate(FLY))
    # The archive has to be back before the photo starts for home, or the flight crosses a blank page
    # and the grid only reappears once it has landed.
    check("and the grid is already back for it to land on",
          pg.evaluate("() => getComputedStyle(document.getElementById('archive')).visibility") == "visible")
    pg.wait_for_timeout(1500)
    home = pg.evaluate("""() => { const t = document.querySelector('.fg-cell img[data-k="2024-5"][data-n="7"]');
      const b = t.getBoundingClientRect();
      return {open: document.getElementById('postView').classList.contains('open'),
              thumbShown: getComputedStyle(t).visibility === 'visible',
              onScreen: b.top >= -1 && b.bottom <= innerHeight + 1,
              fly: !!document.querySelector('.post-fly'),
              grid: getComputedStyle(document.getElementById('archive')).visibility,
              hash: location.hash}; }""")
    check("the week closes", not home["open"], home)
    check("the photo lands back on its own thumbnail", home["thumbShown"] and home["onScreen"], home)
    check("the grid is back", home["grid"] == "visible", home["grid"])
    check("nothing is left flying", not home["fly"])
    check("and the address is back at the archive", home["hash"] in ("", "#"), home["hash"])

    # ---------------- the week number opens the writing ----------------
    lbl = pg.locator('.fg-label[data-k="2024-5"]')
    lbl.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    lbl.click()
    pg.wait_for_timeout(900)
    wk = pg.evaluate("""() => ({hash: location.hash, top: Math.round(document.getElementById('postView').scrollTop),
      textTop: Math.round(document.getElementById('postText').getBoundingClientRect().top),
      shown: !document.getElementById('postText').hidden})""")
    check("the week number opens the week at the top", wk["hash"] == "#2024-w5" and wk["top"] == 0, wk)
    check("with the writing on screen", wk["shown"] and 0 < wk["textTop"] < 900, wk)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(1400)

    # ---------------- a shared link, and the Back button ----------------
    pg.goto(B + "/v5/#2024-w3-i8", wait_until="load")
    pg.wait_for_timeout(1500)
    check("a shared link opens straight into that week", pg.evaluate(OPEN))
    dl = pg.evaluate("""() => { const b = document.getElementById('postStack').children[7].getBoundingClientRect();
      return Math.round((b.top + b.height / 2) - innerHeight / 2); }""")
    check("on the photo the link names", abs(dl) < 60, dl)
    pg.click("#postBack")
    pg.wait_for_timeout(1600)
    check("ARCHIVE returns to the grid", not pg.evaluate(OPEN))

    t4 = pg.locator('.fg-cell img[data-k="2023-40"][data-n="4"]')
    t4.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    t4.click(); pg.wait_for_timeout(1500)
    pg.go_back()
    pg.wait_for_timeout(1600)
    bk = pg.evaluate("""() => { const t = document.querySelector('.fg-cell img[data-k="2023-40"][data-n="4"]');
      return {open: document.getElementById('postView').classList.contains('open'),
              thumbShown: getComputedStyle(t).visibility === 'visible'}; }""")
    check("the browser Back button also closes and flies home", not bk["open"] and bk["thumbShown"], bk)

    # ---------------- year filter and theme ----------------
    pg.locator('.site-head .years button[data-filter="2024"]').click()
    pg.wait_for_timeout(300)
    # Whole sections are hidden, so offsetParent rather than the week's own display tells you what is left
    yf = pg.evaluate("""() => {
      const shown = [...document.querySelectorAll('.fg-week')].filter(w => w.offsetParent !== null);
      return {shown: shown.length, years: [...new Set(shown.map(w => w.dataset.year))],
              stickies: [...document.querySelectorAll('.fg-sticky')].filter(s => s.offsetParent !== null).length,
              marked: [...document.querySelectorAll('.years button[data-filter="2024"]')].every(b => b.classList.contains('active'))}; }""")
    check("the year filter shows only that year", yf["years"] == ["2024"], yf)
    check("and the hidden year takes its sticky label with it", yf["stickies"] <= 1, yf)
    check("and both copies of the years are marked", yf["marked"], yf)
    pg.locator('.site-head .years button[data-filter="all"]').click()
    pg.wait_for_timeout(300)
    check("ALL brings them back", pg.evaluate("() => [...document.querySelectorAll('.fg-week')].filter(w => getComputedStyle(w).display !== 'none').length") == N)

    was = pg.evaluate("() => document.documentElement.dataset.theme")
    pg.locator(".site-head .theme-toggle").click()
    pg.wait_for_timeout(250)
    other = "dark" if was == "light" else "light"
    th2 = pg.evaluate("""() => ({theme: document.documentElement.dataset.theme,
      both: [...document.querySelectorAll('.theme-toggle')].map(t => t.textContent.trim()),
      saved: localStorage.getItem('theme')})""")
    check("the theme toggle switches and is remembered", th2["theme"] == other and th2["saved"] == other, (was, th2))
    check("and both copies say the same thing", len(set(th2["both"])) == 1, th2["both"])
    check("the toggle now offers the one you came from", th2["both"][0] == was.upper(), (was, th2["both"]))
    pg.locator(".site-head .theme-toggle").click(); pg.wait_for_timeout(200)
    check("switching back to the device's own mode stops saving a choice",
          pg.evaluate("() => localStorage.getItem('theme')") is None)

    check("no page errors anywhere in that", not errors, errors[:3])
    pg.close()

    # ---------------- the scroll-up bar (V2) ----------------
    sp = br.new_page(viewport={"width": 1440, "height": 900})
    sp.goto(B + "/v5/", wait_until="load")
    sp.wait_for_timeout(1500)
    sp.mouse.move(720, 700)   # park the pointer off the bar, or resting on it holds it open
    SHOW = "() => document.getElementById('slimbar').classList.contains('show')"
    check("no bar at the top of the page", not sp.evaluate(SHOW))
    sp.evaluate("window.scrollTo(0, 2000)"); sp.wait_for_timeout(250)
    check("the first scroll down shows it once, as a hint", sp.evaluate(SHOW))
    sp.wait_for_timeout(2400)
    check("then it goes away", not sp.evaluate(SHOW))
    sp.evaluate("window.scrollTo(0, 4000)"); sp.wait_for_timeout(400)
    check("and stays away while you head down", not sp.evaluate(SHOW))
    sp.evaluate("window.scrollTo(0, 3000)"); sp.wait_for_timeout(400)
    check("heading back up brings it in", sp.evaluate(SHOW))
    # V2's frosted band, not a flat panel: the tint and blur live on ::before, feathered along the bottom
    bar = sp.evaluate("""() => { const s = document.getElementById('slimbar');
      const be = getComputedStyle(s, '::before');
      return {top: Math.round(s.getBoundingClientRect().top),
              tint: be.backgroundColor, blur: be.backdropFilter || be.webkitBackdropFilter,
              feather: be.maskImage || be.webkitMaskImage,
              flat: getComputedStyle(s).borderBottomWidth,
              years: s.querySelectorAll('.years button').length, hasTop: !!s.querySelector('#slimTop')}; }""")
    check("sitting at the top", bar["top"] <= 1, bar)
    check("frosted, not a flat panel", "blur" in (bar["blur"] or "") and bar["tint"] != "rgba(0, 0, 0, 0)", bar)
    check("and feathered out along the bottom instead of ruled off",
          "gradient" in (bar["feather"] or "") and bar["flat"] == "0px", bar)
    check("carrying every year plus ALL", bar["years"] == len(years) + 1, bar["years"])
    sp.click("#slimTop")
    sp.wait_for_timeout(2200)
    check("TOP glides back to the start", sp.evaluate("() => pageYOffset") == 0)
    check("and the bar steps aside once you are there", not sp.evaluate(SHOW))
    sp.close()

    # ---------------- phone: the same page, fewer columns ----------------
    ph = br.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    perrs = []
    ph.on("pageerror", lambda e: perrs.append(str(e)))
    ph.goto(B + "/v5/", wait_until="load")
    ph.wait_for_timeout(1600)
    m = ph.evaluate("""() => { const row = document.querySelector('.fg-row');
      const cell = document.querySelector('.fg-cell'), img = cell.querySelector('img');
      const cb = cell.getBoundingClientRect();
      return {cols: getComputedStyle(row).gridTemplateColumns.split(' ').length,
              gap: getComputedStyle(row).gap, square: Math.abs(cb.width - cb.height) < 1.5,
              fit: getComputedStyle(img).objectFit,
              label: document.querySelector('.fg-label').innerText.replace(/\\s+/g, ' ').trim(),
              name: document.querySelector('.site-name').innerText.trim(),
              overflow: document.documentElement.scrollWidth > innerWidth + 1}; }""")
    check("phone: 3 across (V2)", m["cols"] == 3, m["cols"])
    check("phone: V2's 2px gap", m["gap"].startswith("2px"), m["gap"])
    check("phone: square cells, photos still shown whole", m["square"] and m["fit"] == "contain", m)
    check("phone: each week carries its week and year", m["label"] == "9 2024", m["label"])
    check("phone: the title shortens", m["name"] == "12FPW", m["name"])
    check("phone: no sideways scrolling at 390", not m["overflow"])
    cl = ph.evaluate("""() => { const w = document.querySelectorAll('.fg-week')[1], prev = document.querySelectorAll('.fg-week')[0];
      const l = w.querySelector('.fg-label'), b = l.querySelector('b'), r = document.createRange();
      r.setStart(b, 0); r.setEndAfter(l.querySelector('.fg-yr')); const ink = r.getBoundingClientRect();
      const lb = l.getBoundingClientRect(), above = prev.querySelector('.fg-row').getBoundingClientRect().bottom;
      const next = (w.querySelector('.fg-text') || w.querySelector('.fg-row')).getBoundingClientRect().top;
      return {off: Math.abs((ink.left + ink.width / 2) - innerWidth / 2), above: lb.top - above, below: next - lb.bottom}; }""")
    check("phone: the week and year are centred across the screen", cl["off"] <= 2, cl)
    check("phone: and centred between the week before and its own", abs(cl["above"] - cl["below"]) <= 1, cl)
    ph.screenshot(path=os.path.join(shots, "v5-phone-landing.png"))
    ph.mouse.wheel(0, 1500); ph.wait_for_timeout(500)
    ph.evaluate("() => scrollBy(0, -200)"); ph.wait_for_timeout(600)
    pb = ph.evaluate("""() => { const bar = document.getElementById('slimbar'), b = bar.getBoundingClientRect();
      const t = bar.querySelector('.slim-top').getBoundingClientRect(), ps = getComputedStyle(bar, '::before');
      return {shown: bar.classList.contains('show'), above: t.top - b.top, below: b.bottom - t.bottom,
              fade: -parseFloat(ps.bottom), mask: ps.webkitMaskImage || ps.maskImage}; }""")
    check("phone: the frosted bar is as solid under its words as above them", pb["shown"] and abs(pb["above"] - pb["below"]) <= 1, pb)
    check("phone: then feathers out over a long eased run below the bar", pb["fade"] >= 30 and pb["mask"].count("rgba") >= 3, pb)
    ph.screenshot(path=os.path.join(shots, "v5-phone-bar.png"))
    # the toolbar collapsing mid-scroll changes only the height: it must not pull the page back
    ph.evaluate("() => scrollTo(0, 2000)"); ph.wait_for_timeout(300)
    ph.set_viewport_size({"width": 390, "height": 900})
    ph.evaluate("() => scrollTo(0, 2600)")
    ph.wait_for_timeout(500)
    ty = ph.evaluate("() => pageYOffset")
    check("phone: the toolbar hiding mid-scroll does not yank the page back", abs(ty - 2600) <= 1, ty)
    ph.set_viewport_size({"width": 390, "height": 844}); ph.wait_for_timeout(300)
    ph.evaluate("() => scrollTo(0, 0)"); ph.wait_for_timeout(600)

    # ---------------- phone: the weekly blurb sits open in the grid ----------------
    bl = ph.evaluate("""() => { const t = document.querySelector('.fg-text[data-k="2024-5"]');
      const label = document.querySelector('.fg-label[data-k="2024-5"]').getBoundingClientRect();
      const row = document.querySelector('.fg-row[data-k]') || t.nextElementSibling;
      return {present: !!t, shown: t && getComputedStyle(t).display !== 'none',
              hasText: !!(t && t.innerText.trim()),
              afterLabel: t.getBoundingClientRect().top >= label.bottom - 1,
              beforeRow: t.getBoundingClientRect().bottom <= row.getBoundingClientRect().top + 1,
              role: t.getAttribute('role'), tabindex: t.getAttribute('tabindex')}; }""")
    check("phone: the week's writing is right there in the grid", bl["present"] and bl["shown"] and bl["hasText"], bl)
    check("phone: sitting between the week number and the photos", bl["afterLabel"] and bl["beforeRow"], bl)
    check("phone: reachable as a button, by keyboard too", bl["role"] == "button" and bl["tabindex"] == "0", bl)

    ph.locator('.fg-text[data-k="2024-5"]').tap()
    ph.wait_for_timeout(900)
    bo = ph.evaluate("""() => ({open: document.getElementById('postView').classList.contains('open'),
      hash: location.hash, top: Math.round(document.getElementById('postView').scrollTop),
      text: document.getElementById('postText').innerText.trim().length > 0})""")
    check("phone: tapping the blurb opens the full week too, from the top", bo["open"] and bo["hash"] == "#2024-w5" and bo["top"] == 0, bo)
    check("phone: with its own writing right there", bo["text"])
    ph.locator("#postBack").tap()
    ph.wait_for_timeout(1600)

    # a link inside the blurb is still just a link — tapping it must not swallow the tap into the post
    link = ph.locator('.fg-text[data-k="2023-21"] a').first
    link.scroll_into_view_if_needed(); ph.wait_for_timeout(300)
    popped = None
    try:
        with ph.context.expect_page(timeout=3000) as pop:
            link.tap()
        popped = pop.value
    except Exception:
        pass
    ph.wait_for_timeout(300)
    lp = ph.evaluate("() => document.getElementById('postView').classList.contains('open')")
    check("phone: except a link in the blurb, which opens for itself", bool(popped) and not lp, {"popup": bool(popped), "postOpen": lp})
    if popped: popped.close()
    ph.screenshot(path=os.path.join(shots, "v5-phone-blurb.png"))

    # ---------------- desktop: the dense one-line week has no room for the blurb ----------------
    dp = br.new_page(viewport={"width": 1440, "height": 900})
    dp.goto(B + "/v5/", wait_until="load")
    dp.wait_for_timeout(400)
    dt = dp.evaluate("""() => { const t = document.querySelector('.fg-text[data-k="2024-5"]');
      return {present: !!t, hidden: t && getComputedStyle(t).display === 'none'}; }""")
    check("desktop: the blurb exists but stays out of the one-line week row", dt["present"] and dt["hidden"], dt)
    dp.close()

    # the very same gesture, and the very same flight
    pt = ph.locator('.fg-cell img[data-k="2024-5"][data-n="7"]')
    pt.scroll_into_view_if_needed(); ph.wait_for_timeout(400)
    pt.tap()
    ph.wait_for_timeout(140)
    check("phone: one tap starts the flight", ph.evaluate(FLY))
    ph.wait_for_timeout(1400)
    mp = ph.evaluate("""() => { const st = document.getElementById('postStack');
      const b = st.children[6].getBoundingClientRect();
      const ws = [...st.querySelectorAll('img')].map(i => Math.round(i.getBoundingClientRect().width));
      return {open: document.getElementById('postView').classList.contains('open'), hash: location.hash,
              off: Math.round((b.top + b.height / 2) - innerHeight / 2),
              widths: [...new Set(ws)], col: Math.round(st.clientWidth),
              scrim: document.getElementById('postScrim').classList.contains('fx')}; }""")
    check("phone: it opens at the photo that was tapped", mp["open"] and abs(mp["off"]) < 60, mp)
    check("phone: the same address as the desktop", mp["hash"] == "#2024-w5-i7", mp["hash"])
    check("phone: photos fill the column, all one width", len(mp["widths"]) == 1 and mp["widths"][0] == mp["col"], mp)
    check("phone: the same blur behind", mp["scrim"])
    ph.screenshot(path=os.path.join(shots, "v5-phone-post.png"))
    ph.locator("#postBack").tap()
    ph.wait_for_timeout(1600)
    phome = ph.evaluate("""() => { const t = document.querySelector('.fg-cell img[data-k="2024-5"][data-n="7"]');
      const b = t.getBoundingClientRect();
      return {open: document.getElementById('postView').classList.contains('open'),
              thumbShown: getComputedStyle(t).visibility === 'visible',
              onScreen: b.top >= -1 && b.bottom <= innerHeight + 1}; }""")
    check("phone: ARCHIVE flies it home to its thumbnail", not phome["open"] and phome["thumbShown"] and phome["onScreen"], phome)
    check("phone: no page errors", not perrs, perrs[:3])
    ph.close()

    # ---------------- zooming keeps your place ----------------
    # Browser zoom shrinks the CSS viewport and reflows; it does not scale the coordinate system. So the
    # honest way to simulate it is to resize the window, which drives the very resize path v5.js listens
    # on. (body.style.zoom would scale getBoundingClientRect but not scrollBy, a mismatch the real
    # gesture never produces.) 2x here crosses the 900px breakpoint into the 3-across layout, where a
    # week is four rows tall instead of one: the week you are on must survive even that.
    BASE_W, BASE_H = 1440, 800
    gp = br.new_page(viewport={"width": BASE_W, "height": BASE_H})
    gp.goto(B + "/v5/", wait_until="load"); gp.wait_for_timeout(1500)
    gp.add_style_tag(content="*{overflow-anchor:none!important}")
    gp.evaluate("document.querySelectorAll('.fg-week')[9].scrollIntoView({block: 'center'})")
    gp.wait_for_timeout(600)
    # the same line v5.js anchors on (gridProbeY): nothing is pinned over the grid at any width
    ROW = """() => { const y = 12;
      const rows = [...document.querySelectorAll('.fg-week')];
      for (let i = 0; i < rows.length; i++) { const r = rows[i].getBoundingClientRect();
        if (r.height && r.bottom >= y) return {row: i, f: Math.round((y - r.top) / r.height * 100) / 100,
                                               wide: innerWidth >= 900,
                                               h: document.documentElement.scrollWidth > innerWidth + 1}; } }"""
    base = gp.evaluate(ROW); seen = []
    for z in (1.25, 1.5, 2, 1):
        gp.set_viewport_size({"width": round(BASE_W / z), "height": round(BASE_H / z)})
        gp.wait_for_timeout(600)
        seen.append((z, gp.evaluate(ROW)))
    check("zooming keeps the same week in view",
          all(r["row"] == base["row"] for z, r in seen), (base, seen))
    check("and lands on much the same part of it, while the layout holds",
          all(abs(r["f"] - base["f"]) < 0.15 for z, r in seen if r["wide"]), (base, seen))
    check("and never sideways-scrolls", not any(r["h"] for z, r in seen), seen)
    check("back at 100% it is exactly where it started",
          seen[-1][1]["row"] == base["row"] and abs(seen[-1][1]["f"] - base["f"]) < 0.08, (base, seen[-1]))
    gp.close()
    br.close()

srv.terminate()
print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
