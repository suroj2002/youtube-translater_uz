// Server manzili bitta joyda saqlanadi.
const CONFIG = {
  API_BASE_URL: "https://backend-production-0b9ea6ca.up.railway.app",
};

// Har bir brauzer/qurilma uchun yagona doimiy ID
async function getDeviceId() {
  const data = await chrome.storage.local.get(["device_id"]);
  if (data.device_id) return data.device_id;
  const id = crypto.randomUUID();
  await chrome.storage.local.set({ device_id: id });
  return id;
}
