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

  function renderPaperList(container, checked) {
    container.replaceChildren(...page.papers.map(function (paper) {
      const item = document.createElement("div");
      const input = document.createElement("input");
      const label = document.createElement("label");
      const meta = document.createElement("small");
      item.className = "form-check";
      input.className = "form-check-input";
      input.type = "checkbox";
      input.value = paper.id;
      input.checked = checked;
      input.id = container.dataset.authorFixPapers + "-" + paper.id;
      label.className = "form-check-label";
      label.htmlFor = input.id;
      label.textContent = paper.title;
      meta.className = "text-muted ms-1";
      meta.textContent = "(" + paper.year
        + (paper.name !== page.canonicalName ? ", as " + paper.name : "") + ")";
      label.append(meta);
      const link = document.createElement("a");
      link.href = paper.url;
      link.target = "_blank";
      link.className = "ms-1 text-muted";
      link.title = "Open paper page";
      link.setAttribute("aria-label", "Open paper page for \u201c" + paper.title + "\u201d");
      link.innerHTML = '<i class="fas fa-external-link-alt fa-xs" aria-hidden="true"></i>';
      item.append(input, label, link);
      if (paper.citation) {
        new bootstrap.Tooltip(label, {
          title: paper.citation,
          placement: "top",
        });
      }
      return item;
    }));
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

  function showError(form, message) {
    const box = form.querySelector("[data-author-fix-error]");
    box.textContent = message;
    box.classList.toggle("d-none", !message);
    if (message) box.scrollIntoView({ block: "nearest", behavior: "smooth" });
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
    showError(form, "");
    window.open(url, "_blank");
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
    const pane = document.getElementById(id);
    pane.querySelector("h6").focus();
    pane.dispatchEvent(new Event("author-fix:shown"));
  }

  // ---- Verify author ----

  const verifyForm = document.getElementById("authorFixVerifyForm");
  let orcidCheck = Promise.resolve({ orcid: null });

  function initVerify() {
    const orcidInput = document.getElementById("authorFixOrcid");
    const feedback = document.getElementById("authorFixOrcidFeedback");
    const defaultFeedback = feedback.innerHTML;
    const verifyPapers = verifyForm.querySelector("[data-author-fix-papers]");
    // On a verified page all papers start ticked; on an unverified page the author picks theirs.
    renderPaperList(verifyPapers, page.verified);
    if (page.verified) {
      showPaperCounts(verifyPapers, "to keep", "to remove");
    } else {
      showPaperCounts(verifyPapers, "to move to your page", "to stay here");
      initSelectAll(document.getElementById("authorFixVerifyAll"), verifyPapers);
    }

    // ---- Name to show, when the ticked papers print it in different ways ----
    const nameField = document.getElementById("authorFixPreferredName");
    const nameOptions = nameField.querySelector("[data-author-fix-names]");
    new bootstrap.Tooltip(document.getElementById("authorFixLastNameInfo"));

    // Distinct first/last splits on the ticked papers, so "Juan Lopez Obrador"
    // split as Juan Lopez | Obrador and Juan | Lopez Obrador are separate options.
    function nameVariants() {
      const mine = new Set(selectedPapers(verifyPapers, true));
      const variants = new Map();
      page.papers.forEach(function (paper) {
        if (!mine.has(paper.id)) return;
        const key = paper.first + "\u0000" + paper.last;
        if (!variants.has(key)) variants.set(key, { first: paper.first, last: paper.last });
      });
      return Array.from(variants.values());
    }

    function renderNameOptions() {
      const checked = nameOptions.querySelector("input:checked");
      const previous = checked ? checked.value : null;
      const variants = nameVariants();
      nameField.hidden = variants.length < 2;
      nameOptions.replaceChildren(...variants.map(function (variant, index) {
        const item = document.createElement("div");
        const input = document.createElement("input");
        const label = document.createElement("label");
        const last = document.createElement("b");
        item.className = "form-check";
        input.className = "form-check-input";
        input.type = "radio";
        input.name = "authorFixPreferredName";
        input.id = "authorFixPreferredName-" + index;
        // Sent as "Last, First" so staff see the split.
        input.value = variant.first ? variant.last + ", " + variant.first : variant.last;
        input.checked = input.value === previous;
        label.className = "form-check-label";
        label.htmlFor = input.id;
        last.textContent = variant.last;
        if (variant.first) label.append(variant.first + " ");
        label.append(last);
        item.append(input, label);
        return item;
      }));
    }

    renderNameOptions();
    verifyPapers.addEventListener("change", renderNameOptions);

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
      });
    }

    function setFeedback(state, content) {
      orcidInput.classList.toggle("is-valid", state === "valid");
      orcidInput.classList.toggle("is-invalid", state === "invalid");
      feedback.className = "form-text" + (state === "invalid" ? " text-danger" : "");
      feedback.replaceChildren(...content);
    }

    function checkOrcid() {
      const raw = orcidInput.value;
      if (!raw.trim()) {
        orcidInput.classList.remove("is-valid", "is-invalid");
        feedback.className = "form-text";
        feedback.innerHTML = defaultFeedback;
        orcidCheck = Promise.resolve({ orcid: null });
        return orcidCheck;
      }
      const orcid = normalizeOrcid(raw);
      if (!orcid) {
        setFeedback("invalid", ["This is not a valid ORCID iD. It should look like 0000-0002-1825-0097."]);
        orcidCheck = Promise.resolve({ orcid: null });
        return orcidCheck;
      }
      orcidInput.value = "https://orcid.org/" + orcid;
      setFeedback(null, ["Checking whether this ORCID iD is already in the Anthology…"]);
      orcidCheck = lookupOrcid(orcid)
        .then(function (owner) {
          if (owner && owner !== page.id && page.verified) {
            // A legacy page (verified ID, no ORCID iD): staff merge it with the iD's page.
            const link = document.createElement("a");
            link.href = authorPageUrl(owner);
            link.textContent = owner;
            setFeedback("valid", [
              "This ORCID iD already has an author page: ", link,
              ". Submitting will ask staff to merge this page with it.",
            ]);
            return { orcid: orcid, owner: null, mergeWith: owner };
          }
          if (owner && owner !== page.id) {
            const link = document.createElement("a");
            const move = document.createElement("a");
            link.href = authorPageUrl(owner);
            link.textContent = owner;
            move.href = "#";
            move.textContent = "move papers from this page to it";
            move.addEventListener("click", function (event) {
              event.preventDefault();
              chooseDestination({ id: owner, name: owner });
              showPane("authorFixMove");
            });
            setFeedback("invalid", [
              "This ORCID iD already has an author page: ", link,
              ". Instead of verifying this page, ", move, ".",
            ]);
            return { orcid: orcid, owner: owner };
          }
          setFeedback("valid", ["Valid ORCID iD."]);
          return { orcid: orcid, owner: null };
        })
        .catch(function () {
          // The lookup is a convenience; staff check again when processing the issue.
          setFeedback("valid", ["Valid ORCID iD."]);
          return { orcid: orcid, owner: null };
        });
      return orcidCheck;
    }

    orcidInput.addEventListener("change", checkOrcid);

    verifyForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      const check = await checkOrcid();
      const degree = document.getElementById("authorFixDegree").value.trim();
      const openReview = document.getElementById("authorFixOpenReviewProfile").value.trim();
      const mine = selectedPapers(verifyPapers, true);
      const notMine = selectedPapers(verifyPapers, false);

      if (!check.orcid) return showError(verifyForm, "Please enter a valid ORCID iD.");
      if (check.owner) return showError(verifyForm, "This ORCID iD already has an author page; see the note under the ORCID iD field.");
      if (!degree) return showError(verifyForm, "Please enter the institution of your highest degree.");
      if (!openReview) return showError(verifyForm, "Please enter your OpenReview profile URL, or \"none\".");
      if (openReview.toLowerCase() !== "none" && !openReview.startsWith(OPENREVIEW_PROFILE_PREFIX)) {
        return showError(verifyForm, "Your OpenReview profile URL should start with " + OPENREVIEW_PROFILE_PREFIX + " (or enter \"none\").");
      }
      if (mine.length === 0) return showError(verifyForm, "Please select at least one paper that is yours.");
      const preferredName = nameField.hidden ? null : nameOptions.querySelector("input:checked");
      if (!nameField.hidden && !preferredName) return showError(verifyForm, "Please choose the name to show on your page.");

      // List whichever set of papers is shorter.
      const listMine = notMine.length > mine.length;
      const title = "Author Page: " + page.id + (check.mergeWith ? " (merge with " + check.mergeWith + ")" : "");
      openIssue(verifyForm, "02a-verify-author.yml", title, {
        author_page: page.url,
        merge_with: check.mergeWith ? authorPageUrl(check.mergeWith) : "",
        author_orcid: "https://orcid.org/" + check.orcid,
        author_highest_degree_institution: degree,
        papers_not_mine: listMine ? "" : notMine.join("\n"),
        papers_only_mine: listMine ? mine.join("\n") : "",
        preferred_name: preferredName ? preferredName.value : "",
        openreview_profile: openReview,
        notes: document.getElementById("authorFixVerifyNotes").value.trim(),
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

    // Names printed on the papers here.
    function paperNames() {
      return Array.from(new Set(page.papers.map(function (paper) { return paper.name; })));
    }

    // A destination must be known under a name like the one on some paper here,
    // and must not be an author of that paper already (e.g. a coauthor).
    function acceptsPapers(id, names) {
      return page.papers.some(function (paper) {
        return !paper.coauthors.includes(id)
          && names.some(function (name) { return namesMatch(paper.name, name); });
      });
    }

    // Papers can be selected once a destination is chosen, except those its author coauthored.
    function updatePaperList() {
      movePapers.querySelectorAll("input[type=checkbox]").forEach(function (input) {
        const paper = page.papers.find(function (paper) { return paper.id === input.value; });
        const coauthored = destination !== null && paper.coauthors.includes(destination.id);
        input.disabled = destination === null || coauthored;
        if (input.disabled) input.checked = false;
        let note = input.parentElement.querySelector("[data-author-fix-coauthor]");
        if (coauthored && !note) {
          note = document.createElement("small");
          note.className = "text-muted ms-1";
          note.dataset.authorFixCoauthor = "";
          note.textContent = "(coauthor)";
          input.labels[0].append(note);
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
        destSearch.value = person.name;
        destResults.hidden = true;
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
          refreshDestinations();
        });
        destStatus.replaceChildren("Selected: ", link, " \u00b7 ", change);
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
      // Without a query, suggest pages under the names printed on the papers.
      const queries = typed.length >= 2 ? [typed] : paperNames();
      let matches;
      try {
        const outcomes = await Promise.all(queries.map(function (query) {
          return search.findAuthors(query, page.indexBase);
        }));
        const seen = new Set();
        matches = outcomes.flatMap(function (outcome) { return outcome.matches; })
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

    document.getElementById("authorFixMove").addEventListener("author-fix:shown", refreshDestinations);
    destSearch.addEventListener("input", function () {
      if (destination) setDestination(null);
      refreshDestinations();
    });
    moveForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const papers = selectedPapers(movePapers, true);

      if (!destination) return showError(moveForm, "Please choose your verified author page first.");
      if (papers.length === 0) return showError(moveForm, "Please select at least one paper to move.");

      openIssue(moveForm, "02b-move-author-papers.yml", "Move Papers: " + page.id + " → " + destination.id, {
        source_page: page.url,
        papers_to_move: papers.length === page.papers.length ? "all" : papers.join("\n"),
        destination: authorPageUrl(destination.id),
        notes: document.getElementById("authorFixMoveNotes").value.trim(),
      });
    });
  }

  // ---- Remove papers (verified pages) ----

  // Unticked papers go to the unverified page for their name, as a move to "unverified".
  function initRemove() {
    const removeForm = document.getElementById("authorFixRemoveForm");
    const keepPapers = removeForm.querySelector("[data-author-fix-papers]");
    renderPaperList(keepPapers, true);
    showPaperCounts(keepPapers, "to keep", "to remove");

    removeForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const removed = selectedPapers(keepPapers, false);
      if (removed.length === 0) return showError(removeForm, "Please untick the papers to remove from this page.");

      openIssue(removeForm, "02b-move-author-papers.yml", "Move Papers: " + page.id + " → unverified", {
        source_page: page.url,
        papers_to_move: removed.length === page.papers.length ? "all" : removed.join("\n"),
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

  if (verifyForm) initVerify();
  if (moveForm) initMove();
  else initRemove();
  initOther();
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
