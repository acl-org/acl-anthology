// "Fix author" dialog on author pages (partials/author_correction_modal.html).
// Collects a correction and opens a prefilled GitHub issue from one of two forms:
// .github/ISSUE_TEMPLATE/02a-verify-author.yml or 02b-move-author-papers.yml.
(function () {
  "use strict";

  const ISSUE_BASE = "https://github.com/acl-org/acl-anthology/issues/new";
  // GitHub rejects longer issue URLs.
  const MAX_URL_LENGTH = 8000;
  // Unverified authors with papers since this year likely submitted via OpenReview.
  const OPENREVIEW_YEAR = 2025;

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
      item.append(input, label);
      return item;
    }));
  }

  function selectedPapers(container, checked) {
    return Array.from(container.querySelectorAll("input[type=checkbox]"))
      .filter(function (input) { return input.checked === checked; })
      .map(function (input) { return input.value; });
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

  function showTab(id) {
    bootstrap.Tab.getOrCreateInstance(document.getElementById(id)).show();
  }

  // ---- Verify author tab ----

  const verifyForm = document.getElementById("authorFixVerifyForm");
  let orcidCheck = Promise.resolve({ orcid: null });

  function initVerify() {
    const orcidInput = document.getElementById("authorFixOrcid");
    const feedback = document.getElementById("authorFixOrcidFeedback");
    const defaultFeedback = feedback.innerHTML;
    const verifyPapers = verifyForm.querySelector("[data-author-fix-papers]");
    renderPaperList(verifyPapers, true);

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
              showTab("authorFixMoveTab");
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
      if (mine.length === 0) return showError(verifyForm, "Please tick at least one paper that is yours.");

      // List whichever set of papers is shorter.
      const listMine = notMine.length > mine.length;
      openIssue(verifyForm, "02a-verify-author.yml", "Author Page: " + page.id, {
        author_page: page.url,
        author_orcid: "https://orcid.org/" + check.orcid,
        author_highest_degree_institution: degree,
        papers_not_mine: listMine ? "" : notMine.join("\n"),
        papers_only_mine: listMine ? mine.join("\n") : "",
        preferred_name: document.getElementById("authorFixPreferredName").value.trim(),
        openreview_profile: openReview,
        notes: document.getElementById("authorFixVerifyNotes").value.trim(),
      });
    });
  }

  // ---- Move papers tab ----

  const moveForm = document.getElementById("authorFixMoveForm");
  const destSearch = document.getElementById("authorFixDestSearch");
  const destResults = document.getElementById("authorFixDestResults");
  const destStatus = document.getElementById("authorFixDestStatus");
  const destDefaultStatus = destStatus.textContent;
  let destination = null;

  function chooseDestination(person) {
    destination = person;
    document.getElementById("authorFixDestExisting").checked = true;
    destSearch.value = person.name;
    destResults.hidden = true;
    destStatus.replaceChildren("Selected: ");
    const link = document.createElement("a");
    link.href = authorPageUrl(person.id);
    link.target = "_blank";
    link.textContent = person.id;
    destStatus.append(link);
  }

  function initMove() {
    const movePapers = moveForm.querySelector("[data-author-fix-papers]");
    const moveAll = document.getElementById("authorFixMoveAll");
    renderPaperList(movePapers, false);

    moveAll.addEventListener("change", function () {
      movePapers.querySelectorAll("input[type=checkbox]").forEach(function (input) {
        input.checked = moveAll.checked;
      });
    });
    movePapers.addEventListener("change", function () {
      const selected = selectedPapers(movePapers, true).length;
      moveAll.checked = selected === page.papers.length;
      moveAll.indeterminate = selected > 0 && selected < page.papers.length;
    });

    let searchTimer;
    let searchVersion = 0;
    destSearch.addEventListener("input", function () {
      destination = null;
      document.getElementById("authorFixDestExisting").checked = true;
      clearTimeout(searchTimer);
      searchTimer = setTimeout(async function () {
        const version = ++searchVersion;
        const query = destSearch.value.trim();
        if (query.length < 2) {
          destResults.hidden = true;
          destStatus.textContent = destDefaultStatus;
          return;
        }
        let matches;
        try {
          matches = (await search.findAuthors(query, page.indexBase)).matches;
        } catch (error) {
          if (version !== searchVersion) return;
          destResults.hidden = true;
          destStatus.textContent = "Author search is temporarily unavailable.";
          return;
        }
        if (version !== searchVersion) return;
        matches = matches.filter(function (entry) {
          return search.isVerified(entry.row) && entry.row[1] !== page.id;
        }).slice(0, 8);
        destResults.replaceChildren(...matches.map(function (entry) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "list-group-item list-group-item-action py-1";
          button.append(search.makeAuthorIdentity(entry, {
            identity: "d-flex flex-column",
            heading: "d-flex align-items-center gap-1",
            verification: "fa-xs",
          }));
          button.addEventListener("click", function () {
            chooseDestination({ id: entry.row[1], name: entry.row[0] });
          });
          return button;
        }));
        destResults.hidden = matches.length === 0;
        destStatus.textContent = matches.length === 0
          ? "No matching verified author pages." : destDefaultStatus;
      }, 120);
    });

    moveForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const papers = selectedPapers(movePapers, true);
      const toUnverified = document.getElementById("authorFixDestUnverified").checked;

      if (papers.length === 0) return showError(moveForm, "Please select at least one paper to move.");
      if (!toUnverified && !destination) return showError(moveForm, "Please search for and select the author page to move the papers to.");

      openIssue(moveForm, "02b-move-author-papers.yml",
        "Move Papers: " + page.id + " → " + (toUnverified ? "unverified" : destination.id), {
          source_page: page.url,
          papers_to_move: papers.length === page.papers.length ? "all" : papers.join("\n"),
          destination: toUnverified ? "unverified" : authorPageUrl(destination.id),
          notes: document.getElementById("authorFixMoveNotes").value.trim(),
        });
    });
  }

  // ---- Setup ----

  if (verifyForm) initVerify();
  initMove();
  modal.querySelectorAll("[data-author-fix-show-move]").forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      showTab("authorFixMoveTab");
    });
  });
  // Open on Verify unless the page already has an ORCID iD.
  modal.addEventListener("show.bs.modal", function () {
    if (!modal.querySelector(".nav-link.active")) {
      showTab(page.orcid ? "authorFixMoveTab" : "authorFixVerifyTab");
    }
  }, { once: true });

  window.aclAuthorCorrection = { normalizeOrcid: normalizeOrcid };
})();
