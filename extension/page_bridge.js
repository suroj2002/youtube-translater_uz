(() => {
  const REQ_TYPE = "YT_UZ_GET_TRANSCRIPT_REQ";
  const RES_TYPE = "YT_UZ_GET_TRANSCRIPT_RES";

  const capturedUrls = new Map();   // videoId -> string[]
  const capturedBodies = new Map(); // videoId -> snippets[]

  function extractVideoIdFromUrl(rawUrl) {
    try {
      const u = new URL(rawUrl, location.origin);
      return u.searchParams.get("v") || "";
    } catch {
      return "";
    }
  }

  function recordTimedTextUrl(rawUrl) {
    if (!rawUrl || !rawUrl.includes("/api/timedtext")) return;
    const vid = extractVideoIdFromUrl(rawUrl);
    if (!vid) return;
    const list = capturedUrls.get(vid) || [];
    if (!list.includes(rawUrl)) {
      list.push(rawUrl);
      capturedUrls.set(vid, list);
    }
  }

  function parseJson3(rawText) {
    if (!rawText || !rawText.trim()) return null;
    try {
      const data = JSON.parse(rawText);
      const events = data.events || [];
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

  function parseXmlTimedText(rawText) {
    if (!rawText || !rawText.trim().startsWith("<")) return null;
    try {
      const doc = new DOMParser().parseFromString(rawText, "text/xml");
      const snippets = [];

      // Format 1: <p t="1234" d="567">text</p> (srv3)
      const pNodes = doc.querySelectorAll("p");
      if (pNodes.length > 0) {
        for (const p of pNodes) {
          const text = (p.textContent || "").replace(/\s+/g, " ").trim();
          if (!text) continue;
          const tMs = Number(p.getAttribute("t") || 0);
          const dMs = Number(p.getAttribute("d") || 2000);
          snippets.push({
            start: Number((tMs / 1000).toFixed(3)),
            duration: Number((dMs / 1000).toFixed(3)),
            text,
          });
        }
        return snippets.length > 0 ? snippets : null;
      }

      // Format 2: <text start="1.23" dur="4.56">text</text> (srv1 / default)
      const tNodes = doc.querySelectorAll("text");
      for (const t of tNodes) {
        const text = (t.textContent || "").replace(/\s+/g, " ").trim();
        if (!text) continue;
        const start = Number(t.getAttribute("start") || 0);
        const dur = Number(t.getAttribute("dur") || 2);
        snippets.push({
          start: Number(start.toFixed(3)),
          duration: Number(dur.toFixed(3)),
          text,
        });
      }
      return snippets.length > 0 ? snippets : null;
    } catch {
      return null;
    }
  }

  function parseTimedText(rawText) {
    return parseJson3(rawText) || parseXmlTimedText(rawText);
  }

  // Hook fetch & XHR early (document_start) to capture YouTube's pot-signed timedtext requests
  const origFetch = window.fetch;
  if (typeof origFetch === "function") {
    window.fetch = function (...args) {
      const reqUrl = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
      if (reqUrl.includes("/api/timedtext")) {
        recordTimedTextUrl(reqUrl);
      }
      const p = origFetch.apply(this, args);
      if (reqUrl.includes("/api/timedtext")) {
        p.then((resp) => {
          if (resp && resp.ok) {
            resp.clone().text().then((txt) => {
              const parsed = parseTimedText(txt);
              const vid = extractVideoIdFromUrl(reqUrl);
              if (parsed && vid) {
                capturedBodies.set(vid, parsed);
              }
            }).catch(() => {});
          }
        }).catch(() => {});
      }
      return p;
    };
  }

  const origXhrOpen = XMLHttpRequest.prototype.open;
  const origXhrSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this._ytUzUrl = typeof url === "string" ? url : "";
    if (this._ytUzUrl.includes("/api/timedtext")) {
      recordTimedTextUrl(this._ytUzUrl);
    }
    return origXhrOpen.call(this, method, url, ...rest);
  };
  XMLHttpRequest.prototype.send = function (...args) {
    if (this._ytUzUrl && this._ytUzUrl.includes("/api/timedtext")) {
      const reqUrl = this._ytUzUrl;
      this.addEventListener("load", () => {
        if (this.status >= 200 && this.status < 300 && typeof this.responseText === "string") {
          const parsed = parseTimedText(this.responseText);
          const vid = extractVideoIdFromUrl(reqUrl);
          if (parsed && vid) {
            capturedBodies.set(vid, parsed);
          }
        }
      });
    }
    return origXhrSend.apply(this, args);
  };

  function getCaptionTracks(videoId) {
    const player = document.getElementById("movie_player");
    if (player && typeof player.getPlayerResponse === "function") {
      const pr = player.getPlayerResponse();
      if (
        pr &&
        pr.videoDetails &&
        pr.videoDetails.videoId === videoId &&
        pr.captions &&
        pr.captions.playerCaptionsTracklistRenderer &&
        Array.isArray(pr.captions.playerCaptionsTracklistRenderer.captionTracks)
      ) {
        return pr.captions.playerCaptionsTracklistRenderer.captionTracks;
      }
    }

    const ytPr = window.ytInitialPlayerResponse;
    if (
      ytPr &&
      ytPr.videoDetails &&
      ytPr.videoDetails.videoId === videoId &&
      ytPr.captions &&
      ytPr.captions.playerCaptionsTracklistRenderer &&
      Array.isArray(ytPr.captions.playerCaptionsTracklistRenderer.captionTracks)
    ) {
      return ytPr.captions.playerCaptionsTracklistRenderer.captionTracks;
    }

    if (player && typeof player.getOption === "function") {
      try {
        const tracklist = player.getOption("captions", "tracklist");
        if (Array.isArray(tracklist) && tracklist.length > 0) {
          return tracklist;
        }
      } catch {
        // ignore
      }
    }
    return null;
  }

  function pickTrack(tracks) {
    return (
      tracks.find((t) => ["en", "ru"].includes(t.languageCode) && t.kind !== "asr") ||
      tracks.find((t) => ["en", "ru"].includes(t.languageCode)) ||
      tracks.find((t) => t.kind !== "asr") ||
      tracks[0]
    );
  }

  async function tryFetchTimedText(rawUrl) {
    try {
      const u = new URL(rawUrl, location.origin);
      u.searchParams.set("fmt", "json3");
      const resp = await origFetch.call(window, u.toString(), { credentials: "include" });
      if (resp.ok) {
        const txt = await resp.text();
        const parsed = parseTimedText(txt);
        if (parsed) return parsed;
      }
      // Fallback: try original URL without overriding fmt
      const resp2 = await origFetch.call(window, rawUrl, { credentials: "include" });
      if (!resp2.ok) return null;
      const txt2 = await resp2.text();
      return parseTimedText(txt2);
    } catch {
      return null;
    }
  }

  async function findFromCapturedOrPerf(videoId) {
    if (capturedBodies.has(videoId)) {
      return capturedBodies.get(videoId);
    }

    const urls = capturedUrls.get(videoId) || [];
    for (let i = urls.length - 1; i >= 0; i--) {
      const parsed = await tryFetchTimedText(urls[i]);
      if (parsed) return parsed;
    }

    const existing = performance
      .getEntriesByType("resource")
      .filter((e) => e.name.includes("/api/timedtext") && e.name.includes(`v=${videoId}`));
    for (let i = existing.length - 1; i >= 0; i--) {
      const parsed = await tryFetchTimedText(existing[i].name);
      if (parsed) return parsed;
    }
    return null;
  }

  async function getTranscriptViaPlayer(videoId) {
    // 1) Allaqachon ushlangan javob yoki timedtext URL dan olish
    const fromExisting = await findFromCapturedOrPerf(videoId);
    if (fromExisting) return fromExisting;

    // 2) Player'ning joriy captionTracks'idan olish
    const tracks = getCaptionTracks(videoId);
    const track = tracks && tracks.length > 0 ? pickTrack(tracks) : null;
    if (track && track.baseUrl) {
      const direct = await tryFetchTimedText(track.baseUrl);
      if (direct) return direct;
    }

    // 3) YouTube pot-token talab qilsa, CC tugmasini / modulini vaqtincha yoqib timedtext so'rovini ushlash
    const player = document.getElementById("movie_player");
    const ccBtn = document.querySelector(".ytp-subtitles-button");
    const wasOff = ccBtn && ccBtn.getAttribute("aria-pressed") === "false";

    try {
      if (wasOff) {
        ccBtn.click();
      }
      if (player && typeof player.loadModule === "function") {
        player.loadModule("captions");
        if (typeof player.setOption === "function" && track) {
          const opt = { languageCode: track.languageCode };
          if (track.vssId) opt.vssId = track.vssId;
          player.setOption("captions", "track", opt);
        }
      }

      const deadline = Date.now() + 3500;
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 250));
        const found = await findFromCapturedOrPerf(videoId);
        if (found) return found;
      }
    } catch {
      // ignore
    } finally {
      if (wasOff && ccBtn && ccBtn.getAttribute("aria-pressed") === "true") {
        ccBtn.click();
      }
    }

    return null;
  }

  window.addEventListener("message", async (event) => {
    if (event.source !== window || !event.data || event.data.type !== REQ_TYPE) return;
    const { requestId, videoId } = event.data;
    let snippets = null;
    try {
      snippets = await getTranscriptViaPlayer(videoId);
    } catch {
      snippets = null;
    }
    window.postMessage({ type: RES_TYPE, requestId, snippets }, "*");
  });
})();
