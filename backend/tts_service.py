import os
from pathlib import Path
import re

import edge_tts
import httpx

_UPPER_ACRONYMS = {
    "IT": "ayti",
    "AI": "ey-ay",
    "API": "ey-pi-ay",
    "IP": "ay-pi",
    "URL": "yu-ar-el",
    "VPN": "vi-pi-en",
    "DNS": "di-en-es",
    "HTTP": "eych-ti-ti-pi",
    "HTTPS": "eych-ti-ti-pi-es",
    "SQL": "es-kyu-el",
    "HTML": "eych-ti-em-el",
    "CSS": "si-es-es",
    "JSON": "jeyson",
    "UI": "yu-ay",
    "UX": "yu-eks",
    "CPU": "si-pi-yu",
    "GPU": "ji-pi-yu",
    "RAM": "ram",
    "OS": "o-es",
    "ID": "ay-di",
    "SDK": "es-di-key",
    "VPS": "vi-pi-es",
    "SSH": "es-es-eych",
    "SSL": "es-es-el",
    "TLS": "ti-el-es",
    "PDF": "pi-di-ef",
    "USB": "yu-es-bi",
    "CLI": "si-el-ay",
    "MVP": "em-vi-pi",
    "DDoS": "di-dos",
    "DDOS": "di-dos",
}

_TECH_WORDS_CI = {
    "wi-fi": "vay-fay",
    "wifi": "vay-fay",
    "youtube": "Yutub",
    "facebook": "Feysbuk",
    "google": "Gugl",
    "python": "Payton",
    "javascript": "JavaSkript",
    "typescript": "TaypSkript",
    "framework": "freymvork",
    "backend": "bekend",
    "frontend": "frontend",
}

_UPPER_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_UPPER_ACRONYMS, key=len, reverse=True)) + r")\b"
)
_CI_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_TECH_WORDS_CI, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def normalize_for_uzbek_tts(text: str) -> str:
    """Convert IT/tech acronyms and English brand terms to Uzbek phonetic spelling for edge-tts."""
    out = _UPPER_RE.sub(lambda m: _UPPER_ACRONYMS[m.group(1)], text)
    out = _CI_RE.sub(lambda m: _TECH_WORDS_CI[m.group(1).lower()], out)
    return out

EDGE_VOICES = {
    "sardor": "uz-UZ-SardorNeural",
    "madina": "uz-UZ-MadinaNeural",
}
VALID_VOICES = {"sardor", "madina", "elevenlabs"}
DEFAULT_ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"


class TTSConfigError(ValueError):
    """Raised when an invalid voice or missing ElevenLabs key is requested."""


def validate_voice(voice: str) -> str:
    """Normalize and validate the requested TTS voice mode."""
    voice_key = voice.strip().lower()
    if voice_key not in VALID_VOICES:
        raise TTSConfigError(
            "Noto'g'ri ovoz turi. Ruxsat etilgan: sardor, madina, elevenlabs"
        )

    if voice_key == "elevenlabs" and not os.getenv("ELEVENLABS_API_KEY", "").strip():
        raise TTSConfigError("ELEVENLABS_API_KEY sozlanmagan")

    return voice_key


async def synthesize_text(text: str, voice: str, output_path: Path) -> Path:
    """Synthesize Uzbek text into an MP3 file using edge-tts or ElevenLabs."""
    voice_key = validate_voice(voice)
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Bo'sh matn ovozlashtirib bo'lmaydi")

    if voice_key in EDGE_VOICES:
        tts_text = normalize_for_uzbek_tts(cleaned)
        communicate = edge_tts.Communicate(
            text=tts_text,
            voice=EDGE_VOICES[voice_key],
            rate="+10%",
        )
        await communicate.save(str(output_path))
        return output_path

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_ELEVENLABS_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": cleaned,
        "model_id": "eleven_flash_v2_5",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code >= 400:
        raise RuntimeError(
            f"ElevenLabs xatoligi ({response.status_code}): {response.text[:300]}"
        )

    output_path.write_bytes(response.content)
    return output_path
