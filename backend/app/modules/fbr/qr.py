from __future__ import annotations

import segno


def qr_data_uri(content: str) -> str:
    return segno.make(content, error="m").png_data_uri(scale=10, border=2)
