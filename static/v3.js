/* V3 landing (hidden preview at /v3/). Grid + preview + in-page week post with a zoom-open transition.
   Desktop: hover a thumbnail to see it in the blank zone above; click to open the week.
   Phones: tap a thumbnail to bring it forward over the blurred grid; tap it again to open the week. */
(function () {
  'use strict';

  var data = {};
  try { data = JSON.parse(document.getElementById('v3data').textContent); } catch (e) { return; }

  var html = document.documentElement;
  var archive = document.getElementById('archive');
  var preview = document.getElementById('hoverPreview');
  var previewImg = document.getElementById('previewImg');
  var tapScrim = document.getElementById('tapScrim');
  var postView = document.getElementById('postView');
  var postHead = document.getElementById('postHead');
  var postTextEl = document.getElementById('postText');
  var postStack = document.getElementById('postStack');
  var postBack = document.getElementById('postBack');
  var postScrim = document.getElementById('postScrim');

  var mqWide = window.matchMedia('(min-width: 720px)');
  var mqHover = window.matchMedia('(hover: hover) and (pointer: fine)');
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

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
  var toggle = document.getElementById('themeToggle');
  function paintToggle() { toggle.textContent = html.getAttribute('data-theme') === 'dark' ? 'LIGHT' : 'DARK'; }
  paintToggle();
  toggle.addEventListener('click', function () {
    var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
    paintToggle();
  });

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
  var tapped = null;   // the thumbnail currently brought forward on a touch screen

  function showPreview(img) {
    var im = imageOf(img);
    if (!im) return;
    previewImg.src = bigOf(im);
    previewImg.alt = '';
    preview.classList.add('visible');
    if (!mqHover.matches) {
      if (tapped && tapped !== img) tapped.classList.remove('tapped');
      tapped = img;
      img.classList.add('tapped');
      tapScrim.classList.add('on');
    }
  }
  function hidePreview() {
    preview.classList.remove('visible');
    tapScrim.classList.remove('on');
    if (tapped) { tapped.classList.remove('tapped'); tapped = null; }
  }

  function imageOf(img) {
    var post = data[img.dataset.k];
    return post ? post.i[+img.dataset.n - 1] : null;
  }

  archive.addEventListener('mouseover', function (e) {
    if (!mqHover.matches) return;
    var img = e.target.closest('.grid-cell img');
    if (img) showPreview(img);
  });
  archive.addEventListener('mouseout', function (e) {
    if (!mqHover.matches) return;
    if (e.target.closest('.grid-cell img')) preview.classList.remove('visible');
  });

  // ---------- the zoom ----------
  var pendingFly = null;   // where the zoom starts, set by the click
  var activeFly = null;    // the flying copy while it is in the air
  var closeTimer = 0;
  var guardTimer = 0;

  // Where the zoom starts: the picture as drawn in the preview (or the thumbnail itself if there is no preview)
  function flyStart(thumb) {
    if (reduceMotion.matches) return null;
    var rect;
    if (preview.classList.contains('visible') && previewImg.naturalWidth) {
      var b = previewImg.getBoundingClientRect();
      var nw = previewImg.naturalWidth, nh = previewImg.naturalHeight;
      var s = Math.min(b.width / nw, b.height / nh);   // object-fit: contain
      var w = nw * s, h = nh * s;
      rect = { left: b.left + (b.width - w) / 2, top: b.top + (b.height - h) / 2, width: w, height: h };
      return { rect: rect, src: previewImg.currentSrc || previewImg.src };
    }
    var t = thumb.getBoundingClientRect();
    return { rect: { left: t.left, top: t.top, width: t.width, height: t.height }, src: thumb.currentSrc || thumb.src };
  }

  function removeFly() {
    if (!activeFly) return;
    activeFly.target.style.visibility = '';
    activeFly.el.remove();
    activeFly = null;
  }

  function flyIn(fly, target) {
    removeFly();
    var end = target.getBoundingClientRect();
    if (!end.width || !end.height) return;
    var el = document.createElement('img');
    el.className = 'post-fly';
    el.src = fly.src;
    el.alt = '';
    el.style.left = end.left + 'px';
    el.style.top = end.top + 'px';
    el.style.width = end.width + 'px';
    el.style.height = end.height + 'px';
    el.style.transform = 'translate(' + (fly.rect.left - end.left) + 'px, ' + (fly.rect.top - end.top) + 'px) scale(' + (fly.rect.width / end.width) + ', ' + (fly.rect.height / end.height) + ')';
    document.body.appendChild(el);
    target.style.visibility = 'hidden';   // the real image is revealed when the copy lands
    activeFly = { el: el, target: target };
    el.getBoundingClientRect();           // flush, so the transition starts from the preview position
    el.style.transition = 'transform .55s var(--ease-open)';
    el.style.transform = 'none';
    var done = function () { if (activeFly && activeFly.el === el) removeFly(); };
    el.addEventListener('transitionend', done, { once: true });
    setTimeout(done, 800);
  }

  // ---------- post view ----------
  var currentKey = '';
  var openedFromGrid = false;
  var currentPost = null;

  // One width for every photo in the post, portraits and landscapes alike, so the column looks even.
  // It is a middle ground drawn from the preview box: 0 = the preview's height (the width a square photo has
  // in the preview), 1 = the preview's full width (the width a landscape photo has). 0.2 was the gentlest for this archive (about 41% landscape, 50% portrait or square); 0.4 is a bit wider, keeping
  // the zoom from the preview gentle for both kinds of photo and keeps most portraits on the screen.
  // Tweak this one number to taste; COLUMN_MAX caps the width on big screens.
  var POST_WIDTH_MIX = 0.4;
  var COLUMN_MAX = 816;   // the old post column width

  function layoutPost() {
    if (!currentPost) return;
    var b = previewImg.getBoundingClientRect();   // the preview box, measured even while hidden
    // on a narrow desktop window the preview box can be tiny; keep a sensible floor
    var boxW = Math.max(b.width, Math.min(window.innerWidth - 48, 560));
    var boxH = b.height;
    var w = boxH + POST_WIDTH_MIX * (boxW - boxH);
    w = Math.min(w, COLUMN_MAX, postStack.clientWidth || 9999);
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
    postView.classList.toggle('instant', !animate);
    if (animate) preview.style.transition = 'none';   // the flying copy takes over from the preview, so hide that at once
    hidePreview();
    if (animate) { void preview.offsetHeight; preview.style.transition = ''; }
    postView.classList.add('open');
    postView.setAttribute('aria-hidden', 'false');
    postView.scrollTop = 0;
    currentPost = post;
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
    removeFly();
    currentKey = '';
    openedFromGrid = false;
    currentPost = null;
    if (!postView.classList.contains('open')) return;
    postView.classList.remove('shown', 'instant');
    postScrim.classList.remove('fx');
    postView.setAttribute('aria-hidden', 'true');
    clearTimeout(closeTimer);
    closeTimer = setTimeout(function () {
      if (!postView.classList.contains('shown')) {
        postView.classList.remove('open');
        postStack.textContent = '';
        postTextEl.innerHTML = '';
      }
    }, 260);
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
    if (!img) return;
    e.preventDefault();
    if (mqHover.matches) openFrom(img);
    else if (tapped === img) openFrom(img);
    else showPreview(img);
  });

  preview.addEventListener('click', function (e) {
    if (mqHover.matches) return;
    if (e.target === previewImg && tapped) openFrom(tapped);
    else hidePreview();
  });
  tapScrim.addEventListener('click', hidePreview);
  window.addEventListener('scroll', function () { if (tapped) hidePreview(); }, { passive: true });

  function leavePost() {
    if (openedFromGrid) history.back();   // drops the #hash entry; hashchange then closes the view
    else { location.hash = ''; route(); }
  }
  postBack.addEventListener('click', function (e) { e.preventDefault(); leavePost(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && postView.classList.contains('open')) leavePost();
  });

  route();   // a link ending in #2024-w5-i5 opens straight to that image
})();
