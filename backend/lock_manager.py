import asyncio
import weakref

# Kalit -> Lock. WeakValueDictionary: lock hech kim ishlatmasa o'zi xotiradan o'chadi.
_locks: "weakref.WeakValueDictionary[str, asyncio.Lock]" = weakref.WeakValueDictionary()


def get_lock(*parts: object) -> asyncio.Lock:
    """Berilgan kalit qismlari (video_id, voice, chunk_index...) uchun yagona asyncio.Lock qaytaradi."""
    key = ":".join(str(p) for p in parts)
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock
