(() => {
  const REQ_TYPE = "YT_UZ_GET_TRANSCRIPT_REQ";
  const RES_TYPE = "YT_UZ_GET_TRANSCRIPT_RES";

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

  function parseJson3(rawText) {
    if (!rawText || !rawText.trim()) return null;
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
  }

  async function tryFetchTimedText(url) {
    try {
      const json3Url = url.includes("fmt=") ? url : `${url}&fmt=json3`;
      const resp = await fetch(json3Url, { credentials: "include" });
      if (!resp.ok) return null;
      const txt = await resp.text();
      return parseJson3(txt);
    } catch {
      return null;
    }
  }

  async function getTranscriptViaPlayer(videoId) {
    // 1) Agar brauzerda allaqachon timedtext so'rovi bo'lgan bo'lsa, o'shandan olamiz
    const existing = performance
      .getEntriesByType("resource")
      .filter((e) => e.name.includes("/api/timedtext") && e.name.includes(`v=${videoId}`));
    for (let i = existing.length - 1; i >= 0; i--) {
      const parsed = await tryFetchTimedText(existing[i].name);
      if (parsed) return parsed;
    }

    // 2) Player'ning joriy captionTracks'idan olamiz
    const tracks = getCaptionTracks(videoId);
    if (!tracks || tracks.length === 0) return null;
    const track = pickTrack(tracks);
    if (track && track.baseUrl) {
      const direct = await tryFetchTimedText(track.baseUrl);
      if (direct) return direct;
    }

    // 3) Agar YouTube pot-token talab qilsa, CC ni 1 soniyaga yoqib timedtext URL'ni ushlaymiz
    const player = document.getElementById("movie_player");
    if (player && typeof player.loadModule === "function") {
      try {
        player.loadModule("captions");
        if (typeof player.setOption === "function" && track) {
          player.setOption("captions", "track", { languageCode: track.languageCode });
        }
        await new Promise((r) => setTimeout(r, 900));
        const after = performance
          .getEntriesByType("resource")
          .filter((e) => e.name.includes("/api/timedtext") && e.name.includes(`v=${videoId}`));
        for (let i = after.length - 1; i >= 0; i--) {
          const parsed = await tryFetchTimedText(after[i].name);
          if (parsed) return parsed;
        }
      } catch {
        // ignore
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
