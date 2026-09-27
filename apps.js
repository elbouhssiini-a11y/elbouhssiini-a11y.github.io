(function () {
  "use strict";

  var featuredRoot = document.getElementById("work-featured");
  var caseRoot = document.getElementById("work-cases");
  var status = document.getElementById("work-status");

  if (!featuredRoot || !caseRoot || !status) return;

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

  function makeIcon(src, size) {
    var img = document.createElement("img");
    img.className = size === "featured" ? "featured-app-icon" : "case-icon";
    img.src = src;
    img.width = size === "featured" ? 220 : 72;
    img.height = size === "featured" ? 220 : 72;
    img.alt = "";
    img.decoding = "async";
    if (size !== "featured") img.loading = "lazy";
    return img;
  }

  function makeIconLink(app, size) {
    var link = document.createElement("a");
    link.className = "app-icon-link";
    link.href = app.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.appendChild(makeIcon(app.icon, size));
    var hidden = document.createElement("span");
    hidden.className = "visually-hidden";
    hidden.textContent = "View " + app.name + " on the App Store (opens in a new tab)";
    link.appendChild(hidden);
    return link;
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

  function cleanList(value) {
    if (!Array.isArray(value)) return [];
    var seen = [];
    value.forEach(function (item) {
      var text = cleanText(item);
      if (!text || text.length > 40 || seen.indexOf(text) !== -1) return;
      seen.push(text);
    });
    return seen.slice(0, 6);
  }

  function appendStudy(parent, app) {
    var facts = [];
    if (app.platform) facts.push(["Platform", app.platform]);
    if (app.role) facts.push(["Role", app.role]);
    if (app.technologies.length) facts.push(["Technologies", app.technologies.join(" · ")]);
    if (!facts.length && !app.focus) return;

    var study = document.createElement("div");
    study.className = "study";

    if (facts.length) {
      var row = document.createElement("p");
      row.className = "study-facts";
      facts.forEach(function (pair) {
        var fact = document.createElement("span");
        fact.className = "study-fact";
        var label = document.createElement("span");
        label.className = "study-kicker";
        label.textContent = pair[0];
        var value = document.createElement("span");
        value.textContent = pair[1];
        fact.appendChild(label);
        fact.appendChild(value);
        row.appendChild(fact);
      });
      study.appendChild(row);
    }

    if (app.focus) {
      var focus = document.createElement("p");
      focus.className = "study-focus";
      var label = document.createElement("span");
      label.className = "study-kicker";
      label.textContent = "Engineering focus";
      focus.appendChild(label);
      focus.appendChild(document.createTextNode(app.focus));
      study.appendChild(focus);
    }

    parent.appendChild(study);
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
    addMeta(meta, "Category", app.category);
    addMeta(meta, "Distribution", "App Store");

    content.appendChild(kicker);
    content.appendChild(title);
    content.appendChild(copy);
    appendStudy(content, app);
    content.appendChild(meta);
    content.appendChild(makeStoreLink(app.url, "View on the App Store"));

    var visual = document.createElement("div");
    visual.className = "featured-visual";
    if (app.icon) visual.appendChild(makeIconLink(app, "featured"));

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
    appendStudy(body, app);

    if (app.icon) article.appendChild(makeIconLink(app, "case"));
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
      role: cleanText(entry.role),
      focus: cleanText(entry.focus),
      technologies: cleanList(entry.technologies),
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
      render(Array.isArray(data && data.apps) ? data.apps : []);
    })
    .catch(function () {
      setStatus("Selected work is unavailable right now.");
    });
})();
