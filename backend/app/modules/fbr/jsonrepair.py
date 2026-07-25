from __future__ import annotations

import json
import re
from typing import Any

_BOM = "﻿"
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def _clean(text: str) -> str:
    if text.startswith(_BOM):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text)
    text = _TRAILING_COMMA.sub(r"\1", text)
    return text.strip()


def loads(text: str | None) -> Any:
    """Decode JSON, tolerating the trailing commas and stray control characters
    FBR occasionally returns. Well-formed responses are parsed untouched; only a
    failed strict parse triggers the cleanup pass, so valid data is never mangled.
    """
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return json.loads(_clean(text))
