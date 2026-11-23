importScripts("config.js");

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "API_FETCH") {
    return false;
  }

  (async () => {
    try {
      const url = `${CONFIG.API_BASE_URL}${message.path}`;
      const resp = await fetch(url, {
        method: message.method || "POST",
        headers: message.headers || {},
        body: message.body ? JSON.stringify(message.body) : undefined,
      });
      const data = await resp.json().catch(() => ({}));
      sendResponse({ ok: resp.ok, status: resp.status, data });
    } catch (err) {
      sendResponse({
        ok: false,
        status: 0,
        error: err && err.message ? err.message : "Tarmoq xatosi",
      });
    }
  })();

  return true;
});
