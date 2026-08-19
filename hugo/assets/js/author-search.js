(function () {
  "use strict";

  const bucketCache = new Map();
  const numberFormat = new Intl.NumberFormat(document.documentElement.lang || "en");

  function normalize(value) {
    return value
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function compareText(left, right) {
    if (left < right) return -1;
    if (left > right) return 1;
    return 0;
  }

  function cleanQuery(value) {
    return value.trim().replace(/^https?:\/\/(?:www\.)?orcid\.org\//i, "");
  }

  function bucketFor(query) {
    const firstWordCharacter = normalize(query).match(/\w/);
    const initial = firstWordCharacter ? firstWordCharacter[0] : "";
    return initial >= "a" && initial <= "z" ? initial : "other";
  }

  function prepareAuthorRows(rows) {
    return rows.map(function (row) {
      const alternateNames = Array.isArray(row[4]) ? row[4] : row[4] ? [row[4]] : [];
      const nameVariants = Array.isArray(row[6]) ? row[6] : row[6] ? [row[6]] : [];
      const canonicalName = row[7] || row[0];
      return {
        row: row,
        name: normalize(canonicalName),
        names: [canonicalName].concat(alternateNames, nameVariants).map(normalize),
        comment: row[5] || "",
        nameVariants: nameVariants,
        searchable: normalize([row[0], row[3], canonicalName]
          .concat(alternateNames, nameVariants).join(" ")),
      };
    });
  }

  function loadAuthorBucket(indexBase, bucket) {
    const cacheKey = indexBase + bucket;
    if (!bucketCache.has(cacheKey)) {
      const request = fetch(indexBase + bucket + ".json", {
        headers: { Accept: "application/json" },
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Author index request failed");
          return response.json();
        })
        .then(prepareAuthorRows)
        .catch(function (error) {
          bucketCache.delete(cacheKey);
          throw error;
        });
      bucketCache.set(cacheKey, request);
    }
    return bucketCache.get(cacheKey);
  }

  function isVerified(row) {
    return !row[1].endsWith("/unverified");
  }

  function nameMatchRank(name, query) {
    if (name === query) return 0;
    if (name.startsWith(query)) return 1;
    if (name.split(/[\s-]+/).some(function (token) { return token.startsWith(query); })) return 2;
    return 3;
  }

  function authorMatchRank(entry, query) {
    return entry.names.reduce(function (rank, name) {
      return Math.min(rank, nameMatchRank(name, query));
    }, 3);
  }

  function authorUrl(peopleBase, personId) {
    const path = personId.split("/").map(encodeURIComponent).join("/");
    return peopleBase + path + "/";
  }

  async function findAuthors(rawQuery, indexBase) {
    const query = cleanQuery(rawQuery);
    const normalizedQuery = normalize(query);
    if (normalizedQuery.length < 2) {
      return { query: query, matches: [] };
    }

    const tokens = normalizedQuery.split(/\s+/).filter(Boolean);
    const entries = await loadAuthorBucket(indexBase, bucketFor(query));
    const matches = entries.filter(function (entry) {
      return tokens.every(function (token) { return entry.searchable.includes(token); });
    });

    matches.sort(function (left, right) {
      return authorMatchRank(left, normalizedQuery) - authorMatchRank(right, normalizedQuery)
        || Number(isVerified(right.row)) - Number(isVerified(left.row))
        || right.row[2] - left.row[2]
        || compareText(left.name, right.name)
        || compareText(left.row[1], right.row[1]);
    });

    return { query: query, matches: matches };
  }

  function makeAuthorSuggestion(entry, peopleBase) {
    const row = entry.row;
    const item = document.createElement("li");
    const link = document.createElement("a");
    const identity = document.createElement("span");
    const heading = document.createElement("span");
    const name = document.createElement("strong");
    const meta = document.createElement("small");
    const status = document.createElement("i");
    const arrow = document.createElement("i");
    const verified = isVerified(row);
    const statusLabel = verified ? "Verified author" : "Unverified author";

    link.href = authorUrl(peopleBase, row[1]);
    link.className = "acl-navbar-search__author";
    heading.className = "acl-navbar-search__author-heading";
    name.textContent = row[0];
    status.className = verified && row[3]
      ? "fab fa-orcid acl-navbar-search__verification text-verified"
      : "fas fa-question-circle acl-navbar-search__verification "
        + (verified ? "text-verified" : "text-secondary");
    status.title = statusLabel;
    status.setAttribute("aria-label", statusLabel);
    status.setAttribute("role", "img");
    arrow.className = "fas fa-arrow-right";
    arrow.setAttribute("aria-hidden", "true");

    heading.append(name, status);
    identity.append(heading);
    const detailParts = entry.comment ? [entry.comment] : [];
    const normalizedContext = normalize(row[0] + " " + entry.comment);
    entry.nameVariants.forEach(function (variant) {
      if (!normalizedContext.includes(normalize(variant))) detailParts.push(variant);
    });
    if (detailParts.length > 0) {
      meta.textContent = detailParts.join(" \u00b7 ");
      identity.append(meta);
    }
    link.append(identity, arrow);
    item.append(link);
    return item;
  }

  function makeHeading(text) {
    const item = document.createElement("li");
    item.className = "acl-navbar-search__heading";
    item.textContent = text;
    return item;
  }

  function makeNoAuthors(message) {
    const item = document.createElement("li");
    item.className = "acl-navbar-search__empty";
    item.textContent = message;
    return item;
  }

  function makeDirectoryLink(peopleBase) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    const icon = document.createElement("i");

    item.className = "acl-navbar-search__command";
    link.href = peopleBase;
    icon.className = "fas fa-users";
    icon.setAttribute("aria-hidden", "true");
    link.append(icon, "Browse all authors");
    item.append(link);
    return item;
  }

  function fullSearchUrl(form, query) {
    const url = new URL(form.action, window.location.href);
    url.searchParams.set("q", query);
    return url.toString();
  }

  function makeFullSearchLink(form, query) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    const icon = document.createElement("i");
    const label = document.createElement("span");
    const hint = document.createElement("small");
    const queryText = document.createElement("strong");

    item.className = "acl-navbar-search__command acl-navbar-search__full";
    link.href = fullSearchUrl(form, query);
    icon.className = "fas fa-search";
    icon.setAttribute("aria-hidden", "true");
    queryText.textContent = "\u201c" + query + "\u201d";
    label.append("Search all papers for ", queryText);
    hint.className = "acl-navbar-search__return-hint";
    hint.textContent = "Press Return for full search";
    label.append(hint);
    link.append(icon, label);
    item.append(link);
    return item;
  }

  function initNavbarSearch(form) {
    const input = form.querySelector(".acl-search-box");
    const results = form.querySelector("[data-navbar-author-results]");
    const status = form.querySelector("[data-navbar-author-status]");
    const resultLimit = 6;
    let inputTimer;
    let searchVersion = 0;

    function closeResults() {
      searchVersion += 1;
      results.hidden = true;
    }

    function navigationDirection(event) {
      if (event.key === "ArrowDown" || (event.ctrlKey && event.key.toLowerCase() === "n")) {
        return 1;
      }
      if (event.key === "ArrowUp" || (event.ctrlKey && event.key.toLowerCase() === "p")) {
        return -1;
      }
      return 0;
    }

    function renderResults(query, matches, emptyMessage) {
      const visibleMatches = matches.slice(0, resultLimit);
      const children = [makeFullSearchLink(form, query), makeHeading("Author matches")];

      if (visibleMatches.length === 0) {
        children.push(makeNoAuthors(emptyMessage || "No matching authors"));
      } else {
        children.push(...visibleMatches.map(function (entry) {
          return makeAuthorSuggestion(entry, form.dataset.peopleBase);
        }));
      }
      children.push(makeDirectoryLink(form.dataset.peopleBase));

      results.replaceChildren(...children);
      results.hidden = false;
      status.textContent = matches.length === 1
        ? "1 matching author. Press Return for full search."
        : numberFormat.format(matches.length) + " matching authors. Press Return for full search.";
    }

    async function search() {
      const query = input.value.trim();
      const version = ++searchVersion;
      if (normalize(cleanQuery(query)).length < 2) {
        closeResults();
        status.textContent = "";
        return;
      }

      status.textContent = "Searching authors...";
      try {
        const outcome = await findAuthors(query, form.dataset.indexBase);
        if (version !== searchVersion) return;
        renderResults(query, outcome.matches);
      } catch (error) {
        if (version !== searchVersion) return;
        renderResults(query, [], "Author suggestions unavailable");
        status.textContent = "Author suggestions are temporarily unavailable. Press Return for full search.";
      }
    }

    input.addEventListener("input", function () {
      clearTimeout(inputTimer);
      inputTimer = setTimeout(search, 120);
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeResults();
        return;
      }
      const direction = navigationDirection(event);
      if (direction === 0 || results.hidden) return;

      const links = results.querySelectorAll("a");
      const target = direction > 0 ? links[0] : links[links.length - 1];
      if (!target) return;
      event.preventDefault();
      target.focus();
    });

    results.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeResults();
        input.focus();
        return;
      }
      const direction = navigationDirection(event);
      if (direction === 0) return;

      const links = Array.from(results.querySelectorAll("a"));
      const current = links.indexOf(document.activeElement);
      if (current < 0) return;
      event.preventDefault();
      if (direction < 0 && current === 0) {
        input.focus();
      } else {
        const next = direction > 0
          ? Math.min(current + 1, links.length - 1)
          : current - 1;
        links[next].focus();
      }
    });

    document.addEventListener("focusin", function (event) {
      if (!form.contains(event.target)) closeResults();
    });

    document.addEventListener("pointerdown", function (event) {
      if (!form.contains(event.target)) closeResults();
    });

    form.addEventListener("submit", closeResults);
  }

  window.aclAuthorSearch = {
    authorUrl: authorUrl,
    cleanQuery: cleanQuery,
    findAuthors: findAuthors,
    isVerified: isVerified,
    normalize: normalize,
  };

  document.querySelectorAll("[data-navbar-author-search]").forEach(initNavbarSearch);
})();
