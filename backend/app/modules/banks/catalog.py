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
    {"code": "HBL", "name": "Habib Bank Limited", "colour": "#00A94F", "logo": "/bank-logos/hbl.png"},
    {"code": "UBL", "name": "United Bank Limited", "colour": "#0C4DA2", "logo": "/bank-logos/ubl.png"},
    {"code": "MCB", "name": "MCB Bank", "colour": "#00693E", "logo": "/bank-logos/mcb.png"},
    {"code": "NBP", "name": "National Bank of Pakistan", "colour": "#006838", "logo": "/bank-logos/nbp.png"},
    {"code": "ABL", "name": "Allied Bank", "colour": "#7C2529", "logo": "/bank-logos/abl.png"},
    {"code": "MEZN", "name": "Meezan Bank", "colour": "#00694E", "logo": "/bank-logos/mezn.png"},
    {"code": "ALFH", "name": "Bank Alfalah", "colour": "#C8102E", "logo": "/bank-logos/alfh.png"},
    {"code": "FYSL", "name": "Faysal Bank", "colour": "#006B54", "logo": "/bank-logos/fysl.png"},
    {"code": "ASKR", "name": "Askari Bank", "colour": "#005CAB", "logo": "/bank-logos/askr.png"},
    {"code": "BOP", "name": "The Bank of Punjab", "colour": "#00539F", "logo": "/bank-logos/bop.png"},
    {"code": "BIPL", "name": "BankIslami Pakistan", "colour": "#00843D", "logo": "/bank-logos/bipl.png"},
    {"code": "DIBP", "name": "Dubai Islamic Bank Pakistan", "colour": "#0E7C61", "logo": "/bank-logos/dibp.png"},
    {"code": "HMB", "name": "Habib Metropolitan Bank", "colour": "#003A70", "logo": "/bank-logos/hmb.png"},
    {"code": "JS", "name": "JS Bank", "colour": "#005596", "logo": "/bank-logos/js.png"},
    {"code": "SNBL", "name": "Soneri Bank", "colour": "#A6192E", "logo": "/bank-logos/snbl.png"},
    {"code": "SCB", "name": "Standard Chartered Pakistan", "colour": "#0473EA", "logo": "/bank-logos/scb.png"},
    {"code": "SILK", "name": "Silkbank", "colour": "#00A0DF", "logo": "/bank-logos/silk.png"},
    {"code": "SMBL", "name": "Summit Bank", "colour": "#005EA8", "logo": "/bank-logos/smbl.png"},
    {"code": "SINDH", "name": "Sindh Bank", "colour": "#007A33", "logo": "/bank-logos/sindh.png"},
    {"code": "BOK", "name": "The Bank of Khyber", "colour": "#00693E", "logo": "/bank-logos/bok.png"},
    {"code": "ALBRK", "name": "Al Baraka Bank Pakistan", "colour": "#006A4D", "logo": "/bank-logos/albrk.png"},
    {"code": "SAMBA", "name": "Samba Bank", "colour": "#003C71", "logo": "/bank-logos/samba.png"},
    {"code": "MIB", "name": "MCB Islamic Bank", "colour": "#00693E", "logo": "/bank-logos/mib.png"},
    {"code": "UMBL", "name": "U Microfinance Bank", "colour": "#7B2C8F", "logo": "/bank-logos/umbl.png"},
    {"code": "EASY", "name": "Easypaisa", "colour": "#00C46A", "logo": "/bank-logos/easy.png"},
    {"code": "JAZZ", "name": "JazzCash", "colour": "#C8102E", "logo": "/bank-logos/jazz.png"},
    {"code": "SADA", "name": "SadaPay", "colour": "#FF6B57", "logo": "/bank-logos/sada.png"},
    {"code": "NAYA", "name": "NayaPay", "colour": "#F26522", "logo": "/bank-logos/naya.png"},
    {"code": "ZNDG", "name": "Zindigi", "colour": "#4FC3B5", "logo": "/bank-logos/zndg.png"},
    {"code": "UPAISA", "name": "UPaisa", "colour": "#F58220", "logo": "/bank-logos/upaisa.png"},
]
