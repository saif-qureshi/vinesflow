from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def _client_ip(request: Request) -> str:
    """The client address, counting back past proxies we actually run.

    Each proxy appends the peer it saw, so only the last TRUSTED_PROXY_COUNT
    entries are ours to trust — everything to their left is caller-supplied and
    would otherwise let one attacker occupy unlimited rate-limit buckets.
    """
    trusted = settings.TRUSTED_PROXY_COUNT
    if trusted > 0:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
            if hops:
                return hops[-min(trusted, len(hops))]
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip)
