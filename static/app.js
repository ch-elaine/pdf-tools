const form = document.getElementById("form");
const picker = document.getElementById("picker");
const pick = document.getElementById("pick");
const drop = document.getElementById("drop");
const status = document.getElementById("status");
const list = document.getElementById("files");
const dpi = document.getElementById("dpi");
const dpiValue = document.getElementById("dpi-value");

let busy = false;

const showDpi = () => {
  const n = Number(dpi.value);
  const word =
    n >= 300 ? "print" : n >= 200 ? "high" : n >= 120 ? "good" : n >= 72 ? "screen" : "draft";
  dpiValue.textContent = `${n} dpi · ${word}`;
};

const fmt = (bytes) => {
  const units = ["B", "KB", "MB", "GB"];
  let n = Number(bytes) || 0;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
  return `${n < 10 && i > 0 ? n.toFixed(1) : Math.round(n)} ${units[i]}`;
};

const say = (message, kind = "busy") => {
  status.textContent = message;
  status.className = `status ${kind}`;
};

const show = (files) => {
  list.innerHTML = "";
  for (const file of files) {
    const li = document.createElement("li");
    li.textContent = `${file.name} — ${fmt(file.size)}`;
    list.append(li);
  }
};

const save = (blob, name) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name || "compressed.pdf";
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 20000);
};

const nameFromDisposition = (header) => {
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header || "");
  return match ? decodeURIComponent(match[1]) : null;
};

async function upload(files) {
  if (busy || !files.length) return;
  busy = true;
  pick.disabled = true;
  show(files);
  say(`Compressing ${files.length} file${files.length > 1 ? "s" : ""}…`);

  const body = new FormData();
  for (const file of files) body.append("files", file);
  body.append("dpi", dpi.value);

  try {
    const response = await fetch("/process", { method: "POST", body });

    if (!response.ok) {
      let message = `Failed (${response.status})`;
      try {
        const data = await response.json();
        if (data.error) message = data.error;
      } catch { /* non-JSON error body */ }
      say(message, "err");
      return;
    }

    const blob = await response.blob();
    const before = Number(response.headers.get("X-Original-Bytes")) || 0;
    const after = blob.size;
    const pages = response.headers.get("X-Pages");
    const usedDpi = response.headers.get("X-Dpi");
    const notes = response.headers.get("X-Notes");

    save(blob, nameFromDisposition(response.headers.get("Content-Disposition")));

    const saved = before ? Math.round((1 - after / before) * 100) : 0;
    const delta = saved > 0 ? `−${saved}%` : "no size gain";
    say(`Done · ${fmt(before)} → ${fmt(after)} (${delta}) · ${pages} pages · ${usedDpi} dpi`, "ok");
    if (notes) {
      const li = document.createElement("li");
      li.textContent = notes;
      list.append(li);
    }
  } catch (error) {
    say(`Upload failed: ${error.message}`, "err");
  } finally {
    busy = false;
    pick.disabled = false;
    picker.value = "";
  }
}

pick.addEventListener("click", () => picker.click());
picker.addEventListener("change", () => upload([...picker.files]));
form.addEventListener("submit", (event) => event.preventDefault());
dpi.addEventListener("input", showDpi);
showDpi();

["dragenter", "dragover"].forEach((type) =>
  drop.addEventListener(type, (event) => {
    event.preventDefault();
    drop.classList.add("over");
  })
);
["dragleave", "drop"].forEach((type) =>
  drop.addEventListener(type, () => drop.classList.remove("over"))
);
drop.addEventListener("drop", (event) => {
  event.preventDefault();
  upload([...event.dataTransfer.files]);
});
