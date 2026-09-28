const DATA_V = "2026-09-27a";
const DATA_DIR = "data/labels-v3/";
const X_MARK = '<svg class="xmark" viewBox="0 0 24 24" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>';
const $ = (s) => document.querySelector(s),
  NS = "http://www.w3.org/2000/svg";
const names = {
  "claude-fable-5.1": "Claude Fable 5.1",
  "claude-opus-5": "Claude Opus 5",
  "claude-opus-5.5": "Claude Opus 5.5",
  "gpt-6-sol": "GPT-6 Sol",
  "gpt-6-luna": "GPT-6 Luna",
  "grok-4.7": "Grok 4.7",
  "gpt-6-astra": "GPT-6 Astra",
  "gpt-5.6-sol": "GPT-5.6 Sol",
  "gpt-5.6-luna": "GPT-5.6 Luna",
  "muse-spark-1.3": "Muse Spark 1.3",
  "muse-spark-1.2": "Muse Spark 1.2",
  "gemini-3.8-flash": "Gemini 3.8 Flash",
  "gemini-3.7-flash": "Gemini 3.7 Flash",
  "grok-4.6": "Grok 4.6",
  "glm-5.3": "GLM 5.3",
  "glm-5.3-flash": "GLM 5.3 Flash",
  "kimi-k3": "Kimi K3",
  claude_code: "Claude Code",
  codex: "Codex",
  opencode: "OpenCode",
  pi: "Pi",
  grokbot: "Grok Bot",
  claude: '"Claude"',
  gpt: '"GPT" / ChatGPT',
  gemini: '"Gemini"',
  grok: '"Grok"',
  glm: '"GLM"',
  kimi: '"Kimi"',
  muse: '"Muse"',
};
const logos = {
  "claude-fable-5.1": "anthropic",
  "claude-opus-5": "anthropic",
  "claude-opus-5.5": "anthropic",
  "gpt-6-sol": "openai",
  "gpt-6-luna": "openai",
  "grok-4.7": "xai",
  "gpt-6-astra": "openai",
  "gpt-5.6-sol": "openai",
  "gpt-5.6-luna": "openai",
  "gemini-3.8-flash": "gemini",
  "gemini-3.7-flash": "gemini",
  "muse-spark-1.3": "meta",
  "muse-spark-1.2": "meta",
  "grok-4.6": "xai",
  "glm-5.3": "zai",
  "glm-5.3-flash": "zai",
  "kimi-k3": "moonshot",
  claude_code: "anthropic",
  codex: "openai",
  grokbot: "xai",
  claude: "anthropic",
  gpt: "openai",
  gemini: "gemini",
  grok: "xai",
  glm: "zai",
  kimi: "moonshot",
  muse: "meta",
};
const modelOrder = [
  "claude-opus-5.5",
  "claude-opus-5",
  "claude-fable-5.1",
  "gpt-6-sol",
  "gpt-6-luna",
  "gpt-6-astra",
  "gpt-5.6-sol",
  "gpt-5.6-luna",
  "grok-4.7",
  "grok-4.6",
  "gemini-3.8-flash",
  "glm-5.3",
  "glm-5.3-flash",
  "kimi-k3",
  "muse-spark-1.3",
];
const harnessAll = new Set(["claude_code", "codex", "opencode", "pi", "grokbot"]);
const harnessOrder = ["claude_code", "codex", "grokbot"];
const shownHarness = new Set(harnessOrder);
let DIMS = { model: [], harness: [] };
const dimName = (kind, id) => (DIMS[kind].find((d) => d[0] === id) || [id, id])[1];
const label = (x) =>
  names[x] ||
  String(x)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
const icon = (k) =>
  logos[k]
    ? `<img src="assets/logos/${logos[k]}.svg" alt="">`
    : '<i class="avatar-fallback" style="width:20px;height:20px"></i>';
const el = (tag, attrs = {}) => {
  const n = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
  return n;
};
const addText = (svg, x, y, t, c = "svg-label", anchor = "start") => {
  const n = el("text", { x, y, class: c, "text-anchor": anchor });
  n.textContent = t;
  svg.append(n);
  return n;
};
const fmt = (n) => new Intl.NumberFormat("en-US").format(n || 0);
const esc = (s) =>
  String(s || "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
const pts = (v) => (v == null ? "—" : `${v > 0 ? "+" : ""}${Math.round(v * 100)}`);

let EV = {};

function heroMesh() {
  const svg = $("#heroMesh");
  for (let i = 0; i <= 12; i++) {
    svg.append(
      el("path", {
        d: `M ${70 + i * 23} ${185 - i * 13} L ${350 + i * 23} ${347 - i * 13}`,
        class: "mesh-grid",
      }),
    );
  }
}

/* ---------- evidence cards ---------- */
const tag = (cls, t) => `<span class="tag ${cls}">${esc(t)}</span>`;
function card(p, kind) {
  let verdict = "",
    tags = "";
  if (kind === "sentiment") {
    const s = p.sentiment;
    tags =
      tag(s === "negative" ? "neg" : s === "mixed" ? "mix" : "", s) +
      (p.firsthand
        ? tag("fh", "firsthand")
        : p.endorsement
          ? tag("", "endorsement")
          : tag("", "stated"));
    const t0 = p.model || p.family || p.harness;
    verdict = `${icon(t0)}${esc(label(t0))} · ${esc(p.aspect || "")}`;
  } else if (kind === "preference") {
    verdict = `${icon(p.winner)}${esc(label(p.winner))} <em>&gt;</em> ${icon(p.loser)}${esc(label(p.loser))}`;
    tags =
      (p.firsthand ? tag("fh", "firsthand") : tag("", "stated")) +
      (p.aspect ? tag("", p.aspect) : "");
  } else if (kind === "switching") {
    verdict = `${icon(p.origin)}${esc(label(p.origin))} <em>→</em> ${icon(p.destination)}${esc(label(p.destination))}`;
    tags = tag("fh", "completed");
  }
  return `<a class="counted-tweet" href="${p.url}" target="_blank" rel="noreferrer"><header><span><b>${verdict}</b><small>${new Date(p.created_at).toLocaleString()}</small></span></header><p>${esc(p.text)}</p><p class="why">${esc(p.reason || "")}</p><span class="open" aria-hidden="true">${X_MARK}<i>↗</i></span></a>`;
}
const renderCards = (root, rows, kind, empty = "No counted posts.") => {
  root.innerHTML =
    rows.map((p) => card(p, kind)).join("") || `<div class="evidence-empty">${empty}</div>`;
};
const byDate = (a, b) => new Date(b.created_at) - new Date(a.created_at);

/* ---------- sentiment rows with drawers ---------- */
function spark(daily) {
  const vals = (daily || []).map((d) => d.net_sentiment);
  return `<div class="spark" aria-hidden="true">${vals.map((v, i) => (v == null ? '<i class="empty"></i>' : `<i class="${v > 0 ? "up" : v < 0 ? "down" : ""}" style="height:${Math.max(2, Math.abs(v) * 22)}px" title="day ${i + 1}: ${pts(v)}"></i>`)).join("")}</div>`;
}
function delta24(daily) {
  const d = daily || [],
    last = d[d.length - 1],
    prev = d[d.length - 2];
  if (!last || !prev || last.net_sentiment == null || prev.net_sentiment == null) return null;
  return last.net_sentiment - prev.net_sentiment;
}
function sentimentRows(root, models, evidenceRows, keyField, mode = "firsthand") {
  root.innerHTML = "";
  const list = [...(models || [])].filter(
      (m) => (m[mode] || {}).n > 0 && (keyField !== "harness" || shownHarness.has(m.model)),
    ),
    score = (m) => m[mode]?.net_sentiment ?? -9,
    size = (m) => m[mode]?.n || 0;
  list.sort((a, b) => score(b) - score(a) || size(b) - size(a));
  list.forEach((m, rank) => {
    const c = m[mode] || {},
      tot = c.n || 0,
      net = c.net_sentiment,
      netClass = net > 0.05 ? "positive" : net < -0.05 ? "negative" : "neutral",
      row = document.createElement("div");
    row.className = "sentiment-row";
    const sub = `n ${tot}`;
    const star =
      (m.firsthand?.n || 0) < 30 && !label(m.model).endsWith("*")
        ? '<span class="star">*</span>'
        : "";
    const kind = harnessOrder.includes(m.model) ? "harness" : "model",
      dm = m.dimensions || {},
      core = Object.entries(dm).filter(([k]) => k !== "overall" && k !== "other"),
      solid = core.filter(([, v]) => v.n >= 5),
      praised = solid
        .filter(([, v]) => v.positive - v.negative > 0 && v.net_sentiment >= 0.15)
        .sort((a, b) => b[1].positive - b[1].negative - (a[1].positive - a[1].negative))
        .slice(0, 2)
        .map(([k]) => dimName(kind, k).toLowerCase()),
      knocked = solid
        .filter(([, v]) => v.negative - v.positive > 0 && v.net_sentiment <= -0.1)
        .sort((a, b) => b[1].negative - b[1].positive - (a[1].negative - a[1].positive))
        .slice(0, 2)
        .map(([k]) => dimName(kind, k).toLowerCase()),
      dimsLine =
        praised.length || knocked.length
          ? `<span class="dims">${praised.length ? `<i>+</i> ${praised.join(", ")}` : ""}${praised.length && knocked.length ? " · " : ""}${knocked.length ? `<u>−</u> ${knocked.join(", ")}` : ""}</span>`
          : "";
    row.innerHTML = `<div class="sentiment-name"><strong><em class="rank">#${rank + 1}</em>${icon(m.model)}${label(m.model)}${star}</strong></div><div class="sentiment-main"><div class="stack" aria-label="${c.positive} positive, ${c.mixed} mixed, ${c.negative} negative"><span class="positive" style="width:${(c.positive / tot) * 100}%"></span><span class="mixed" style="width:${(c.mixed / tot) * 100}%"></span><span class="negative" style="width:${(c.negative / tot) * 100}%"></span></div><small class="n">${tot}</small><div class="metric-tail ${netClass}">${pts(net)}%</div></div>`;
    root.append(row);
  });
  if (!list.length)
    root.innerHTML = '<div class="evidence-empty">Nothing recorded in this mode.</div>';
}
function drawer(node, m, rows, kind) {
  const dm = m.dimensions || {},
    order = DIMS[kind].map((d) => d[0]),
    sc = order
      .filter((k) => dm[k] && dm[k].n > 0)
      .map((k) => {
        const b = dm[k],
          n = b.n,
          net = b.net_sentiment,
          cls = net > 0.05 ? "positive" : net < -0.05 ? "negative" : "neutral",
          tip = [
            ...(b.top_aspects?.positive || []).map(([t]) => "+ " + t),
            ...(b.top_aspects?.negative || []).map(([t]) => "− " + t),
          ].join("\n");
        return `<div class="score-row${n < 5 ? " thin" : ""}" title="${esc(tip)}"><span>${dimName(kind, k)}</span><div class="stack"><span class="positive" style="width:${(b.positive / n) * 100}%"></span><span class="mixed" style="width:${(b.mixed / n) * 100}%"></span><span class="negative" style="width:${(b.negative / n) * 100}%"></span></div><b class="${cls}">${pts(net)}</b><small>n${n}</small></div>`;
      })
      .join(""),
    tasks = Object.entries(m.tasks || {})
      .filter(([k]) => k !== "none")
      .sort((x, y) => y[1] - x[1])
      .slice(0, 6)
      .map(([k, v]) => `<span>${k} <b>${v}</b></span>`)
      .join("");
  node.innerHTML = `<div class="scorecard">${sc || '<div class="evidence-empty">No firsthand aspects.</div>'}</div>${tasks ? `<div class="tasks">${tasks}</div>` : ""}<div class="evidence-scroll"></div>`;
  const fh = rows.filter((r) => r.firsthand).sort(byDate),
    rest = rows.filter((r) => !r.firsthand).sort(byDate);
  renderCards(node.querySelector(".evidence-scroll"), [...fh, ...rest].slice(0, 30), "sentiment");
}

/* ---------- radar ---------- */
function radar(svg, legend, rows, kind, defaults) {
  const dims = DIMS[kind].filter((d) => d[0] !== "overall" && d[0] !== "other"),
    n = dims.length,
    cx = 280,
    cy = 284,
    R = 200,
    list = [...(rows || [])]
      .filter(
        (m) => (m.firsthand || {}).n >= 30 && (kind !== "harness" || shownHarness.has(m.model)),
      )
      .sort((a, b) => (b.firsthand.net_sentiment ?? -9) - (a.firsthand.net_sentiment ?? -9));
  const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n,
    span = kind === "harness" ? 0.6 : 1,
    rad = (v) => (R * (Math.max(-span, Math.min(span, v)) + span)) / (2 * span),
    pt = (i, v) => [cx + Math.cos(angle(i)) * rad(v), cy + Math.sin(angle(i)) * rad(v)];
  svg.innerHTML = "";
  [-1, -0.5, 0, 0.5, 1].forEach((v) => {
    const d =
      dims
        .map((_, i) => pt(i, v))
        .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
        .join(" ") + "Z";
    svg.append(el("path", { d, class: `r-ring${v === 0 ? " zero" : v === 1 ? " outer" : ""}` }));
  });
  dims.forEach(([id, name], i) => {
    const [x, y] = pt(i, 1);
    svg.append(el("line", { x1: cx, y1: cy, x2: x, y2: y, class: "r-axis" }));
    const [lx, ly] = pt(i, 1.17),
      anchor =
        Math.abs(Math.cos(angle(i))) < 0.2 ? "middle" : Math.cos(angle(i)) > 0 ? "start" : "end";
    addText(
      svg,
      lx,
      ly + 4,
      {
        limits: "Limits",
        efficiency: "Efficiency",
        dx: "Dev experience",
        agent: "Agent behaviour",
        reliability: "Reliability",
      }[id] || name,
      "r-label",
      anchor,
    );
  });
  const val = (m, id) => {
    const b = (m.dimensions || {})[id];
    return b && b.n ? { v: b.net_sentiment, n: b.n } : { v: -1, n: 0 };
  };
  const polys = new Map();
  list.forEach((m) => {
    const d =
      dims
        .map(([id], i) => {
          const { v } = val(m, id);
          return pt(i, v);
        })
        .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
        .join(" ") + "Z";
    const p = el("path", { d, class: "r-poly" });
    p.dataset.model = m.model;
    svg.append(p);
    polys.set(m.model, p);
  });
  const marks = el("g");
  svg.append(marks);
  let sel = defaults.filter((k) => polys.has(k)).slice(0, 4),
    hover = null;
  const cls = (k) => {
    const i = sel.indexOf(k);
    return `r-poly${i >= 0 ? " on p" + i : ""}${hover === k && i < 0 ? " hover" : ""}${(sel.length || hover) && i < 0 && hover !== k ? " dim" : ""}`;
  };
  function paint() {
    marks.innerHTML = "";
    polys.forEach((p, k) => p.setAttribute("class", cls(k)));
    const front = [...sel, ...(hover && !sel.includes(hover) ? [hover] : [])];
    front.forEach((k) => {
      const p = polys.get(k);
      if (p) svg.insertBefore(p, marks);
    });
    front.forEach((k) => {
      const i = sel.indexOf(k),
        m = list.find((x) => x.model === k);
      if (!m) return;
      dims.forEach(([id], di) => {
        const { v, n } = val(m, id),
          [x, y] = pt(di, v),
          c = el("circle", {
            cx: x,
            cy: y,
            r: 3.2,
            class: `r-pt ${i >= 0 ? "p" + i : "hov"}${n < 5 ? " thin" : ""}`,
          });
        const t = el("title");
        t.textContent = `${label(k)} · ${dimName(kind, id)} ${pts(v)} on ${n}`;
        c.append(t);
        marks.append(c);
      });
    });
    legend.querySelectorAll(".legend-chip").forEach((b) => {
      const i = sel.indexOf(b.dataset.model);
      b.className = `legend-chip${i >= 0 ? " on p" + i : ""}${hover === b.dataset.model ? " hov" : ""}`;
    });
    const note = legend.querySelector(".legend-note");
    if (note) note.textContent = `${sel.length}/4 selected · click a name to add or remove`;
  }
  legend.innerHTML =
    list
      .map(
        (m) =>
          `<button class="legend-chip" data-model="${m.model}"><i></i>${logos[m.model] ? `<img src="assets/logos/${logos[m.model]}.svg" alt="">` : "<b></b>"}<span>${label(m.model)}</span><small>n${m.firsthand.n}</small></button>`,
      )
      .join("") + '<p class="legend-note">click a name to add it · up to four</p>';
  legend.addEventListener("click", (e) => {
    const b = e.target.closest(".legend-chip");
    if (!b) return;
    const k = b.dataset.model;
    if (sel.includes(k)) sel = sel.filter((x) => x !== k);
    else {
      if (sel.length >= 4) sel.shift();
      sel.push(k);
    }
    paint();
  });
  legend.addEventListener("mouseover", (e) => {
    const b = e.target.closest(".legend-chip");
    if (!b || hover === b.dataset.model) return;
    hover = b.dataset.model;
    paint();
  });
  legend.addEventListener("mouseleave", () => {
    hover = null;
    paint();
  });
  paint();
}

/* ---------- aspect book: one page per model ---------- */
function book(root, models, kind, evidenceRows, keyField) {
  const list = [...(models || [])]
    .filter((m) => (m.firsthand || {}).n > 0 && (kind !== "harness" || shownHarness.has(m.model)))
    .sort((a, b) => (b.firsthand.net_sentiment ?? -9) - (a.firsthand.net_sentiment ?? -9));
  root.innerHTML = `<div class="book-picker">${list.map((m) => `<button class="pick" data-model="${m.model}">${icon(m.model)}<span>${label(m.model)}</span></button>`).join("")}</div><div class="book-stage"></div>`;
  const stage = root.querySelector(".book-stage"),
    built = new Map();
  function show(k) {
    const m = list.find((x) => x.model === k);
    if (!m) return;
    root.querySelectorAll(".pick").forEach((b) => b.classList.toggle("on", b.dataset.model === k));
    if (!built.has(k)) {
      const net = m.firsthand.net_sentiment,
        cls = net > 0.05 ? "positive" : net < -0.05 ? "negative" : "neutral",
        page = document.createElement("section");
      page.className = "book-page";
      page.innerHTML = `<header class="book-head"><div class="book-name">${icon(m.model)}<strong>${label(m.model)}</strong></div><div class="book-meta"><b class="${cls}">${pts(net)}</b><span>${m.firsthand.n} firsthand · ${m.firsthand.positive} / ${m.firsthand.mixed} / ${m.firsthand.negative}</span></div></header><div class="drawer"></div>`;
      drawer(
        page.querySelector(".drawer"),
        m,
        evidenceRows.filter((r) => r[keyField] === m.model),
        kind,
      );
      built.set(k, page);
    }
    stage.innerHTML = "";
    stage.append(built.get(k));
  }
  root.querySelector(".book-picker").onclick = (e) => {
    const b = e.target.closest(".pick");
    if (b) show(b.dataset.model);
  };
  if (list.length) show(list[0].model);
}

/* ---------- matrices and ratings ---------- */
function matrix(root, items, order, evidenceRows, evidenceRoot, labelNode, small = false) {
  const byPair = new Map((items || []).map((b) => [[...b.models].sort().join("|"), b])),
    head = order
      .map((m) => {
        const w = label(m).split(" "),
          cut = w.length > 1 ? Math.ceil(w.length / 2) : 1,
          l1 = w.slice(0, cut).join(" "),
          l2 = w.slice(cut).join(" ");
        return `<th><span class="matrix-col">${icon(m)}<span>${l1}${l2 ? `<br>${l2}` : ""}</span></span></th>`;
      })
      .join(""),
    rows = order
      .map(
        (row) =>
          `<tr><th><span class="matrix-row">${icon(row)}${label(row)}</span></th>${order
            .map((col) => {
              if (row === col) return '<td class="matrix-diagonal"></td>';
              const b = byPair.get([row, col].sort().join("|"));
              if (!b) return '<td class="matrix-empty">·</td>';
              const w = b.votes?.[row] || 0,
                l = b.votes?.[col] || 0,
                n = w + l,
                share = n ? w / n : 0.5,
                kind = w === l ? "tie" : w > l ? "lead" : "trail",
                strength = Math.min(0.32, 0.04 + n * 0.012),
                ids = (b.evidence_ids || []).join(",");
              return `<td><button class="matrix-cell ${kind}${n < 5 ? " thin" : ""}" style="--strength:${strength}" data-evidence="${ids}" data-pair="${label(row)} vs ${label(col)}" aria-label="${label(row)} ${w}, ${label(col)} ${l}"><b>${w}–${l}</b><small>${Math.round(share * 100)}% · n${n}</small></button></td>`;
            })
            .join("")}</tr>`,
      )
      .join("");
  root.innerHTML = `<table class="battle-matrix${small ? " small" : ""}"><thead><tr><th>row wins</th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
  root.onclick = (e) => {
    const cell = e.target.closest(".matrix-cell");
    if (!cell) return;
    const ids = new Set(cell.dataset.evidence.split(","));
    labelNode.textContent = `${cell.dataset.pair} · opens on X ↗`;
    renderCards(
      evidenceRoot,
      evidenceRows.filter((p) => ids.has(String(p.post_id))).sort(byDate),
      "preference",
    );
    evidenceRoot.scrollIntoView({ block: "nearest", behavior: "smooth" });
  };
}
function ratings(root, rows) {
  rows = (rows || []).filter((r) => !harnessAll.has(r.model) || shownHarness.has(r.model));
  if (!rows?.length) {
    root.innerHTML = '<div class="evidence-empty">Not enough connected comparisons.</div>';
    return;
  }
  const lo = Math.min(...rows.map((r) => r.low_95)),
    hi = Math.max(...rows.map((r) => r.high_95)),
    span = Math.max(1, hi - lo);
  root.innerHTML = [...rows]
    .sort((a, b) => b.rating - a.rating)
    .map((r, i) => {
      const l = ((r.low_95 - lo) / span) * 100,
        w = ((r.high_95 - r.low_95) / span) * 100,
        m = ((r.rating - lo) / span) * 100;
      return `<div class="rating-row"><div class="rating-name"><em class="rank">${String(i + 1).padStart(2, "0")}</em>${icon(r.model)}<span>${label(r.model)} <small style="color:var(--b48)">· ${r.votes} votes</small></span></div><div class="rating-range" aria-label="${r.rating}; interval ${r.low_95} to ${r.high_95}"><i style="left:${l}%;width:${w}%"></i><b style="left:${m}%"></b></div><strong class="rating-score">${r.rating}</strong></div>`;
    })
    .join("");
}

/* ---------- switching: two-column sankey ---------- */
function sankey(svg, items, evidenceRows, evidenceRoot, labelNode) {
  svg.innerHTML = "";
  const flows = Object.entries(items || {})
    .map(([pair, count]) => {
      const [a, b] = pair.split(" -> ");
      return { a, b, count };
    })
    .filter((f) => f.count > 0);
  if (!flows.length) {
    svg.setAttribute("viewBox", "0 0 1180 120");
    svg.style.height = "120px";
    addText(svg, 590, 65, "No completed switches", "svg-value", "middle");
    return;
  }
  const out = new Map(),
    inn = new Map();
  flows.forEach((f) => {
    out.set(f.a, (out.get(f.a) || 0) + f.count);
    inn.set(f.b, (inn.get(f.b) || 0) + f.count);
  });
  const total = flows.reduce((s, f) => s + f.count, 0);
  const L = [...out.entries()].sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0])),
    R = [...inn.entries()].sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]));
  const gap = 24,
    duelCol = svg.closest(".flow-duel") && !matchMedia("(max-width: 680px)").matches ? document.getElementById("harnessDuel") : null,
    targetH = duelCol ? (1180 * Math.max(260, duelCol.offsetHeight - 40)) / Math.max(320, svg.parentElement.clientWidth - 60) : 0,
    unit = duelCol
      ? Math.max(16, Math.min(90, (targetH - 48 - gap * Math.max(L.length, R.length)) / total))
      : Math.max(16, Math.min(26, (560 - gap * Math.max(L.length, R.length)) / total)),
    H = Math.max(200, Math.max(L.length, R.length) * gap + total * unit + 48),
    xl = 330,
    xr = 850,
    nw = 12,
    top = 24;
  svg.setAttribute("viewBox", `0 0 1180 ${H}`);
  svg.style.height = svg.closest(".flow-duel") ? "" : `${H}px`;
  svg.innerHTML =
    '<defs><pattern id="stripe-s" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#f2f2ed" stroke-width="2"/></pattern></defs>';
  const pos = (list, x, side) => {
    let y = top;
    const m = new Map();
    list.forEach(([k, n]) => {
      const h = n * unit;
      m.set(k, { y, h, cursor: y });
      svg.append(el("rect", { x, y, width: nw, height: h, class: `s-node ${side}` }));
      if (duelCol && logos[k]) {
        const S = Math.min(96, Math.max(44, h * 0.9)), yc = y + h / 2,
          ix = side === "left" ? x - 24 - S : x + nw + 24;
        svg.append(el("image", { href: `assets/logos/${logos[k]}.svg`, x: ix, y: yc - S / 2 - 10, width: S, height: S, class: "s-logo" }));
        addText(svg, ix + S / 2, yc + S / 2 + 12, label(k), "s-label s-name", "middle");
        addText(svg, side === "left" ? ix - 18 : ix + S + 18, yc + 14, `${n}`, "s-label s-count", side === "left" ? "end" : "start");
      } else if (side === "left") {
        addText(svg, x - 16, y + h / 2 + 5, `${label(k)}  ·  ${n} out`, "s-label", "end");
      } else {
        addText(svg, x + nw + 16, y + h / 2 + 5, `${label(k)}  ·  ${n} in`, "s-label");
      }
      y += h + gap;
    });
    return m;
  };
  const lm = pos(L, xl, "left"),
    rm = pos(R, xr, "right");
  flows.sort((x, y) => lm.get(x.a).y - lm.get(y.a).y || rm.get(x.b).y - rm.get(y.b).y);
  const ribbons = [];
  flows.forEach((f) => {
    const a = lm.get(f.a),
      b = rm.get(f.b),
      h = f.count * unit,
      y0 = a.cursor,
      y1 = b.cursor;
    a.cursor += h;
    b.cursor += h;
    const x0 = xl + nw,
      x1 = xr,
      cx = (x0 + x1) / 2,
      d = `M ${x0} ${y0} C ${cx} ${y0}, ${cx} ${y1}, ${x1} ${y1} L ${x1} ${y1 + h} C ${cx} ${y1 + h}, ${cx} ${y0 + h}, ${x0} ${y0 + h} Z`,
      r = el("path", { d, class: "s-ribbon" });
    r.dataset.a = f.a;
    r.dataset.b = f.b;
    r.dataset.count = f.count;
    r.dataset.mx = cx;
    r.dataset.my = (y0 + y1 + h) / 2;
    svg.append(r);
    ribbons.push(r);
  });
  const tagG = el("g", { class: "s-tag", hidden: "" }),
    tagRect = el("rect", { rx: 2, ry: 2 }),
    tagText = el("text", { "text-anchor": "middle" });
  tagG.append(tagRect, tagText);
  svg.append(tagG);
  const showTag = (r) => {
    if (!r) {
      tagG.setAttribute("hidden", "");
      return;
    }
    const n = +r.dataset.count;
    tagText.innerHTML = `<tspan class="s-tag-n">${n}</tspan><tspan class="s-tag-who" dx="14">${esc(label(r.dataset.a))} → ${esc(label(r.dataset.b))}</tspan>`;
    tagG.removeAttribute("hidden");
    const bb = tagText.getBBox(),
      padX = 18,
      padY = 12,
      x = +r.dataset.mx,
      y = +r.dataset.my;
    tagRect.setAttribute("x", x - bb.width / 2 - padX);
    tagRect.setAttribute("y", y - bb.height / 2 - padY);
    tagRect.setAttribute("width", bb.width + padX * 2);
    tagRect.setAttribute("height", bb.height + padY * 2);
    tagText.setAttribute("x", x);
    tagText.setAttribute("y", y + bb.height / 2 - 6);
  };
  svg.addEventListener("mouseover", (e) => {
    const r = e.target.closest(".s-ribbon");
    if (r) showTag(r);
  });
  svg.addEventListener("mouseleave", () => showTag(ribbons.find((x) => x.classList.contains("on"))));
  if (svg.id === "switchChart" && rm.has("grok-4.6")) {
    const wrap = svg.closest(".panel") || svg.parentElement, scroller = svg.parentElement, node = rm.get("grok-4.6"), n = R.find(([k]) => k === "grok-4.6")[1];
    let img = wrap.querySelector(".g-elon");
    if (!img) { img = document.createElement("img"); img.className = "guest g-elon"; img.src = "assets/stickers/elon.png"; img.alt = ""; wrap.append(img); }
    const place = () => {
      const sc = svg.clientWidth / 1180, yc = (node.y + (n * unit) / 2) * sc;
      const want = (xr + nw + 120) * sc, maxLeft = wrap.clientWidth - img.offsetWidth - 12;
      img.style.left = `${Math.max(scroller.offsetLeft + (xr + nw + 40) * sc, Math.min(want, maxLeft))}px`;
      img.style.top = `${scroller.offsetTop + yc - img.offsetHeight / 2 + 20}px`;
    };
    place(); img.onload = place; window.addEventListener("resize", place);
  }
  svg.onclick = (e) => {
    const r = e.target.closest(".s-ribbon");
    if (!r) return;
    ribbons.forEach((x) => x.classList.toggle("on", x === r));
    showTag(r);
    if (labelNode)
      labelNode.textContent = `${label(r.dataset.a)} → ${label(r.dataset.b)} · ${r.dataset.count} · opens on X ↗`;
    renderCards(
      evidenceRoot,
      evidenceRows
        .filter((p) => p.origin === r.dataset.a && p.destination === r.dataset.b)
        .sort(byDate),
      "switching",
    );
  };
}

/* ---------- harness duel ---------- */
function harnessDuel(h, rows) {
  const pair = (h.head_to_head || []).find((b) => b.models.includes("claude_code") && b.models.includes("codex")) || { votes: {}, n: 0 },
    cc = pair.votes?.claude_code || 0,
    cx = pair.votes?.codex || 0,
    n = cc + cx,
    sw = h.switches?.by_direction || {},
    ccx = sw["claude_code -> codex"] || 0,
    cxc = sw["codex -> claude_code"] || 0,
    votes = (rows || []).filter((p) => (p.winner === "codex" && p.loser === "claude_code") || (p.winner === "claude_code" && p.loser === "codex")),
    fh = votes.filter((p) => p.firsthand).length,
    days = Array.from({ length: 7 }, (_, d) => ({ cx: votes.filter((p) => p.day_index === d && p.winner === "codex").length, cc: votes.filter((p) => p.day_index === d && p.winner === "claude_code").length })),
    dayMax = Math.max(1, ...days.map((d) => Math.max(d.cx, d.cc))),
    dims = ["limits", "reliability", "efficiency", "agent", "dx", "overall", "other"],
    byDim = dims.map((d) => ({ d, cx: votes.filter((p) => p.winner === "codex" && (p.dimension || "other") === d).length, cc: votes.filter((p) => p.winner === "claude_code" && (p.dimension || "other") === d).length })).filter((x) => x.cx + x.cc > 0),
    dimMax = Math.max(1, ...byDim.map((x) => Math.max(x.cx, x.cc))),
    pct = n ? Math.round((cx / n) * 100) : 0;
  $("#harnessDuel").innerHTML = `
    <p class="duel-title">direct head-to-head, people who used both</p>
    <div class="tug"><span class="duel-who">Codex</span><b class="positive">${cx}</b><div class="tug-bar"><i style="width:${pct}%"></i></div><b class="cc">${cc}</b><span class="duel-who">Claude Code</span></div>
    <p class="duel-title">what each one wins on</p>
    <div class="dimbars">${byDim.map((x) => `<div class="dimrow"><b>${x.cx}</b><div class="dl"><i style="width:${(x.cx / dimMax) * 100}%"></i></div><span>${dimName("harness", x.d)}</span><div class="dr"><i style="width:${(x.cc / dimMax) * 100}%"></i></div><b>${x.cc}</b></div>`).join("")}</div>
    <p class="duel-title">votes by day</p>
    <div class="daybars">${days.map((d, i) => `<div class="day"><div class="cols"><i class="c1" style="height:${(d.cx / dayMax) * 100}%"></i><i class="c2" style="height:${(d.cc / dayMax) * 100}%"></i></div><small>${i + 1}</small></div>`).join("")}<div class="daykey"><span><i class="c1"></i>Codex</span><span><i class="c2"></i>Claude Code</span></div></div>`;
}

/* ---------- hero mural ---------- */
function mural(rows) {
  const root = $("#muralGrid"),
    posts = [...rows];
  if (!posts.length) {
    root.innerHTML = '<p class="mural-loading">The conversation is quiet.</p>';
    return;
  }
  const c = (p, i, enter = false) => {
    const axis = i % 2 ? "flip-x" : "flip-y";
    const who = p.username ? `<b>${esc(p.name || p.username)}</b><small>@${esc(p.username)}</small>` : `<b>${esc(label(p.target))}</b><small>${esc(p.aspect || "")}</small>`;
    const lines = (p.lines && p.lines.length ? p.lines : [{ target: p.target, sentiment: p.sentiment }]).slice(0, 3);
    const tags = `<span class="mural-tags">${lines.map((l) => `<span class="who">${icon(l.target)}<span>${esc(label(l.target))}</span><em class="tab ${esc(l.sentiment)}">${esc(l.sentiment)}</em></span>`).join("")}</span>`;
    const avatar = p.avatar ? `<img src="${p.avatar}" alt="" loading="lazy" onerror="this.remove()">` : "";
    return `<a class="mural-card ${axis}${enter ? " is-entering" : ""}" href="${p.url}" target="_blank" rel="noreferrer"><header>${avatar}<span>${who}</span></header><p>${esc(p.text)}</p>${tags}<span class="mural-open" aria-hidden="true">${X_MARK}<i>↗</i></span></a>`;
  };
  for (let i = posts.length - 1; i > 0; i--) {
    const k = Math.floor(Math.random() * (i + 1));
    [posts[i], posts[k]] = [posts[k], posts[i]];
  }
  root.innerHTML = posts.slice(0, 6).map((p, i) => c(p, i)).join("");
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches && posts.length > 6) {
    let cursor = 6;
    setInterval(() => {
      const cells = [...root.children], i = cursor % cells.length, current = cells[i];
      if (!current) return;
      current.classList.add("is-flipping");
      setTimeout(() => {
        if (!current.parentNode) return;
        current.outerHTML = c(posts[cursor % posts.length], i, true);
        cursor++;
      }, 260);
    }, 5100);
  }
}

/* ---------- featured: a model, twelve hours at a time ---------- */
// Dated from the posts that announced them (snowflake ids decode to the minute); Artificial Analysis has only a report date.
const EVENTS = [
  { at: "2026-09-25T12:00:00Z", label: "Artificial Analysis #1", url: "https://www.heise.de/en/news/External-benchmarks-Claude-Opus-5-5-overtakes-OpenAI-s-Astra-and-Fable-5-1-11466259.html", approx: true },
  { at: "2026-09-26T17:02:36Z", label: "Arena #1", url: "https://x.com/arena/status/2103893011164017018" },
  { at: "2026-09-27T16:10:38Z", label: "NerfBench: 99.2% of launch", url: "https://x.com/i/web/status/2104242319037804728" },
];
// The other lines the switcher can show, with the moments that matter to them.
const TREND_EVENTS = {
  "gpt-6-astra": [
    { at: "2026-09-22T16:31:03Z", label: "Opus 5.5 ships", url: "https://x.com/claudeai/status/2102435517165912464" },
    { at: "2026-09-26T17:02:36Z", label: "Arena #1 goes to Opus 5.5", url: "https://x.com/arena/status/2103893011164017018" },
    { at: "2026-09-27T16:10:38Z", label: "NerfBench: Astra 102.8%", url: "https://x.com/i/web/status/2104242319037804728" },
  ],
};
function featured(summary, ev) {
  const F = summary.launch.featured,
    focusId = summary.launch.focus,
    focus = summary.sentiment.models.find((m) => m.model === focusId),
    firstXb = (id) => (summary.launch.then_now && id === focusId ? summary.launch.then_now.opus_5_then.net_sentiment : F.trends?.[id]?.first_xbench),
    sets = [
      { id: focusId, curve: F.curve, start: summary.launch.t0, launch: true, events: EVENTS,
        ref: { v: F.reference.opus_5_first_xbench, t: `Opus 5, first Xbench` },
        avg: { v: F.reference.opus_5_5_window, t: "five-day net" }, rows: (ev.sentiment || []).filter((r) => r.model === focusId && r.firsthand) },
      ...Object.entries(F.trends || {}).map(([id, t]) => ({ id, curve: t.curve, start: t.start, launch: false, events: TREND_EVENTS[id] || [],
        ref: { v: t.first_xbench, t: `${label(id).replace(/^GPT-6 |^Claude /, "")}, first Xbench` }, avg: { v: t.overall.net_sentiment, t: "seven-day net" }, overall: t.overall,
        rows: (ev.featured_trends || []).filter((r) => r.model === id) })),
    ];
  const sw = $("#featuredSwitch"),
    pick = Math.max(0, sets.findIndex((x) => location.hash === `#featured-${x.id}`)); // e.g. #featured-gpt-6-astra
  sw.innerHTML = sets.map((x, i) => `<button class="${i === pick ? "on" : ""}" data-i="${i}">${icon(x.id)}${label(x.id).replace("Claude ", "")}</button>`).join("");
  sw.onclick = (e) => {
    const bt = e.target.closest("button");
    if (!bt) return;
    [...sw.children].forEach((x) => x.classList.toggle("on", x === bt));
    draw(sets[+bt.dataset.i]);
    history.replaceState(null, "", +bt.dataset.i ? `#featured-${sets[+bt.dataset.i].id}` : "#opus");
  };
  draw(sets[pick]);
  if (pick) $("#opus").scrollIntoView();

  function draw(S) {
  const curve = S.curve,
    t0 = new Date(S.start).getTime(),
    svg = $("#featuredChart"),
    W = 1180, L = 64, R = 170, T = 34, H1 = 340, G = 0, H2 = 0, B = 40,
    H = T + H1 + G + H2 + B,
    lo = -0.5, hi = 1,
    hours = (curve.length * F.step_hours),
    X = (h) => L + (h / hours) * (W - L - R),
    Y = (v) => T + ((hi - v) / (hi - lo)) * H1,
    mid = (b) => (new Date(b.start).getTime() + new Date(b.end).getTime()) / 2,
    hx = (ms) => X((ms - t0) / 36e5),
    ok = curve.filter((b) => b.n >= 12 && b.net_sentiment != null),
    dayFmt = (ms) => new Date(ms).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = '<defs><linearGradient id="fBand" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#2b4bd6" stop-opacity=".16"/><stop offset="1" stop-color="#2b4bd6" stop-opacity=".07"/></linearGradient></defs>';
  // grid: sentiment ticks, day boundaries
  [-0.5, 0, 0.5, 1].forEach((v) => {
    svg.append(el("line", { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: v === 0 ? "f-zero" : "f-grid" }));
    addText(svg, L - 12, Y(v) + 4, pts(v), v === 0 ? "f-axis strong" : "f-axis", "end");
  });
  for (let h = 0; h <= hours; h += 24) {
    const x = X(h);
    svg.append(el("line", { x1: x, x2: x, y1: T, y2: T + H1 + G + H2, class: "f-day" }));
    if (h < hours) addText(svg, x + 6, T + H1 + G + H2 + 22, h === 0 && S.launch ? `launch · ${dayFmt(t0)}` : dayFmt(t0 + h * 36e5), h === 0 ? "f-axis strong" : "f-axis");
  }
  // references
  const refLine = (v, cls, text) => {
    if (v == null) return;
    svg.append(el("line", { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: cls }));
    addText(svg, W - R + 12, Y(v) + 4, text, cls + "-t");
  };
  refLine(S.ref.v, "f-ref-rust", `${S.ref.t} ${pts(S.ref.v)}`);
  refLine(S.avg.v, "f-ref-ink", `${S.avg.t} ${pts(S.avg.v)}`);
  // events: dated moments, labels that would run into the one before drop a row
  const placed = [];
  S.events.forEach((e) => {
    const x = hx(new Date(e.at).getTime());
    if (x < L || x > W - R) return;
    const row = Math.max(-1, ...placed.filter((px) => x - px.x < 190).map((px) => px.row)) + 1;
    placed.push({ x, row });
    const top = T - 10 + row * 16, bottom = T + H1, ty = top + 4;
    svg.append(el("line", { x1: x, x2: x, y1: top, y2: bottom, class: `f-event${e.approx ? " approx" : ""}` }));
    svg.append(el("circle", { cx: x, cy: top, r: 3, class: "f-event-dot" }));
    const a = el("a", { href: e.url, target: "_blank", rel: "noreferrer" });
    const t = el("text", { x: x + 7, y: ty, class: "f-event-t" });
    t.textContent = e.label + (e.approx ? " (reported)" : "");
    a.append(t); svg.append(a);
  });
  // band and line (monotone cubic through bucket midpoints)
  const P = ok.map((b) => [hx(mid(b)), Y(b.net_sentiment)]);
  const band = ok.filter((b) => b.low != null);
  if (band.length > 1) {
    const up = band.map((b) => `${hx(mid(b)).toFixed(1)},${Y(b.high).toFixed(1)}`),
      dn = band.slice().reverse().map((b) => `${hx(mid(b)).toFixed(1)},${Y(b.low).toFixed(1)}`);
    svg.append(el("path", { d: `M${up.join("L")}L${dn.join("L")}Z`, class: "f-band" }));
  }
  const mono = (p) => {
    if (p.length < 3) return p.length ? "M" + p.map((q) => q.join(",")).join("L") : "";
    const n = p.length, d = [], m = [];
    for (let i = 0; i < n - 1; i++) d.push((p[i + 1][1] - p[i][1]) / (p[i + 1][0] - p[i][0]));
    m.push(d[0]);
    for (let i = 1; i < n - 1; i++) m.push(d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2);
    m.push(d[n - 2]);
    for (let i = 0; i < n - 1; i++) {
      if (d[i] === 0) { m[i] = m[i + 1] = 0; continue; }
      const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b;
      if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
    }
    let path = `M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}`;
    for (let i = 0; i < n - 1; i++) {
      const dx = (p[i + 1][0] - p[i][0]) / 3;
      path += `C${(p[i][0] + dx).toFixed(1)},${(p[i][1] + m[i] * dx).toFixed(1)} ${(p[i + 1][0] - dx).toFixed(1)},${(p[i + 1][1] - m[i + 1] * dx).toFixed(1)} ${p[i + 1][0].toFixed(1)},${p[i + 1][1].toFixed(1)}`;
    }
    return path;
  };
  svg.append(el("path", { d: mono(P), class: "f-line" }));
  const maxN = Math.max(...ok.map((b) => b.n), 1);
  ok.forEach((b, i) => {
    svg.append(el("circle", { cx: P[i][0], cy: P[i][1], r: 3 + 5 * Math.sqrt(b.n / maxN), class: `f-pt${b.partial ? " partial" : ""}` }));
  });
  const last = ok[ok.length - 1];
  if (last) addText(svg, P[P.length - 1][0] + 12, P[P.length - 1][1] - 10, pts(last.net_sentiment), "f-last");
  // hover and click
  const cross = el("line", { y1: T - 4, y2: T + H1 + G + H2, class: "f-cross", visibility: "hidden" });
  svg.append(cross);
  const hit = el("rect", { x: L, y: T - 4, width: W - L - R, height: H1 + G + H2 + 4, fill: "transparent", class: "f-hit" });
  svg.append(hit);
  const tip = $("#featuredTip"), cardsRoot = $("#featuredEvidence"), lab = $("#featuredEvidenceLabel");
  const at = (e) => {
    const r = svg.getBoundingClientRect(), x = ((e.clientX - r.left) / r.width) * W;
    return Math.max(0, Math.min(curve.length - 1, Math.floor(((x - L) / (W - L - R)) * curve.length)));
  };
  hit.addEventListener("mousemove", (e) => {
    const i = at(e), b = curve[i], x = X(i * F.step_hours + F.step_hours / 2);
    cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("visibility", "visible");
    const when = `${dayFmt(new Date(b.start).getTime())} ${b.start.slice(11, 16)}–${b.end.slice(11, 16)} UTC`;
    const asp = (a, s) => a.slice(0, 2).map(([t]) => `<span class="${s}">${s === "up" ? "+" : "−"} ${esc(t)}</span>`).join("");
    tip.innerHTML = `<b>${label(S.id)} · ${when}${b.partial ? " · so far" : ""}</b><strong class="${b.net_sentiment > 0 ? "positive" : "negative"}">${b.n >= 12 ? pts(b.net_sentiment) : "—"}</strong><small>${b.n} people · ${b.positive} + / ${b.mixed} ~ / ${b.negative} −${b.low != null ? ` · 95% ${pts(b.low)} to ${pts(b.high)}` : ""}</small>${asp(b.top_positive, "up")}${asp(b.top_negative, "down")}`;
    tip.hidden = false;
    const pr = svg.parentElement.getBoundingClientRect(), left = e.clientX - pr.left;
    tip.style.left = `${Math.min(left + 18, pr.width - tip.offsetWidth - 8)}px`;
    tip.style.top = `${Math.max(8, e.clientY - pr.top - tip.offsetHeight - 14)}px`;
  });
  hit.addEventListener("mouseleave", () => { cross.setAttribute("visibility", "hidden"); tip.hidden = true; });
  hit.addEventListener("click", (e) => {
    const i = at(e), b = curve[i], s = new Date(b.start), en = new Date(b.end);
    const inBucket = (r) => { const t = new Date(r.created_at); return t >= s && t < en; };
    const rows = S.rows.filter(inBucket).sort(byDate);
    lab.textContent = `${label(S.id)} · ${dayFmt(s.getTime())} ${b.start.slice(11, 16)}–${b.end.slice(11, 16)} UTC · ${rows.length} firsthand · opens on X ↗`;
    cardsRoot.innerHTML = rows.slice(0, 40).map((p) => card(p, "sentiment")).join("") || '<div class="evidence-empty">No firsthand posts in these twelve hours.</div>';
  });
  // facts
  const first = ok[0], lowest = ok.reduce((m, b) => (b.net_sentiment < m.net_sentiment ? b : m), ok[0] || {}),
    best = ok.reduce((m, b) => (b.net_sentiment > m.net_sentiment ? b : m), ok[0] || {});
  const lowFact = `<div><span>lowest twelve hours</span><strong>${lowest?.net_sentiment != null ? pts(lowest.net_sentiment) : "—"}</strong><small>${lowest?.start ? `${dayFmt(new Date(lowest.start).getTime())}, ${lowest.start.slice(11, 16)} UTC` : ""}</small></div>`;
  const cls = (v) => (v > 0.05 ? "positive" : v < -0.05 ? "negative" : "");
  if (S.launch) {
    const f = focus.firsthand, rank = summary.sentiment.models.filter((m) => m.firsthand.n >= 30 && m.firsthand.net_sentiment != null)
      .sort((a, b) => b.firsthand.net_sentiment - a.firsthand.net_sentiment).findIndex((m) => m.model === focus.model) + 1;
    $("#featuredFacts").innerHTML = `
      <div><span>net since launch</span><strong class="positive">${pts(f.net_sentiment)}</strong><small>${f.n} people firsthand · #${rank || "—"} of the models on this page</small></div>
      <div><span>launch day → latest</span><strong>${first ? pts(first.net_sentiment) : "—"} → ${last ? pts(last.net_sentiment) : "—"}</strong><small>twelve-hour steps with at least twelve people</small></div>
      ${lowFact}
      <div><span>best twelve hours</span><strong class="positive">${best?.net_sentiment != null ? pts(best.net_sentiment) : "—"}</strong><small>${best?.start ? `${dayFmt(new Date(best.start).getTime())}, ${best.start.slice(11, 16)} UTC` : ""}</small></div>`;
    lab.textContent = `${label(S.id)} · newest firsthand first · click the chart for any twelve hours · opens on X ↗`;
    cardsRoot.innerHTML = S.rows.slice().sort(byDate).slice(0, 30).map((p) => card(p, "sentiment")).join("");
  } else {
    const o = S.overall;
    $("#featuredFacts").innerHTML = `
      <div><span>net, last seven days</span><strong class="${cls(o.net_sentiment)}">${pts(o.net_sentiment)}</strong><small>${o.n} people firsthand, from ${label(S.id)}'s own name search</small></div>
      <div><span>seven days ago → latest</span><strong>${first ? pts(first.net_sentiment) : "—"} → ${last ? pts(last.net_sentiment) : "—"}</strong><small>twelve-hour steps with at least twelve people</small></div>
      ${lowFact}
      <div><span>on the first Xbench</span><strong class="${cls(S.ref.v)}">${pts(S.ref.v)}</strong><small>Aug 29 to Sep 5, the week it launched</small></div>`;
    lab.textContent = `${label(S.id)} · click the chart for any twelve hours · opens on X ↗`;
    cardsRoot.innerHTML = S.rows.slice().sort(byDate).slice(0, 30).map((p) => card(p, "sentiment")).join("") || '<div class="evidence-empty">No firsthand posts.</div>';
  }
  }
}
/* ---------- method ---------- */
function method(s, ev) {
  const c = s.corpus || {},
    rows = [
      [
        "posts classified",
        fmt(c.classified_posts),
        "one language-model pass per post, no keyword rules",
      ],
      [
        "reviewer corrections",
        fmt(c.reviewer_overrides),
        "flagged and sampled posts re-labeled by hand; replace the record wholesale",
      ],
      [
        "accounts excluded",
        fmt(c.excluded_ai_authors),
        `${fmt(c.excluded_posts)} posts from reply bots and spam accounts dropped before counting`,
      ],
      [
        "quota audit",
        fmt(c.quota_audit?.lines_read),
        `model lines about cost re-read: ${fmt(c.quota_audit?.moved_to_harness)} plan-limit complaints moved to the harness, ${fmt(c.quota_audit?.dropped_untracked_plan)} on untracked plans dropped`,
      ],
      [
        "model stances recorded",
        fmt(ev.sentiment?.length),
        `${fmt(ev.sentiment?.filter((r) => r.firsthand).length)} firsthand · ${fmt(ev.family_sentiment?.length)} on unversioned names`,
      ],
      [
        "harness stances recorded",
        fmt(ev.harness_sentiment?.length),
        `${fmt(ev.harness_sentiment?.filter((r) => r.firsthand).length)} firsthand across five harnesses`,
      ],
      [
        "preferences recorded",
        fmt(ev.preference?.length),
        `${fmt(s.preference?.firsthand_votes)} firsthand votes scored · ${fmt(s.preference?.benchmark_reposts)} benchmark reposts set aside`,
      ],
      [
        "completed switches",
        fmt((ev.switching?.length || 0) + (ev.harness_switching?.length || 0)),
        `${fmt(ev.switching?.length)} between models · ${fmt(ev.harness_switching?.length)} between harnesses`,
      ],
    ];
  $("#methodTable").innerHTML =
    `<div class="quality-row"><span>measure</span><span>count</span><span>note</span></div>${rows.map(([a, b, c]) => `<div class="quality-row"><strong>${a}</strong><span class="quality-status">${b}</span><span>${c}</span></div>`).join("")}`;
}

async function init() {
  heroMesh();
  $("#trackedModels").innerHTML = modelOrder
    .map((m) => `<span>${icon(m)}${label(m)}</span>`)
    .join("");
  $("#trackedHarnesses").innerHTML = harnessOrder
    .map((m) => `<span>${icon(m)}${label(m)}</span>`)
    .join("");
  try {
    const [summary, ev, hero] = await Promise.all([
      fetch(DATA_DIR + "public-summary.json?v=" + DATA_V).then((r) => r.json()),
      fetch(DATA_DIR + "public-evidence.json?v=" + DATA_V).then((r) => r.json()),
      fetch(DATA_DIR + "hero.json?v=" + DATA_V).then((r) => (r.ok ? r.json() : { posts: [] })).catch(() => ({ posts: [] })),
    ]);
    EV = ev;
    DIMS = summary.dimensions || DIMS;
    const corpus = summary.corpus || {},
      w = summary.window || {};
    $("#statPosts").textContent = fmt(corpus.unique_posts);
    $("#statAuthors").textContent = fmt(corpus.unique_authors);
    $("#statFirsthand").textContent = fmt(
      [
        ...(ev.sentiment || []),
        ...(ev.harness_sentiment || []),
        ...(ev.family_sentiment || []),
      ].filter((r) => r.firsthand).length,
    );
    $("#statOverrides").textContent = fmt(corpus.reviewer_overrides);
    const fmtDay = (d) =>
      new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    $("#footWindow").textContent = `window ${fmtDay(w.start)} to ${fmtDay(w.end)}`;
    const modelRows = summary.sentiment.models,
      drawModels = (mode) =>
        sentimentRows($("#sentimentRows"), modelRows, ev.sentiment || [], "model", mode);
    drawModels("firsthand");
    $("#sentimentMode").onclick = (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      [...e.currentTarget.children].forEach((x) => x.classList.toggle("on", x === b));
      drawModels(b.dataset.mode);
    };
    radar($("#radarModels"), $("#radarModelsLegend"), summary.sentiment.models, "model", [
      "claude-opus-5.5",
      "gpt-6-sol",
      "gpt-6-astra",
      "claude-fable-5.1",
    ]);
    radar(
      $("#radarHarness"),
      $("#radarHarnessLegend"),
      (summary.harnesses || {}).sentiment,
      "harness",
      ["claude_code", "codex", "grokbot"],
    );
    book($("#aspectModels"), summary.sentiment.models, "model", ev.sentiment || [], "model");
    book(
      $("#aspectHarness"),
      (summary.harnesses || {}).sentiment,
      "harness",
      ev.harness_sentiment || [],
      "harness",
    );
    const pref = summary.preference,
      h2h = pref.head_to_head || [];
    matrix(
      $("#battleList"),
      h2h,
      modelOrder,
      ev.preference || [],
      $("#battleEvidence"),
      $("#battleEvidenceLabel"),
    );
    renderCards(
      $("#battleEvidence"),
      (ev.preference || [])
        .filter((p) => p.firsthand)
        .sort(byDate)
        .slice(0, 40),
      "preference",
    );
    $("#preferenceTotals").textContent =
      `${fmt(pref.firsthand_votes)} votes · ${fmt(pref.distinct_authors)} people · ${h2h.length} matchups`;
    ratings($("#ratingChart"), pref.xbenchpref?.ratings);
    $("#ratingCount").textContent = fmt(pref.firsthand_votes);
    $("#ratingMatchups").textContent = h2h.length;
    sankey(
      $("#switchChart"),
      summary.switching.by_origin_destination,
      ev.switching || [],
      $("#switchEvidence"),
      $("#switchEvidenceLabel"),
    );
    renderCards($("#switchEvidence"), (ev.switching || []).sort(byDate), "switching");
    const h = summary.harnesses || {};
    if ($("#harnessRows")) sentimentRows($("#harnessRows"), h.sentiment, ev.harness_sentiment || [], "harness");
    harnessDuel(h, ev.harness || []);
    matrix(
      $("#harnessMatrix"),
      h.head_to_head,
      harnessOrder,
      ev.harness || [],
      $("#harnessEvidence"),
      $("#harnessEvidenceLabel"),
      true,
    );
    ratings($("#harnessRating"), h.ratings);
    renderCards(
      $("#harnessEvidence"),
      (ev.harness || [])
        .filter((p) => p.firsthand)
        .sort(byDate)
        .slice(0, 40),
      "preference",
    );
    sankey(
      $("#harnessSwitchChart"),
      Object.fromEntries(
        Object.entries(h.switches?.by_direction || {}).filter(([k]) =>
          k.split(" -> ").every((x) => shownHarness.has(x)),
        ),
      ),
      (ev.harness_switching || []).filter(
        (p) => shownHarness.has(p.origin) && shownHarness.has(p.destination),
      ),
      $("#harnessSwitchEvidence"),
      $("#harnessSwitchEvidenceLabel"),
    );
    {
      const hs = (ev.harness_switching || []).filter(
        (p) => shownHarness.has(p.origin) && shownHarness.has(p.destination),
      );
      $("#harnessSwitchCount").textContent = `${hs.length}`;
      renderCards($("#harnessSwitchEvidence"), hs.sort(byDate), "switching");
    }
    method(summary, ev);
    if (summary.launch?.featured) featured(summary, ev);
    const byPost = new Map();
    for (const r of [...(ev.sentiment || []), ...(ev.harness_sentiment || [])]) {
      if (!r.firsthand) continue;
      const t = r.model || r.harness;
      const arr = byPost.get(r.post_id) || [];
      if (!arr.some((x) => x.target === t)) arr.push({ target: t, sentiment: r.sentiment });
      byPost.set(r.post_id, arr);
    }
    mural(
      hero.posts && hero.posts.length
        ? hero.posts.map((p) => ({ ...p, lines: byPost.get(p.post_id) || [] }))
        : [...byPost.entries()].map(([post_id, lines]) => ({ ...(ev.sentiment || []).concat(ev.harness_sentiment || []).find((r) => r.post_id === post_id), post_id, target: lines[0].target, sentiment: lines[0].sentiment, lines })),
    );
  } catch (err) {
    console.error(err);
    document.body.classList.add("data-error");
    $("#footWindow").textContent = "data could not load";
  }
}
init();

/* info-tap: tap toggles an explainer on touch screens */
document.addEventListener("click", (e) => {
  const i = e.target.closest(".info");
  document.querySelectorAll(".info.open").forEach((x) => x !== i && x.classList.remove("open"));
  if (i) {
    e.preventDefault();
    i.classList.toggle("open");
  }
});

/* hero battle: Codex and Clawd cross the floor, face each other, and trade lasers and bubbles */
(function battle() {
  const st = document.querySelector(".stage");
  if (!st || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const A = { el: st.querySelector(".codex-f"), x: 0.28, v: 0.06, y: 0, vy: 0, next: 0, face: 1, kind: "laser" };
  const B = { el: st.querySelector(".clawd-f"), x: 0.66, v: -0.05, y: 0, vy: 0, next: 0, face: -1, kind: "bubble" };
  if (!A.el || !B.el) return;
  const shots = [];
  let last = 0, visible = true, fireA = 1.2, fireB = 2.1;
  const W = () => st.clientWidth;
  const H = () => st.clientHeight;
  const rnd = (a, b) => a + Math.random() * (b - a);
  function fire(from, to, k = 0) {
    const el = document.createElement("i");
    el.className = "shot " + from.kind;
    st.append(el);
    const fw = from.el.offsetWidth, fh = from.el.offsetHeight;
    const dir = to.x > from.x ? 1 : -1;
    const bubble = from.kind === "bubble";
    if (bubble) { const sz = rnd(7, 15); el.style.width = el.style.height = sz + "px"; }
    const s = { el, x: from.x * W() + fw / 2 + dir * (fw * 0.4 + k * 9), y: from.y + fh * (bubble ? 0.42 + rnd(-0.08, 0.08) : 0.55), vx: dir * (bubble ? rnd(300, 380) : 520), vy: bubble ? rnd(-6, 14) : 0, life: bubble ? 4 : 2.2, to, kind: from.kind, ph: rnd(0, 6) };
    shots.push(s);
  }
  let stop = 0;
  function impact(x, y, big) {
    const el = document.createElement("i");
    el.className = "impact" + (big ? " big" : "");
    el.style.transform = `translate(${x}px, ${-y}px) rotate(${rnd(-20, 20)}deg)`;
    st.append(el);
    setTimeout(() => el.remove(), 260);
    st.classList.add("flash");
    setTimeout(() => st.classList.remove("flash"), 60);
    stop = big ? 0.09 : 0.05;
  }
  function step(now) {
    requestAnimationFrame(step);
    if (!visible) { last = now; return; }
    let dt = Math.min(0.05, (now - last) / 1000 || 0);
    last = now;
    if (stop > 0) { stop -= dt; dt = 0; }
    const w = W();
    for (const f of [A, B]) {
      const other = f === A ? B : A;
      f.next -= dt;
      if (f.next <= 0) {
        f.next = rnd(1.4, 3.2);
        const r = Math.random();
        if (r < 0.45) f.v = Math.sign(other.x - f.x || 1) * rnd(0.05, 0.16);
        else if (r < 0.75) f.v = -Math.sign(other.x - f.x || 1) * rnd(0.04, 0.1);
        else f.v = (Math.random() < 0.5 ? -1 : 1) * rnd(0.12, 0.22);
        if (Math.random() < 0.5 && f.y === 0) f.vy = rnd(260, 420);
      }
      f.x += f.v * dt;
      const fw = f.el.offsetWidth / w;
      if (f.x < 0.02) { f.x = 0.02; f.v = Math.abs(f.v); }
      if (f.x > 1 - fw - 0.02) { f.x = 1 - fw - 0.02; f.v = -Math.abs(f.v); }
      if (f.y > 0 || f.vy > 0) { f.vy -= 1100 * dt; f.y += f.vy * dt; if (f.y <= 0) { f.y = 0; f.vy = 0; } }
      const face = other.x + other.el.offsetWidth / w / 2 > f.x + fw / 2 ? 1 : -1;
      f.face = face;
      const squash = f.y > 0 ? 1.03 : 1;
      f.el.style.transform = `translate(${f.x * w}px, ${-f.y}px) scaleX(${face}) scaleY(${squash})`;
    }
    fireA -= dt; fireB -= dt;
    if (fireA <= 0) { fire(A, B); fireA = rnd(1.6, 3.4); }
    if (fireB <= 0) { for (let k = 0; k < 8; k++) fire(B, A, k); fireB = rnd(1.8, 3.2); }
    for (let i = shots.length - 1; i >= 0; i--) {
      const s = shots[i];
      s.x += s.vx * dt; s.y += s.vy * dt; s.life -= dt;
      if (s.kind === "bubble") s.y += Math.sin(now / 140 + s.ph) * 12 * dt;
      s.el.style.transform = `translate(${s.x}px, ${-s.y}px)`;
      const t = s.to, tx = t.x * w, tw = t.el.offsetWidth, th = t.el.offsetHeight;
      const hit = s.x > tx + tw * 0.2 && s.x < tx + tw * 0.8 && s.y > t.y && s.y < t.y + th;
      if (hit || s.life <= 0 || s.x < -80 || s.x > w + 80) {
        if (hit) {
          t.el.classList.add("hit"); setTimeout(() => t.el.classList.remove("hit"), 180);
          t.vy = t.y === 0 ? 180 : t.vy;
          t.x += Math.sign(s.vx) * (s.kind === "laser" ? 0.03 : 0.008);

        }
        s.el.remove(); shots.splice(i, 1);
      }
    }
  }
  new IntersectionObserver((e) => { visible = e[0].isIntersecting; }).observe(st);
  requestAnimationFrame(step);
})();

/* reasons: one panel each, toggled between models and harnesses */
document.querySelectorAll(".kind-switch").forEach((sw) => {
  sw.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    sw.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    const panel = sw.closest(".panel");
    panel.querySelectorAll("[data-kind]").forEach((el) => { el.hidden = el.dataset.kind !== b.dataset.kind; });
  });
});
