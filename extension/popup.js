const accessKeyInput = document.getElementById("accessKeyInput");
const togglePwBtn = document.getElementById("togglePwBtn");
const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const authCard = document.getElementById("authCard");
const controlsCard = document.getElementById("controlsCard");
const authMsg = document.getElementById("authMsg");
const ctrlMsg = document.getElementById("ctrlMsg");
const statusPill = document.getElementById("statusPill");
const userNameText = document.getElementById("userNameText");
const voiceSelect = document.getElementById("voiceSelect");
const vipOption = document.getElementById("vipOption");
const vipHint = document.getElementById("vipHint");
const origVolSlider = document.getElementById("origVolSlider");
const transVolSlider = document.getElementById("transVolSlider");
const origVolVal = document.getElementById("origVolVal");
const transVolVal = document.getElementById("transVolVal");
const toggleTranslateBtn = document.getElementById("toggleTranslateBtn");
const showChangePwBtn = document.getElementById("showChangePwBtn");
const changePwBox = document.getElementById("changePwBox");
const newKeyInput = document.getElementById("newKeyInput");
const toggleNewPwBtn = document.getElementById("toggleNewPwBtn");
const saveNewKeyBtn = document.getElementById("saveNewKeyBtn");

function setMsg(el, text, isErr = false) {
  el.textContent = text;
  el.className = "msg " + (text ? (isErr ? "msg-err" : "msg-ok") : "");
}

function notifyActiveTab(payload) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs && tabs[0];
    if (!tab || !tab.id) return;
    if (tab.url && !tab.url.startsWith("https://www.youtube.com/")) return;
    chrome.tabs.sendMessage(tab.id, payload, () => {
      void chrome.runtime.lastError;
    });
  });
}

function renderLoggedIn(state) {
  authCard.classList.add("hidden");
  controlsCard.classList.remove("hidden");
  statusPill.className = "pill pill-ok";
  statusPill.textContent = "Faol";
  userNameText.textContent = state.user_name || "Foydalanuvchi";

  const vipAllowed = Boolean(state.elevenlabs_enabled);
  vipOption.disabled = !vipAllowed;
  if (!vipAllowed) {
    vipOption.textContent = "ElevenLabs (VIP — ruxsat yo'q)";
    vipHint.textContent = "VIP ovoz admin tomonidan yoqilganda faollashadi.";
    if (state.voice === "elevenlabs") {
      state.voice = "sardor";
      chrome.storage.local.set({ voice: "sardor" });
    }
  } else {
    vipOption.textContent = "ElevenLabs (VIP)";
    vipHint.textContent = "";
  }

  voiceSelect.value = state.voice || "sardor";
  const origVol = state.originalVolume ?? 15;
  const transVol = state.translationVolume ?? 100;
  origVolSlider.value = origVol;
  transVolSlider.value = transVol;
  origVolVal.textContent = origVol + "%";
  transVolVal.textContent = transVol + "%";

  const active = Boolean(state.isTranslating);
  toggleTranslateBtn.textContent = active ? "Tarjimani to'xtatish" : "Tarjimani yoqish";
  toggleTranslateBtn.className = active ? "btn btn-danger" : "btn btn-success";
}

function renderLoggedOut() {
  authCard.classList.remove("hidden");
  controlsCard.classList.add("hidden");
  statusPill.className = "pill pill-muted";
  statusPill.textContent = "Kirilmagan";
  setMsg(authMsg, "");
}

togglePwBtn.addEventListener("click", () => {
  const show = accessKeyInput.type === "password";
  accessKeyInput.type = show ? "text" : "password";
  togglePwBtn.classList.toggle("active", show);
});

loginBtn.addEventListener("click", async () => {
  const key = accessKeyInput.value.trim();
  if (!key) {
    setMsg(authMsg, "Iltimos, parolni kiriting", true);
    return;
  }
  loginBtn.disabled = true;
  loginBtn.textContent = "Tekshirilmoqda...";
  setMsg(authMsg, "");
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/check-key`, {
      method: "GET",
      headers: { "X-Access-Key": key },
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setMsg(authMsg, data.detail || "Parol noto'g'ri yoki muddati tugagan", true);
      return;
    }
    const nextState = {
      access_key: key,
      user_name: data.user || "Foydalanuvchi",
      elevenlabs_enabled: Boolean(data.elevenlabs_enabled),
    };
    await chrome.storage.local.set(nextState);
    const full = await chrome.storage.local.get(null);
    renderLoggedIn(full);
  } catch {
    setMsg(authMsg, "Server bilan bog'lanib bo'lmadi (" + CONFIG.API_BASE_URL + ")", true);
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = "Kirish va tekshirish";
  }
});

logoutBtn.addEventListener("click", async () => {
  await chrome.storage.local.remove(["access_key", "user_name", "elevenlabs_enabled", "isTranslating"]);
  accessKeyInput.value = "";
  notifyActiveTab({ type: "TRANSLATION_STOP" });
  renderLoggedOut();
});

voiceSelect.addEventListener("change", async () => {
  const voice = voiceSelect.value;
  await chrome.storage.local.set({ voice });
  notifyActiveTab({ type: "SETTINGS_CHANGED", voice });
  setMsg(ctrlMsg, "Ovoz saqlandi: " + voice);
});

origVolSlider.addEventListener("input", () => {
  const val = Number(origVolSlider.value);
  origVolVal.textContent = val + "%";
  chrome.storage.local.set({ originalVolume: val });
  notifyActiveTab({ type: "VOLUME_CHANGED", originalVolume: val });
});

transVolSlider.addEventListener("input", () => {
  const val = Number(transVolSlider.value);
  transVolVal.textContent = val + "%";
  chrome.storage.local.set({ translationVolume: val });
  notifyActiveTab({ type: "VOLUME_CHANGED", translationVolume: val });
});

toggleTranslateBtn.addEventListener("click", async () => {
  const cur = await chrome.storage.local.get(["isTranslating"]);
  const next = !Boolean(cur.isTranslating);
  await chrome.storage.local.set({ isTranslating: next });
  const full = await chrome.storage.local.get(null);
  renderLoggedIn(full);
  notifyActiveTab({ type: next ? "TRANSLATION_START" : "TRANSLATION_STOP" });
  setMsg(ctrlMsg, next ? "Tarjima yoqildi" : "Tarjima to'xtatildi");
});

showChangePwBtn.addEventListener("click", () => {
  changePwBox.classList.toggle("hidden");
});

toggleNewPwBtn.addEventListener("click", () => {
  const show = newKeyInput.type === "password";
  newKeyInput.type = show ? "text" : "password";
  toggleNewPwBtn.classList.toggle("active", show);
});

saveNewKeyBtn.addEventListener("click", async () => {
  const newKey = newKeyInput.value.trim();
  if (newKey.length < 6) {
    setMsg(ctrlMsg, "Parol kamida 6 ta belgi bo'lishi kerak", true);
    return;
  }
  const saved = await chrome.storage.local.get(["access_key"]);
  if (!saved.access_key) return;
  saveNewKeyBtn.disabled = true;
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/change-key`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Access-Key": saved.access_key,
      },
      body: JSON.stringify({ new_key: newKey }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setMsg(ctrlMsg, data.detail || "Parolni o'zgartirib bo'lmadi", true);
      return;
    }
    await chrome.storage.local.set({ access_key: data.access_key });
    newKeyInput.value = "";
    changePwBox.classList.add("hidden");
    setMsg(ctrlMsg, "Parolingiz muvaffaqiyatli o'zgartirildi!");
  } catch {
    setMsg(ctrlMsg, "Server bilan bog'lanib bo'lmadi", true);
  } finally {
    saveNewKeyBtn.disabled = false;
  }
});

document.addEventListener("DOMContentLoaded", async () => {
  const saved = await chrome.storage.local.get(null);
  if (!saved.access_key) {
    renderLoggedOut();
    return;
  }
  renderLoggedIn(saved);
  // Har ochilganda serverdan VIP va parol holatini yangilab olish
  try {
    const resp = await fetch(`${CONFIG.API_BASE_URL}/check-key`, {
      headers: { "X-Access-Key": saved.access_key },
    });
    if (resp.ok) {
      const data = await resp.json();
      await chrome.storage.local.set({
        user_name: data.user,
        elevenlabs_enabled: Boolean(data.elevenlabs_enabled),
      });
      renderLoggedIn(await chrome.storage.local.get(null));
    } else if (resp.status === 401) {
      await chrome.storage.local.remove(["access_key", "user_name", "elevenlabs_enabled"]);
      renderLoggedOut();
      setMsg(authMsg, "Parol muddati tugagan yoki bloklangan", true);
    }
  } catch {
    // Server vaqtincha o'chiq bo'lsa lokal holatni saqlab turamiz
  }
});
