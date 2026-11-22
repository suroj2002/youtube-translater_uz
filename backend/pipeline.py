import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import parse_qs, urlparse

from google import genai
from google.genai import types
from pydantic import BaseModel
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    YouTubeTranscriptApiException,
)

from database import record_gemini_usage
from tts_service import synthesize_text


class TranscriptNotFoundError(Exception):
    """Raised when a YouTube video has no usable captions."""


class PipelineConfigError(ValueError):
    """Raised when required translation configuration (e.g. GEMINI_API_KEY) is missing."""


class TranslatedSegment(BaseModel):
    """Single translated subtitle segment returned by Gemini."""

    start: float
    text: str


class TranslationPayload(BaseModel):
    """Structured JSON wrapper returned by Gemini translation."""

    segments: list[TranslatedSegment]


def normalize_video_id(raw: str) -> str:
    """Extract a YouTube video ID from a URL or return the stripped ID string."""
    cleaned = raw.strip()
    if not cleaned:
        return ""

    if cleaned.startswith(
        ("www.youtube.com/", "youtube.com/", "m.youtube.com/", "youtu.be/")
    ):
        cleaned = f"https://{cleaned}"

    if cleaned.startswith(("http://", "https://")):
        parsed = urlparse(cleaned)
        host = parsed.netloc.lower()
        parts = [p for p in parsed.path.split("/") if p]
        if host.endswith("youtu.be") and parts:
            return parts[0]

        query_v = parse_qs(parsed.query).get("v")
        if query_v and query_v[0]:
            return query_v[0].strip()

        for marker in ("shorts", "embed", "live"):
            if marker in parts:
                idx = parts.index(marker)
                if idx + 1 < len(parts):
                    return parts[idx + 1]

    return cleaned


def fetch_transcript(video_id: str) -> list[dict]:
    """Fetch en/ru captions or fall back to any available YouTube transcript."""
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
    except (RequestBlocked, IpBlocked) as exc:
        raise TranscriptNotFoundError(
            "YouTube subtitr so'rovini vaqtincha blokladi, birozdan keyin urinib ko'ring"
        ) from exc
    except YouTubeTranscriptApiException as exc:
        raise TranscriptNotFoundError("Bu videoda tayyor subtitr yo'q") from exc

    try:
        transcript = transcript_list.find_transcript(
            ["en", "ru", "en-US", "en-GB", "ru-RU"]
        )
    except NoTranscriptFound:
        available = list(transcript_list)
        if not available:
            raise TranscriptNotFoundError("Bu videoda tayyor subtitr yo'q")
        manual = next((t for t in available if not t.is_generated), None)
        transcript = manual or available[0]

    try:
        raw_items = transcript.fetch().to_raw_data()
    except (RequestBlocked, IpBlocked) as exc:
        raise TranscriptNotFoundError(
            "YouTube subtitr so'rovini vaqtincha blokladi, birozdan keyin urinib ko'ring"
        ) from exc
    except YouTubeTranscriptApiException as exc:
        raise TranscriptNotFoundError("Bu videoda tayyor subtitr yo'q") from exc

    cleaned: list[dict] = []
    for item in raw_items:
        text = " ".join(str(item.get("text", "")).split())
        if not text:
            continue
        cleaned.append(
            {
                "start": round(float(item["start"]), 3),
                "duration": round(float(item.get("duration", 0.0)), 3),
                "text": text,
            }
        )

    if not cleaned:
        raise TranscriptNotFoundError("Bu videoda tayyor subtitr yo'q")

    return cleaned


_SENTENCE_PUNCT_CLASS = r"[.!?…।॥。！？]"
_NON_SPEECH_RE = re.compile(
    r"^[\[\(♪♫\s]*([♪♫]+|music|musiqa|applause|laughter)[\]\)\s♪♫]*$",
    re.IGNORECASE,
)


def _ends_sentence(text: str) -> bool:
    """Return True if text concludes with sentence-ending punctuation."""
    return bool(re.search(rf'{_SENTENCE_PUNCT_CLASS}+["\'\)\]]*$', text.strip()))


def _split_snippets_on_sentences(snippets: list[dict]) -> list[dict]:
    """Strip pure non-speech tags and split snippets at internal sentence boundaries."""
    cleaned: list[dict] = []
    for idx, snippet in enumerate(snippets):
        text = " ".join(str(snippet.get("text", "")).split())
        if not text or _NON_SPEECH_RE.match(text):
            continue

        start = float(snippet["start"])
        dur = max(0.0, float(snippet.get("duration", 0.0)))
        next_start = float(snippets[idx + 1]["start"]) if idx + 1 < len(snippets) else start + dur
        span = min(dur, next_start - start) if next_start > start else dur
        if span <= 0.0:
            span = max(dur, 0.2)

        parts = [p.strip() for p in re.split(rf"(?<={_SENTENCE_PUNCT_CLASS})\s+", text) if p.strip()]
        if len(parts) <= 1:
            cleaned.append({"start": round(start, 3), "duration": round(dur, 3), "text": text})
            continue

        total_chars = max(1, sum(len(p) for p in parts))
        offset_chars = 0
        for p in parts:
            frac_start = start + span * (offset_chars / total_chars)
            frac_dur = max(0.1, span * (len(p) / total_chars))
            cleaned.append(
                {
                    "start": round(frac_start, 3),
                    "duration": round(frac_dur, 3),
                    "text": p,
                }
            )
            offset_chars += len(p)
    return cleaned


def extract_last_sentences(snippets: list[dict], count: int = 2) -> str:
    """Return the last N sentences (or trailing snippets if unpunctuated) for context."""
    joined = " ".join(s["text"] for s in snippets if s.get("text")).strip()
    if not joined:
        return ""

    sentences = [s.strip() for s in re.split(rf"(?<={_SENTENCE_PUNCT_CLASS})\s+", joined) if s.strip()]
    if len(sentences) >= 2:
        return " ".join(sentences[-count:])

    return " ".join(s["text"] for s in snippets[-3:] if s.get("text")).strip()


def build_chunks(
    snippets: list[dict], target_sec: float = 60.0, max_sec: float = 75.0
) -> list[dict]:
    """Split transcript snippets into ~60s sentence-safe chunks with prior context."""
    snippets = _split_snippets_on_sentences(snippets)
    if not snippets:
        return []

    groups: list[list[dict]] = []
    current: list[dict] = []

    for idx, snippet in enumerate(snippets):
        current.append(snippet)
        has_next = idx + 1 < len(snippets)
        if not has_next:
            groups.append(current)
            current = []
            continue

        chunk_start = current[0]["start"]
        snippet_end = snippet["start"] + max(snippet["duration"], 0.0)
        elapsed = snippet_end - chunk_start
        next_gap = snippets[idx + 1]["start"] - snippet_end

        should_cut = (
            (elapsed >= target_sec - 5.0 and _ends_sentence(snippet["text"]))
            or (elapsed >= target_sec and next_gap >= 0.7)
            or elapsed >= max_sec
        )
        if should_cut:
            groups.append(current)
            current = []

    chunks: list[dict] = []
    for idx, group in enumerate(groups):
        start_sec = round(group[0]["start"], 2)
        last = group[-1]
        end_sec = round(last["start"] + max(last["duration"], 0.1), 2)
        prev_context = "" if idx == 0 else extract_last_sentences(groups[idx - 1], count=2)
        chunks.append(
            {
                "chunk_index": idx,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "raw_json": json.dumps(group, ensure_ascii=False),
                "prev_context": prev_context,
            }
        )

    return chunks


def group_into_sentences(
    snippets: list[dict], max_group_sec: float = 18.0
) -> list[dict]:
    """Combine short subtitle fragments into complete spoken sentences without mid-sentence cuts."""
    snippets = _split_snippets_on_sentences(snippets)
    if not snippets:
        return []

    grouped: list[dict] = []
    current: list[dict] = []

    for idx, snippet in enumerate(snippets):
        current.append(snippet)
        has_next = idx + 1 < len(snippets)
        group_start = current[0]["start"]
        snippet_end = snippet["start"] + max(snippet["duration"], 0.0)
        group_dur = snippet_end - group_start
        next_gap = (snippets[idx + 1]["start"] - snippet_end) if has_next else 0.0
        ends_here = _ends_sentence(snippet["text"])

        if (
            not has_next
            or (ends_here and (group_dur >= 2.0 or next_gap >= 0.25))
            or next_gap >= 0.45
            or group_dur >= max_group_sec
        ):
            combined_text = " ".join(s["text"] for s in current if s.get("text")).strip()
            if combined_text:
                grouped.append(
                    {
                        "start": group_start,
                        "end": round(snippet_end, 3),
                        "text": combined_text,
                    }
                )
            current = []

    return grouped


def translate_chunk_segments(
    segments: list[dict], video_title: str, prev_context: str
) -> list[dict]:
    """Translate grouped subtitle segments into concise, natural Uzbek using Gemini."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise PipelineConfigError("GEMINI_API_KEY sozlanmagan")

    if not segments:
        return []

    payload_json = json.dumps(segments, ensure_ascii=False)
    prompt = (
        "Sen professional YouTube video dublyaj tarjimonisan.\n"
        "Quyidagi video subtitridagi gap segmentlarini (qaysi tilda bo'lishidan qat'i nazar) "
        "o'zbek tiliga tarjima qil.\n\n"
        "Qat'iy qoidalar:\n"
        "1. video_title va prev_context faqat mazmunni tushunish uchun kontekstdir; "
        "ularni tarjima natijasiga qo'shma.\n"
        "2. Har bir segmentning 'text' maydonini qisqa, tabiiy va og'zaki dublyajga "
        "qulay o'zbek tiliga tarjima qil.\n"
        "3. Ilmiy, texnologik va IT atamalarini o'zbekchaga so'zma-so'z tarjima qilma — "
        "xalqaro texnik holatini saqla, lekin o'zbekcha ovoz (TTS) to'g'ri talaffuz qilishi "
        "uchun inglizcha qisqartma va atamalarni o'zbekcha talaffuzda yoz "
        "(masalan: IT -> ayti, AI -> ey-ay, API -> ey-pi-ay, IP -> ay-pi, URL -> yu-ar-el, "
        "VPN -> vi-pi-en, SQL -> es-kyu-el, HTML -> eych-ti-em-el, CSS -> si-es-es, "
        "JSON -> jeyson, UI -> yu-ay, UX -> yu-eks, CPU -> si-pi-yu, GPU -> ji-pi-yu, "
        "Python -> Payton, JavaScript -> JavaSkript, Framework -> freymvork, "
        "Backend -> bekend, Frontend -> frontend, YouTube -> Yutub, Facebook -> Feysbuk, "
        "Google -> Gugl).\n"
        "4. Segmentlar sonini, tartibini va 'start' vaqtlarini aynan o'zgartirmasdan qaytar.\n\n"
        f"video_title (kontekst): {video_title or 'Noma lum'}\n"
        f"prev_context (oldingi bo'lak oxiri): {prev_context or 'Yo q'}\n"
        f"segments: {payload_json}"
    )

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=25000),
    )
    primary_model = os.getenv("GEMINI_MODEL", "").strip() or "gemini-3.6-flash"
    candidate_models = list(
        dict.fromkeys([primary_model, "gemini-3.5-flash-lite", "gemini-3.5-flash"])
    )
    response = None
    last_exc: Exception | None = None
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=TranslationPayload,
                        temperature=0.3,
                    ),
                )
                break
            except Exception as exc:
                last_exc = exc
                msg = str(exc).upper()
                transient = any(
                    code in msg
                    for code in ("503", "504", "429", "UNAVAILABLE", "DEADLINE_EXCEEDED", "TIMEOUT")
                )
                if not transient:
                    raise
                if attempt == 0:
                    time.sleep(1)
        if response is not None:
            break

    if response is None and last_exc is not None:
        raise last_exc

    try:
        meta = getattr(response, "usage_metadata", None)
        total_tokens = int(getattr(meta, "total_token_count", 0) or 0)
        record_gemini_usage(total_tokens)
    except Exception:
        pass

    data = json.loads(response.text)
    raw_segments = data.get("segments", [])

    result: list[dict] = []
    if len(raw_segments) == len(segments):
        for orig, trans in zip(segments, raw_segments):
            text = " ".join(str(trans.get("text", "")).split())
            if text:
                item = {"start": float(orig["start"]), "text": text}
                if "end" in orig:
                    item["end"] = float(orig["end"])
                result.append(item)
    else:
        for trans in raw_segments:
            text = " ".join(str(trans.get("text", "")).split())
            if text:
                result.append({"start": float(trans["start"]), "text": text})

    result.sort(key=lambda item: item["start"])
    return result


def _trim_silence(audio: AudioSegment) -> AudioSegment:
    """Trim leading/trailing silence while keeping soft 20ms edges."""
    if len(audio) <= 120:
        return audio
    ranges = detect_nonsilent(audio, min_silence_len=80, silence_thresh=-45)
    if not ranges:
        return audio
    start_ms = max(0, ranges[0][0] - 20)
    end_ms = min(len(audio), ranges[-1][1] + 20)
    return audio[start_ms:end_ms] if end_ms > start_ms else audio


def compute_atempo_factor(
    audio_duration_sec: float, allowed_sec: float | None, max_speed: float = 1.38
) -> float:
    """Compute bounded ffmpeg atempo speedup factor when TTS exceeds the time slot."""
    if allowed_sec is None or allowed_sec <= 0.05 or audio_duration_sec <= allowed_sec:
        return 1.0

    ratio = audio_duration_sec / allowed_sec
    factor = min(max_speed, ratio)
    return round(factor, 4) if factor > 1.01 else 1.0


def _apply_atempo(input_mp3: Path, output_mp3: Path, factor: float) -> Path:
    """Speed up an MP3 segment using ffmpeg's atempo audio filter."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_mp3),
            "-filter:a",
            f"atempo={factor:.4f}",
            "-vn",
            str(output_mp3),
        ],
        check=True,
        capture_output=True,
    )
    return output_mp3


async def build_chunk_audio(
    translated_segments: list[dict],
    chunk_start: float,
    chunk_end: float,
    voice: str,
    output_mp3: Path,
) -> Path:
    """Synthesize translated segments, auto-pace overlaps, and mix into one 64k MP3."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg o'rnatilmagan. Terminalda 'sudo apt update && sudo apt install ffmpeg -y' buyrug'ini bajaring."
        )

    valid_segments = [s for s in translated_segments if str(s.get("text", "")).strip()]
    base_duration_ms = max(500, int(round((chunk_end - chunk_start) * 1000)))
    if not valid_segments:
        await asyncio.to_thread(
            AudioSegment.silent(duration=base_duration_ms).export,
            str(output_mp3),
            format="mp3",
            bitrate="64k",
        )
        return output_mp3

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        semaphore = asyncio.Semaphore(4)

        async def _synth_one(idx: int, text: str) -> Path:
            seg_path = tmp_dir / f"seg_{idx}.mp3"
            async with semaphore:
                await synthesize_text(text, voice, seg_path)
            return seg_path

        raw_paths = await asyncio.gather(
            *(_synth_one(idx, seg["text"]) for idx, seg in enumerate(valid_segments))
        )

        placed: list[tuple[int, AudioSegment]] = []
        max_end_ms = base_duration_ms
        cursor_ms = 0

        for idx, (seg, seg_path) in enumerate(zip(valid_segments, raw_paths)):
            raw_audio = await asyncio.to_thread(AudioSegment.from_file, seg_path)
            audio = await asyncio.to_thread(_trim_silence, raw_audio)
            seg_start = float(seg["start"])
            target_offset_ms = max(0, int(round((seg_start - chunk_start) * 1000)))
            # Oldingi ovoz tugamasdan keyingisini qo'ymaslik (ovozlar ustma-ust tushmasin)
            offset_ms = max(target_offset_ms, cursor_ms)
            effective_start_sec = chunk_start + (offset_ms / 1000.0)

            next_start = (
                float(valid_segments[idx + 1]["start"])
                if idx + 1 < len(valid_segments)
                else (chunk_end if chunk_end > effective_start_sec else None)
            )
            seg_end = float(seg["end"]) if "end" in seg else None
            # Agar videoda nutqdan keyin kamida 0.6s pauza bo'lsa, tarjimani ham o'sha pauzagacha tugatish
            if (
                seg_end is not None
                and next_start is not None
                and (next_start - seg_end) >= 0.6
                and seg_end > effective_start_sec
            ):
                target_end = seg_end
            else:
                target_end = next_start
            allowed_sec = (
                max(0.4, target_end - effective_start_sec)
                if target_end is not None
                else None
            )
            factor = compute_atempo_factor(len(audio) / 1000.0, allowed_sec)

            if factor > 1.0:
                paced_path = tmp_dir / f"seg_{idx}_paced.mp3"
                await asyncio.to_thread(_apply_atempo, seg_path, paced_path, factor)
                paced_audio = await asyncio.to_thread(AudioSegment.from_file, paced_path)
                audio = await asyncio.to_thread(_trim_silence, paced_audio)

            placed.append((offset_ms, audio))
            cursor_ms = offset_ms + len(audio) + 40
            max_end_ms = max(max_end_ms, offset_ms + len(audio))

        def _mix_and_export() -> None:
            canvas = AudioSegment.silent(duration=max_end_ms)
            for offset_ms, audio in placed:
                canvas = canvas.overlay(audio, position=offset_ms)
            canvas.export(str(output_mp3), format="mp3", bitrate="64k")

        await asyncio.to_thread(_mix_and_export)
        return output_mp3
