#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 build_by_surah.py — بناء ملف الكلمات مرتّب سورة بسورة (من غير نص الآية)
 كل كلمة بتتسجّل مرة واحدة، عند السورة اللي ظهرت فيها أول مرة.
"""
import os
from collections import defaultdict
import pandas as pd

OUT = r"D:\Claude\Work\output"
c = pd.read_csv(OUT + r"\quran_corpus.csv", encoding="utf-8-sig")
freq = pd.read_csv(OUT + r"\word_frequency_raw.csv", encoding="utf-8-sig")

freq = freq.sort_values(["count", "word"], ascending=[False, True]).reset_index(drop=True)
rank   = {w: i + 1 for i, w in enumerate(freq["word"])}
counts = dict(zip(freq["word"], freq["count"]))
nsurah = dict(zip(freq["word"], freq["number_of_distinct_surahs"]))

MAX_REFS = 12
locs = defaultdict(list)
for r in c.itertuples(index=False):
    ref = f"{r.surah_number}:{r.ayah_number}"
    for w in str(r.ayah_text_raw).split():
        locs[w].append(ref)

def refs(w):
    L = locs[w]
    return " · ".join(L) if len(L) <= MAX_REFS else " · ".join(L[:MAX_REFS]) + f" … (+{len(L)-MAX_REFS})"

# المشي بترتيب المصحف؛ كل كلمة تتسجّل عند أول ظهور
rows, seen, per_surah = [], set(), defaultdict(int)
for r in c.itertuples(index=False):
    for w in str(r.ayah_text_raw).split():
        if w in seen:
            continue
        seen.add(w)
        per_surah[r.surah_number] += 1
        rows.append({
            "الكلمة": w,
            "رقم السورة": r.surah_number,
            "السورة": r.surah_name,
            "رقم في السورة": per_surah[r.surah_number],
            "الرقم": len(seen),                     # الرقم العام 1..17,576
            "خلص": "No",
            "عدد التكرار": counts[w],
            "أول موضع": f"{r.surah_number}:{r.ayah_number}",
            "كل المواضع": refs(w),
            "عدد السور": nsurah[w],
            "ترتيب التكرار": rank[w],
        })

d = pd.DataFrame(rows)
d["إجمالي كلمات السورة"] = d["رقم السورة"].map(per_surah)
d = d[["الكلمة", "رقم السورة", "السورة", "رقم في السورة", "إجمالي كلمات السورة",
       "الرقم", "خلص", "عدد التكرار", "أول موضع", "كل المواضع",
       "عدد السور", "ترتيب التكرار"]]

assert len(d) == 17576
assert d["الكلمة"].duplicated().sum() == 0
assert sorted(d["الرقم"]) == list(range(1, 17577))
assert int(d["عدد التكرار"].sum()) == 77794
assert d["رقم السورة"].nunique() == 114
# رقم داخل كل سورة لازم يكون متسلسل 1..n
for s, g in d.groupby("رقم السورة"):
    assert sorted(g["رقم في السورة"]) == list(range(1, len(g) + 1)), f"surah {s} broken"

p = OUT + r"\quran_words_by_surah.csv"
d.to_csv(p, index=False, encoding="utf-8-sig")
print(f"rows: {len(d):,} | size: {os.path.getsize(p):,} bytes ({os.path.getsize(p)/1048576:.2f} MB)")
print("all assertions passed")
print()
print(d.head(6)[["رقم السورة","السورة","رقم في السورة","الرقم","الكلمة","عدد التكرار"]].to_string(index=False))
print("   ...")
print(d[d["رقم السورة"]==2].head(3)[["رقم السورة","السورة","رقم في السورة","الرقم","الكلمة"]].to_string(index=False))
