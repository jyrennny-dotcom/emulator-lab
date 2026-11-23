// Main loop: refreshes every 2 seconds, builds the cards once, then keeps them up to date.
import { act, copyText, el, getState } from "./api.js";
import { buildCard } from "./card.js";
import { openHardware, openReset, setPhrases } from "./dialogs.js";
import { openPhone } from "./phone.js";

const cards = new Map();
const cardBox = document.getElementById("cards");
const ui = { openPhone, openReset, openHardware };
const friend = document.body.dataset.mode === "friend";
if (friend) document.getElementById("modeText").textContent = "Shared with you · changes show up live for both of you";

document.getElementById("goTiktok").onclick = () => act("/api/go", { app: "tiktok" });
document.getElementById("goYoutube").onclick = () => act("/api/go", { app: "youtube" });
document.getElementById("startAll").onclick = () => act("/api/start-all", {}, "Starting all enabled emulators…");
document.getElementById("stopAll").onclick = () => confirm("Stop every running emulator?") && act("/api/stop-all", {}, "Stopping…");
document.getElementById("reconnect").onclick = () => act("/api/adb/reconnect", {}, "Asked ADB to reconnect offline devices");

let pageVersion = null;

function render(state) {
  if (pageVersion !== null && state.pageVersion !== pageVersion && !document.querySelector("dialog[open]")) {
    location.reload(); // the page itself was updated
    return;
  }
  pageVersion = state.pageVersion;
  setPhrases(state.resetPhrases);
  const problems = document.getElementById("problems");
  const lines = [...state.problems, state.adbError].filter(Boolean);
  problems.hidden = !lines.length;
  problems.textContent = lines.length ? "Setup needed:\n" + lines.join("\n") : "";
  for (const item of state.emulators) {
    const known = cards.get(item.config.id);
    if (known) known.update(item);
    else {
      const card = buildCard(item, state, ui);
      cards.set(item.config.id, card);
      cardBox.append(card.node);
    }
  }
  const feed = document.getElementById("feed");
  feed.replaceChildren(...(state.feed.length ? state.feed : [{ time: "", text: "Nothing yet. Press Start all." }])
    .map((f) => el("li", {}, el("time", {}, f.time), f.text)));
  document.getElementById("clock").textContent = state.time;
  document.getElementById("updates").replaceChildren(...(state.updates.length ? state.updates
    : [{ date: "", text: "No updates yet." }]).map((u) => el("li", {}, el("b", {}, u.date), u.text)));
  if (state.friend) {
    const ready = !!state.friend.link;
    friendLink = state.friend.link;
    document.getElementById("copyFriend").disabled = !ready;
    document.getElementById("friendStatus").textContent = ready
      ? "Live. Send it to your friend; he sees everything you see, in real time."
      : `Not ready yet (${state.friend.status}).`;
  }
}

let friendLink = "";
document.getElementById("copyFriend").onclick = () => friendLink && copyText(friendLink);

async function tick() {
  try {
    render(await getState());
  } catch (err) {
    const problems = document.getElementById("problems");
    problems.hidden = false;
    problems.textContent = `Can't reach the dashboard server (${err.message}). Is it running?`;
  }
  setTimeout(tick, 2000);
}
tick();
