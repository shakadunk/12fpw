// Theme toggle, ARCHIVE dropdown, archive views (Scroll / Grid / Calendar) with infinite scroll,
// scroll-up bar, home-page date, signup form. No dependencies.
(function () {
  var root = document.documentElement;
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  };

  // ----- theme (the header and the scroll-up bar each have a toggle) -----
  var themeBtns = document.querySelectorAll('.theme-toggle');
  function syncTheme() {
    var dark = root.dataset.theme !== 'light';
    themeBtns.forEach(function (b) { b.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme'); });
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#000000' : '#ffffff');
  }
  themeBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
      store.set('theme', root.dataset.theme);
      syncTheme();
    });
  });
  syncTheme();

  // ----- ARCHIVE dropdowns (header + scroll-up bar) -----
  var navs = Array.prototype.slice.call(document.querySelectorAll('.nav-archive'));
  function parts(nav) {
    return { btn: nav.querySelector('.nav-archive-btn'), menu: nav.querySelector('.nav-menu'), host: nav.closest('.slimbar') };
  }
  function closeNav(nav) {
    var p = parts(nav);
    clearTimeout(nav._t); delete nav.dataset.hover;
    p.menu.hidden = true;
    nav.classList.remove('open');
    if (p.host) p.host.classList.remove('menu-open');
    p.btn.setAttribute('aria-expanded', 'false');
  }
  function closeAllNavs() { navs.forEach(closeNav); }
  // Frosted shape around the open menu. Outer edges: 41px left of the labels, 26px right, 40px below the menu (10px more than before:
  // optical room under the last item before the fade), corners 40px, edges fading in over 24px.
  var SHAPE = { left: 41, right: 26, below: 40, corner: 40, fade: 24 };
  function openNav(nav) {
    closeAllNavs();
    var p = parts(nav);
    p.menu.hidden = false;
    var h = p.menu.offsetHeight + 'px';
    nav.style.setProperty('--menu-h', h);
    if (p.host) {
      p.host.style.setProperty('--menu-h', h);
      // Geometry for the single frosted layer behind the bar + menu (see style.css): how far it extends below the band,
      // and the menu column's left edge and width in px.
      var br = p.host.getBoundingClientRect(), mr = p.menu.getBoundingClientRect();
      var BELOW = 12;                         // how far the bar's frosted layer reaches below the bar (keep in sync with style.css)
      var extra = Math.max(0, Math.round((mr.bottom + SHAPE.below) - (br.bottom + BELOW)));
      var pl = Math.round(mr.left - SHAPE.left), pw = Math.round(mr.width + SHAPE.left + SHAPE.right);
      p.host.style.setProperty('--menu-extra', extra + 'px');
      p.host.style.setProperty('--patch-l', pl + 'px');
      p.host.style.setProperty('--patch-w', pw + 'px');
      p.host.style.setProperty('--menu-mask', menuMask(pw, br.height + BELOW + extra, SHAPE.corner, SHAPE.fade, true, false));
      p.host.classList.add('menu-open');
    } else {
      // Header (top of the page): there is no band above, so the shape is one rounded blob around the ARCHIVE label and its
      // menu, with the same spacing. It is flush with the top of the screen when it would reach past it, and open (no fade)
      // at the right edge when it would reach past the screen, so the page never scrolls sideways.
      var nr = nav.getBoundingClientRect(), mr2 = p.menu.getBoundingClientRect(), vw = document.documentElement.clientWidth;
      var L = Math.min(nr.left, mr2.left) - SHAPE.left, R = Math.max(nr.right, mr2.right) + SHAPE.right;
      var T = nr.top - 30, Bt = mr2.bottom + SHAPE.below;
      var openTop = T <= 0, openRight = R >= vw;
      if (openTop) T = 0;
      if (openRight) R = vw;
      var gw = Math.round(R - L), gh = Math.round(Bt - T);
      nav.style.setProperty('--g-l', Math.round(L - nr.left) + 'px');
      nav.style.setProperty('--g-t', Math.round(T - nr.top) + 'px');
      nav.style.setProperty('--g-w', gw + 'px');
      nav.style.setProperty('--g-h', gh + 'px');
      nav.style.setProperty('--g-mask', menuMask(gw, gh, SHAPE.corner, SHAPE.fade, openTop, openRight));
    }
    nav.classList.add('open');
    p.btn.setAttribute('aria-expanded', 'true');
  }
  // Soft rounded shape for the frosted area around the ARCHIVE menu, drawn once per open as one smooth image (so there are
  // no seams): w x h px, rounded corners of radius `c`, edges fading in over `f` px. An edge can be left open (no fade, square
  // corners) where the shape runs into the bar or the edge of the screen. Returned as a CSS url() for use as a mask image.
  function menuMask(w, h, c, f, openTop, openRight) {
    var S = 2, W = Math.max(1, Math.round(w * S)), H = Math.max(1, Math.round(h * S));
    var cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    var ctx = cv.getContext('2d'); if (!ctx) return 'none';
    var img = ctx.createImageData(W, H), d = img.data, INF = 1e9;
    for (var y = 0; y < H; y++) {
      for (var x = 0; x < W; x++) {
        var px = (x + 0.5) / S, py = (y + 0.5) / S;
        var dl = px, dr = openRight ? INF : w - px, dt = openTop ? INF : py, db = h - py;
        var dist = Math.min(dl, dr, dt, db);                                            // distance to the nearest straight edge
        var cx = px < c ? c : (!openRight && px > w - c) ? w - c : null;                 // corner centres (only where both edges are closed)
        var cy = (!openTop && py < c) ? c : py > h - c ? h - c : null;
        if (cx !== null && cy !== null) dist = Math.min(dist, c - Math.hypot(px - cx, py - cy));
        var a = dist <= 0 ? 0 : dist >= f ? 1 : dist / f;
        d[(y * W + x) * 4 + 3] = Math.round(a * 255);
      }
    }
    ctx.putImageData(img, 0, 0);
    return 'url("' + cv.toDataURL('image/png') + '")';
  }

  // Desktop (mouse): the menu opens when the pointer rests on ARCHIVE and closes shortly after it leaves.
  // Clicking ARCHIVE while it is open from hovering "pins" it open (it then closes on Esc or a click elsewhere).
  // Touch and pen never hover-open: they tap, as before.
  navs.forEach(function (nav) {
    var p = parts(nav);
    p.btn.addEventListener('click', function () {
      clearTimeout(nav._t);                                                            // a quick click beats a pending hover-open
      if (!p.menu.hidden && nav.dataset.hover) { delete nav.dataset.hover; return; }   // pin
      if (p.menu.hidden) openNav(nav); else closeNav(nav);
    });
    nav.addEventListener('pointerenter', function (e) {
      if (e.pointerType !== 'mouse') return;
      clearTimeout(nav._t);
      if (!p.menu.hidden) return;
      nav._t = setTimeout(function () { openNav(nav); nav.dataset.hover = '1'; }, 80);   // short delay: a pointer sweeping past does not open it
    });
    nav.addEventListener('pointerleave', function (e) {
      if (e.pointerType !== 'mouse') return;
      clearTimeout(nav._t);
      if (!nav.dataset.hover) return;                                                  // pinned or opened by click: leave it
      nav._t = setTimeout(function () { if (nav.dataset.hover) closeNav(nav); }, 250);
    });
  });
  document.addEventListener('click', function (e) {
    navs.forEach(function (nav) { if (!nav.contains(e.target)) closeNav(nav); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    navs.forEach(function (nav) {
      var p = parts(nav);
      if (!p.menu.hidden) { closeNav(nav); p.btn.focus(); }
    });
  });

  // ----- home page feed (infinite scroll) + archive views (GRID / CALENDAR) -----
  var viewLinks = document.querySelectorAll('.nav-menu [data-view]');
  var list = document.getElementById('scroll-list');
  var onArchive = document.body.dataset.page === 'archive';
  var manifestEl = document.getElementById('manifest');
  var statusEl = document.getElementById('scroll-status');
  var endEl = document.getElementById('scroll-end');
  var urls = [];
  try { urls = manifestEl ? JSON.parse(manifestEl.textContent) : []; } catch (e) {}
  var next = list ? Number(list.getAttribute('data-loaded')) || 0 : 0;
  var loading = false, failedAt = 0;

  function setStatus(msg) { if (statusEl) statusEl.textContent = msg; }
  function nearEnd() { return endEl && endEl.getBoundingClientRect().top < window.innerHeight + 1600; }

  function loadMore() {
    if (!list || loading) return;
    if (next >= urls.length) { setStatus(urls.length ? 'End' : ''); return; }
    if (Date.now() - failedAt < 3000) return;
    loading = true;
    setStatus('Loading');
    fetch(urls[next])
      .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.text(); })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var post = doc.querySelector('article.post');
        if (post) {
          var h1 = post.querySelector('h1');
          if (h1) { var h2 = document.createElement('h2'); h2.className = h1.className; h2.innerHTML = h1.innerHTML; h1.replaceWith(h2); }
          list.appendChild(document.importNode(post, true));
        }
        next++;
        loading = false;
        setStatus(next >= urls.length ? 'End' : '');
        if (nearEnd()) loadMore();
      })
      .catch(function () { loading = false; failedAt = Date.now(); setStatus('Could not load more. Keep scrolling to retry.'); });
  }
  function check() { if (list && nearEnd()) loadMore(); }

  function syncView() {
    if (!onArchive) return;
    var v = root.dataset.view;
    viewLinks.forEach(function (a) {
      if (a.dataset.view === v) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
    store.set('archiveView', v);
  }
  // Opened from the archive grid at '#img-<year>-<week>-<n>': put that image in the vertical middle of the screen
  // (the browser's own jump would leave it at the very top). An image taller than the screen is lined up near the top instead.
  if (document.body.dataset.page === 'post' && /^#img-/.test(location.hash)) {
    var navType = ''; try { navType = performance.getEntriesByType('navigation')[0].type; } catch (e) {}
    if (navType !== 'back_forward' && navType !== 'reload') {
      var centerImg = function () {
        var fig = document.getElementById(decodeURIComponent(location.hash.slice(1)));
        if (!fig) return;
        var r = fig.getBoundingClientRect(), vh = window.innerHeight || document.documentElement.clientHeight;
        var top = r.height >= vh - 32 ? r.top - 16 : r.top - (vh - r.height) / 2;
        window.scrollTo({ top: Math.max(0, window.scrollY + top), behavior: 'instant' });
      };
      centerImg();
      window.addEventListener('load', centerImg);
    }
  }

  if (onArchive) {
    viewLinks.forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();                                   // already on the archive: switch in place
        root.dataset.view = a.dataset.view;
        history.replaceState(null, '', '#' + a.dataset.view);
        closeAllNavs();
        window.scrollTo(0, 0);
        syncView();
      });
    });
    window.addEventListener('hashchange', function () {
      var h = location.hash.replace('#', '');
      if (h === 'grid' || h === 'calendar') { root.dataset.view = h; syncView(); }
    });
    syncView();
  }
  if (list) {                                                // the home page feed
    window.addEventListener('scroll', check, { passive: true });
    window.addEventListener('resize', check);
    check();
  }

  // ----- scroll-up bar: hides on scroll down, returns on scroll up (every page) -----
  var slim = document.getElementById('slimbar');
  if (slim) {
    var topBtn = document.getElementById('slim-top');
    var header = document.querySelector('.site-header');
    var slimNav = slim.querySelector('.nav-archive');
    var lastY = window.pageYOffset, ticking = false;

    // Scrolling down does not hide the bar at once: it lingers for HIDE_DELAY first. Scrolling back up cancels the
    // countdown (the bar stays), and while a mouse is resting on the bar or its menu the bar stays; the countdown
    // starts again when the mouse leaves. Reaching the top of the page hides it immediately (the header is back).
    var HIDE_DELAY = 1000;
    var hideTimer = 0, hidePending = false, overBar = false;
    // A one-time hint: the first time you scroll down from the top of a page, the bar slides in for the same one second and
    // then slides away again, so people learn it is there before it disappears. After that it only appears on scroll up.
    var hinted = false;

    function cancelHide() { clearTimeout(hideTimer); hideTimer = 0; }
    function hideSlim() { cancelHide(); hidePending = false; slim.classList.remove('show'); if (slimNav) closeNav(slimNav); }
    function scheduleHide() {
      if (hideTimer || !slim.classList.contains('show')) return;
      hidePending = true;
      hideTimer = setTimeout(function () {
        hideTimer = 0;
        if (overBar) return;                                   // mouse is on the bar: wait for it to leave
        hideSlim();
      }, HIDE_DELAY);
    }
    slim.addEventListener('pointerenter', function (e) { if (e.pointerType === 'mouse') { overBar = true; cancelHide(); } });
    slim.addEventListener('pointerleave', function (e) {
      if (e.pointerType !== 'mouse') return;
      overBar = false;
      if (hidePending) scheduleHide();                         // it was on its way out: restart the countdown
    });

    function topZone() { return header ? header.offsetTop + header.offsetHeight : 120; }
    function update() {
      ticking = false;
      var y = window.pageYOffset;
      var dy = y - lastY;
      if (y <= topZone()) { hideSlim(); lastY = y; return; }   // the header is still on screen
      if (Math.abs(dy) < 6) return;                            // ignore tiny movements
      if (dy < 0) { cancelHide(); hidePending = false; slim.classList.add('show'); }
      else if (!hinted && !slim.classList.contains('show')) { hinted = true; slim.classList.add('show'); scheduleHide(); }   // the hint
      else if (!overBar) scheduleHide();
      else hidePending = true;
      lastY = y;
    }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });

    // TOP: glide back up through the page. The bar stays on screen during the trip and hides itself on arrival.
    // Duration grows with distance (about 0.45s for a short climb, capped at 1.4s). Any wheel, touch, key or
    // mouse press stops it where it is; readers who prefer reduced motion get an instant jump.
    var flyId = 0;
    function cancelFly() { if (flyId) { cancelAnimationFrame(flyId); flyId = 0; } }
    function flyToTop() {
      var from = window.pageYOffset;
      if (from <= 0) return;
      if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) { window.scrollTo(0, 0); return; }
      var dur = Math.min(1400, Math.max(450, 350 + from * 0.04));
      var t0 = null;
      function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }   // ease in-out cubic
      function step(ts) {
        if (t0 === null) t0 = ts;
        var t = Math.min(1, (ts - t0) / dur);
        window.scrollTo(0, Math.round(from * (1 - ease(t))));
        flyId = t < 1 ? requestAnimationFrame(step) : 0;
      }
      flyId = requestAnimationFrame(step);
    }
    ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (ev) { window.addEventListener(ev, cancelFly, { passive: true }); });
    topBtn.addEventListener('click', function () { if (slimNav) closeNav(slimNav); flyToTop(); });
  }

  // ----- home page footer: today's date, kept current while the page stays open -----
  var todayEl = document.getElementById('today');
  if (todayEl) {
    var showToday = function () {
      var d = new Date();
      var label = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' });   // 26 October 2026
      if (todayEl.textContent !== label) {
        todayEl.textContent = label;
        var pad2 = function (n) { return (n < 10 ? '0' : '') + n; };
        todayEl.setAttribute('datetime', d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()));
      }
    };
    showToday();
    setInterval(showToday, 15000);                       // rolls over at midnight if the tab stays open
    document.addEventListener('visibilitychange', showToday);
  }

  // ----- signup form (parked: not shown on any page right now) -----
  var form = document.getElementById('subscribe-form');
  var note = document.getElementById('form-note');
  if (form) {
    form.addEventListener('submit', function (e) {
      var email = form.elements.email;
      if (!email.value || !email.checkValidity()) {
        e.preventDefault();
        if (note) note.textContent = 'Please enter a valid email address.';
        email.focus();
        return;
      }
      if (form.hasAttribute('data-unconfigured')) {
        e.preventDefault();
        if (note) note.textContent = 'Signup is not connected yet.';
      }
    });
  }
})();
