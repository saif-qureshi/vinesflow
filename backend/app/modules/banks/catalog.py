"""Banks operating in Pakistan, offered as a starting point when adding an account.

The colour is the bank's brand colour, used for the placeholder badge until a
logo is uploaded. Both are editable per organisation — this is a convenience
list, not a registry.
"""

from __future__ import annotations

PAKISTANI_BANKS: list[dict[str, str]] = [
    {"code": "HBL", "name": "Habib Bank Limited", "colour": "#00A94F"},
    {"code": "UBL", "name": "United Bank Limited", "colour": "#0C4DA2"},
    {"code": "MCB", "name": "MCB Bank", "colour": "#00693E"},
    {"code": "NBP", "name": "National Bank of Pakistan", "colour": "#006838"},
    {"code": "ABL", "name": "Allied Bank", "colour": "#7C2529"},
    {"code": "MEZN", "name": "Meezan Bank", "colour": "#00694E"},
    {"code": "ALFH", "name": "Bank Alfalah", "colour": "#C8102E"},
    {"code": "FYSL", "name": "Faysal Bank", "colour": "#006B54"},
    {"code": "ASKR", "name": "Askari Bank", "colour": "#005CAB"},
    {"code": "BOP", "name": "The Bank of Punjab", "colour": "#00539F"},
    {"code": "BIPL", "name": "BankIslami Pakistan", "colour": "#00843D"},
    {"code": "DIBP", "name": "Dubai Islamic Bank Pakistan", "colour": "#0E7C61"},
    {"code": "HMB", "name": "Habib Metropolitan Bank", "colour": "#003A70"},
    {"code": "JS", "name": "JS Bank", "colour": "#005596"},
    {"code": "SNBL", "name": "Soneri Bank", "colour": "#A6192E"},
    {"code": "SCB", "name": "Standard Chartered Pakistan", "colour": "#0473EA"},
    {"code": "SILK", "name": "Silkbank", "colour": "#00A0DF"},
    {"code": "SMBL", "name": "Summit Bank", "colour": "#005EA8"},
    {"code": "SINDH", "name": "Sindh Bank", "colour": "#007A33"},
    {"code": "BOK", "name": "The Bank of Khyber", "colour": "#00693E"},
    {"code": "ALBRK", "name": "Al Baraka Bank Pakistan", "colour": "#006A4D"},
    {"code": "FWBL", "name": "First Women Bank", "colour": "#8E1B6B"},
    {"code": "ZTBL", "name": "Zarai Taraqiati Bank", "colour": "#0F7B3F"},
    {"code": "SAMBA", "name": "Samba Bank", "colour": "#003C71"},
    {"code": "MIB", "name": "MCB Islamic Bank", "colour": "#00693E"},
    {"code": "UMBL", "name": "U Microfinance Bank", "colour": "#7B2C8F"},
    {"code": "EASY", "name": "Easypaisa", "colour": "#3AAA35"},
    {"code": "JAZZ", "name": "JazzCash", "colour": "#B01C2E"},
]
