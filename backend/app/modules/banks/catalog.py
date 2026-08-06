"""Banks operating in Pakistan, offered as a starting point when adding an account.

`logo` is the filename of the artwork in this module's `logos/` folder, which
`vineflow banks sync-logos` uploads into object storage under the shared
`catalog/banks/` prefix. The API hands clients the resulting URL, so the same
image works from any origin and the PDF renderer can read the bytes directly.

`colour` is only a fallback for the initials badge when a bank has no artwork.
This is a convenience list, not a registry.
"""

from __future__ import annotations

LOGO_DIR = "logos"
LOGO_PREFIX = "banks"

PAKISTANI_BANKS: list[dict[str, str]] = [
    {"code": "HBL", "name": "Habib Bank Limited", "colour": "#00A94F", "logo": "hbl.png"},
    {"code": "UBL", "name": "United Bank Limited", "colour": "#0C4DA2", "logo": "ubl.png"},
    {"code": "MCB", "name": "MCB Bank", "colour": "#00693E", "logo": "mcb.png"},
    {"code": "NBP", "name": "National Bank of Pakistan", "colour": "#006838", "logo": "nbp.png"},
    {"code": "ABL", "name": "Allied Bank", "colour": "#7C2529", "logo": "abl.png"},
    {"code": "MEZN", "name": "Meezan Bank", "colour": "#00694E", "logo": "mezn.png"},
    {"code": "ALFH", "name": "Bank Alfalah", "colour": "#C8102E", "logo": "alfh.png"},
    {"code": "FYSL", "name": "Faysal Bank", "colour": "#006B54", "logo": "fysl.png"},
    {"code": "ASKR", "name": "Askari Bank", "colour": "#005CAB", "logo": "askr.png"},
    {"code": "BOP", "name": "The Bank of Punjab", "colour": "#00539F", "logo": "bop.png"},
    {"code": "BIPL", "name": "BankIslami Pakistan", "colour": "#00843D", "logo": "bipl.png"},
    {"code": "DIBP", "name": "Dubai Islamic Bank Pakistan", "colour": "#0E7C61", "logo": "dibp.png"},
    {"code": "HMB", "name": "Habib Metropolitan Bank", "colour": "#003A70", "logo": "hmb.png"},
    {"code": "JS", "name": "JS Bank", "colour": "#005596", "logo": "js.png"},
    {"code": "SNBL", "name": "Soneri Bank", "colour": "#A6192E", "logo": "snbl.png"},
    {"code": "SCB", "name": "Standard Chartered Pakistan", "colour": "#0473EA", "logo": "scb.png"},
    {"code": "SILK", "name": "Silkbank", "colour": "#00A0DF", "logo": "silk.png"},
    {"code": "SMBL", "name": "Summit Bank", "colour": "#005EA8", "logo": "smbl.png"},
    {"code": "SINDH", "name": "Sindh Bank", "colour": "#007A33", "logo": "sindh.png"},
    {"code": "BOK", "name": "The Bank of Khyber", "colour": "#00693E", "logo": "bok.png"},
    {"code": "ALBRK", "name": "Al Baraka Bank Pakistan", "colour": "#006A4D", "logo": "albrk.png"},
    {"code": "SAMBA", "name": "Samba Bank", "colour": "#003C71", "logo": "samba.png"},
    {"code": "MIB", "name": "MCB Islamic Bank", "colour": "#00693E", "logo": "mib.png"},
    {"code": "UMBL", "name": "U Microfinance Bank", "colour": "#7B2C8F", "logo": "umbl.png"},
    {"code": "EASY", "name": "Easypaisa", "colour": "#00C46A", "logo": "easy.png"},
    {"code": "JAZZ", "name": "JazzCash", "colour": "#C8102E", "logo": "jazz.png"},
    {"code": "SADA", "name": "SadaPay", "colour": "#FF6B57", "logo": "sada.png"},
    {"code": "NAYA", "name": "NayaPay", "colour": "#F26522", "logo": "naya.png"},
    {"code": "ZNDG", "name": "Zindigi", "colour": "#4FC3B5", "logo": "zndg.png"},
    {"code": "UPAISA", "name": "UPaisa", "colour": "#F58220", "logo": "upaisa.png"},
]


def logo_key(filename: str) -> str:
    """Storage key the artwork is served from."""
    from app.core.storage import catalog_key

    return catalog_key(LOGO_PREFIX, filename)


def sync_logos() -> tuple[int, int]:
    """Upload the bundled artwork into storage. Idempotent — safe on every deploy."""
    import mimetypes
    import pathlib

    from app.core.storage import get_storage

    storage = get_storage()
    source = pathlib.Path(__file__).parent / LOGO_DIR
    uploaded = skipped = 0
    for bank in PAKISTANI_BANKS:
        path = source / bank["logo"]
        if not path.is_file():
            skipped += 1
            continue
        storage.put_bytes(
            logo_key(bank["logo"]),
            path.read_bytes(),
            content_type=mimetypes.guess_type(path.name)[0] or "image/png",
        )
        uploaded += 1
    return uploaded, skipped
