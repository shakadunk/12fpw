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

        # other pages keep the original footer
        for url in ("/archive/", "/2024/week-3/"):
            page3.goto(B + url); page3.wait_for_load_state("networkidle")
            f = page3.locator("footer").text_content()
            check(f"{url}: footer keeps the name + Archive link (Subscribe link removed with the signup form)", "12 Frames Per Week" in f and "Archive" in f and "Subscribe" not in f and page3.locator("#today").count() == 0)

        # light theme and phone
        page3.add_init_script("try{localStorage.setItem('theme','light')}catch(e){}")
        page3.goto(B + "/"); page3.reload(); page3.wait_for_load_state("networkidle")
        page3.screenshot(path="/tmp/12fpw-test-shots/footer-home-light.png", clip={"x": 0, "y": 600, "width": 1440, "height": 300})
        m = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True).new_page()
        m.goto(B + "/"); m.wait_for_load_state("networkidle")
        check("phone: date visible at bottom right, no horizontal overflow", m.evaluate("(()=>{const r=document.getElementById('today').getBoundingClientRect();return r.right<=innerWidth && r.right>innerWidth-40 && document.documentElement.scrollWidth<=innerWidth})()"))
        m.evaluate("window.scrollTo(0, document.body.scrollHeight)"); m.wait_for_timeout(200)
        m.screenshot(path="/tmp/12fpw-test-shots/footer-home-phone.png")
        check("no console errors", not errors)
        if errors: print(errors)
        br.close()
finally:
    srv.terminate()
print(f"{sum(ok for _, ok in results)}/{len(results)} passed")
sys.exit(0 if all(ok for _, ok in results) else 1)
