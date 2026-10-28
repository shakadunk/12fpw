"""ARCHIVE must open on the FIRST tap on a phone, in the header and in the scroll-up bar, even when the browser's synthesized click never
arrives (it can be swallowed on iPhones right after the bar slides in). A drag or a release off the button does nothing; a mouse click and
the keyboard still work. Run after building:  python3 tests/test_touchtap.py"""
import subprocess, time, os, sys
from playwright.sync_api import sync_playwright
proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=proj, env={**os.environ, "PORT": "3279"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3279"
res = []
def check(name, cond):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name)
# touch pointer events without the click that normally follows
TOUCH = """([sel, dx, dy, cancel]) => { const b = document.querySelector(sel), r = b.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2;
  const mk = (t, px, py) => new PointerEvent(t, {pointerType: 'touch', pointerId: 7, isPrimary: true, bubbles: true, cancelable: true, clientX: px, clientY: py});
  b.dispatchEvent(mk('pointerdown', x, y)); if (cancel) b.dispatchEvent(mk('pointercancel', x, y)); b.dispatchEvent(mk('pointerup', x + dx, y + dy)); }"""
def to_bar(pg):
    for _ in range(4): pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(200)
    pg.evaluate("window.scrollTo(0, 3000)"); pg.wait_for_timeout(300); pg.evaluate("window.scrollBy(0,-120)"); pg.wait_for_timeout(500)
def hidden(pg, id): return pg.evaluate(f"document.getElementById('{id}').hidden")
try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{history.scrollRestoration='manual'}catch(e){}")
        pg = ctx.new_page(); pg.goto(B + "/"); pg.wait_for_load_state("networkidle")
        # ---- header, at the top of the page
        pg.tap("#nav-btn"); pg.wait_for_timeout(250)
        check("header: one real tap opens the menu (and the click after it does not close it again)", not hidden(pg, "nav-menu"))
        pg.tap("#nav-btn"); pg.wait_for_timeout(250)
        check("header: a second tap closes it", hidden(pg, "nav-menu"))
        pg.evaluate(TOUCH, ["#nav-btn", 0, 0, False]); pg.wait_for_timeout(250)
        check("header: a tap whose click never arrives still opens the menu", not hidden(pg, "nav-menu"))
        pg.evaluate(TOUCH, ["#nav-btn", 0, 0, False]); pg.wait_for_timeout(250)
        pg.evaluate(TOUCH, ["#nav-btn", 40, 0, False]); pg.wait_for_timeout(250)
        check("header: lifting the finger well away from the button does nothing", hidden(pg, "nav-menu"))
        pg.evaluate(TOUCH, ["#nav-btn", 0, 0, True]); pg.wait_for_timeout(250)
        check("header: a cancelled touch (it turned into a scroll) does nothing", hidden(pg, "nav-menu"))
        # ---- scroll-up bar
        to_bar(pg)
        pg.tap("#slim-btn"); pg.wait_for_timeout(300)
        check("bar: ONE real tap on ARCHIVE opens the menu", not hidden(pg, "slim-menu"))
        pg.tap("#slim-btn"); pg.wait_for_timeout(300)
        check("bar: a second tap closes it", hidden(pg, "slim-menu"))
        pg.evaluate(TOUCH, ["#slim-btn", 0, 0, False]); pg.wait_for_timeout(300)
        check("bar: a tap whose click never arrives still opens the menu on the first tap", not hidden(pg, "slim-menu"))
        pg.evaluate(TOUCH, ["#slim-btn", 0, 0, False]); pg.wait_for_timeout(300)
        check("bar: and the next tap closes it", hidden(pg, "slim-menu"))
        pg.tap("#slim-theme"); pg.wait_for_timeout(250)
        check("bar: LIGHT/DARK still works on one tap", pg.evaluate("document.documentElement.dataset.theme") == "light")
        pg.tap("#slim-btn"); pg.wait_for_timeout(300); pg.tap('#slim-menu a[data-view="calendar"]'); pg.wait_for_url("**/archive/#calendar", timeout=5000)
        check("bar: tapping GRID / CALENDAR in the opened menu still works", pg.url.endswith("/archive/#calendar"))
        ctx.close()
        # ---- mouse and keyboard
        ctx = br.new_context(viewport={"width": 1280, "height": 800}); pg = ctx.new_page(); pg.goto(B + "/"); pg.wait_for_load_state("networkidle")
        pg.click("#nav-btn"); pg.wait_for_timeout(250)
        check("mouse: a click opens the menu", not hidden(pg, "nav-menu"))
        pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
        pg.focus("#nav-btn"); pg.keyboard.press("Enter"); pg.wait_for_timeout(250)
        check("keyboard: Enter on ARCHIVE opens the menu", not hidden(pg, "nav-menu"))
        ctx.close(); br.close()
finally:
    srv.terminate()
print(f"{sum(res)}/{len(res)} passed"); sys.exit(0 if all(res) else 1)
