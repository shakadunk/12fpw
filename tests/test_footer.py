import subprocess, time, os, sys, datetime
from playwright.sync_api import sync_playwright
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."), env={**os.environ, "PORT": "3222"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3222"
results = []
def check(name, cond):
    results.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name)
try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 1440, "height": 900}, timezone_id="America/New_York")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e))); page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        # fixed clock: late evening, Oct 26 2026
        page.clock.install(time=datetime.datetime(2026, 10, 26, 23, 58, 0))
        page.goto(B + "/"); page.wait_for_load_state("networkidle")
        foot = page.locator("footer")
        check("home: footer shows today's date", page.inner_text("#today").strip().lower() == "26 october 2026")
        check("home: date is in the footer, bottom right", page.evaluate("(()=>{const r=document.getElementById('today').getBoundingClientRect();return r.right>innerWidth-60 && r.left>innerWidth/2})()"))
        check("home: old footer content removed (no name, no links)", "frames per week" not in foot.text_content().lower() and foot.locator("a").count() == 0)
        check("home: <time> has a machine-readable date", page.get_attribute("#today", "datetime") == "2026-10-26")
        check("home: date is small uppercase label style", page.evaluate("(()=>{const c=getComputedStyle(document.getElementById('today'));return c.textTransform==='uppercase'&&c.fontSize==='12px'})()"))
        page.screenshot(path="/tmp/12fpw-test-shots/footer-home-dark.png", clip={"x": 0, "y": 600, "width": 1440, "height": 300})

        # wide screens: the date stays put in the bottom-right corner while the feed scrolls (like LIGHT/DARK in the bottom-left)
        d0 = page.evaluate("(()=>{const r=document.getElementById('today').getBoundingClientRect();return [r.right, r.bottom, getComputedStyle(document.getElementById('today')).position]})()")
        page.evaluate("window.scrollTo(0, 2500)"); page.wait_for_timeout(300)
        d1 = page.evaluate("(()=>{const r=document.getElementById('today').getBoundingClientRect();return [r.right, r.bottom]})()")
        check("home (wide): the date is fixed in the bottom-right corner and does not move when scrolling", d0[2] == "fixed" and abs(d0[0] - d1[0]) < 1 and abs(d0[1] - d1[1]) < 1 and 1440 - d0[0] < 50 and 900 - d0[1] < 50)
        lt = page.evaluate("(()=>{const a=document.getElementById('corner-theme').getBoundingClientRect(), b=document.getElementById('today').getBoundingClientRect();return [Math.abs(a.bottom-b.bottom), a.left, 1440-b.right]})()")
        check("home (wide): same height and same margin as the LIGHT/DARK label in the opposite corner", lt[0] < 3 and abs(lt[1] - lt[2]) < 1)
        page.evaluate("window.scrollTo(0, 0)")

        # live update across midnight (same open page)
        page.clock.run_for(3 * 60 * 1000)          # 23:58 -> 00:01
        check("home: date rolls over to the next day by itself at midnight", page.inner_text("#today").strip().lower() == "27 october 2026" and page.get_attribute("#today", "datetime") == "2026-10-27")

        # year change
        page2 = ctx.new_page(); page2.clock.install(time=datetime.datetime(2026, 12, 31, 23, 59, 30))
        page2.goto(B + "/"); page2.wait_for_load_state("networkidle")
        page2.clock.run_for(60 * 1000)
        check("home: rolls over a new year too", page2.inner_text("#today").strip().lower() == "01 january 2027")

        # real clock matches the browser's today
        page3 = ctx.new_page(); page3.goto(B + "/"); page3.wait_for_load_state("networkidle")
        expected = page3.evaluate("new Date().toLocaleDateString('en-GB',{day:'2-digit',month:'long',year:'numeric'})").lower()
        check("home: with the real clock it shows the device's date", page3.inner_text("#today").strip().lower() == expected)

        # every other page has no footer text at all (the name and Archive link were removed), only empty space at the bottom
        for url in ("/archive/", "/2023/week-3/", "/no-such-page/"):
            page3.goto(B + url); page3.wait_for_load_state("networkidle")
            txt = page3.evaluate("[...document.querySelectorAll('.site-footer')].map(e => e.textContent.trim()).join('')")
            check(f"{url}: no footer text or links (no name, no Archive link)", txt == "" and page3.locator(".site-footer a").count() == 0 and page3.locator("footer").count() == 0 and page3.locator("#today").count() == 0)
            check(f"{url}: still some space under the last content", page3.evaluate("(()=>{const f=document.querySelector('.site-footer');return f && f.getBoundingClientRect().height >= 60})()"))
        page3.goto(B + "/archive/#grid"); page3.wait_for_load_state("networkidle")
        check("grid page: nothing below the grid but space", page3.evaluate("document.body.innerText.toLowerCase().trim().endsWith('2023') || !document.body.innerText.toLowerCase().includes('12 frames per week archive')"))

        # light theme and phone
        page3.add_init_script("try{localStorage.setItem('theme','light')}catch(e){}")
        page3.goto(B + "/"); page3.reload(); page3.wait_for_load_state("networkidle")
        page3.screenshot(path="/tmp/12fpw-test-shots/footer-home-light.png", clip={"x": 0, "y": 600, "width": 1440, "height": 300})
        m = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True).new_page()
        m.goto(B + "/"); m.wait_for_load_state("networkidle")
        check("phone: date visible at bottom right, no horizontal overflow", m.evaluate("(()=>{const r=document.getElementById('today').getBoundingClientRect();return r.right<=innerWidth && r.right>innerWidth-40 && document.documentElement.scrollWidth<=innerWidth})()"))
        m.evaluate("window.scrollTo(0, document.body.scrollHeight)"); m.wait_for_timeout(200)
        m.screenshot(path="/tmp/12fpw-test-shots/footer-home-phone.png")
        # under 1200px the date stays in the footer at the very end of the feed
        mid = br.new_context(viewport={"width": 1000, "height": 800}).new_page(); mid.goto(B + "/"); mid.wait_for_load_state("networkidle")
        check("home (under 1200px): the date is not fixed, it sits in the footer", mid.evaluate("getComputedStyle(document.getElementById('today')).position") == "static")
        check("no console errors", not errors)
        if errors: print(errors)
        br.close()
finally:
    srv.terminate()
print(f"{sum(ok for _, ok in results)}/{len(results)} passed")
sys.exit(0 if all(ok for _, ok in results) else 1)
