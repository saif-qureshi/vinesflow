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

```
abl.png    albrk.png  alfh.png   askr.png   bipl.png   bok.png
bop.png    dibp.png   easy.png   fysl.png   hbl.png    hmb.png
jazz.png   js.png     mcb.png    mezn.png   mib.png    naya.png
nbp.png    sada.png   samba.png  scb.png    silk.png   sindh.png
smbl.png   snbl.png   ubl.png    upaisa.png zndg.png
```

## Still needed

These fall back to an initials badge until a file is added:

```
umbl.png   U Microfinance Bank
```

The "Pakistani Banks - Digital Wallet - Logo" Figma community file has artwork
for it.
