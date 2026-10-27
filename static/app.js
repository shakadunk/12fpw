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
    return { btn: nav.querySelector('.nav-archive-btn'), menu: nav.querySelector('.nav-menu'), host: nav.closest('.slim-grp') };
  }
  function closeNav(nav) {
    var p = parts(nav);
    p.menu.hidden = true;
    nav.classList.remove('open');
    if (p.host) p.host.classList.remove('menu-open');
    p.btn.setAttribute('aria-expanded', 'false');
  }
  function closeAllNavs() { navs.forEach(closeNav); }
  function openNav(nav) {
    closeAllNavs();
    var p = parts(nav);
    p.menu.hidden = false;
    var h = p.menu.offsetHeight + 'px';
    nav.style.setProperty('--menu-h', h);
    if (p.host) { p.host.style.setProperty('--menu-h', h); p.host.classList.add('menu-open'); }
    nav.classList.add('open');
    p.btn.setAttribute('aria-expanded', 'true');
  }
  navs.forEach(function (nav) {
    var p = parts(nav);
    p.btn.addEventListener('click', function () { if (p.menu.hidden) openNav(nav); else closeNav(nav); });
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

  // ----- archive views + infinite scroll -----
  var viewLinks = document.querySelectorAll('.nav-menu [data-view]');
  var list = document.getElementById('scroll-list');
  var onArchive = !!list;
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
    if (!list || loading || root.dataset.view !== 'scroll') return;
    if (next >= urls.length) { setStatus(urls.length ? 'End of archive' : ''); return; }
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
        setStatus(next >= urls.length ? 'End of archive' : '');
        if (nearEnd()) loadMore();
      })
      .catch(function () { loading = false; failedAt = Date.now(); setStatus('Could not load more. Keep scrolling to retry.'); });
  }
  function check() { if (root.dataset.view === 'scroll' && nearEnd()) loadMore(); }

  function syncView() {
    if (!onArchive) return;
    var v = root.dataset.view;
    viewLinks.forEach(function (a) {
      if (a.dataset.view === v) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
    store.set('archiveView', v);
    check();
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
      if (h === 'scroll' || h === 'grid' || h === 'calendar') { root.dataset.view = h; syncView(); }
    });
    window.addEventListener('scroll', check, { passive: true });
    window.addEventListener('resize', check);
    syncView();
  }

  // ----- scroll-up bar: hides on scroll down, returns on scroll up (every page) -----
  var slim = document.getElementById('slimbar');
  if (slim) {
    var topBtn = document.getElementById('slim-top');
    var header = document.querySelector('.site-header');
    var slimNav = slim.querySelector('.nav-archive');
    var lastY = window.pageYOffset, ticking = false;

    function hideSlim() { slim.classList.remove('show'); if (slimNav) closeNav(slimNav); }
    function topZone() { return header ? header.offsetTop + header.offsetHeight : 120; }
    function update() {
      ticking = false;
      var y = window.pageYOffset;
      var dy = y - lastY;
      if (y <= topZone()) { hideSlim(); lastY = y; return; }   // the header is still on screen
      if (Math.abs(dy) < 6) return;                            // ignore tiny movements
      if (dy < 0) slim.classList.add('show'); else hideSlim();
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
