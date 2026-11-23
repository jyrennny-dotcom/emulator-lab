// Talks to the dashboard server and shows short messages at the bottom of the screen.
export async function getState() {
  const res = await fetch("/api/state", { cache: "no-store" });
  if (!res.ok) throw new Error(`Server said ${res.status}`);
  return res.json();
}

export async function post(path, body = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Lab-Request": "1" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({ ok: false, error: `Server said ${res.status}` }));
  if (!data.ok) throw new Error(data.error || "Request failed");
  return data.result;
}

let toastTimer;
export function toast(text, bad = false) {
  const el = document.getElementById("toast");
  el.textContent = Array.isArray(text) ? text.join("\n") : String(text);
  el.className = "toast" + (bad ? " bad" : "");
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 5000);
}

// Runs an action, shows the result or the error, and returns the result.
export async function act(path, body, okText) {
  try {
    const result = await post(path, body);
    const shown = okText || (typeof result === "string" ? result : Array.isArray(result) && result.length ? result : "Done");
    toast(shown);
    return result;
  } catch (err) {
    toast(err.message, true);
    return undefined;
  }
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  toast(`Copied ${text}`);
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value === true) node.setAttribute(key, "");
    else if (value !== false && value != null) node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child != null) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
