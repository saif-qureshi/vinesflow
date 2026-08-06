# Bank logos

Shared artwork for the banks in `backend/app/modules/banks/catalog.py`. A file
here is picked up by every organisation — an organisation can still upload its
own on a bank account to override it. Until a file exists the badge falls back
to the bank's initials on its brand colour, so a missing file degrades quietly
rather than showing a broken image.

## Filenames

The bank's code from the catalogue, lowercased, as `.png`. Square artwork reads
best — the badge contains it inside a rounded tile.

## Present

Exported at 500×500 from the "Pakistani Banks - Digital Wallet - Logo" Figma
community file:

```
abl.png    albrk.png  alfh.png   askr.png   bipl.png
bok.png    bop.png    dibp.png   hbl.png    hmb.png
js.png     mcb.png    mezn.png   nbp.png    silk.png
sindh.png  smbl.png   snbl.png   ubl.png
```

## Still needed

These fall back to an initials badge until a file is added:

```
easy.png   Easypaisa
fwbl.png   First Women Bank
fysl.png   Faysal Bank
jazz.png   JazzCash
mib.png    MCB Islamic Bank
samba.png  Samba Bank
scb.png    Standard Chartered Pakistan
umbl.png   U Microfinance Bank
ztbl.png   Zarai Taraqiati Bank
```

The Figma file has artwork for all of these except Faysal Bank, Standard
Chartered and Samba Bank, whose frames there are empty.
