# Qur'anic Word Frequency Analysis — Summary Report

- **Source:** `D:\Claude\Work\quran.docx`
- **Orthography:** Imlaei (رسم إملائي) — established at codepoint level, see §2
- **Counting tradition for validation:** Hafs / Kufi (6236 ayat)
- **Total characters in source:** 721,974
- **Distinct Unicode codepoints:** 59

> Every figure below is followed by the exact rule that produced it. Where a figure depends on a definitional choice, the alternatives are given side by side and none is marked as correct.

## 1. Corpus

| Metric | Value | Rule |
|---|---:|---|
| Surahs | 114 | count of `سورة` header lines |
| Ayat | 6236 | segments delimited by `(n)` markers, Hafs counting |
| Standalone Basmalah headings | 111 | unnumbered paragraphs beginning `بسم` |

**Validation gate: PASSED.** 114 surahs; 6236 ayat; every per-surah count matches the hardcoded Hafs table; every surah numbers contiguously 1..N; Al-Fatihah = 7, Al-Baqarah = 286, An-Nas = 6; zero ayat contain residual markup; zero empty ayat.

## 2. Orthography and the codepoint audit trail

The source is **Imlaei, not Uthmani**. Every Uthmani-exclusive character is absent — this is a measured fact, not an inference:

| Uthmani-only character | Occurrences |
|---|---:|
| U+0671 ALEF WASLA ٱ | 0 |
| U+0670 SUPERSCRIPT (dagger) ALEF | 0 |
| U+06DD END OF AYAH ۝ | 0 |
| U+06DE START OF RUB EL HIZB ۞ | 0 |
| U+06E9 PLACE OF SAJDAH ۩ | 0 |
| U+06D6 waqf mark (first of range) | 0 |
| U+0640 TATWEEL | 0 |

### Consequences for the normalization layer

| Form | Characters | Removed vs raw | Note |
|---|---:|---:|---|
| `raw` | 685,148 | 0 |  |
| `no_marks` | 685,148 | 0 | **NO-OP — byte-identical to `raw`** |
| `no_tashkeel` | 408,498 | 276,650 |  |
| `normalized` | 408,498 | 276,650 |  |

`no_marks` removes Qur'anic annotation symbols. This source contains none, so the form is a genuine no-op here. It is still computed and reported rather than quietly dropped, because on an Uthmani source it would differ.

Full inventory of all distinct codepoints, with official Unicode names and exact counts: `codepoint_inventory.csv`.

## 3. Word segmentation — four definitions

| Definition | Total words | Rule |
|---|---:|---|
| **A** | **78,238** | split(); all 6236 ayat PLUS the standalone Basmalah headings actually present in the source (112 total, incl. Al-Fatihah's as ayah 1:1). Surah headers and (n) markers excluded. |
| **B** | **77,794** | split(); the 6236 ayat only. The 111 standalone Basmalah headings are dropped. Al-Fatihah's Basmalah is retained because it IS ayah 1:1 in the Hafs counting. |
| **C** | **77,794** | Definition B, then each of the 30 Muqatta'at occurrences (29 surahs; surah 42 has two) is counted as exactly one token. Tokens removed by this rule: 0. |
| **D** | **77,794** | Definition B. Fused units are identified and listed in review_needed.csv but are NOT split, so the total is unchanged from B by construction. The 'if split' figure below is a hypothetical shown for scale only — it is NOT a count of the Qur'an's words and must not be quoted as one. |

### The differences between these numbers are definitional, not errors.

Each total counts a different thing. None is more correct than the others; they answer different questions.

Component breakdown:

- **A** — Whitespace tokens (raw), Basmalah included
  - `ayah_tokens` = 77,794
  - `standalone_basmalah_tokens` = 444
  - `standalone_basmalah_count` = 111
- **B** — Whitespace tokens, Basmalah excluded (except Al-Fatihah 1:1)
  - `ayah_tokens` = 77,794
- **C** — Definition B, with Muqatta'at forced to one token each
  - `base_definition_B` = 77,794
  - `tokens_removed_by_muqattaat_merge` = 0
  - `muqattaat_occurrences_examined` = 30
- **D** — Fused orthographic units: FLAGGED, NOT SPLIT
  - `base_definition_B` = 77,794
  - `fused_occurrences_flagged` = 1,669
  - `distinct_fused_types` = 38
  - `homographs_suppressed_by_vocalization_gate` = 171
  - `hypothetical_total_if_all_split` = 79,470
  - `hypothetical_extra_tokens` = 1,676

**Excluded from every definition:** surah header lines (232 tokens across 114 lines) are editorial apparatus, not Qur'anic text. Ayah marker numerals `(n)` are delimiters, not tokens.

### Definition D is deliberately not a smaller number

The brief requires fused units to be **flagged, not split**. They were flagged. D therefore equals B by construction. The 'if all were split' figure in the component list is a hypothetical for scale only and must not be quoted as a word count of the Qur'an. The decision on each case is yours; every occurrence is in `review_needed.csv` with its surah:ayah.

### Homograph suppression (vocalization gate)

Some fused forms are indistinguishable from ordinary words once tashkeel is stripped. Because this source is fully vocalized, harakat separate them mechanically. Flagging on the bare skeleton alone would have filled the review list with false positives. The following were identified as homographs and deliberately **not** flagged:

| Skeleton | Occurrences suppressed | Why it is not a fusion |
|---|---:|---|
| `لم` | 163 | the jussive negative particle لَمْ (the fusion is لِمَ, which *is* flagged) |
| `مال` | 5 | the noun مَال 'wealth' in its nominative/accusative/indefinite forms |
| `إلا` | 2 | the noun إِلًّا 'kinship/covenant' at 9:8 and 9:10 |
| `أمن` | 1 | the verb أَمِنَ 'he trusted' at 2:283 |

This gate affects only the *precision of the review list*. It changes no word total, because Definition D splits nothing.

## 4. Comparison with published counts

Published totals commonly cited include ~77,430, ~77,439, and ~77,797. They disagree with each other, and this analysis does not adjudicate between them. The following accounts for where the gaps come from — it does **not** claim any published figure is authoritative, nor that the figures here are.

| Source of variation | Effect on the total |
|---|---:|
| Including vs excluding the 111 standalone Basmalah headings | 444 tokens (A − B) |
| Muqatta'at merged to one token each | 0 tokens (B − C) |
| Fused units split (hypothetical, NOT applied) | +1,676 tokens |

The single largest driver, however, is **orthography, not arithmetic**. This source is Imlaei. Imlaei writes as two tokens much of what Uthmani writes as one — most conspicuously `يا أيها` (two tokens here) against Uthmani `يَٰٓأَيُّهَا` (one). A count taken over an Uthmani rasm will therefore be *lower* than the same rule applied to this text. Any comparison between a figure here and a published figure must first establish that both used the same rasm; otherwise the comparison is meaningless.

## 5. Frequency analysis

| Form | Total tokens | Unique types | Hapax legomena | Type/token ratio |
|---|---:|---:|---:|---:|
| `raw` | 77,794 | 17,576 | 10,880 | 0.22593 |
| `no_marks` | 77,794 | 17,576 | 10,880 | 0.22593 |
| `no_tashkeel` | 77,794 | 14,872 | 8,711 | 0.19117 |
| `normalized` | 77,794 | 14,652 | 8,549 | 0.18834 |

### Why the unique counts differ so much

Token totals are identical across all four forms — normalization never adds or removes whitespace boundaries, so it cannot change *how many* words there are. It changes only how many are judged **the same word**.

- `raw` → `no_marks`: no change on this source (no annotation marks exist).
- `no_marks` → `no_tashkeel`: collapses every vocalization variant of one consonantal skeleton into a single type. This is the largest single drop: words differing only by case-ending (i'rab) merge.
- `no_tashkeel` → `normalized`: merges hamza-carrier variants, ى with ي, and ة with ه. **These are conventions, not facts**, and each is a deliberate choice documented in §6.

A rising unique count means finer distinctions are preserved; a falling one means more surface forms are being treated as the same lexical item. Neither is 'the' vocabulary size of the Qur'an — that depends entirely on what you consider one word.

### Top 20 — form `normalized`

| # | Word | Count | First occurrence | Distinct surahs |
|---:|---|---:|---|---:|
| 1 | من | 2,763 | 2:4 | 98 |
| 2 | الله | 2,155 | 1:1 | 81 |
| 3 | ان | 1,605 | 2:6 | 97 |
| 4 | في | 1,185 | 2:10 | 93 |
| 5 | ما | 1,010 | 2:17 | 96 |
| 6 | لا | 812 | 2:2 | 83 |
| 7 | الذين | 810 | 1:7 | 74 |
| 8 | الا | 763 | 2:9 | 80 |
| 9 | علي | 686 | 2:5 | 83 |
| 10 | ولا | 658 | 1:7 | 78 |
| 11 | وما | 646 | 2:4 | 85 |
| 12 | الي | 430 | 2:14 | 80 |
| 13 | قال | 416 | 2:30 | 41 |
| 14 | لهم | 373 | 2:11 | 69 |
| 15 | يا | 349 | 2:21 | 59 |
| 16 | ومن | 342 | 2:8 | 67 |
| 17 | ثم | 340 | 2:28 | 72 |
| 18 | لكم | 337 | 2:22 | 64 |
| 19 | كان | 333 | 2:75 | 69 |
| 20 | به | 327 | 2:22 | 63 |

Full tables: `word_frequency_<form>.csv`. Top 200: `top200_<form>.csv`. Hapax with locations: `hapax_<form>.csv`.

### Distribution histogram

How many distinct word types occur exactly N times (form `normalized`; per-form tables in `frequency_distribution_<form>.csv`):

| Occurrences | Distinct word types | Tokens accounted for |
|---|---:|---:|
| 1× | 8,549 | 8,549 |
| 2× | 2,366 | 4,732 |
| 3× | 1,013 | 3,039 |
| 4× | 619 | 2,476 |
| 5× | 399 | 1,995 |
| 6× | 278 | 1,668 |
| 7× | 199 | 1,393 |
| 8× | 130 | 1,040 |
| 9× | 117 | 1,053 |
| 10× | 93 | 930 |
| 11–99× | 792 | 21,341 |
| 100+× | 97 | 29,578 |

The distribution is steeply Zipfian: 8,549 types (58.3% of the vocabulary) occur exactly once, yet account for only 11.0% of all tokens. Full per-count table in `frequency_distribution.csv`.

### Longest and shortest words

Reported for two forms, because the answer differs and only one of them is linguistically meaningful. In `raw`, length is inflated by combining marks — each haraka is its own codepoint — so `raw` measures *storage*, not word length. `normalized` measures letters.

**Form `normalized` — longest:**

| Word | Chars | Count | First |
|---|---:|---:|---|
| والمستضعفين | 11 | 2 | 4:75 |
| فاسقيناكموه | 11 | 1 | 15:22 |
| والمستغفرين | 11 | 1 | 3:17 |
| والمنافقات | 10 | 5 | 9:67 |
| والمنافقين | 10 | 4 | 9:73 |
| وبالوالدين | 10 | 4 | 2:83 |
| والمهاجرين | 10 | 3 | 9:117 |
| ويستعجلونك | 10 | 3 | 13:6 |
| فليستجيبوا | 10 | 2 | 2:186 |
| والموتفكات | 10 | 2 | 9:70 |

**Form `normalized` — shortest:**

| Word | Chars | Count | First |
|---|---:|---:|---|
| ص | 1 | 1 | 38:1 |
| ق | 1 | 1 | 50:1 |
| ن | 1 | 1 | 68:1 |
| من | 2 | 2763 | 2:4 |
| ان | 2 | 1605 | 2:6 |
| في | 2 | 1185 | 2:10 |
| ما | 2 | 1010 | 2:17 |
| لا | 2 | 812 | 2:2 |
| يا | 2 | 349 | 2:21 |
| ثم | 2 | 340 | 2:28 |

**Form `raw` — longest:**

| Word | Chars | Count | First |
|---|---:|---:|---|
| لَيَسْتَخْلِفَنَّهُمْ | 21 | 1 | 24:55 |
| وَالْمُسْتَضْعَفِينَ | 20 | 2 | 4:75 |
| وَلَأُصَلِّبَنَّكُمْ | 20 | 2 | 20:71 |
| فَأَسْقَيْنَاكُمُوهُ | 20 | 1 | 15:22 |
| وَالْمُسْتَغْفِرِينَ | 20 | 1 | 3:17 |
| وَلَأُمَنِّيَنَّهُمْ | 20 | 1 | 4:119 |
| وَلَيُبَدِّلَنَّهُمْ | 20 | 1 | 24:55 |
| وَلَنَجْزِيَنَّهُمْ | 19 | 3 | 16:97 |
| وَيَسْتَعْجِلُونَكَ | 19 | 3 | 13:6 |
| وَلَنَبْلُوَنَّكُمْ | 19 | 2 | 2:155 |

**Form `raw` — shortest:**

| Word | Chars | Count | First |
|---|---:|---:|---|
| ص | 1 | 1 | 38:1 |
| ق | 1 | 1 | 50:1 |
| ن | 1 | 1 | 68:1 |
| حم | 2 | 7 | 40:1 |
| طس | 2 | 1 | 27:1 |
| طه | 2 | 1 | 20:1 |
| يس | 2 | 1 | 36:1 |
| فِي | 3 | 1185 | 2:10 |
| مَا | 3 | 1010 | 2:17 |
| لَا | 3 | 812 | 2:2 |

### Per-surah statistics

Full table: `per_surah_statistics.csv` (word count, unique count and lexical density for all 114 surahs, under all four forms).

| # | Surah | Ayat | Words | Unique | Density |
|---:|---|---:|---:|---:|---:|
| 2 | البقرة | 286 | 6,140 | 2,254 | 0.3671 |
| 4 | النساء | 176 | 3,763 | 1,505 | 0.3999 |
| 3 | آل عمران | 200 | 3,501 | 1,459 | 0.4167 |
| 7 | الأعراف | 206 | 3,341 | 1,545 | 0.4624 |
| 6 | الأنعام | 165 | 3,056 | 1,347 | 0.4408 |

Lexical density = unique / total within that surah. Short surahs score high mechanically, because there is less room for repetition — the metric is not comparable across surahs of very different lengths.

## 6. Caveats, conventions, and open decisions

### Conventions chosen (each is contestable; each is isolated in the code)

1. **`ى` → `ي`** in `normalized`. A convention, not a fact. It merges e.g. `علي`/`على`. Mapping `ى` → `ا` instead, or leaving it distinct, changes the `normalized` unique count and nothing else.
2. **`ة` → `ه`** in `normalized`. Merges e.g. `رحمة`/`رحمه`. Same isolation.
3. **Surah headers excluded** from all word counts as editorial apparatus.
4. **Ayah markers `(n)` are delimiters**, never tokens.
5. **Whitespace splitting only.** No stemming, no clitic separation, no root extraction.

### Source anomalies — recorded, never repaired

- **Surah 15 (الحجر), ayah 99:** the source has no `(99)` marker. The ayah text is present and complete; only the delimiter is missing. Rule `TRAILING_REMAINDER_AS_FINAL_AYAH` inferred the boundary. No text was created, altered, or reconstructed. Hafs boundary match: yes.
- **Surah 104 (الهمزة):** the Basmalah is absent from the source document. Surahs 103 and 105 have theirs. It was **not** reconstructed. Definition A therefore counts 112 Basmalah instances, not 113 — four tokens fewer than a source carrying all of them.

### Awaiting your decision

`review_needed.csv` holds 1669 flagged fused-unit occurrences, each with its surah:ayah reference, the raw token, the rule that flagged it, and a suggested decomposition. Nothing in that file has been acted on.

## 7. What was verified vs what was assumed

### Verified (measured directly from the source)

- Extraction is lossless: zero `w:delText`, `w:sym`, `w:instrText` nodes; zero U+FFFD; zero unexpected codepoints across the whole file.
- Reading order is correct: WordprocessingML stores logical order; ayah markers ascend contiguously 1..N in every surah.
- All 59 distinct codepoints identified by official Unicode name.
- The source is Imlaei: every Uthmani-exclusive codepoint counted, all zero.
- 114 surahs, 6236 ayat, every per-surah count matched against a hardcoded Hafs table.
- Basmalah census reconciled exactly: every occurrence of the string `بسم` in the file is accounted for, including two coincidental substring matches (`بسمعهم` 2:20, `فتبسم` 27:19) that are not the word.
- Token totals are identical across all four normalization forms, as they must be.

### Assumed (choices made, not facts derived)

- **The Hafs/Kufi table itself** is taken as the reference standard. Other counting traditions (Basri, Madani, Makki, Shami) give different per-surah totals. Nothing here validates Hafs as correct; it validates the source *against* Hafs.
- **Surah 15:99's boundary** was inferred from the surah's end, on your instruction. The text is verbatim from the source; the boundary is not.
- **The fused-forms list** in `FUSED_FORMS` is a curated set, not an exhaustive one. Absence from that list is not evidence that a token is unfused — it means the pipeline was not told to look for it.
- **The vocalization gate** resolves homographs using the source's own harakat, which is objective. But one case remains genuinely unresolved: `مَالِ` is the fusion at 18:49 and 25:7 and the noun 'wealth' at 24:33. Vocalization cannot separate those three; only context can. All three are flagged, with a note, for you to split manually.
- **`أَلَا` (54 occurrences) is classed as contested, not fused.** Reading the inceptive particle as interrogative hamza + `لا` is one analysis among several. It is listed under its own rule `PARTICLE_A_LA` so it can be included or excluded independently of the genuine `أَلَّا` fusions.
- **The orthographic mappings** `ى`→`ي` and `ة`→`ه` are conventions.
- **Word-level analysis only.** No morphological claim is made. Arabic clitics (`و`, `ف`, `ب`, `ل`, `ال`, pronominal suffixes) remain attached, so `الكتاب` and `بالكتاب` are distinct types under every form here.
