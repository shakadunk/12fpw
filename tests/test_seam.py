"""Regression test: no seam between the scroll-up bar and the ARCHIVE menu.
Run after `node build.mjs`:  python3 tests/test_seam.py

With everything behind the bar made a flat grey, the frosting's brightness down the menu column should be a flat
plateau (the band's tint) that fades out at the bottom. Two overlapping layers would show up as a ridge: a denser
stripe where the bar and the menu patch overlap. The test fails if any ridge is taller than 2 grey levels."""
"""Measure the seam between the scroll-up bar and the ARCHIVE menu patch.
Everything behind the bar is made a flat mid-grey, so any change in brightness down the menu column is the frosting itself.
Reports the brightness profile down a column inside the menu patch (to the right of the labels)."""
import subprocess, time, os, sys, io
from playwright.sync_api import sync_playwright
from PIL import Image

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); port = "3466"; label = "seam test"
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=root, env={**os.environ, "PORT": port}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = f"http://localhost:{port}"
FLAT = "html,body{background:#7a7a7a!important}.post figure{background:#7a7a7a!important}.post figure img{visibility:hidden!important}.post+.post{border-top-color:#7a7a7a!important}"
res = {}
with sync_playwright() as p:
    br = p.chromium.launch()
    for theme in ("light", "dark"):
        for dev, (w, h, mob) in (("phone", (390, 844, True)), ("desktop", (900, 800, False))):
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=mob, has_touch=mob)
            ctx.add_init_script("try{history.scrollRestoration='manual'}catch(e){}")
            pg = ctx.new_page(); pg.add_init_script(f"try{{localStorage.setItem('theme','{theme}')}}catch(e){{}}")
            pg.goto(B + "/"); pg.reload(); pg.wait_for_load_state("networkidle")
            pg.add_style_tag(content=FLAT)
            for _ in range(5):
                pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(250)
            pg.evaluate("window.scrollTo(0, 3000)"); pg.wait_for_timeout(250); pg.evaluate("window.scrollBy(0,-120)"); pg.wait_for_timeout(600)
            pg.tap("#slim-btn") if mob else pg.hover("#slim-btn"); pg.wait_for_timeout(700)
            # hide the text so only the frosting is measured
            pg.add_style_tag(content=".slimbar a,.slimbar button{color:transparent!important;text-decoration:none!important}")
            pg.wait_for_timeout(200)
            geo = pg.evaluate("""() => { const m=document.getElementById('slim-menu').getBoundingClientRect(); const s=document.getElementById('slimbar').getBoundingClientRect(); return {mL:m.left, mR:m.right, mTop:m.top, mBot:m.bottom, barBot:s.bottom} }""")
            png = pg.screenshot(clip={"x": 0, "y": 0, "width": w, "height": 330})
            im = Image.open(io.BytesIO(png)).convert("L"); sc = 2
            x = int((geo["mL"] + (geo["mR"] - geo["mL"]) * 0.88) * sc)    # right part of the menu column, clear of the labels
            col = [im.getpixel((x, y)) for y in range(0, im.height)]
            base = 0x7a
            dev_from_base = [c - base for c in col]
            res[f"{theme}/{dev}"] = (dev_from_base, geo, sc)
            ctx.close()
    br.close()
srv.terminate()

def describe(name, d, geo, sc):
    sign = 1 if name.startswith("light") else -1
    mag = [max(0, v * sign) for v in d]
    end = int((geo["mBot"] + 40) * sc)
    seg = mag[:end]
    top = seg[int(2 * sc)]                          # tint at the very top of the bar (the band)
    ridge = max(seg) - top                          # how far the tint rises ABOVE the band's own tint further down (a seam shows as a ridge)
    # non-increasing check with a 1-level tolerance
    bumps = sum(1 for i in range(1, len(seg)) if seg[i] - min(seg[:i]) > 1.5 and seg[i] > top + 1.5)
    return top, ridge, mag

print(f"==== {label} ====")
for name, (d, geo, sc) in res.items():
    top, ridge, mag = describe(name, d, geo, sc)
    # sample the profile every ~6 css px for display
    samp = [mag[min(len(mag)-1, int(y * sc))] for y in range(0, int(geo['mBot'] + 40), 6)]
    print(f"{name:14s} band tint {top:3d}  ridge above the band's tint {ridge:4.1f} grey levels   profile: {' '.join(f'{int(v):2d}' for v in samp)}")

bad = []
for name, (d, geo, sc) in res.items():
    top, ridge, mag = describe(name, d, geo, sc)
    ok = ridge <= 2.0 and top >= 20            # a visible tint, and no ridge
    print(("PASS " if ok else "FAIL ") + f"{name}: band tint {top}, ridge {ridge:.1f}")
    if not ok: bad.append(name)
print(f"{len(res) - len(bad)}/{len(res)} passed")
sys.exit(1 if bad else 0)
