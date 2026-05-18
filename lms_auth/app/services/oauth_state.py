import hashlib
import secrets
import time

from ..config import get_settings

_state_store: dict[str, float] = {}
_STATE_TTL_SECONDS = 600


def create_state(provider: str) -> str:
    settings = get_settings()
    raw = f"{provider}:{secrets.token_urlsafe(16)}:{settings.jwt_secret_key}"
    state = hashlib.sha256(raw.encode()).hexdigest()[:32]
    _state_store[state] = time.time()
    return state


def validate_state(state: str | None) -> bool:
    if not state or state not in _state_store:
        return False
    created = _state_store.pop(state)
    return (time.time() - created) <= _STATE_TTL_SECONDS
