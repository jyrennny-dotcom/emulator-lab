// Phone screen window: shows the emulator's screen live and sends clicks as taps and drags as swipes.
import { act, post, toast } from "./api.js";

const dlg = document.getElementById("phone");
const img = document.getElementById("phoneImg");
let current = null; // emulator config
let loopId = 0;
let lastUrl = "";

async function refreshLoop(myLoop) {
  while (myLoop === loopId && dlg.open) {
    try {
      const res = await fetch(`/api/emulators/${current.id}/screen?t=${Date.now()}`, { cache: "no-store" });
      if (res.ok) {
        const url = URL.createObjectURL(await res.blob());
        img.src = url;
        if (lastUrl) URL.revokeObjectURL(lastUrl);
        lastUrl = url;
      }
    } catch { /* try again next round */ }
    await new Promise((r) => setTimeout(r, 450));
  }
}

function toPhone(event) {
  const box = img.getBoundingClientRect();
  return {
    x: Math.round(((event.clientX - box.left) / box.width) * img.naturalWidth),
    y: Math.round(((event.clientY - box.top) / box.height) * img.naturalHeight),
  };
}

async function send(body) {
  try { await post(`/api/emulators/${current.id}/input`, body); }
  catch (err) { toast(err.message, true); }
}

let down = null;
img.addEventListener("pointerdown", (e) => { down = { ...toPhone(e), t: Date.now() }; e.preventDefault(); });
img.addEventListener("pointerup", (e) => {
  if (!down || !img.naturalWidth) return;
  const up = toPhone(e);
  const moved = Math.hypot(up.x - down.x, up.y - down.y);
  if (moved < 15) send({ type: "tap", x: up.x, y: up.y });
  else send({ type: "swipe", x: down.x, y: down.y, x2: up.x, y2: up.y, ms: Math.min(1500, Math.max(120, Date.now() - down.t)) });
  down = null;
});
let wheelBusy = false;
img.addEventListener("wheel", (e) => {
  e.preventDefault();
  if (wheelBusy || !img.naturalWidth) return;
  wheelBusy = true;
  const x = Math.round(img.naturalWidth / 2), mid = Math.round(img.naturalHeight / 2), d = Math.round(img.naturalHeight / 4);
  const [y, y2] = e.deltaY > 0 ? [mid + d, mid - d] : [mid - d, mid + d];
  send({ type: "swipe", x, y, x2: x, y2, ms: 250 }).finally(() => setTimeout(() => (wheelBusy = false), 350));
}, { passive: false });

dlg.querySelectorAll("[data-key]").forEach((button) =>
  button.addEventListener("click", () => send({ type: "key", key: button.dataset.key })));
dlg.querySelectorAll("[data-app]").forEach((button) =>
  button.addEventListener("click", () => act(`/api/emulators/${current.id}/open`, { app: button.dataset.app })));
document.getElementById("typeForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const field = document.getElementById("typeText");
  if (field.value) send({ type: "text", text: field.value });
  field.value = "";
});
dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
dlg.addEventListener("close", () => { loopId++; });

export function openPhone(config) {
  current = config;
  document.getElementById("phoneTitle").textContent = `${config.name} · phone screen`;
  img.removeAttribute("src");
  dlg.showModal();
  loopId++;
  refreshLoop(loopId);
}
