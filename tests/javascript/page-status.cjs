const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const script = readFileSync(resolve(__dirname, "../../hugo/assets/js/page-status.js"), "utf8");
const header = "path\ttype\tmessage\n";
const local = "/page-status.tsv";
const wiki = "https://raw.githubusercontent.com/wiki/acl-org/acl-anthology/Page-status.md";

class Element {
  constructor(tag = "div") {
    this.tag = tag;
    this.children = [];
    this.hidden = true;
    this.attributes = {};
    this.listeners = {};
  }
  append(...children) {
    children.forEach(child => { child.parent = this; });
    this.children.push(...children);
  }
  remove() {
    this.parent.children = this.parent.children.filter(child => child !== this);
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
}

function setup({ path = "/events/emnlp-2026/", sources = {}, missingContainer = false } = {}) {
  const container = new Element();
  container.dataset = { pagePath: path, localSource: local, wikiSource: wiki };
  const warnings = [];
  const requests = [];
  vm.runInNewContext(script, {
    document: {
      getElementById: id => id === "page-status" && !missingContainer ? container : null,
      createElement: tag => new Element(tag),
    },
    console: { warn: (...args) => warnings.push(args) },
    fetch: (url, options) => {
      requests.push({ url, options });
      const source = sources[url] ?? header;
      if (source instanceof Error) return Promise.reject(source);
      if (typeof source !== "string") return source;
      return Promise.resolve({ ok: true, text: () => Promise.resolve(source) });
    },
  });
  return { container, warnings, requests };
}

async function settle() {
  await new Promise(resolve => setImmediate(resolve));
}

function messages(state) {
  return state.container.children.map(alert => alert.children[0].textContent);
}

test("loads both sources independently and combines matching messages", async () => {
  const state = setup({
    sources: {
      [local]: header + "/events/emnlp-2026/\tinfo\tLocal notice\n",
      [wiki]: header + "/events/emnlp-2026\twarning\tWiki notice\n",
    },
  });
  await settle();
  assert.deepEqual(messages(state), ["Local notice", "Wiki notice"]);
  assert.equal(state.container.hidden, false);
  assert.deepEqual(state.requests.map(request => request.url), [local, wiki]);
  state.requests.forEach(request => {
    assert.equal(request.options.cache, "no-cache");
    assert.equal(request.options.credentials, "omit");
  });
  assert.equal(state.container.children[1].className, "alert alert-warning alert-dismissible");
  assert.deepEqual(state.warnings, []);
});

test("matches only the canonical page path, not siblings, parents or children", async () => {
  const state = setup({
    sources: { [local]: header +
      "/events/\tinfo\tParent\n" +
      "/events/emnlp-2026/workshops/\tinfo\tChild\n" +
      "/events/EMNLP-2026/\tinfo\tWrong case\n" +
      "/events/emnlp-2026-other/\tinfo\tSibling\n" },
  });
  await settle();
  assert.deepEqual(messages(state), []);
  assert.equal(state.container.hidden, true);
});

test("normalizes trailing slashes, supports homepage, BOM and CRLF", async () => {
  const state = setup({ path: "/", sources: {
    [local]: "\uFEFFpath\ttype\tmessage\r\n/\tsuccess\tWelcome\r\n\r\n",
  } });
  await settle();
  assert.deepEqual(messages(state), ["Welcome"]);
  const event = setup({ path: "/events/emnlp-2026", sources: {
    [local]: header + "/events/emnlp-2026/\tinfo\tNotice\n",
  } });
  await settle();
  assert.deepEqual(messages(event), ["Notice"]);
});

test("deduplicates exact type/message pairs within and across sources", async () => {
  const row = "/events/emnlp-2026/\tinfo\tSame notice\n";
  const state = setup({ sources: {
    [local]: header + row + row,
    [wiki]: header + row + "/events/emnlp-2026/\twarning\tSame notice\n",
  } });
  await settle();
  assert.deepEqual(messages(state), ["Same notice", "Same notice"]);
});

test("renders messages as text and dismissal hides the empty container", async () => {
  const message = '<img src=x onerror="alert(1)"> **Not Markdown**';
  const state = setup({ sources: {
    [local]: header + "/events/emnlp-2026/\tdanger\t" + message + "\n",
  } });
  await settle();
  const alert = state.container.children[0];
  assert.equal(alert.children[0].textContent, message);
  assert.equal(alert.children[0].children.length, 0);
  assert.equal(alert.children[1].attributes["aria-label"], "Dismiss page notice");
  alert.children[1].listeners.click();
  assert.equal(state.container.children.length, 0);
  assert.equal(state.container.hidden, true);
});

test("invalid rows are diagnosed and skipped without discarding good rows", async () => {
  const invalid = [
    "https://aclanthology.org/events/emnlp-2026/\tinfo\tFull URL",
    "//example.com/\tinfo\tProtocol relative",
    "/events/emnlp-2026/?q=x\tinfo\tQuery",
    "/events/emnlp-2026/#fragment\tinfo\tFragment",
    "/events/emnlp-2026/\\x\tinfo\tBackslash",
    "/events/emnlp-2026/\tother\tUnknown type",
    "/events/emnlp-2026/\tinfo\t  ",
    "/events/emnlp-2026/\tinfo\tExtra\ttab",
    "/events/emnlp-2026/",
  ];
  const state = setup({ sources: {
    [local]: header + invalid.join("\n") + "\n/events/emnlp-2026/\tinfo\tValid\n",
  } });
  await settle();
  assert.deepEqual(messages(state), ["Valid"]);
  assert.equal(state.warnings.length, invalid.length);
  assert.match(state.warnings[0][0], /page-status.tsv at line 2/);
});

test("bad headers, HTTP failures and network failures do not block the other source", async () => {
  for (const failure of [
    "A Markdown page instead of TSV",
    Promise.resolve({ ok: false, status: 404 }),
    new Error("Network unavailable"),
  ]) {
    const state = setup({ sources: {
      [local]: failure,
      [wiki]: header + "/events/emnlp-2026/\tinfo\tWiki works\n",
    } });
    await settle();
    assert.deepEqual(messages(state), ["Wiki works"]);
    assert.equal(state.warnings.length, 1);
    assert.match(state.warnings[0][0], /Could not load page notices from \/page-status.tsv/);
  }
});

test("a pending wiki request does not delay local notices", async () => {
  const state = setup({ sources: {
    [local]: header + "/events/emnlp-2026/\tinfo\tLocal works\n",
    [wiki]: new Promise(() => {}),
  } });
  await settle();
  assert.deepEqual(messages(state), ["Local works"]);
});

test("a missing wiki page does not block local notices", async () => {
  const state = setup({ sources: {
    [local]: header + "/events/emnlp-2026/\tinfo\tLocal works\n",
    [wiki]: Promise.resolve({ ok: false, status: 404 }),
  } });
  await settle();
  assert.deepEqual(messages(state), ["Local works"]);
  assert.equal(state.warnings.length, 1);
  assert.ok(state.warnings[0][0].includes(wiki));
});

test("both sources failing leaves the notice container hidden", async () => {
  const state = setup({ sources: {
    [local]: new Error("Offline"),
    [wiki]: new Error("Offline"),
  } });
  await settle();
  assert.equal(state.container.hidden, true);
  assert.deepEqual(messages(state), []);
  assert.equal(state.warnings.length, 2);
});

test("an absent insertion point does not trigger requests", async () => {
  const state = setup({ missingContainer: true });
  await settle();
  assert.equal(state.requests.length, 0);
});
