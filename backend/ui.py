from fastapi.openapi.docs import get_swagger_ui_html

_LOGO_SVG = """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
  <rect x="2" y="4" width="20" height="16" rx="5" stroke="currentColor" stroke-width="1.9"/>
  <path d="M9.8 8.7L15.4 12L9.8 15.3V8.7Z" fill="currentColor"/>
  <path d="M18.6 7.5C19.7 8.7 20.3 10.3 20.3 12C20.3 13.7 19.7 15.3 18.6 16.5" stroke="#3b82f6" stroke-width="1.9" stroke-linecap="round"/>
</svg>"""

_SHIELD_SVG = """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
  <path d="M12 3L4 6.5V12C4 16.8 7.4 20.9 12 22C16.6 20.9 20 16.8 20 12V6.5L12 3Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M9 12.2L11.1 14.3L15.4 10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

_WAVE_SVG = """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
  <path d="M4 10V14M8 7V17M12 4V20M16 7V17M20 10V14" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>
</svg>"""

_STORAGE_SVG = """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
  <ellipse cx="12" cy="6" rx="8" ry="3" stroke="currentColor" stroke-width="1.8"/>
  <path d="M4 6V12C4 13.7 7.6 15 12 15C16.4 15 20 13.7 20 12V6" stroke="currentColor" stroke-width="1.8"/>
  <path d="M4 12V18C4 19.7 7.6 21 12 21C16.4 21 20 19.7 20 18V12" stroke="currentColor" stroke-width="1.8"/>
</svg>"""

_DOCS_ARROW_SVG = """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
  <path d="M5 12H19M13 6L19 12L13 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

_BACK_ARROW_SVG = """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
  <path d="M19 12H5M11 6L5 12L11 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


def render_dashboard_html(
    elevenlabs_enabled: bool,
    gemini_enabled: bool = False,
    r2_enabled: bool = False,
) -> str:
    """Render the bright studio-light developer console for the backend root."""
    if gemini_enabled:
        gem_badge = '<span class="pill pill-emerald"><span class="dot dot-emerald"></span>Gemini Faol</span>'
    else:
        gem_badge = '<span class="pill pill-amber"><span class="dot dot-amber"></span>GEMINI_API_KEY bo\'sh</span>'

    if elevenlabs_enabled:
        el_badge = '<span class="pill pill-emerald"><span class="dot dot-emerald"></span>ElevenLabs Ulangan</span>'
    else:
        el_badge = '<span class="pill pill-amber"><span class="dot dot-amber"></span>ElevenLabs O\'chirilgan</span>'

    if r2_enabled:
        storage_badge = '<span class="pill pill-emerald"><span class="dot dot-emerald"></span>Cloudflare R2</span>'
        storage_desc = "MP3 bo'laklar R2 bulut xotirasiga yuklanadi."
    else:
        storage_badge = '<span class="pill pill-blue"><span class="dot dot-blue"></span>Lokal (/audio)</span>'
        storage_desc = "MP3 bo'laklar backend/audio_cache/ ichida saqlanadi."

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>YouTube O'zbekcha Tarjimon — Boshqaruv Paneli</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --border: #e2e8f0;
      --border-strong: #cbd5e1;
      --text: #0f172a;
      --text-muted: #475569;
      --text-dim: #64748b;
      --accent: #2563eb;
      --accent-hover: #1d4ed8;
      --emerald: #047857;
      --amber: #b45309;
      --rose: #b91c1c;
      --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, "Helvetica Neue", Arial, sans-serif;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      min-height: 100vh;
      color-scheme: light;
      font-family: var(--sans);
      font-size: 15px;
      color: var(--text);
      background-color: var(--bg);
      background-image:
        radial-gradient(ellipse 85% 45% at 50% -10%, rgba(37, 99, 235, 0.08), transparent 70%);
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }}
    a {{ color: inherit; text-decoration: none; }}
    code {{
      font-family: var(--mono);
      font-size: 0.9em;
      padding: 2px 6px;
      border-radius: 6px;
      background: #f1f5f9;
      color: #1e293b;
      border: 1px solid #e2e8f0;
    }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 20;
      backdrop-filter: blur(12px);
      background: rgba(255, 255, 255, 0.92);
      border-bottom: 1px solid var(--border);
      box-shadow: 0 2px 12px -6px rgba(15, 23, 42, 0.08);
    }}
    .topbar-inner {{
      max-width: 1060px;
      margin: 0 auto;
      padding: 13px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .brand-icon {{
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: var(--accent);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
    .brand-title {{
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.015em;
      color: var(--text);
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 11px;
      border-radius: 999px;
      font-size: 12.5px;
      font-weight: 600;
      border: 1px solid var(--border);
      background: var(--surface-soft);
      color: var(--text-muted);
      white-space: nowrap;
    }}
    .pill-emerald {{
      border-color: #a7f3d0;
      background: #ecfdf5;
      color: #047857;
    }}
    .pill-amber {{
      border-color: #fde68a;
      background: #fffbeb;
      color: #b45309;
    }}
    .pill-blue {{
      border-color: #bfdbfe;
      background: #eff6ff;
      color: #1d4ed8;
    }}
    .pill-rose {{
      border-color: #fecaca;
      background: #fef2f2;
      color: #b91c1c;
    }}
    .dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      display: inline-block;
      flex-shrink: 0;
    }}
    .dot-emerald {{ background: #10b981; }}
    .dot-amber {{ background: #f59e0b; }}
    .dot-blue {{ background: #2563eb; }}
    .nav-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 44px;
      padding: 0 18px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: background 0.15s ease, border-color 0.15s ease, transform 0.1s ease, box-shadow 0.15s ease;
    }}
    .btn:active {{ transform: translateY(1px); }}
    .btn-sm {{
      min-height: 38px;
      padding: 0 14px;
      font-size: 13.5px;
    }}
    .btn-primary {{
      background: var(--accent);
      color: #ffffff;
      box-shadow: 0 2px 6px rgba(37, 99, 235, 0.22);
    }}
    .btn-primary:hover {{ background: var(--accent-hover); }}
    .btn-primary:disabled {{ opacity: 0.65; cursor: wait; }}
    .btn-ghost {{
      background: var(--surface);
      border-color: var(--border-strong);
      color: var(--text);
    }}
    .btn-ghost:hover {{
      background: #f8fafc;
      border-color: #94a3b8;
    }}
    .container {{
      max-width: 1060px;
      margin: 0 auto;
      padding: 36px 24px 64px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}
    .hero {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 4px 0;
    }}
    .hero h1 {{
      font-size: clamp(26px, 3.2vw, 34px);
      font-weight: 750;
      letter-spacing: -0.025em;
      color: var(--text);
      line-height: 1.2;
    }}
    .hero p {{
      max-width: 760px;
      font-size: 15.5px;
      color: var(--text-muted);
    }}
    .hero-note {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      width: fit-content;
      margin-top: 4px;
      padding: 8px 14px;
      border-radius: 10px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1e40af;
      font-size: 13.5px;
      font-weight: 500;
    }}
    .grid-3 {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
    }}
    @media (max-width: 840px) {{
      .grid-3 {{ grid-template-columns: 1fr; }}
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 22px;
      box-shadow: 0 4px 20px -6px rgba(15, 23, 42, 0.07);
    }}
    .stat-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }}
    .stat-label {{
      font-size: 12.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-dim);
    }}
    .stat-icon {{
      width: 34px;
      height: 34px;
      border-radius: 9px;
      background: #f1f5f9;
      color: var(--accent);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
    .stat-value {{
      font-size: 16px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .stat-sub {{
      font-size: 13.5px;
      color: var(--text-muted);
    }}
    .card-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }}
    .card-title {{
      font-size: 17px;
      font-weight: 700;
      color: var(--text);
      letter-spacing: -0.01em;
    }}
    .card-subtitle {{
      font-size: 14px;
      color: var(--text-muted);
      margin-top: 3px;
    }}
    .tester-form {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .input-wrap {{
      flex: 1 1 280px;
      position: relative;
    }}
    .input {{
      width: 100%;
      height: 44px;
      padding: 0 14px;
      border-radius: 10px;
      border: 1px solid var(--border-strong);
      background: #ffffff;
      color: var(--text);
      font-family: var(--mono);
      font-size: 14.5px;
      outline: none;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    .input::placeholder {{ color: #94a3b8; }}
    .input:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
    }}
    .quick-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 12px;
      flex-wrap: wrap;
      font-size: 13px;
      color: var(--text-muted);
    }}
    .quick-pill {{
      padding: 5px 11px;
      border-radius: 8px;
      border: 1px solid var(--border-strong);
      background: var(--surface-soft);
      color: var(--text);
      font-family: var(--mono);
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }}
    .quick-pill:hover {{
      background: #eff6ff;
      border-color: #93c5fd;
      color: #1d4ed8;
    }}
    .result-box {{
      margin-top: 18px;
      border-radius: 12px;
      border: 1px solid var(--border);
      overflow: hidden;
      background: #1e293b;
      box-shadow: 0 4px 14px -6px rgba(15, 23, 42, 0.25);
    }}
    .result-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 11px 16px;
      background: #f8fafc;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
    }}
    .result-banner {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 13.5px;
      font-weight: 650;
    }}
    .result-meta {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: var(--mono);
      font-size: 12.5px;
      color: var(--text-muted);
    }}
    .result-pre {{
      padding: 16px;
      font-family: var(--mono);
      font-size: 13.5px;
      line-height: 1.6;
      color: #f8fafc;
      background: #1e293b;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .endpoint-list {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .endpoint-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 16px;
      border-radius: 12px;
      background: var(--surface-soft);
      border: 1px solid var(--border);
      flex-wrap: wrap;
    }}
    .endpoint-left {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .method-badge {{
      padding: 5px 10px;
      border-radius: 8px;
      font-family: var(--mono);
      font-size: 12.5px;
      font-weight: 700;
      min-width: 72px;
      text-align: center;
      color: #ffffff;
    }}
    .method-get {{ background: #2563eb; }}
    .method-post {{ background: #059669; }}
    .method-static {{ background: #d97706; }}
    .endpoint-path {{
      font-family: var(--mono);
      font-size: 14.5px;
      font-weight: 700;
      color: var(--text);
    }}
    .endpoint-desc {{
      font-size: 14px;
      color: var(--text-muted);
    }}
    .link-inline {{
      color: var(--accent);
      font-weight: 600;
    }}
    .link-inline:hover {{ text-decoration: underline; }}
    .hidden {{ display: none; }}
    .admin-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}
    @media (max-width: 720px) {{
      .admin-grid {{ grid-template-columns: 1fr; }}
    }}
    .field-label {{
      display: block;
      font-size: 12.5px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 5px;
    }}
    .field-input {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 9px;
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text);
      font-size: 14px;
      font-family: var(--mono);
    }}
    .field-input:focus {{
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
    }}
    .admin-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      font-size: 13.5px;
    }}
    .admin-table th, .admin-table td {{
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--border);
    }}
    .admin-table th {{
      font-size: 12px;
      text-transform: uppercase;
      color: var(--text-muted);
      font-weight: 700;
    }}
    .btn-xs {{
      padding: 5px 10px;
      font-size: 12px;
      border-radius: 7px;
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text);
      cursor: pointer;
      font-weight: 600;
    }}
    .btn-xs:hover {{ background: #f1f5f9; }}
    .btn-xs-danger {{ color: #b91c1c; border-color: #fecaca; }}
    .btn-xs-danger:hover {{ background: #fef2f2; }}
    .admin-note {{
      margin-top: 10px;
      font-size: 13px;
      font-weight: 600;
    }}
    .pw-wrap {{
      position: relative;
      display: flex;
      align-items: center;
      width: 100%;
    }}
    .pw-wrap .field-input {{
      padding-right: 38px;
    }}
    .pw-eye {{
      position: absolute;
      right: 8px;
      background: transparent;
      border: none;
      cursor: pointer;
      color: var(--text-muted);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 4px;
      border-radius: 6px;
    }}
    .pw-eye:hover {{
      color: var(--text);
      background: #f1f5f9;
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <span class="brand-icon">{_LOGO_SVG}</span>
        <div class="brand-title">YouTube O'zbekcha Tarjimon</div>
        <span class="pill pill-blue">v2.0</span>
      </div>
      <div class="nav-actions">
        <span class="pill pill-emerald"><span class="dot dot-emerald"></span>API Faol</span>
        <a class="btn btn-primary btn-sm" href="/docs">Swagger UI (/docs) {_DOCS_ARROW_SVG}</a>
      </div>
    </div>
  </header>

  <main class="container">
    <section class="hero">
      <h1>Backend API Boshqaruv Paneli</h1>
      <p>
        FastAPI serveri, SQLite (<code>app.db</code>), <code>X-Access-Key</code> autentifikatsiyasi,
        ~60 soniyalik bo'laklash, Gemini tarjima va TTS audio kesh tizimi ishlamoqda.
      </p>
      <div class="hero-note">
        1–2-bosqichlar: Autentifikatsiya, bo'laklash, Gemini tarjima, TTS va kesh tayyor. Chrome Extension 3–4-bosqichlarda quriladi.
      </div>
    </section>

    <section class="grid-3">
      <article class="card">
        <div class="stat-top">
          <div class="stat-label">Autentifikatsiya</div>
          <span class="stat-icon">{_SHIELD_SVG}</span>
        </div>
        <div class="stat-value">
          <span>X-Access-Key</span>
          <span class="pill pill-emerald"><span class="dot dot-emerald"></span>Faol</span>
        </div>
        <div class="stat-sub">SQLite (<code>app.db</code>) · <code>users</code>, <code>video_chunks</code>, <code>audio_cache</code></div>
      </article>

      <article class="card">
        <div class="stat-top">
          <div class="stat-label">Tarjima va TTS</div>
          <span class="stat-icon">{_WAVE_SVG}</span>
        </div>
        <div class="stat-value">
          {gem_badge}
          {el_badge}
        </div>
        <div class="stat-sub"><code>gemini-2.5-flash</code> + <code>edge-tts</code> (Sardor / Madina) va ElevenLabs VIP</div>
      </article>

      <article class="card">
        <div class="stat-top">
          <div class="stat-label">Audio Kesh &amp; Hujjatlar</div>
          <span class="stat-icon">{_STORAGE_SVG}</span>
        </div>
        <div class="stat-value">
          {storage_badge}
        </div>
        <div class="stat-sub">
          {storage_desc}
          <a class="link-inline" href="/docs">/docs</a>
          &nbsp;·&nbsp;
          <a class="link-inline" href="/openapi.json">OpenAPI JSON</a>
        </div>
      </article>
    </section>

    <section class="card">
      <div class="card-header">
        <div>
          <h2 class="card-title">Parolni (Access Key) tekshirish</h2>
          <p class="card-subtitle">To'g'ridan-to'g'ri <code>GET /check-key</code> endpointiga jonli so'rov yuboring.</p>
        </div>
      </div>

      <form id="keyForm" class="tester-form">
        <div class="input-wrap">
          <input
            id="accessKeyInput"
            class="input"
            type="password"
            value=""
            placeholder="Kirish parolini yozing"
            autocomplete="off"
            spellcheck="false"
            aria-label="X-Access-Key"
          >
        </div>
        <button id="checkBtn" class="btn btn-primary" type="submit">Tekshirish</button>
      </form>

      <div class="quick-row">
        <span>Tezkor test:</span>
        <button type="button" class="quick-pill" data-key="WRONG-KEY">WRONG-KEY</button>
      </div>

      <div id="resultBox" class="result-box hidden">
        <div class="result-head">
          <span id="resultBanner" class="result-banner"></span>
          <div class="result-meta">
            <span id="statusBadge" class="pill"></span>
            <span id="latencyBadge"></span>
          </div>
        </div>
        <pre id="resultJson" class="result-pre"></pre>
      </div>
    </section>

    <section class="card">
      <div class="card-header">
        <div>
          <h2 class="card-title">Mavjud Endpointlar</h2>
          <p class="card-subtitle">1–2-bosqichlarda faollashtirilgan API yo'llari va statik audio manzili.</p>
        </div>
        <a class="btn btn-ghost btn-sm" href="/docs">Batafsil /docs da ochish</a>
      </div>

      <div class="endpoint-list">
        <div class="endpoint-row">
          <div class="endpoint-left">
            <span class="method-badge method-get">GET</span>
            <span class="endpoint-path">/check-key</span>
            <span class="endpoint-desc"><code>X-Access-Key</code> headerini tekshiradi va foydalanuvchi holatini qaytaradi.</span>
          </div>
          <span class="pill">200 / 401</span>
        </div>

        <div class="endpoint-row">
          <div class="endpoint-left">
            <span class="method-badge method-post">POST</span>
            <span class="endpoint-path">/init</span>
            <span class="endpoint-desc">YouTube subtitrini (~60s bo'laklarga) ajratadi va <code>video_chunks</code> ga keshlaydi.</span>
          </div>
          <span class="pill">X-Access-Key</span>
        </div>

        <div class="endpoint-row">
          <div class="endpoint-left">
            <span class="method-badge method-post">POST</span>
            <span class="endpoint-path">/chunk</span>
            <span class="endpoint-desc">Bo'lakni Gemini orqali tarjima qilib, TTS + auto-pacing bilan MP3 kesh qaytaradi.</span>
          </div>
          <span class="pill">X-Access-Key</span>
        </div>

        <div class="endpoint-row">
          <div class="endpoint-left">
            <span class="method-badge method-static">STATIC</span>
            <span class="endpoint-path">/audio/{{filename}}</span>
            <span class="endpoint-desc">Lokal <code>backend/audio_cache/</code> ichidagi tayyor MP3 fayllarni uzatadi.</span>
          </div>
          <span class="pill">audio/mpeg</span>
        </div>
      </div>
    </section>

    <section class="card" id="adminCabinetCard">
      <div class="card-header">
        <div>
          <h2 class="card-title">Shaxsiy Kabinet (Admin)</h2>
          <p class="card-subtitle">API kalitlarini (Gemini, ElevenLabs) qayta ishga tushirishsiz almashtirish va obunachilarni boshqarish.</p>
        </div>
        <span class="pill" id="adminAuthBadge">Kirilmagan</span>
      </div>

      <form id="adminLoginForm" style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
        <div class="pw-wrap" style="max-width:280px;">
          <input id="adminKeyInput" class="field-input" type="password" placeholder="Admin parolini kiriting" required />
          <button type="button" class="pw-eye" data-target="adminKeyInput" title="Ko'rsatish / yashirish" aria-label="Parolni ko'rsatish">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
        <button type="submit" class="btn btn-primary btn-sm">Kabinetga kirish</button>
        <button type="button" id="adminLogoutBtn" class="btn btn-ghost btn-sm hidden">Chiqish</button>
      </form>
      <div id="adminLoginErr" class="admin-note" style="color:#b91c1c;"></div>

      <div id="adminBody" class="hidden" style="margin-top:20px;">
        <h3 style="font-size:15px; margin:0 0 6px;">1. API Kalitlari va Model</h3>
        <p style="font-size:13px; color:var(--text-muted); margin:0 0 10px;">Bo'sh qoldirilgan maxfiy kalit o'zgarmaydi. Saqlangandan so'ng darhol kuchga kiradi.</p>
        <form id="adminSettingsForm">
          <div class="admin-grid">
            <div>
              <label class="field-label">GEMINI_API_KEY <span id="geminiMask" style="color:#047857;"></span></label>
              <div class="pw-wrap">
                <input id="cfgGeminiKey" class="field-input" type="password" placeholder="Yangi Gemini kaliti (o'zgartirmaslik uchun bo'sh qoldiring)" />
                <button type="button" class="pw-eye" data-target="cfgGeminiKey" title="Ko'rsatish / yashirish" aria-label="Kalitni ko'rsatish">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
              </div>
            </div>
            <div>
              <label class="field-label">GEMINI_MODEL</label>
              <input id="cfgGeminiModel" class="field-input" type="text" placeholder="gemini-3.6-flash" />
            </div>
            <div>
              <label class="field-label">ELEVENLABS_API_KEY (VIP) <span id="elMask" style="color:#047857;"></span></label>
              <div class="pw-wrap">
                <input id="cfgElKey" class="field-input" type="password" placeholder="ElevenLabs API kaliti (ixtiyoriy)" />
                <button type="button" class="pw-eye" data-target="cfgElKey" title="Ko'rsatish / yashirish" aria-label="Kalitni ko'rsatish">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
              </div>
            </div>
            <div>
              <label class="field-label">ELEVENLABS_VOICE_ID</label>
              <input id="cfgElVoice" class="field-input" type="text" placeholder="JBFqnCBsd6RMkjVDRZzb" />
            </div>
          </div>
          <div style="margin-top:12px; display:flex; align-items:center; gap:12px;">
            <button type="submit" class="btn btn-primary btn-sm">API sozlamalarini saqlash</button>
            <span id="settingsMsg" class="admin-note" style="margin:0; color:#047857;"></span>
          </div>
        </form>

        <hr style="border:none; border-top:1px solid var(--border); margin:22px 0;" />

        <h3 style="font-size:15px; margin:0 0 8px;">2. Obunachilar (Foydalanuvchilar)</h3>
        <form id="adminAddUserForm" style="display:flex; gap:8px; flex-wrap:wrap; align-items:flex-end;">
          <div>
            <label class="field-label">Ism</label>
            <input id="newUserName" class="field-input" style="width:150px;" type="text" placeholder="Ali" required />
          </div>
          <div>
            <label class="field-label">Parol (bo'sh = avto)</label>
            <input id="newUserKey" class="field-input" style="width:150px;" type="text" placeholder="UZ-1234" />
          </div>
          <div>
            <label class="field-label">Muddat (kun)</label>
            <input id="newUserDays" class="field-input" style="width:90px;" type="number" value="30" min="1" />
          </div>
          <div>
            <label class="field-label">Kunlik VIP limit</label>
            <input id="newUserLimit" class="field-input" style="width:105px;" type="number" value="20" min="0" />
          </div>
          <label style="display:flex; align-items:center; gap:6px; font-size:13px; padding-bottom:10px; cursor:pointer;">
            <input id="newUserVip" type="checkbox" /> VIP ovoz
          </label>
          <button type="submit" class="btn btn-primary btn-sm" style="margin-bottom:2px;">+ Qo'shish</button>
        </form>
        <div id="usersMsg" class="admin-note" style="color:#047857;"></div>

        <div style="overflow-x:auto;">
          <table class="admin-table">
            <thead>
              <tr>
                <th>Ism</th>
                <th>Parol</th>
                <th>Muddat</th>
                <th>VIP (bugun/limit)</th>
                <th>Holat</th>
                <th>Amallar</th>
              </tr>
            </thead>
            <tbody id="adminUsersBody"></tbody>
          </table>
        </div>

        <hr style="border:none; border-top:1px solid var(--border); margin:22px 0;" />

        <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
          <h3 style="font-size:15px; margin:0;">3. API Sarfi va Balans</h3>
          <button type="button" id="refreshUsageBtn" class="btn-xs">Yangilash</button>
        </div>
        <div class="admin-grid" style="margin-top:10px;">
          <div style="padding:12px; border:1px solid var(--border); border-radius:10px; background:#f8fafc;">
            <div style="font-size:12px; font-weight:700; color:var(--text-muted);">GEMINI (ILOVA ORQALI)</div>
            <div id="geminiUsageText" style="margin-top:6px; font-size:13.5px; font-weight:600;">Yuklanmoqda...</div>
            <a class="link-inline" style="font-size:12px; display:inline-block; margin-top:6px;" href="https://aistudio.google.com/usage" target="_blank" rel="noreferrer">Google AI Studio kvotasini ochish ↗</a>
          </div>
          <div style="padding:12px; border:1px solid var(--border); border-radius:10px; background:#f8fafc;">
            <div style="font-size:12px; font-weight:700; color:var(--text-muted);">ELEVENLABS (VIP BALANS)</div>
            <div id="elUsageText" style="margin-top:6px; font-size:13.5px; font-weight:600;">Yuklanmoqda...</div>
            <a class="link-inline" style="font-size:12px; display:inline-block; margin-top:6px;" href="https://elevenlabs.io/app/subscription" target="_blank" rel="noreferrer">ElevenLabs obunasini ochish ↗</a>
          </div>
        </div>

        <hr style="border:none; border-top:1px solid var(--border); margin:22px 0;" />

        <h3 style="font-size:15px; margin:0 0 8px;">4. Admin parolini o'zgartirish</h3>
        <form id="adminChangePwForm" style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
          <div class="pw-wrap" style="max-width:280px;">
            <input id="newAdminKeyInput" class="field-input" type="password" minlength="6" placeholder="Yangi admin paroli (kamida 6 belgi)" required />
            <button type="button" class="pw-eye" data-target="newAdminKeyInput" title="Ko'rsatish / yashirish" aria-label="Parolni ko'rsatish">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
          </div>
          <button type="submit" class="btn btn-primary btn-sm">Parolni yangilash</button>
          <span id="adminPwMsg" class="admin-note" style="margin:0; color:#047857;"></span>
        </form>
      </div>
    </section>
  </main>

  <script>
    const keyForm = document.getElementById("keyForm");
    const accessKeyInput = document.getElementById("accessKeyInput");
    const checkBtn = document.getElementById("checkBtn");
    const resultBox = document.getElementById("resultBox");
    const resultBanner = document.getElementById("resultBanner");
    const statusBadge = document.getElementById("statusBadge");
    const latencyBadge = document.getElementById("latencyBadge");
    const resultJson = document.getElementById("resultJson");

    function setBanner(isOk, message) {{
      resultBanner.replaceChildren();
      const ns = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(ns, "svg");
      svg.setAttribute("width", "18");
      svg.setAttribute("height", "18");
      svg.setAttribute("viewBox", "0 0 24 24");
      svg.setAttribute("fill", "none");
      const path = document.createElementNS(ns, "path");
      path.setAttribute("stroke", "currentColor");
      path.setAttribute("stroke-width", "2.2");
      path.setAttribute("stroke-linecap", "round");
      path.setAttribute("stroke-linejoin", "round");
      path.setAttribute("d", isOk ? "M5 13l4 4L19 7" : "M18 6L6 18M6 6l12 12");
      svg.appendChild(path);
      const span = document.createElement("span");
      span.textContent = message;
      resultBanner.appendChild(svg);
      resultBanner.appendChild(span);
      resultBanner.style.color = isOk ? "#047857" : "#b91c1c";
    }}

    async function runCheck(keyValue) {{
      checkBtn.disabled = true;
      checkBtn.textContent = "Tekshirilmoqda...";
      const started = performance.now();
      try {{
        const response = await fetch("/check-key", {{
          method: "GET",
          headers: {{ "X-Access-Key": keyValue }}
        }});
        const elapsed = Math.round(performance.now() - started);
        const text = await response.text();
        let parsed;
        try {{
          parsed = JSON.parse(text);
        }} catch {{
          parsed = {{ raw: text }};
        }}

        resultBox.classList.remove("hidden");
        latencyBadge.textContent = elapsed + " ms";
        resultJson.textContent = JSON.stringify(parsed, null, 2);

        if (response.ok) {{
          statusBadge.className = "pill pill-emerald";
          statusBadge.textContent = response.status + " OK";
          setBanner(true, "Faol: " + (parsed && parsed.user ? parsed.user : "Tasdiqlandi"));
        }} else {{
          statusBadge.className = "pill pill-rose";
          statusBadge.textContent = response.status + " Unauthorized";
          setBanner(false, parsed && parsed.detail ? parsed.detail : "Ruxsat berilmadi");
        }}
      }} catch (err) {{
        resultBox.classList.remove("hidden");
        statusBadge.className = "pill pill-rose";
        statusBadge.textContent = "Xatolik";
        latencyBadge.textContent = "";
        setBanner(false, "Server bilan bog'lanib bo'lmadi");
        resultJson.textContent = String(err);
      }} finally {{
        checkBtn.disabled = false;
        checkBtn.textContent = "Tekshirish";
      }}
    }}

    keyForm.addEventListener("submit", (event) => {{
      event.preventDefault();
      runCheck(accessKeyInput.value.trim());
    }});

    document.querySelectorAll(".quick-pill").forEach((btn) => {{
      btn.addEventListener("click", () => {{
        const value = btn.getAttribute("data-key") || "";
        accessKeyInput.value = value;
        runCheck(value);
      }});
    }});

    // --- Admin Kabinet ---
    const adminLoginForm = document.getElementById("adminLoginForm");
    const adminKeyInput = document.getElementById("adminKeyInput");
    const adminLogoutBtn = document.getElementById("adminLogoutBtn");
    const adminAuthBadge = document.getElementById("adminAuthBadge");
    const adminLoginErr = document.getElementById("adminLoginErr");
    const adminBody = document.getElementById("adminBody");
    const adminSettingsForm = document.getElementById("adminSettingsForm");
    const adminAddUserForm = document.getElementById("adminAddUserForm");
    const adminUsersBody = document.getElementById("adminUsersBody");
    const settingsMsg = document.getElementById("settingsMsg");
    const usersMsg = document.getElementById("usersMsg");

    function getAdminKey() {{
      return sessionStorage.getItem("yt_uz_admin_key") || "";
    }}

    async function adminFetch(path, options = {{}}) {{
      const key = getAdminKey();
      const headers = Object.assign({{}}, options.headers || {{}}, {{ "X-Access-Key": key }});
      return fetch(path, Object.assign({{}}, options, {{ headers }}));
    }}

    async function loadAdminData() {{
      const resCfg = await adminFetch("/admin/settings");
      if (!resCfg.ok) {{
        sessionStorage.removeItem("yt_uz_admin_key");
        adminBody.classList.add("hidden");
        adminLogoutBtn.classList.add("hidden");
        adminAuthBadge.className = "pill pill-rose";
        adminAuthBadge.textContent = "Ruxsat rad etildi";
        adminLoginErr.textContent = "Admin paroli noto'g'ri yoki ruxsati yo'q.";
        return false;
      }}
      const cfg = await resCfg.json();
      adminLoginErr.textContent = "";
      adminBody.classList.remove("hidden");
      adminLogoutBtn.classList.remove("hidden");
      adminAuthBadge.className = "pill pill-emerald";
      adminAuthBadge.textContent = "Admin faol";

      document.getElementById("geminiMask").textContent = cfg.gemini_configured ? "(" + cfg.gemini_api_key_masked + ")" : "(kiritilmagan)";
      document.getElementById("elMask").textContent = cfg.elevenlabs_configured ? "(" + cfg.elevenlabs_api_key_masked + ")" : "(kiritilmagan)";
      document.getElementById("cfgGeminiModel").value = cfg.gemini_model || "";
      document.getElementById("cfgElVoice").value = cfg.elevenlabs_voice_id || "";

      const resUsers = await adminFetch("/admin/users");
      if (resUsers.ok) {{
        const data = await resUsers.json();
        renderUsersTable(data.users || []);
      }}
      await loadAdminUsage();
      return true;
    }}

    async function loadAdminUsage() {{
      const gEl = document.getElementById("geminiUsageText");
      const eEl = document.getElementById("elUsageText");
      const res = await adminFetch("/admin/usage");
      if (!res.ok) return;
      const d = await res.json();
      const g = d.gemini || {{}};
      gEl.textContent = `Bugun: ${{g.today_calls || 0}} so'rov (${{(g.today_tokens || 0).toLocaleString()}} token) · Jami: ${{g.total_calls || 0}} so'rov`;
      const el = d.elevenlabs || {{}};
      if (!el.configured) {{
        eEl.textContent = "ELEVENLABS_API_KEY kiritilmagan";
      }} else if (el.ok) {{
        eEl.textContent = `Qoldi: ${{el.remaining.toLocaleString()}} belgi (Ishlatildi: ${{el.character_count.toLocaleString()}} / ${{el.character_limit.toLocaleString()}})`;
      }} else {{
        eEl.textContent = "Balansni olishda xato: " + (el.error || "noma'lum");
      }}
    }}

    document.getElementById("refreshUsageBtn").addEventListener("click", loadAdminUsage);

    document.getElementById("adminChangePwForm").addEventListener("submit", async (e) => {{
      e.preventDefault();
      const pwMsg = document.getElementById("adminPwMsg");
      const newKey = document.getElementById("newAdminKeyInput").value.trim();
      const res = await adminFetch("/change-key", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ new_key: newKey }}),
      }});
      const data = await res.json().catch(() => ({{}}));
      if (res.ok) {{
        sessionStorage.setItem("yt_uz_admin_key", data.access_key);
        document.getElementById("newAdminKeyInput").value = "";
        pwMsg.style.color = "#047857";
        pwMsg.textContent = "Admin paroli yangilandi!";
        loadAdminData();
      }} else {{
        pwMsg.style.color = "#b91c1c";
        pwMsg.textContent = data.detail || "Xatolik";
      }}
    }});

    function renderUsersTable(users) {{
      adminUsersBody.replaceChildren();
      users.forEach((u) => {{
        const tr = document.createElement("tr");
        const exp = u.expires_at ? u.expires_at.slice(0, 10) : "Cheksiz";
        const vipText = u.allow_vip ? `Ha (${{u.vip_used_today}}/${{u.vip_daily_limit}})` : "Yo'q";
        const activeText = u.is_active ? "Faol" : "Bloklangan";

        tr.innerHTML = `
          <td><strong></strong></td>
          <td><code></code></td>
          <td></td>
          <td></td>
          <td></td>
          <td style="display:flex; gap:6px; flex-wrap:wrap;"></td>
        `;
        tr.children[0].querySelector("strong").textContent = u.name + (u.is_admin ? " (Admin)" : "");
        tr.children[1].querySelector("code").textContent = u.access_key;
        tr.children[2].textContent = exp;
        tr.children[3].textContent = vipText;
        tr.children[4].textContent = activeText;
        tr.children[4].style.color = u.is_active ? "#047857" : "#b91c1c";

        const actionsTd = tr.children[5];
        if (!u.is_admin) {{
          const toggleActive = document.createElement("button");
          toggleActive.className = "btn-xs";
          toggleActive.textContent = u.is_active ? "Bloklash" : "Yoqish";
          toggleActive.onclick = async () => {{
            await adminFetch("/admin/users/" + encodeURIComponent(u.access_key), {{
              method: "PATCH",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{ is_active: !u.is_active }})
            }});
            loadAdminData();
          }};

          const toggleVip = document.createElement("button");
          toggleVip.className = "btn-xs";
          toggleVip.textContent = u.allow_vip ? "VIP o'chirish" : "VIP yoqish";
          toggleVip.onclick = async () => {{
            await adminFetch("/admin/users/" + encodeURIComponent(u.access_key), {{
              method: "PATCH",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{ allow_vip: !u.allow_vip, vip_daily_limit: u.vip_daily_limit || 20 }})
            }});
            loadAdminData();
          }};

          const delBtn = document.createElement("button");
          delBtn.className = "btn-xs btn-xs-danger";
          delBtn.textContent = "O'chirish";
          delBtn.onclick = async () => {{
            await adminFetch("/admin/users/" + encodeURIComponent(u.access_key), {{ method: "DELETE" }});
            loadAdminData();
          }};
          actionsTd.append(toggleActive, toggleVip, delBtn);
        }}
        adminUsersBody.appendChild(tr);
      }});
    }}

    adminLoginForm.addEventListener("submit", async (e) => {{
      e.preventDefault();
      sessionStorage.setItem("yt_uz_admin_key", adminKeyInput.value.trim());
      await loadAdminData();
    }});

    adminLogoutBtn.addEventListener("click", () => {{
      sessionStorage.removeItem("yt_uz_admin_key");
      adminBody.classList.add("hidden");
      adminLogoutBtn.classList.add("hidden");
      adminAuthBadge.className = "pill";
      adminAuthBadge.textContent = "Kirilmagan";
    }});

    adminSettingsForm.addEventListener("submit", async (e) => {{
      e.preventDefault();
      const payload = {{
        gemini_model: document.getElementById("cfgGeminiModel").value.trim(),
        elevenlabs_voice_id: document.getElementById("cfgElVoice").value.trim(),
      }};
      const gKey = document.getElementById("cfgGeminiKey").value.trim();
      const eKey = document.getElementById("cfgElKey").value.trim();
      if (gKey) payload.gemini_api_key = gKey;
      if (eKey) payload.elevenlabs_api_key = eKey;
      const res = await adminFetch("/admin/settings", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
      if (res.ok) {{
        document.getElementById("cfgGeminiKey").value = "";
        document.getElementById("cfgElKey").value = "";
        settingsMsg.textContent = "Saqlandi va darhol kuchga kirdi!";
        loadAdminData();
      }}
    }});

    adminAddUserForm.addEventListener("submit", async (e) => {{
      e.preventDefault();
      const res = await adminFetch("/admin/users", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          name: document.getElementById("newUserName").value.trim(),
          access_key: document.getElementById("newUserKey").value.trim(),
          days: Number(document.getElementById("newUserDays").value) || 30,
          vip_daily_limit: Number(document.getElementById("newUserLimit").value) || 0,
          allow_vip: document.getElementById("newUserVip").checked,
        }}),
      }});
      if (res.ok) {{
        const data = await res.json();
        document.getElementById("newUserName").value = "";
        document.getElementById("newUserKey").value = "";
        usersMsg.textContent = "Qo'shildi! Parol: " + data.user.access_key;
        loadAdminData();
      }} else {{
        const err = await res.json().catch(() => ({{}}));
        usersMsg.textContent = err.detail || "Xatolik";
      }}
    }});

    if (getAdminKey()) {{
      loadAdminData();
    }}

    document.querySelectorAll(".pw-eye").forEach((btn) => {{
      btn.addEventListener("click", () => {{
        const input = document.getElementById(btn.getAttribute("data-target"));
        if (!input) return;
        const show = input.type === "password";
        input.type = show ? "text" : "password";
        btn.style.color = show ? "var(--accent)" : "var(--text-muted)";
      }});
    }});
  </script>
</body>
</html>"""


def render_swagger_html(openapi_url: str, title: str) -> str:
    """Render FastAPI Swagger UI wrapped with a cohesive bright studio-light theme."""
    response = get_swagger_ui_html(
        openapi_url=openapi_url,
        title=title,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 1,
            "docExpansion": "list",
            "displayRequestDuration": True,
            "persistAuthorization": True,
        },
    )
    html = response.body.decode("utf-8")

    custom_css = """<style>
  :root {
    --bg: #f4f7fb;
    --surface: #ffffff;
    --surface-soft: #f8fafc;
    --border: #e2e8f0;
    --border-strong: #cbd5e1;
    --text: #0f172a;
    --text-muted: #475569;
    --text-dim: #64748b;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
    --emerald: #059669;
    --code-bg: #1e293b;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, "Helvetica Neue", Arial, sans-serif;
    --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  }
  html, body {
    margin: 0;
    padding: 0;
    min-height: 100vh;
    color-scheme: light;
    background-color: var(--bg) !important;
    background-image:
      radial-gradient(ellipse 85% 45% at 50% -10%, rgba(37, 99, 235, 0.08), transparent 70%) !important;
    color: var(--text) !important;
    font-family: var(--sans);
    font-size: 15px;
    -webkit-font-smoothing: antialiased;
  }
  .yt-studio-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(12px);
    background: rgba(255, 255, 255, 0.92);
    border-bottom: 1px solid var(--border);
    box-shadow: 0 2px 12px -6px rgba(15, 23, 42, 0.08);
    color: var(--text);
  }
  .yt-studio-bar-inner {
    max-width: 1060px;
    margin: 0 auto;
    padding: 13px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }
  .yt-studio-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.015em;
    color: var(--text);
  }
  .yt-studio-icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: var(--accent);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .yt-studio-ver {
    padding: 4px 11px;
    border-radius: 999px;
    font-size: 12.5px;
    font-weight: 600;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1d4ed8;
  }
  .yt-studio-back {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 40px;
    padding: 0 16px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    text-decoration: none;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
  }
  .yt-studio-back:hover {
    background: #eff6ff;
    border-color: #93c5fd;
    color: var(--accent-hover);
  }
  .swagger-ui {
    color: var(--text) !important;
    font-family: var(--sans) !important;
  }
  .swagger-ui .topbar { display: none !important; }
  .swagger-ui .wrapper {
    max-width: 1060px;
    padding: 0 24px;
  }
  .swagger-ui .information-container.wrapper {
    padding-top: 32px;
    padding-bottom: 12px;
  }
  .swagger-ui .info {
    margin: 0 0 12px;
    padding: 24px 28px;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px;
    box-shadow: 0 4px 20px -6px rgba(15, 23, 42, 0.07);
  }
  .swagger-ui .info .title {
    font-size: 26px !important;
    font-weight: 750 !important;
    letter-spacing: -0.025em;
    color: var(--text) !important;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
  }
  .swagger-ui .info .title small {
    border-radius: 999px !important;
    padding: 4px 11px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    background: #2563eb !important;
  }
  .swagger-ui .info .title small pre {
    color: #ffffff !important;
    background: transparent !important;
  }
  .swagger-ui .info .title small.version-stamp {
    background: #059669 !important;
  }
  .swagger-ui .info a {
    color: var(--accent) !important;
    font-weight: 600;
  }
  .swagger-ui .info p,
  .swagger-ui .info li,
  .swagger-ui .renderedMarkdown p {
    color: var(--text-muted) !important;
    font-size: 15px !important;
    margin-top: 8px;
  }
  .swagger-ui .scheme-container {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px;
    margin: 0 auto 18px !important;
    padding: 16px 24px !important;
    box-shadow: 0 4px 20px -6px rgba(15, 23, 42, 0.06) !important;
  }
  .swagger-ui .opblock-tag {
    border-bottom: 1px solid var(--border) !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    color: var(--text) !important;
    padding: 14px 4px !important;
    margin-bottom: 14px !important;
  }
  .swagger-ui .opblock-tag:hover {
    background: rgba(37, 99, 235, 0.03) !important;
  }
  .swagger-ui .opblock-tag small {
    color: var(--text-muted) !important;
    font-size: 14px !important;
    font-weight: 450 !important;
  }
  .swagger-ui .opblock-tag svg,
  .swagger-ui .opblock-summary-control svg,
  .swagger-ui .opblock-control-arrow svg,
  .swagger-ui section.models h4 svg {
    fill: #334155 !important;
    width: 20px !important;
    height: 20px !important;
  }
  .swagger-ui .opblock-summary-control,
  .swagger-ui .opblock-control-arrow {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
  }
  .swagger-ui .opblock {
    border-radius: 14px !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    box-shadow: 0 4px 16px -6px rgba(15, 23, 42, 0.07) !important;
    overflow: hidden;
    margin-bottom: 14px !important;
  }
  .swagger-ui .opblock .opblock-summary {
    padding: 12px 16px !important;
    border-bottom: 1px solid transparent !important;
  }
  .swagger-ui .opblock.opblock-get {
    border-color: #bfdbfe !important;
    background: var(--surface) !important;
  }
  .swagger-ui .opblock.opblock-get .opblock-summary {
    background: #f8fbff !important;
  }
  .swagger-ui .opblock.opblock-get.is-open .opblock-summary {
    border-bottom-color: #dbeafe !important;
  }
  .swagger-ui .opblock.opblock-get .opblock-summary-method {
    background: #2563eb !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    min-width: 72px !important;
    padding: 7px 12px !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    text-shadow: none !important;
  }
  .swagger-ui .opblock.opblock-post {
    border-color: #a7f3d0 !important;
    background: var(--surface) !important;
  }
  .swagger-ui .opblock.opblock-post .opblock-summary {
    background: #f4fdf9 !important;
  }
  .swagger-ui .opblock.opblock-post.is-open .opblock-summary {
    border-bottom-color: #d1fae5 !important;
  }
  .swagger-ui .opblock.opblock-post .opblock-summary-method {
    background: #059669 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    min-width: 72px !important;
    padding: 7px 12px !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    text-shadow: none !important;
  }
  .swagger-ui .opblock-summary-path {
    font-family: var(--mono) !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: var(--text) !important;
  }
  .swagger-ui .opblock-summary-description {
    color: var(--text-muted) !important;
    font-size: 14px !important;
  }
  .swagger-ui .opblock-body,
  .swagger-ui .opblock-description-wrapper,
  .swagger-ui .responses-wrapper {
    background: var(--surface) !important;
    color: var(--text) !important;
  }
  .swagger-ui .opblock .opblock-section-header {
    background: var(--surface-soft) !important;
    border-top: 1px solid var(--border) !important;
    border-bottom: 1px solid var(--border) !important;
    box-shadow: none !important;
  }
  .swagger-ui .opblock .opblock-section-header h4,
  .swagger-ui .opblock .opblock-section-header label,
  .swagger-ui .responses-inner h4,
  .swagger-ui .responses-inner h5 {
    color: var(--text) !important;
    font-weight: 700 !important;
  }
  .swagger-ui table thead tr td,
  .swagger-ui table thead tr th {
    color: var(--text-muted) !important;
    font-weight: 700 !important;
    border-bottom: 1px solid var(--border) !important;
  }
  .swagger-ui table tbody tr td,
  .swagger-ui .parameters-col_description,
  .swagger-ui .response-col_status,
  .swagger-ui .response-col_description,
  .swagger-ui .response-col_links {
    color: var(--text) !important;
    font-size: 14px !important;
    border-bottom-color: var(--border) !important;
  }
  .swagger-ui .parameter__name {
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 14px !important;
    font-weight: 700 !important;
  }
  .swagger-ui .parameter__name.required span,
  .swagger-ui .parameter__name.required::after {
    color: #dc2626 !important;
  }
  .swagger-ui .parameter__type {
    color: var(--accent) !important;
    font-family: var(--mono) !important;
    font-weight: 600 !important;
  }
  .swagger-ui .parameter__in,
  .swagger-ui .parameter__deprecated {
    color: var(--text-dim) !important;
  }
  .swagger-ui .tab li button.tablinks {
    color: var(--text-muted) !important;
    font-weight: 600 !important;
  }
  .swagger-ui .tab li.active button.tablinks {
    color: var(--text) !important;
    font-weight: 700 !important;
  }
  .swagger-ui input[type=text],
  .swagger-ui input[type=password],
  .swagger-ui input[type=search],
  .swagger-ui textarea,
  .swagger-ui select {
    background: #ffffff !important;
    color: var(--text) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 9px !important;
    padding: 8px 12px !important;
    font-family: var(--mono);
    font-size: 14px !important;
  }
  .swagger-ui textarea {
    min-height: 120px;
  }
  .swagger-ui input[type=text]::placeholder,
  .swagger-ui textarea::placeholder {
    color: #94a3b8 !important;
  }
  .swagger-ui input[type=text]:focus,
  .swagger-ui input[type=password]:focus,
  .swagger-ui textarea:focus,
  .swagger-ui select:focus {
    border-color: var(--accent) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14) !important;
  }
  .swagger-ui .btn {
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 7px 14px !important;
    box-shadow: none !important;
    transition: background 0.15s ease, border-color 0.15s ease;
  }
  .swagger-ui .btn.try-out__btn {
    background: #eff6ff !important;
    border: 1px solid #bfdbfe !important;
    color: #1d4ed8 !important;
  }
  .swagger-ui .btn.try-out__btn:hover {
    background: #dbeafe !important;
    border-color: #93c5fd !important;
  }
  .swagger-ui .btn.cancel {
    background: #fef2f2 !important;
    border: 1px solid #fecaca !important;
    color: #b91c1c !important;
  }
  .swagger-ui .btn.execute {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #ffffff !important;
  }
  .swagger-ui .btn.execute:hover {
    background: var(--accent-hover) !important;
  }
  .swagger-ui .btn.btn-clear {
    background: var(--surface-soft) !important;
    border: 1px solid var(--border-strong) !important;
    color: var(--text-muted) !important;
  }
  .swagger-ui .microlight,
  .swagger-ui .highlight-code pre,
  .swagger-ui .responses-table pre,
  .swagger-ui pre.example {
    border-radius: 10px !important;
    padding: 14px 16px !important;
    background: var(--code-bg) !important;
    border: 1px solid #334155 !important;
    color: #f8fafc !important;
    font-family: var(--mono) !important;
    font-size: 13.5px !important;
  }
  .swagger-ui .copy-to-clipboard,
  .swagger-ui .download-contents {
    background: rgba(255, 255, 255, 0.12) !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
    border-radius: 7px !important;
    color: #ffffff !important;
  }
  .swagger-ui .copy-to-clipboard button {
    filter: invert(1) brightness(1.1);
  }
  .swagger-ui .response-control-media-type__accept-message {
    color: #047857 !important;
    font-weight: 600;
  }
  .swagger-ui section.models {
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    background: var(--surface) !important;
    box-shadow: 0 4px 20px -6px rgba(15, 23, 42, 0.07) !important;
    margin: 24px 0 48px !important;
    overflow: hidden;
  }
  .swagger-ui section.models h4 {
    margin: 0 !important;
    padding: 16px 20px !important;
    border-bottom: 1px solid var(--border) !important;
    color: var(--text) !important;
  }
  .swagger-ui section.models h4 button.models-control {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: var(--text) !important;
    font-size: 17px !important;
    font-weight: 700 !important;
    padding: 0 !important;
  }
  .swagger-ui section.models .model-container {
    background: var(--surface-soft) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    margin: 12px 18px !important;
    padding: 12px 16px !important;
  }
  .swagger-ui button.model-box-control {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: var(--text) !important;
    font-size: 15px !important;
    font-weight: 650 !important;
    padding: 4px 6px !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
  }
  .swagger-ui .model-title {
    color: var(--text) !important;
    font-size: 15px !important;
    font-weight: 650 !important;
  }
  .swagger-ui .model-toggle {
    background: transparent !important;
    border: none !important;
    top: 0 !important;
  }
  .swagger-ui .model-box button:not(.model-box-control):not(.model-toggle) {
    background: #eff6ff !important;
    color: #1d4ed8 !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 6px !important;
    padding: 3px 10px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    margin-left: 8px !important;
    cursor: pointer;
  }
  .swagger-ui .model-box button:not(.model-box-control):not(.model-toggle):hover {
    background: #dbeafe !important;
  }
  .swagger-ui .model,
  .swagger-ui .prop-name {
    color: #1e293b !important;
    font-size: 14px !important;
  }
  .swagger-ui .prop-type {
    color: var(--accent) !important;
    font-weight: 600 !important;
  }
  .swagger-ui .prop-format {
    color: var(--text-dim) !important;
  }
</style>"""

    top_bar = f"""<header class="yt-studio-bar">
  <div class="yt-studio-bar-inner">
    <div class="yt-studio-brand">
      <span class="yt-studio-icon">{_LOGO_SVG}</span>
      <span>YouTube O'zbekcha Tarjimon API</span>
      <span class="yt-studio-ver">v2.0</span>
    </div>
    <a class="yt-studio-back" href="/">{_BACK_ARROW_SVG} Boshqaruv paneli</a>
  </div>
</header>"""

    html = html.replace("</head>", f"{custom_css}\n</head>", 1)
    html = html.replace("<body>", f"<body>\n{top_bar}", 1)
    return html
