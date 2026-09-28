(function () {
  "use strict";

  const root = document.querySelector("[data-author-metrics]");
  if (!root) return;

  const data = JSON.parse(document.getElementById("author-metrics-data").textContent);
  const count = document.getElementById("author-metrics-count");
  const checkpoints = document.getElementById("author-metrics-checkpoints");
  const number = new Intl.NumberFormat(document.documentElement.lang || "en");
  const percent = new Intl.NumberFormat(document.documentElement.lang || "en", {
    style: "percent", maximumFractionDigits: 1,
  });
  const categories = [
    "Verified with ORCID", "Verified without ORCID",
    "Unverified with ORCID", "Unverified without ORCID",
  ];
  const total = values => values.reduce((sum, value) => sum + value, 0);
  const share = values => total(values) ? percent.format(values[0] / total(values)) : "\u2014";
  const yearLabel = year => year === 0 ? "Pre-2020" : String(year);
  const shortDate = date => date.slice(5, 7) + "/" + date.slice(2, 4);

  function svgElement(name, attributes, text) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attributes || {}).forEach(([key, value]) => element.setAttribute(key, value));
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function renderChart(container, groups, label, description) {
    if (!groups.length || groups.every(group => !group.bars.length)) {
      container.textContent = "No data is available for this selection.";
      container.hidden = false;
      return;
    }
    const left = 76, right = 60, top = 35, plotHeight = 240, bottom = 88;
    const compact = groups.every(group => group.bars.length === 1 && !group.bars[0].label);
    const groupWidths = groups.map(group => compact ? 24 : Math.max(72, group.bars.length * 18 + 20));
    const naturalWidth = total(groupWidths);
    const plotWidth = Math.max(860, naturalWidth);
    const scale = plotWidth / naturalWidth;
    const width = left + plotWidth + right;
    const height = top + plotHeight + bottom;
    const max = Math.max(1, ...groups.flatMap(group => group.bars.map(bar => total(bar.values))));
    const magnitude = Math.pow(10, Math.floor(Math.log10(max)));
    const ceiling = Math.ceil(max / magnitude) * magnitude;
    const svg = svgElement("svg", {
      viewBox: `0 0 ${width} ${height}`, width, height, role: "img",
      "aria-label": description, class: "acl-author-metrics__chart",
    });
    svg.append(svgElement("title", {}, description));
    svg.append(svgElement("text", { x: left, y: 18 }, label));
    svg.append(svgElement("text", { x: width - right, y: 18, "text-anchor": "end" }, "Verified with ORCID (%)"));
    for (let tick = 0; tick <= 4; tick++) {
      const y = top + plotHeight * (1 - tick / 4);
      svg.append(svgElement("line", { x1: left, x2: width - right, y1: y, y2: y, class: "acl-author-metrics__grid" }));
      svg.append(svgElement("text", { x: left - 8, y: y + 4, "text-anchor": "end" }, number.format(ceiling * tick / 4)));
      svg.append(svgElement("text", { x: width - right + 8, y: y + 4 }, `${tick * 25}%`));
    }
    let start = left;
    groups.forEach((group, groupIndex) => {
      const groupWidth = groupWidths[groupIndex] * scale;
      const gap = compact ? 4 : 20;
      const step = (groupWidth - gap) / group.bars.length;
      const barWidth = Math.min(38, step * 0.72);
      let points = [];
      const drawLine = () => {
        if (points.length) svg.append(svgElement("polyline", { points: points.join(" "), class: "acl-author-metrics__line" }));
        points = [];
      };
      group.bars.forEach((bar, index) => {
        const x = start + gap / 2 + step * (index + 0.5);
        const sum = total(bar.values);
        const barGroup = svgElement("g", {});
        barGroup.append(svgElement("title", {}, [
          `${group.label}, ${bar.label}: ${number.format(sum)} ${label.toLowerCase()}`,
          ...categories.map((category, i) => `${category}: ${number.format(bar.values[i])}`),
          `Verified with ORCID / total: ${share(bar.values)}`,
        ].join("\n")));
        let y = top + plotHeight;
        bar.values.forEach((value, i) => {
          const barHeight = value / ceiling * plotHeight;
          y -= barHeight;
          barGroup.append(svgElement("rect", {
            x: x - barWidth / 2, y, width: barWidth, height: barHeight,
            class: `acl-author-metrics__category-${i}`,
          }));
        });
        svg.append(barGroup);
        if (sum) {
          const pointY = top + plotHeight * (1 - bar.values[0] / sum);
          points.push(`${x},${pointY}`);
          const point = svgElement("circle", { cx: x, cy: pointY, r: 3, class: "acl-author-metrics__point" });
          point.append(svgElement("title", {}, `${group.label}, ${bar.label}: ${share(bar.values)} verified with ORCID`));
          svg.append(point);
        } else {
          // A zero denominator has no percentage; do not connect across it.
          drawLine();
        }
        if (bar.label) {
          const labelY = top + plotHeight + 12;
          svg.append(svgElement("text", {
            x, y: labelY, transform: `rotate(-55 ${x} ${labelY})`, "text-anchor": "end",
          }, bar.shortLabel || bar.label));
        }
      });
      drawLine();
      const labelX = start + groupWidth / 2;
      const labelY = compact ? top + plotHeight + 12 : height - 8;
      svg.append(svgElement("text", {
        x: labelX, y: labelY, "text-anchor": compact ? "end" : "middle",
        ...(compact ? { transform: `rotate(-55 ${labelX} ${labelY})` } : {}),
        class: "acl-author-metrics__group-label",
      }, group.label));
      start += groupWidth;
      if (!compact && groupIndex < groups.length - 1) {
        svg.append(svgElement("line", {
          x1: start, x2: start, y1: top, y2: height - 4, class: "acl-author-metrics__divider",
        }));
      }
    });
    container.replaceChildren(svg);
    container.hidden = false;
  }

  function renderTable(groups, label) {
    const body = root.querySelector("[data-metrics-table]");
    const rows = groups.flatMap(group => group.bars.map(bar => {
      const row = document.createElement("tr");
      [group.label, bar.label || "Current", ...bar.values.map(value => number.format(value)),
        number.format(total(bar.values)), share(bar.values)].forEach((value, index) => {
        const cell = document.createElement(index === 0 ? "th" : "td");
        if (index === 0) cell.scope = "row";
        cell.textContent = value;
        row.append(cell);
      });
      return row;
    }));
    body.replaceChildren(...rows);
    root.querySelector("[data-metrics-caption]").textContent =
      `${label} by publication year: ${checkpoints.options[checkpoints.selectedIndex].text}`;
  }

  function renderAuthorships() {
    const current = checkpoints.value === "current";
    const selected = current ? [data.current] : data.checkpoints.filter(checkpoint =>
      checkpoints.value === "monthly" || Number(checkpoint.date.slice(5, 7)) % 2 === 1);
    const years = [...new Set(selected.flatMap(checkpoint => checkpoint.years.map(row => row.year)))]
      .filter(year => current ? year !== 0 : year === 0 || year >= 2020)
      .sort((a, b) => a - b);
    const groups = years.map(year => ({
      label: yearLabel(year),
      bars: selected.map(checkpoint => {
        const row = checkpoint.years.find(entry => entry.year === year);
        return {
          label: current ? "" : checkpoint.date,
          shortLabel: current ? "" : shortDate(checkpoint.date),
          values: row ? row[count.value] : [0, 0, 0, 0],
        };
      }),
    }));
    const label = count.value === "authors" ? "Unique authors" : "Authorships";
    renderChart(root.querySelector("[data-authorship-chart]"), groups, label,
      `${label} by publication year and database checkpoint. Exact counts are in the following table.`);
    renderTable(groups, label);
    root.querySelector("[data-metrics-status]").textContent = current
      ? `Current database: ${label.toLowerCase()} across ${years.length} publication years. Scroll horizontally to see all years.`
      : `${selected.length} historical checkpoints, ${years.length} publication-year groups. Dates are MM/YY (the first of each month). Scroll horizontally if needed.`;
  }

  renderAuthorships();
  renderChart(root.querySelector("[data-author-growth-chart]"), [{
    label: "Database checkpoint (UTC)",
    bars: data.checkpoints.map(checkpoint => ({
      label: checkpoint.date, shortLabel: shortDate(checkpoint.date), values: checkpoint.totals,
    })),
  }], "Author pages", "Author pages at monthly checkpoints. Exact counts and source commits are in the following table.");
  root.querySelector("[data-metrics-controls]").hidden = false;
  count.addEventListener("change", renderAuthorships);
  checkpoints.addEventListener("change", renderAuthorships);
})();
