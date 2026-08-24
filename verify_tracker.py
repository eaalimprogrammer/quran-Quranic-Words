#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 verify_tracker.py  —  فحص سلامة ملف متابعة الفيديوهات
================================================================================
 شغّلي الملف ده في أي وقت. بيقارن ملف المتابعة بالمصحف نفسه ويتأكد إن:
   1. عدد الصفوف صح
   2. مفيش كلمة مكررة
   3. الترقيم متسلسل 1..N من غير فجوات
   4. كل كلمة في الملف موجودة فعلاً في القرآن
   5. كل كلمة في القرآن موجودة في الملف (مفيش حاجة ناقصة)
   6. مجموع التكرارات = 77,794
   7. كل المواضع (سورة:آية) حقيقية
   8. خانة "خلص" قيمها صالحة
 وبيطلع تقرير تقدّم: خلص كام، فاضل كام، والكلمة الجاية.

 التشغيل:
     python verify_tracker.py [ملف_المتابعة.csv]

 لو رجّع "كل الفحوصات نجحت" يبقى الملف سليم 100%.
 لو فيه مشكلة، بيقولك بالظبط فين ومع أنهي كلمة — من غير ما يصلّح حاجة لوحده.
================================================================================
"""
import sys, os
import pandas as pd

CORPUS  = r"D:\Claude\Work\output\quran_corpus.csv"
DEFAULT = r"D:\Claude\Work\output\notion_tracker_17576_slim.csv"
EXPECTED_ROWS, EXPECTED_TOKENS = 17576, 77794

def main():
    tracker_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    print("=" * 66)
    print(" فحص سلامة ملف المتابعة")
    print("=" * 66)
    print(f" الملف   : {os.path.basename(tracker_path)}")
    print(f" المرجع  : {os.path.basename(CORPUS)}")
    print()

    c = pd.read_csv(CORPUS, encoding="utf-8-sig")
    d = pd.read_csv(tracker_path, encoding="utf-8-sig")

    problems = []
    def check(label, ok, detail=""):
        print(f"  [{'✓' if ok else '✗'}] {label}" + (f"  → {detail}" if detail else ""))
        if not ok:
            problems.append(f"{label}: {detail}")

    # 1 عدد الصفوف
    check("عدد الصفوف = 17,576", len(d) == EXPECTED_ROWS, f"وجدت {len(d):,}")

    # 2 تكرار
    dup = d["الكلمة"].duplicated().sum()
    check("مفيش كلمة مكررة", dup == 0, f"{dup} مكررة" if dup else "")
    if dup:
        for w in d.loc[d["الكلمة"].duplicated(keep=False), "الكلمة"].unique()[:5]:
            print(f"        مكررة: {w}")

    # 3 تسلسل الترقيم
    nums = sorted(d["الرقم"].tolist())
    ok_seq = nums == list(range(1, len(d) + 1))
    gaps = [i for i in range(1, len(d) + 1) if i not in set(nums)][:5] if not ok_seq else []
    check("الترقيم متسلسل 1..N", ok_seq, f"فجوات عند {gaps}" if gaps else "")

    # بناء مفردات المصحف ومواضعها
    vocab, refs = {}, set()
    for r in c.itertuples(index=False):
        refs.add(f"{r.surah_number}:{r.ayah_number}")
        for w in str(r.ayah_text_raw).split():
            vocab[w] = vocab.get(w, 0) + 1

    # 4 كل كلمة في الملف موجودة في القرآن
    extra = set(d["الكلمة"]) - set(vocab)
    check("كل كلمة في الملف موجودة في القرآن", not extra,
          f"{len(extra)} كلمة غريبة مثل {list(extra)[:3]}" if extra else "")

    # 5 كل كلمة في القرآن موجودة في الملف
    missing = set(vocab) - set(d["الكلمة"])
    check("مفيش كلمة من القرآن ناقصة", not missing,
          f"{len(missing)} ناقصة مثل {list(missing)[:3]}" if missing else "")

    # 6 مجموع التكرارات
    s = int(d["عدد التكرار"].sum())
    check(f"مجموع التكرارات = {EXPECTED_TOKENS:,}", s == EXPECTED_TOKENS, f"وجدت {s:,}")

    # 6b التكرارات مطابقة للمصحف كلمة كلمة
    mism = [w for w, n in zip(d["الكلمة"], d["عدد التكرار"]) if vocab.get(w) != n]
    check("عدد تكرار كل كلمة مطابق للمصحف", not mism,
          f"{len(mism)} غير مطابقة مثل {mism[:3]}" if mism else "")

    # 7 المواضع حقيقية
    bad = [r for r in d["أول موضع"].astype(str) if r not in refs]
    check("كل المواضع (سورة:آية) حقيقية", not bad,
          f"{len(bad)} موضع غلط مثل {bad[:3]}" if bad else "")

    # 8 خانة خلص
    vals = set(d["خلص"].astype(str).str.strip().str.lower())
    allowed = {"yes", "no", "true", "false", "نعم", "لا", "", "nan"}
    check("قيم خانة (خلص) صالحة", vals <= allowed,
          f"قيم غريبة: {vals - allowed}" if not vals <= allowed else "")

    # ---- تقرير التقدّم ----
    done_mask = d["خلص"].astype(str).str.strip().str.lower().isin({"yes", "true", "نعم"})
    done, left = int(done_mask.sum()), len(d) - int(done_mask.sum())
    print()
    print("-" * 66)
    print(" التقدّم")
    print("-" * 66)
    print(f"  خلص     : {done:,}")
    print(f"  فاضل    : {left:,}")
    print(f"  النسبة  : {100*done/len(d):.2f}%")
    nxt = d[~done_mask].sort_values("الرقم").head(3)
    if len(nxt):
        print("  الكلمات الجاية:")
        # .iterrows() لأن أسماء الأعمدة فيها مسافات ومش صالحة كـ attributes
        for _, r in nxt.iterrows():
            print(f"     #{r['الرقم']}  {r['الكلمة']}   "
                  f"({r['أول موضع']} — {r['السورة']})")

    print()
    print("=" * 66)
    if problems:
        print(f" ✗ فيه {len(problems)} مشكلة — لم يتم تصليح أي حاجة تلقائياً:")
        for p in problems:
            print(f"    - {p}")
        sys.exit(1)
    print(" ✓ كل الفحوصات نجحت — الملف سليم 100%")
    print("=" * 66)

if __name__ == "__main__":
    main()
