const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

class Element {
  constructor(tag = "div") {
    this.tag = tag;
    this.children = [];
    this.attributes = {};
    this.textContent = "";
    this.hidden = true;
    this.listeners = {};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
}

function setup({ addLatestMay = false } = {}) {
  const root = new Element();
  const elements = new Map();
  root.querySelector = selector => elements.get(selector);
  for (const name of ["metrics-table", "metrics-caption", "metrics-status", "metrics-controls",
    "authorship-chart", "author-growth-chart"]) {
    elements.set(`[data-${name}]`, new Element());
  }
  elements.get("[data-author-growth-chart]").clientWidth = 480;
  const row = (year, authorships, authors) => ({ year, authorships, authors });
  const snapshots = [
    { date: "2026-02-01", years: [row(0, [10, 20, 0, 70], [1, 2, 0, 7]),
      row(2026, [0, 0, 0, 0], [0, 0, 0, 0])], totals: [10, 20, 0, 70] },
    { date: "2026-03-01", years: [row(0, [20, 20, 0, 60], [2, 2, 0, 6])], totals: [20, 20, 0, 60] },
    { date: "2026-04-01", years: [row(0, [30, 20, 5, 45], [3, 2, 1, 4]),
      row(2026, [4, 2, 1, 3], [2, 1, 1, 2])], totals: [34, 22, 6, 48] },
  ];
  if (addLatestMay) {
    snapshots.push({ ...snapshots[2], date: "2026-05-01" });
  }
  const data = new Element();
  data.textContent = JSON.stringify({
    checkpoints: snapshots,
    current: { years: [row(0, [30, 20, 5, 45], [3, 2, 1, 4]),
      row(2019, [3, 2, 1, 4], [1, 1, 1, 1]), row(2026, [4, 2, 1, 3], [2, 1, 1, 2])] },
  });
  const count = new Element("select");
  count.value = "authorships";
  const checkpoints = new Element("select");
  checkpoints.value = "bimonthly";
  checkpoints.selectedIndex = 0;
  checkpoints.options = [{ text: "Every two months (plus latest)" }, { text: "Every month" }, { text: "Current database" }];
  const byId = { "author-metrics-data": data, "author-metrics-count": count, "author-metrics-checkpoints": checkpoints };
  const document = {
    documentElement: { lang: "en" },
    querySelector: () => root,
    getElementById: id => byId[id],
    createElement: tag => new Element(tag),
    createElementNS: (_, tag) => new Element(tag),
  };
  vm.runInNewContext(readFileSync(resolve(__dirname, "../../hugo/assets/js/author-metrics.js"), "utf8"), {
    document, Intl,
  });
  return { count, checkpoints, elements };
}

function table(state) {
  return state.elements.get("[data-metrics-table]").children.map(row =>
    Array.from(row.children, cell => cell.textContent));
}

test("default checkpoints, four categories, percentages and undefined denominators", () => {
  const state = setup();
  assert.deepEqual(table(state), [
    ["Pre-2020", "2026-02-01", "10", "20", "0", "70", "100", "10%"],
    ["Pre-2020", "2026-04-01", "30", "20", "5", "45", "100", "30%"],
    ["2026", "2026-02-01", "0", "0", "0", "0", "0", "\u2014"],
    ["2026", "2026-04-01", "4", "2", "1", "3", "10", "40%"],
  ]);
  const svg = state.elements.get("[data-authorship-chart]").children[0];
  const clips = svg.children[0];
  assert.equal(clips.tag, "defs");
  assert.equal(clips.children.length, 3, "only nonempty bars need rounded clipping");
  assert.ok(clips.children.every(clip => clip.children[0].attributes.d.includes(" Q ")));
  assert.equal(svg.children.filter(child => child.attributes.class === "acl-author-metrics__bar").length, 4);
  const lines = svg.children.filter(child => child.tag === "polyline");
  assert.equal(lines.length, 2, "percentage lines must not connect year groups");
  assert.equal(svg.children.filter(child => child.tag === "circle").length, 3,
    "zero denominators must not appear as zero-percent points");
  assert.equal(state.elements.get("[data-metrics-controls]").hidden, false);
});

test("unique authors use deduplicated backend values, including pre-2020", () => {
  const state = setup();
  state.count.value = "authors";
  state.count.listeners.change();
  assert.deepEqual(table(state)[0], ["Pre-2020", "2026-02-01", "1", "2", "0", "7", "10", "10%"]);
  assert.deepEqual(table(state)[3], ["2026", "2026-04-01", "2", "1", "1", "2", "6", "33.3%"]);
});

test("monthly selection includes all checkpoints and fills absent years with zero", () => {
  const state = setup();
  state.checkpoints.value = "monthly";
  state.checkpoints.selectedIndex = 1;
  state.checkpoints.listeners.change();
  assert.equal(table(state).length, 6);
  assert.deepEqual(table(state)[4], ["2026", "2026-03-01", "0", "0", "0", "0", "0", "\u2014"]);
  const growth = state.elements.get("[data-author-growth-chart]").children[0];
  assert.equal(growth.children.filter(child => child.tag === "circle").length, 3);
  const growthBars = growth.children.filter(child => child.attributes.class === "acl-author-metrics__bar");
  assert.equal(growth.children[0].children.length, 3);
  assert.ok(growthBars.every(bar => bar.children[1].attributes.width === 46));
  assert.ok(growthBars[0].children[1].attributes.x < 200,
    "the first bar should be visible without scrolling past empty plot space");
});

test("current view shows every publication year without double counting pre-2020", () => {
  const state = setup();
  state.checkpoints.value = "current";
  state.checkpoints.selectedIndex = 2;
  state.checkpoints.listeners.change();
  assert.deepEqual(table(state), [
    ["2019", "Current", "3", "2", "1", "4", "10", "30%"],
    ["2026", "Current", "4", "2", "1", "3", "10", "40%"],
  ]);
});

test("bimonthly selection includes latest odd-month checkpoint", () => {
  const state = setup({ addLatestMay: true });
  assert.deepEqual(table(state).slice(0, 3).map(row => row[1]),
    ["2026-02-01", "2026-04-01", "2026-05-01"]);
});
