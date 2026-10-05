/* Meridian Performance — site interactions (no dependencies) */
(function () {
  "use strict";
  var doc = document.documentElement;
  doc.classList.remove("no-js");
  doc.classList.add("js");
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) doc.classList.add("reduced");
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* ---------- Nav: solid on scroll, hide on fast scroll down ---------- */
  var nav = $(".nav");
  var lastY = window.scrollY;
  function onNavScroll() {
    var y = window.scrollY;
    if (!nav) return;
    nav.classList.toggle("is-solid", y > 24);
    var menuOpen = document.body.classList.contains("menu-open");
    if (!menuOpen && y > 420 && y > lastY + 6) nav.classList.add("is-hidden");
    else if (y < lastY - 6 || y < 420) nav.classList.remove("is-hidden");
    doc.classList.toggle("nav-hidden", nav.classList.contains("is-hidden"));
    lastY = y;
  }

  /* ---------- Mobile menu ---------- */
  var toggle = $(".nav__toggle");
  var menu = $("#site-menu");
  function setMenu(open) {
    if (!toggle || !menu) return;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    menu.classList.toggle("is-open", open);
    menu.setAttribute("aria-hidden", String(!open));
    if (open) menu.removeAttribute("inert"); else menu.setAttribute("inert", "");
    document.body.classList.toggle("menu-open", open);
    if (open) { nav.classList.add("is-solid"); nav.classList.remove("is-hidden"); var first = $("a", menu); if (first) setTimeout(function () { first.focus(); }, 300); }
    else { onNavScroll(); }
  }
  if (toggle && menu) {
    menu.setAttribute("inert", "");
    toggle.addEventListener("click", function () { setMenu(toggle.getAttribute("aria-expanded") !== "true"); });
    $$("a", menu).forEach(function (a) { a.addEventListener("click", function () { setMenu(false); }); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && menu.classList.contains("is-open")) { setMenu(false); toggle.focus(); } });
    window.addEventListener("resize", function () { if (window.innerWidth > 1080 && menu.classList.contains("is-open")) setMenu(false); });
  }

  /* ---------- Reveal on scroll (content stays visible without JS) ---------- */
  var revealEls = $$(".reveal, .reveal-mask");
  if (!reduced && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    revealEls.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top < window.innerHeight * 0.98) el.classList.add("is-in"); else io.observe(el);
    });
    // Safety net: never leave content hidden
    setTimeout(function () { revealEls.forEach(function (el) { var r = el.getBoundingClientRect(); if (r.top < window.innerHeight) el.classList.add("is-in"); }); }, 2500);
  } else {
    revealEls.forEach(function (el) { el.classList.add("is-in"); });
  }

  /* ---------- Scroll-linked effects (one rAF loop) ---------- */
  var heroImg = $(".hero__media img");
  var ghost = $(".philosophy__ghost");
  var words = $$(".philosophy__statement .w");
  var statement = $(".philosophy__statement");
  var steps = $$(".step");
  var stepsWrap = $(".steps");
  var fill = $(".steps__fill");
  var needle = $(".dial__needle");
  var dialName = $(".dial__readout .name");
  var dialCount = $(".dial__readout .count b");
  var dialMarks = $$(".dial__mark");
  var stepLinks = $$(".stepper a");
  var puzzle = $$(".puzzle i");
  var puzzleWrap = $(".puzzle");
  var sun = $(".arc .sun");
  var arcWrap = $(".arc");
  var activeStep = -1;
  var ticking = false;

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function progressOf(el, startFrac, endFrac) {
    var r = el.getBoundingClientRect(), vh = window.innerHeight;
    var start = vh * startFrac, end = vh * endFrac;
    return clamp((start - r.top) / (r.height + start - end), 0, 1);
  }

  function setStep(i) {
    if (i === activeStep) return;
    activeStep = i;
    steps.forEach(function (s, k) { s.classList.toggle("is-active", k === i); s.classList.toggle("is-past", k < i); });
    if (needle) needle.style.transform = "rotate(" + (i * 90) + "deg)";
    dialMarks.forEach(function (m, k) { m.classList.toggle("on", k <= i); });
    if (dialName && steps[i]) dialName.textContent = steps[i].getAttribute("data-name");
    if (dialCount) dialCount.textContent = "0" + (i + 1);
    stepLinks.forEach(function (a, k) { a.classList.toggle("is-active", k === i); if (k === i) a.setAttribute("aria-current", "step"); else a.removeAttribute("aria-current"); });
  }

  function frame() {
    ticking = false;
    var y = window.scrollY, vh = window.innerHeight;
    onNavScroll();

    if (!reduced) {
      if (heroImg && y < vh * 1.2 && window.innerWidth > 900) heroImg.style.translate = "0 " + (y * 0.18).toFixed(1) + "px";
      if (ghost) { var gp = progressOf(ghost.parentElement, 1, 0); ghost.style.transform = "translateX(" + (-gp * 22).toFixed(2) + "%)"; }
    }

    if (words.length && statement && !reduced) {
      var p = progressOf(statement, 0.9, 0.45);
      var n = Math.round(p * words.length * 1.15);
      words.forEach(function (w, k) { w.classList.toggle("on", k < n); });
    }

    if (steps.length) {
      var idx = 0;
      steps.forEach(function (s, k) { if (s.getBoundingClientRect().top < vh * 0.55) idx = k; });
      setStep(idx);
      if (fill && stepsWrap) fill.style.setProperty("--p", progressOf(stepsWrap, 0.55, 0.5).toFixed(3));
    }

    if (puzzle.length && puzzleWrap) {
      var pp = progressOf(puzzleWrap, 0.95, 0.35);
      var on = Math.round(pp * puzzle.length);
      puzzle.forEach(function (c, k) { c.classList.toggle("on", k < on); });
    }
    if (sun && arcWrap) {
      var sp = reduced ? 1 : progressOf(arcWrap, 0.95, 0.4);
      // sun travels along the arc from east horizon to the meridian (peak)
      var t = Math.PI * (1 - sp * 0.5); // PI -> PI/2
      var cx = 320 + 260 * Math.cos(t), cy = 250 - 200 * Math.sin(t);
      sun.setAttribute("transform", "translate(" + cx.toFixed(1) + " " + cy.toFixed(1) + ")");
    }
  }
  function requestFrame() { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }
  window.addEventListener("scroll", requestFrame, { passive: true });
  window.addEventListener("resize", requestFrame);
  frame();
  if (reduced) { words.forEach(function (w) { w.classList.add("on"); }); }

  /* ---------- Coaching accordion ---------- */
  $$(".service").forEach(function (svc) {
    var btn = $(".service__trigger", svc);
    var panel = $(".service__panel", svc);
    if (!btn || !panel) return;
    btn.addEventListener("click", function () {
      var open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!open));
      svc.classList.toggle("is-open", !open);
      if (open) panel.setAttribute("inert", ""); else panel.removeAttribute("inert");
    });
    if (btn.getAttribute("aria-expanded") !== "true") panel.setAttribute("inert", "");
  });

  /* ---------- Reviews slider ---------- */
  $$(".slider").forEach(function (sl) {
    var track = $(".slider__track", sl);
    var prev = $(".slider__btn--prev", sl);
    var next = $(".slider__btn--next", sl);
    var bar = $(".slider__progress i", sl);
    var count = $(".slider__count", sl);
    var cards = $$(".rcard", track);
    if (!track || !cards.length) return;
    function step() { return cards[0].getBoundingClientRect().width + parseFloat(getComputedStyle(track).columnGap || 24); }
    function update() {
      var max = track.scrollWidth - track.clientWidth;
      var visible = Math.max(1, Math.round(track.clientWidth / step()));
      var first = Math.round(track.scrollLeft / step());
      var lastIdx = Math.min(cards.length, first + visible);
      if (prev) prev.disabled = track.scrollLeft <= 2;
      if (next) next.disabled = track.scrollLeft >= max - 2;
      if (bar) { var w = visible / cards.length; bar.style.width = (w * 100) + "%"; bar.style.transform = "translateX(" + (first / visible * 100) + "%)"; }
      if (count) count.textContent = (visible > 1 ? String(first + 1).padStart(2, "0") + "–" + String(lastIdx).padStart(2, "0") : String(first + 1).padStart(2, "0")) + " / " + String(cards.length).padStart(2, "0");
    }
    if (prev) prev.addEventListener("click", function () { track.scrollBy({ left: -step(), behavior: reduced ? "auto" : "smooth" }); });
    if (next) next.addEventListener("click", function () { track.scrollBy({ left: step(), behavior: reduced ? "auto" : "smooth" }); });
    track.addEventListener("scroll", function () { requestAnimationFrame(update); }, { passive: true });
    window.addEventListener("resize", update);
    update();
  });
  /* ---------- Blog: category filter ---------- */
  var chips = $$(".chip[data-filter]");
  if (chips.length) {
    var items = $$(".blog-list [data-category]");
    var emptyMsg = $(".blog-empty-filter");
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        var f = chip.getAttribute("data-filter");
        chips.forEach(function (c) { c.setAttribute("aria-pressed", String(c === chip)); });
        var shown = 0;
        items.forEach(function (it) {
          var on = f === "all" || it.getAttribute("data-category") === f;
          it.hidden = !on; if (on) shown++;
        });
        if (emptyMsg) emptyMsg.hidden = shown > 0;
      });
    });
  }

  /* ---------- Article: reading progress ---------- */
  var prog = $(".read-progress");
  var prose = $(".prose");
  if (prog && prose) {
    var onProg = function () {
      var r = prose.getBoundingClientRect();
      var total = r.height - window.innerHeight * 0.6;
      var p = clamp((-r.top + window.innerHeight * 0.25) / Math.max(1, total), 0, 1);
      prog.style.setProperty("--p", p.toFixed(3));
    };
    window.addEventListener("scroll", function () { requestAnimationFrame(onProg); }, { passive: true });
    onProg();
  }
})();
