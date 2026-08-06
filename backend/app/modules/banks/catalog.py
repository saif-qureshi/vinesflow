"""Banks operating in Pakistan, offered as a starting point when adding an account.

`logo` points at a file served from the frontend's public/bank-logos folder.
Drop the artwork in once and every organisation picks it up; an organisation
can still upload its own to override it. Until a file exists the badge falls
back to the bank's initials on `colour`.

Colours are approximations of each bank's brand colour and are editable per
account — this is a convenience list, not a registry.
"""

from __future__ import annotations

PAKISTANI_BANKS: list[dict[str, str]] = [
    {"code": "HBL", "name": "Habib Bank Limited", "colour": "#00A94F", "logo": "/bank-logos/hbl.svg"},
    {"code": "UBL", "name": "United Bank Limited", "colour": "#0C4DA2", "logo": "/bank-logos/ubl.svg"},
    {"code": "MCB", "name": "MCB Bank", "colour": "#00693E", "logo": "/bank-logos/mcb.svg"},
    {"code": "NBP", "name": "National Bank of Pakistan", "colour": "#006838", "logo": "/bank-logos/nbp.svg"},
    {"code": "ABL", "name": "Allied Bank", "colour": "#7C2529", "logo": "/bank-logos/abl.svg"},
    {"code": "MEZN", "name": "Meezan Bank", "colour": "#00694E", "logo": "/bank-logos/mezn.svg"},
    {"code": "ALFH", "name": "Bank Alfalah", "colour": "#C8102E", "logo": "/bank-logos/alfh.svg"},
    {"code": "FYSL", "name": "Faysal Bank", "colour": "#006B54", "logo": "/bank-logos/fysl.svg"},
    {"code": "ASKR", "name": "Askari Bank", "colour": "#005CAB", "logo": "/bank-logos/askr.svg"},
    {"code": "BOP", "name": "The Bank of Punjab", "colour": "#00539F", "logo": "/bank-logos/bop.svg"},
    {"code": "BIPL", "name": "BankIslami Pakistan", "colour": "#00843D", "logo": "/bank-logos/bipl.svg"},
    {"code": "DIBP", "name": "Dubai Islamic Bank Pakistan", "colour": "#0E7C61", "logo": "/bank-logos/dibp.svg"},
    {"code": "HMB", "name": "Habib Metropolitan Bank", "colour": "#003A70", "logo": "/bank-logos/hmb.svg"},
    {"code": "JS", "name": "JS Bank", "colour": "#005596", "logo": "/bank-logos/js.svg"},
    {"code": "SNBL", "name": "Soneri Bank", "colour": "#A6192E", "logo": "/bank-logos/snbl.svg"},
    {"code": "SCB", "name": "Standard Chartered Pakistan", "colour": "#0473EA", "logo": "/bank-logos/scb.svg"},
    {"code": "SILK", "name": "Silkbank", "colour": "#00A0DF", "logo": "/bank-logos/silk.svg"},
    {"code": "SMBL", "name": "Summit Bank", "colour": "#005EA8", "logo": "/bank-logos/smbl.svg"},
    {"code": "SINDH", "name": "Sindh Bank", "colour": "#007A33", "logo": "/bank-logos/sindh.svg"},
    {"code": "BOK", "name": "The Bank of Khyber", "colour": "#00693E", "logo": "/bank-logos/bok.svg"},
    {"code": "ALBRK", "name": "Al Baraka Bank Pakistan", "colour": "#006A4D", "logo": "/bank-logos/albrk.svg"},
    {"code": "FWBL", "name": "First Women Bank", "colour": "#8E1B6B", "logo": "/bank-logos/fwbl.svg"},
    {"code": "ZTBL", "name": "Zarai Taraqiati Bank", "colour": "#0F7B3F", "logo": "/bank-logos/ztbl.svg"},
    {"code": "SAMBA", "name": "Samba Bank", "colour": "#003C71", "logo": "/bank-logos/samba.svg"},
    {"code": "MIB", "name": "MCB Islamic Bank", "colour": "#00693E", "logo": "/bank-logos/mib.svg"},
    {"code": "UMBL", "name": "U Microfinance Bank", "colour": "#7B2C8F", "logo": "/bank-logos/umbl.svg"},
    {"code": "EASY", "name": "Easypaisa", "colour": "#3AAA35", "logo": "/bank-logos/easy.svg"},
    {"code": "JAZZ", "name": "JazzCash", "colour": "#B01C2E", "logo": "/bank-logos/jazz.svg"},
]
