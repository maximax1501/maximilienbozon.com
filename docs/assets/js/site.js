/* Maximilien Bozon — behaviour.
   Five jobs: move the light, run the entrance, reveal on scroll, light the
   plates, and open a plate full screen.
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
  var openable = Array.prototype.slice.call(
    document.querySelectorAll(".plate[data-full]"));

  if (openable.length) {
    var box = null, boxImg, boxIndex, boxTitle, boxBrief, boxCount, boxPrev, boxNext;
    var at = -1, opener = null;
    var loupe, loupeBtn;

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

      box.querySelector(".lightbox__close").addEventListener("click", close);
      boxPrev.addEventListener("click", function () { open(at - 1); });
      boxNext.addEventListener("click", function () { open(at + 1); });
      box.addEventListener("click", function (e) {
        if (e.target === box || e.target.classList.contains("lightbox__stage")) { close(); }
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
      box.classList.remove("is-open", "is-ready", "is-loupe");
      root.classList.remove("lightbox-open");
      if (opener) { opener.focus(); opener = null; }
    }

    function onBoxKey(e) {
      if (!box || !box.classList.contains("is-open")) return;
      if (e.key === "Escape") { close(); }
      else if (e.key === "ArrowLeft") { open(at - 1); }
      else if (e.key === "ArrowRight") { open(at + 1); }
      else if (e.key === "Tab") {                     // keep focus inside the viewer
        var stops = Array.prototype.filter.call(
          box.querySelectorAll("button"), function (b) { return !b.disabled; });
        if (!stops.length) return;
        var first = stops[0], last = stops[stops.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
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
