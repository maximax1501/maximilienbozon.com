/* Maximilien Bozon — behaviour.
   Six jobs: move the light, run the entrance, reveal on scroll, wind the
   hero film by the scroll wheel, light the plates, and open a plate full
   screen.
   Everything degrades to a fully readable page without it. */

(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = window.matchMedia("(pointer: fine)").matches;
  var root = document.documentElement;

  /* --- the lamp ------------------------------------------------------- */
  /* the position lives on <html> so the overture can borrow the same light */
  if (fine && !reduced) {
    var lamp = document.createElement("div");
    lamp.className = "lamp";
    document.body.appendChild(lamp);

    var tx = window.innerWidth / 2, ty = window.innerHeight * 0.38;
    var cx = tx, cy = ty, queued = false;

    window.addEventListener("pointermove", function (e) {
      tx = e.clientX; ty = e.clientY;
      if (!queued) { queued = true; requestAnimationFrame(step); }
    }, { passive: true });

    function step() {
      queued = false;
      cx += (tx - cx) * 0.12;
      cy += (ty - cy) * 0.12;
      root.style.setProperty("--mx", cx + "px");
      root.style.setProperty("--my", cy + "px");
      if (Math.abs(tx - cx) > 0.5 || Math.abs(ty - cy) > 0.5) {
        queued = true; requestAnimationFrame(step);
      }
    }
    step();
  }

  /* --- the overture --------------------------------------------------- */
  /* Armed in <head> so it never flashes. It lifts on its own after the name
     has settled, or the moment the visitor does anything at all. */
  var overture = document.querySelector("[data-overture]");
  if (overture && root.classList.contains("overture-armed")) {
    var lifted = false;
    var hold = window.setTimeout(lift, reduced ? 2400 : 3200);
    var enter = overture.querySelector("[data-enter]");

    if (enter) { try { enter.focus({ preventScroll: true }); } catch (e) { enter.focus(); } }

    overture.addEventListener("click", lift);
    window.addEventListener("keydown", onKey);
    window.addEventListener("wheel", lift, { passive: true });
    window.addEventListener("touchstart", lift, { passive: true });

    function onKey(e) {
      if (e.key === "Tab") return;         // let focus move without leaving
      lift();
    }

    function lift() {
      if (lifted) return;
      lifted = true;
      window.clearTimeout(hold);
      try { sessionStorage.setItem("mb-overture", "seen"); } catch (e) {}

      window.removeEventListener("keydown", onKey);
      window.removeEventListener("wheel", lift);
      window.removeEventListener("touchstart", lift);

      if (enter && document.activeElement === enter) { enter.blur(); }
      overture.classList.add("is-lifting");

      window.setTimeout(function () {
        root.classList.remove("overture-armed");
        if (overture.parentNode) { overture.parentNode.removeChild(overture); }
      }, reduced ? 320 : 1150);
    }
  }

  /* mark the page as enhanced so the failsafe in <head> stands down */
  document.documentElement.dataset.enhanced = "1";

  /* --- reveal on scroll ----------------------------------------------- */
  var revealables = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var revealer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-in");
        revealer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });

    revealables.forEach(function (el) { revealer.observe(el); });
  } else {
    revealables.forEach(function (el) { el.classList.add("is-in"); });
  }

  /* --- light the plates as they reach the middle of the frame --------- */
  var plates = document.querySelectorAll(".plate");
  if (plates.length && "IntersectionObserver" in window && !reduced) {
    var lighter = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        entry.target.classList.toggle("is-lit", entry.isIntersecting);
      });
    }, { rootMargin: "-18% 0px -18% 0px", threshold: 0 });

    plates.forEach(function (p) { lighter.observe(p); });
  } else {
    plates.forEach(function (p) { p.classList.add("is-lit"); });
  }

  /* --- the hero film: the scroll wheel is the transport ---------------- */
  /* The clip was cut into numbered stills by film.py. The section is made
     tall, its stage is pinned to the window, and how far the page has
     scrolled through the section decides which still is on the canvas. The
     effect is a film you wind by hand, forwards and backwards.

     Three things keep it honest. It only starts on a wide screen with
     motion allowed, because on a phone a landscape frame cropped to a
     portrait window is a sliver and three megabytes is somebody's data
     plan. It never blocks: the still photograph underneath is the page
     until the first frame is decoded, and stays the page if the frames
     never arrive. And it draws on an animation frame, never straight from
     the scroll event, so a fast wheel cannot queue up work it has to
     finish. */
  var film = document.querySelector("[data-film]");
  var canvas = film && film.querySelector("[data-film-canvas]");

  /* Pixels, not rem: this is about how much window there is to fill, and
     the root font size on this site moves with the viewport. The aspect
     test keeps a landscape clip out of a portrait window, where cover
     would crop it to a sliver. */
  var wide = window.matchMedia("(min-width: 800px) and (min-aspect-ratio: 9/10)");

  if (film && canvas && canvas.getContext && !reduced) {
    /* Where each frame belongs in the clip, 0 to 1. They are not evenly
       spaced: film.py keeps every frame through the stretch where the
       camera pulls back and only a few through the still end, so the
       download buys smoothness where there is something to be smooth
       about. The timing of the piece is carried here rather than by the
       spacing of the files. */
    var times = [];
    try { times = JSON.parse(film.getAttribute("data-film-times") || "[]"); }
    catch (e) { times = []; }

    var count = times.length;
    var path = film.getAttribute("data-film-path") || "";
    var screens = parseInt(film.getAttribute("data-film-screens"), 10) || 3;
    var ease = parseFloat(film.getAttribute("data-film-ease"));
    if (!(ease >= 0 && ease <= 1)) { ease = 0; }

    // The name holds the opening screen and has cleared by this much of
    // the scroll, well before the camera starts to pull back.
    var FADE = 0.16;

    var ctx = canvas.getContext("2d", { alpha: false });
    var shots = new Array(count);       // the Image objects, once decoded
    var ready = 0;                      // how many have arrived, from the top
    var shown = -1;                     // which one is on the canvas now
    var started = false;
    var pending = false;
    var box = { w: 0, h: 0 };

    if (count > 0) {
      if (wide.matches) {
        load();
      } else if (wide.addEventListener) {
        // a window dragged wider, or a phone turned on its side
        wide.addEventListener("change", function once(e) {
          if (!e.matches) return;
          wide.removeEventListener("change", once);
          load();
        });
      }
    }

    /* Frames are asked for in order and the run of them that has arrived
       from the first is what we are allowed to draw, so the film is never
       missing a middle. Six at a time keeps the connection busy without
       starving the photographs further down the page. */
    function load() {
      var next = 0, open = 0;

      function pump() {
        while (open < 6 && next < count) { fetch(next++); }
      }

      function fetch(i) {
        open++;
        var img = new Image();
        img.decoding = "async";
        img.onload = function () { shots[i] = img; done(); };
        img.onerror = function () { done(); };   // a hole stops the run, not the page
        img.src = path + pad(i + 1) + ".jpg";
      }

      function done() {
        open--;
        while (ready < count && shots[ready]) { ready++; }
        if (ready > 0 && !started) { begin(); }
        draw();
        pump();
      }

      pump();
    }

    function pad(n) { return n < 100 ? ("00" + n).slice(-3) : String(n); }

    /* Nothing visible changes until there is a frame to show, so a failed
       or slow download leaves the still photograph in place. */
    function begin() {
      started = true;
      film.style.setProperty("--film-screens", screens);
      film.classList.add("is-film");
      size();
      window.addEventListener("scroll", request, { passive: true });
      window.addEventListener("resize", onResize, { passive: true });
    }

    /* The canvas is given real device pixels rather than CSS ones, or the
       frames would be drawn soft on the screens most likely to see them. */
    function size() {
      var rect = canvas.getBoundingClientRect();
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      box.w = Math.round(rect.width * dpr);
      box.h = Math.round(rect.height * dpr);
      if (canvas.width !== box.w || canvas.height !== box.h) {
        canvas.width = box.w;
        canvas.height = box.h;
        shown = -1;                    // resizing clears it: draw again

        /* Giving a canvas a size throws away everything the context was
           told, this included — so it is set here, after, and never once
           at the start. The frames are drawn larger than they were cut,
           and this is how the browser fills in between their pixels: the
           default is the cheapest filter it has. */
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
      }
    }

    function onResize() { size(); request(); }

    function request() {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(function () { pending = false; draw(); });
    }

    /* 0 while the film waits at the top of the window, 1 once the section
       has been scrolled all the way through. */
    function progress() {
      var top = film.getBoundingClientRect().top;
      var run = film.offsetHeight - window.innerHeight;
      if (run <= 0) return 0;
      return Math.min(1, Math.max(0, -top / run));
    }

    /* Scroll in, position in the clip out. A straight one-to-one spends as
       much scrolling on the still end of this clip as on the pull-back,
       which reads as a rush followed by a long nothing. Bending it towards
       p^2.2 spends more scroll where the picture is moving and less where
       it has settled. The bend is blended with the straight mapping rather
       than used on its own, because on its own it starts at a standstill,
       and this clip opens on half a second of near-stillness that would
       then sit frozen for a quarter of the scroll. */
    function wind(p) {
      if (!ease) return p;
      return (1 - ease) * p + ease * Math.pow(p, 2.2);
    }

    /* The frame standing closest to this point in the clip. Binary search,
       because a thrown scroll can land anywhere and walking from where we
       were would make a long jump cost more than a short one. */
    function at(p) {
      var lo = 0, hi = count - 1;
      while (lo < hi) {
        var mid = (lo + hi) >> 1;
        if (times[mid] < p) { lo = mid + 1; } else { hi = mid; }
      }
      if (lo > 0 && p - times[lo - 1] < times[lo] - p) { lo -= 1; }
      return lo;
    }

    function draw() {
      if (!started) return;
      var p = progress();

      film.style.setProperty(
        "--film-fade", (1 - Math.min(1, p / FADE)).toFixed(3));

      // The wanted frame, held back to the last one that has arrived.
      var want = at(wind(p));
      if (want > ready - 1) { want = ready - 1; }
      if (want < 0 || want === shown) return;

      var img = shots[want];
      if (!img) return;
      shown = want;

      // cover: fill the window and lose the overflow, as the still does
      var scale = Math.max(box.w / img.naturalWidth, box.h / img.naturalHeight);
      var w = img.naturalWidth * scale, h = img.naturalHeight * scale;
      ctx.drawImage(img, (box.w - w) / 2, (box.h - h) / 2, w, h);
    }
  }

  /* --- hold layout steady: set the real ratio once each image loads ---- */
  Array.prototype.forEach.call(
    document.querySelectorAll(".plate__frame img"),
    function (img) {
      var frame = img.parentNode;
      var figure = frame.parentNode;
      function fix() {
        var w = img.naturalWidth, h = img.naturalHeight;
        if (!w || !h) return;
        frame.style.aspectRatio = w + " / " + h;
        figure.style.setProperty("--ar", (w / h).toFixed(4));
      }
      if (img.complete) { fix(); } else { img.addEventListener("load", fix, { once: true }); }
    }
  );

  /* --- a plate that failed to arrive gets one more chance -------------- */
  /* A dropped connection leaves the frame empty and the alt text bare.
     Ask again once, past the cache, rather than leave a hole on the wall. */
  Array.prototype.forEach.call(
    document.querySelectorAll(".plate__frame img"),
    function (img) {
      var retried = false;
      img.addEventListener("error", function () {
        if (retried) return;
        retried = true;
        var base = img.src.split("#")[0];
        window.setTimeout(function () {
          img.src = base + (base.indexOf("?") < 0 ? "?" : "&") + "retry=1";
        }, 600);
      });
    }
  );

  /* --- arriving on a link straight to a plate ------------------------- */
  /* Every plate is published with a measured ratio, but the block above
     replaces it with the image's real one as each photograph arrives, so
     the column keeps changing height for a second or two after load. A
     link to plate XXX would land wherever the page happened to be at that
     instant. So the scroll is re-asserted every frame until the target
     stops moving — or until the visitor takes over, which always wins.

     This is for links from elsewhere: the study pages point back here, and
     so does anyone who saved the address of a plate. The index at the top
     of the page no longer scrolls at all — it opens the picture. */
  if (document.querySelector(".plates")) {
    var frame = 0, release = null;

    function stop() {
      if (frame) { window.cancelAnimationFrame(frame); frame = 0; }
      if (release) { release(); release = null; }
    }

    function hold(target) {
      stop();

      // Smooth scrolling is right for a reading page and wrong for this:
      // the animation would restart from a new place on every reflow.
      var was = root.style.scrollBehavior;
      root.style.scrollBehavior = "auto";

      var deadline = Date.now() + 1800;
      var previous = -1, steady = 0;
      var taken = false;
      function surrender() { taken = true; }

      window.addEventListener("wheel", surrender, { passive: true });
      window.addEventListener("touchstart", surrender, { passive: true });
      window.addEventListener("keydown", surrender);

      release = function () {
        root.style.scrollBehavior = was;
        window.removeEventListener("wheel", surrender);
        window.removeEventListener("touchstart", surrender);
        window.removeEventListener("keydown", surrender);
      };

      (function tick() {
        frame = 0;
        if (taken) { stop(); return; }

        var margin = parseFloat(
          window.getComputedStyle(target).scrollMarginTop) || 0;
        var top = Math.max(
          0, target.getBoundingClientRect().top + window.pageYOffset - margin);

        window.scrollTo(0, top);
        steady = Math.abs(top - previous) < 1 ? steady + 1 : 0;
        previous = top;

        // Six still frames means the images above have finished arriving.
        if (steady < 6 && Date.now() < deadline) {
          frame = window.requestAnimationFrame(tick);
        } else {
          stop();
        }
      })();
    }

    if (window.location.hash) {
      var landing = document.querySelector(window.location.hash);
      if (landing && landing.classList.contains("plate")) {
        window.addEventListener("load", function () { hold(landing); });
      }
    }
  }

  /* --- open a plate full screen --------------------------------------- */
  /* The expand control is a plain link to the full-size file, so it still
     works with none of this. Here it becomes a viewer instead. */
  /* --- ordering a print ------------------------------------------------
     The price list arrives as JSON written by build.py from shop.py, so
     nothing here knows what anything costs. If that block is missing — the
     shop closed, or no price entered yet — `shop` stays null and the order
     control is never built, which is the right way for this to fail.

     The panel slides over the lightbox rather than replacing it: choosing a
     size is a decision about a particular photograph, and you should be
     able to keep looking at it while you decide. */
  var shop = null;
  try {
    var raw = document.getElementById("shop-data");
    if (raw) { shop = JSON.parse(raw.textContent); }
  } catch (e) { shop = null; }

  function money(v) {
    if (v === null || v === undefined) return "";
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency", currency: (shop.currency || "eur").toUpperCase(),
        maximumFractionDigits: 0
      }).format(v);
    } catch (e) {
      return (shop.symbol || "") + Math.round(v);
    }
  }

  /* A format is a longest edge, not a rectangle, so the short side is the
     photograph's own. This is what lets one price list serve pictures of
     every shape without cropping any of them. */
  function sides(edge, ar) {
    if (!ar || !isFinite(ar) || ar <= 0) return null;
    var w = ar >= 1 ? edge : edge * ar;
    var h = ar >= 1 ? edge / ar : edge;
    return Math.round(w) + " × " + Math.round(h) + " cm";
  }

  function remembered(key, fallback) {
    try {
      return window.localStorage.getItem("mb-order-" + key) || fallback;
    } catch (e) { return fallback; }
  }

  function remember(key, value) {
    try { window.localStorage.setItem("mb-order-" + key, value); } catch (e) {}
  }

  function makeOrder(host) {
    if (!shop) return null;

    var el = document.createElement("aside");
    el.className = "order";
    el.setAttribute("aria-label", "Order a print");
    el.hidden = true;

    var state = {
      fig: null,
      format: remembered("format", shop.formats[0] && shop.formats[0].id),
      support: remembered("support", shop.supports[0] && shop.supports[0].id),
      framing: remembered("framing", shop.framings[0] && shop.framings[0].id)
    };

    function group(name, legend, items) {
      return '<fieldset class="order__group">' +
        '<legend class="order__legend">' + legend + "</legend>" +
        '<div class="order__options" data-group="' + name + '">' + items + "</div>" +
        "</fieldset>";
    }

    function option(name, value, label, note, extra) {
      return '<label class="order__opt">' +
        '<input type="radio" name="mb-' + name + '" value="' + value + '">' +
        '<span class="order__opt-body">' +
          '<span class="order__opt-label">' + label + "</span>" +
          (extra ? '<span class="order__opt-extra">' + extra + "</span>" : "") +
          (note ? '<span class="order__opt-note">' + note + "</span>" : "") +
        "</span></label>";
    }

    el.innerHTML =
      '<button class="order__close" type="button" aria-label="Close order panel">✕</button>' +
      '<div class="order__scroll">' +
        '<p class="label order__eyebrow">Order a print</p>' +
        '<p class="order__plate"></p>' +
        '<h2 class="order__title"></h2>' +
        '<form class="order__form">' +
          group("format", "Size of the long side", "") +
          group("support", "Print", "") +
          group("framing", "Framing", "") +
          '<div class="order__total">' +
            '<span class="order__total-label">Total</span>' +
            '<span class="order__total-sum"></span>' +
          "</div>" +
          '<p class="order__fine"></p>' +
          '<button class="order__buy" type="submit">Continue to payment</button>' +
          '<p class="order__error" role="alert" hidden></p>' +
          '<p class="order__ask">Something else in mind? ' +
            '<a href="mailto:' + shop.email + '">Write to me</a>.</p>' +
        "</form>" +
      "</div>";

    host.appendChild(el);

    var elPlate = el.querySelector(".order__plate");
    var elTitle = el.querySelector(".order__title");
    var elSum = el.querySelector(".order__total-sum");
    var elFine = el.querySelector(".order__fine");
    var elError = el.querySelector(".order__error");
    var elBuy = el.querySelector(".order__buy");
    var form = el.querySelector(".order__form");
    var slots = {
      format: el.querySelector('[data-group="format"]'),
      support: el.querySelector('[data-group="support"]'),
      framing: el.querySelector('[data-group="framing"]')
    };

    /* The framing choices depend on the print, and a price depends on all
       three, so every render redraws the lot from `state`. Cheap, and it
       makes an impossible combination impossible to hold. */
    /* What shape this photograph is, which is what turns a long edge into
       a pair of centimetres. build.py writes the ratio onto the plate when
       it knows it, but it only knows it for the series that have a ratio
       table — so the picture itself is asked second. By the time anyone is
       ordering a print they are looking at the loaded file, and the file
       is never wrong about its own proportions. */
    function ratio(fig) {
      if (!fig) return NaN;
      var declared = parseFloat(fig.dataset.ar);
      if (isFinite(declared) && declared > 0) return declared;

      /* The plate's own thumbnail is lazy-loaded and, when an order is
         opened from the index at the top, has usually never been drawn —
         so it is asked last. The picture on screen is the one certain to
         have arrived, and it is the same photograph. */
      var shown = host.querySelector(".lightbox__img");
      var img = (shown && shown.naturalWidth) ? shown : fig.querySelector("img");
      if (img && img.naturalWidth && img.naturalHeight) {
        return img.naturalWidth / img.naturalHeight;
      }
      return NaN;
    }

    function render() {
      var ar = ratio(state.fig);

      slots.format.innerHTML = shop.formats.map(function (f) {
        var p = priceOf(f.id, state.support, state.framing);
        var dim = sides(f.edge, ar);
        return option("format", f.id, f.edge + " cm",
                      dim || "long edge", p === null ? "" : money(p));
      }).join("");

      slots.support.innerHTML = shop.supports.map(function (s) {
        return option("support", s.id, s.label, s.note, "");
      }).join("");

      slots.framing.innerHTML = shop.framings.filter(function (g) {
        return g.supports.indexOf(state.support) > -1;
      }).map(function (g) {
        return option("framing", g.id, g.label, g.note, "");
      }).join("");

      /* A framing that the newly chosen print does not take falls back to
         the first one that it does, rather than leaving a dead selection. */
      if (!el.querySelector('input[name="mb-framing"][value="' + state.framing + '"]')) {
        var first = el.querySelector('input[name="mb-framing"]');
        if (first) { state.framing = first.value; }
      }

      ["format", "support", "framing"].forEach(function (name) {
        var input = el.querySelector(
          'input[name="mb-' + name + '"][value="' + state[name] + '"]');
        if (input) {
          input.checked = true;
          input.closest(".order__opt").classList.add("is-on");
        }
      });

      var total = priceOf(state.format, state.support, state.framing);
      var ok = total !== null;
      elSum.textContent = ok ? money(total) : "—";
      elBuy.disabled = !ok;

      /* Most of what the shop sells carries its transport in the price.
         The bare paper print does not, and the buyer is told the sum here
         rather than meeting it at the till. The rule lives in shop.py and
         arrives as data, so this only has to read it. */
      var due = carriageOf(state.support, state.framing);
      elFine.textContent = [
        shop.edition,
        shop.leadTime,
        due ? "Shipping " + money(due) + ", added at checkout."
            : "Shipping included."
      ].filter(Boolean).join(" ");
    }

    function carriageOf(sid, gid) {
      var c = shop.carriage && shop.carriage[sid];
      return (c && c[gid]) || 0;
    }

    function priceOf(fid, sid, gid) {
      var f = shop.formats.filter(function (x) { return x.id === fid; })[0];
      if (!f || !f.prices[sid]) return null;
      var p = f.prices[sid][gid];
      return (p === null || p === undefined) ? null : p;
    }

    form.addEventListener("change", function (e) {
      var input = e.target;
      if (!input.name || input.name.indexOf("mb-") !== 0) return;
      var key = input.name.slice(3);
      state[key] = input.value;
      remember(key, input.value);
      hideError();
      render();
    });

    function hideError() { elError.hidden = true; elError.textContent = ""; }

    function fail(message) {
      elError.hidden = false;
      elError.innerHTML = message +
        ' You can also <a href="mailto:' + shop.email + '">order by email</a>.';
      elBuy.disabled = false;
      elBuy.textContent = "Continue to payment";
    }

    /* The browser is told the price only so it can show it. What it sends
       is the choice — size, print, framing, which photograph — and the
       server prices that again from shop.py before it charges anything. A
       page that could name its own price would be a page anyone could
       rewrite. */
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!state.fig) return;
      hideError();
      elBuy.disabled = true;
      elBuy.textContent = "Opening checkout…";

      var fig = state.fig;
      fetch(shop.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          photo: fig.dataset.id,
          title: fig.dataset.title || "",
          plate: fig.dataset.plate || "",
          series: fig.dataset.series || "",
          format: state.format,
          support: state.support,
          framing: state.framing,
          returnTo: window.location.href
        })
      }).then(function (r) {
        return r.json().then(function (data) {
          if (!r.ok) { throw new Error(data && data.error ? data.error : "Checkout is not answering."); }
          return data;
        });
      }).then(function (data) {
        if (!data.url) throw new Error("Checkout did not return an address.");
        window.location.href = data.url;
      }).catch(function (err) {
        fail(err.message || "Checkout is not answering.");
      });
    });

    el.querySelector(".order__close").addEventListener("click", hide);

    function show(fig) {
      state.fig = fig;
      elPlate.textContent = "Plate " + (fig.dataset.plate || "") +
                            " · " + (fig.dataset.series || "");
      elTitle.textContent = fig.dataset.title || "This photograph";
      hideError();
      elBuy.textContent = "Continue to payment";
      render();

      // opened before the file finished arriving: draw the sizes again
      // the moment it can say what shape it is.
      var shown = host.querySelector(".lightbox__img");
      if (shown && !shown.naturalWidth) {
        shown.addEventListener("load", function once() {
          shown.removeEventListener("load", once);
          if (state.fig === fig) render();
        });
      }

      window.clearTimeout(hiding);
      el.hidden = false;

      /* The open state is set synchronously, and only the transition is
         allowed to depend on the frame timer. Deferring the class itself
         to requestAnimationFrame looked identical on a screen someone was
         watching and failed everywhere else: in a background tab the frame
         never comes, so the panel would be up while every control still
         believed it was shut — and Escape, meaning "put this order away",
         would close the photograph instead. Reading offsetHeight flushes
         the layout so the browser still has an old state to animate from. */
      void el.offsetHeight;
      el.classList.add("is-open");
      host.classList.add("is-ordering");
      el.querySelector(".order__close").focus();
    }

    var hiding = null;
    function hide() {
      if (el.hidden) return;
      el.classList.remove("is-open");
      host.classList.remove("is-ordering");
      window.clearTimeout(hiding);
      hiding = window.setTimeout(function () { el.hidden = true; }, 420);
      var btn = host.querySelector(".lightbox__order-btn");
      if (btn) btn.focus();
    }

    return {
      el: el, show: show, hide: hide,
      isOpen: function () { return el.classList.contains("is-open"); }
    };
  }

  var openable = Array.prototype.slice.call(
    document.querySelectorAll(".plate[data-full]"));

  if (openable.length) {
    var box = null, boxImg, boxIndex, boxTitle, boxBrief, boxCount, boxPrev, boxNext;
    var at = -1, opener = null;
    var loupe, loupeBtn, order = null;

    openable.forEach(function (fig) {
      var link = fig.querySelector("[data-expand]");
      if (!link) return;
      link.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;  // let new-tab work
        e.preventDefault();
        opener = link;
        open(openable.indexOf(fig));
      });
    });

    /* The index at the top opens a plate outright rather than walking the
       visitor down to it. Choosing a thumbnail is already an act of
       choosing a picture; sending them scrolling to find it again would be
       asking them to choose it twice. Closing returns them to the
       thumbnail they came from, so the index keeps its place. */
    Array.prototype.forEach.call(
      document.querySelectorAll(".pindex__item"),
      function (link) {
        var fig = document.querySelector(link.getAttribute("href"));
        var i = openable.indexOf(fig);
        if (i < 0) return;                    // let the plain link do its job
        link.addEventListener("click", function (e) {
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
          e.preventDefault();
          opener = link;
          open(i);
        });
      }
    );

    function build() {
      box = document.createElement("div");
      box.className = "lightbox";
      box.setAttribute("role", "dialog");
      box.setAttribute("aria-modal", "true");
      box.setAttribute("aria-label", "Photograph, full screen");
      box.innerHTML =
        '<button class="lightbox__close" type="button" aria-label="Close">✕</button>' +
        '<button class="lightbox__nav lightbox__nav--prev" type="button" aria-label="Previous plate">←</button>' +
        '<button class="lightbox__nav lightbox__nav--next" type="button" aria-label="Next plate">→</button>' +
        '<div class="lightbox__stage">' +
          '<img class="lightbox__img" alt="">' +
          '<div class="lightbox__loupe" aria-hidden="true"></div>' +
        "</div>" +
        '<div class="lightbox__bar">' +
          '<p class="lightbox__index"></p>' +
          '<div class="lightbox__meta">' +
            '<p class="lightbox__count"></p>' +
            '<button class="lightbox__loupe-btn" type="button" aria-pressed="true">Loupe</button>' +
            (shop ? '<button class="lightbox__order-btn" type="button">Order a print</button>' : "") +
          "</div>" +
          '<p class="lightbox__title"></p>' +
          '<p class="lightbox__brief"></p>' +
        "</div>";
      document.body.appendChild(box);

      boxImg = box.querySelector(".lightbox__img");
      boxIndex = box.querySelector(".lightbox__index");
      boxTitle = box.querySelector(".lightbox__title");
      boxBrief = box.querySelector(".lightbox__brief");
      boxCount = box.querySelector(".lightbox__count");
      boxPrev = box.querySelector(".lightbox__nav--prev");
      boxNext = box.querySelector(".lightbox__nav--next");
      loupe = box.querySelector(".lightbox__loupe");
      loupeBtn = box.querySelector(".lightbox__loupe-btn");
      wireLoupe();

      if (shop) {
        order = makeOrder(box);
        box.querySelector(".lightbox__order-btn")
           .addEventListener("click", function () { order.show(openable[at]); });
      }

      box.querySelector(".lightbox__close").addEventListener("click", close);
      boxPrev.addEventListener("click", function () { open(at - 1); });
      boxNext.addEventListener("click", function () { open(at + 1); });
      box.addEventListener("click", function (e) {
        if (e.target !== box && !e.target.classList.contains("lightbox__stage")) return;
        if (order && order.isOpen()) { order.hide(); } else { close(); }
      });
      boxImg.addEventListener("load", function () { box.classList.add("is-ready"); });
      document.addEventListener("keydown", onBoxKey);
    }

    /* A magnifier held over the plate.
       `object-fit: contain` means the picture rarely fills its box, so the
       drawn rectangle is worked out first and the pointer is ignored outside
       it. The lens is a circle painted with the same file at a larger
       background-size, offset so that whatever is under the cursor stays
       under the cursor. Nothing is fetched that the viewer did not already
       have — this only shows detail the served file already carries. */
    var LOUPE_ON = true;
    try {
      LOUPE_ON = window.localStorage.getItem("mb-loupe") !== "off";
    } catch (e) {}

    var finePointer = !window.matchMedia ||
      window.matchMedia("(hover: hover) and (pointer: fine)").matches;

    function drawnRect() {
      var r = boxImg.getBoundingClientRect();
      var nw = boxImg.naturalWidth, nh = boxImg.naturalHeight;
      if (!nw || !nh) return null;
      var s = Math.min(r.width / nw, r.height / nh);
      var w = nw * s, h = nh * s;
      return { left: r.left + (r.width - w) / 2, top: r.top + (r.height - h) / 2,
               width: w, height: h, natural: nw };
    }

    function hideLoupe() { box.classList.remove("is-loupe"); }

    function moveLoupe(e) {
      if (!LOUPE_ON || !finePointer || !box.classList.contains("is-ready")) {
        return hideLoupe();
      }
      var d = drawnRect();
      if (!d) return hideLoupe();

      var x = e.clientX - d.left, y = e.clientY - d.top;
      if (x < 0 || y < 0 || x > d.width || y > d.height) return hideLoupe();

      // Enough to read past what the page itself shows, never so much that
      // the file runs out of detail and goes soft. A wide lens wants a
      // gentler magnification: it already covers far more of the picture.
      var zoom = Math.min(2.4, Math.max(1.6, (d.natural / d.width) * 1.05));
      var size = loupe.offsetWidth / 2;

      loupe.style.backgroundSize = (d.width * zoom) + "px " + (d.height * zoom) + "px";
      loupe.style.backgroundPosition = (size - x * zoom) + "px " + (size - y * zoom) + "px";
      loupe.style.left = (e.clientX - size) + "px";
      loupe.style.top = (e.clientY - size) + "px";
      box.classList.add("is-loupe");
    }

    function setLoupe(on) {
      LOUPE_ON = on;
      loupeBtn.setAttribute("aria-pressed", on ? "true" : "false");
      if (!on) hideLoupe();
      try { window.localStorage.setItem("mb-loupe", on ? "on" : "off"); } catch (e) {}
    }

    function wireLoupe() {
      loupeBtn.setAttribute("aria-pressed", LOUPE_ON ? "true" : "false");
      if (!finePointer) { loupeBtn.hidden = true; return; }
      var stage = box.querySelector(".lightbox__stage");
      stage.addEventListener("pointermove", moveLoupe);
      stage.addEventListener("pointerleave", hideLoupe);
      loupeBtn.addEventListener("click", function () { setLoupe(!LOUPE_ON); });
    }

    function open(i) {
      if (i < 0 || i >= openable.length) return;
      if (!box) { build(); }

      var fig = openable[i];
      at = i;

      box.classList.remove("is-ready");
      if (loupe) {
        hideLoupe();
        loupe.style.backgroundImage = 'url("' + fig.dataset.full + '")';
      }
      boxImg.src = fig.dataset.full;
      boxImg.alt = fig.querySelector("img") ? fig.querySelector("img").alt : "";
      boxIndex.textContent = "Plate " + fig.dataset.plate + " · " + fig.dataset.series;
      boxTitle.textContent = fig.dataset.title || "";
      boxBrief.textContent = fig.dataset.brief || "";
      boxCount.textContent = (i + 1) + " / " + openable.length;
      boxPrev.disabled = i === 0;
      boxNext.disabled = i === openable.length - 1;

      if (!root.classList.contains("lightbox-open")) {
        root.classList.add("lightbox-open");
        box.classList.add("is-open");
        window.requestAnimationFrame(function () {
          box.querySelector(".lightbox__close").focus();
        });
      }

      [i - 1, i + 1].forEach(function (n) {          // quietly fetch the neighbours
        if (n >= 0 && n < openable.length) { new Image().src = openable[n].dataset.full; }
      });
    }

    function close() {
      if (!box || !box.classList.contains("is-open")) return;
      if (order) order.hide();
      box.classList.remove("is-open", "is-ready", "is-loupe");
      root.classList.remove("lightbox-open");
      if (opener) { opener.focus(); opener = null; }
    }

    var FOCUSABLE = "button, input, a[href], select, textarea";

    function onBoxKey(e) {
      if (!box || !box.classList.contains("is-open")) return;

      /* With the order panel up it is the panel that owns the keyboard.
         Escape backs out of the choice rather than out of the photograph,
         and the arrows stop walking the series — moving to another plate
         under a half-filled order form would quietly change what you were
         about to buy. */
      var ordering = order && order.isOpen();

      if (e.key === "Escape") { ordering ? order.hide() : close(); }
      else if (e.key === "ArrowLeft") { if (!ordering) open(at - 1); }
      else if (e.key === "ArrowRight") { if (!ordering) open(at + 1); }
      else if (e.key === "Tab") {                     // keep focus inside the viewer
        var scope = ordering ? order.el : box;
        var stops = Array.prototype.filter.call(
          scope.querySelectorAll(FOCUSABLE), function (b) {
            return !b.disabled && b.offsetParent !== null;
          });
        if (!stops.length) return;
        var first = stops[0], last = stops[stops.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
  }

  /* --- the order reference on the confirmation page -------------------
     Stripe sends the buyer back with the session id in the address. The
     last stretch of it is enough to quote in an email, and short enough to
     read aloud, so that is what the page shows. */
  var refSlot = document.querySelector("[data-order-ref]");
  if (refSlot) {
    var sid = new URLSearchParams(window.location.search).get("session_id");
    if (sid) {
      refSlot.querySelector("span").textContent = sid.slice(-12).toUpperCase();
      refSlot.hidden = false;
    }
  }

  /* --- contact form: works with no back end, upgrades with one -------- */
  var form = document.querySelector("form[data-mailto]");
  if (form) {
    form.addEventListener("submit", function (e) {
      if (form.getAttribute("action")) return;   // a real endpoint is configured
      e.preventDefault();
      var name = (form.elements.name.value || "").trim();
      var from = (form.elements.email.value || "").trim();
      var msg = (form.elements.message.value || "").trim();
      var body = msg + "\n\n\u2014 " + name + " (" + from + ")";
      window.location.href = "mailto:" + form.dataset.mailto
        + "?subject=" + encodeURIComponent("Website enquiry from " + name)
        + "&body=" + encodeURIComponent(body);
    });
  }

  /* Casual copying, discouraged.

     Right-click and drag are how a photograph gets taken by accident — a
     visitor admires it, saves it, posts it somewhere without a name on it.
     Blocking both handles that case and nothing harder: the developer
     tools, view-source, or a screenshot all still work, and no amount of
     JavaScript changes that. Treated as a speed bump, not a lock.

     Only the photographs are affected, so right-click still behaves
     normally on text and links. */
  var PROTECTED = ".plate img, .lightbox__img, .series__item img," +
                  " .about__portrait img, .bookgrid img";

  document.addEventListener("contextmenu", function (e) {
    if (e.target && e.target.closest && e.target.closest(PROTECTED)) {
      e.preventDefault();
    }
  });

  document.addEventListener("dragstart", function (e) {
    if (e.target && e.target.closest && e.target.closest(PROTECTED)) {
      e.preventDefault();
    }
  });
})();
