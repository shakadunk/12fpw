"""Header ARCHIVE menu at the top of the page: the same frosted rounded shape as the scroll-up bar's menu (41px left of the labels,
26px right, 40px below the menu, 26% tint, 14px blur), flush with the top of the screen, open at the screen's right edge (no sideways
scrolling). Run after building:  python3 tests/test_headermenu.py"""
import subprocess, time, os, sys
from playwright.sync_api import sync_playwright
proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=proj, env={**os.environ, "PORT": "3277"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3277"
res = []
def check(name, cond):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name)
GEO = """() => {
  const nav = document.querySelector('.site-header .nav-archive'), btn = nav.querySelector('.nav-archive-btn'), menu = nav.querySelector('.nav-menu');
  const cs = getComputedStyle(nav, '::before'), nr = nav.getBoundingClientRect(), mr = menu.getBoundingClientRect();
  const links = [...menu.querySelectorAll('a')].map(a => { const r = document.createRange(); r.selectNodeContents(a); return r.getBoundingClientRect(); });
  const L = nr.left + parseFloat(cs.left), T = nr.top + parseFloat(cs.top);
  return { L, T, R: L + parseFloat(cs.width), Bt: T + parseFloat(cs.height), nr: {l: nr.left, r: nr.right, t: nr.top}, mr: {l: mr.left, r: mr.right, b: mr.bottom},
           textL: Math.min(...links.map(r => r.left)), textR: Math.max(...links.map(r => r.right)),
           blur: cs.backdropFilter || cs.webkitBackdropFilter, tint: cs.backgroundColor, mask: cs.maskImage || cs.webkitMaskImage, content: cs.content,
           vw: document.documentElement.clientWidth, over: document.documentElement.scrollWidth - innerWidth };
}"""
try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        for name, (w, h, mob) in (("phone 390", (390, 844, True)), ("tablet 900", (900, 800, False)), ("desktop 1280", (1280, 800, False))):
            for theme in ("dark", "light"):
                ctx = br.new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob)
                ctx.add_init_script("try{history.scrollRestoration='manual'}catch(e){}")
                pg = ctx.new_page(); pg.add_init_script(f"try{{localStorage.setItem('theme','{theme}')}}catch(e){{}}")
                pg.goto(B + "/"); pg.reload(); pg.wait_for_load_state("networkidle")
                pg.tap("#nav-btn") if mob else pg.click("#nav-btn")
                pg.wait_for_timeout(500)
                g = pg.evaluate(GEO); tag = f"{name} {theme}: "
                tint = "rgba(0, 0, 0, 0.26)" if theme == "dark" else "rgba(255, 255, 255, 0.26)"
                check(tag + "frosted layer is 14px blur + 26% tint, drawn with a mask image", "blur(14px)" in g["blur"] and g["tint"] == tint and "url(" in g["mask"])
                check(tag + "about 41px of room left of the labels (or more)", g["textL"] - g["L"] >= 40)
                right_room = g["R"] - max(g["textR"], g["nr"]["r"])
                check(tag + "about 26px of room right of the labels, or runs to the screen edge", right_room >= 25 or abs(g["R"] - g["vw"]) <= 1)
                check(tag + "40px below the last item (+/-2)", abs(g["Bt"] - g["mr"]["b"] - 40) <= 2)
                check(tag + "flush with the top of the screen (no hard line above ARCHIVE)", abs(g["T"]) <= 1 or g["T"] <= g["nr"]["t"] - 29)
                check(tag + "no sideways scrolling while the menu is open", g["over"] <= 0)
                ctx.close()
        br.close()
finally:
    srv.terminate()
print(f"{sum(res)}/{len(res)} passed"); sys.exit(0 if all(res) else 1)
