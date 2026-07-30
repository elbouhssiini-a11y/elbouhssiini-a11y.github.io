(function () {
  "use strict";

  document.documentElement.classList.add("js");

  var header = document.querySelector(".site-header");
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("primary-nav");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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

  // Reveal anything already in the viewport immediately.
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

  // Safety net: never leave content hidden.
  window.setTimeout(function () {
    revealEls.forEach(function (el) {
      if (!el.classList.contains("is-visible")) show(el);
    });
  }, 1200);
})();
