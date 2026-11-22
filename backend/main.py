import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel, Field

from database import (
    change_access_key,
    create_user_record,
    delete_user_record,
    get_cached_audio,
    get_gemini_usage_summary,
    get_settings_dict,
    get_user_by_key,
    get_video_chunk,
    get_video_chunks,
    init_db,
    list_all_users,
    load_settings_to_env,
    reserve_vip_usage,
    save_cached_audio,
    save_settings_dict,
    save_video_chunks,
    update_user_record,
)
from lock_manager import get_lock
from pipeline import (
    PipelineConfigError,
    TranscriptNotFoundError,
    build_chunk_audio,
    build_chunks,
    fetch_transcript,
    group_into_sentences,
    normalize_video_id,
    translate_chunk_segments,
)
from storage import AUDIO_CACHE_DIR, is_r2_configured, save_audio
from tts_service import TTSConfigError, VALID_VOICES, validate_voice
from ui import render_dashboard_html, render_swagger_html

load_dotenv(Path(__file__).resolve().parent / ".env")

AUTH_ERROR_DETAIL = "Parol noto'g'ri yoki muddati tugagan"


class CheckKeyResponse(BaseModel):
    """Response model for access key verification."""

    ok: bool = Field(examples=[True])
    user: str = Field(examples=["Admin"])
    elevenlabs_enabled: bool = Field(examples=[False])


class ErrorResponse(BaseModel):
    """Standard error payload returned for rejected requests."""

    detail: str = Field(examples=[AUTH_ERROR_DETAIL])


class TranscriptSnippet(BaseModel):
    """Single caption line sent directly from the user's browser."""

    start: float = Field(ge=0.0)
    duration: float = Field(default=0.0, ge=0.0)
    text: str


class InitRequest(BaseModel):
    """Request body for initializing and chunking a YouTube video's captions."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "video_id": "dQw4w9WgXcQ",
                "video_title": "Sample English Video",
            }
        }
    }

    video_id: str = Field(examples=["dQw4w9WgXcQ"])
    video_title: str = Field(default="", examples=["Sample English Video"])
    transcript: list[TranscriptSnippet] | None = Field(
        default=None,
        description="Ixtiyoriy: brauzerdan olingan subtitrlar (yuborilsa server YouTube'ga so'rov yubormaydi)",
    )


class ChunkMeta(BaseModel):
    """Time boundaries for a single logical ~60s transcript chunk."""

    index: int
    start: float
    end: float


class InitResponse(BaseModel):
    """Chunk map returned by POST /init."""

    chunks: list[ChunkMeta]


class ChunkRequest(BaseModel):
    """Request body for translating and synthesizing one video chunk."""

    video_id: str = Field(examples=["dQw4w9WgXcQ"])
    chunk_index: int = Field(ge=0, examples=[0])
    voice: str = Field(default="sardor", examples=["sardor"])
    video_title: str = Field(default="", examples=["Sample English Video"])


class ChunkResponse(BaseModel):
    """Response containing the playable MP3 URL and cache hit indicator."""

    audio_url: str = Field(
        examples=["http://127.0.0.1:8000/audio/VIDEO_ID_sardor_chunk_0.mp3"]
    )
    cached: bool = Field(examples=[False])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize SQLite schema, default user seed, DB settings, and audio cache folder."""
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    load_settings_to_env()
    yield


app = FastAPI(
    title="YouTube O'zbekcha Tarjimon API",
    version="2.0.0",
    description=(
        "YouTube videolarini o'zbek tiliga bo'laklab tarjima qilish va "
        "ovozlashtirish uchun ichki FastAPI backend xizmati (Private MVP v2)."
    ),
    docs_url=None,
    openapi_tags=[
        {
            "name": "Autentifikatsiya",
            "description": "Foydalanuvchi paroli (X-Access-Key) va amal qilish muddatini tekshirish.",
        },
        {
            "name": "Tarjima va Audio",
            "description": "Subtitr bo'laklash (/init), Gemini tarjima + TTS dublyaj (/chunk) va kesh.",
        },
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(AUDIO_CACHE_DIR)), name="audio")


def _is_expired(expires_at: str | None) -> bool:
    """Return True if expires_at is invalid or in the past (UTC)."""
    if not expires_at:
        return False

    try:
        expires_dt = datetime.fromisoformat(str(expires_at).strip())
    except ValueError:
        return True

    if expires_dt.tzinfo is None:
        expires_dt = expires_dt.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) > expires_dt


def _is_elevenlabs_enabled() -> bool:
    """Return True when a non-empty ELEVENLABS_API_KEY is configured."""
    return bool(os.getenv("ELEVENLABS_API_KEY", "").strip())


def _is_gemini_enabled() -> bool:
    """Return True when a non-empty GEMINI_API_KEY is configured."""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def verify_access_key(
    x_access_key: str | None = Header(
        default=None,
        alias="X-Access-Key",
        description="Foydalanuvchi kirish kaliti (masalan: ADMIN-1234)",
    ),
) -> dict:
    """Validate X-Access-Key against active, non-expired records in users."""
    key = (x_access_key or "").strip()
    if not key:
        raise HTTPException(status_code=401, detail=AUTH_ERROR_DETAIL)

    row = get_user_by_key(key)
    if row is None or row["is_active"] == 0 or _is_expired(row["expires_at"]):
        raise HTTPException(status_code=401, detail=AUTH_ERROR_DETAIL)

    return {
        "access_key": row["access_key"],
        "name": row["name"],
        "allow_vip": bool(row["allow_vip"]),
        "vip_daily_limit": int(row["vip_daily_limit"] or 0),
        "is_admin": bool(row["is_admin"]),
    }


def verify_admin_key(user: dict = Depends(verify_access_key)) -> dict:
    """Require an admin access key for cabinet endpoints."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Faqat admin uchun ruxsat")
    return user


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> str:
    """Serve the backend status and live key-testing developer console."""
    return render_dashboard_html(
        elevenlabs_enabled=_is_elevenlabs_enabled(),
        gemini_enabled=_is_gemini_enabled(),
        r2_enabled=is_r2_configured(),
    )


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def custom_docs() -> str:
    """Serve customized dark-slate Swagger UI documentation."""
    return render_swagger_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title="YouTube O'zbekcha Tarjimon — API Hujjatlari",
    )


@app.get(
    "/check-key",
    response_model=CheckKeyResponse,
    tags=["Autentifikatsiya"],
    summary="Access Key ni tekshirish",
    description="X-Access-Key sarlavhasidagi parolni SQLite bazasida tekshiradi (faolligi va muddati bo'yicha).",
    responses={401: {"model": ErrorResponse, "description": AUTH_ERROR_DETAIL}},
)
def check_key(user: dict = Depends(verify_access_key)) -> CheckKeyResponse:
    """Verify the provided access key and return user info plus ElevenLabs status."""
    return CheckKeyResponse(
        ok=True,
        user=user["name"],
        elevenlabs_enabled=_is_elevenlabs_enabled() and user["allow_vip"],
    )


class ChangeKeyRequest(BaseModel):
    """Request body for changing the authenticated user's own access key."""

    new_key: str = Field(min_length=6, max_length=64)


@app.post(
    "/change-key",
    tags=["Autentifikatsiya"],
    summary="O'z parolini o'zgartirish",
    description="Admin va oddiy foydalanuvchilar o'z kirish parolini yangisiga almashtiradi.",
)
def change_own_key(
    payload: ChangeKeyRequest,
    user: dict = Depends(verify_access_key),
) -> dict:
    """Allow any authenticated user (admin or subscriber) to change their access key."""
    try:
        updated_key = change_access_key(user["access_key"], payload.new_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "access_key": updated_key}


@app.post(
    "/init",
    response_model=InitResponse,
    tags=["Tarjima va Audio"],
    summary="Video subtitrini ~60s bo'laklarga ajratish",
    description="YouTube video subtitrini oladi, ~60 soniyalik mantiqiy bo'laklarga ajratadi va video_chunks ga saqlaydi.",
    responses={
        400: {"model": ErrorResponse, "description": "Bu videoda tayyor subtitr yo'q"},
        401: {"model": ErrorResponse, "description": AUTH_ERROR_DETAIL},
    },
)
async def init_video(
    payload: InitRequest,
    _user: dict = Depends(verify_access_key),
) -> InitResponse:
    """Fetch, chunk, and cache a video's transcript metadata."""
    video_id = normalize_video_id(payload.video_id)
    if not video_id:
        raise HTTPException(status_code=400, detail="video_id bo'sh bo'lishi mumkin emas")

    existing = await asyncio.to_thread(get_video_chunks, video_id)
    if existing:
        return InitResponse(
            chunks=[
                ChunkMeta(
                    index=row["chunk_index"],
                    start=row["start_sec"],
                    end=row["end_sec"],
                )
                for row in existing
            ]
        )

    async with get_lock("init", video_id):
        existing = await asyncio.to_thread(get_video_chunks, video_id)
        if existing:
            return InitResponse(
                chunks=[
                    ChunkMeta(
                        index=row["chunk_index"],
                        start=row["start_sec"],
                        end=row["end_sec"],
                    )
                    for row in existing
                ]
            )

        # Swagger /docs standart namunasini ("string") haqiqiy subtitr deb qabul qilmaslik
        is_swagger_placeholder = (
            payload.transcript is not None
            and len(payload.transcript) == 1
            and payload.transcript[0].start == 0
            and payload.transcript[0].duration == 0
            and payload.transcript[0].text.strip().lower() == "string"
        )
        if payload.transcript is not None and not is_swagger_placeholder:
            snippets = [
                {
                    "start": round(float(item.start), 3),
                    "duration": round(float(item.duration), 3),
                    "text": " ".join(item.text.split()),
                }
                for item in payload.transcript
                if " ".join(item.text.split())
            ]
            if not snippets:
                raise HTTPException(
                    status_code=400, detail="Bu videoda tayyor subtitr yo'q"
                )
        else:
            try:
                snippets = await asyncio.to_thread(fetch_transcript, video_id)
            except TranscriptNotFoundError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        chunks = build_chunks(snippets)
        await asyncio.to_thread(save_video_chunks, video_id, chunks)
    return InitResponse(
        chunks=[
            ChunkMeta(
                index=c["chunk_index"],
                start=c["start_sec"],
                end=c["end_sec"],
            )
            for c in chunks
        ]
    )


@app.post(
    "/chunk",
    response_model=ChunkResponse,
    tags=["Tarjima va Audio"],
    summary="Bo'lakni tarjima qilish va ovozlashtirish",
    description="Bo'lakni keshdan qaytaradi yoki Gemini tarjima + TTS + auto-pacing bilan MP3 tayyorlaydi.",
    responses={
        400: {"model": ErrorResponse, "description": "Noto'g'ri so'rov yoki API kaliti"},
        401: {"model": ErrorResponse, "description": AUTH_ERROR_DETAIL},
        404: {"model": ErrorResponse, "description": "Video bo'lagi topilmadi"},
    },
)
async def process_chunk(
    payload: ChunkRequest,
    request: Request,
    user: dict = Depends(verify_access_key),
) -> ChunkResponse:
    """Return cached chunk audio or translate, synthesize, pace, and store MP3."""
    video_id = normalize_video_id(payload.video_id)
    if not video_id:
        raise HTTPException(status_code=400, detail="video_id bo'sh bo'lishi mumkin emas")

    voice_key = payload.voice.strip().lower()
    if voice_key not in VALID_VOICES:
        raise HTTPException(
            status_code=400,
            detail="Noto'g'ri ovoz turi. Ruxsat etilgan: sardor, madina, elevenlabs",
        )

    cached_url = await asyncio.to_thread(
        get_cached_audio, video_id, payload.chunk_index, voice_key
    )
    if cached_url:
        return ChunkResponse(audio_url=cached_url, cached=True)

    # Bir xil (video, ovoz, bo'lak) uchun parallel so'rovlar navbatga turadi:
    # Gemini/TTS ikki marta chaqirilmaydi.
    async with get_lock(video_id, voice_key, payload.chunk_index):
        cached_url = await asyncio.to_thread(
            get_cached_audio, video_id, payload.chunk_index, voice_key
        )
        if cached_url:
            return ChunkResponse(audio_url=cached_url, cached=True)

        return await _generate_chunk(payload, video_id, voice_key, user, request)


async def _generate_chunk(
    payload: ChunkRequest,
    video_id: str,
    voice_key: str,
    user: dict,
    request: Request,
) -> ChunkResponse:
    """Translate + synthesize one chunk (called while holding the per-chunk lock)."""
    try:
        validate_voice(voice_key)
    except TTSConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if voice_key == "elevenlabs":
        if not user["allow_vip"]:
            raise HTTPException(
                status_code=403,
                detail="ElevenLabs (VIP) ovozi sizning parolingiz uchun yoqilmagan",
            )
        reserved = await asyncio.to_thread(
            reserve_vip_usage, user["access_key"], user["vip_daily_limit"]
        )
        if not reserved:
            raise HTTPException(
                status_code=429,
                detail="ElevenLabs (VIP) kunlik limiti tugadi. Ertaga urinib ko'ring",
            )

    chunk_row = await asyncio.to_thread(get_video_chunk, video_id, payload.chunk_index)
    if chunk_row is None:
        raise HTTPException(
            status_code=404,
            detail="Video bo'lagi topilmadi. Avval /init so'rovini yuboring",
        )

    raw_snippets = json.loads(chunk_row["raw_json"])
    sentence_segments = group_into_sentences(raw_snippets)

    try:
        translated_segments = await asyncio.to_thread(
            translate_chunk_segments,
            sentence_segments,
            payload.video_title,
            chunk_row["prev_context"] or "",
        )
    except PipelineConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini tarjima xatoligi: {exc}",
        ) from exc

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        temp_mp3 = Path(tmp_dir_str) / "chunk.mp3"
        try:
            await build_chunk_audio(
                translated_segments=translated_segments,
                chunk_start=float(chunk_row["start_sec"]),
                chunk_end=float(chunk_row["end_sec"]),
                voice=voice_key,
                output_mp3=temp_mp3,
            )
        except TTSConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        req_base_url = f"{proto}://{host}" if host else str(request.base_url).rstrip("/")

        audio_url = await asyncio.to_thread(
            save_audio,
            temp_mp3,
            video_id,
            voice_key,
            payload.chunk_index,
            req_base_url,
        )

    await asyncio.to_thread(
        save_cached_audio, video_id, payload.chunk_index, voice_key, audio_url
    )
    return ChunkResponse(audio_url=audio_url, cached=False)


class AdminSettingsUpdate(BaseModel):
    """Payload for updating API keys and model settings from the Admin Cabinet."""

    gemini_api_key: str | None = None
    gemini_model: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None


class AdminCreateUserRequest(BaseModel):
    """Payload for creating a new subscriber access key from the Admin Cabinet."""

    name: str = Field(min_length=1, max_length=80)
    access_key: str = Field(default="")
    days: int | None = Field(default=30, ge=1, le=3650)
    allow_vip: bool = False
    vip_daily_limit: int = Field(default=20, ge=0, le=100000)


class AdminUpdateUserRequest(BaseModel):
    """Payload for updating a subscriber's status or VIP limits."""

    is_active: bool | None = None
    allow_vip: bool | None = None
    vip_daily_limit: int | None = Field(default=None, ge=0, le=100000)
    days: int | None = Field(default=None, ge=0, le=3650)


def _mask_secret(value: str) -> str:
    """Return a masked preview of an API key without exposing the full secret."""
    v = value.strip()
    if not v:
        return ""
    if len(v) <= 8:
        return "*" * len(v)
    return f"{v[:4]}...{v[-4:]}"


@app.get("/admin/settings", tags=["Admin Kabinet"], summary="API kalitlari holatini olish")
def admin_get_settings(_admin: dict = Depends(verify_admin_key)) -> dict:
    """Return masked API key previews and non-secret config for the Admin Cabinet."""
    cfg = get_settings_dict()
    return {
        "gemini_configured": bool(cfg["GEMINI_API_KEY"]),
        "gemini_api_key_masked": _mask_secret(cfg["GEMINI_API_KEY"]),
        "gemini_model": cfg["GEMINI_MODEL"] or "gemini-3.6-flash",
        "elevenlabs_configured": bool(cfg["ELEVENLABS_API_KEY"]),
        "elevenlabs_api_key_masked": _mask_secret(cfg["ELEVENLABS_API_KEY"]),
        "elevenlabs_voice_id": cfg["ELEVENLABS_VOICE_ID"] or "JBFqnCBsd6RMkjVDRZzb",
    }


@app.post("/admin/settings", tags=["Admin Kabinet"], summary="API kalitlarini yangilash")
def admin_save_settings(
    payload: AdminSettingsUpdate,
    _admin: dict = Depends(verify_admin_key),
) -> dict:
    """Save updated API keys to SQLite and apply immediately without restart."""
    updates: dict[str, str] = {}
    if payload.gemini_api_key is not None:
        updates["GEMINI_API_KEY"] = payload.gemini_api_key
    if payload.gemini_model is not None:
        updates["GEMINI_MODEL"] = payload.gemini_model
    if payload.elevenlabs_api_key is not None:
        updates["ELEVENLABS_API_KEY"] = payload.elevenlabs_api_key
    if payload.elevenlabs_voice_id is not None:
        updates["ELEVENLABS_VOICE_ID"] = payload.elevenlabs_voice_id
    save_settings_dict(updates)
    return admin_get_settings(_admin)


@app.get("/admin/users", tags=["Admin Kabinet"], summary="Foydalanuvchilar ro'yxati")
def admin_list_users(_admin: dict = Depends(verify_admin_key)) -> dict:
    """List all users, their expiry, active status, and VIP permissions."""
    return {"users": list_all_users()}


@app.post("/admin/users", tags=["Admin Kabinet"], summary="Yangi obunachi qo'shish")
def admin_create_user(
    payload: AdminCreateUserRequest,
    _admin: dict = Depends(verify_admin_key),
) -> dict:
    """Create a new subscriber with optional custom key, expiry days, and VIP limits."""
    key = payload.access_key.strip().upper()
    if not key:
        key = f"UZ-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
    expires_at = (
        (datetime.now(timezone.utc) + timedelta(days=payload.days)).isoformat()
        if payload.days
        else None
    )
    try:
        user = create_user_record(
            access_key=key,
            name=payload.name.strip(),
            expires_at=expires_at,
            allow_vip=payload.allow_vip,
            vip_daily_limit=payload.vip_daily_limit,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Bu parol allaqachon mavjud") from exc
    return {"user": user}


@app.patch("/admin/users/{access_key}", tags=["Admin Kabinet"], summary="Obunachini tahrirlash")
def admin_update_user(
    access_key: str,
    payload: AdminUpdateUserRequest,
    _admin: dict = Depends(verify_admin_key),
) -> dict:
    """Update active status, VIP permission, daily limit, or expiry for a user."""
    expires_at: str | None = "__KEEP__"
    if payload.days is not None:
        expires_at = (
            (datetime.now(timezone.utc) + timedelta(days=payload.days)).isoformat()
            if payload.days > 0
            else None
        )
    updated = update_user_record(
        access_key=access_key,
        is_active=payload.is_active,
        allow_vip=payload.allow_vip,
        vip_daily_limit=payload.vip_daily_limit,
        expires_at=expires_at,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return {"user": updated}


@app.delete("/admin/users/{access_key}", tags=["Admin Kabinet"], summary="Obunachini o'chirish")
def admin_delete_user(
    access_key: str,
    _admin: dict = Depends(verify_admin_key),
) -> dict:
    """Delete a non-admin subscriber."""
    if not delete_user_record(access_key):
        raise HTTPException(
            status_code=400, detail="Foydalanuvchi topilmadi yoki adminni o'chirib bo'lmaydi"
        )
    return {"ok": True}


@app.get("/admin/usage", tags=["Admin Kabinet"], summary="API sarfi va ElevenLabs balansi")
async def admin_get_usage(_admin: dict = Depends(verify_admin_key)) -> dict:
    """Return Gemini request/token stats and live ElevenLabs character quota."""
    gemini = await asyncio.to_thread(get_gemini_usage_summary)
    el_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    elevenlabs: dict = {"configured": bool(el_key)}
    if el_key:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    "https://api.elevenlabs.io/v1/user/subscription",
                    headers={"xi-api-key": el_key},
                )
            if resp.status_code == 200:
                d = resp.json()
                used = int(d.get("character_count", 0))
                limit = int(d.get("character_limit", 0))
                elevenlabs.update(
                    {
                        "ok": True,
                        "tier": d.get("tier", ""),
                        "character_count": used,
                        "character_limit": limit,
                        "remaining": max(0, limit - used),
                    }
                )
            else:
                elevenlabs.update({"ok": False, "error": f"HTTP {resp.status_code}"})
        except Exception as exc:
            elevenlabs.update({"ok": False, "error": str(exc)})
    return {"gemini": gemini, "elevenlabs": elevenlabs}


