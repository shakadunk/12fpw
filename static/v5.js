/* V5 (hidden preview at /v5/). V2's archive with V3's motion: tap or click any photo and its week opens
   in place, the photo zooming out of the thumbnail; leave and it flies back to where it came from.
   One gesture at every width — the phone's — so there is no hover step and no preview layer to get in
   the way of reading the grid. */
(function () {
  'use strict';

  var data = {};
  try { data = JSON.parse(document.getElementById('v5data').textContent); } catch (e) { return; }

  var html = document.documentElement;

  // Going back makes the browser restore the scroll position it recorded for that history entry, and it
  // can do that AFTER this code has already placed the grid for the flight home — so the grid ends up
  // somewhere else and the photo lands away from its thumbnail. The page positions itself, so take it over.
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

  var archive = document.getElementById('archive');
  var postView = document.getElementById('postView');
  var postHead = document.getElementById('postHead');
  var postTextEl = document.getElementById('postText');
  var postStack = document.getElementById('postStack');
  var postBack = document.getElementById('postBack');
  var postScrim = document.getElementById('postScrim');
  var siteHead = document.querySelector('.site-head');
  var slimbar = document.getElementById('slimbar');

  var mqWide = window.matchMedia('(min-width: 720px)');
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  // The thumbnail's flight and the post image use the same file on a given width, so the zoom never
  // re-downloads or pops: the desktop copy on wide screens, the phone copy on narrow ones.
  function bigOf(im) { return (mqWide.matches ? im.u : (im.s || im.u)); }
  function imageOf(img) {
    var post = data[img.dataset.k];
    return post ? post.i[+img.dataset.n - 1] : null;
  }

  // ---------- theme ----------
  // The page follows the device's own light or dark setting (set before paint, in the page's head).
  // Choosing here overrides that for this person, on this device, and is remembered. Setting it back to
  // whatever the device is doing clears the override, so it follows the device again from then on.
  var toggles = [].slice.call(document.querySelectorAll('.theme-toggle'));
  var mqLight = window.matchMedia ? window.matchMedia('(prefers-color-scheme: light)') : null;
  function systemTheme() { return mqLight && mqLight.matches ? 'light' : 'dark'; }
  function savedTheme() { try { var t = localStorage.getItem('theme'); return (t === 'light' || t === 'dark') ? t : null; } catch (e) { return null; } }

  function paintTheme() {
    var dark = html.getAttribute('data-theme') !== 'light';
    toggles.forEach(function (t) {
      t.textContent = dark ? 'LIGHT' : 'DARK';
      t.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    });
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#000000' : '#ffffff');
  }
  paintTheme();

  toggles.forEach(function (t) {
    t.addEventListener('click', function () {
      var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      try {
        if (next === systemTheme()) localStorage.removeItem('theme');
        else localStorage.setItem('theme', next);
      } catch (e) {}
      paintTheme();
    });
  });

  if (mqLight) {
    var onSystem = function () {
      if (savedTheme()) return;
      html.setAttribute('data-theme', systemTheme());
      paintTheme();
    };
    if (mqLight.addEventListener) mqLight.addEventListener('change', onSystem);
    else if (mqLight.addListener) mqLight.addListener(onSystem);
  }

  // ---------- year filter ----------
  // The same years appear twice (header and scroll-up bar), so a click marks both copies.
  [].forEach.call(document.querySelectorAll('.years button'), function (b) {
    b.addEventListener('click', function () {
      var f = b.dataset.filter;
      [].forEach.call(document.querySelectorAll('.years button'), function (x) {
        var on = x.dataset.filter === f;
        x.classList.toggle('active', on);
        x.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      // Whole sections, so a hidden year takes its sticky label with it
      [].forEach.call(document.querySelectorAll('.fg-year'), function (s) {
        s.style.display = (f === 'all' || s.dataset.year === f) ? '' : 'none';
      });
    });
  });

  // ---------- the zoom ----------
  var pendingFly = null;   // where the flight starts, set by the click
  var activeFly = null;    // the flying copy while it is in the air
  var closeTimer = 0;
  var gridHideTimer = 0;   // the grid is only taken out of view once the week has fully covered it
  var guardTimer = 0;

  // Where a thumbnail's photo really is. The cell is a square but the photo is shown whole inside it,
  // so it does not fill the cell; flying from the photo's own rectangle keeps the zoom even rather than
  // stretching it out of a square.
  function thumbPhotoRect(thumb) {
    var t = thumb.getBoundingClientRect();
    var im = imageOf(thumb);
    if (!im || !im.w || !im.h) return { left: t.left, top: t.top, width: t.width, height: t.height };
    var s = Math.min(t.width / im.w, t.height / im.h);
    var w = im.w * s, h = im.h * s;
    return { left: t.left + (t.width - w) / 2, top: t.top + (t.height - h) / 2, width: w, height: h };
  }

  function flyStart(thumb) {
    if (reduceMotion.matches) return null;
    return { rect: thumbPhotoRect(thumb), src: thumb.currentSrc || thumb.src };
  }

  function removeFly() {
    if (!activeFly) return;
    if (activeFly.target) activeFly.target.style.visibility = '';
    activeFly.el.remove();
    activeFly = null;
  }

  // One flight, used both ways: a copy of the photo starts at fromRect and lands on toRect. Both
  // rectangles are measured against the window. `onPage` pins the copy to the document instead, which is
  // what the flight home needs: it ends on a thumbnail in the grid, so if anything scrolls the page
  // mid-flight the copy has to move with the grid rather than stay put on the screen.
  function flyBetween(fromRect, toRect, src, hideEl, done, onPage) {
    removeFly();
    if (!toRect || !toRect.width || !toRect.height || !fromRect.width || !fromRect.height) { if (done) done(); return; }
    var dx = onPage ? window.pageXOffset : 0, dy = onPage ? window.pageYOffset : 0;
    var el = document.createElement('img');
    el.className = onPage ? 'post-fly on-page' : 'post-fly';
    el.src = src;
    el.alt = '';
    el.style.left = (toRect.left + dx) + 'px';
    el.style.top = (toRect.top + dy) + 'px';
    el.style.width = toRect.width + 'px';
    el.style.height = toRect.height + 'px';
    el.style.transform = 'translate(' + (fromRect.left - toRect.left) + 'px, ' + (fromRect.top - toRect.top) + 'px) scale(' + (fromRect.width / toRect.width) + ', ' + (fromRect.height / toRect.height) + ')';
    document.body.appendChild(el);
    if (hideEl) hideEl.style.visibility = 'hidden';   // the real image appears when the copy lands
    activeFly = { el: el, target: hideEl };
    el.getBoundingClientRect();           // flush, so the transition starts from the other end
    el.style.transition = 'transform .55s var(--ease-open)';
    el.style.transform = 'none';
    var fin = function () {
      if (!activeFly || activeFly.el !== el) return;
      if (done) done();
      removeFly();
    };
    el.addEventListener('transitionend', fin, { once: true });
    setTimeout(fin, 800);
  }

  // The flight starts from the grid's small copy, which is already on screen, so it can leave at once. The
  // full-size photo it is growing into is swapped in as soon as it is decoded, so the photo is sharp for
  // most of the way rather than a 240px copy stretched across the column.
  function flyIn(fly, target) {
    flyBetween(fly.rect, target.getBoundingClientRect(), fly.src, target);
    var el = activeFly && activeFly.el, big = target.currentSrc || target.src;
    if (!el || !big || big === fly.src) return;
    var pre = new Image();
    pre.src = big;
    (pre.decode ? pre.decode() : Promise.reject()).then(function () {
      if (activeFly && activeFly.el === el) el.src = big;
    }, function () {});
  }

  // Which photo you are on: the one whose centre is nearest the centre of the screen.
  function currentPostIndex() {
    var kids = postStack.children, mid = window.innerHeight / 2, best = 0, bestD = Infinity;
    for (var i = 0; i < kids.length; i++) {
      var r = kids[i].getBoundingClientRect();
      var d = Math.abs(r.top + r.height / 2 - mid);
      if (d < bestD) { bestD = d; best = i; }
    }
    return best;
  }

  // Put the photo's own thumbnail somewhere it can be seen before the flight home. Nothing is pinned
  // over the grid, so centre it: nudging it just inside an edge would land the photo flush against the
  // bottom of the screen, which reads as "it went to the bottom" rather than "it went where it lives".
  // The page is still hidden behind the post while this happens, so the move itself is never seen.
  function ensureThumbVisible(thumb) {
    if (!thumb || !thumb.offsetParent) return;
    var r = thumb.getBoundingClientRect();
    var bottom = window.innerHeight, margin = 16;
    if (r.top >= margin && r.bottom <= bottom - margin) return;
    window.scrollBy(0, (r.top + r.height / 2) - bottom / 2);
  }

  // ---------- keeping your place while the window changes size ----------
  // Zooming the browser (or resizing the window) reflows everything. Safari has no scroll anchoring, so
  // the scroll position would stay as a number while the photos under it changed size, and whatever you
  // were looking at would slide away. Remember which photo (or row) sits at the middle of the screen and
  // how far down it, and put that same spot back after the reflow.
  var anchorPost = null, anchorGrid = null, resizing = false, anchorQueued = false;

  function postAnchorNow() {
    var kids = postStack.children;
    if (!kids.length || !postView.classList.contains('open')) return null;
    var cy = postView.getBoundingClientRect().top + postView.clientHeight / 2;
    for (var i = 0; i < kids.length; i++) {
      var r = kids[i].getBoundingClientRect();
      if (r.bottom >= cy || i === kids.length - 1) return { i: i, f: r.height ? (cy - r.top) / r.height : 0 };
    }
    return null;
  }
  // Nothing is pinned over the grid (the scroll-up bar is only there on the way up), so the line we
  // judge "which week are you on" by is just inside the top of the screen, at every width.
  function gridProbeY() { return 12; }
  function gridAnchorNow() {
    var rows = document.querySelectorAll('.fg-week');
    var y = gridProbeY();
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i].getBoundingClientRect();
      // Clamped: the weeks tile the page, but a filtered-out week or a sub-pixel seam could still put
      // the probe just outside one, and a fraction beyond its own box would move the mark on restore.
      if (r.height && r.bottom >= y) return { i: i, f: Math.min(1, Math.max(0, (y - r.top) / r.height)) };
    }
    return null;
  }
  function rememberPlace() {
    if (resizing) return;   // a scroll the browser makes while resizing must not overwrite the place we hold
    anchorPost = postAnchorNow();
    anchorGrid = gridAnchorNow() || anchorGrid;
  }
  function onScrollRemember() {
    if (anchorQueued) return;
    anchorQueued = true;
    requestAnimationFrame(function () { anchorQueued = false; rememberPlace(); });
  }
  window.addEventListener('scroll', onScrollRemember, { passive: true });
  postView.addEventListener('scroll', onScrollRemember, { passive: true });

  // Trackpad Smart Zoom and pinch-zoom fire dozens of resize events during one smooth ~300ms gesture.
  // Restoring on every frame fights the gesture and makes the page jump: wait until the stream goes
  // quiet (150ms with no new event), then put the place back once.
  var restoreTimer = null;
  function restorePlace() {
    restoreTimer = null;
    if (anchorPost && postView.classList.contains('open')) {
      var node = postStack.children[anchorPost.i];
      if (node) {
        var r = node.getBoundingClientRect();
        var cy = postView.getBoundingClientRect().top + postView.clientHeight / 2;
        postView.scrollTop += (r.top + anchorPost.f * r.height) - cy;
      }
    }
    // Not while a post covers the grid: the grid is hidden, and scrolling it would only confuse the
    // scrollbar under a view that is not showing it.
    if (anchorGrid && !activeFly && !postView.classList.contains('open')) {
      var row = document.querySelectorAll('.fg-week')[anchorGrid.i];
      if (row) {
        var rr = row.getBoundingClientRect();
        window.scrollBy(0, (rr.top + anchorGrid.f * rr.height) - gridProbeY());
      }
    }
    resizing = false;
    rememberPlace();
  }
  // Only a change of width is a zoom. On a phone the browser's toolbar shrinks and grows as you scroll,
  // which fires resize with only the height changed; nothing reflows then, and treating it as a zoom froze
  // the place mid-scroll and pulled the page back to it 150ms later, a visible jump against your finger.
  var lastWidth = window.innerWidth;
  window.addEventListener('resize', function () {
    if (window.innerWidth === lastWidth) return;
    lastWidth = window.innerWidth;
    resizing = true;
    if (restoreTimer) clearTimeout(restoreTimer);
    restoreTimer = setTimeout(restorePlace, 150);
  });
  setTimeout(rememberPlace, 0);

  // ---------- post view ----------
  var currentKey = '';
  var openedFromGrid = false;
  var currentPost = null;
  var currentPostKey = '';

  function showPost(year, week, imageNum) {
    var fly = pendingFly;
    pendingFly = null;
    var key = year + '-' + (+week);
    var post = data[key];
    if (!post) return false;

    postHead.textContent = 'Week ' + (+week) + ' ';
    var yr = document.createElement('span');
    yr.className = 'post-year';
    yr.textContent = year;
    postHead.appendChild(yr);

    postTextEl.innerHTML = post.t || '';
    postTextEl.hidden = !post.t;

    postStack.textContent = '';
    post.i.forEach(function (im, i) {
      var img = document.createElement('img');
      img.src = bigOf(im);
      // Its own proportions, so the column holds the right space before the file arrives and nothing
      // jumps. The width comes from the CSS column; no script sizes anything.
      if (im.w && im.h) { img.width = im.w; img.height = im.h; }
      img.alt = 'Image ' + (i + 1) + ' of ' + post.i.length + ', Week ' + (+week) + ' ' + year;
      img.loading = i < 2 ? 'eager' : 'lazy';
      img.decoding = 'async';
      var node = img;
      if (im.l) {   // reverse-image search, or the week's own link
        var a = document.createElement('a');
        a.href = im.l;
        a.target = '_blank';
        a.rel = 'noopener';
        a.appendChild(img);
        node = a;
      }
      postStack.appendChild(node);
    });

    var animate = !!fly && !reduceMotion.matches;
    clearTimeout(closeTimer);
    postView.classList.remove('leaving');
    postScrim.classList.remove('leaving');
    postView.classList.toggle('instant', !animate);
    postView.classList.add('open');
    // The grid stays where it is while the photo flies, so you see it lift off the archive and the scrim
    // blur the rest away behind it. Taking the grid out of view at this point would leave the photo
    // crossing a blank page. It is only hidden once the week has fully covered it, which is also the
    // only time it could show through: Safari's fixed overlay can uncover the page during a pinch-zoom.
    clearTimeout(gridHideTimer);
    gridHideTimer = setTimeout(function () {
      gridHideTimer = 0;
      if (postView.classList.contains('open') && !postView.classList.contains('leaving')) {
        archive.style.visibility = 'hidden';
      }
    }, animate ? 620 : 0);
    postView.setAttribute('aria-hidden', 'false');
    postView.scrollTop = 0;
    currentPost = post;
    currentPostKey = key;

    // imageNum 0 means "open at the top", which is what the week number does: you arrive at the week's
    // writing and scroll down into the photos. A thumbnail passes its own number and lands on that photo.
    var atTop = !imageNum;
    var n = Math.min(Math.max(imageNum || 1, 1), post.i.length);
    var target = postStack.children[n - 1];
    if (!atTop) {
      var r = target.getBoundingClientRect();
      var c = postView.getBoundingClientRect();
      postView.scrollTop += (r.top + r.height / 2) - (c.top + c.height / 2);
    }
    postView.focus({ preventScroll: true });

    // A fast double-tap on a thumbnail must not land on the image and open its link by accident
    postStack.classList.add('guard');
    clearTimeout(guardTimer);
    guardTimer = setTimeout(function () { postStack.classList.remove('guard'); }, 600);

    var targetImg = target.tagName === 'IMG' ? target : target.querySelector('img');
    if (animate) {
      flyIn(fly, targetImg);
      requestAnimationFrame(function () {
        postView.classList.add('shown');
        postScrim.classList.add('fx');
      });
    } else {
      removeFly();
      postView.classList.add('shown');
      postScrim.classList.add('fx');
    }
    return true;
  }

  function closePostView() {
    if (postView.classList.contains('leaving')) return;   // already flying home; a second call would cancel it
    if (!postView.classList.contains('open')) {
      removeFly();
      currentKey = ''; openedFromGrid = false; currentPost = null; currentPostKey = '';
      return;
    }

    // Back in view before anything flies, so the photo has an archive to land on and the week fades off
    // it rather than off a blank page.
    clearTimeout(gridHideTimer);
    gridHideTimer = 0;
    archive.style.visibility = '';

    // Work out the flight home before anything is torn down: the photo you are on, where it is now, and
    // the thumbnail it came from.
    var ret = null;
    if (currentPost && !reduceMotion.matches) {
      var n = currentPostIndex();
      var im = currentPost.i[n];
      var node = postStack.children[n];
      var imgEl = node && (node.tagName === 'IMG' ? node : node.querySelector('img'));
      var thumb = document.querySelector('.fg-cell img[data-k="' + currentPostKey + '"][data-n="' + (n + 1) + '"]');
      if (imgEl && im && thumb) {
        ensureThumbVisible(thumb);
        ret = { from: imgEl.getBoundingClientRect(), to: thumbPhotoRect(thumb), src: bigOf(im), imgEl: imgEl, thumb: thumb };
      }
    }

    currentKey = '';
    openedFromGrid = false;
    currentPost = null;
    currentPostKey = '';

    postView.classList.remove('shown', 'instant');
    postScrim.classList.remove('fx');
    postView.setAttribute('aria-hidden', 'true');

    if (ret) {
      postView.classList.add('leaving');        // unblur and fade at the pace of the flight
      postScrim.classList.add('leaving');
      ret.thumb.style.visibility = 'hidden';    // the copy lands in its place
      flyBetween(ret.from, ret.to, ret.src, ret.imgEl, function () {
        ret.thumb.style.visibility = '';
      }, true);   // pinned to the page, so it stays on its thumbnail whatever the scroll does
    } else {
      postScrim.classList.add('leaving');   // fade the blur out rather than snap it off
      removeFly();
    }

    clearTimeout(closeTimer);
    closeTimer = setTimeout(function () {
      if (!postView.classList.contains('shown')) {
        postView.classList.remove('open', 'leaving');
        postScrim.classList.remove('leaving');
        archive.style.visibility = '';   // reveal the grid again now the overlay is fully gone
        postStack.textContent = '';
        postTextEl.innerHTML = '';
      }
    }, ret ? 650 : 260);
  }

  // The address hash drives the view, so the Back button and direct links both work.
  // #2024-w5-i5 opens on that photo; #2024-w5 opens the week at its writing.
  function route() {
    var m = /^#(\d{4})-w(\d{1,2})(?:-i(\d{1,2}))?$/.exec(location.hash);
    if (m) {
      if (currentKey === m[0] && postView.classList.contains('open')) return;
      if (showPost(m[1], m[2], m[3] ? +m[3] : 0)) { currentKey = m[0]; return; }
    }
    closePostView();
  }
  window.addEventListener('hashchange', route);

  function openFrom(img) {
    pendingFly = flyStart(img);
    openedFromGrid = true;
    location.hash = img.dataset.k.replace('-', '-w') + '-i' + img.dataset.n;
    route();
  }

  // The week number opens the week from the top, where its writing is
  function openWeek(key) {
    pendingFly = null;
    openedFromGrid = true;
    location.hash = key.replace('-', '-w');
    route();
  }

  // One gesture, the same on a mouse and a finger: touch a photo and you are in its week, at it.
  archive.addEventListener('click', function (e) {
    var num = e.target.closest('.fg-label');
    if (num) { e.preventDefault(); openWeek(num.dataset.k); return; }
    var txt = e.target.closest('.fg-text');
    if (txt) {
      if (e.target.closest('a')) return;   // a link inside the blurb goes to its own page, not into the week
      e.preventDefault();
      openWeek(txt.dataset.k);
      return;
    }
    var img = e.target.closest('.fg-cell img');
    if (!img) {   // the empty margin around a photo floating in its square counts as the photo
      var cell = e.target.closest('.fg-cell');
      img = cell && cell.querySelector('img');
    }
    if (!img) return;
    e.preventDefault();
    openFrom(img);
  });

  // The blurb is reachable by keyboard too (role="button" tabindex="0"); Enter/Space open it the same way.
  archive.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var txt = e.target.closest && e.target.closest('.fg-text');
    if (!txt) return;
    e.preventDefault();
    openWeek(txt.dataset.k);
  });

  function leavePost() {
    if (openedFromGrid) history.back();           // drops the #hash entry; hashchange then closes the view
    else if (location.hash) location.hash = '';   // let the hashchange do the routing, exactly once
    else route();
  }
  postBack.addEventListener('click', function (e) { e.preventDefault(); leavePost(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && postView.classList.contains('open')) leavePost();
  });

  // ---------- scroll-up bar ----------
  // The header scrolls away with the page, so the controls come back as a thin bar whenever you head
  // back up. Scrolling down does not hide it at once: it lingers, and resting the mouse on it holds it.
  // The first time you scroll down from the top it slides in briefly and leaves again, so you learn it is there.
  if (slimbar) {
    var slimTop = document.getElementById('slimTop');
    var lastSlimY = window.pageYOffset, slimTicking = false;
    function hideDelay() { return mqWide.matches ? 1800 : 1400; }
    var hideTimer = 0, hidePending = false, overBar = false, hinted = false;

    function cancelHide() { clearTimeout(hideTimer); hideTimer = 0; }
    function hideSlim() { cancelHide(); hidePending = false; slimbar.classList.remove('show'); }
    function scheduleHide() {
      if (hideTimer || !slimbar.classList.contains('show')) return;
      hidePending = true;
      hideTimer = setTimeout(function () {
        hideTimer = 0;
        if (overBar) return;                 // mouse is resting on the bar: wait for it to leave
        hideSlim();
      }, hideDelay());
    }
    slimbar.addEventListener('pointerenter', function (e) { if (e.pointerType === 'mouse') { overBar = true; cancelHide(); } });
    slimbar.addEventListener('pointerleave', function (e) {
      if (e.pointerType !== 'mouse') return;
      overBar = false;
      if (hidePending) scheduleHide();       // it was on its way out: restart the countdown
    });

    function topZone() { return siteHead ? siteHead.offsetHeight : 120; }
    function slimUpdate() {
      slimTicking = false;
      var y = window.pageYOffset;
      var dy = y - lastSlimY;
      if (y <= topZone()) { hideSlim(); lastSlimY = y; return; }   // the header itself is still on screen
      if (Math.abs(dy) < 6) return;                                // ignore tiny movements
      if (dy < 0) { cancelHide(); hidePending = false; slimbar.classList.add('show'); }
      else if (!hinted && !slimbar.classList.contains('show')) { hinted = true; slimbar.classList.add('show'); scheduleHide(); }
      else if (!overBar) scheduleHide();
      else hidePending = true;
      lastSlimY = y;
    }
    window.addEventListener('scroll', function () {
      if (!slimTicking) { slimTicking = true; requestAnimationFrame(slimUpdate); }
    }, { passive: true });

    // TOP: glide back up through the page rather than teleport, so you keep your bearings on a long
    // archive. Any wheel, touch, key or mouse press stops it where it is.
    var flyId = 0;
    function cancelFlyTop() { if (flyId) { cancelAnimationFrame(flyId); flyId = 0; } }
    function flyToTop() {
      var from = window.pageYOffset;
      if (from <= 0) return;
      if (reduceMotion.matches) { window.scrollTo(0, 0); return; }
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
    ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (ev) {
      window.addEventListener(ev, cancelFlyTop, { passive: true });
    });
    if (slimTop) slimTop.addEventListener('click', flyToTop);
  }

  route();   // a link ending in #2024-w5-i5 opens straight to that photo
})();
