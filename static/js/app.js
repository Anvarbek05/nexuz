// Nexuz frontend. The server renders every page (with its language); this file only adds behaviour.
// window.NEXUZ = { page: "home" | "tool" | "uzbek" | "login" | "register" | "account" | ..., lang, ui: {...texts...}, tool: {...}, account: {...} }
(() => {
  "use strict";

  const N = window.NEXUZ;
  const ui = N.ui;
  const $ = s => document.querySelector(s);

  // fetch() that tells the server our language, so error messages come back in it
  const api = (url, options = {}) =>
    fetch(url, { ...options, headers: { "X-Lang": N.lang, ...(options.headers || {}) } });

  // The server sends errors as {"detail": "text in our language"}
  async function errorText(res) {
    try {
      const detail = (await res.json()).detail;
      if (typeof detail === "string") return detail;
    } catch (_) {}
    return ui.err_generic;
  }

  function showStatus(msg, isError = false) {
    const el = $("#status");
    if (!el) return;
    el.textContent = msg;
    el.classList.toggle("is-error", isError);
  }

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

  // "3 of 5 uses left today. Create a free account for more."
  function renderQuota(q) {
    const el = $("#quota");
    if (!el || !q) return;
    el.replaceChildren();
    if (q.per_day === null) { el.textContent = ui.quota_unlimited; return; }
    el.append(t("quota_left", { left: q.left, limit: q.per_day }) + " ");
    const link = document.createElement("a");
    link.href = "/" + N.lang + (q.plan === "guest" ? "/register" : "/pricing");
    link.textContent = q.plan === "guest" ? ui.quota_register : ui.quota_premium;
    el.append(link);
  }

  // ---------------- file tools ----------------
  function initTool(tool) {
    let files = [];
    let maxMb = (N.account && N.account.max_mb) || 25;   // biggest file for this visitor's plan

    async function refreshQuota() {
      try {
        const res = await api("/api/me");
        if (!res.ok) return;
        const data = await res.json();
        maxMb = data.quota.max_mb;
        renderQuota(data.quota);
      } catch (_) {}
    }

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
      const tooBig = valid.find(f => f.size > maxMb * 1048576);
      if (valid.length < incoming.length) setStatus(t("err_ext", { exts: exts.join(", ") }), true);
      else if (tooBig) setStatus(t("err_big", { name: tooBig.name, max: maxMb }), true);
      else setStatus("");
      const ok = valid.filter(f => f.size <= maxMb * 1048576);
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
        const res = await api(tool.endpoint, { method: "POST", body });
        if (!res.ok) throw new Error(await errorText(res));   // short explanation from the server, in our language
        showResult(await res.blob(), outputName(), originalSize);
        setStatus("");
      } catch (err) {
        setStatus(err.message, true);
      }
      refreshQuota();
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
    renderQuota(N.account);
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
          const res = await api("/api/uzbek/convert", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, target: $("#uz-target").value }),
          });
          if (!res.ok) throw new Error(res.status === 429 ? await errorText(res) : ui.uz_err_long);
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

    // ---- upload a PDF or TXT file: the server sends the text in all 3 alphabets ----
    let fileTexts = null;
    let fileName = "text";

    async function uploadFile(file) {
      status(ui.uz_file_reading);
      const form = new FormData();
      form.append("file", file);
      try {
        const res = await api("/api/uzbek/convert-file", { method: "POST", body: form });
        if (!res.ok) throw new Error(await errorText(res));
        const data = await res.json();
        fileTexts = data.texts;
        fileName = file.name.replace(/\.[^.]+$/, "");
        $("#uz-in").value = "";
        $("#uz-out").value = fileTexts[$("#uz-target").value];
        $("#uz-detected").textContent = t("uz_detected", { script: ui.uz_scripts[data.source] });
        status(t("uz_file_done", { chars: data.chars, name: file.name }));
        try {
          const me = await (await api("/api/me")).json();
          renderQuota(me.quota);
        } catch (_) {}
      } catch (err) {
        status(err instanceof TypeError ? ui.acc_network : err.message, true);
      }
    }

    function download() {
      const text = $("#uz-out").value;
      if (!text) { status(ui.uz_nothing, true); return; }
      const link = document.createElement("a");
      link.href = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
      link.download = fileName + "-" + $("#uz-target").value + ".txt";
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    }

    $("#uz-file").addEventListener("change", e => { if (e.target.files[0]) uploadFile(e.target.files[0]); e.target.value = ""; });
    $("#uz-download").addEventListener("click", download);
    renderQuota(N.account);

    $("#uz-in").addEventListener("input", () => { fileTexts = null; convert(); });
    $("#uz-target").addEventListener("change", () => {
      if (fileTexts && !$("#uz-in").value) $("#uz-out").value = fileTexts[$("#uz-target").value];
      else convert();
    });
    $("#uz-copy").addEventListener("click", copy);
    $("#uz-example").addEventListener("click", () => { fileTexts = null; $("#uz-in").value = ui.uz_example_text; convert(); });
    $("#uz-clear").addEventListener("click", () => {
      fileTexts = null; $("#uz-in").value = ""; $("#uz-out").value = ""; $("#uz-detected").textContent = ""; status("");
      $("#uz-in").focus();
    });
  }

  // ---------------- sign in / create account ----------------
  function initAuth() {
    const form = $("#auth-form");
    const button = $("#auth-submit");
    form.addEventListener("submit", async e => {
      e.preventDefault();
      const mode = form.dataset.mode;                       // "login" or "register"
      button.disabled = true;
      showStatus(ui.acc_working);
      try {
        const res = await api("/api/auth/" + mode, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: $("#f-email").value, password: $("#f-password").value }),
        });
        if (!res.ok) throw new Error(await errorText(res));
        location.href = "/" + N.lang + "/" + (mode === "register" ? "account" : "");
      } catch (err) {
        showStatus(err instanceof TypeError ? ui.acc_network : err.message, true);
        button.disabled = false;
      }
    });
  }

  // ---------------- account page: sign out, delete ----------------
  function initAccount() {
    $("#logout").addEventListener("click", async () => {
      try { await api("/api/auth/logout", { method: "POST" }); } catch (_) {}
      location.href = "/" + N.lang + "/";
    });
    $("#delete-form").addEventListener("submit", async e => {
      e.preventDefault();
      if (!confirm(ui.acc_delete_confirm)) return;
      showStatus(ui.acc_working);
      try {
        const res = await api("/api/auth/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: $("#d-password").value }),
        });
        if (!res.ok) throw new Error(await errorText(res));
        showStatus(ui.acc_deleted);
        setTimeout(() => { location.href = "/" + N.lang + "/"; }, 1500);
      } catch (err) {
        showStatus(err instanceof TypeError ? ui.acc_network : err.message, true);
      }
    });
  }

  // ---------------- pricing page: pay for Premium ----------------
  function initPricing() {
    document.querySelectorAll("[data-pay]").forEach(button => button.addEventListener("click", async () => {
      button.disabled = true;
      showStatus(ui.acc_working);
      try {
        const res = await api("/api/pay/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ provider: button.dataset.pay }),
        });
        if (!res.ok) throw new Error(await errorText(res));
        location.href = (await res.json()).url;            // the provider's payment page
      } catch (err) {
        showStatus(err instanceof TypeError ? ui.acc_network : err.message, true);
        button.disabled = false;
      }
    }));
  }

  // ---------------- light / dark theme ----------------
  function initTheme() {
    const button = $("#theme-toggle");
    if (!button) return;
    const apply = theme => {
      document.documentElement.dataset.theme = theme;
      const label = theme === "dark" ? button.dataset.toLight : button.dataset.toDark;
      button.setAttribute("aria-label", label);
      button.title = label;
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.content = theme === "dark" ? "#0c1522" : "#0b7a75";
    };
    apply(document.documentElement.dataset.theme || "light");
    button.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      apply(next);
      try { localStorage.setItem("nexuz-theme", next); } catch (_) {}
    });
  }
  initTheme();

  const pages = {
    home: initHome, tool: () => initTool(N.tool), uzbek: initUzbek,
    login: initAuth, register: initAuth, account: initAccount, pricing: initPricing,
  };
  if (pages[N.page]) pages[N.page]();
})();
