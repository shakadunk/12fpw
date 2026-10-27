// Theme toggle, archive views (Scroll / Grid / Calendar), infinite scroll, signup form. No dependencies.
(function () {
  var root = document.documentElement;
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  };

  // ----- theme -----
  var themeBtn = document.getElementById('theme-toggle');
  function syncTheme() {
    var dark = root.dataset.theme !== 'light';
    if (themeBtn) themeBtn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#000000' : '#ffffff');
  }
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
      store.set('theme', root.dataset.theme);
      syncTheme();
    });
  }
  syncTheme();

  // ----- archive views + infinite scroll -----
  var viewBtns = document.querySelectorAll('.view-toggle [data-view], .slim-menu [data-view]');
  var list = document.getElementById('scroll-list');
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
    var v = root.dataset.view;
    viewBtns.forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.view === v)); });
    check();
  }
  viewBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      root.dataset.view = b.dataset.view;
      store.set('archiveView', b.dataset.view);
      history.replaceState(null, '', '#' + b.dataset.view);
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
  if (viewBtns.length) syncView();

  // ----- slim bar (archive only): hides on scroll down, returns on scroll up -----
  var slim = document.getElementById('slimbar');
  if (slim) {
    var viewBtn = document.getElementById('slim-view-btn');
    var menu = document.getElementById('slim-menu');
    var topBtn = document.getElementById('slim-top');
    var archiveBar = document.querySelector('.archive-bar');
    var lastY = window.pageYOffset, ticking = false;

    function closeMenu() { menu.hidden = true; slim.classList.remove('menu-open'); viewBtn.setAttribute('aria-expanded', 'false'); }
    function hideSlim() { slim.classList.remove('show'); closeMenu(); }
    function topZone() { return archiveBar ? archiveBar.offsetTop + archiveBar.offsetHeight : 200; }
    function update() {
      ticking = false;
      var y = window.pageYOffset;
      var dy = y - lastY;
      if (y <= topZone()) { hideSlim(); lastY = y; return; }   // page header and view switcher are already on screen
      if (Math.abs(dy) < 6) return;                            // ignore tiny movements
      if (dy < 0) slim.classList.add('show'); else hideSlim();
      lastY = y;
    }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });

    viewBtn.addEventListener('click', function () {
      if (!menu.hidden) { closeMenu(); return; }
      menu.hidden = false;
      slim.style.setProperty('--menu-h', menu.offsetHeight + 'px');
      slim.classList.add('menu-open');
      viewBtn.setAttribute('aria-expanded', 'true');
    });
    menu.addEventListener('click', function (e) { if (e.target.closest('[data-view]')) closeMenu(); });
    document.addEventListener('click', function (e) { if (!slim.contains(e.target)) closeMenu(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) { closeMenu(); viewBtn.focus(); } });
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
    topBtn.addEventListener('click', function () { closeMenu(); flyToTop(); });
  }

  // ----- signup form -----
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
