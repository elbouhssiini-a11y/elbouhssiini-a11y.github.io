(function () {
  "use strict";

  var THEME_KEY = "portfolio-theme";
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.documentElement.classList.add("js");

  function getPreference() {
    try {
      var stored = localStorage.getItem(THEME_KEY);
      if (stored === "light" || stored === "dark" || stored === "system") return stored;
    } catch (e) {}
    return "system";
  }

  function resolveTheme(pref) {
    if (pref === "light" || pref === "dark") return pref;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(pref) {
    var resolved = resolveTheme(pref);
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.setAttribute("data-theme-pref", pref);

    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      meta.setAttribute("content", resolved === "dark" ? "#0b0b0c" : "#f5f5f7");
    }

    var select = document.getElementById("theme-select");
    if (select && select.value !== pref) select.value = pref;
  }

  function setPreference(pref) {
    try {
      localStorage.setItem(THEME_KEY, pref);
    } catch (e) {}
    applyTheme(pref);
  }

  // Apply immediately (also used after early head script).
  applyTheme(getPreference());

  var media = window.matchMedia("(prefers-color-scheme: dark)");
  function onSystemChange() {
    if (getPreference() === "system") applyTheme("system");
  }
  if (media.addEventListener) media.addEventListener("change", onSystemChange);
  else if (media.addListener) media.addListener(onSystemChange);

  function initThemeControl() {
    var select = document.getElementById("theme-select");
    if (!select) return;
    select.value = getPreference();
    select.addEventListener("change", function () {
      setPreference(select.value);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initThemeControl);
  } else {
    initThemeControl();
  }

  var header = document.querySelector(".site-header");
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("primary-nav");

  function onScroll() {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 8);
  }

  function closeNav() {
    if (!toggle || !nav) return;
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Open menu");
    nav.classList.remove("is-open");
  }

  function openNav() {
    if (!toggle || !nav) return;
    toggle.setAttribute("aria-expanded", "true");
    toggle.setAttribute("aria-label", "Close menu");
    nav.classList.add("is-open");
  }

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var expanded = toggle.getAttribute("aria-expanded") === "true";
      if (expanded) closeNav();
      else openNav();
    });

    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", closeNav);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeNav();
    });
  }

  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  var revealEls = document.querySelectorAll(".reveal");

  if (!revealEls.length) return;

  function show(el) {
    el.classList.add("is-visible");
  }

  function showAll() {
    revealEls.forEach(show);
  }

  if (reduceMotion || !("IntersectionObserver" in window)) {
    showAll();
    return;
  }

  revealEls.forEach(function (el) {
    var rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      show(el);
    }
  });

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        show(entry.target);
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.01, rootMargin: "0px 0px -8px 0px" }
  );

  revealEls.forEach(function (el) {
    if (!el.classList.contains("is-visible")) {
      observer.observe(el);
    }
  });

  window.setTimeout(function () {
    revealEls.forEach(function (el) {
      if (!el.classList.contains("is-visible")) show(el);
    });
  }, 1200);
})();
