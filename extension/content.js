(() => {
  const state = {
    active: false,
    videoId: null,
    chunks: [],
    audioUrls: new Map(),      // chunkIndex -> audio_url
    inFlight: new Map(),       // chunkIndex -> Promise<string>
    currentChunkIdx: -1,
    audio: new Audio(),
    savedVideoVolume: null,
    origVol: 15,
    transVol: 100,
    voice: "sardor",
    accessKey: "",
    statusText: "",
    syncTimer: null,
  };

  state.audio.preload = "auto";

  function apiPost(path, body, headers) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { type: "API_FETCH", method: "POST", path, body, headers },
        (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }
          if (!response) {
            reject(new Error("Background xizmatidan javob kelmadi"));
            return;
          }
          resolve(response);
        }
      );
    });
  }

  // --- UI: YouTube player ustidagi kichik boshqaruv tugmasi ---
  let pillEl = null;
  let pillTextEl = null;

  function ensurePlayerPill() {
    const player = document.querySelector("#movie_player") || document.querySelector(".html5-video-player");
    if (!player) return null;

    if (pillEl && player.contains(pillEl)) return pillEl;

    pillEl = document.createElement("button");
    pillEl.id = "yt-uz-dub-pill";
    pillEl.type = "button";
    Object.assign(pillEl.style, {
      position: "absolute",
      top: "14px",
      right: "14px",
      zIndex: "9999",
      display: "inline-flex",
      alignItems: "center",
      gap: "7px",
      padding: "7px 13px",
      borderRadius: "999px",
      border: "1px solid rgba(255,255,255,0.22)",
      background: "rgba(15, 23, 42, 0.82)",
      color: "#ffffff",
      fontSize: "12.5px",
      fontWeight: "600",
      fontFamily: "system-ui, -apple-system, sans-serif",
      cursor: "pointer",
      backdropFilter: "blur(6px)",
      boxShadow: "0 4px 14px rgba(0,0,0,0.3)",
    });

    const dot = document.createElement("span");
    dot.id = "yt-uz-dub-dot";
    Object.assign(dot.style, {
      width: "8px",
      height: "8px",
      borderRadius: "50%",
      background: "#94a3b8",
    });

    pillTextEl = document.createElement("span");
    pillTextEl.textContent = "UZ Tarjima";
    pillEl.append(dot, pillTextEl);

    pillEl.addEventListener("click", (e) => {
      e.stopPropagation();
      if (state.active) {
        stopTranslation(true);
      } else {
        startTranslation();
      }
    });

    player.appendChild(pillEl);
    return pillEl;
  }

  function setStatus(text, color = "#94a3b8") {
    state.statusText = text;
    ensurePlayerPill();
    if (!pillEl) return;
    const dot = pillEl.querySelector("#yt-uz-dub-dot");
    if (dot) dot.style.background = color;
    if (pillTextEl) pillTextEl.textContent = text;
  }

  function getVideoIdFromUrl() {
    const url = new URL(window.location.href);
    if (url.pathname === "/watch") return url.searchParams.get("v");
    const m = url.pathname.match(/^\/(shorts|live|embed)\/([^/?]+)/);
    return m ? m[2] : null;
  }

  function getVideoEl() {
    return document.querySelector("video.html5-main-video") || document.querySelector("video");
  }

  function isAdPlaying() {
    return document.querySelector(".ad-showing") !== null;
  }

  // --- Foydalanuvchi brauzeridan YouTube subtitrini olish (server IP bloklanmasligi uchun) ---
  function getTranscriptFromPageBridge(videoId) {
    return new Promise((resolve) => {
      const requestId = Math.random().toString(36).slice(2);
      const timer = setTimeout(() => {
        window.removeEventListener("message", onMsg);
        resolve(null);
      }, 4000);

      function onMsg(event) {
        if (
          event.source !== window ||
          !event.data ||
          event.data.type !== "YT_UZ_GET_TRANSCRIPT_RES" ||
          event.data.requestId !== requestId
        ) {
          return;
        }
        clearTimeout(timer);
        window.removeEventListener("message", onMsg);
        resolve(Array.isArray(event.data.snippets) ? event.data.snippets : null);
      }

      window.addEventListener("message", onMsg);
      window.postMessage({ type: "YT_UZ_GET_TRANSCRIPT_REQ", requestId, videoId }, "*");
    });
  }

  async function extractBrowserTranscript(videoId) {
    const bridged = await getTranscriptFromPageBridge(videoId);
    if (bridged && bridged.length > 0) return bridged;
    try {
      const resp = await fetch(`https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`, {
        credentials: "include",
      });
      const html = await resp.text();
      const marker = '"captionTracks":';
      const idx = html.indexOf(marker);
      if (idx === -1) return null;

      const arrStart = html.indexOf("[", idx);
      if (arrStart === -1) return null;

      let depth = 0;
      let end = -1;
      let inStr = false;
      let esc = false;
      for (let i = arrStart; i < html.length; i++) {
        const ch = html[i];
        if (esc) { esc = false; continue; }
        if (ch === "\\") { esc = true; continue; }
        if (ch === '"') { inStr = !inStr; continue; }
        if (inStr) continue;
        if (ch === "[") depth++;
        else if (ch === "]") {
          depth--;
          if (depth === 0) { end = i + 1; break; }
        }
      }
      if (end === -1) return null;

      const tracks = JSON.parse(html.slice(arrStart, end));
      if (!Array.isArray(tracks) || tracks.length === 0) return null;

      const preferred =
        tracks.find((t) => ["en", "ru"].includes(t.languageCode) && t.kind !== "asr") ||
        tracks.find((t) => ["en", "ru"].includes(t.languageCode)) ||
        tracks.find((t) => t.kind !== "asr") ||
        tracks[0];

      if (!preferred || !preferred.baseUrl) return null;
      const capUrl = preferred.baseUrl.includes("fmt=")
        ? preferred.baseUrl
        : `${preferred.baseUrl}&fmt=json3`;

      const capResp = await fetch(capUrl, { credentials: "include" });
      const capJson = await capResp.json();
      const events = capJson.events || [];
      const snippets = [];
      for (const ev of events) {
        if (!Array.isArray(ev.segs)) continue;
        const text = ev.segs.map((s) => s.utf8 || "").join("").replace(/\s+/g, " ").trim();
        if (!text) continue;
        snippets.push({
          start: Number(((ev.tStartMs || 0) / 1000).toFixed(3)),
          duration: Number(((ev.dDurationMs || 0) / 1000).toFixed(3)),
          text,
        });
      }
      return snippets.length > 0 ? snippets : null;
    } catch {
      return null;
    }
  }

  async function loadSettings() {
    const saved = await chrome.storage.local.get([
      "access_key",
      "voice",
      "originalVolume",
      "translationVolume",
      "isTranslating",
    ]);
    state.accessKey = (saved.access_key || "").trim();
    state.voice = saved.voice || "sardor";
    state.origVol = saved.originalVolume ?? 15;
    state.transVol = saved.translationVolume ?? 100;
    return saved;
  }

  function applyVolumes() {
    const video = getVideoEl();
    if (video && state.active && !isAdPlaying()) {
      if (state.savedVideoVolume === null) {
        state.savedVideoVolume = video.volume;
      }
      video.volume = Math.max(0, Math.min(1, state.origVol / 100));
    }
    state.audio.volume = Math.max(0, Math.min(1, state.transVol / 100));
  }

  function restoreVideoVolume() {
    const video = getVideoEl();
    if (video && state.savedVideoVolume !== null) {
      video.volume = state.savedVideoVolume;
    }
    state.savedVideoVolume = null;
  }

  async function fetchChunkAudioUrl(chunkIndex) {
    if (state.audioUrls.has(chunkIndex)) {
      return state.audioUrls.get(chunkIndex);
    }
    if (state.inFlight.has(chunkIndex)) {
      return state.inFlight.get(chunkIndex);
    }

    const titleEl = document.querySelector("h1.ytd-watch-metadata yt-formatted-string");
    const videoTitle = titleEl ? titleEl.textContent.trim() : document.title.replace(" - YouTube", "");

    const promise = (async () => {
      const deviceId = await getDeviceId();
      const res = await apiPost(
        "/chunk",
        {
          video_id: state.videoId,
          chunk_index: chunkIndex,
          voice: state.voice,
          video_title: videoTitle,
        },
        {
          "Content-Type": "application/json",
          "X-Access-Key": state.accessKey,
          "X-Device-Id": deviceId,
        }
      );
      const data = res.data || {};
      if (!res.ok) {
        throw new Error(data.detail || res.error || `Xatolik (${res.status})`);
      }
      state.audioUrls.set(chunkIndex, data.audio_url);
      return data.audio_url;
    })();

    state.inFlight.set(chunkIndex, promise);
    try {
      return await promise;
    } finally {
      state.inFlight.delete(chunkIndex);
    }
  }

  function preloadNextChunk(idx) {
    const nextIdx = idx + 1;
    if (nextIdx < state.chunks.length && !state.audioUrls.has(nextIdx) && !state.inFlight.has(nextIdx)) {
      fetchChunkAudioUrl(nextIdx).catch(() => {});
    }
  }

  function findChunkIndexForTime(t) {
    if (!state.chunks.length) return -1;
    for (let i = 0; i < state.chunks.length; i++) {
      const c = state.chunks[i];
      if (t >= c.start && t < c.end) return i;
    }
    if (t < state.chunks[0].start) return 0;
    return -1;
  }

  async function switchToChunk(idx, targetVideoTime) {
    if (idx < 0 || idx >= state.chunks.length) return;
    const reqVideoId = state.videoId;
    state.currentChunkIdx = idx;
    const chunk = state.chunks[idx];

    if (!state.audioUrls.has(idx)) {
      setStatus(`${idx + 1}-bo'lak yuklanmoqda...`, "#f59e0b");
    }

    try {
      const url = await fetchChunkAudioUrl(idx);
      if (!state.active || state.videoId !== reqVideoId || state.currentChunkIdx !== idx) return;

      if (state.audio.src !== url) {
        state.audio.src = url;
      }
      const video = getVideoEl();
      if (!video) return;

      const offset = Math.max(0, (targetVideoTime ?? video.currentTime) - chunk.start);
      if (Number.isFinite(offset)) {
        state.audio.currentTime = offset;
      }
      state.audio.playbackRate = Math.max(0.5, Math.min(2.0, video.playbackRate || 1));
      applyVolumes();

      if (!video.paused && !isAdPlaying()) {
        await state.audio.play().catch(() => {});
      }
      setStatus("UZ Tarjima faol", "#10b981");
      preloadNextChunk(idx);
    } catch (err) {
      setStatus("Xato: " + err.message, "#ef4444");
    }
  }

  function syncLoop() {
    if (!state.active) return;
    const video = getVideoEl();
    if (!video) return;

    if (isAdPlaying()) {
      if (!state.audio.paused) state.audio.pause();
      restoreVideoVolume();
      setStatus("Reklama — pauza", "#f59e0b");
      return;
    }

    applyVolumes();

    if (video.paused) {
      if (!state.audio.paused) state.audio.pause();
      return;
    }

    const t = video.currentTime;
    const idx = findChunkIndexForTime(t);
    if (idx === -1) {
      if (!state.audio.paused) state.audio.pause();
      return;
    }

    const curChunk = state.chunks[state.currentChunkIdx];
    // Bo'lak chegarasida gap tugamagan bo'lsa, 1.5s gacha oxirigacha gapirib olsin
    if (
      state.currentChunkIdx !== -1 &&
      idx === state.currentChunkIdx + 1 &&
      curChunk &&
      !state.audio.ended &&
      !state.audio.paused &&
      t - curChunk.end < 1.5
    ) {
      return;
    }

    if (idx !== state.currentChunkIdx) {
      switchToChunk(idx, t);
      return;
    }

    if (curChunk) {
      const expected = Math.max(0, t - curChunk.start);
      if (t < curChunk.start) {
        if (!state.audio.paused) state.audio.pause();
        return;
      }
      if (state.audio.paused && state.audio.src && !state.audio.ended) {
        state.audio.currentTime = expected;
        state.audio.play().catch(() => {});
      } else if (
        !state.audio.paused &&
        !state.audio.ended &&
        Math.abs(state.audio.currentTime - expected) > 0.7
      ) {
        state.audio.currentTime = expected;
      }
      state.audio.playbackRate = Math.max(0.5, Math.min(2.0, video.playbackRate || 1));
    }
  }

  function handleVideoSeeked() {
    if (!state.active || isAdPlaying()) return;
    const video = getVideoEl();
    if (!video) return;
    const idx = findChunkIndexForTime(video.currentTime);
    if (idx === -1) {
      state.audio.pause();
      return;
    }
    if (idx !== state.currentChunkIdx) {
      switchToChunk(idx, video.currentTime);
    } else if (state.chunks[idx]) {
      state.audio.currentTime = Math.max(0, video.currentTime - state.chunks[idx].start);
    }
  }

  async function startTranslation() {
    const videoId = getVideoIdFromUrl();
    if (!videoId) return;

    await loadSettings();
    if (!state.accessKey) {
      setStatus("Avval parol kiriting", "#ef4444");
      return;
    }

    stopTranslation(false);
    state.active = true;
    state.videoId = videoId;
    await chrome.storage.local.set({ isTranslating: true });
    setStatus("Subtitr olinmoqda...", "#f59e0b");

    const transcript = await extractBrowserTranscript(videoId);
    if (!state.active || state.videoId !== videoId) return;

    const titleEl = document.querySelector("h1.ytd-watch-metadata yt-formatted-string");
    const videoTitle = titleEl ? titleEl.textContent.trim() : document.title.replace(" - YouTube", "");

    try {
      const deviceId = await getDeviceId();
      const initBody = { video_id: videoId, video_title: videoTitle };
      if (transcript) initBody.transcript = transcript;

      const res = await apiPost("/init", initBody, {
        "Content-Type": "application/json",
        "X-Access-Key": state.accessKey,
        "X-Device-Id": deviceId,
      });
      const data = res.data || {};
      if (!res.ok) {
        throw new Error(data.detail || res.error || `Init xatosi (${res.status})`);
      }

      if (!state.active || state.videoId !== videoId) return;
      state.chunks = data.chunks || [];
      if (!state.chunks.length) {
        throw new Error("Subtitr bo'laklari topilmadi");
      }

      const video = getVideoEl();
      if (video) {
        video.addEventListener("seeked", handleVideoSeeked);
      }
      state.syncTimer = setInterval(syncLoop, 300);
      await switchToChunk(findChunkIndexForTime(video ? video.currentTime : 0), video?.currentTime);
    } catch (err) {
      state.active = false;
      await chrome.storage.local.set({ isTranslating: false });
      setStatus("Xato: " + err.message, "#ef4444");
    }
  }

  function stopTranslation(updateStorage = true) {
    state.active = false;
    state.currentChunkIdx = -1;
    state.chunks = [];
    state.audioUrls.clear();
    state.inFlight.clear();
    state.audio.pause();
    state.audio.removeAttribute("src");
    if (state.syncTimer) {
      clearInterval(state.syncTimer);
      state.syncTimer = null;
    }
    const video = getVideoEl();
    if (video) {
      video.removeEventListener("seeked", handleVideoSeeked);
    }
    restoreVideoVolume();
    if (updateStorage) {
      chrome.storage.local.set({ isTranslating: false });
    }
    setStatus("UZ Tarjima", "#94a3b8");
  }

  // Popup'dan keladigan xabarlar
  chrome.runtime.onMessage.addListener((msg) => {
    if (!msg || !msg.type) return;
    if (msg.type === "TRANSLATION_START") {
      startTranslation();
    } else if (msg.type === "TRANSLATION_STOP") {
      stopTranslation(false);
    } else if (msg.type === "VOLUME_CHANGED") {
      if (msg.originalVolume !== undefined) state.origVol = msg.originalVolume;
      if (msg.translationVolume !== undefined) state.transVol = msg.translationVolume;
      applyVolumes();
    } else if (msg.type === "SETTINGS_CHANGED") {
      if (msg.voice && msg.voice !== state.voice) {
        state.voice = msg.voice;
        if (state.active) {
          state.audioUrls.clear();
          state.inFlight.clear();
          state.currentChunkIdx = -1;
          syncLoop();
        }
      }
    }
  });

  // YouTube SPA navigatsiyasi
  window.addEventListener("yt-navigate-finish", async () => {
    const newId = getVideoIdFromUrl();
    if (state.active && newId !== state.videoId) {
      stopTranslation(false);
      if (newId) startTranslation();
    } else {
      ensurePlayerPill();
    }
  });

  // Dastlabki yuklanish
  setTimeout(async () => {
    ensurePlayerPill();
    const saved = await loadSettings();
    if (saved.isTranslating && getVideoIdFromUrl()) {
      startTranslation();
    }
  }, 1200);
})();
