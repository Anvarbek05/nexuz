// Nexuz frontend: tool list, home grid, and the tool page.
const MAX_MB = 25;

// ---- icons (simple line icons) ----
const ICONS = {
  merge: '<rect x="3" y="3" width="10" height="12" rx="2"/><rect x="11" y="9" width="10" height="12" rx="2"/>',
  split: '<path d="M12 3v18M7 8l-4 4 4 4M17 8l4 4-4 4"/>',
  rotate: '<path d="M20 12a8 8 0 1 1-2.6-5.9M20 4v5h-5"/>',
  compress: '<path d="M9 3v6H3M15 21v-6h6M9 9 3 3M15 15l6 6"/>',
  drop: '<path d="M12 3s6 6.5 6 10.5a6 6 0 0 1-12 0C6 9.5 12 3 12 3z"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m21 16-5-5-9 9"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  unlock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 7.5-2"/>',
  text: '<path d="M4 6h10M9 4v2M6 6c0 4 3 7 7 8M12 6c0 3-2 6-6 8M13 20l4-9 4 9M14.5 17h5"/>',
};
const icon = name =>
  `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[name]}</svg>`;

// ---- tools ----
// A tool with an `api` object is live. Fields:
//   endpoint, accept (extensions), multiple, min, need (message when too few files),
//   button, out or suffix (download name), compare (show size reduction), options[]
const GROUPS = { all: "All", organize: "Organize", convert: "Convert", edit: "Edit", security: "Security" };

const TOOLS = [
  { id: "merge", name: "Merge PDF", group: "organize", icon: "merge",
    desc: "Combine several PDF files into one, in the order you choose.",
    api: { endpoint: "/api/merge", accept: ".pdf", multiple: true, min: 2, need: "Add at least 2 PDF files.", out: "merged.pdf", button: "Merge PDF" } },
  { id: "split", name: "Extract pages", group: "organize", icon: "split",
    desc: "Keep only the pages you need from a PDF.",
    api: { endpoint: "/api/split", accept: ".pdf", multiple: false, min: 1, need: "Add a PDF file.", suffix: "-pages.pdf", button: "Extract pages",
      options: [{ name: "pages", label: "Pages to keep", type: "text", value: "1", help: "Example: 1-3,5 keeps pages 1, 2, 3 and 5." }] } },
  { id: "rotate", name: "Rotate PDF", group: "organize", icon: "rotate",
    desc: "Turn all pages of a PDF the right way up.",
    api: { endpoint: "/api/rotate", accept: ".pdf", multiple: false, min: 1, need: "Add a PDF file.", suffix: "-rotated.pdf", button: "Rotate PDF",
      options: [{ name: "angle", label: "Rotation", type: "select", choices: [["90", "90° clockwise"], ["180", "180°"], ["270", "90° counter-clockwise"]] }] } },
  { id: "compress", name: "Compress PDF", group: "organize", icon: "compress",
    desc: "Make a PDF smaller for email and uploads.",
    api: { endpoint: "/api/compress", accept: ".pdf", multiple: false, min: 1, need: "Add a PDF file.", suffix: "-compressed.pdf", button: "Compress PDF", compare: true,
      options: [{ name: "level", label: "Compression level", type: "select", value: "medium",
        choices: [["low", "Low: best quality"], ["medium", "Medium: recommended"], ["high", "High: smallest file"]],
        help: "Works best on PDFs with photos or scans. Text-only PDFs are already small." }] } },
  { id: "pdf2img", name: "PDF to images", group: "convert", icon: "image",
    desc: "Save every page as an image. Up to 50 pages.",
    api: { endpoint: "/api/pdf2img", accept: ".pdf", multiple: false, min: 1, need: "Add a PDF file.", suffix: "-images.zip", button: "Convert to images",
      options: [{ name: "fmt", label: "Image format", type: "select", choices: [["png", "PNG: sharp"], ["jpg", "JPG: smaller files"]] }] } },
  { id: "img2pdf", name: "Images to PDF", group: "convert", icon: "image",
    desc: "Put JPG and PNG images into one PDF, one image per page.",
    api: { endpoint: "/api/img2pdf", accept: ".jpg,.jpeg,.png", multiple: true, min: 1, need: "Add at least 1 JPG or PNG image.", out: "images.pdf", button: "Create PDF" } },
  { id: "uzbek", name: "Uzbek alphabet converter", group: "convert", icon: "text", desc: "Convert text between Uzbek Cyrillic and Latin." },
  { id: "watermark", name: "Add watermark", group: "edit", icon: "drop",
    desc: "Stamp text across every page of a PDF.",
    api: { endpoint: "/api/watermark", accept: ".pdf", multiple: false, min: 1, need: "Add a PDF file.", suffix: "-watermarked.pdf", button: "Add watermark",
      options: [{ name: "text", label: "Watermark text", type: "text", value: "Nexuz", help: "Latin letters and numbers. Marks like ğ or ş are not supported yet." }] } },
  { id: "protect", name: "Protect PDF", group: "security", icon: "lock", desc: "Lock a PDF with a password." },
  { id: "unlock", name: "Unlock PDF", group: "security", icon: "unlock", desc: "Remove the password from your own PDF." },
];

const $ = s => document.querySelector(s);
const state = { group: "all", tool: null, files: [], total: 0 };

// ---- home: filters + grid ----
function renderFilters() {
  const box = $("#filters");
  box.innerHTML = "";
  Object.entries(GROUPS).forEach(([key, label]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.setAttribute("aria-pressed", String(state.group === key));
    b.onclick = () => { state.group = key; renderFilters(); renderGrid(); };
    box.appendChild(b);
  });
}

function renderGrid() {
  const grid = $("#grid");
  grid.innerHTML = "";
  TOOLS.filter(t => state.group === "all" || t.group === state.group).forEach(t => {
    const ready = !!t.api;
    const card = document.createElement(ready ? "a" : "div");
    card.className = "card" + (ready ? "" : " card--soon");
    if (ready) card.href = "#" + t.id;
    card.innerHTML = `<span class="card__icon">${icon(t.icon)}</span><h3></h3><p></p>`;
    card.querySelector("h3").textContent = t.name;
    card.querySelector("p").textContent = t.desc;
    if (!ready) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = "Coming soon";
      card.appendChild(badge);
    }
    grid.appendChild(card);
  });
}

// ---- tool page ----
const fmtSize = bytes => bytes < 1048576 ? Math.max(1, Math.round(bytes / 1024)) + " KB" : (bytes / 1048576).toFixed(2) + " MB";

function setStatus(msg, isError = false) {
  const s = $("#status");
  s.textContent = msg;
  s.classList.toggle("is-error", isError);
}

function iconButton(label, text, disabled, onClick, cls = "") {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = text;
  b.title = label;
  b.setAttribute("aria-label", label);
  b.disabled = disabled;
  if (cls) b.className = cls;
  b.onclick = onClick;
  return b;
}

function renderOptions(tool) {
  const box = $("#options");
  box.replaceChildren();
  (tool.api.options || []).forEach(o => {
    const wrap = document.createElement("div");
    wrap.className = "option";
    const label = document.createElement("label");
    label.htmlFor = "opt-" + o.name;
    label.textContent = o.label;
    let input;
    if (o.type === "select") {
      input = document.createElement("select");
      o.choices.forEach(([value, text]) => input.add(new Option(text, value)));
      if (o.value) input.value = o.value;
    } else {
      input = document.createElement("input");
      input.type = "text";
      input.value = o.value || "";
      input.maxLength = 60;
    }
    input.id = "opt-" + o.name;
    input.name = o.name;
    wrap.append(label, input);
    if (o.help) {
      const help = document.createElement("p");
      help.className = "help";
      help.textContent = o.help;
      wrap.appendChild(help);
    }
    box.appendChild(wrap);
  });
}

function renderFiles() {
  const api = state.tool.api;
  const list = $("#files");
  list.innerHTML = "";
  state.files.forEach((f, i) => {
    const li = document.createElement("li");
    li.className = "file";
    const name = document.createElement("span");
    name.className = "file__name";
    name.textContent = f.name;
    const size = document.createElement("span");
    size.className = "file__size";
    size.textContent = fmtSize(f.size);
    const actions = document.createElement("span");
    actions.className = "file__actions";
    if (api.multiple) {
      actions.append(
        iconButton("Move up", "↑", i === 0, () => moveFile(i, -1)),
        iconButton("Move down", "↓", i === state.files.length - 1, () => moveFile(i, 1)),
      );
    }
    actions.append(iconButton("Remove " + f.name, "✕", false, () => { state.files.splice(i, 1); renderFiles(); }, "remove"));
    li.append(name, size, actions);
    list.appendChild(li);
  });
  const n = state.files.length;
  let hint = api.need;
  if (n >= api.min) hint = api.multiple && n > 1 ? `${n} files ready. Use the arrows to change the order.` : "Ready.";
  $("#hint").textContent = hint;
  $("#run").disabled = n < api.min;
}

function moveFile(i, step) {
  const j = i + step;
  [state.files[i], state.files[j]] = [state.files[j], state.files[i]];
  renderFiles();
}

function addFiles(fileList) {
  const api = state.tool.api;
  const exts = api.accept.split(",").map(e => e.trim().toLowerCase());
  const incoming = [...fileList];
  const valid = incoming.filter(f => exts.some(e => f.name.toLowerCase().endsWith(e)));
  const tooBig = valid.find(f => f.size > MAX_MB * 1048576);
  if (valid.length < incoming.length) setStatus(`Only ${exts.join(", ")} files can be added here.`, true);
  else if (tooBig) setStatus(`${tooBig.name} is larger than ${MAX_MB} MB.`, true);
  else setStatus("");
  const ok = valid.filter(f => f.size <= MAX_MB * 1048576);
  state.files = api.multiple ? state.files.concat(ok) : ok.slice(0, 1);
  $("#result").hidden = true;
  renderFiles();
}

function outputName(api) {
  if (api.out) return api.out;
  const base = state.files[0].name.replace(/\.[^.]+$/, "");
  return base + api.suffix;
}

async function runTool() {
  const api = state.tool.api;
  const body = new FormData();
  state.files.forEach(f => body.append("files", f));
  document.querySelectorAll("#options [name]").forEach(el => body.append(el.name, el.value));
  const originalSize = state.files.reduce((sum, f) => sum + f.size, 0);
  $("#run").disabled = true;
  $("#result").hidden = true;
  setStatus("Working on it…");
  try {
    const res = await fetch(api.endpoint, { method: "POST", body });
    if (!res.ok) {
      let msg = "Something went wrong. Please try again.";
      try { msg = (await res.json()).detail || msg; } catch (_) {}
      throw new Error(msg);
    }
    showResult(await res.blob(), outputName(api), api.compare ? originalSize : 0);
    setStatus("");
  } catch (err) {
    setStatus(err.message, true);
  }
  $("#run").disabled = state.files.length < api.min;
}

function showResult(blob, filename, originalSize) {
  const box = $("#result");
  const p = document.createElement("p");
  if (originalSize && blob.size < originalSize) {
    const saved = Math.round((1 - blob.size / originalSize) * 100);
    p.textContent = `Reduced from ${fmtSize(originalSize)} to ${fmtSize(blob.size)} (${saved}% smaller).`;
  } else if (originalSize) {
    p.textContent = `This PDF is already well optimized (${fmtSize(originalSize)}), so its size did not change.`;
  } else {
    p.textContent = `Your file is ready (${fmtSize(blob.size)}).`;
  }
  const link = document.createElement("a");
  link.className = "btn btn--primary";
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.textContent = "Download " + filename;
  const again = document.createElement("button");
  again.type = "button";
  again.className = "again";
  again.textContent = "Start over";
  again.onclick = () => { state.files = []; box.hidden = true; setStatus(""); renderFiles(); };
  box.replaceChildren(p, link, again);
  box.hidden = false;
}

function openTool(tool) {
  state.tool = tool;
  state.files = [];
  document.title = `${tool.name} — Nexuz`;
  $("#tool-title").textContent = tool.name;
  $("#tool-desc").textContent = tool.desc;
  $("#run").textContent = tool.api.button;
  const picker = $("#picker");
  picker.accept = tool.api.accept;
  picker.multiple = tool.api.multiple;
  picker.value = "";
  $("#drop strong").textContent = tool.api.multiple ? "Choose files" : "Choose a file";
  $("#drop span").textContent = tool.api.multiple ? "or drag and drop them here" : "or drag and drop it here";
  renderOptions(tool);
  $("#result").hidden = true;
  setStatus("");
  renderFiles();
}

// ---- routing: #merge opens a tool, anything else shows home ----
function route() {
  const id = location.hash.slice(1);
  const tool = TOOLS.find(t => t.id === id && t.api);
  $("#home").hidden = !!tool;
  $("#tool-view").hidden = !tool;
  if (tool) { openTool(tool); window.scrollTo(0, 0); }
  else document.title = "Nexuz — Free online PDF tools";
  if (!tool && id === "tools") $("#tools").scrollIntoView();
}

const drop = $("#drop");
$("#picker").addEventListener("change", e => { addFiles(e.target.files); e.target.value = ""; });
drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("is-over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("is-over"));
drop.addEventListener("drop", e => { e.preventDefault(); drop.classList.remove("is-over"); addFiles(e.dataTransfer.files); });
$("#run").addEventListener("click", runTool);
window.addEventListener("hashchange", route);

renderFilters();
renderGrid();
route();
