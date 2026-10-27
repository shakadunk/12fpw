"""Wide desktop layout (1200px and up): LIGHT/DARK stands alone in the bottom-left corner, ARCHIVE is the far-right item in
the header and in the scroll-up bar (so it never moves), TOP sits to its left in the bar, and the ARCHIVE menu opens
right-aligned. Below 1200px (tablets, phones) the older layout stays.   Run after building:  python3 tests/test_wide.py"""
import subprocess, time, os, sys
from playwright.sync_api import sync_playwright

proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=proj, env={**os.environ, "PORT": "3268"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3268"
res = []
def check(name, cond):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name)

def vis(page, sel):
    return page.evaluate("(s)=>{const e=document.querySelector(s);if(!e)return false;const r=e.getBoundingClientRect();return getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'&&r.width>0&&r.height>0}", sel)
def rect(page, sel):
    return page.evaluate("(s)=>{const r=document.querySelector(s).getBoundingClientRect();return {l:r.left,r:r.right,t:r.top,b:r.bottom}}", sel)
def bar_up(page):
    page.evaluate("window.scrollTo(0,1800)"); page.wait_for_timeout(250); page.evaluate("window.scrollBy(0,-150)"); page.wait_for_timeout(350)

try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        for width in (1200, 1440, 1920):
            ctx = br.new_context(viewport={"width": width, "height": 900})
            ctx.add_init_script("try{history.scrollRestoration='manual'}catch(e){}")
            pg = ctx.new_page()
            pg.goto(B + "/2023/week-2/"); pg.wait_for_load_state("networkidle")
            w = f"{width}px: "
            check(w + "header shows ARCHIVE only (no LIGHT/DARK)", vis(pg, "#nav-btn") and not vis(pg, "#theme-toggle"))
            hdr = rect(pg, "#nav-btn")
            check(w + "ARCHIVE is the far-right item in the header", abs(hdr["r"] - (width - pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.site-header')).paddingRight)"))) < 2)
            cr = rect(pg, "#corner-theme")
            check(w + "LIGHT/DARK stands alone, bottom-left corner", vis(pg, "#corner-theme") and cr["l"] < 60 and cr["b"] > 900 - 50 and cr["t"] > 900 - 80)
            check(w + "corner toggle is fixed (stays put when scrolling)", pg.evaluate("getComputedStyle(document.getElementById('corner-theme')).position") == "fixed")
            col = pg.evaluate("document.querySelector('.col').getBoundingClientRect().left")
            check(w + "corner toggle sits in the empty margin, not over the text column or images", cr["r"] < col - 20)
            before = pg.evaluate("document.documentElement.dataset.theme")
            lab = pg.evaluate("getComputedStyle(document.getElementById('corner-theme'),'::after').content")
            pg.click("#corner-theme"); pg.wait_for_timeout(200)
            after = pg.evaluate("document.documentElement.dataset.theme")
            lab2 = pg.evaluate("getComputedStyle(document.getElementById('corner-theme'),'::after').content")
            check(w + "corner toggle switches the theme and its label", before == "dark" and after == "light" and lab != lab2)
            pg.click("#corner-theme"); pg.wait_for_timeout(150)
            bar_up(pg)
            check(w + "scroll-up bar appears", pg.evaluate("(()=>{const r=document.getElementById('slimbar').getBoundingClientRect();return getComputedStyle(document.getElementById('slimbar')).visibility==='visible'&&r.bottom>0&&r.top>=-1})()"))
            check(w + "bar has no LIGHT/DARK, only TOP and ARCHIVE", not vis(pg, "#slim-theme") and vis(pg, "#slim-top") and vis(pg, "#slim-btn"))
            t, a = rect(pg, "#slim-top"), rect(pg, "#slim-btn")
            check(w + "TOP sits to the left of ARCHIVE", t["r"] < a["l"] and t["r"] > a["l"] - 60)
            check(w + "ARCHIVE does not move between the header and the bar (same right edge)", abs(a["r"] - hdr["r"]) < 1.5)
            check(w + "ARCHIVE label keeps the same size in the bar", abs((a["r"] - a["l"]) - (hdr["r"] - hdr["l"])) < 1.5)
            pg.hover("#slim-btn"); pg.wait_for_timeout(600)
            mn = rect(pg, "#slim-menu")
            check(w + "menu opens, right-aligned under ARCHIVE, fully on screen", pg.evaluate("document.getElementById('slim-menu').hidden") is False and abs(mn["r"] - a["r"]) < 1.5 and mn["l"] > 0)
            check(w + "no sideways scrolling", pg.evaluate("document.documentElement.scrollWidth") <= width)
            check(w + "menu text is right-aligned", pg.evaluate("getComputedStyle(document.getElementById('slim-menu')).textAlign") == "right")
            # header menu
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(500)
            pg.hover("#nav-btn"); pg.wait_for_timeout(600)
            hm = rect(pg, "#nav-menu")
            check(w + "header menu opens right-aligned and on screen", pg.evaluate("document.getElementById('nav-menu').hidden") is False and abs(hm["r"] - hdr["r"]) < 1.5)
            pg.keyboard.press("Escape")
            # archive page
            pg.goto(B + "/archive/#grid"); pg.wait_for_load_state("networkidle")
            gl = pg.evaluate("document.querySelector('.fg-label').getBoundingClientRect().left")
            cr2 = rect(pg, "#corner-theme")
            check(w + "corner toggle clears the archive grid (FULL is the default view) too", cr2["r"] < gl - 8)
            ctx.close()

        # narrower than 1200: the older layout
        for width in (1199, 1024, 800):
            ctx = br.new_context(viewport={"width": width, "height": 900}); pg = ctx.new_page()
            pg.goto(B + "/2023/week-2/"); pg.wait_for_load_state("networkidle")
            w = f"{width}px: "
            check(w + "older layout: LIGHT/DARK in the header, no corner toggle", vis(pg, "#theme-toggle") and not vis(pg, "#corner-theme"))
            bar_up(pg)
            order = pg.evaluate("[...document.querySelectorAll('#slim-grp > *')].filter(e=>e.getBoundingClientRect().width>0).sort((a,b)=>a.getBoundingClientRect().left-b.getBoundingClientRect().left).map(e=>e.id||e.className)")
            check(w + "older layout: bar reads ARCHIVE, TOP, LIGHT", order[-1] == "slim-theme" and order[-2] == "slim-top")
            ctx.close()

        # phone
        ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True); pg = ctx.new_page()
        pg.goto(B + "/"); pg.wait_for_load_state("networkidle")
        check("phone: unchanged (LIGHT in the header, no corner toggle)", vis(pg, "#theme-toggle") and not vis(pg, "#corner-theme"))
        ctx.close()
        br.close()
finally:
    srv.terminate()
print(f"{sum(res)}/{len(res)} passed"); sys.exit(0 if all(res) else 1)
