"""V5 in WebKit (Safari's engine): the flight home from a week must not freeze.
Scrolling down a week loads its full-size photos, and Safari makes room by letting go of the grid's
thumbnails. Closing the week then had to redraw a screenful of 700px thumbnails in the very frame the
flight started, which froze it for most of its length (median ~900ms here), so the photo jumped
straight to its thumbnail or raced to catch up. The grid now draws copies sized to its cells.
Headless WebKit renders in software and is much slower than Safari on a Mac, so the limit is loose:
it is there to catch the freeze coming back, not to time real frames.
Run after building:  python3 tests/test_v5_webkit.py"""
import subprocess, time, os
from playwright.sync_api import sync_playwright

proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=proj, env={**os.environ, "PORT": "3281"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3281"
res = []
def check(name, cond, extra=""):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))

# Longest gap between painted frames from the moment ARCHIVE is clicked
TRACE = """() => new Promise(res => {
  const ts = []; let n = 0;
  const step = (t) => { ts.push(t); if (++n < 60) requestAnimationFrame(step); else res(Math.round(Math.max(...ts.slice(1).map((x, i) => x - ts[i])))); };
  requestAnimationFrame(step);
  setTimeout(() => document.getElementById('postBack').click(), 0);
})"""

try:
    with sync_playwright() as pw:
        br = pw.webkit.launch()
        pg = br.new_page(viewport={"width": 1440, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(B + "/v5/", wait_until="load"); pg.wait_for_timeout(1500)
        stalls = []
        for run in range(5):
            pg.evaluate("() => scrollTo(0, 1200)"); pg.wait_for_timeout(600)
            im = pg.locator('.fg-cell img').nth(40 + run * 25)
            im.scroll_into_view_if_needed(); pg.wait_for_timeout(500)
            im.click(); pg.wait_for_timeout(1800)
            pg.mouse.wheel(0, 900); pg.wait_for_timeout(900)   # scrolled down the week, as in the report
            stalls.append(pg.evaluate(TRACE))
            pg.wait_for_timeout(1200)
        med = sorted(stalls)[len(stalls) // 2]
        check("WebKit: the flight home starts without a freeze (median longest frame %dms)" % med, med < 500, stalls)
        landed = pg.evaluate("() => !document.querySelector('.post-fly') && !document.getElementById('postView').classList.contains('open')")
        check("WebKit: and it lands, leaving nothing behind", landed)
        check("WebKit: no page errors", not errs, errs[:3])
        br.close()
finally:
    srv.terminate()
print(f"\n{sum(res)}/{len(res)} passed")
