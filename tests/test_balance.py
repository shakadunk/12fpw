"""Regression test: the text sits balanced inside the scroll-up bar.
Run after `node build.mjs`:  python3 tests/test_balance.py

Over a flat grey, measures the space from the top of the screen to the top of the capital letters and the space from the
bottom of the capitals to where the frosting visibly ends (where its tint has faded to 75%). They should match within 1px,
in both themes and on phone and desktop widths."""
"""Measure how balanced the text is inside the scroll-up bar: space from the top of the screen to the top of the capital
letters, versus space from the bottom of the capitals to where the frosting visibly ends. Everything behind the bar is a
flat grey so the frosting's own edge can be read from pixels."""
import subprocess, time, os, sys, io
from playwright.sync_api import sync_playwright
from PIL import Image

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
port = "3601"
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=root, env={**os.environ, "PORT": port}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = f"http://localhost:{port}"
FLAT = "html,body{background:#7a7a7a!important}.post figure{background:#7a7a7a!important}.post figure img{visibility:hidden!important}.post+.post{border-top-color:#7a7a7a!important}"
SC = 4
out = {}
with sync_playwright() as p:
    br = p.chromium.launch()
    for theme in ("light", "dark"):
        for dev, (w, h, mob) in (("phone", (390, 844, True)), ("desktop", (1000, 800, False))):
            ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=SC, is_mobile=mob, has_touch=mob)
            ctx.add_init_script("try{history.scrollRestoration='manual'}catch(e){}")
            pg = ctx.new_page(); pg.add_init_script(f"try{{localStorage.setItem('theme','{theme}')}}catch(e){{}}")
            pg.goto(B + "/archive/#scroll"); pg.reload(); pg.wait_for_load_state("networkidle")
            pg.add_style_tag(content=FLAT)
            for _ in range(4):
                pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(200)
            pg.evaluate("window.scrollTo(0, 3000)"); pg.wait_for_timeout(250); pg.evaluate("window.scrollBy(0,-120)"); pg.wait_for_timeout(700)
            geo = pg.evaluate("""() => { const a=document.getElementById('slim-btn').getBoundingClientRect(), n=document.querySelector('#slim-name .'+(innerWidth<720?'short':'long')).getBoundingClientRect(), s=document.getElementById('slimbar').getBoundingClientRect(); return {aL:a.left,aR:a.right,nR:n.right,aTop:a.top,aBot:a.bottom,barH:s.height} }""")
            png = pg.screenshot(clip={"x": 0, "y": 0, "width": w, "height": 120})
            im = Image.open(io.BytesIO(png)).convert("L")
            base = 0x7a
            # glyph rows: look at the ARCHIVE word's columns (exclude the underline-free state: the bar is not hovered)
            x0, x1 = int(geo["aL"] * SC) + 2, int(geo["aR"] * SC) - 2
            xc = int(((geo["nR"] + geo["aL"]) / 2) * SC)
            def row_has_text(y):
                bg = im.getpixel((xc, y))
                for x in range(x0, x1):
                    v = im.getpixel((x, y))
                    if (theme == "light" and bg - v > 45) or (theme == "dark" and v - bg > 45): return True
                return False
            rows = [y for y in range(0, im.height) if row_has_text(y)]
            gtop, gbot = min(rows), max(rows)
            # frosting profile in a text-free column (between the name and ARCHIVE)
            col = [abs(im.getpixel((xc, y)) - base) for y in range(0, im.height)]
            plateau = sum(col[4:12]) / 8
            edge = next(y for y in range(12, len(col)) if col[y] < 0.75 * plateau)
            half = next(y for y in range(12, len(col)) if col[y] < 0.5 * plateau)
            out[f"{theme}/{dev}"] = dict(above=gtop / SC, glyph=(gbot - gtop + 1) / SC, below75=(edge - gbot) / SC, below50=(half - gbot) / SC, barH=geo["barH"], plateau=round(plateau, 1))
            ctx.close()
    br.close()
srv.terminate()
for k, v in out.items():
    print(f"{k:14s} space above caps {v['above']:5.1f}px | caps {v['glyph']:4.1f}px | space below caps to visible edge (75% / 50%): {v['below75']:5.1f} / {v['below50']:5.1f}px | bar {v['barH']:.1f}px | tint {v['plateau']}")

bad = []
for k, v in out.items():
    ok = abs(v["below75"] - v["above"]) <= 1.0
    print(("PASS " if ok else "FAIL ") + f"{k}: {v['above']:.1f}px above the letters, {v['below75']:.1f}px below")
    if not ok: bad.append(k)
print(f"{len(out) - len(bad)}/{len(out)} passed")
sys.exit(1 if bad else 0)
