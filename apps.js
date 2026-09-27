(function () {
  "use strict";

  var featuredRoot = document.getElementById("work-featured");
  var caseRoot = document.getElementById("work-cases");
  var status = document.getElementById("work-status");
  var syncStatus = document.getElementById("sync-status");
  var syncLabel = document.getElementById("sync-status-label");
  var syncedAt = "";

  if (!featuredRoot || !caseRoot || !status) return;

  function relativeSyncTime(iso) {
    if (typeof iso !== "string" || !iso.trim()) return "";
    var then = Date.parse(iso);
    if (Number.isNaN(then)) return "";
    var elapsed = Date.now() - then;
    if (elapsed < 0) elapsed = 0;
    var minutes = Math.floor(elapsed / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return minutes + " min ago";
    var hours = Math.floor(minutes / 60);
    if (hours < 24) return hours === 1 ? "1 hour ago" : hours + " hours ago";
    var days = Math.floor(hours / 24);
    return days === 1 ? "1 day ago" : days + " days ago";
  }

  function renderSync(iso) {
    if (!syncStatus || !syncLabel) return;
    var when = relativeSyncTime(iso);
    var live = Boolean(when);
    syncStatus.classList.toggle("is-live", live);
    syncStatus.classList.toggle("is-unavailable", !live);
    syncStatus.hidden = false;
    syncLabel.textContent = live
      ? "Live · App Store Connect · Synced " + when
      : "Sync unavailable";
  }

  function setStatus(message) {
    status.hidden = false;
    status.textContent = message;
  }

  function storeUrl(value, appId) {
    try {
      var url = new URL(value);
      if (url.protocol !== "https:" || url.hostname !== "apps.apple.com") return "";
      if (appId && url.pathname.indexOf("id" + appId) === -1) return "";
      url.search = "";
      url.hash = "";
      return url.href;
    } catch (e) {
      return "";
    }
  }

  function iconUrl(value) {
    if (typeof value !== "string" || value.indexOf("..") !== -1) return "";
    if (/^assets\/icons\/[A-Za-z0-9._-]+$/.test(value)) return value;
    try {
      var url = new URL(value);
      var host = url.hostname;
      if (url.protocol !== "https:") return "";
      if (host !== "mzstatic.com" && host.slice(-12) !== ".mzstatic.com") return "";
      return url.href;
    } catch (e) {
      return "";
    }
  }

  function cleanText(value) {
    return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
  }

  function makeIcon(src, name, size) {
    var img = document.createElement("img");
    img.className = size === "featured" ? "featured-app-icon" : "case-icon";
    img.src = src;
    img.width = size === "featured" ? 220 : 72;
    img.height = size === "featured" ? 220 : 72;
    img.alt = name + " app icon";
    img.decoding = "async";
    if (size !== "featured") img.loading = "lazy";
    return img;
  }

  function makeStoreLink(url, label) {
    var link = document.createElement("a");
    link.className = "arrow-link";
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.appendChild(document.createTextNode(label));
    var hidden = document.createElement("span");
    hidden.className = "visually-hidden";
    hidden.textContent = " (opens in a new tab)";
    link.appendChild(hidden);
    return link;
  }

  function addMeta(list, label, value) {
    if (!value) return;
    var item = document.createElement("div");
    var term = document.createElement("dt");
    term.textContent = label;
    var detail = document.createElement("dd");
    detail.textContent = value;
    item.appendChild(term);
    item.appendChild(detail);
    list.appendChild(item);
  }

  function renderFeatured(app, index) {
    var article = document.createElement("article");
    article.className = "featured-card reveal is-visible";

    var content = document.createElement("div");
    content.className = "featured-content";

    var kicker = document.createElement("p");
    kicker.className = "project-kicker";
    kicker.textContent = index + " — Featured";

    var title = document.createElement("h3");
    title.id = "featured-heading";
    title.textContent = app.name;

    var copy = document.createElement("p");
    copy.className = "project-copy";
    copy.textContent = app.description;

    var meta = document.createElement("dl");
    meta.className = "case-meta";
    addMeta(meta, "Platform", app.platform);
    addMeta(meta, "Category", app.category);
    addMeta(meta, "Distribution", "App Store");

    content.appendChild(kicker);
    content.appendChild(title);
    content.appendChild(copy);
    content.appendChild(meta);
    content.appendChild(makeStoreLink(app.url, "View on the App Store"));

    var visual = document.createElement("div");
    visual.className = "featured-visual";
    if (app.icon) visual.appendChild(makeIcon(app.icon, app.name, "featured"));

    article.appendChild(content);
    article.appendChild(visual);
    return article;
  }

  function renderCase(app, index) {
    var article = document.createElement("article");
    article.className = "case-row reveal is-visible";

    var number = document.createElement("p");
    number.className = "case-index";
    number.textContent = index;

    var body = document.createElement("div");
    body.className = "case-body";

    var title = document.createElement("h3");
    title.textContent = app.name;
    body.appendChild(title);

    if (app.category) {
      var category = document.createElement("p");
      category.className = "case-type";
      category.textContent = app.category;
      body.appendChild(category);
    }

    var copy = document.createElement("p");
    copy.className = "case-copy";
    copy.textContent = app.description;
    body.appendChild(copy);

    if (app.icon) article.appendChild(makeIcon(app.icon, app.name, "case"));
    else {
      var spacer = document.createElement("span");
      spacer.className = "case-icon";
      spacer.setAttribute("aria-hidden", "true");
      article.appendChild(spacer);
    }

    article.insertBefore(number, article.firstChild);
    article.appendChild(body);
    article.appendChild(makeStoreLink(app.url, "App Store"));
    return article;
  }

  function normalize(entry) {
    if (!entry || typeof entry !== "object") return null;
    var id = cleanText(String(entry.id || ""));
    if (!/^\d{6,}$/.test(id)) return null;
    var name = cleanText(entry.name);
    var description = cleanText(entry.description);
    var url = storeUrl(entry.url, id);
    if (!name || !description || !url) return null;
    return {
      id: id,
      name: name,
      description: description,
      url: url,
      icon: iconUrl(entry.icon),
      category: cleanText(entry.category),
      platform: cleanText(entry.platform),
      featured: entry.featured === true
    };
  }

  function render(apps) {
    var records = [];
    apps.forEach(function (entry) {
      var app = normalize(entry);
      if (app) records.push(app);
    });

    featuredRoot.textContent = "";
    caseRoot.textContent = "";

    if (!records.length) {
      setStatus("No published apps are listed yet.");
      return;
    }

    var featured = records.find(function (app) { return app.featured; }) || records[0];
    var rest = records.filter(function (app) { return app !== featured; });
    var number = 1;

    featuredRoot.appendChild(renderFeatured(featured, String(number).padStart(2, "0")));
    rest.forEach(function (app) {
      number += 1;
      caseRoot.appendChild(renderCase(app, String(number).padStart(2, "0")));
    });

    status.hidden = true;
    status.textContent = "";
  }

  fetch(new URL("apps.json", window.location.href), { cache: "no-cache" })
    .then(function (response) {
      if (!response.ok) throw new Error("status");
      return response.json();
    })
    .then(function (data) {
      syncedAt = data && typeof data.generatedAt === "string" ? data.generatedAt : "";
      renderSync(syncedAt);
      render(Array.isArray(data && data.apps) ? data.apps : []);
    })
    .catch(function () {
      syncedAt = "";
      renderSync("");
      setStatus("Selected work is unavailable right now.");
    });

  window.setInterval(function () {
    if (syncedAt) renderSync(syncedAt);
  }, 60000);
})();
