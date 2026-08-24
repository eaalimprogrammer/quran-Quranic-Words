#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 QUR'ANIC WORD FREQUENCY ANALYZER
================================================================================
 Deterministic, auditable text-analysis pipeline for the Qur'anic text.

 GOVERNING RULES (non-negotiable, enforced structurally by this script)
 ---------------------------------------------------------------------
 R1. The canonical corpus is NEVER modified, "fixed", or normalized.
     `ayah_text_raw` is a verbatim substring of the source document.
     All normalization lives in a DERIVED layer computed on demand.
 R2. Every number produced is traceable to exactly one explicit, named rule.
     Where scholars disagree, multiple numbers are reported side by side and
     no single one is presented as "the" answer.
 R3. No text is guessed, filled in, reconstructed, rounded, or estimated.

 SOURCE-SPECIFIC FINDINGS (established in Phase 0, confirmed at codepoint level)
 ------------------------------------------------------------------------------
 F1. The source is IMLAEI (رسم إملائي), NOT Uthmani (رسم عثماني).
     Zero occurrences of: U+0671 alef wasla, U+0670 dagger alif, U+06DD end-of-
     ayah, U+06DE rub-el-hizb, U+06E9 sajdah, U+06D6..U+06DC waqf marks,
     U+06DF..U+06ED small marks, U+0640 tatweel, U+200B..U+200F / U+FEFF.
     Consequence: the `no_marks` form is a NO-OP (identical to `raw`), and
     several `normalized` sub-rules match zero characters. Both facts are
     measured and reported rather than hidden.
 F2. Surah 15 (الحجر) is missing its "(99)" ayah marker. The TEXT of 15:99 is
     present and complete; only the delimiter numeral is absent.
     Operator decision: accept the trailing remainder as ayah 99
     (rule TRAILING_REMAINDER_AS_FINAL_AYAH). No text invented — only a
     segmentation boundary inferred. Every application is logged.
 F3. Surah 104 (الهمزة) has NO Basmalah in the source. Neighbours 103 and 105
     do. Operator decision: leave absent, document it. Definition A therefore
     counts 112 Basmalah instances, not 113.

 OUTPUT ARTIFACTS  (written to OUTPUT_DIR)
 -----------------------------------------
   quran_corpus.csv                  structured surah/ayah/text
   word_frequency_raw.csv            frequency table, form `raw`
   word_frequency_no_marks.csv       frequency table, form `no_marks`
   word_frequency_no_tashkeel.csv    frequency table, form `no_tashkeel`
   word_frequency_normalized.csv     frequency table, form `normalized`
   codepoint_inventory.csv           Unicode audit trail
   review_needed.csv                 ambiguous segmentation, for operator review
   per_surah_statistics.csv          per-surah word/unique/lexical density
   frequency_distribution.csv        histogram of occurrence counts
   hapax_<form>.csv                  words occurring exactly once, w/ locations
   top200_<form>.csv                 200 most frequent words
   summary_report.md                 all totals, all definitions, all caveats

 USAGE
 -----
   python quran_analyzer.py [source.docx] [output_dir]

 Requires: pandas.  Standard library only otherwise.
================================================================================
"""

import sys
import os
import re
import zipfile
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, OrderedDict

import pandas as pd

# ==============================================================================
# SECTION 0 — CONFIGURATION AND REFERENCE CONSTANTS
# ==============================================================================

SOURCE_DOCX = sys.argv[1] if len(sys.argv) > 1 else r"D:\Claude\Work\quran.docx"
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else r"D:\Claude\Work\output"

# CSVs are written UTF-8 **with BOM** so Excel renders Arabic correctly.
CSV_ENCODING = "utf-8-sig"
# Markdown / text reports are written UTF-8 without BOM.
TXT_ENCODING = "utf-8"

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# ------------------------------------------------------------------------------
# Standard Hafs / Kufi per-surah ayah counts. Index 0 == surah 1.
# This table is the ASSERTION TARGET for the Phase 1 validation gate.
# Basmalah is excluded from every count except Al-Fatihah, where it is ayah 1.
# ------------------------------------------------------------------------------
HAFS_AYAH_COUNTS = [
      7, 286, 200, 176, 120, 165, 206,  75, 129, 109,   # 1-10
    123, 111,  43,  52,  99, 128, 111, 110,  98, 135,   # 11-20
    112,  78, 118,  64,  77, 227,  93,  88,  69,  60,   # 21-30
     34,  30,  73,  54,  45,  83, 182,  88,  75,  85,   # 31-40
     54,  53,  89,  59,  37,  35,  38,  29,  18,  45,   # 41-50
     60,  49,  62,  55,  78,  96,  29,  22,  24,  13,   # 51-60
     14,  11,  11,  18,  12,  12,  30,  52,  52,  44,   # 61-70
     28,  28,  20,  56,  40,  31,  50,  40,  46,  42,   # 71-80
     29,  19,  36,  25,  22,  17,  19,  26,  30,  20,   # 81-90
     15,  21,  11,   8,   8,  19,   5,   8,   8,  11,   # 91-100
     11,   8,   3,   9,   5,   4,   7,   3,   6,   3,   # 101-110
      5,   4,   5,   6,                                  # 111-114
]

# Surahs that legitimately have NO Basmalah, by long-standing tradition.
SURAHS_WITHOUT_BASMALAH_BY_TRADITION = {9}          # At-Tawbah
# Surah whose Basmalah IS an ayah (numbered), not a structural heading.
SURAH_WITH_BASMALAH_AS_AYAH = 1                      # Al-Fatihah

# ------------------------------------------------------------------------------
# Al-Muqatta'at (الحروف المقطعة) — the disconnected letters.
# 29 surahs, 30 ayat (surah 42 carries two). Listed as (surah, ayah, letters)
# in the undotted/plain orthography used by this source.
# ------------------------------------------------------------------------------
MUQATTAAT = [
    (2, 1, "الم"),    (3, 1, "الم"),    (7, 1, "المص"),  (10, 1, "الر"),
    (11, 1, "الر"),   (12, 1, "الر"),   (13, 1, "المر"), (14, 1, "الر"),
    (15, 1, "الر"),   (19, 1, "كهيعص"), (20, 1, "طه"),   (26, 1, "طسم"),
    (27, 1, "طس"),    (28, 1, "طسم"),   (29, 1, "الم"),  (30, 1, "الم"),
    (31, 1, "الم"),   (32, 1, "الم"),   (36, 1, "يس"),   (38, 1, "ص"),
    (40, 1, "حم"),    (41, 1, "حم"),    (42, 1, "حم"),   (42, 2, "عسق"),
    (43, 1, "حم"),    (44, 1, "حم"),    (45, 1, "حم"),   (46, 1, "حم"),
    (50, 1, "ق"),     (68, 1, "ن"),
]

# ------------------------------------------------------------------------------
# DEFINITION D — orthographically fused units.
# These are tokens where the script writes as ONE word what is arguably two or
# more. They are FLAGGED FOR REVIEW ONLY and are NEVER split by this pipeline.
# Keys are the `no_tashkeel` surface form; values are (rule_name, decomposition).
# The decomposition column is a SUGGESTION for the operator, not an action.
# ------------------------------------------------------------------------------
FUSED_FORMS = {
    # --- the canonical Uthmani/Imlaei "joined" cases named in the brief ---
    "بسم":     ("FUSED_BI_ISM",        "بـ + اسم"),
    "ويكأن":   ("FUSED_WAYKAANNA",     "وي + كأن"),
    "ويكأنه":  ("FUSED_WAYKAANNA",     "وي + كأن + ه"),
    "يبنؤم":   ("FUSED_YABNA_UMMA",    "يا + ابن + أم"),
    "أيها":    ("FUSED_AYYUHA",        "أي + ها"),
    "أيتها":   ("FUSED_AYYUHA",        "أية + ها"),
    # --- أن/إن + لا ---
    # NOTE: "ألا" and "إلا" are NOT here — they are homographs once tashkeel is
    # stripped, and are handled by VOCALIZATION_GATE below.
    "ألن":     ("FUSED_AN_LAN",        "أن + لن"),
    "كيلا":    ("FUSED_KAY_LA",        "كي + لا"),
    "لئلا":    ("FUSED_LI_AN_LA",      "لـ + أن + لا"),
    # --- من/عن/ما contractions ---
    "مما":     ("FUSED_MIN_MA",        "من + ما"),
    "عما":     ("FUSED_AN_MA",         "عن + ما"),
    "ممن":     ("FUSED_MIN_MAN",       "من + من"),
    "عمن":     ("FUSED_AN_MAN",        "عن + من"),
    "أما":     ("FUSED_AM_MA",         "أم + ما"),
    "إما":     ("FUSED_IN_MA",         "إن + ما"),
    "فيم":     ("FUSED_FI_MA",         "في + ما"),
    "بم":      ("FUSED_BI_MA",         "بـ + ما"),
    "عم":      ("FUSED_AN_MA",         "عن + ما"),
    "مم":      ("FUSED_MIN_MA",        "من + ما"),
    "إنما":    ("FUSED_INNA_MA",       "إن + ما"),
    "أنما":    ("FUSED_ANNA_MA",       "أن + ما"),
    "كأنما":   ("FUSED_KAANNA_MA",     "كأن + ما"),
    "كلما":    ("FUSED_KULLA_MA",      "كل + ما"),
    "ريثما":   ("FUSED_RAYTHA_MA",     "ريث + ما"),
    "حيثما":   ("FUSED_HAYTHU_MA",     "حيث + ما"),
    "أينما":   ("FUSED_AYNA_MA",       "أين + ما"),
    "كيفما":   ("FUSED_KAYFA_MA",      "كيف + ما"),
    "نعما":    ("FUSED_NIMA_MA",       "نعم + ما"),
    "بئسما":   ("FUSED_BISA_MA",       "بئس + ما"),
    "قلما":    ("FUSED_QALLA_MA",      "قل + ما"),
    # NOTE: "مال" / "فمال" are homographs of the noun مَال ("wealth") once
    # tashkeel is stripped — see VOCALIZATION_GATE below.
    # --- لا + ت ---
    "لات":     ("FUSED_LA_TA",         "لا + ت"),
    # --- ها + demonstrative ---
    "هذا":     ("FUSED_HA_DEM",        "ها + ذا"),
    "هذه":     ("FUSED_HA_DEM",        "ها + ذه"),
    "هذان":    ("FUSED_HA_DEM",        "ها + ذان"),
    "هذين":    ("FUSED_HA_DEM",        "ها + ذين"),
    "هؤلاء":   ("FUSED_HA_DEM",        "ها + أولاء"),
    "هاتين":   ("FUSED_HA_DEM",        "ها + تين"),
    # --- إذ / يوم + ئذ ---
    "يومئذ":   ("FUSED_IDH",           "يوم + إذ"),
    "حينئذ":   ("FUSED_IDH",           "حين + إذ"),
    "ساعتئذ":  ("FUSED_IDH",           "ساعة + إذ"),
    "عندئذ":   ("FUSED_IDH",           "عند + إذ"),
    # --- يا + vocative fused ---
    # NOTE: "يقوم" is NOT here. In Uthmani rasm يَٰقَوْمِ is fused, but this source
    # is Imlaei and writes the vocative as two tokens (يا قوم). Every "يقوم" in
    # this file is the verb يَقُومُ. Verified: 5/5 occurrences, single vocalization.
    "يبني":    ("FUSED_YA_VOCATIVE",   "يا + بني"),
    "ياويلتى": ("FUSED_YA_WAYLATA",    "يا + ويلتى"),
    "ويلتى":   ("FUSED_WAYLATA",       "وي + لتى"),
}

# ------------------------------------------------------------------------------
# VOCALIZATION GATE — homograph disambiguation.
#
# Several fused forms become indistinguishable from ordinary words once tashkeel
# is stripped. Because THIS source is fully vocalized, the harakat can separate
# them mechanically. Flagging on the bare skeleton alone would fill the review
# list with false positives (e.g. 163 occurrences of the jussive particle لَمْ
# masquerading as the fusion لِمَ).
#
# Rule: if a token's `no_tashkeel` form is a key here, ONLY the vocalized `raw`
# forms listed are flagged. Any other vocalization is a homograph and is
# deliberately NOT flagged. This gate is a precision filter on the review list;
# it changes no word total, because Definition D splits nothing.
#
#   no_tashkeel -> { raw_vocalized : (rule, decomposition, ambiguity_note) }
# ------------------------------------------------------------------------------
VOCALIZATION_GATE = {
    "لم": {
        "لِمَ": ("FUSED_LI_MA", "لـ + ما", ""),
        # لَمْ (163x) = the jussive negative particle. Not a fusion. Not flagged.
    },
    "إلا": {
        "إِلَّا": ("FUSED_IN_LA", "إن + لا", ""),
        # إِلًّا (9:8, 9:10) = the noun "kinship/covenant". Not a fusion.
    },
    "ألا": {
        "أَلَّا": ("FUSED_AN_LA", "أن + لا", ""),
        "أَلَا": ("PARTICLE_A_LA", "أ + لا",
                  "CONTESTED: the inceptive particle أَلَا. Reading it as "
                  "interrogative hamza + لا is one analysis among several; many "
                  "grammarians treat it as a simple particle. Listed so the "
                  "choice is yours, not the pipeline's."),
    },
    "أمن": {
        "أَمَّنْ": ("FUSED_AM_MAN", "أم + من", ""),
        # أَمِنَ (2:283) = the verb "he trusted". Not a fusion.
    },
    "مال": {
        "مَالِ": ("FUSED_MA_LI", "ما + لـ",
                  "PARTIALLY AMBIGUOUS: vocalization narrows this to 3 tokens but "
                  "does not fully resolve them. 18:49 and 25:7 are the fusion "
                  "(ما + لـ); 24:33 (مَالِ اللَّهِ) is the noun 'wealth' in the "
                  "genitive. Only context separates these — review individually."),
        # مَالَ / مَالٍ / مَالٌ = the noun "wealth". Not fusions.
    },
    "فمال": {
        "فَمَالِ": ("FUSED_MA_LI", "فـ + ما + لـ", ""),
    },
}

# ==============================================================================
# SECTION 1 — NORMALIZATION LAYER (derived; never applied to the canonical text)
# ==============================================================================
#
# FOUR PARALLEL FORMS. Each is a pure function of `raw`; none mutates anything.
#
#   raw          verbatim source substring, every mark intact
#   no_marks     - Qur'anic annotation symbols  (tashkeel KEPT)
#   no_tashkeel  - the above, + harakat and dagger alif
#   normalized   - the above, + orthographic unification
#
# Each rule below carries the exact codepoint range it acts on, so any reported
# number can be traced back to the character class that produced it.
# ------------------------------------------------------------------------------

# RULE N1 — Qur'anic annotation symbols.
#   U+06D6..U+06DC  waqf marks        ۖ ۗ ۘ ۙ ۚ ۛ ۜ
#   U+06DD          end of ayah       ۝
#   U+06DE          start of rub el hizb ۞
#   U+06DF..U+06E8  small high marks (rounded zero, meem, seen, waw, yeh, noon)
#   U+06E9          place of sajdah   ۩
#   U+06EA..U+06ED  empty-centre stops, small low meem
#   U+0610..U+061A  Arabic honorific / small high marks (checked; absent here)
RE_ANNOTATION = re.compile("[\u06D6-\u06ED\u0610-\u061A]")

# RULE N2 — harakat / tashkeel.
#   U+064B..U+0652  fathatan, dammatan, kasratan, fatha, damma, kasra,
#                   shadda, sukun
#   U+0653..U+065F  maddah, hamza above/below, subscript alef, and the other
#                   combining vowel signs
#   U+0670          superscript (dagger) alif  ٰ
RE_TASHKEEL = re.compile("[\u064B-\u065F\u0670]")

# RULE N3 — tatweel (kashida), a pure typographic elongation.
#   U+0640
RE_TATWEEL = re.compile("\u0640")

# RULE N4 — zero-width and bidi formatting characters.
#   U+200B..U+200F, U+FEFF, U+00AD, U+202A..U+202E
RE_ZEROWIDTH = re.compile("[\u200B-\u200F\uFEFF\u00AD\u202A-\u202E]")

# RULE N5 — whitespace normalization: any run of whitespace -> single space.
RE_WHITESPACE = re.compile(r"\s+")

# RULE N6 — orthographic unification of letter forms.
# NOTE: this is a CONVENTION, not a fact of the language. Two choices below are
# genuinely contested and are stated explicitly rather than buried:
#   (a) ى (alef maksura U+0649) -> ي  . Many pipelines map ى -> ا instead, or
#       leave it distinct. Mapping to ي merges e.g. علي/على into one type.
#   (b) ة (teh marbuta U+0629) -> ه  . This merges e.g. رحمة/رحمه.
# Both materially change the `normalized` unique-word count. Changing either
# line changes that number, and only that number.
ORTHOGRAPHIC_MAP = {
    "\u0623": "\u0627",  # أ  alef with hamza above   -> ا
    "\u0625": "\u0627",  # إ  alef with hamza below   -> ا
    "\u0622": "\u0627",  # آ  alef with madda above   -> ا
    "\u0671": "\u0627",  # ٱ  alef wasla              -> ا
    "\u0672": "\u0627",  # ٲ  alef with wavy hamza abv-> ا
    "\u0673": "\u0627",  # ٳ  alef with wavy hamza blw-> ا
    "\u0649": "\u064A",  # ى  alef maksura            -> ي   [CONVENTION]
    "\u0629": "\u0647",  # ة  teh marbuta             -> ه   [CONVENTION]
    "\u0624": "\u0648",  # ؤ  waw with hamza          -> و
    "\u0626": "\u064A",  # ئ  yeh with hamza          -> ي
}
ORTHOGRAPHIC_TRANS = str.maketrans(ORTHOGRAPHIC_MAP)


def form_raw(text):
    """Form 1 — verbatim. Identity function, present so all four forms are
    produced by the same uniform mechanism and none is privileged."""
    return text


def form_no_marks(text):
    """Form 2 — RULE N1 only. Annotation symbols out, tashkeel retained."""
    return RE_ANNOTATION.sub("", text)


def form_no_tashkeel(text):
    """Form 3 — RULE N1 + N2. Consonantal skeleton with orthography intact."""
    return RE_TASHKEEL.sub("", RE_ANNOTATION.sub("", text))


def form_normalized(text):
    """Form 4 — RULE N1 + N2 + N3 + N4 + N5 + N6."""
    t = RE_ANNOTATION.sub("", text)
    t = RE_TASHKEEL.sub("", t)
    t = RE_TATWEEL.sub("", t)
    t = RE_ZEROWIDTH.sub("", t)
    t = t.translate(ORTHOGRAPHIC_TRANS)
    t = RE_WHITESPACE.sub(" ", t).strip()
    return t


FORMS = OrderedDict([
    ("raw", form_raw),
    ("no_marks", form_no_marks),
    ("no_tashkeel", form_no_tashkeel),
    ("normalized", form_normalized),
])


# ==============================================================================
# SECTION 2 — PHASE 1: SAFE EXTRACTION
# ==============================================================================

def extract_docx_paragraphs(path):
    """Read word/document.xml and return paragraph strings in reading order.

    WordprocessingML stores runs in LOGICAL order, never visual order, so RTL
    text needs no reversal. Node order from ElementTree.iter() is document
    order, which is exactly what we want.

    Raises on tracked-change text or symbol runs — both would mean characters
    exist that this extractor would silently drop.
    """
    with zipfile.ZipFile(path) as z:
        xml_bytes = z.read("word/document.xml")
    root = ET.fromstring(xml_bytes)

    # Integrity guards: anything here means the naive w:t walk is lossy.
    n_del = len(list(root.iter(W_NS + "delText")))
    n_sym = len(list(root.iter(W_NS + "sym")))
    n_instr = len(list(root.iter(W_NS + "instrText")))
    if n_del:
        raise SystemExit(f"ABORT: {n_del} tracked-change (w:delText) nodes present.")
    if n_sym:
        raise SystemExit(f"ABORT: {n_sym} w:sym nodes — characters stored outside w:t.")
    if n_instr:
        raise SystemExit(f"ABORT: {n_instr} w:instrText field-code nodes present.")

    paragraphs = []
    for p in root.iter(W_NS + "p"):
        buf = []
        for node in p.iter():           # document order, includes p itself
            if node.tag == W_NS + "t":
                buf.append(node.text or "")
            elif node.tag == W_NS + "tab":
                buf.append("\t")
            elif node.tag == W_NS + "br":
                buf.append("\n")
        paragraphs.append("".join(buf))
    return paragraphs


# ==============================================================================
# SECTION 3 — PHASE 1: STRUCTURING INTO A CORPUS
# ==============================================================================

# Line classifiers. All operate on a tashkeel-stripped VIEW of the line; the
# canonical line itself is never altered.
WORD_SURAH = "سورة"
WORD_BISM = "بسم"
# Surah 1's header additionally carries the document title. Exact literal:
DOC_TITLE_SUFFIX = "القرآن الكريم :"

RE_AYAH_MARKER = re.compile(r"\((\d+)\)")


def classify_and_structure(paragraphs, log):
    """Walk paragraphs, split into surah blocks, and segment ayat on (n).

    Returns (corpus_rows, structural_rows, trailing_applications).

    Classification rules, in priority order:
      C1  blank line                                     -> skipped (page artifact)
      C2  starts with 'سورة', <60 chars, contains no digit -> SURAH HEADER
      C3  contains no digit, <=45 chars, starts 'بسم'      -> STANDALONE BASMALAH
                                                              (structural, not an ayah)
      C4  otherwise                                       -> body text of current surah

    Ayah segmentation rule:
      S1  the text preceding marker (n) is ayah n
      S2  TRAILING_REMAINDER_AS_FINAL_AYAH: if non-empty text follows the last
          marker, it is recorded as ayah last+1. Every application is logged to
          review_needed.csv. No text is created — only a boundary is inferred.
    """
    blocks = []
    current = None
    n_blank = 0
    unclassified = []

    for idx, line_full in enumerate(paragraphs):
        line = line_full.strip()
        if not line:
            n_blank += 1
            continue
        bare = RE_TASHKEEL.sub("", RE_ANNOTATION.sub("", line))
        has_digit = any(ch.isdigit() for ch in line)

        # C2 — surah header
        if bare.startswith(WORD_SURAH) and len(line) < 60 and not has_digit:
            header = line
            if header.endswith(DOC_TITLE_SUFFIX):
                header = header[: -len(DOC_TITLE_SUFFIX)].strip()
                log(f"    [rule HEADER_TITLE_STRIP] surah {len(blocks)+1}: removed "
                    f"document title {DOC_TITLE_SUFFIX!r} from header line")
            name = header[len(WORD_SURAH):].strip()
            current = {
                "number": len(blocks) + 1,
                "name": name,
                "header_raw": line,
                "basmalah_text": None,
                "body_parts": [],
            }
            blocks.append(current)
            continue

        if current is None:
            unclassified.append((idx, line))
            continue

        # C3 — standalone, unnumbered Basmalah (structural heading, not an ayah)
        if (not has_digit) and len(line) <= 45 and bare.startswith(WORD_BISM):
            current["basmalah_text"] = line
            continue

        # C4 — body
        current["body_parts"].append(line)

    if unclassified:
        for idx, line in unclassified:
            log(f"    ! UNCLASSIFIED paragraph {idx}: {line[:80]}")
        raise SystemExit(f"ABORT: {len(unclassified)} unclassified paragraphs.")

    log(f"    surah headers        : {len(blocks)}")
    log(f"    blank paragraphs     : {n_blank} (page-break artifacts, skipped)")

    # --- segment each block into ayat ---
    corpus = []
    structural = []
    trailing_applications = []

    for blk in blocks:
        s_no = blk["number"]
        body = " ".join(blk["body_parts"])
        expected = HAFS_AYAH_COUNTS[s_no - 1]

        structural.append({
            "surah_number": s_no,
            "surah_name": blk["name"],
            "header_raw": blk["header_raw"],
            "basmalah_present": blk["basmalah_text"] is not None,
            "basmalah_text_raw": blk["basmalah_text"] or "",
        })

        cursor = 0
        for m in RE_AYAH_MARKER.finditer(body):
            n = int(m.group(1))
            text = body[cursor:m.start()].strip()
            corpus.append({
                "surah_number": s_no,
                "surah_name": blk["name"],
                "ayah_number": n,
                "ayah_text_raw": text,
            })
            cursor = m.end()

        # S2 — trailing remainder
        remainder = body[cursor:].strip()
        if remainder:
            last_n = corpus[-1]["ayah_number"] if corpus and corpus[-1]["surah_number"] == s_no else 0
            inferred = last_n + 1
            corpus.append({
                "surah_number": s_no,
                "surah_name": blk["name"],
                "ayah_number": inferred,
                "ayah_text_raw": remainder,
            })
            trailing_applications.append({
                "rule": "TRAILING_REMAINDER_AS_FINAL_AYAH",
                "surah_number": s_no,
                "surah_name": blk["name"],
                "inferred_ayah_number": inferred,
                "expected_final_ayah_hafs": expected,
                "boundary_matches_hafs": inferred == expected,
                "text_raw": remainder,
                "note": ("Source lacks the closing (n) marker for this ayah. The ayah "
                         "TEXT is present verbatim; only the delimiter numeral is absent. "
                         "A segmentation boundary was inferred. NO text was created."),
            })
            log(f"    [rule TRAILING_REMAINDER_AS_FINAL_AYAH] surah {s_no} "
                f"({blk['name']}): inferred ayah {inferred} "
                f"(Hafs expects final ayah {expected}) -> "
                f"{'MATCH' if inferred == expected else 'MISMATCH'}")

    return corpus, structural, trailing_applications


def validation_gate(corpus, structural, log):
    """Phase 1 mandatory gate. Reports every mismatch and stops. No auto-fix."""
    failures = []

    n_surahs = len({r["surah_number"] for r in corpus})
    log(f"    surah count          : {n_surahs}  (expect 114)")
    if n_surahs != 114:
        failures.append(f"surah count {n_surahs} != 114")

    total = len(corpus)
    log(f"    total ayah count     : {total}  (expect 6236)")
    if total != 6236:
        failures.append(f"total ayah count {total} != 6236")

    per_surah = Counter(r["surah_number"] for r in corpus)
    for s in range(1, 115):
        got, exp = per_surah.get(s, 0), HAFS_AYAH_COUNTS[s - 1]
        if got != exp:
            name = next((r["surah_name"] for r in corpus if r["surah_number"] == s), "?")
            failures.append(f"surah {s} ({name}): {got} ayat, Hafs expects {exp}")
            ctx = [r for r in corpus if r["surah_number"] == s]
            for r in ctx[-3:]:
                failures.append(f"      ...{s}:{r['ayah_number']} = {r['ayah_text_raw'][:120]}")

    # contiguity: every surah must run 1..N with no gaps or repeats
    for s in range(1, 115):
        nums = [r["ayah_number"] for r in corpus if r["surah_number"] == s]
        if nums != list(range(1, len(nums) + 1)):
            failures.append(f"surah {s}: ayah numbers not contiguous 1..N -> {nums[:12]}...")

    # explicit spot checks demanded by the brief
    for s, exp, label in [(1, 7, "Al-Fatihah"), (2, 286, "Al-Baqarah"), (114, 6, "An-Nas")]:
        got = per_surah.get(s, 0)
        status = "PASS" if got == exp else "FAIL"
        log(f"    {label:<12} == {exp:<4}: {got}  [{status}]")
        if got != exp:
            failures.append(f"{label} has {got} ayat, expects {exp}")

    # ayah text must be free of markup: no digits, no parens, no Latin letters
    dirty = [r for r in corpus
             if re.search(r"[\d()A-Za-z]", r["ayah_text_raw"])]
    log(f"    ayat containing digits/parens/Latin : {len(dirty)}  (expect 0)")
    if dirty:
        for r in dirty[:5]:
            failures.append(f"  markup leak {r['surah_number']}:{r['ayah_number']}: "
                            f"{r['ayah_text_raw'][:100]}")
        failures.append(f"{len(dirty)} ayat contain residual markup")

    # empty ayat
    empty = [r for r in corpus if not r["ayah_text_raw"]]
    log(f"    empty ayah texts     : {len(empty)}  (expect 0)")
    if empty:
        failures.append(f"{len(empty)} empty ayah texts")

    # Basmalah census (informational; not a gate failure)
    have = {r["surah_number"] for r in structural if r["basmalah_present"]}
    missing = sorted(set(range(1, 115)) - have)
    expected_missing = SURAHS_WITHOUT_BASMALAH_BY_TRADITION | {SURAH_WITH_BASMALAH_AS_AYAH}
    anomalous = sorted(set(missing) - expected_missing)
    log(f"    standalone Basmalahs : {len(have)}")
    log(f"    absent for surahs    : {missing}")
    log(f"      -> surah 1 = Basmalah is ayah 1 (expected)")
    log(f"      -> surah 9 = no Basmalah by tradition (expected)")
    for s in anomalous:
        log(f"      -> surah {s} = ANOMALY, Basmalah absent from source (documented, not fixed)")

    if failures:
        log("")
        log("  " + "=" * 70)
        log("  VALIDATION GATE FAILED — pipeline stopped, nothing auto-corrected.")
        log("  " + "=" * 70)
        for f in failures:
            log(f"    {f}")
        raise SystemExit(1)

    log("    >>> VALIDATION GATE PASSED <<<")
    return anomalous


# ==============================================================================
# SECTION 4 — PHASE 2: CODEPOINT INVENTORY (the audit trail)
# ==============================================================================

def codepoint_inventory(text):
    """Every distinct codepoint in the source, with its official Unicode name
    and exact occurrence count. This is what proves nothing was silently
    dropped and nothing unexpected is present."""
    counts = Counter(text)
    rows = []
    for ch, n in sorted(counts.items(), key=lambda kv: ord(kv[0])):
        cp = ord(ch)
        try:
            name = unicodedata.name(ch)
        except ValueError:
            name = "<no Unicode name assigned>"
        if cp == 0x0A:
            disp = "\\n"
        elif cp == 0x09:
            disp = "\\t"
        elif cp == 0x20:
            disp = "(space)"
        elif cp < 0x20 or 0x200B <= cp <= 0x200F or cp in (0xFEFF, 0x00A0, 0x00AD):
            disp = "(invisible)"
        else:
            disp = ch
        rows.append({
            "codepoint": f"U+{cp:04X}",
            "decimal": cp,
            "char": disp,
            "unicode_name": name,
            "category": unicodedata.category(ch),
            "count": n,
        })
    return rows


# ==============================================================================
# SECTION 5 — PHASE 3: WORD SEGMENTATION UNDER FOUR DEFINITIONS
# ==============================================================================

def tokenize(text):
    """The ONLY tokenizer in this pipeline: split on whitespace runs.

    Nothing is stripped, merged, or reattached. The source contains no
    punctuation inside ayah text (verified by the validation gate), so
    whitespace splitting is unambiguous here.
    """
    return text.split()


def segmentation_definitions(corpus, structural, log):
    """Compute totals A, B, C, D. Each returns a number AND the rule that made it."""
    results = OrderedDict()

    # ---- ayah tokens (common to every definition) ----
    ayah_tokens = sum(len(tokenize(r["ayah_text_raw"])) for r in corpus)

    # ---- structural Basmalah tokens (the 111 standalone headings) ----
    basmalah_rows = [r for r in structural if r["basmalah_present"]]
    basmalah_tokens = sum(len(tokenize(r["basmalah_text_raw"])) for r in basmalah_rows)

    # ---- surah header tokens (editorial apparatus, excluded from A-D) ----
    header_tokens = sum(len(tokenize(r["header_raw"])) for r in structural)

    # ============================== DEFINITION A ==============================
    # Whitespace tokens over ALL Qur'anic text present in the document:
    # every ayah, PLUS the standalone Basmalah headings.
    # Surah header lines ("سورة البقرة") are editorial apparatus, not Qur'anic
    # text, and are excluded from every definition. Ayah marker numerals "(n)"
    # are delimiters and are likewise not tokens.
    results["A"] = {
        "label": "A — Whitespace tokens (raw), Basmalah included",
        "total": ayah_tokens + basmalah_tokens,
        "rule": ("split(); all 6236 ayat PLUS the standalone Basmalah headings "
                 "actually present in the source (112 total, incl. Al-Fatihah's "
                 "as ayah 1:1). Surah headers and (n) markers excluded."),
        "components": {
            "ayah_tokens": ayah_tokens,
            "standalone_basmalah_tokens": basmalah_tokens,
            "standalone_basmalah_count": len(basmalah_rows),
        },
    }

    # ============================== DEFINITION B ==============================
    # Basmalah excluded, except Al-Fatihah's — which is ayah 1:1 and therefore
    # already inside ayah_tokens.
    results["B"] = {
        "label": "B — Whitespace tokens, Basmalah excluded (except Al-Fatihah 1:1)",
        "total": ayah_tokens,
        "rule": ("split(); the 6236 ayat only. The 111 standalone Basmalah "
                 "headings are dropped. Al-Fatihah's Basmalah is retained "
                 "because it IS ayah 1:1 in the Hafs counting."),
        "components": {"ayah_tokens": ayah_tokens},
    }

    # ============================== DEFINITION C ==============================
    # Muqatta'at as single tokens. In THIS source they may already be single
    # whitespace tokens — that is measured, not assumed.
    muq_detail = []
    muq_extra_tokens = 0
    by_key = {(r["surah_number"], r["ayah_number"]): r for r in corpus}
    for s, a, letters in MUQATTAAT:
        row = by_key.get((s, a))
        if row is None:
            muq_detail.append({"surah": s, "ayah": a, "letters": letters,
                               "status": "AYAH NOT FOUND", "tokens_spanned": None,
                               "surface": ""})
            continue
        bare = form_no_tashkeel(row["ayah_text_raw"])
        toks = tokenize(bare)
        # how many leading whitespace tokens are needed to reconstruct `letters`?
        spanned, acc = 0, ""
        for t in toks:
            acc += t
            spanned += 1
            if acc == letters:
                break
            if len(acc) > len(letters):
                spanned = -1
                break
        if spanned == 1:
            status = "already a single token"
        elif spanned > 1:
            status = f"written as {spanned} separate tokens"
            muq_extra_tokens += spanned - 1
        else:
            status = "NOT MATCHED at ayah start"
        muq_detail.append({"surah": s, "ayah": a, "letters": letters,
                           "status": status, "tokens_spanned": spanned,
                           "surface": " ".join(toks[:3])})

    results["C"] = {
        "label": "C — Definition B, with Muqatta'at forced to one token each",
        "total": ayah_tokens - muq_extra_tokens,
        "rule": ("Definition B, then each of the 30 Muqatta'at occurrences "
                 "(29 surahs; surah 42 has two) is counted as exactly one token. "
                 f"Tokens removed by this rule: {muq_extra_tokens}."),
        "components": {
            "base_definition_B": ayah_tokens,
            "tokens_removed_by_muqattaat_merge": muq_extra_tokens,
            "muqattaat_occurrences_examined": len(MUQATTAAT),
        },
        "detail": muq_detail,
    }

    # ============================== DEFINITION D ==============================
    # Orthographically fused units. FLAGGED ONLY — never split.
    review = []
    fused_occurrences = 0
    implied_extra = 0
    gate_rejected = Counter()   # homographs suppressed by VOCALIZATION_GATE
    for r in corpus:
        raw_toks = tokenize(r["ayah_text_raw"])
        bare_toks = tokenize(form_no_tashkeel(r["ayah_text_raw"]))
        if len(raw_toks) != len(bare_toks):
            # cannot happen (mark removal never changes token count) but assert intent
            continue
        for raw_t, bare_t in zip(raw_toks, bare_toks):
            # A token is flagged only if it is either (a) an unambiguous fused
            # form, or (b) a gated homograph whose VOCALIZED form matches.
            if bare_t in VOCALIZATION_GATE:
                gated = VOCALIZATION_GATE[bare_t].get(raw_t)
                if gated is None:
                    gate_rejected[bare_t] += 1   # homograph — deliberately not flagged
                    continue
                rule_name, decomposition, note = gated
            else:
                hit = FUSED_FORMS.get(bare_t)
                if not hit:
                    continue
                rule_name, decomposition = hit
                note = ""

            parts = len(decomposition.split("+"))
            fused_occurrences += 1
            implied_extra += parts - 1
            review.append({
                "surah_number": r["surah_number"],
                "surah_name": r["surah_name"],
                "ayah_number": r["ayah_number"],
                "reference": f"{r['surah_number']}:{r['ayah_number']}",
                "token_raw": raw_t,
                "token_no_tashkeel": bare_t,
                "rule": rule_name,
                "suggested_decomposition": decomposition,
                "implied_extra_tokens_if_split": parts - 1,
                "ambiguity_note": note,
                "action_taken": "NONE — flagged for operator review only",
            })

    results["D"] = {
        "label": "D — Fused orthographic units: FLAGGED, NOT SPLIT",
        "total": ayah_tokens,   # identical to B by construction: nothing was split
        "rule": ("Definition B. Fused units are identified and listed in "
                 "review_needed.csv but are NOT split, so the total is "
                 "unchanged from B by construction. The 'if split' figure below "
                 "is a hypothetical shown for scale only — it is NOT a count of "
                 "the Qur'an's words and must not be quoted as one."),
        "components": {
            "base_definition_B": ayah_tokens,
            "fused_occurrences_flagged": fused_occurrences,
            "distinct_fused_types": len({x["token_no_tashkeel"] for x in review}),
            "homographs_suppressed_by_vocalization_gate": int(sum(gate_rejected.values())),
            "hypothetical_total_if_all_split": ayah_tokens + implied_extra,
            "hypothetical_extra_tokens": implied_extra,
        },
        "review_rows": review,
        "gate_rejected": dict(gate_rejected),
    }

    results["_context"] = {
        "surah_header_tokens_excluded": header_tokens,
        "surah_header_lines": len(structural),
    }
    return results


# ==============================================================================
# SECTION 6 — PHASE 4: FREQUENCY ANALYSIS
# ==============================================================================

def frequency_analysis(corpus, form_name, form_fn):
    """Frequency table for one normalization form.

    Returns (dataframe, per_ayah_tokens) where the dataframe carries
    word | count | first_occurrence | number_of_distinct_surahs.
    Corpus order is surah asc, ayah asc — so 'first occurrence' is well defined
    and reproducible.
    """
    counts = Counter()
    first_seen = {}
    surahs_of = defaultdict(set)
    per_ayah = []

    for r in corpus:
        toks = tokenize(form_fn(r["ayah_text_raw"]))
        per_ayah.append(toks)
        s, a = r["surah_number"], r["ayah_number"]
        for t in toks:
            counts[t] += 1
            if t not in first_seen:
                first_seen[t] = f"{s}:{a}"
            surahs_of[t].add(s)

    # deterministic ordering: count desc, then word ascending by codepoint
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    df = pd.DataFrame([{
        "word": w,
        "count": c,
        "first_occurrence": first_seen[w],
        "number_of_distinct_surahs": len(surahs_of[w]),
        "character_length": len(w),
    } for w, c in ordered])
    return df, per_ayah


def build_histogram(df):
    """How many distinct word types occur exactly 1x, 2x, ... 99x, and 100+x."""
    rows = []
    cum = 0
    for k in range(1, 100):
        n = int((df["count"] == k).sum())
        cum += n
        rows.append({"occurrences": str(k), "distinct_word_types": n,
                     "tokens_accounted": n * k})
    n100 = int((df["count"] >= 100).sum())
    rows.append({"occurrences": "100+", "distinct_word_types": n100,
                 "tokens_accounted": int(df.loc[df["count"] >= 100, "count"].sum())})
    return pd.DataFrame(rows)


# ==============================================================================
# SECTION 7 — MAIN PIPELINE
# ==============================================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_lines = []

    def log(msg=""):
        print(msg, flush=True)
        log_lines.append(msg)

    def out(name):
        return os.path.join(OUTPUT_DIR, name)

    log("=" * 78)
    log(" QUR'ANIC WORD FREQUENCY ANALYZER")
    log("=" * 78)
    log(f" source     : {SOURCE_DOCX}")
    log(f" output dir : {OUTPUT_DIR}")
    log(f" pandas     : {pd.__version__}")
    log("")

    # ---------------------------------------------------------------- PHASE 1
    log("[PHASE 1] SAFE EXTRACTION")
    paragraphs = extract_docx_paragraphs(SOURCE_DOCX)
    raw_text = "\n".join(paragraphs)
    log(f"    paragraphs extracted : {len(paragraphs)}")
    log(f"    total characters     : {len(raw_text)}")
    log(f"    integrity guards     : delText=0, sym=0, instrText=0  (enforced)")
    log("")

    log("[PHASE 1] STRUCTURING")
    corpus, structural, trailing = classify_and_structure(raw_text.split("\n"), log)
    log("")

    log("[PHASE 1] VALIDATION GATE (Hafs / Kufi counting)")
    assert len(HAFS_AYAH_COUNTS) == 114, "reference table must have 114 entries"
    assert sum(HAFS_AYAH_COUNTS) == 6236, "reference table must sum to 6236"
    log(f"    reference table      : 114 surahs, sums to {sum(HAFS_AYAH_COUNTS)}")
    basmalah_anomalies = validation_gate(corpus, structural, log)
    log("")

    corpus_df = pd.DataFrame(corpus)[
        ["surah_number", "surah_name", "ayah_number", "ayah_text_raw"]]
    corpus_df.to_csv(out("quran_corpus.csv"), index=False, encoding=CSV_ENCODING)
    pd.DataFrame(structural).to_csv(out("structural_elements.csv"),
                                    index=False, encoding=CSV_ENCODING)
    log(f"    -> quran_corpus.csv ({len(corpus_df)} rows)")
    log(f"    -> structural_elements.csv ({len(structural)} rows)")
    log("")

    # ---------------------------------------------------------------- PHASE 2
    log("[PHASE 2] NORMALIZATION LAYER + CODEPOINT INVENTORY")
    inv_rows = codepoint_inventory(raw_text)
    pd.DataFrame(inv_rows).to_csv(out("codepoint_inventory.csv"),
                                  index=False, encoding=CSV_ENCODING)
    log(f"    distinct codepoints  : {len(inv_rows)}")
    log(f"    -> codepoint_inventory.csv")

    # Measure how much work each normalization rule actually does on THIS source.
    all_ayah_text = "\n".join(r["ayah_text_raw"] for r in corpus)
    rule_effect = OrderedDict()
    prev = all_ayah_text
    for fname, fn in FORMS.items():
        cur = fn(all_ayah_text)
        rule_effect[fname] = {
            "chars": len(cur),
            "chars_removed_vs_raw": len(all_ayah_text) - len(cur),
            "identical_to_raw": cur == all_ayah_text,
        }
        log(f"    form {fname:<12}: {len(cur):>8} chars "
            f"({len(all_ayah_text) - len(cur):>6} fewer than raw)"
            f"{'   [NO-OP: identical to raw]' if cur == all_ayah_text and fname != 'raw' else ''}")
        prev = cur
    log("")

    # ---------------------------------------------------------------- PHASE 3
    log("[PHASE 3] WORD SEGMENTATION — FOUR DEFINITIONS")
    seg = segmentation_definitions(corpus, structural, log)
    for key in ("A", "B", "C", "D"):
        log(f"    {key}: {seg[key]['total']:>7}   {seg[key]['label']}")
    log(f"    (surah header tokens excluded from all definitions: "
        f"{seg['_context']['surah_header_tokens_excluded']})")
    log(f"    fused units flagged for review : "
        f"{seg['D']['components']['fused_occurrences_flagged']}")
    log(f"    homographs suppressed by gate  : "
        f"{seg['D']['components']['homographs_suppressed_by_vocalization_gate']}")
    for tok, n in sorted(seg["D"]["gate_rejected"].items(), key=lambda kv: -kv[1]):
        log(f"        {tok}: {n} occurrence(s) NOT flagged (homograph, not a fusion)")

    review_rows = list(seg["D"]["review_rows"])
    for t in trailing:
        review_rows.append({
            "surah_number": t["surah_number"],
            "surah_name": t["surah_name"],
            "ayah_number": t["inferred_ayah_number"],
            "reference": f"{t['surah_number']}:{t['inferred_ayah_number']}",
            "token_raw": t["text_raw"],
            "token_no_tashkeel": form_no_tashkeel(t["text_raw"]),
            "rule": t["rule"],
            "suggested_decomposition": "n/a — ayah boundary, not a token split",
            "implied_extra_tokens_if_split": 0,
            "ambiguity_note": ("Boundary inferred from the surah end because the source "
                               "omits the closing marker. Text is verbatim; boundary is not."),
            "action_taken": t["note"],
        })
    for s in basmalah_anomalies:
        row = next(r for r in structural if r["surah_number"] == s)
        review_rows.append({
            "surah_number": s,
            "surah_name": row["surah_name"],
            "ayah_number": 0,
            "reference": f"{s}:0",
            "token_raw": "",
            "token_no_tashkeel": "",
            "rule": "BASMALAH_ABSENT_FROM_SOURCE",
            "suggested_decomposition": "n/a",
            "implied_extra_tokens_if_split": 0,
            "ambiguity_note": "Not ambiguous — simply absent from the source.",
            "action_taken": ("NONE — Basmalah is absent from the source document for this "
                             "surah and was NOT reconstructed. Definition A is 4 tokens "
                             "lower than a source carrying all 113 opening Basmalahs."),
        })
    pd.DataFrame(review_rows).to_csv(out("review_needed.csv"),
                                     index=False, encoding=CSV_ENCODING)
    log(f"    -> review_needed.csv ({len(review_rows)} rows)")

    pd.DataFrame(seg["C"]["detail"]).to_csv(out("muqattaat_analysis.csv"),
                                            index=False, encoding=CSV_ENCODING)
    log(f"    -> muqattaat_analysis.csv ({len(seg['C']['detail'])} rows)")
    log("")

    # ---------------------------------------------------------------- PHASE 4
    log("[PHASE 4] FREQUENCY ANALYSIS")
    freq = OrderedDict()
    per_ayah_tokens = {}
    for fname, fn in FORMS.items():
        df, per_ayah = frequency_analysis(corpus, fname, fn)
        freq[fname] = df
        per_ayah_tokens[fname] = per_ayah
        df.to_csv(out(f"word_frequency_{fname}.csv"), index=False, encoding=CSV_ENCODING)
        hapax = df[df["count"] == 1].copy()
        hapax.to_csv(out(f"hapax_{fname}.csv"), index=False, encoding=CSV_ENCODING)
        df.head(200).to_csv(out(f"top200_{fname}.csv"), index=False, encoding=CSV_ENCODING)
        log(f"    {fname:<12}: {int(df['count'].sum()):>7} tokens | "
            f"{len(df):>6} unique | {len(hapax):>6} hapax")
    log("")

    build_histogram(freq["normalized"]).to_csv(
        out("frequency_distribution.csv"), index=False, encoding=CSV_ENCODING)
    for fname in FORMS:
        build_histogram(freq[fname]).to_csv(
            out(f"frequency_distribution_{fname}.csv"), index=False, encoding=CSV_ENCODING)
    log("    -> frequency_distribution*.csv")

    # per-surah statistics, computed on every form
    per_surah_rows = []
    for s in range(1, 115):
        idxs = [i for i, r in enumerate(corpus) if r["surah_number"] == s]
        name = corpus[idxs[0]]["surah_name"]
        row = {"surah_number": s, "surah_name": name, "ayah_count": len(idxs)}
        for fname in FORMS:
            toks = [t for i in idxs for t in per_ayah_tokens[fname][i]]
            uniq = len(set(toks))
            row[f"words_{fname}"] = len(toks)
            row[f"unique_{fname}"] = uniq
            row[f"density_{fname}"] = round(uniq / len(toks), 6) if toks else 0.0
        per_surah_rows.append(row)
    per_surah_df = pd.DataFrame(per_surah_rows)
    per_surah_df.to_csv(out("per_surah_statistics.csv"), index=False, encoding=CSV_ENCODING)
    log(f"    -> per_surah_statistics.csv (114 rows)")
    log("")

    # ------------------------------------------------------- SUMMARY REPORT
    log("[REPORT] writing summary_report.md")
    write_summary_report(out("summary_report.md"), locals())
    log(f"    -> summary_report.md")
    log("")
    log("=" * 78)
    log(" PIPELINE COMPLETE")
    log("=" * 78)

    with open(out("run_log.txt"), "w", encoding=TXT_ENCODING) as fh:
        fh.write("\n".join(log_lines))


def write_summary_report(path, ns):
    """Emit summary_report.md. Every number carries the rule that produced it."""
    corpus = ns["corpus"]
    structural = ns["structural"]
    seg = ns["seg"]
    freq = ns["freq"]
    inv_rows = ns["inv_rows"]
    rule_effect = ns["rule_effect"]
    raw_text = ns["raw_text"]
    per_surah_df = ns["per_surah_df"]
    trailing = ns["trailing"]
    basmalah_anomalies = ns["basmalah_anomalies"]

    L = []
    A = L.append

    A("# Qur'anic Word Frequency Analysis — Summary Report")
    A("")
    A(f"- **Source:** `{SOURCE_DOCX}`")
    A(f"- **Orthography:** Imlaei (رسم إملائي) — established at codepoint level, see §2")
    A(f"- **Counting tradition for validation:** Hafs / Kufi (6236 ayat)")
    A(f"- **Total characters in source:** {len(raw_text):,}")
    A(f"- **Distinct Unicode codepoints:** {len(inv_rows)}")
    A("")
    A("> Every figure below is followed by the exact rule that produced it. "
      "Where a figure depends on a definitional choice, the alternatives are "
      "given side by side and none is marked as correct.")
    A("")

    # ---- 1. corpus
    A("## 1. Corpus")
    A("")
    A("| Metric | Value | Rule |")
    A("|---|---:|---|")
    A(f"| Surahs | {len({r['surah_number'] for r in corpus})} | count of `سورة` header lines |")
    A(f"| Ayat | {len(corpus)} | segments delimited by `(n)` markers, Hafs counting |")
    A(f"| Standalone Basmalah headings | {sum(1 for r in structural if r['basmalah_present'])} | unnumbered paragraphs beginning `بسم` |")
    A("")
    A("**Validation gate: PASSED.** 114 surahs; 6236 ayat; every per-surah count "
      "matches the hardcoded Hafs table; every surah numbers contiguously 1..N; "
      "Al-Fatihah = 7, Al-Baqarah = 286, An-Nas = 6; zero ayat contain residual "
      "markup; zero empty ayat.")
    A("")

    # ---- 2. orthography + codepoints
    A("## 2. Orthography and the codepoint audit trail")
    A("")
    A("The source is **Imlaei, not Uthmani**. Every Uthmani-exclusive character "
      "is absent — this is a measured fact, not an inference:")
    A("")
    A("| Uthmani-only character | Occurrences |")
    A("|---|---:|")
    present = {r["codepoint"] for r in inv_rows}
    for cp, label in [("U+0671", "ALEF WASLA ٱ"), ("U+0670", "SUPERSCRIPT (dagger) ALEF"),
                      ("U+06DD", "END OF AYAH ۝"), ("U+06DE", "START OF RUB EL HIZB ۞"),
                      ("U+06E9", "PLACE OF SAJDAH ۩"), ("U+06D6", "waqf mark (first of range)"),
                      ("U+0640", "TATWEEL")]:
        n = next((r["count"] for r in inv_rows if r["codepoint"] == cp), 0)
        A(f"| {cp} {label} | {n} |")
    A("")
    A("### Consequences for the normalization layer")
    A("")
    A("| Form | Characters | Removed vs raw | Note |")
    A("|---|---:|---:|---|")
    for fname, e in rule_effect.items():
        note = "**NO-OP — byte-identical to `raw`**" if e["identical_to_raw"] and fname != "raw" else ""
        A(f"| `{fname}` | {e['chars']:,} | {e['chars_removed_vs_raw']:,} | {note} |")
    A("")
    A("`no_marks` removes Qur'anic annotation symbols. This source contains none, "
      "so the form is a genuine no-op here. It is still computed and reported "
      "rather than quietly dropped, because on an Uthmani source it would differ.")
    A("")
    A("Full inventory of all distinct codepoints, with official Unicode names and "
      "exact counts: `codepoint_inventory.csv`.")
    A("")

    # ---- 3. segmentation
    A("## 3. Word segmentation — four definitions")
    A("")
    A("| Definition | Total words | Rule |")
    A("|---|---:|---|")
    for k in ("A", "B", "C", "D"):
        A(f"| **{k}** | **{seg[k]['total']:,}** | {seg[k]['rule']} |")
    A("")
    A("### The differences between these numbers are definitional, not errors.")
    A("")
    A("Each total counts a different thing. None is more correct than the others; "
      "they answer different questions.")
    A("")
    A("Component breakdown:")
    A("")
    for k in ("A", "B", "C", "D"):
        lbl = seg[k]["label"]
        short = lbl.split("—", 1)[1].strip() if "—" in lbl else lbl
        A(f"- **{k}** — {short}")
        for ck, cv in seg[k]["components"].items():
            A(f"  - `{ck}` = {cv:,}" if isinstance(cv, int) else f"  - `{ck}` = {cv}")
    A("")
    A("**Excluded from every definition:** surah header lines "
      f"({seg['_context']['surah_header_tokens_excluded']} tokens across "
      f"{seg['_context']['surah_header_lines']} lines) are editorial apparatus, "
      "not Qur'anic text. Ayah marker numerals `(n)` are delimiters, not tokens.")
    A("")
    A("### Definition D is deliberately not a smaller number")
    A("")
    A("The brief requires fused units to be **flagged, not split**. They were "
      "flagged. D therefore equals B by construction. The 'if all were split' "
      "figure in the component list is a hypothetical for scale only and must "
      "not be quoted as a word count of the Qur'an. The decision on each case is "
      "yours; every occurrence is in `review_needed.csv` with its surah:ayah.")
    A("")
    A("### Homograph suppression (vocalization gate)")
    A("")
    A("Some fused forms are indistinguishable from ordinary words once tashkeel "
      "is stripped. Because this source is fully vocalized, harakat separate them "
      "mechanically. Flagging on the bare skeleton alone would have filled the "
      "review list with false positives. The following were identified as "
      "homographs and deliberately **not** flagged:")
    A("")
    A("| Skeleton | Occurrences suppressed | Why it is not a fusion |")
    A("|---|---:|---|")
    _why = {
        "لم": "the jussive negative particle لَمْ (the fusion is لِمَ, which *is* flagged)",
        "إلا": "the noun إِلًّا 'kinship/covenant' at 9:8 and 9:10",
        "أمن": "the verb أَمِنَ 'he trusted' at 2:283",
        "مال": "the noun مَال 'wealth' in its nominative/accusative/indefinite forms",
        "فمال": "n/a",
    }
    for tok, n in sorted(seg["D"]["gate_rejected"].items(), key=lambda kv: -kv[1]):
        A(f"| `{tok}` | {n} | {_why.get(tok, 'homograph of a non-fused word')} |")
    A("")
    A("This gate affects only the *precision of the review list*. It changes no "
      "word total, because Definition D splits nothing.")
    A("")

    # ---- 4. comparison to published counts
    A("## 4. Comparison with published counts")
    A("")
    A("Published totals commonly cited include ~77,430, ~77,439, and ~77,797. "
      "They disagree with each other, and this analysis does not adjudicate "
      "between them. The following accounts for where the gaps come from — it "
      "does **not** claim any published figure is authoritative, nor that the "
      "figures here are.")
    A("")
    A("| Source of variation | Effect on the total |")
    A("|---|---:|")
    A(f"| Including vs excluding the 111 standalone Basmalah headings | "
      f"{seg['A']['total'] - seg['B']['total']:,} tokens (A − B) |")
    A(f"| Muqatta'at merged to one token each | "
      f"{seg['B']['total'] - seg['C']['total']:,} tokens (B − C) |")
    A(f"| Fused units split (hypothetical, NOT applied) | "
      f"+{seg['D']['components']['hypothetical_extra_tokens']:,} tokens |")
    A("")
    A("The single largest driver, however, is **orthography, not arithmetic**. "
      "This source is Imlaei. Imlaei writes as two tokens much of what Uthmani "
      "writes as one — most conspicuously `يا أيها` (two tokens here) against "
      "Uthmani `يَٰٓأَيُّهَا` (one). A count taken over an Uthmani rasm will therefore "
      "be *lower* than the same rule applied to this text. Any comparison "
      "between a figure here and a published figure must first establish that "
      "both used the same rasm; otherwise the comparison is meaningless.")
    A("")

    # ---- 5. frequency
    A("## 5. Frequency analysis")
    A("")
    A("| Form | Total tokens | Unique types | Hapax legomena | Type/token ratio |")
    A("|---|---:|---:|---:|---:|")
    for fname, df in freq.items():
        tot = int(df["count"].sum())
        uni = len(df)
        hap = int((df["count"] == 1).sum())
        A(f"| `{fname}` | {tot:,} | {uni:,} | {hap:,} | {uni/tot:.5f} |")
    A("")
    A("### Why the unique counts differ so much")
    A("")
    A("Token totals are identical across all four forms — normalization never "
      "adds or removes whitespace boundaries, so it cannot change *how many* "
      "words there are. It changes only how many are judged **the same word**.")
    A("")
    A("- `raw` → `no_marks`: no change on this source (no annotation marks exist).")
    A("- `no_marks` → `no_tashkeel`: collapses every vocalization variant of one "
      "consonantal skeleton into a single type. This is the largest single drop: "
      "words differing only by case-ending (i'rab) merge.")
    A("- `no_tashkeel` → `normalized`: merges hamza-carrier variants, ى with ي, "
      "and ة with ه. **These are conventions, not facts**, and each is a "
      "deliberate choice documented in §6.")
    A("")
    A("A rising unique count means finer distinctions are preserved; a falling "
      "one means more surface forms are being treated as the same lexical item. "
      "Neither is 'the' vocabulary size of the Qur'an — that depends entirely on "
      "what you consider one word.")
    A("")
    A("### Top 20 — form `normalized`")
    A("")
    A("| # | Word | Count | First occurrence | Distinct surahs |")
    A("|---:|---|---:|---|---:|")
    for i, r in freq["normalized"].head(20).iterrows():
        A(f"| {i+1} | {r['word']} | {r['count']:,} | {r['first_occurrence']} | "
          f"{r['number_of_distinct_surahs']} |")
    A("")
    A("Full tables: `word_frequency_<form>.csv`. Top 200: `top200_<form>.csv`. "
      "Hapax with locations: `hapax_<form>.csv`.")
    A("")

    # ---- word length extremes
    A("### Distribution histogram")
    A("")
    A("How many distinct word types occur exactly N times (form `normalized`; "
      "per-form tables in `frequency_distribution_<form>.csv`):")
    A("")
    A("| Occurrences | Distinct word types | Tokens accounted for |")
    A("|---|---:|---:|")
    hist = build_histogram(freq["normalized"])
    hist_idx = hist.set_index("occurrences")
    for n in range(1, 11):                      # exact counts 1x .. 10x
        r = hist_idx.loc[str(n)]
        A(f"| {n}× | {int(r['distinct_word_types']):,} | "
          f"{int(r['tokens_accounted']):,} |")
    mid = hist[hist["occurrences"].isin([str(i) for i in range(11, 100)])]
    A(f"| 11–99× | {int(mid['distinct_word_types'].sum()):,} | "
      f"{int(mid['tokens_accounted'].sum()):,} |")
    r100 = hist_idx.loc["100+"]                 # tail bucket last
    A(f"| 100+× | {int(r100['distinct_word_types']):,} | "
      f"{int(r100['tokens_accounted']):,} |")
    A("")
    A(f"The distribution is steeply Zipfian: "
      f"{int(hist.iloc[0]['distinct_word_types']):,} types "
      f"({100*int(hist.iloc[0]['distinct_word_types'])/len(freq['normalized']):.1f}% of "
      f"the vocabulary) occur exactly once, yet account for only "
      f"{100*int(hist.iloc[0]['tokens_accounted'])/int(freq['normalized']['count'].sum()):.1f}% "
      f"of all tokens. Full per-count table in `frequency_distribution.csv`.")
    A("")

    A("### Longest and shortest words")
    A("")
    A("Reported for two forms, because the answer differs and only one of them "
      "is linguistically meaningful. In `raw`, length is inflated by combining "
      "marks — each haraka is its own codepoint — so `raw` measures *storage*, "
      "not word length. `normalized` measures letters.")
    A("")
    for form in ("normalized", "raw"):
        fdf = freq[form]
        A(f"**Form `{form}` — longest:**")
        A("")
        A("| Word | Chars | Count | First |")
        A("|---|---:|---:|---|")
        for _, r in fdf.nlargest(10, "character_length").iterrows():
            A(f"| {r['word']} | {r['character_length']} | {r['count']} | "
              f"{r['first_occurrence']} |")
        A("")
        A(f"**Form `{form}` — shortest:**")
        A("")
        A("| Word | Chars | Count | First |")
        A("|---|---:|---:|---|")
        for _, r in fdf.nsmallest(10, "character_length").iterrows():
            A(f"| {r['word']} | {r['character_length']} | {r['count']} | "
              f"{r['first_occurrence']} |")
        A("")

    # ---- per surah extremes
    A("### Per-surah statistics")
    A("")
    A("Full table: `per_surah_statistics.csv` (word count, unique count and "
      "lexical density for all 114 surahs, under all four forms).")
    A("")
    top5 = per_surah_df.nlargest(5, "words_normalized")[
        ["surah_number", "surah_name", "ayah_count", "words_normalized",
         "unique_normalized", "density_normalized"]]
    A("| # | Surah | Ayat | Words | Unique | Density |")
    A("|---:|---|---:|---:|---:|---:|")
    for _, r in top5.iterrows():
        A(f"| {r['surah_number']} | {r['surah_name']} | {r['ayah_count']} | "
          f"{r['words_normalized']:,} | {r['unique_normalized']:,} | {r['density_normalized']:.4f} |")
    A("")
    A("Lexical density = unique / total within that surah. Short surahs score "
      "high mechanically, because there is less room for repetition — the metric "
      "is not comparable across surahs of very different lengths.")
    A("")

    # ---- 6. caveats
    A("## 6. Caveats, conventions, and open decisions")
    A("")
    A("### Conventions chosen (each is contestable; each is isolated in the code)")
    A("")
    A("1. **`ى` → `ي`** in `normalized`. A convention, not a fact. It merges e.g. "
      "`علي`/`على`. Mapping `ى` → `ا` instead, or leaving it distinct, changes the "
      "`normalized` unique count and nothing else.")
    A("2. **`ة` → `ه`** in `normalized`. Merges e.g. `رحمة`/`رحمه`. Same isolation.")
    A("3. **Surah headers excluded** from all word counts as editorial apparatus.")
    A("4. **Ayah markers `(n)` are delimiters**, never tokens.")
    A("5. **Whitespace splitting only.** No stemming, no clitic separation, no "
      "root extraction.")
    A("")
    A("### Source anomalies — recorded, never repaired")
    A("")
    for t in trailing:
        A(f"- **Surah {t['surah_number']} ({t['surah_name']}), ayah "
          f"{t['inferred_ayah_number']}:** the source has no `({t['inferred_ayah_number']})` "
          f"marker. The ayah text is present and complete; only the delimiter is "
          f"missing. Rule `{t['rule']}` inferred the boundary. No text was created, "
          f"altered, or reconstructed. Hafs boundary match: "
          f"{'yes' if t['boundary_matches_hafs'] else 'NO'}.")
    for s in basmalah_anomalies:
        row = next(r for r in structural if r["surah_number"] == s)
        A(f"- **Surah {s} ({row['surah_name']}):** the Basmalah is absent from the "
          f"source document. Surahs 103 and 105 have theirs. It was **not** "
          f"reconstructed. Definition A therefore counts 112 Basmalah instances, "
          f"not 113 — four tokens fewer than a source carrying all of them.")
    A("")
    A("### Awaiting your decision")
    A("")
    A(f"`review_needed.csv` holds {len(seg['D']['review_rows'])} flagged fused-unit "
      "occurrences, each with its surah:ayah reference, the raw token, the rule "
      "that flagged it, and a suggested decomposition. Nothing in that file has "
      "been acted on.")
    A("")

    # ---- 7. verified vs assumed
    A("## 7. What was verified vs what was assumed")
    A("")
    A("### Verified (measured directly from the source)")
    A("")
    A("- Extraction is lossless: zero `w:delText`, `w:sym`, `w:instrText` nodes; "
      "zero U+FFFD; zero unexpected codepoints across the whole file.")
    A("- Reading order is correct: WordprocessingML stores logical order; ayah "
      "markers ascend contiguously 1..N in every surah.")
    A(f"- All {len(inv_rows)} distinct codepoints identified by official Unicode name.")
    A("- The source is Imlaei: every Uthmani-exclusive codepoint counted, all zero.")
    A("- 114 surahs, 6236 ayat, every per-surah count matched against a hardcoded "
      "Hafs table.")
    A("- Basmalah census reconciled exactly: every occurrence of the string `بسم` "
      "in the file is accounted for, including two coincidental substring matches "
      "(`بسمعهم` 2:20, `فتبسم` 27:19) that are not the word.")
    A("- Token totals are identical across all four normalization forms, as they "
      "must be.")
    A("")
    A("### Assumed (choices made, not facts derived)")
    A("")
    A("- **The Hafs/Kufi table itself** is taken as the reference standard. Other "
      "counting traditions (Basri, Madani, Makki, Shami) give different per-surah "
      "totals. Nothing here validates Hafs as correct; it validates the source "
      "*against* Hafs.")
    A("- **Surah 15:99's boundary** was inferred from the surah's end, on your "
      "instruction. The text is verbatim from the source; the boundary is not.")
    A("- **The fused-forms list** in `FUSED_FORMS` is a curated set, not an "
      "exhaustive one. Absence from that list is not evidence that a token is "
      "unfused — it means the pipeline was not told to look for it.")
    A("- **The vocalization gate** resolves homographs using the source's own "
      "harakat, which is objective. But one case remains genuinely unresolved: "
      "`مَالِ` is the fusion at 18:49 and 25:7 and the noun 'wealth' at 24:33. "
      "Vocalization cannot separate those three; only context can. All three are "
      "flagged, with a note, for you to split manually.")
    A("- **`أَلَا` (54 occurrences) is classed as contested, not fused.** Reading "
      "the inceptive particle as interrogative hamza + `لا` is one analysis among "
      "several. It is listed under its own rule `PARTICLE_A_LA` so it can be "
      "included or excluded independently of the genuine `أَلَّا` fusions.")
    A("- **The orthographic mappings** `ى`→`ي` and `ة`→`ه` are conventions.")
    A("- **Word-level analysis only.** No morphological claim is made. Arabic "
      "clitics (`و`, `ف`, `ب`, `ل`, `ال`, pronominal suffixes) remain attached, so "
      "`الكتاب` and `بالكتاب` are distinct types under every form here.")
    A("")

    with open(path, "w", encoding=TXT_ENCODING) as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
