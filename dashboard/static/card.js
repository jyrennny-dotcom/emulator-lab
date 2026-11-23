// One card per emulator: live status, controls, and the hand-filled checklist (TikTok first, then YouTube).
import { act, copyText, el, toast } from "./api.js";

const CHECK_LABELS = {
  installed: "Installed",
  loggedIn: "Logged in (by hand)",
  rewardsVisible: "Rewards tab visible",
  inviteUiVisible: "Invite screen visible",
  inviteLinkShown: "Invite link shown",
};

function pill(item) {
  const { live, job } = item;
  if (!live.created) return ["Not created", "bad"];
  if (job && job.running) return [`${job.action}…`, "boot"];
  if (live.running && live.adb === "offline") return ["ADB offline", "bad"];
  if (live.running && live.booted) return ["Ready", "ready"];
  if (live.running) return ["Booting", "boot"];
  return ["Stopped", ""];
}

export function buildCard(item, shared, ui) {
  const id = item.config.id;
  const base = `/api/emulators/${id}`;
  const f = {}; // live fields we update every refresh
  const fact = (label, key) => el("div", { class: "fact" }, el("span", {}, label), (f[key] = el("b", {}, "–")));

  const openApp = async (app) => {
    const result = await act(`${base}/open`, { app });
    if (result !== undefined) ui.openPhone(item.config);
  };
  const btn = (text, cls, onclick, title) => el("button", { class: `btn small ${cls}`, onclick, title }, text);
  const b = {
    start: btn("Start", "ok", () => act(`${base}/start`, {}, `Starting ${item.config.name}…`)),
    stop: btn("Stop", "", () => act(`${base}/stop`, {}, `Stopping ${item.config.name}…`)),
    force: btn("Force stop", "ghost", () => confirm(`Force stop ${item.config.name}? Unsaved app state may be lost.`) &&
      act(`${base}/forcestop`)),
    reboot: btn("Reboot", "", () => act(`${base}/reboot`, {}, `Rebooting ${item.config.name}…`)),
    phone: btn("Phone screen", "", () => ui.openPhone(item.config)),
    window: btn("Open window", "owner-only", () => act(`${base}/window`, {}, "Window brought to front")),
    copy: btn("Copy ADB serial", "ghost", () => copyText(item.live.serial)),
    hw: btn("Hardware", "ghost", () => ui.openHardware(item.config)),
    reset: btn("Reset…", "danger", () => ui.openReset(item.config)),
    // opening an app also opens the phone screen, so it shows up for whoever pressed the button
    tiktok: el("button", { class: "btn tt", onclick: () => openApp("tiktok") }, "Open TikTok"),
    youtube: el("button", { class: "btn yt", onclick: () => openApp("youtube") }, "Open YouTube"),
  };

  // ---- checklist form ----
  const form = el("form", { class: "track-grid" });
  const input = (name, attrs = {}) => el("input", { name, ...attrs });
  form.append(
    el("label", {}, "Nickname", input("nickname", { maxlength: 40 })),
    el("label", {}, "Account label (nickname only, no emails)", input("accountLabel", { maxlength: 40 })),
    el("label", {}, "Testing status",
      el("select", { name: "testingStatus" }, shared.testStates.map((s) => el("option", { value: s }, s)))),
    el("label", {}, "Date last checked", input("lastChecked", { type: "date" })),
  );
  const detected = {};
  for (const app of shared.apps) {
    const box = el("fieldset", { class: `full ${app.key}` }, el("legend", {}, app.label));
    for (const check of shared.checks) {
      box.append(el("label", { class: "check" }, input(`${app.key}.${check}`, { type: "checkbox" }), CHECK_LABELS[check] || check));
    }
    box.append((detected[app.key] = el("div", { class: "detected" })));
    form.append(box);
  }
  const saved = el("span", { class: "saved" });
  form.append(
    el("label", { class: "full" }, "Notes (never put passwords or codes here)", el("textarea", { name: "notes", maxlength: 4000 })),
    el("div", { class: "row-end" }, saved, el("button", { class: "btn ok small" }, "Save checklist")),
  );
  let dirty = false;
  form.addEventListener("input", () => { dirty = true; saved.textContent = "unsaved"; });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const body = { apps: {} };
    for (const key of ["nickname", "accountLabel", "testingStatus", "lastChecked", "notes"]) body[key] = data.get(key) || "";
    for (const app of shared.apps) {
      body.apps[app.key] = {};
      for (const check of shared.checks) body.apps[app.key][check] = data.get(`${app.key}.${check}`) === "on";
    }
    const result = await act(`${base}/tracking`, body, "Checklist saved");
    if (result) { dirty = false; saved.textContent = "saved"; fillForm(result); }
  });
  function fillForm(t) {
    for (const key of ["nickname", "accountLabel", "testingStatus", "lastChecked", "notes"]) form.elements[key].value = t[key] || "";
    for (const app of shared.apps) {
      for (const check of shared.checks) form.elements[`${app.key}.${check}`].checked = !!(t.apps[app.key] || {})[check];
    }
  }

  const title = el("h3", {}, item.config.name, " ", (f.nick = el("span", { class: "nick" })));
  const card = el("article", { class: "card" },
    el("div", { class: "card-head" }, title, (f.pill = el("span", { class: "pill" }))),
    el("div", { class: "facts" }, fact("ADB serial", "serial"), fact("ADB", "adb"), fact("Android", "android"),
      fact("CPU", "cpu"), fact("Memory", "mem"), fact("Hardware", "hw")),
    (f.warn = el("div", { class: "warn" })),
    (f.job = el("div", { class: "job" })),
    el("div", { class: "apps-row" }, b.tiktok, b.youtube),
    el("div", { class: "actions" }, b.start, b.stop, b.reboot, b.phone, b.window, b.copy, b.hw, b.force, b.reset),
    el("details", { class: "track" }, el("summary", {}, "Checklist & notes"), form),
  );

  function update(next) {
    item = next;
    const { live, job, config: c, tracking } = next;
    const [text, cls] = pill(next);
    f.pill.textContent = text;
    f.pill.className = `pill ${cls}`;
    f.nick.textContent = tracking.nickname ? `· ${tracking.nickname}` : "";
    f.serial.textContent = live.serial;
    f.adb.textContent = live.adb;
    f.android.textContent = live.android ? `Android ${live.android}` : "–";
    f.cpu.textContent = live.cpuPct != null ? `${live.cpuPct}%` : "–";
    f.mem.textContent = live.memMB != null ? `${(live.memMB / 1024).toFixed(1)} GB` : "–";
    f.hw.textContent = `${c.ramMB / 1024} GB · ${c.cores} cores · ${c.dpi} dpi`;
    f.warn.textContent = live.warning || live.adbError || (!c.enabled ? "Not in \"Start all\" (turn on in Hardware)" : "");
    f.job.textContent = job && job.message ? job.message : "";
    f.job.className = "job" + (job && job.ok === false ? " bad" : "");
    card.classList.toggle("off", !live.running);
    const busy = !!(job && job.running);
    const ready = live.running && live.booted;
    b.start.disabled = busy || live.running || !live.created;
    b.stop.disabled = busy || !live.running;
    b.force.disabled = !live.running;
    b.reboot.disabled = busy || !ready;
    b.phone.disabled = b.tiktok.disabled = b.youtube.disabled = !ready;
    b.window.disabled = !live.running;
    b.reset.disabled = busy || !live.created;
    b.hw.disabled = busy || live.running;
    for (const app of shared.apps) {
      const seen = live.appsDetected[app.key];
      detected[app.key].textContent = seen == null ? "Detected: start the emulator to check" : `Detected on device: ${seen ? "yes" : "no"}`;
    }
    if (!dirty) fillForm(tracking);
  }

  update(item);
  return { node: card, update, get item() { return item; } };
}

export { toast };
