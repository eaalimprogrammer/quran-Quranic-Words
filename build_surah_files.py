#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 build_surah_files.py — ملف منفصل لكل سورة (114 ملف)
 كل ملف فيه كلمات السورة دي بترقيمها الداخلي + الرقم العام.
"""
import os, zipfile, shutil
import pandas as pd

OUT = r"D:\Claude\Work\output"
DIR = os.path.join(OUT, "surah_files")
if os.path.isdir(DIR):
    shutil.rmtree(DIR)
os.makedirs(DIR)

d = pd.read_csv(OUT + r"\quran_words_by_surah.csv", encoding="utf-8-sig")

COLS = ["الكلمة", "رقم في السورة", "الرقم", "خلص", "عدد التكرار",
        "أول موضع", "كل المواضع", "عدد السور", "ترتيب التكرار", "السورة", "رقم السورة"]

made, total_rows = [], 0
for sno in range(1, 115):
    g = d[d["رقم السورة"] == sno].sort_values("رقم في السورة")
    name = g["السورة"].iloc[0]
    fname = f"{sno:03d} - {name}.csv"
    path = os.path.join(DIR, fname)
    g[COLS].to_csv(path, index=False, encoding="utf-8-sig")
    # كل ملف لازم ترقيمه الداخلي متسلسل 1..n
    assert list(g["رقم في السورة"]) == list(range(1, len(g) + 1)), f"surah {sno} sequence broken"
    total_rows += len(g)
    made.append((sno, name, len(g), os.path.getsize(path)))

# ---- تحقق شامل ----
allrows = pd.concat([pd.read_csv(os.path.join(DIR, f"{s:03d} - {n}.csv"), encoding="utf-8-sig")
                     for s, n, _, _ in made])
assert total_rows == 17576, total_rows
assert len(allrows) == 17576
assert allrows["الكلمة"].duplicated().sum() == 0, "duplicate word across files!"
assert sorted(allrows["الرقم"]) == list(range(1, 17577)), "global numbering broken"
assert int(allrows["عدد التكرار"].sum()) == 77794
assert len(made) == 114

# ---- ZIP ----
zip_path = OUT + r"\quran_surah_files_114.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for s, n, _, _ in made:
        f = f"{s:03d} - {n}.csv"
        z.write(os.path.join(DIR, f), f)

print(f"files created : {len(made)}")
print(f"total rows    : {total_rows:,}")
print(f"folder        : {DIR}")
print(f"zip           : {zip_path}  ({os.path.getsize(zip_path):,} bytes)")
print(f"largest file  : {max(m[3] for m in made):,} bytes")
print("ALL CHECKS PASSED — 114 files, 17,576 rows, no duplicates, numbering intact")
print()
print("  #   السورة        كلمات")
for s, n, cnt, _ in made[:6]:
    print(f"  {s:>3} {n:<12} {cnt:>5}")
print("  ...")
for s, n, cnt, _ in made[-5:]:
    print(f"  {s:>3} {n:<12} {cnt:>5}")
