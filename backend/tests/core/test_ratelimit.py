import pytest

from app.core import ratelimit
from app.core.ratelimit import _client_ip


class _Request:
    def __init__(self, forwarded: str | None, peer: str = "10.0.0.9"):
        self.headers = {"x-forwarded-for": forwarded} if forwarded else {}
        self.client = type("C", (), {"host": peer})()


@pytest.fixture()
def proxies(monkeypatch):
    def _set(count: int):
        monkeypatch.setattr(ratelimit.settings, "TRUSTED_PROXY_COUNT", count)

    return _set


def test_without_trusted_proxies_the_header_is_ignored(proxies):
    proxies(0)
    assert _client_ip(_Request("1.2.3.4")) == "10.0.0.9"


def test_a_spoofed_leading_hop_cannot_shift_the_bucket(proxies):
    proxies(1)
    assert _client_ip(_Request("9.9.9.9, 203.0.113.5")) == "203.0.113.5"
    assert _client_ip(_Request("1.1.1.1, 203.0.113.5")) == "203.0.113.5"


def test_two_proxies_count_back_two_hops(proxies):
    proxies(2)
    assert _client_ip(_Request("9.9.9.9, 203.0.113.5, 172.16.0.1")) == "203.0.113.5"


def test_short_chains_do_not_overrun(proxies):
    proxies(2)
    assert _client_ip(_Request("203.0.113.5")) == "203.0.113.5"
    assert _client_ip(_Request(None)) == "10.0.0.9"
