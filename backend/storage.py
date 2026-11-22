import os
from pathlib import Path
import re
import shutil

import boto3

_BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", "").strip() or _BASE_DIR)
AUDIO_CACHE_DIR = DATA_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def is_r2_configured() -> bool:
    """Return True when Cloudflare R2 account and bucket env vars are set."""
    return bool(os.getenv("R2_ACCOUNT_ID", "").strip()) and bool(
        os.getenv("R2_BUCKET_NAME", "").strip()
    )


def build_audio_filename(video_id: str, voice: str, chunk_index: int) -> str:
    """Build a path-safe MP3 filename for a translated chunk."""
    safe_video_id = re.sub(r"[^A-Za-z0-9_-]", "_", video_id)
    safe_voice = re.sub(r"[^A-Za-z0-9_-]", "_", voice)
    return f"{safe_video_id}_{safe_voice}_chunk_{chunk_index}.mp3"


def save_audio(
    local_mp3_path: Path,
    video_id: str,
    voice: str,
    chunk_index: int,
    base_url: str = "",
) -> str:
    """Store an MP3 chunk in Cloudflare R2 if configured, or local audio_cache."""
    filename = build_audio_filename(video_id, voice, chunk_index)

    if is_r2_configured():
        account_id = os.getenv("R2_ACCOUNT_ID", "").strip()
        bucket_name = os.getenv("R2_BUCKET_NAME", "").strip()
        access_key_id = os.getenv("R2_ACCESS_KEY_ID", "").strip()
        secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
        public_url = os.getenv("R2_PUBLIC_URL", "").strip()

        client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )
        object_key = f"audio/{filename}"
        client.upload_file(
            str(local_mp3_path),
            bucket_name,
            object_key,
            ExtraArgs={"ContentType": "audio/mpeg"},
        )
        local_mp3_path.unlink(missing_ok=True)

        if public_url:
            return f"{public_url.rstrip('/')}/{object_key}"
        return f"https://{account_id}.r2.cloudflarestorage.com/{bucket_name}/{object_key}"

    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = AUDIO_CACHE_DIR / filename
    if local_mp3_path.resolve() != dest_path.resolve():
        shutil.move(str(local_mp3_path), str(dest_path))

    public_base = (
        os.getenv("PUBLIC_BASE_URL", "").strip()
        or base_url.strip()
        or "http://127.0.0.1:8000"
    ).rstrip("/")
    return f"{public_base}/audio/{filename}"
