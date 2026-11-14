// Nexuz frontend. The server renders every page (with its language); this file only adds behaviour.
// window.NEXUZ = { page: "home" | "tool" | "uzbek" | "404", ui: {...texts...}, tool: {...} }
(() => {
  "use strict";

  const N = window.NEXUZ;
  const ui = N.ui;
  const MAX_MB = 25;
  const $ = s => document.querySelector(s);

  // t("hint_many", {n: 3}) -> text from the current language with {n} filled in
  const t = (key, vars = {}) => String(ui[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
  const fmtSize = bytes => bytes < 1048576
    ? Math.max(1, Math.round(bytes / 1024)) + " " + ui.kb
    : (bytes / 1048576).toFixed(2) + " " + ui.mb;

  // ---------------- home: category filters ----------------
  function initHome() {
    const buttons = document.querySelectorAll("#filters button");
    const cards = document.querySelectorAll("#grid .card");
    buttons.forEach(button => button.addEventListener("click", () => {
      buttons.forEach(b => b.setAttribute("aria-pressed", String(b === button)));
      cards.forEach(card => {
        card.hidden = button.dataset.group !== "all" && card.dataset.group !== button.dataset.group;
      });
    }));
  }

  // ---------------- file tools ----------------
  function initTool(tool) {
    let files = [];

    const setStatus = (msg, isError = false) => {
      const el = $("#status");
      el.textContent = msg;
      el.classList.toggle("is-error", isError);
    };

    const iconButton = (label, text, disabled, onClick, cls = "") => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = text;
      b.title = label;
      b.setAttribute("aria-label", label);
      b.disabled = disabled;
      if (cls) b.className = cls;
      b.onclick = onClick;
      return b;
    };

    function renderOptions() {
      const box = $("#options");
      tool.options.forEach(o => {
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
          input.type = o.type === "password" ? "password" : "text";
          input.value = o.value || "";
          input.maxLength = o.type === "password" ? 64 : 60;
          if (o.type === "password") input.autocomplete = "off";
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
      const list = $("#files");
      list.innerHTML = "";
      files.forEach((f, i) => {
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
        if (tool.multiple) {
          actions.append(
            iconButton(ui.move_up, "↑", i === 0, () => moveFile(i, -1)),
            iconButton(ui.move_down, "↓", i === files.length - 1, () => moveFile(i, 1)),
          );
        }
        actions.append(iconButton(t("remove", { name: f.name }), "✕", false, () => { files.splice(i, 1); renderFiles(); }, "remove"));
        li.append(name, size, actions);
        list.appendChild(li);
      });
      const n = files.length;
      let hint = tool.need;
      if (n >= tool.min) hint = tool.multiple && n > 1 ? t("hint_many", { n }) : ui.hint_ready;
      $("#hint").textContent = hint;
      $("#run").disabled = n < tool.min;
    }

    function moveFile(i, step) {
      const j = i + step;
      [files[i], files[j]] = [files[j], files[i]];
      renderFiles();
    }

    function addFiles(fileList) {
      const exts = tool.accept.split(",").map(e => e.trim().toLowerCase());
      const incoming = [...fileList];
      const valid = incoming.filter(f => exts.some(e => f.name.toLowerCase().endsWith(e)));
      const tooBig = valid.find(f => f.size > MAX_MB * 1048576);
      if (valid.length < incoming.length) setStatus(t("err_ext", { exts: exts.join(", ") }), true);
      else if (tooBig) setStatus(t("err_big", { name: tooBig.name, max: MAX_MB }), true);
      else setStatus("");
      const ok = valid.filter(f => f.size <= MAX_MB * 1048576);
      files = tool.multiple ? files.concat(ok) : ok.slice(0, 1);
      $("#result").hidden = true;
      renderFiles();
    }

    const outputName = () => tool.out || files[0].name.replace(/\.[^.]+$/, "") + tool.suffix;

    function showResult(blob, filename, originalSize) {
      const box = $("#result");
      const p = document.createElement("p");
      if (originalSize && blob.size < originalSize) {
        const pct = Math.round((1 - blob.size / originalSize) * 100);
        p.textContent = t("reduced", { from: fmtSize(originalSize), to: fmtSize(blob.size), pct });
      } else if (originalSize) {
        p.textContent = t("optimized", { size: fmtSize(originalSize) });
      } else {
        p.textContent = t("ready_msg", { size: fmtSize(blob.size) });
      }
      const link = document.createElement("a");
      link.className = "btn btn--primary";
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.textContent = t("download", { name: filename });
      const again = document.createElement("button");
      again.type = "button";
      again.className = "again";
      again.textContent = ui.start_over;
      again.onclick = () => { files = []; box.hidden = true; setStatus(""); renderFiles(); };
      box.replaceChildren(p, link, again);
      box.hidden = false;
    }

    async function run() {
      const body = new FormData();
      files.forEach(f => body.append("files", f));
      document.querySelectorAll("#options [name]").forEach(el => body.append(el.name, el.value));
      const originalSize = tool.compare ? files.reduce((sum, f) => sum + f.size, 0) : 0;
      $("#run").disabled = true;
      $("#result").hidden = true;
      setStatus(ui.working);
      try {
        const res = await fetch(tool.endpoint, { method: "POST", body });
        if (!res.ok) {
          let msg = ui.err_generic;
          try {
            const detail = (await res.json()).detail;
            if (typeof detail === "string") msg = detail;   // short explanation from the server (English)
          } catch (_) {}
          throw new Error(msg);
        }
        showResult(await res.blob(), outputName(), originalSize);
        setStatus("");
      } catch (err) {
        setStatus(err.message, true);
      }
      $("#run").disabled = files.length < tool.min;
    }

    const drop = $("#drop");
    $("#picker").addEventListener("change", e => { addFiles(e.target.files); e.target.value = ""; });
    drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("is-over"); });
    drop.addEventListener("dragleave", () => drop.classList.remove("is-over"));
    drop.addEventListener("drop", e => { e.preventDefault(); drop.classList.remove("is-over"); addFiles(e.dataTransfer.files); });
    $("#run").addEventListener("click", run);

    renderOptions();
    renderFiles();
  }

  // ---------------- Uzbek alphabet converter ----------------
  function initUzbek() {
    let timer = null;
    let latest = 0;

    const status = (msg, isError = false) => {
      const el = $("#uz-status");
      el.textContent = msg;
      el.classList.toggle("is-error", isError);
    };

    function convert() {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const text = $("#uz-in").value;
        if (!text.trim()) {
          $("#uz-out").value = "";
          $("#uz-detected").textContent = "";
          status("");
          return;
        }
        const mine = ++latest;
        try {
          const res = await fetch("/api/uzbek/convert", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, target: $("#uz-target").value }),
          });
          if (!res.ok) throw new Error(ui.uz_err_long);
          const data = await res.json();
          if (mine !== latest) return;   // a newer request is already running
          $("#uz-out").value = data.text;
          $("#uz-detected").textContent = t("uz_detected", { script: ui.uz_scripts[data.source] });
          status("");
        } catch (err) {
          if (mine === latest) status(err.message || ui.err_generic, true);
        }
      }, 300);
    }

    async function copy() {
      const text = $("#uz-out").value;
      if (!text) { status(ui.uz_nothing, true); return; }
      try {
        await navigator.clipboard.writeText(text);
      } catch (_) {
        $("#uz-out").select();
        document.execCommand("copy");
      }
      status(ui.uz_copied);
    }

    $("#uz-in").addEventListener("input", convert);
    $("#uz-target").addEventListener("change", convert);
    $("#uz-copy").addEventListener("click", copy);
    $("#uz-example").addEventListener("click", () => { $("#uz-in").value = ui.uz_example_text; convert(); });
    $("#uz-clear").addEventListener("click", () => {
      $("#uz-in").value = ""; $("#uz-out").value = ""; $("#uz-detected").textContent = ""; status("");
      $("#uz-in").focus();
    });
  }

  const pages = { home: initHome, tool: () => initTool(N.tool), uzbek: initUzbek };
  if (pages[N.page]) pages[N.page]();
})();
