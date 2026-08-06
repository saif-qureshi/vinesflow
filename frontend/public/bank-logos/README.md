# Bank logos

Drop each bank's logo here and every organisation picks it up — no per-account
upload needed. An organisation can still upload its own on the bank account to
override whatever sits here.

Until a file exists the badge falls back to the bank's initials on its brand
colour, so the app works with this folder empty and lights up file by file.

## Filenames

Named after the bank code in `backend/app/modules/banks/catalog.py`, lowercased,
as `.svg`. SVG keeps them crisp at any size; a PNG works if you change the
`logo` path in the catalog to match.

```
hbl.svg      Habib Bank Limited
ubl.svg      United Bank Limited
mcb.svg      MCB Bank
nbp.svg      National Bank of Pakistan
abl.svg      Allied Bank
mezn.svg     Meezan Bank
alfh.svg     Bank Alfalah
fysl.svg     Faysal Bank
askr.svg     Askari Bank
bop.svg      The Bank of Punjab
bipl.svg     BankIslami Pakistan
dibp.svg     Dubai Islamic Bank Pakistan
hmb.svg      Habib Metropolitan Bank
js.svg       JS Bank
snbl.svg     Soneri Bank
scb.svg      Standard Chartered Pakistan
silk.svg     Silkbank
smbl.svg     Summit Bank
sindh.svg    Sindh Bank
bok.svg      The Bank of Khyber
albrk.svg    Al Baraka Bank Pakistan
fwbl.svg     First Women Bank
ztbl.svg     Zarai Taraqiati Bank
samba.svg    Samba Bank
mib.svg      MCB Islamic Bank
umbl.svg     U Microfinance Bank
easy.svg     Easypaisa
jazz.svg     JazzCash
```

Square artwork on a transparent background reads best — the badge renders them
contained inside a 40px rounded tile.
