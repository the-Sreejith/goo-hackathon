// DummE browser client. No framework — 60 lines, vanilla fetch.

const form = document.getElementById("cmd-form");
const input = document.getElementById("utterance");
const result = document.getElementById("result");
const pill = document.getElementById("status-pill");
const estopBtn = document.getElementById("estop-btn");
const micBtn = document.getElementById("mic-btn");

function setStatus(state, text) {
  pill.className = "pill " + state;
  pill.textContent = text;
}

async function postJSON(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const utterance = input.value.trim();
  if (!utterance) return;
  setStatus("busy", "running…");
  result.textContent = "";
  try {
    const data = await postJSON("/command", { utterance });
    result.textContent = JSON.stringify(data, null, 2);
    setStatus(data.ok ? "ok" : "err", data.ok ? "ok" : "error");
  } catch (err) {
    result.textContent = "Network error: " + err.message;
    setStatus("err", "error");
  }
});

micBtn.addEventListener("click", async () => {
  if (micBtn.disabled) return;
  micBtn.disabled = true;
  setStatus("busy", "listening…");
  result.textContent = "";
  try {
    const data = await postJSON("/listen", { max_seconds: 5.0 });
    if (data.transcript) input.value = data.transcript;
    result.textContent = JSON.stringify(data, null, 2);
    setStatus(data.ok ? "ok" : "err", data.ok ? "ok" : "error");
  } catch (err) {
    result.textContent = "Network error: " + err.message;
    setStatus("err", "error");
  } finally {
    micBtn.disabled = false;
  }
});

estopBtn.addEventListener("click", async () => {
  setStatus("busy", "estop…");
  try {
    await postJSON("/estop");
    setStatus("err", "ESTOP");
  } catch (err) {
    result.textContent = "Estop failed: " + err.message;
  }
});

async function pollStatus() {
  try {
    const res = await fetch("/status");
    const data = await res.json();
    if (data.estop) setStatus("err", "ESTOP");
  } catch {
    /* ignore — polling is best-effort */
  }
}

setInterval(pollStatus, 2000);
