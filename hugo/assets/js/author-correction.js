// "Fix author" dialog on author pages (partials/author_correction_modal.html).
// Collects a correction and opens a prefilled GitHub issue from one of three forms:
// .github/ISSUE_TEMPLATE/02a-verify-author.yml, 02b-move-author-papers.yml,
// or 02c-other-author-page.yml.
(function () {
  "use strict";

  const ISSUE_BASE = "https://github.com/acl-org/acl-anthology/issues/new";
  // GitHub rejects longer issue URLs.
  const MAX_URL_LENGTH = 8000;
  // Unverified authors with papers since this year likely submitted via OpenReview.
  const OPENREVIEW_YEAR = 2025;
  const OPENREVIEW_PROFILE_PREFIX = "https://openreview.net/profile?id=~";

  const dataElement = document.getElementById("authorFixData");
  const modal = document.getElementById("authorFixModal");
  if (!dataElement || !modal) return;
  const page = JSON.parse(dataElement.textContent);
  const search = window.aclAuthorSearch;

  // ---- ORCID iDs ----

  // Accepts a bare iD or orcid.org URL, with or without hyphens; returns the
  // canonical hyphenated form, or null if malformed or the check digit is wrong.
  function normalizeOrcid(value) {
    const compact = value.trim()
      .replace(/^(?:https?:\/\/)?(?:www\.)?orcid\.org\//i, "")
      .replace(/[\s-]/g, "")
      .toUpperCase();
    if (!/^\d{15}[\dX]$/.test(compact)) return null;
    // ISO 7064 MOD 11-2
    let total = 0;
    for (const digit of compact.slice(0, 15)) total = (total + Number(digit)) * 2;
    const result = (12 - (total % 11)) % 11;
    if (compact[15] !== (result === 10 ? "X" : String(result))) return null;
    return compact.match(/.{4}/g).join("-");
  }

  const orcidShards = new Map();

  // Returns the person ID that has this ORCID iD, or null.
  function lookupOrcid(orcid) {
    const shard = orcid.slice(-1);
    if (!orcidShards.has(shard)) {
      orcidShards.set(shard, fetch(page.orcidBase + shard + ".json")
        .then(function (response) {
          if (response.status === 404) return {};
          if (!response.ok) throw new Error("ORCID index request failed");
          return response.json();
        })
        .catch(function (error) {
          orcidShards.delete(shard);
          throw error;
        }));
    }
    return orcidShards.get(shard).then(function (mapping) { return mapping[orcid] || null; });
  }

  // ---- Shared helpers ----

  function authorPageUrl(personId) {
    // Resolve against this page's permalink so links use the site's canonical host.
    return new URL(search.authorUrl(page.peopleBase, personId), page.url).toString();
  }

  const papersById = new Map(page.papers.map(function (paper) { return [paper.id, paper]; }));

  // Papers are listed in issues by their full URLs, one per line.
  function paperUrls(ids) {
    return ids.map(function (id) { return new URL(papersById.get(id).url, page.url).toString(); }).join("\n");
  }

  // Each paper gets an on/off switch (styled by .acl-author-fix-switches).
  function renderPaperItem(container, paper, checked) {
    const item = document.createElement("div");
    const input = document.createElement("input");
    const label = document.createElement("label");
    item.className = "form-check form-switch";
    input.className = "form-check-input";
    input.type = "checkbox";
    input.setAttribute("role", "switch");
    input.value = paper.id;
    input.checked = checked;
    input.id = container.dataset.authorFixPapers + "-" + paper.id;
    label.className = "form-check-label";
    label.htmlFor = input.id;
    const link = document.createElement("a");
    link.href = paper.url;
    link.target = "_blank";
    link.className = "ms-1 text-muted";
    link.title = "Open paper page";
    link.setAttribute("aria-label", "Open paper page for \u201c" + paper.title + "\u201d");
    link.innerHTML = '<i class="fas fa-external-link-alt fa-xs" aria-hidden="true"></i>';
    // Keep the link on the same line as the title's last word, however the title wraps.
    const cut = paper.title.lastIndexOf(" ") + 1;
    const tail = document.createElement("span");
    tail.className = "text-nowrap";
    tail.append(paper.title.slice(cut));
    if (paper.name !== page.canonicalName) {
      const meta = document.createElement("small");
      meta.className = "text-muted ms-1";
      meta.textContent = "(as " + paper.name + ")";
      tail.append(meta);
    }
    tail.append(link);
    label.append(paper.title.slice(0, cut), tail);
    item.append(input, label);
    if (paper.citation) {
      new bootstrap.Tooltip(label, {
        title: paper.citation,
        placement: "top",
      });
    }
    return item;
  }

  // Papers come newest first; each year's papers form a group under a year heading.
  function renderPaperList(container, checked) {
    const groups = [];
    let year = null;
    page.papers.forEach(function (paper) {
      if (paper.year !== year) {
        year = paper.year;
        const group = document.createElement("div");
        const heading = document.createElement("div");
        heading.id = container.dataset.authorFixPapers + "-year-" + groups.length;
        heading.className = "small fw-semibold text-muted" + (groups.length ? " mt-2" : "");
        heading.textContent = year;
        group.setAttribute("role", "group");
        group.setAttribute("aria-labelledby", heading.id);
        group.append(heading);
        groups.push(group);
      }
      groups[groups.length - 1].append(renderPaperItem(container, paper, checked));
    });
    container.replaceChildren(...groups);
  }

  function selectedPapers(container, checked) {
    return Array.from(container.querySelectorAll("input[type=checkbox]"))
      .filter(function (input) { return input.checked === checked; })
      .map(function (input) { return input.value; });
  }

  function paperCount(n) {
    return n + (n === 1 ? " paper" : " papers");
  }

  // Shows a running "N papers to keep · M papers to remove" line under a paper list.
  function showPaperCounts(container, tickedText, untickedText) {
    const counts = document.createElement("div");
    counts.className = "form-text mt-1";
    counts.setAttribute("aria-live", "polite");
    container.after(counts);
    function update() {
      const ticked = selectedPapers(container, true).length;
      counts.textContent = paperCount(ticked) + " " + tickedText + " · "
        + paperCount(page.papers.length - ticked) + " " + untickedText;
    }
    container.addEventListener("change", update);
    update();
  }

  // Wires a "Select all" checkbox to a paper list, skipping disabled papers. Changing
  // it fires the list's own change event, so the list's other listeners stay in sync.
  function initSelectAll(selectAll, container) {
    function enabledInputs() {
      return Array.from(container.querySelectorAll("input[type=checkbox]:not(:disabled)"));
    }
    function sync() {
      const inputs = enabledInputs();
      const selected = inputs.filter(function (input) { return input.checked; }).length;
      selectAll.checked = inputs.length > 0 && selected === inputs.length;
      selectAll.indeterminate = selected > 0 && selected < inputs.length;
    }
    selectAll.addEventListener("change", function () {
      enabledInputs().forEach(function (input) {
        input.checked = selectAll.checked;
      });
      container.dispatchEvent(new Event("change"));
    });
    container.addEventListener("change", sync);
    sync();
  }

  // Shows text and elements in the form's error box; with none, hides it.
  function showError(form, ...content) {
    const box = form.querySelector("[data-author-fix-error]");
    const shown = content.some(Boolean);
    box.replaceChildren(...content);
    box.classList.toggle("d-none", !shown);
    if (shown) box.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function openIssue(form, template, title, fields) {
    const params = new URLSearchParams({ template: template, title: title });
    Object.entries(fields).forEach(function ([key, value]) {
      if (value) params.set(key, value);
    });
    const url = ISSUE_BASE + "?" + params.toString();
    if (url.length > MAX_URL_LENGTH) {
      showError(form, "This request is too long to send to GitHub. Please select fewer papers, or open the issue on GitHub and list the papers there.");
      return;
    }
    showError(form);
    if (window.open(url, "_blank")) return;
    // Blocked as a popup (e.g. after waiting for a lookup): clicking a link always works.
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.textContent = "Open the GitHub issue";
    showError(form, "Your browser blocked the new tab. ", link, ".");
  }

  // ---- Steps: choose a kind of correction, then fill in its form ----

  const chooser = document.getElementById("authorFixChooser");
  const panes = modal.querySelectorAll("[data-author-fix-pane]");

  // Shows the form pane with this ID, or the chooser when `id` is null.
  function showPane(id) {
    chooser.classList.toggle("d-none", id !== null);
    panes.forEach(function (pane) { pane.classList.toggle("d-none", pane.id !== id); });
    if (id === null) {
      chooser.querySelector("button").focus();
      return;
    }
    document.getElementById(id).querySelector("h6").focus();
  }

  // ---- Forms that verify a person: Verify author, Create my own verified page ----
  // (fields from partials/author_correction_identity.html and author_correction_names.html)

  // A link within the dialog, e.g. to another form.
  function actionLink(text, onClick) {
    const link = document.createElement("a");
    link.href = "#";
    link.textContent = text;
    link.addEventListener("click", function (event) {
      event.preventDefault();
      onClick();
    });
    return link;
  }

  function authorPageLink(personId) {
    const link = document.createElement("a");
    link.href = authorPageUrl(personId);
    link.textContent = personId;
    return link;
  }

  // Wires the ORCID iD field `prefix + "Orcid"`: normalizes the entry, looks it up, and
  // shows the outcome under it. `interpret(orcid, owner)` turns the person ID that already
  // has the iD (or null) into a result, or a promise of one, and `describe(result)` gives
  // the feedback as [state, content]. A result with an `owner` can't be submitted.
  function initOrcidField(prefix, interpret, describe) {
    const input = document.getElementById(prefix + "Orcid");
    const feedback = document.getElementById(prefix + "OrcidFeedback");
    const defaultFeedback = feedback.innerHTML;
    let checked = null;  // {value, result} once the check of the field's `value` has finished

    function setFeedback(state, content) {
      input.classList.toggle("is-valid", state === "valid");
      input.classList.toggle("is-invalid", state === "invalid");
      feedback.className = "form-text" + (state === "invalid" ? " text-danger" : "");
      feedback.replaceChildren(...content);
    }

    // Lookups can finish out of order; only the latest check updates the form.
    let version = 0;
    function check() {
      const current = ++version;
      const raw = input.value;
      if (!raw.trim()) {
        input.classList.remove("is-valid", "is-invalid");
        feedback.className = "form-text";
        feedback.innerHTML = defaultFeedback;
        return Promise.resolve({ orcid: null });
      }
      const orcid = normalizeOrcid(raw);
      if (!orcid) {
        setFeedback("invalid", ["This is not a valid ORCID iD. It should look like 0000-0002-1825-0097."]);
        return Promise.resolve({ orcid: null });
      }
      input.value = "https://orcid.org/" + orcid;
      const value = input.value;
      setFeedback(null, ["Checking whether this ORCID iD is already in the Anthology…"]);
      return lookupOrcid(orcid)
        .then(function (owner) { return interpret(orcid, owner); })
        .catch(function () {
          // The lookup is a convenience; staff check again when processing the issue.
          return { orcid: orcid };
        })
        .then(function (result) {
          if (current === version) {
            setFeedback(...describe(result));
            checked = { value: value, result: result };
          }
          return result;
        });
    }

    input.addEventListener("change", check);
    return {
      input: input,
      check: check,
      // The finished check of the field as it is now, or null.
      checked: function () { return checked && checked.value === input.value ? checked.result : null; },
    };
  }

  // Name choice for the papers switched on in `papers`, when they print the name in more
  // than one way; `isDefault(variant)`, if given, picks the option checked at first.
  // Returns a function giving the chosen name as "Last, First" (so staff see the split),
  // "" if no choice is needed, or null if one is missing.
  function initNameOptions(prefix, papers, isDefault) {
    const field = document.getElementById(prefix + "PreferredName");
    const options = field.querySelector("[data-author-fix-names]");

    function nameValue(variant) {
      return variant.first ? variant.last + ", " + variant.first : variant.last;
    }

    // Distinct first/last splits on the switched-on papers, so "Juan Lopez Obrador"
    // split as Juan Lopez | Obrador and Juan | Lopez Obrador are separate options.
    function nameVariants() {
      const mine = new Set(selectedPapers(papers, true));
      const variants = new Map();
      page.papers.forEach(function (paper) {
        if (!mine.has(paper.id)) return;
        const key = paper.first + "\u0000" + paper.last;
        if (!variants.has(key)) variants.set(key, { first: paper.first, last: paper.last });
      });
      return Array.from(variants.values());
    }

    function render() {
      const checked = options.querySelector("input:checked");
      const previous = checked ? checked.value : null;
      const variants = nameVariants();
      field.hidden = variants.length < 2;
      // Keep the user's choice while it is still offered.
      const keepPrevious = variants.some(function (variant) { return nameValue(variant) === previous; });
      options.replaceChildren(...variants.map(function (variant, index) {
        const item = document.createElement("div");
        const input = document.createElement("input");
        const label = document.createElement("label");
        const last = document.createElement("b");
        item.className = "form-check";
        input.className = "form-check-input";
        input.type = "radio";
        input.name = prefix + "PreferredName";
        input.id = prefix + "PreferredName-" + index;
        input.value = nameValue(variant);
        input.checked = keepPrevious ? input.value === previous : Boolean(isDefault && isDefault(variant));
        label.className = "form-check-label";
        label.htmlFor = input.id;
        last.textContent = variant.last;
        if (variant.first) label.append(variant.first + " ");
        label.append(last);
        item.append(input, label);
        return item;
      }));
    }

    render();
    papers.addEventListener("change", render);
    return function chosenName() {
      if (field.hidden) return "";
      const checked = options.querySelector("input:checked");
      return checked ? checked.value : null;
    };
  }

  // Checks the fields these forms share, showing the first problem. Returns the issue
  // fields they fill in, or undefined.
  function identityIssueFields(form, prefix, check, mine, name) {
    const degree = document.getElementById(prefix + "Degree").value.trim();
    const openReview = document.getElementById(prefix + "OpenReviewProfile").value.trim();
    if (!check.orcid) return showError(form, "Please enter a valid ORCID iD.");
    if (check.owner) return showError(form, "This ORCID iD already has an author page; see the note under the ORCID iD field.");
    if (!degree) return showError(form, "Please enter the institution of your highest degree.");
    if (!openReview) return showError(form, "Please enter your OpenReview profile URL, or \"none\".");
    if (openReview.toLowerCase() !== "none" && !openReview.startsWith(OPENREVIEW_PROFILE_PREFIX)) {
      return showError(form, "Your OpenReview profile URL should start with " + OPENREVIEW_PROFILE_PREFIX + " (or enter \"none\").");
    }
    if (mine.length === 0) return showError(form, "Please switch on (✓) at least one paper that is yours.");
    if (name === null) return showError(form, "Please choose the name to show on your page.");
    return {
      author_orcid: "https://orcid.org/" + check.orcid,
      author_highest_degree_institution: degree,
      preferred_name: name,
      openreview_profile: openReview,
    };
  }

  // ---- Verify author ----

  const verifyForm = document.getElementById("authorFixVerifyForm");

  function initVerify() {
    const verifyPapers = verifyForm.querySelector("[data-author-fix-papers]");
    // On a verified page all papers start kept; on an unverified page the author
    // switches on theirs.
    renderPaperList(verifyPapers, page.verified);
    if (page.verified) {
      showPaperCounts(verifyPapers, "to keep", "to remove");
    } else {
      showPaperCounts(verifyPapers, "to move to your page", "to stay here");
      initSelectAll(document.getElementById("authorFixVerifyAll"), verifyPapers);
    }
    // A verified page starts on its current name.
    const chosenName = initNameOptions("authorFix", verifyPapers, page.verified && function (variant) {
      return variant.first === page.canonicalFirst && variant.last === page.canonicalLast;
    });

    const orcidField = initOrcidField("authorFix", function (orcid, owner) {
      if (!owner || owner === page.id) return { orcid: orcid };
      if (page.verified) return { orcid: orcid, mergeWith: owner };
      return ownerPage(orcid, owner).then(function (ownerInfo) {
        return { orcid: orcid, owner: ownerInfo };
      });
    }, function (result) {
      const otherId = result.mergeWith || (result.owner && result.owner.id);
      if (!otherId) return ["valid", ["Valid ORCID iD."]];
      const prefix = ["This ORCID iD already has an author page: ", authorPageLink(otherId)];
      const owner = result.owner;
      if (result.mergeWith) {
        // A legacy page (verified ID, no ORCID iD): staff merge it with the iD's page.
        return ["valid", [...prefix, ". Submitting will ask staff to merge this page with it."]];
      }
      if (owner.acceptsPapers) {
        const move = actionLink("move papers from this page to it", function () {
          chooseDestination({ id: owner.id, name: owner.name });
          showPane("authorFixMove");
        });
        return ["invalid", [...prefix, ". Instead of verifying this page, ", move, "."]];
      }
      const other = actionLink("Something else", function () { showPane("authorFixOther"); });
      return ["invalid", [
        ...prefix,
        ", but it can't take the papers on this page (its name doesn't match them, or its author coauthored them). Please use “",
        other, "” to describe the problem.",
      ]];
    });

    const openReviewNotice = document.getElementById("authorFixOpenReview");
    const hasRecentPaper = page.papers.some(function (paper) {
      return parseInt(paper.year, 10) >= OPENREVIEW_YEAR;
    });
    if (!page.verified && hasRecentPaper) {
      openReviewNotice.classList.remove("d-none");
      verifyForm.classList.add("d-none");
      document.getElementById("authorFixOpenReviewContinue").addEventListener("click", function () {
        openReviewNotice.classList.add("d-none");
        verifyForm.classList.remove("d-none");
        // This button is now hidden; keep focus in the dialog so Escape still closes it.
        orcidField.input.focus();
      });
    }

    // The author page that already has this ORCID iD, with its name and whether the
    // papers here could be moved to it (as the Move form's search would allow).
    function ownerPage(orcid, owner) {
      const unknown = { id: owner, name: owner, acceptsPapers: true };
      return search.findAuthors(orcid, page.indexBase)
        .then(function (outcome) {
          const entry = outcome.matches.find(function (entry) { return entry.row[1] === owner; });
          if (!entry) return unknown;
          return { id: owner, name: entry.row[0], acceptsPapers: acceptsPapers(owner, entry.names) };
        })
        .catch(function () { return unknown; });
    }

    verifyForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      // Without waiting when the field is already checked, so the new tab opens within
      // the click and isn't blocked as a popup.
      const check = orcidField.checked() || await orcidField.check();
      const mine = selectedPapers(verifyPapers, true);
      const notMine = selectedPapers(verifyPapers, false);
      const fields = identityIssueFields(verifyForm, "authorFix", check, mine, chosenName());
      if (!fields) return;

      // List whichever set of papers is shorter.
      const listMine = notMine.length > mine.length;
      const title = "Author Page: " + page.id + (check.mergeWith ? " (merge with " + check.mergeWith + ")" : "");
      openIssue(verifyForm, "02a-verify-author.yml", title, {
        author_page: page.url,
        merge_with: check.mergeWith ? authorPageUrl(check.mergeWith) : "",
        ...fields,
        papers_not_mine: listMine ? "" : paperUrls(notMine),
        papers_only_mine: listMine ? paperUrls(mine) : "",
        notes: document.getElementById("authorFixVerifyNotes").value.trim(),
      });
    });
  }

  // ---- Create my own verified page (verified pages) ----

  // A namesake of this page's author moves their papers to a new verified page. Papers
  // linked to this page by ID were assigned to its author deliberately, so they stay.
  const splitForm = document.getElementById("authorFixSplitForm");

  function initSplit() {
    const splitPapers = splitForm.querySelector("[data-author-fix-papers]");
    renderPaperList(splitPapers, false);
    splitPapers.querySelectorAll("input[type=checkbox]").forEach(function (input) {
      if (!papersById.get(input.value).linked) return;
      input.disabled = true;
      const note = document.createElement("small");
      note.className = "text-muted ms-1";
      note.tabIndex = 0;
      note.textContent = "(linked)";
      // On the title's last line, like "(coauthor)"; its tooltip replaces the citation's.
      const label = input.labels[0];
      label.querySelector("a").before(note);
      const citation = bootstrap.Tooltip.getInstance(label);
      if (citation) citation.dispose();
      new bootstrap.Tooltip(note, {
        title: "This paper is linked to " + page.id + " in the Anthology data, so it can't be moved with this form."
          + " If it isn't by " + page.canonicalName + ", please use “Something else”.",
        placement: "top",
      });
    });
    showPaperCounts(splitPapers, "to move to your new page", "to stay here");
    initSelectAll(document.getElementById("authorFixSplitAll"), splitPapers);
    const chosenName = initNameOptions("authorFixSplit", splitPapers, null);

    const orcidField = initOrcidField("authorFixSplit", function (orcid, owner) {
      return owner ? { orcid: orcid, owner: { id: owner } } : { orcid: orcid };
    }, function (result) {
      if (!result.owner) return ["valid", ["Valid ORCID iD."]];
      if (result.owner.id === page.id) {
        const remove = actionLink("Remove papers", function () { showPane("authorFixRemove"); });
        return ["invalid", ["This ORCID iD is already linked to this page. If this is your page, please use “", remove, "” instead."]];
      }
      const other = actionLink("Something else", function () { showPane("authorFixOther"); });
      return ["invalid", [
        "This ORCID iD already has an author page: ", authorPageLink(result.owner.id),
        ". To move papers from this page to it, please use “", other, "”.",
      ]];
    });

    splitForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      // As in Verify author: no waiting when the field is already checked.
      const check = orcidField.checked() || await orcidField.check();
      const mine = selectedPapers(splitPapers, true);
      const fields = identityIssueFields(splitForm, "authorFixSplit", check, mine, chosenName());
      if (!fields) return;

      openIssue(splitForm, "02d-split-verified-author.yml", "Split Author Page: " + page.id, {
        source_page: page.url,
        ...fields,
        papers_to_move: paperUrls(mine),
        notes: document.getElementById("authorFixSplitNotes").value.trim(),
      });
    });
  }

  // ---- Name matching ----

  function nameTokens(name) {
    return search.normalize(name).split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  }

  // All runs of adjacent tokens, concatenated: ["seon", "yeong"] -> also "seonyeong".
  function tokenRuns(tokens) {
    const runs = [];
    for (let start = 0; start < tokens.length; start++) {
      for (let end = start + 1; end <= tokens.length; end++) {
        runs.push(tokens.slice(start, end).join(""));
      }
    }
    return runs;
  }

  // Names match if they share a name part of two or more letters, ignoring
  // accents, case, spacing and hyphenation: "Min Wong" ~ "Seong Min",
  // "Chris Dyer" ~ "Christopher James Dyer", "Seon-yeong Woo" ~ "Seonyeong Kim".
  function namesMatch(left, right) {
    const rightRuns = new Set(tokenRuns(nameTokens(right)));
    return tokenRuns(nameTokens(left)).some(function (run) {
      return run.length >= 2 && rightRuns.has(run);
    });
  }

  // A destination must be known under a name like the one on some paper here,
  // and must not be an author of that paper already (e.g. a coauthor).
  function acceptsPapers(id, names) {
    return page.papers.some(function (paper) {
      return !paper.coauthors.includes(id)
        && names.some(function (name) { return namesMatch(paper.name, name); });
    });
  }

  // ---- Move papers (unverified pages) ----

  const moveForm = document.getElementById("authorFixMoveForm");
  const destSearch = document.getElementById("authorFixDestSearch");
  const destResults = document.getElementById("authorFixDestResults");
  const destStatus = document.getElementById("authorFixDestStatus");
  let destination = null;  // {id, name}
  // Set by initMove(); also used by the ORCID iD check to pick its owner's page.
  let chooseDestination = function () {};

  function initMove() {
    const destDefaultStatus = destStatus.textContent;
    const movePapers = moveForm.querySelector("[data-author-fix-papers]");
    const moveAll = document.getElementById("authorFixMoveAll");
    const papersHint = document.getElementById("authorFixMovePapersHint");
    renderPaperList(movePapers, false);
    showPaperCounts(movePapers, "to move", "to stay here");
    initSelectAll(moveAll, movePapers);
    // Registered before the result navigation, so the list is still open here: Escape
    // closes the list without also closing the dialog (from the search box or a
    // focused result), and Enter in the search box never submits the form.
    function keepDialogOpenOnEscape(event) {
      if (event.key === "Escape" && !destResults.hidden) event.stopPropagation();
    }
    destSearch.addEventListener("keydown", keepDialogOpenOnEscape);
    destResults.addEventListener("keydown", keepDialogOpenOnEscape);
    destSearch.addEventListener("keydown", function (event) {
      if (event.key === "Enter") event.preventDefault();
    });
    const destNavigation = search.createResultNavigation({
      input: destSearch,
      list: destResults,
      optionSelector: "button",
      activeClass: "is-active",
      onEscape: function () {
        destResults.hidden = true;
        destNavigation.refresh();
      },
    });

    // Papers can be selected once a destination is chosen, except those its author coauthored.
    function updatePaperList() {
      movePapers.querySelectorAll("input[type=checkbox]").forEach(function (input) {
        const paper = papersById.get(input.value);
        const coauthored = destination !== null && paper.coauthors.includes(destination.id);
        input.disabled = destination === null || coauthored;
        if (input.disabled) input.checked = false;
        let note = input.parentElement.querySelector("[data-author-fix-coauthor]");
        if (coauthored && !note) {
          note = document.createElement("small");
          note.className = "text-muted ms-1";
          note.dataset.authorFixCoauthor = "";
          note.textContent = "(coauthor)";
          input.labels[0].querySelector("a").before(note);
        }
        if (note) note.hidden = !coauthored;
      });
      moveAll.disabled = destination === null;
      papersHint.hidden = destination !== null;
      movePapers.dispatchEvent(new Event("change"));
    }

    function setDestination(person) {
      destination = person;
      if (person) {
        // Chosen from a focused result: hiding the list would drop focus out of the dialog.
        const focusInResults = destResults.contains(document.activeElement);
        destSearch.value = person.name;
        destResults.hidden = true;
        destNavigation.refresh();
        const link = document.createElement("a");
        link.href = authorPageUrl(person.id);
        link.target = "_blank";
        link.textContent = person.id;
        const change = document.createElement("button");
        change.type = "button";
        change.className = "btn btn-link btn-sm p-0 align-baseline";
        change.textContent = "Change";
        change.addEventListener("click", function () {
          destSearch.value = "";
          setDestination(null);
          destSearch.focus();
        });
        destStatus.replaceChildren("Selected: ", link, " \u00b7 ", change);
        if (focusInResults) change.focus();
      } else {
        destStatus.textContent = destDefaultStatus;
      }
      updatePaperList();
    }
    chooseDestination = setDestination;
    updatePaperList();

    let searchVersion = 0;
    async function searchDestinations() {
      const version = ++searchVersion;
      const typed = destSearch.value.trim();
      // Nothing is suggested until the user types.
      if (typed.length < 2) {
        destResults.hidden = true;
        destResults.replaceChildren();
        destNavigation.refresh();
        destStatus.textContent = destDefaultStatus;
        return;
      }
      let matches;
      try {
        const outcome = await search.findAuthors(typed, page.indexBase);
        const seen = new Set();
        matches = outcome.matches
          .filter(function (entry) {
            if (seen.has(entry.row[1])) return false;
            seen.add(entry.row[1]);
            return search.isVerified(entry.row) && entry.row[1] !== page.id
              && acceptsPapers(entry.row[1], entry.names);
          })
          .slice(0, 8);
      } catch (error) {
        if (version !== searchVersion) return;
        destResults.hidden = true;
        destNavigation.refresh();
        destStatus.textContent = "Author search is temporarily unavailable.";
        return;
      }
      if (version !== searchVersion || destination) return;
      destResults.replaceChildren(...matches.map(function (entry) {
        const button = document.createElement("button");
        button.type = "button";
        const details = document.createElement("small");
        const orcid = entry.row[3];
        button.className = "list-group-item list-group-item-action text-body py-1";
        // People with the same name are told apart by page ID and ORCID iD.
        details.className = "text-muted";
        details.textContent = entry.row[1] + (orcid ? " · " + orcid : "");
        button.append(search.makeAuthorIdentity(entry, {
          identity: "d-flex flex-column",
          heading: "d-flex align-items-center gap-1",
          verification: "fa-xs",
        }), details);
        button.addEventListener("click", function () {
          chooseDestination({ id: entry.row[1], name: entry.row[0] });
        });
        return button;
      }));
      destResults.hidden = matches.length === 0;
      destNavigation.refresh();
      destStatus.textContent = matches.length === 0
        ? "No verified author page (other than a coauthor's) has a name like the one on these papers. If a paper's name doesn't match its PDF, use \"Fix data\" on that paper's page first."
        : destDefaultStatus;
    }

    let searchTimer;
    function refreshDestinations() {
      if (destination) return;
      clearTimeout(searchTimer);
      searchTimer = setTimeout(searchDestinations, 120);
    }

    destSearch.addEventListener("input", function () {
      if (destination) setDestination(null);
      refreshDestinations();
    });
    moveForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const papers = selectedPapers(movePapers, true);

      if (!destination) return showError(moveForm, "Please choose your verified author page first.");
      if (papers.length === 0) return showError(moveForm, "Please switch on (\u2713) at least one paper to move.");

      openIssue(moveForm, "02b-move-author-papers.yml", "Move Papers: " + page.id + " → " + destination.id, {
        source_page: page.url,
        papers_to_move: papers.length === page.papers.length ? "all" : paperUrls(papers),
        destination: authorPageUrl(destination.id),
        notes: document.getElementById("authorFixMoveNotes").value.trim(),
      });
    });
  }

  // ---- Remove papers (verified pages) ----

  // Papers switched off go to the unverified page for their name, as a move to "unverified".
  function initRemove() {
    const removeForm = document.getElementById("authorFixRemoveForm");
    const keepPapers = removeForm.querySelector("[data-author-fix-papers]");
    renderPaperList(keepPapers, true);
    showPaperCounts(keepPapers, "to keep", "to remove");

    removeForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const removed = selectedPapers(keepPapers, false);
      if (removed.length === 0) return showError(removeForm, "Please switch off (\u2717) the papers to remove from this page.");

      openIssue(removeForm, "02b-move-author-papers.yml", "Move Papers: " + page.id + " → unverified", {
        source_page: page.url,
        papers_to_move: removed.length === page.papers.length ? "all" : paperUrls(removed),
        destination: "unverified",
        notes: document.getElementById("authorFixRemoveNotes").value.trim(),
      });
    });
  }

  // ---- Something else ----

  function initOther() {
    const otherForm = document.getElementById("authorFixOtherForm");
    otherForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const description = document.getElementById("authorFixOtherDescription").value.trim();
      if (!description) return showError(otherForm, "Please describe the problem.");
      openIssue(otherForm, "02c-other-author-page.yml", "Author Page: " + page.id, {
        author_page: page.url,
        description: description,
      });
    });
  }

  // ---- Setup ----

  // The forms (with a tooltip per paper) are built when the dialog first opens.
  modal.addEventListener("show.bs.modal", function () {
    if (verifyForm) initVerify();
    if (moveForm) initMove();
    else initRemove();
    if (splitForm) initSplit();
    initOther();
  }, { once: true });
  chooser.querySelectorAll("[data-author-fix-choose]").forEach(function (button) {
    button.addEventListener("click", function () { showPane(button.dataset.authorFixChoose); });
  });
  modal.querySelectorAll("[data-author-fix-back]").forEach(function (button) {
    button.addEventListener("click", function () { showPane(null); });
  });
  // Each opening starts from the choice; entered values are kept.
  modal.addEventListener("hidden.bs.modal", function () {
    chooser.classList.remove("d-none");
    panes.forEach(function (pane) { pane.classList.add("d-none"); });
  });

  window.aclAuthorCorrection = { namesMatch: namesMatch, normalizeOrcid: normalizeOrcid };
})();
