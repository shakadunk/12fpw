/* V3 landing (hidden preview at /v3/). Grid + preview + in-page week post with a zoom-open transition.
   Desktop: hover a thumbnail to see it in the blank zone above; click to open the week.
   Phones: tap a thumbnail to bring it forward over the blurred grid; tap it again to open the week. */
(function () {
  'use strict';

  var data = {};
  try { data = JSON.parse(document.getElementById('v3data').textContent); } catch (e) { return; }

  var html = document.documentElement;

  // Going back makes the browser restore the scroll position it recorded for that history entry, and on a
  // phone it can do that AFTER this code has already placed the grid for the flight home — so the grid ends
  // up somewhere else and the photo lands away from its thumbnail. The page positions itself, so take it over.
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  var archive = document.getElementById('archive');
  var preview = document.getElementById('hoverPreview');
  var previewImg = document.getElementById('previewImg');
  var postView = document.getElementById('postView');
  var postHead = document.getElementById('postHead');
  var postTextEl = document.getElementById('postText');
  var postStack = document.getElementById('postStack');
  var postBack = document.getElementById('postBack');
  var postScrim = document.getElementById('postScrim');

  var mqWide = window.matchMedia('(min-width: 720px)');
  var mqHover = window.matchMedia('(hover: hover) and (pointer: fine)');
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  // The preview zone exists only on a wide window with a mouse. Browser zoom narrows the window in CSS pixels,
  // so a laptop zoomed past ~200% gets the phone layout (no zone) while still having a mouse: every decision
  // about the zone has to ask both questions, or the photo flies to a zone that is not there.
  function hasZone() { return mqHover.matches && mqWide.matches; }

  // The preview and the post image use the SAME file, so the zoom never re-downloads or pops:
  // the desktop copy on wide screens, the phone copy on narrow ones.
  function bigOf(im) { return (mqWide.matches ? im.u : (im.s || im.u)); }

  // ---------- blank top zone (desktop only) ----------
  // Sized so about 1.5 rows of the grid show at the bottom. Row heights change with window width and
  // image loading, so measure instead of using a fixed vh.
  var ROWS_SHOWN = 1.5;
  function rowReady(row) {
    var imgs = row.querySelectorAll('img');
    for (var i = 0; i < imgs.length; i++) if (!imgs[i].complete || !imgs[i].naturalHeight) return false;
    return true;
  }
  function sizeOverlay() {
    if (!mqWide.matches) { html.style.removeProperty('--overlay-h'); return; }
    var rows = [].slice.call(document.querySelectorAll('.week-row')).filter(function (r) { return r.offsetHeight > 0; });
    if (rows.length < 2 || !rowReady(rows[0]) || !rowReady(rows[1])) return;
    var visible = rows[0].offsetHeight + (ROWS_SHOWN - 1) * rows[1].offsetHeight;
    // Never let the grid zone take more than 45% of the screen (keeps the preview roomy)
    var capped = Math.min(visible, window.innerHeight * 0.45);
    html.style.setProperty('--overlay-h', (window.innerHeight - capped) + 'px');
  }
  var sizeQueued = false;
  function scheduleSize() {
    if (sizeQueued) return;
    sizeQueued = true;
    requestAnimationFrame(function () { sizeQueued = false; sizeOverlay(); });
  }
  window.addEventListener('resize', scheduleSize);
  window.addEventListener('orientationchange', scheduleSize);
  window.addEventListener('load', scheduleSize);
  archive.addEventListener('load', function (e) { if (e.target.tagName === 'IMG') scheduleSize(); }, true);
  sizeOverlay();

  // ---------- theme ----------
  // The page follows the device's own light or dark setting (set before paint, in the page's head).
  // Tapping the toggle overrides that for this person, on this device, and is remembered. Setting it back
  // to whatever the device is doing clears the override, so it follows the device again from then on.
  var toggle = document.getElementById('themeToggle');
  var mqLight = window.matchMedia ? window.matchMedia('(prefers-color-scheme: light)') : null;
  function systemTheme() { return mqLight && mqLight.matches ? 'light' : 'dark'; }
  function savedTheme() { try { var t = localStorage.getItem('theme'); return (t === 'light' || t === 'dark') ? t : null; } catch (e) { return null; } }

  function paintTheme() {
    var dark = html.getAttribute('data-theme') !== 'light';
    toggle.textContent = dark ? 'LIGHT' : 'DARK';
    toggle.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#000000' : '#ffffff');   // the browser's own bars, on a phone
  }
  paintTheme();

  toggle.addEventListener('click', function () {
    var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    try {
      if (next === systemTheme()) localStorage.removeItem('theme');   // back in step with the device: follow it again
      else localStorage.setItem('theme', next);
    } catch (e) {}
    paintTheme();
  });

  // The device can change on its own (a schedule, or sunset). Follow it, unless this person has chosen.
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
  [].forEach.call(document.querySelectorAll('.year-filters button'), function (b) {
    b.addEventListener('click', function () {
      [].forEach.call(document.querySelectorAll('.year-filters button'), function (x) {
        x.classList.remove('active');
        x.setAttribute('aria-pressed', 'false');
      });
      b.classList.add('active');
      b.setAttribute('aria-pressed', 'true');
      var f = b.dataset.filter;
      [].forEach.call(document.querySelectorAll('.year-section'), function (sec) {
        sec.style.display = (f === 'all' || sec.dataset.year === f) ? '' : 'none';
      });
      hidePreview();
      scheduleSize();
    });
  });

  // ---------- preview ----------
  function showPreview(img) {
    var im = imageOf(img);
    if (!im) return;
    previewImg.src = bigOf(im);
    previewImg.alt = '';
    preview.classList.add('visible');
  }
  function hidePreview() {
    releaseHold();
    preview.classList.remove('visible');
  }

  function imageOf(img) {
    var post = data[img.dataset.k];
    return post ? post.i[+img.dataset.n - 1] : null;
  }

  archive.addEventListener('mouseover', function (e) {
    if (!hasZone()) return;
    var img = e.target.closest('.grid-cell img');
    if (!img) return;
    if (previewHeld) {
      if (!hoverIsReal(e)) return;   // the stray hover fired when the post disappeared
      releaseHold();                 // a real move onto a thumbnail takes the preview back
    }
    showPreview(img);
  });
  archive.addEventListener('mouseout', function (e) {
    if (!hasZone() || previewHeld) return;   // while held, the photo stays up
    if (e.target.closest('.grid-cell img')) preview.classList.remove('visible');
  });

  // ---------- the zoom ----------
  var pendingFly = null;   // where the zoom starts, set by the click
  var activeFly = null;    // the flying copy while it is in the air
  var closeTimer = 0;
  var guardTimer = 0;

  // Where a thumbnail's photo really is. On a phone the cell is a square crop (object-fit: cover), so the
  // photo runs past the cell; flying from that rectangle keeps the zoom even instead of squashing it.
  // On a desktop the cells are uncropped, so this is just the cell.
  function thumbPhotoRect(thumb) {
    var t = thumb.getBoundingClientRect();
    var im = imageOf(thumb);
    if (!im || !im.w || !im.h) return { left: t.left, top: t.top, width: t.width, height: t.height };
    // phone grid: the photo is shown whole (object-fit: contain) inside its box, floating on the page
    var s = Math.min(t.width / im.w, t.height / im.h);
    var w = im.w * s, h = im.h * s;
    return { left: t.left + (t.width - w) / 2, top: t.top + (t.height - h) / 2, width: w, height: h };
  }

  // The preview element fills its whole zone, but the photo inside it is letterboxed (object-fit: contain).
  // This is the rectangle the photo really occupies; the space around it is not part of the photo.
  function previewPictureRect() {
    var b = previewImg.getBoundingClientRect();
    var nw = previewImg.naturalWidth, nh = previewImg.naturalHeight;
    if (!nw || !nh || !b.width || !b.height) return null;
    var s = Math.min(b.width / nw, b.height / nh);
    var w = nw * s, h = nh * s;
    return { left: b.left + (b.width - w) / 2, top: b.top + (b.height - h) / 2, width: w, height: h };
  }

  // Where the zoom starts: the photo as drawn in the preview (or the thumbnail itself if there is no preview)
  function flyStart(thumb) {
    if (reduceMotion.matches) return null;
    var want = imageOf(thumb);
    var showingThis = !!want && previewImg.getAttribute('src') === bigOf(want);
    if (showingThis && preview.classList.contains('visible')) {
      var rect = previewPictureRect();
      if (rect) return { rect: rect, src: previewImg.currentSrc || previewImg.src };
    }
    return { rect: thumbPhotoRect(thumb), src: thumb.currentSrc || thumb.src };
  }

  function removeFly() {
    if (!activeFly) return;
    activeFly.target.style.visibility = '';
    activeFly.el.remove();
    activeFly = null;
  }

  // One flight, used both ways: a copy of the photo starts at fromRect and lands on toRect.
  // Both rectangles are measured against the window. `onPage` pins the copy to the document instead, which
  // is what the flight home needs: it ends on a thumbnail in the grid, so if anything scrolls the page
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

  // Opening: from the preview (or the thumbnail) onto the photo in the post.
  function flyIn(fly, target) {
    flyBetween(fly.rect, target.getBoundingClientRect(), fly.src, target);
  }

  // Leaving: the photo you are on flies back into the preview zone and stays there.
  // Which photo that is: the one whose centre is nearest the centre of the screen.
  function currentPostIndex() {
    var kids = postStack.children, mid = window.innerHeight / 2, best = 0, bestD = Infinity;
    for (var i = 0; i < kids.length; i++) {
      var r = kids[i].getBoundingClientRect();
      var d = Math.abs(r.top + r.height / 2 - mid);
      if (d < bestD) { bestD = d; best = i; }
    }
    return best;
  }

  // Where a photo is drawn inside the preview zone. The preview's own box is a fixed share of that zone,
  // so it can be measured even while the preview is hidden; the photo is fitted inside it (object-fit: contain).
  function previewRectFor(im) {
    var b = previewImg.getBoundingClientRect();
    if (!b.width || !b.height || !im || !im.w || !im.h) return null;
    var s = Math.min(b.width / im.w, b.height / im.h);
    var w = im.w * s, h = im.h * s;
    return { left: b.left + (b.width - w) / 2, top: b.top + (b.height - h) / 2, width: w, height: h };
  }

  // Put that photo's own thumbnail somewhere it can actually be seen before the flight home, clear of
  // whatever sits at the top: the blank zone on a desktop, the sticky year bar on a phone. The page is
  // still hidden behind the post while this happens, so the move itself is never seen.
  function ensureThumbVisible(thumb) {
    if (!thumb || !thumb.offsetParent) return;
    var r = thumb.getBoundingClientRect();
    var bar = document.querySelector('.header-right');
    // Its own height, not where it is sitting now: the bar is only stuck to the top once the page has
    // scrolled, and measuring it while it is still down in the flow throws the sum off by its travel.
    var top = mqWide.matches ? preview.getBoundingClientRect().bottom : (bar ? bar.offsetHeight : 0);
    var bottom = window.innerHeight, margin = 16;
    if (r.top >= top + margin && r.bottom <= bottom - margin) return;   // already comfortably in view: leave the grid alone
    if (mqWide.matches) {
      // only a row or so of grid is visible under the blank zone, so just bring it inside
      window.scrollBy(0, r.top < top + margin ? r.top - top - margin : r.bottom - (bottom - margin));
    } else {
      // On a phone the photo flies back onto the thumbnail itself. Nudging it just inside the edge would
      // land the photo flush against the bottom of the screen, which reads as "it went to the bottom"
      // rather than "it went where it lives". Centre it in the space below the bar instead.
      window.scrollBy(0, (r.top + r.height / 2) - (top + (bottom - top) / 2));
    }
  }

  // After landing, the preview HOLDS that photo: it stays up until the mouse moves onto another thumbnail,
  // so it never just vanishes. The browser fires a stray hover the moment the post disappears, at the spot
  // the cursor was already sitting on; a hover counts as real when it arrives somewhere else, or after the
  // mouse has actually moved. Going by the position rather than the order of events also catches a single
  // quick flick straight onto another thumbnail.
  var previewHeld = false, movedSinceLanding = false;
  var lastX = null, lastY = null, holdX = null, holdY = null;
  document.addEventListener('mousemove', function (e) {
    lastX = e.clientX; lastY = e.clientY;
    if (previewHeld) movedSinceLanding = true;
  }, { passive: true });

  function holdPreview() { previewHeld = true; movedSinceLanding = false; holdX = lastX; holdY = lastY; }
  function releaseHold() { previewHeld = false; movedSinceLanding = false; }
  function hoverIsReal(e) {
    if (movedSinceLanding || holdX === null) return true;
    return Math.abs(e.clientX - holdX) > 2 || Math.abs(e.clientY - holdY) > 2;
  }

  function landOnGrid(ret) {
    var t = preview.style.transition;
    preview.style.transition = 'none';          // swap in with no fade, exactly where the flight ended
    previewImg.src = ret.src;
    preview.classList.add('visible');
    void preview.offsetHeight;
    preview.style.transition = t;
    holdPreview();
  }

  // ---------- post view ----------
  var currentKey = '';
  var openedFromGrid = false;
  var currentPost = null;
  var currentPostKey = '';

  // One width for every photo in the post, portraits and landscapes alike, so the column looks even.
  // It is a middle ground drawn from the preview box: 0 = the preview's height (the width a square photo has
  // in the preview), 1 = the preview's full width (the width a landscape photo has). 0.2 was the gentlest for this archive (about 41% landscape, 50% portrait or square); 0.4 is a bit wider, keeping
  // the zoom from the preview gentle for both kinds of photo and keeps most portraits on the screen.
  // Tweak this one number to taste; COLUMN_MAX caps the width on big screens.
  var POST_WIDTH_MIX = 0.4;
  var COLUMN_MAX = 816;   // the old post column width

  function layoutPost() {
    if (!currentPost) return;
    var avail = postStack.clientWidth || 9999;
    var w;
    if (!mqWide.matches) {
      w = avail;                                  // on a phone the photo simply fills the column
    } else {
      var b = previewImg.getBoundingClientRect();   // the preview box, measured even while hidden
      // on a narrow desktop window the preview box can be tiny; keep a sensible floor
      var boxW = Math.max(b.width, Math.min(window.innerWidth - 48, 560));
      var boxH = b.height;
      w = Math.min(boxH + POST_WIDTH_MIX * (boxW - boxH), COLUMN_MAX, avail);
    }
    var imgs = postStack.querySelectorAll('img');
    for (var i = 0; i < imgs.length; i++) {
      var im = currentPost.i[i];
      imgs[i].style.width = w + 'px';
      imgs[i].style.height = (im && im.w && im.h) ? (w * im.h / im.w) + 'px' : 'auto';   // keeps the photo's own proportions
    }
  }
  var layoutQueued = false;
  window.addEventListener('resize', function () {
    if (layoutQueued || !postView.classList.contains('open')) return;
    layoutQueued = true;
    requestAnimationFrame(function () { layoutQueued = false; layoutPost(); });
  });

  // ---------- keeping your place while the window changes size ----------
  // Zooming the browser (or resizing the window) reflows everything. Safari has no scroll anchoring, so the
  // scroll position would stay as a number while the photos under it changed size, and whatever you were
  // looking at slid away. Remember which photo (or row) sits at the middle of the screen and the fraction
  // of the way down it, and put that same spot back in the middle after the reflow.
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
  function gridProbeY() {
    if (mqWide.matches) return preview.getBoundingClientRect().bottom + 12;
    var bar = document.querySelector('.header-right');
    return (bar ? bar.offsetHeight : 0) + 12;
  }
  function gridAnchorNow() {
    var rows = document.querySelectorAll('.week-row');
    var y = gridProbeY();
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i].getBoundingClientRect();
      if (r.height && r.bottom >= y) return { i: i, f: (y - r.top) / r.height };
    }
    return null;
  }
  function rememberPlace() {
    if (resizing) return;   // a scroll the browser makes while resizing must not overwrite the place we are holding
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

  // Debounce: trackpad Smart Zoom and pinch-zoom fire dozens of resize events
  // during a smooth ~300ms animation.  Restoring on every frame fights the
  // gesture and makes the page jump.  Instead, wait until the resize stream
  // goes quiet (150ms with no new event) and then restore once.
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
    if (anchorGrid && !activeFly) {
      var row = document.querySelectorAll('.week-row')[anchorGrid.i];
      if (row) {
        var rr = row.getBoundingClientRect();
        window.scrollBy(0, (rr.top + anchorGrid.f * rr.height) - gridProbeY());
      }
    }
    resizing = false;
    rememberPlace();
  }
  window.addEventListener('resize', function () {
    resizing = true;
    if (restoreTimer) clearTimeout(restoreTimer);
    restoreTimer = setTimeout(restorePlace, 150);
  });
  // a held preview belongs to the zone; if the window stops having one, put it away
  mqWide.addEventListener && mqWide.addEventListener('change', function () { if (!hasZone()) { hidePreview(); } });
  setTimeout(rememberPlace, 0);

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
    if (animate) preview.style.transition = 'none';   // the flying copy takes over from the preview, so hide that at once
    hidePreview();
    if (animate) { void preview.offsetHeight; preview.style.transition = ''; }
    postView.classList.add('open');
    postView.setAttribute('aria-hidden', 'false');
    postView.scrollTop = 0;
    currentPost = post;
    currentPostKey = key;
    layoutPost();   // sizes every image like the preview, so the space is reserved before anything decodes

    // Scroll so the chosen image's centre lands on the window's centre
    var n = Math.min(Math.max(imageNum, 1), post.i.length);
    var target = postStack.children[n - 1];
    var r = target.getBoundingClientRect();
    var c = postView.getBoundingClientRect();
    postView.scrollTop += (r.top + r.height / 2) - (c.top + c.height / 2);
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

    // Work out the flight home before anything is torn down: the photo you are on, where it is now,
    // and where it belongs in the preview zone.
    var ret = null;
    if (currentPost && !reduceMotion.matches) {
      var n = currentPostIndex();
      var im = currentPost.i[n];
      var node = postStack.children[n];
      var imgEl = node && (node.tagName === 'IMG' ? node : node.querySelector('img'));
      var thumb = document.querySelector('.grid-cell img[data-k="' + currentPostKey + '"][data-n="' + (n + 1) + '"]');
      if (imgEl && im) {
        ensureThumbVisible(thumb);
        // With a mouse the photo flies back into the preview zone and waits there. On a phone there is no
        // preview zone, so it flies back down into its own thumbnail, where it came from.
        var to = hasZone() ? previewRectFor(im) : (thumb ? thumbPhotoRect(thumb) : null);
        if (to) ret = { from: imgEl.getBoundingClientRect(), to: to, src: bigOf(im), imgEl: imgEl, thumb: thumb, toPreview: hasZone() };
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
      if (ret.toPreview) {
        previewImg.src = ret.src;               // the same file as the post image, so it is already cached
        flyBetween(ret.from, ret.to, ret.src, ret.imgEl, function () { landOnGrid(ret); });
      } else {
        if (ret.thumb) ret.thumb.style.visibility = 'hidden';   // the copy lands in its place
        flyBetween(ret.from, ret.to, ret.src, ret.imgEl, function () {
          if (ret.thumb) ret.thumb.style.visibility = '';
        }, true);   // pinned to the page, so it stays on its thumbnail whatever the scroll does
      }
    } else {
      removeFly();
    }

    clearTimeout(closeTimer);
    closeTimer = setTimeout(function () {
      if (!postView.classList.contains('shown')) {
        postView.classList.remove('open', 'leaving');
        postScrim.classList.remove('leaving');
        postStack.textContent = '';
        postTextEl.innerHTML = '';
      }
    }, ret ? 650 : 260);
  }

  // The address hash (#2024-w5-i5) drives the view, so the Back button and direct links both work
  function route() {
    var m = /^#(\d{4})-w(\d{1,2})-i(\d{1,2})$/.exec(location.hash);
    if (m) {
      if (currentKey === m[0] && postView.classList.contains('open')) return;
      if (showPost(m[1], m[2], +m[3])) { currentKey = m[0]; return; }
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

  // Desktop: one click opens. Touch: the first tap previews, a tap on the preview opens.
  archive.addEventListener('click', function (e) {
    var img = e.target.closest('.grid-cell img');
    if (!img) {   // phone: the empty margin around a floating photo counts as the photo
      var cell = e.target.closest('.grid-cell');
      img = cell && cell.querySelector('img');
    }
    if (!img) return;
    e.preventDefault();
    releaseHold();
    openFrom(img);   // one tap opens the week, on a mouse or a finger
  });

  function leavePost() {
    if (openedFromGrid) history.back();        // drops the #hash entry; hashchange then closes the view
    else if (location.hash) location.hash = '';   // let the hashchange do the routing, exactly once
    else route();
  }
  postBack.addEventListener('click', function (e) { e.preventDefault(); leavePost(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && postView.classList.contains('open')) leavePost();
  });

  route();   // a link ending in #2024-w5-i5 opens straight to that image
})();
