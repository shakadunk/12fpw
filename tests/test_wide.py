"""One header and scroll-up-bar system on every screen size (desktop matches the phone layout since 2026-10-28): LIGHT/DARK at the top-left,
the name centred (TOP in the bar, in the same centre spot), ARCHIVE at the top-right, the ARCHIVE menu right-aligned. No corner LIGHT/DARK
label any more. On 1200px and wider the date stays fixed in the bottom-right corner.   Run after building:  python3 tests/test_wide.py"""
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
def mid(r): return (r["l"] + r["r"]) / 2
def bar_up(page):
    page.evaluate("window.scrollTo(0,1800)"); page.wait_for_timeout(250); page.evaluate("window.scrollBy(0,-150)"); page.wait_for_timeout(350)

try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        for width in (720, 1024, 1199, 1200, 1440, 1920):
            ctx = br.new_context(viewport={"width": width, "height": 900})
            ctx.add_init_script("try{history.scrollRestoration='manual'}catch(e){}")
            pg = ctx.new_page()
            pg.goto(B + "/2023/week-2/"); pg.wait_for_load_state("networkidle")
            w = f"{width}px: "
            pad = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.site-header')).paddingLeft)")
            check(w + "no corner LIGHT/DARK label any more", pg.evaluate("document.getElementById('corner-theme')") is None)
            lt, nm, ar = rect(pg, "#theme-toggle"), rect(pg, "#site-name"), rect(pg, "#nav-btn")
            check(w + "header: LIGHT/DARK at the top-left corner", vis(pg, "#theme-toggle") and abs(lt["l"] - pad) < 2)
            check(w + "header: the name is centred on the page", abs(mid(nm) - width / 2) < 2)
            check(w + "header: ARCHIVE at the top-right corner", abs(ar["r"] - (width - pad)) < 2)
            check(w + "header: the full name shows (12 FRAMES PER WEEK, not 12FPW)", pg.evaluate("document.querySelector('#site-name .long').getBoundingClientRect().width") > 0 and pg.evaluate("document.querySelector('#site-name .short').getBoundingClientRect().width") == 0)
            before = pg.evaluate("document.documentElement.dataset.theme")
            pg.click("#theme-toggle"); pg.wait_for_timeout(200)
            check(w + "header: LIGHT/DARK switches the theme", before == "dark" and pg.evaluate("document.documentElement.dataset.theme") == "light")
            pg.click("#theme-toggle"); pg.wait_for_timeout(150)
            bar_up(pg)
            check(w + "scroll-up bar appears", pg.evaluate("(()=>{const r=document.getElementById('slimbar').getBoundingClientRect();return getComputedStyle(document.getElementById('slimbar')).visibility==='visible'&&r.bottom>0&&r.top>=-1})()"))
            bl, bt, ba = rect(pg, "#slim-theme"), rect(pg, "#slim-top"), rect(pg, "#slim-btn")
            check(w + "bar: LIGHT/DARK at the left, TOP in the centre, ARCHIVE at the right", vis(pg, "#slim-theme") and abs(bl["l"] - lt["l"]) < 2 and abs(mid(bt) - width / 2) < 2 and abs(ba["r"] - ar["r"]) < 2)
            check(w + "bar: TOP sits exactly where the header name is (same centre)", abs(mid(bt) - mid(nm)) < 2)
            check(w + "bar: the name is not repeated", not vis(pg, "#slim-name"))
            pg.hover("#slim-btn"); pg.wait_for_timeout(600)
            mn = rect(pg, "#slim-menu")
            check(w + "bar menu opens, right-aligned under ARCHIVE, fully on screen", pg.evaluate("document.getElementById('slim-menu').hidden") is False and abs(mn["r"] - ba["r"]) < 1.5 and mn["l"] > 0)
            check(w + "no sideways scrolling", pg.evaluate("document.documentElement.scrollWidth") <= width)
            pg.mouse.move(width // 2, 600); pg.wait_for_timeout(500)
            pg.click("#slim-theme"); pg.wait_for_timeout(200)
            check(w + "bar: LIGHT/DARK switches the theme on one click", pg.evaluate("document.documentElement.dataset.theme") == "light")
            pg.click("#slim-theme"); pg.wait_for_timeout(150)
            # header menu
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(500)
            pg.hover("#nav-btn"); pg.wait_for_timeout(600)
            hm = rect(pg, "#nav-menu")
            check(w + "header menu opens right-aligned and on screen", pg.evaluate("document.getElementById('nav-menu').hidden") is False and abs(hm["r"] - ar["r"]) < 1.5 and hm["l"] > 0)
            pg.keyboard.press("Escape")
            if width >= 1200:
                d = pg.evaluate("(()=>{const e=document.getElementById('today');return e?getComputedStyle(e).position:null})()")
                pg.goto(B + "/"); pg.wait_for_load_state("networkidle")
                check(w + "home: the date is fixed in the bottom-right corner", pg.evaluate("getComputedStyle(document.getElementById('today')).position") == "fixed")
            # archive grid starts at the page margin (no inset)
            pg.goto(B + "/archive/#grid"); pg.wait_for_load_state("networkidle")
            gl = pg.evaluate("document.querySelector('.fg-label').getBoundingClientRect().left")
            check(w + "archive grid starts at the page margin (the old corner inset is gone)", gl < pad + 6)
            ctx.close()

        # phone: the same system, short name
        ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True); pg = ctx.new_page()
        pg.goto(B + "/"); pg.wait_for_load_state("networkidle")
        nm = rect(pg, "#site-name")
        check("phone: same system, with the short name 12FPW centred", vis(pg, "#theme-toggle") and abs(mid(nm) - 195) < 2 and pg.evaluate("document.querySelector('#site-name .long').getBoundingClientRect().width") == 0)
        ctx.close()
        br.close()
finally:
    srv.terminate()
print(f"{sum(res)}/{len(res)} passed"); sys.exit(0 if all(res) else 1)
