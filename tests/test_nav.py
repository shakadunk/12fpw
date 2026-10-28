import subprocess, time, os, sys, datetime
from playwright.sync_api import sync_playwright

proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
out = "/tmp/12fpw-test-shots"; os.makedirs(out, exist_ok=True)
srv = subprocess.Popen(["node", "scripts/serve.mjs"], cwd=proj, env={**os.environ, "PORT": "3266"}, stdout=subprocess.DEVNULL)
time.sleep(1)
B = "http://localhost:3266"
# how many posts exist and which are newest / oldest, so the checks keep working as real posts replace the demo ones
slugs = sorted(d for d in os.listdir(os.path.join(proj, "issues")) if d[:4].isdigit())
N = len(slugs)
def wk(slug): y, w = slug.split("-w"); return int(y), int(w)
newest_wk, oldest_wk = wk(slugs[-1]), wk(slugs[0])
def month_of(yw): return datetime.date.fromisocalendar(yw[0], yw[1], 4).strftime("%B %Y")
results = []
def check(name, cond):
    results.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name)

def labels(page, sel):
    return page.evaluate("""(sel) => [...document.querySelector(sel).querySelectorAll('.nav-archive-btn, #slim-top, .theme-toggle')].map(el => {
        const after = getComputedStyle(el, '::after').content;
        return (el.textContent.trim() || after.replace(/^"|"$/g, '')).toUpperCase(); })""", sel)
def bar_visible(page):
    return page.evaluate("(()=>{const s=document.getElementById('slimbar');const r=s.getBoundingClientRect();return getComputedStyle(s).visibility==='visible'&&r.bottom>0&&r.top>=-1})()")
def up(page, y, back=150):
    page.evaluate(f"window.scrollTo(0,{y})"); page.wait_for_timeout(250); page.evaluate(f"window.scrollBy(0,-{back})"); page.wait_for_timeout(300)
def all_posts_loaded(page):
    for _ in range(30):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)"); page.wait_for_timeout(300)
        if page.locator("#scroll-list .post").count() == N: break

try:
    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 1180, "height": 900})   # below 1200px: the classic ARCHIVE, TOP, LIGHT layout (the 1200px+ layout is tested in test_wide.py)
        ctx.add_init_script("try{history.scrollRestoration='manual'}catch(e){}")   # reloads must start at the top, or the bar tests race the browser's scroll restoration
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        bad = []
        page.on("response", lambda r: bad.append(r.url) if r.status >= 400 else None)

        # ================= HOME = the feed: most recent post first, then older posts (infinite scroll) =================
        page.goto(B + "/"); page.wait_for_load_state("networkidle")
        check("home: starts with the most recent post, which carries the one h1", f"Week {newest_wk[1]}" in page.inner_text("h1") and str(newest_wk[0]) in page.inner_text("h1") and page.locator("h1").count() == 1)
        check("home: the first post has its 12 images and its text", page.locator("#scroll-list .post").first.locator("figure img").count() == 12 and len(page.locator("#scroll-list .post").first.locator(".text").inner_text()) > 40)
        check("home: no back button", page.locator(".back").count() == 0)
        check("home: header has ARCHIVE and LIGHT, no SUBSCRIBE", labels(page, ".site-header nav") == ["ARCHIVE", "LIGHT"] and "SUBSCRIBE" not in page.locator(".site-header").text_content().upper())
        check("home: no signup form or email field on the page", page.locator("#subscribe-form").count() == 0 and page.locator("input[type=email]").count() == 0)
        check("home: footer is just the date", page.locator("footer a").count() == 0 and page.locator("#today").count() == 1)
        check("home: no pager (the feed replaces it)", page.locator(".pager").count() == 0)
        check("home: only the first posts are on the page at load, the rest load as you scroll", page.locator("#scroll-list .post").count() < N or N <= 2)
        all_posts_loaded(page)
        check("home: infinite scroll loads every post, newest to oldest", page.locator("#scroll-list .post").count() == N and f"Week {newest_wk[1]}" in page.locator("#scroll-list .post .week").first.inner_text() and f"Week {oldest_wk[1]}" in page.locator("#scroll-list .post .week").last.inner_text())
        check("home: thin rule between posts", page.evaluate("getComputedStyle(document.querySelectorAll('#scroll-list .post')[1]).borderTopWidth") == "1px")
        check("home: later posts use h2, not another h1", page.locator("h1").count() == 1 and page.locator("#scroll-list .post h2.week").count() == N - 1)
        page.evaluate("window.scrollTo(0, 0)")
        check("home: black background", page.evaluate("getComputedStyle(document.documentElement).backgroundColor") == "rgb(0, 0, 0)")

        # ================= text name replaces the logo image =================
        page.goto(B + "/"); page.wait_for_load_state("networkidle")
        hn = page.evaluate("""() => { const a=document.getElementById('site-name'), cs=getComputedStyle(a.querySelector('.long')), nav=document.querySelector('.site-header nav .nav-archive-btn');
          return {tag:a.tagName, href:a.getAttribute('href'), label:a.getAttribute('aria-label'), txt:a.querySelector('.long').textContent.trim(), up:cs.textTransform, size:cs.fontSize, ls:cs.letterSpacing, navSize:getComputedStyle(nav).fontSize, navLs:getComputedStyle(nav).letterSpacing,
                  color:getComputedStyle(a).color, navColor:getComputedStyle(nav).color, und:getComputedStyle(a).textDecorationLine, imgs:document.querySelectorAll('.site-header img').length, left:a.getBoundingClientRect().left,
                  nameBase:a.getBoundingClientRect().bottom, navBase:nav.getBoundingClientRect().bottom, short:a.querySelector('.short').getBoundingClientRect().width} }""")
        check("header: the logo image is gone, the name is plain text", hn["imgs"] == 0 and hn["txt"] == "12 Frames Per Week" and hn["up"] == "uppercase")
        check("header: the name is a link to the home page", hn["tag"] == "A" and hn["href"] == "/" and "home" in hn["label"].lower() and hn["und"] == "none")
        check("header: the name matches the nav (same size, spacing and colour)", hn["size"] == hn["navSize"] == "12px" and hn["ls"] == hn["navLs"] and hn["color"] == hn["navColor"])
        check("header: the name sits on the same line as ARCHIVE / LIGHT", abs(hn["nameBase"] - hn["navBase"]) < 2)
        check("header: desktop shows the full name, not 12FPW", hn["short"] == 0)
        check("header: no logo image is shipped in the built site", not os.path.exists(os.path.join(proj, "dist", "logo.png")))
        page.goto(B + "/archive/#grid"); page.reload(); page.wait_for_load_state("networkidle")
        check("header (archive): same text name, linking home", page.locator(".site-header img").count() == 0 and page.get_attribute("#site-name", "href") == "/")
        page.goto(B + "/2023/week-8/"); page.wait_for_load_state("networkidle")
        check("header (older week): same text name, linking home", page.locator(".site-header img").count() == 0 and page.get_attribute("#site-name", "href") == "/")
        page.click("#site-name"); page.wait_for_load_state("networkidle")
        check("header: clicking the name goes to the home page (latest post)", page.url.rstrip("/") == B and f"Week {newest_wk[1]}" in page.inner_text("h1"))
        page.goto(B + "/nope/"); check("404 page: header has the text name too", page.locator("#site-name").count() == 1 and page.locator(".site-header img").count() == 0); errors.clear()
        page.goto(B + "/"); page.wait_for_load_state("networkidle")

        # ================= header ARCHIVE dropdown (on a post page) =================
        page.click("#nav-btn")
        items = [t.strip().lower() for t in page.locator("#nav-menu a").all_inner_texts()]
        check("header: ARCHIVE opens GRID / CALENDAR (the feed is the home page)", items == ["grid", "calendar"] and page.is_visible("#nav-menu"))
        check("header: menu sits under the ARCHIVE label", abs(page.evaluate("document.getElementById('nav-menu').getBoundingClientRect().left - document.getElementById('nav-btn').getBoundingClientRect().left")) < 2)
        check("header: menu has no solid panel", page.evaluate("getComputedStyle(document.getElementById('nav-menu')).backgroundColor") == "rgba(0, 0, 0, 0)")
        check("header: frosted patch is behind the open menu", page.evaluate("(()=>{const c=getComputedStyle(document.querySelector('.site-header .nav-archive'),'::before');return c.content!=='none'&&parseFloat(c.height)>100&&(c.backdropFilter||c.webkitBackdropFilter).includes('blur')})()"))
        page.screenshot(path=f"{out}/nav-header-open.png", clip={"x": 0, "y": 0, "width": 1440, "height": 420})
        page.keyboard.press("Escape")
        check("header: Esc closes the menu", not page.is_visible("#nav-menu"))
        page.click("#nav-btn"); page.mouse.click(700, 500); page.wait_for_timeout(150)
        check("header: clicking elsewhere closes it", not page.is_visible("#nav-menu"))
        page.click("#nav-btn"); page.click('#nav-menu a[data-view="grid"]'); page.wait_for_load_state("networkidle")
        check("header (from the home page): picking GRID opens the archive in grid view", page.url.endswith("/archive/#grid") and page.is_visible(".view-grid") and page.locator(".view-scroll").count() == 0)

        # ================= ARCHIVE page =================
        check("archive: no title row and no inline view buttons", page.locator(".archive-bar").count() == 0 and page.locator(".view-toggle").count() == 0)
        check("archive: header ARCHIVE is marked as the current page", page.get_attribute("#nav-btn", "aria-current") == "page")
        check("archive: grid has one thumbnail per post, with week labels", page.locator(".view-grid .grid li").count() == N and all(t.startswith("Week") for t in page.locator(".view-grid .tag").all_inner_texts()))
        page.click("#nav-btn")
        check("archive: current view is full white in the menu, others dimmed", page.evaluate("(()=>{const a=getComputedStyle(document.querySelector('#nav-menu [aria-current=true]')).opacity;const b=getComputedStyle(document.querySelector('#nav-menu a:not([aria-current])')).opacity;return a==='1'&&parseFloat(b)<0.8})()"))
        check("archive: current view marked is GRID", page.get_attribute('#nav-menu [aria-current="true"]', "data-view") == "grid")
        page.click('#nav-menu a[data-view="calendar"]'); page.wait_for_timeout(300)
        heads = [h.title() for h in page.locator(".view-calendar .month h2").all_inner_texts()]
        check("archive: switching to CALENDAR happens in place (months, dividers)", page.is_visible(".view-calendar") and heads[0] == month_of(newest_wk) and heads[-1] == month_of(oldest_wk) and page.url.endswith("#calendar"))
        check("archive: menu closed and page at the top after switching", not page.is_visible("#nav-menu") and page.evaluate("window.pageYOffset") == 0)
        page.click("#nav-btn"); page.click('#nav-menu a[data-view="grid"]'); page.wait_for_timeout(400)
        check("archive: switching back to GRID works", page.is_visible(".view-grid") and not page.is_visible(".view-calendar"))
        check("archive: the view is remembered across a reload", (page.reload() or True) and page.is_visible(".view-grid"))
        check("archive: there is no SCROLL view any more", page.locator(".view-scroll").count() == 0 and page.locator('[data-view="scroll"]').count() == 0)
        page.goto(B + "/archive/#scroll"); page.reload(); page.wait_for_load_state("networkidle")
        check("archive: an old #scroll link just shows the grid", page.is_visible(".view-grid"))
        page.goto(B + "/archive/#calendar"); page.reload()
        check("archive: #calendar deep link wins over the saved view", page.is_visible(".view-calendar"))

        # ================= scroll-up bar =================
        page.goto(B + "/archive/#calendar"); page.reload(); page.wait_for_load_state("networkidle")
        check("bar: hidden at the top", not bar_visible(page))
        page.evaluate("window.scrollTo(0,1200)"); page.wait_for_timeout(250)
        check("bar: hidden while scrolling down", not bar_visible(page))
        page.evaluate("window.scrollBy(0,-150)"); page.wait_for_timeout(300)
        check("bar: appears on scroll up", bar_visible(page))
        check("bar: contains ARCHIVE, TOP, LIGHT in that order", labels(page, "#slim-grp") == ["ARCHIVE", "TOP", "LIGHT"])
        pos = page.evaluate("(()=>{const r=id=>document.getElementById(id).getBoundingClientRect();const a=r('slim-btn'),t=r('slim-top'),l=r('slim-theme');return {a:a.left,t:t.left,l:l.left,lr:l.right,w:innerWidth}})()")
        check("bar: right-aligned, LIGHT in the far-right corner like the header", pos["a"] < pos["t"] < pos["l"] and pos["lr"] > pos["w"] - 60 and pos["a"] > pos["w"] - 300)
        hdr_light = page.evaluate("document.getElementById('theme-toggle').getBoundingClientRect().right")
        check("bar: LIGHT lines up with the header's LIGHT", abs(pos["lr"] - hdr_light) < 3)
        check("bar: ONE frosted band (blur + 30% tint) across the whole width", page.evaluate("(()=>{const s=document.getElementById('slimbar');const c=getComputedStyle(s,'::before');return (c.backdropFilter||c.webkitBackdropFilter).includes('blur')&&c.backgroundColor==='rgba(0, 0, 0, 0.3)'&&Math.abs(parseFloat(c.width)-innerWidth)<2&&s.getBoundingClientRect().width>=innerWidth-1})()"))
        check("bar: no separate patches behind the name or the buttons", page.evaluate("['slim-name','slim-grp'].every(id=>{const c=getComputedStyle(document.getElementById(id),'::before').content;return c==='none'||c==='normal'})"))
        check("bar: band is feathered along its bottom edge (mask)", page.evaluate("(getComputedStyle(document.getElementById('slimbar'),'::before').maskImage||getComputedStyle(document.getElementById('slimbar'),'::before').webkitMaskImage).includes('linear-gradient')"))
        check("bar: band plus feather is short (under 50px)", page.evaluate("(()=>{const s=document.getElementById('slimbar');const c=getComputedStyle(s,'::before');return s.getBoundingClientRect().height+(-parseFloat(c.bottom))<50})()"))
        nm = page.evaluate("(()=>{const n=document.querySelector('#slim-name .long');const r=n.getBoundingClientRect();return {txt:n.textContent.trim().toLowerCase(), up:getComputedStyle(n).textTransform, left:r.left, vis:r.width>0, link:document.querySelectorAll('#slim-name a').length, short:document.querySelector('#slim-name .short').getBoundingClientRect().width, size:getComputedStyle(n).fontSize, col:getComputedStyle(n).color===getComputedStyle(document.getElementById('slim-top')).color}})()")
        nmlink = page.evaluate("(()=>{const a=document.getElementById('slim-name');return {tag:a.tagName, href:a.getAttribute('href'), und:getComputedStyle(a).textDecorationLine, label:a.getAttribute('aria-label')}})()")
        check("bar: the name is a link home, with no underline until hovered", nmlink["tag"] == "A" and nmlink["href"] == "/" and nmlink["und"] == "none" and "home" in nmlink["label"].lower())
        check("bar: left side reads 12 FRAMES PER WEEK in plain all-caps text", nm["txt"] == "12 frames per week" and nm["up"] == "uppercase" and nm["vis"])
        check("bar: the name is on the left, same size and colour as the buttons", nm["left"] < 60 and nm["size"] == "12px" and nm["col"])
        check("bar: desktop shows the long name, not 12FPW", nm["short"] == 0)
        page.screenshot(path=f"{out}/nav-bar-closed.png", clip={"x": 0, "y": 0, "width": 1440, "height": 200})
        page.click("#slim-btn")
        check("bar: ARCHIVE opens GRID / CALENDAR under it", [t.strip().lower() for t in page.locator("#slim-menu a").all_inner_texts()] == ["grid", "calendar"] and page.is_visible("#slim-menu"))
        page.wait_for_timeout(300)
        cov = page.evaluate("""() => { const g=document.getElementById('slimbar'); const c=getComputedStyle(g,'::before'); const m=document.getElementById('slim-menu'); const mr=m.getBoundingClientRect(); const gr=g.getBoundingClientRect();
          const mi=(c.maskImage||c.webkitMaskImage||''); const ms=(c.maskSize||c.webkitMaskSize||''); const mc=(c.maskComposite||c.webkitMaskComposite||'');
          return {open:g.classList.contains('menu-open'), layerBottom: gr.bottom-parseFloat(c.bottom), menuBottom: mr.bottom, bandH: gr.height, blur:(c.backdropFilter||c.webkitBackdropFilter), tint:c.backgroundColor, layers:(mi.match(/linear-gradient/g)||[]).length, hasImage: mi.includes('url('), mask:mc, size:ms,
                  afterContent:getComputedStyle(m,'::after').content, afterBlur:(getComputedStyle(m,'::after').backdropFilter||getComputedStyle(m,'::after').webkitBackdropFilter||'none'),
                  pl:parseFloat(g.style.getPropertyValue('--patch-l')), pw:parseFloat(g.style.getPropertyValue('--patch-w')), innerW:innerWidth, menuL:mr.left, menuR:mr.right} }""")
        check("bar: the band keeps its single depth when the menu opens", cov["bandH"] < 42)
        check("bar: ONE frosted layer covers the bar and extends down past the menu (no second layer)", cov["open"] and cov["layerBottom"] >= cov["menuBottom"] + 15 and cov["afterContent"] in ("none", "normal"))
        check("bar: that layer is the band's own blur and tint (30%), masked as band + one drawn shape (union)", "blur(14px)" in cov["blur"] and cov["tint"] == "rgba(0, 0, 0, 0.3)" and cov["layers"] == 1 and cov["hasImage"] and "add" in cov["mask"] and "intersect" not in cov["mask"])
        check("bar: the menu column is what extends (not the whole width)", cov["pw"] < 260 and cov["pl"] > cov["innerW"] / 2 - 100 and cov["pl"] + cov["pw"] >= cov["menuR"])
        check("bar: about 41px of room to the left of the labels, 26px right of the menu, 30px below", abs(cov["menuL"] - cov["pl"] - 41) <= 1.5 and abs((cov["pl"] + cov["pw"]) - cov["menuR"] - 26) <= 1.5 and abs(cov["layerBottom"] - cov["menuBottom"] - 30) <= 2)
        shape = page.evaluate("""async () => { const g=document.getElementById('slimbar'); const m=g.style.getPropertyValue('--menu-mask'); const url=m.slice(m.indexOf('"')+1, m.lastIndexOf('"'));
          const img=new Image(); await new Promise((res,rej)=>{img.onload=res; img.onerror=rej; img.src=url;}); const W=img.naturalWidth, H=img.naturalHeight; const cv=document.createElement('canvas'); cv.width=W; cv.height=H; const x=cv.getContext('2d'); x.drawImage(img,0,0); const d=x.getImageData(0,0,W,H).data; const A=(px,py)=>d[(py*W+px)*4+3]; const S=2;
          let maxStep=0; for (const row of [Math.round(H*0.5), H-40*S, H-24*S, H-8*S]) for (let px=1; px<W; px++) maxStep=Math.max(maxStep, Math.abs(A(px,row)-A(px-1,row)));
          for (const col of [Math.round(W*0.5), 40*S, W-40*S, 14*S]) for (let py=1; py<H; py++) maxStep=Math.max(maxStep, Math.abs(A(col,py)-A(col,py-1)));
          return {W,H,S, cornerBL:A(4*S, H-1-4*S), cornerBR:A(W-1-4*S, H-1-4*S), edgeL:A(4*S, H-70*S), edgeR:A(W-1-4*S, H-70*S), centre:A(Math.round(W/2), H-30*S), midBottom:A(Math.round(W/2), H-4*S), top:A(Math.round(W/2), 2), maxStep}; }""")
        check("bar: the shape's bottom corners are ROUND (the outer corner points are fully clear, the straight edges are not)", shape["cornerBL"] == 0 and shape["cornerBR"] == 0 and 20 < shape["edgeL"] < 90 and 20 < shape["edgeR"] < 90 and shape["centre"] == 255 and shape["top"] == 255)
        check("bar: the shape is symmetrical left to right", abs(shape["edgeL"] - shape["edgeR"]) <= 3 and abs(shape["cornerBL"] - shape["cornerBR"]) <= 3)
        check("bar: the shape is one smooth image with no seams (alpha never jumps between neighbouring pixels)", shape["maxStep"] <= 12)
        check("bar: menu text is fully on screen", page.evaluate("(()=>{const r=document.getElementById('slim-menu').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})()"))
        page.screenshot(path=f"{out}/nav-bar-open.png", clip={"x": 0, "y": 0, "width": 1440, "height": 400})
        page.keyboard.press("Escape")
        check("bar: Esc closes the menu and the layer shrinks back to the band", not page.is_visible("#slim-menu") and not page.evaluate("document.getElementById('slimbar').classList.contains('menu-open')"))
        page.click("#slim-btn"); page.mouse.move(5, 500); page.wait_for_timeout(500)
        page.evaluate("window.scrollBy(0,300)"); page.wait_for_timeout(400)
        check("bar: scrolling down does not hide it at once (menu still open too)", bar_visible(page) and page.is_visible("#slim-menu"))
        page.wait_for_timeout(1100)
        check("bar: about a second later it hides, and the menu closes with it", not page.is_visible("#slim-menu") and not bar_visible(page))
        page.evaluate("window.scrollBy(0,-150)"); page.wait_for_timeout(300)
        page.click("#slim-btn"); page.click('#slim-menu a[data-view="grid"]'); page.wait_for_timeout(300)
        check("bar: picking GRID switches the view and goes to the top", page.is_visible(".view-grid") and page.evaluate("window.pageYOffset") == 0 and page.url.endswith("#grid"))

        # ---- hide delay ----
        page.goto(B + "/archive/#calendar"); page.reload(); page.wait_for_load_state("networkidle"); page.mouse.move(5, 500)
        up(page, 1500)
        page.evaluate("window.scrollBy(0,300)"); page.wait_for_timeout(450)
        check("delay: the bar is still up 0.45s after scrolling down", bar_visible(page))
        page.wait_for_timeout(450)
        check("delay: ...and 0.9s after", bar_visible(page))
        page.wait_for_timeout(450)
        check("delay: it is gone by about 1.4s", not bar_visible(page))
        # scrolling back up during the delay cancels it
        up(page, 1500)
        page.evaluate("window.scrollBy(0,300)"); page.wait_for_timeout(500)
        page.evaluate("window.scrollBy(0,-200)"); page.wait_for_timeout(2000)
        check("delay: scrolling back up during the delay cancels it (bar stays well past a second)", bar_visible(page))
        # the countdown restarts from the next scroll down
        page.evaluate("window.scrollBy(0,300)"); page.wait_for_timeout(600)
        check("delay: a fresh scroll down starts a fresh countdown (not the old one)", bar_visible(page))
        page.wait_for_timeout(1000)
        check("delay: ...and it hides after that", not bar_visible(page))
        # scrolling continuously down does not extend the delay forever
        up(page, 1500)
        for _ in range(6):
            page.evaluate("window.scrollBy(0,120)"); page.wait_for_timeout(250)
        check("delay: continuous scrolling down still hides it (the delay is not pushed back each time)", not bar_visible(page))
        # reaching the top is immediate
        up(page, 1500)
        page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(450)
        check("delay: reaching the top of the page hides it straight away", not bar_visible(page))
        # mouse resting on the bar keeps it
        up(page, 1500)
        bb = page.locator("#slim-theme").bounding_box(); page.mouse.move(bb["x"] + 5, bb["y"] + 5); page.wait_for_timeout(150)
        page.evaluate("window.scrollBy(0,300)"); page.wait_for_timeout(1800)
        check("delay (mouse): the bar stays while the mouse rests on it, well past a second", bar_visible(page))
        page.mouse.move(700, 600); page.wait_for_timeout(600)
        check("delay (mouse): after the mouse leaves, it waits out a fresh countdown", bar_visible(page))
        page.wait_for_timeout(1000)
        check("delay (mouse): ...then it hides", not bar_visible(page))
        # mouse on the bar but the bar was never on its way out: nothing hides it
        up(page, 1500)
        page.mouse.move(bb["x"] + 5, bb["y"] + 5); page.wait_for_timeout(150); page.mouse.move(700, 600); page.wait_for_timeout(1800)
        check("delay (mouse): leaving the bar by itself does not hide it if you never scrolled down", bar_visible(page))
        # a quick click on ARCHIVE is a click, not a hover
        up(page, 1500)
        ab = page.locator("#slim-btn").bounding_box(); page.mouse.move(ab["x"] + 5, ab["y"] + 5); page.mouse.down(); page.mouse.up(); page.wait_for_timeout(450)
        page.mouse.move(700, 650); page.wait_for_timeout(700)
        check("delay: a very quick click on ARCHIVE pins the menu (it does not close when the mouse leaves)", page.is_visible("#slim-menu"))
        page.mouse.click(700, 650); page.wait_for_timeout(200)

        # TOP + LIGHT from the bar
        page.goto(B + "/"); page.reload(); page.wait_for_load_state("networkidle"); all_posts_loaded(page)
        page.evaluate("window.scrollTo(0,60000)"); page.wait_for_timeout(250); page.evaluate("window.scrollBy(0,-200)"); page.wait_for_timeout(300)
        start = page.evaluate("window.pageYOffset")
        page.evaluate("""() => { window.__s=[]; const t0=performance.now(); (function s(){ window.__s.push([Math.round(performance.now()-t0), window.pageYOffset]); if (window.pageYOffset>0 || performance.now()-t0<150) requestAnimationFrame(s); })(); }""")
        page.click("#slim-top"); page.wait_for_timeout(2200)
        s = page.evaluate("window.__s"); ys = [y for _, y in s]
        check("TOP: animated glide through intermediate positions", len([1 for _, y in s if 0 < y < start]) > 15 and all(ys[i+1] <= ys[i] for i in range(len(ys)-1)))
        dur = max(t for t, y in s if y > 0)
        check("TOP: long climb takes about 1.4s", 1100 <= dur <= 1800)
        check("TOP: arrives at the top of the feed, bar hides", page.evaluate("window.pageYOffset") == 0 and page.locator("#scroll-list").count() == 1 and not bar_visible(page))
        page.evaluate("window.scrollTo(0,60000)"); page.wait_for_timeout(250); page.evaluate("window.scrollBy(0,-200)"); page.wait_for_timeout(300)
        page.click("#slim-top"); page.wait_for_timeout(350); page.mouse.move(700, 400); page.mouse.wheel(0, 120); page.wait_for_timeout(120)
        at = page.evaluate("window.pageYOffset"); page.wait_for_timeout(800)
        check("TOP: scrolling mid-flight stops the glide", at > 1000 and abs(page.evaluate("window.pageYOffset") - at) < 400)
        up(page, 3000)
        page.click("#slim-theme"); page.wait_for_timeout(200)
        check("LIGHT in the bar switches the theme (and the label)", page.evaluate("document.documentElement.dataset.theme") == "light" and page.evaluate("getComputedStyle(document.getElementById('slim-theme'),'::after').content") == '"Dark"')
        check("light theme: bar patch tint is white", page.evaluate("getComputedStyle(document.getElementById('slimbar'),'::before').backgroundColor") == "rgba(255, 255, 255, 0.3)")
        check("bar stays on screen after toggling the theme", bar_visible(page))
        page.screenshot(path=f"{out}/nav-bar-light.png", clip={"x": 0, "y": 0, "width": 1440, "height": 200})
        page.click("#slim-btn"); page.wait_for_timeout(300)
        check("light theme: the menu shares the band's single layer (30% white), and the labels are dark", page.evaluate("getComputedStyle(document.getElementById('slimbar'),'::before').backgroundColor") == "rgba(255, 255, 255, 0.3)" and page.evaluate("getComputedStyle(document.getElementById('slim-menu'),'::after').content") in ("none", "normal") and page.evaluate("getComputedStyle(document.querySelector('#slim-menu a')).color") == "rgb(17, 17, 17)")
        page.keyboard.press("Escape")
        page.click("#slim-theme"); page.wait_for_timeout(100)
        page.goto(B + "/2023/week-8/"); page.reload()
        check("the theme choice carries to other pages", page.evaluate("document.documentElement.dataset.theme") == "dark")

        # ================= hover (desktop mouse) =================
        page.goto(B + "/2023/week-8/"); page.wait_for_load_state("networkidle"); page.mouse.move(5, 300)
        page.hover("#nav-btn"); page.wait_for_timeout(300)
        check("hover: resting on ARCHIVE opens the menu", page.is_visible("#nav-menu") and page.get_attribute("#nav-btn", "aria-expanded") == "true")
        page.hover('#nav-menu a[data-view="grid"]'); page.wait_for_timeout(450)
        check("hover: stays open while the pointer travels down onto the menu", page.is_visible("#nav-menu"))
        page.mouse.move(700, 650); page.wait_for_timeout(600)
        check("hover: closes a moment after the pointer leaves", not page.is_visible("#nav-menu") and page.get_attribute("#nav-btn", "aria-expanded") == "false")
        bb = page.locator("#nav-btn").bounding_box(); ly = bb["y"] + bb["height"] / 2
        page.mouse.move(bb["x"] - 25, ly); page.mouse.move(bb["x"] + bb["width"] + 25, ly); page.mouse.move(bb["x"] + bb["width"] + 90, ly); page.wait_for_timeout(500)
        check("hover: a pointer sweeping quickly past ARCHIVE does not open it", not page.is_visible("#nav-menu"))
        page.hover("#nav-btn"); page.wait_for_timeout(300); page.click("#nav-btn"); page.mouse.move(700, 650); page.wait_for_timeout(600)
        check("hover: clicking ARCHIVE while it is open pins it (stays open after leaving)", page.is_visible("#nav-menu"))
        page.mouse.click(700, 650); page.wait_for_timeout(200)
        check("hover: a click elsewhere then closes the pinned menu", not page.is_visible("#nav-menu"))
        page.hover("#nav-btn"); page.wait_for_timeout(300); page.click('#nav-menu a[data-view="calendar"]'); page.wait_for_load_state("networkidle")
        check("hover: choosing a view from the hover menu opens the archive in that view", page.url.endswith("/archive/#calendar") and page.is_visible(".view-calendar"))
        page.hover("#nav-btn"); page.wait_for_timeout(300); page.hover('#nav-menu a[data-view="grid"]'); page.click('#nav-menu a[data-view="grid"]'); page.wait_for_timeout(300)
        check("hover: on the archive page, picking a view switches in place and closes the menu", page.is_visible(".view-grid") and not page.is_visible("#nav-menu"))
        # keyboard still works with no mouse involved
        page.goto(B + "/2023/week-8/"); page.mouse.move(5, 300); page.focus("#nav-btn"); page.keyboard.press("Enter")
        check("keyboard: Enter on ARCHIVE opens the menu", page.is_visible("#nav-menu"))
        page.keyboard.press("Escape")
        check("keyboard: Esc closes it", not page.is_visible("#nav-menu"))
        # hover in the scroll-up bar
        page.goto(B + "/"); page.reload(); page.wait_for_load_state("networkidle"); page.mouse.move(5, 300); up(page, 3000)
        page.hover("#slim-btn"); page.wait_for_timeout(450)
        check("hover (bar): resting on ARCHIVE in the bar opens the menu (the layer extends under it)", page.is_visible("#slim-menu") and page.evaluate("document.getElementById('slimbar').classList.contains('menu-open')"))
        page.mouse.move(700, 700); page.wait_for_timeout(700)
        check("hover (bar): the menu closes and the layer shrinks back after the pointer leaves", not page.is_visible("#slim-menu") and not page.evaluate("document.getElementById('slimbar').classList.contains('menu-open')"))

        # ================= post pages =================
        page.goto(B + "/2023/week-8/"); page.wait_for_load_state("networkidle")
        check("older week: back button to the archive is at the top", page.locator(".back a").count() == 1 and page.get_attribute(".back a", "href") == "/archive/")
        check("older week: back button sits above the Week heading", page.evaluate("document.querySelector('.back').getBoundingClientRect().top < document.querySelector('h1').getBoundingClientRect().top"))
        page.click(".back a"); page.wait_for_load_state("networkidle")
        check("older week: back button returns to the archive", page.url.endswith("/archive/") or "/archive/#" in page.url)
        page.goto(B + "/2023/week-8/"); page.wait_for_load_state("networkidle")
        check("older week: header is logo + ARCHIVE + LIGHT only", labels(page, ".site-header nav") == ["ARCHIVE", "LIGHT"])
        up(page, 1800)
        check("older week: the bar appears on scroll up", bar_visible(page))
        page.click("#slim-btn"); page.click('#slim-menu a[data-view="calendar"]'); page.wait_for_load_state("networkidle")
        check("older week: bar ARCHIVE > CALENDAR opens the archive in calendar view", page.url.endswith("/archive/#calendar") and page.is_visible(".view-calendar"))
        page.goto(B + "/"); page.wait_for_load_state("networkidle"); up(page, 2500)
        check("home: the bar appears on scroll up", bar_visible(page))
        page.click("#slim-top"); page.wait_for_timeout(1500)
        check("home: TOP glides to the top", page.evaluate("window.pageYOffset") == 0)

        # ================= 404 + other =================
        errors.clear(); page.goto(B + "/nope/"); check("404 page has the same header", page.locator("#nav-btn").count() == 1); errors.clear()

        # ================= phone =================
        mctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        m = mctx.new_page()
        m.goto(B + "/"); m.wait_for_load_state("networkidle")
        check("phone: header fits (logo + ARCHIVE + LIGHT), no overflow", m.evaluate("document.documentElement.scrollWidth <= innerWidth") and labels(m, ".site-header nav") == ["ARCHIVE", "LIGHT"])
        m.tap("#nav-btn"); m.wait_for_timeout(300)
        pw = m.evaluate("(()=>{const a=document.getElementById('site-name');const l=a.querySelector('.long').getBoundingClientRect().width, s=a.querySelector('.short'), r=s.getBoundingClientRect();return {long:l, txt:s.textContent.trim(), left:r.left, right:r.right, href:a.getAttribute('href'), navLeft:document.querySelector('.site-header nav').getBoundingClientRect().left}})()")
        check("phone: the header shows 12FPW (long name hidden), still a link home", pw["long"] == 0 and pw["txt"] == "12FPW" and pw["href"] == "/" and pw["left"] < 40 and pw["right"] < pw["navLeft"] - 20)
        check("phone: header dropdown opens and fits", m.is_visible("#nav-menu") and m.evaluate("(()=>{const r=document.getElementById('nav-menu').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})()"))
        m.screenshot(path=f"{out}/nav-phone-header.png", clip={"x": 0, "y": 0, "width": 390, "height": 300})
        m.tap('#nav-menu a[data-view="grid"]'); m.wait_for_url("**/archive/#grid"); m.wait_for_load_state("networkidle")
        check("phone: picking GRID goes to the archive grid", m.url.endswith("/archive/#grid") and m.is_visible(".view-grid"))
        m.goto(B + "/"); m.reload(); m.wait_for_load_state("networkidle")
        m.evaluate("window.scrollTo(0,1600)"); m.wait_for_timeout(250); m.evaluate("window.scrollBy(0,-160)"); m.wait_for_timeout(300)
        check("phone: bar appears on scroll up with ARCHIVE, TOP, LIGHT", bar_visible(m) and labels(m, "#slim-grp") == ["ARCHIVE", "TOP", "LIGHT"])
        pn = m.evaluate("(()=>{const l=document.querySelector('#slim-name .long').getBoundingClientRect().width, sh=document.querySelector('#slim-name .short'), r=sh.getBoundingClientRect();return {long:l, txt:sh.textContent.trim(), left:r.left, right:r.right, vis:r.width>0, gstart:document.getElementById('slim-grp').getBoundingClientRect().left}})()")
        check("phone: the left side reads 12FPW (the long name is hidden)", pn["long"] == 0 and pn["txt"] == "12FPW" and pn["vis"] and pn["left"] < 40)
        check("phone: 12FPW does not collide with the buttons", pn["right"] < pn["gstart"] - 20)
        m.evaluate("window.scrollBy(0,250)"); m.wait_for_timeout(450)
        check("phone: the bar lingers after scrolling down (still up at 0.45s)", bar_visible(m))
        m.wait_for_timeout(1100)
        check("phone: ...then hides about a second later", not bar_visible(m))
        m.evaluate("window.scrollBy(0,-160)"); m.wait_for_timeout(300)
        check("phone: bar buttons stay on screen", m.evaluate("(()=>{const r=document.getElementById('slim-grp').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})()"))
        m.tap("#slim-btn"); m.wait_for_timeout(300)
        check("phone: bar menu opens and fits", m.is_visible("#slim-menu") and m.evaluate("(()=>{const r=document.getElementById('slim-menu').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<innerHeight})()"))
        m.screenshot(path=f"{out}/nav-phone-bar.png", clip={"x": 0, "y": 0, "width": 390, "height": 300})
        m.tap('#slim-menu a[data-view="calendar"]'); m.wait_for_timeout(400)
        check("phone: picking CALENDAR switches in place", m.is_visible(".view-calendar") and m.evaluate("window.pageYOffset") == 0)
        check("phone: no horizontal overflow on the archive", m.evaluate("document.documentElement.scrollWidth <= innerWidth"))

        # ================= reduced motion =================
        rm = br.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce").new_page()
        rm.goto(B + "/archive/#calendar"); rm.reload(); rm.wait_for_load_state("networkidle")
        up(rm, 1600)
        rm.click("#slim-top"); rm.wait_for_timeout(80)
        check("reduced motion: TOP jumps instantly", rm.evaluate("window.pageYOffset") == 0)

        check("no console errors", not errors)
        check("no 4xx/5xx (excluding favicon and the deliberate 404 page)", not [u for u in bad if "favicon" not in u and "/nope" not in u])
        if errors: print(errors)
        br.close()
finally:
    srv.terminate()
print(f"{sum(ok for _, ok in results)}/{len(results)} passed")
sys.exit(0 if all(ok for _, ok in results) else 1)
