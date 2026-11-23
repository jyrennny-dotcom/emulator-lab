// Reset (typed confirmation, one emulator only) and hardware (RAM, cores, resolution, DPI) dialogs.
import { act } from "./api.js";

const resetDlg = document.getElementById("resetDlg");
const resetInput = document.getElementById("resetInput");
const resetGo = document.getElementById("resetGo");
let resetTarget = null;
let phrases = {};

export function setPhrases(map) { phrases = map || {}; }

export function openReset(config) {
  resetTarget = config;
  document.getElementById("resetName").textContent = config.name;
  document.getElementById("resetPhrase").textContent = phrases[config.id];
  resetInput.value = "";
  resetGo.disabled = true;
  resetDlg.showModal();
  resetInput.focus();
}
resetInput.addEventListener("input", () => { resetGo.disabled = resetInput.value !== phrases[resetTarget.id]; });
document.getElementById("resetForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (resetInput.value !== phrases[resetTarget.id]) return;
  resetDlg.close();
  await act(`/api/emulators/${resetTarget.id}/reset`, { confirm: resetInput.value }, `Resetting ${resetTarget.name}…`);
});

const hwDlg = document.getElementById("hwDlg");
const hwForm = document.getElementById("hwForm");
let hwTarget = null;

export function openHardware(config) {
  hwTarget = config;
  document.getElementById("hwName").textContent = config.name;
  for (const key of ["ramMB", "cores", "width", "height", "dpi"]) hwForm.elements[key].value = config[key];
  hwForm.elements.enabled.checked = !!config.enabled;
  hwDlg.showModal();
}
hwForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = { enabled: hwForm.elements.enabled.checked };
  for (const key of ["ramMB", "cores", "width", "height", "dpi"]) body[key] = Number(hwForm.elements[key].value);
  if (await act(`/api/emulators/${hwTarget.id}/hardware`, body, "Hardware saved")) hwDlg.close();
});

for (const dlg of [resetDlg, hwDlg]) {
  dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
}
