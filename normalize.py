"""Normalization: raw extracted listings -> canonical, comparable records.

  department    top-level taxonomy (vocab.DEPARTMENTS) from breadcrumbs/category/title/URL keywords,
                with an embedding-similarity fallback for anything the keywords miss
  brand/model   legal suffixes and aliases removed; brand inferred from title/URL using brands seen
                elsewhere in the catalog; GTIN checksum-validated; SKU-like "models" dropped
  specs         canonical keys and values: colors, materials, genders, sizes, conditions in English;
                quantities converted to one unit per dimension (mm, g, ml, GB, W, ...), with num/unit kept
  price         parsed in any locale format; "kr" resolved from the shop's TLD; converted to EUR (ECB rates)
"""
import json
import re
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

from vocab import (BRAND_ALIASES, COLOR_EXACT_ONLY, COLORS, DEFAULT_SPEC_WEIGHT, DEPARTMENTS, GENDERS,
                   LEGAL_SUFFIXES, MATERIAL_EXACT_ONLY, MATERIALS, NULL_BRANDS, SPEC_WEIGHTS)

ROOT = Path(__file__).resolve().parent
FX_CACHE = ROOT / "cache" / "fx.json"
# Approximate fallback (EUR = 1) used only if the ECB feed is unreachable.
FX_FALLBACK = {"EUR": 1.0, "DKK": 7.46, "SEK": 11.2, "NOK": 11.6, "PLN": 4.27, "USD": 1.14, "GBP": 0.86,
               "CHF": 0.94, "CZK": 24.6, "HUF": 395.0, "ISK": 143.0, "JPY": 165.0, "CAD": 1.58, "AUD": 1.75}
TECH_DEPARTMENTS = {"phones & tablets", "computers", "cameras & photo", "electronics", "kitchen & dining",
                    "tools & garden", "automotive"}
GENDERED_DEPARTMENTS = {"clothing", "footwear", "bags & accessories", "jewelry & watches",
                        "beauty & personal care", "sports & outdoor"}


# ---------- text helpers ----------

def fold(s):
    """Lowercase, NFKC, collapse whitespace."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s)).lower()).strip()


def tokens(s):
    return re.findall(r"[^\W_]+(?:[-'][^\W_]+)*", fold(s))


def slug(s):
    s = unicodedata.normalize("NFKD", fold(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


class Lexicon:
    """Fast multilingual keyword matcher: whole words, light inflection (jakke->jakker),
    and compounds (vinterjakke -> jakke) for keywords of >= 4 chars."""

    def __init__(self, mapping, exact_only=()):
        self.plain, self.exact, self.compound, self.phrases = {}, {}, {}, []
        for target, words in mapping.items():
            for w in words:
                w = fold(w)
                exact = w.startswith("=") or w in exact_only
                w = w.lstrip("=")
                if " " in w:
                    self.phrases.append((w, target))
                elif exact:
                    self.exact.setdefault(w, target)
                else:
                    self.plain.setdefault(w, target)
                    if len(w) >= 4:
                        self.compound.setdefault(w, target)

    def match_token(self, tok):
        if tok in self.plain:
            return self.plain[tok]
        if tok in self.exact:
            return self.exact[tok]
        for j in (1, 2, 3):  # inflections: plural/definite forms ("jakker", "bukserne")
            base, ending = tok[:-j], tok[-j:]
            if len(base) >= 4 and base in self.plain:
                return self.plain[base]
            if len(base) == 3 and ending == "s" and base in self.plain:
                return self.plain[base]  # "bags", "cars"; whole-word-only keywords never inflect
        for i in range(2, len(tok) - 3):  # compound: known word at the end
            if tok[i:] in self.compound:
                return self.compound[tok[i:]]
        return None

    def matches(self, text):
        """List of targets matched in text (one per matching token/phrase)."""
        text = fold(text)
        toks = tokens(text)
        toks += [part for t in toks if "-" in t for part in t.split("-")]  # "støddæmper-pude"
        found = [t for t in (self.match_token(tok) for tok in toks) if t]
        found += [t for p, t in self.phrases if re.search(rf"(?<!\w){re.escape(p)}(?!\w)", text)]
        return found


DEPT_LEX = Lexicon({d: v["kw"] for d, v in DEPARTMENTS.items()})
COLOR_LEX = Lexicon(COLORS, COLOR_EXACT_ONLY)
MATERIAL_LEX = Lexicon(MATERIALS, MATERIAL_EXACT_ONLY)
GENDER_LEX = Lexicon({g: [w for w in ws if len(w) > 2] for g, ws in GENDERS.items()},
                     exact_only={w for ws in GENDERS.values() for w in ws})


# ---------- prices & currencies ----------

def parse_price(v):
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    s = re.sub(r"[^\d.,]", "", str(v or "")).strip(".,")
    if not s or not re.search(r"\d", s):
        return None
    if "," in s and "." in s:  # the later separator is the decimal one
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:  # "574,57" decimal vs "1,299" thousands
        s = s.replace(",", "") if len(s.rsplit(",", 1)[1]) == 3 else s.replace(",", ".")
    elif s.count(".") > 1 or len(s.rsplit(".", 1)[-1]) == 3 and "." in s:  # "12.490" = 12490
        s = s.replace(".", "")
    try:
        p = float(s)
        return p if p > 0 else None
    except ValueError:
        return None


def norm_currency(cur, source):
    c = fold(cur or "").replace(".", "").strip()
    tld = (source or "").rsplit(".", 1)[-1]
    if not c:
        return None
    if c in ("kr", "kr,-", ":-"):
        return {"dk": "DKK", "se": "SEK", "no": "NOK"}.get(tld, "DKK")
    symbols = {"€": "EUR", "$": "USD", "£": "GBP", "zł": "PLN", "zl": "PLN"}
    if c in symbols:
        return symbols[c]
    return c.upper()[:3] if re.fullmatch(r"[a-z]{3}", c) else None


def load_fx():
    """EUR reference rates from the ECB (cached per day), falling back to FX_FALLBACK."""
    today = date.today().isoformat()
    try:
        cached = json.loads(FX_CACHE.read_text())
        if cached.get("date") == today:
            return cached["rates"]
    except (OSError, ValueError):
        pass
    try:
        xml = urllib.request.urlopen("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
                                     timeout=10).read().decode()
        rates = {"EUR": 1.0, **{c: float(r) for c, r in re.findall(r"currency='(\w+)' rate='([\d.]+)'", xml)}}
        FX_CACHE.parent.mkdir(exist_ok=True)
        FX_CACHE.write_text(json.dumps({"date": today, "rates": rates}))
        return rates
    except Exception:
        print("! ECB rates unavailable - using approximate fallback rates")
        return FX_FALLBACK


# ---------- brand / model / gtin ----------

_LEGAL = re.compile(r"[,.]?\s+(" + "|".join(re.escape(s) for s in LEGAL_SUFFIXES) + r")\.?$")


def norm_brand(s):
    if not s or not isinstance(s, str):
        return None
    s = fold(s)
    prev = None
    while prev != s:  # legal suffixes first ("Tvilum A/S"), then alternatives ("Olympus / OM System")
        prev, s = s, _LEGAL.sub("", s).strip(" ,.-")
    s = re.split(r"\s*[/|]\s*", s)[0].strip(" ,.-")
    s = BRAND_ALIASES.get(s, s)
    if not s or s in NULL_BRANDS or len(s) > 40 or re.fullmatch(r"[\d\W]+", s):
        return None
    return s


def valid_gtin(s):
    d = re.sub(r"\D", "", str(s or ""))
    if len(d) not in (8, 12, 13, 14):
        return None
    digits = [int(c) for c in d]
    check = (10 - sum(x * (3 if i % 2 == 0 else 1) for i, x in enumerate(reversed(digits[:-1])))) % 10
    return d.zfill(14) if check == digits[-1] else None


def norm_model(s, brand=None):
    if not s or not isinstance(s, str):
        return None
    s = fold(s)
    if brand:
        s = re.sub(rf"^{re.escape(brand)}\b", "", s).strip()
    m = re.sub(r"[\s\-_/.]", "", s).upper()
    if not m or len(m) > 30 or re.fullmatch(r"\d{7,}", m):  # long pure numbers are SKUs/EANs, not models
        return None
    return m


def model_from_title(title, brand):
    """First token containing a digit right after the brand: 'Olympus OM10 + ...' -> 'OM10'."""
    if not brand:
        return None
    toks = re.findall(r"[\w\-/.]+", title or "")
    first = brand.split()[0]
    for i, tok in enumerate(toks):
        if tok.lower() == first:
            for nxt in toks[i + len(brand.split()):i + len(brand.split()) + 2]:
                if re.search(r"\d", nxt) and not re.fullmatch(r"\d+([.,]\d+)?(mm|cm|m|gb|tb|mp|ml|l|g|kg|w|stk|pcs)?",
                                                             nxt, re.I):
                    return nxt
            return None
    return None


class BrandIndex:
    """Brands seen in the catalog, used to infer missing brands from titles and URLs."""

    def __init__(self, brands=()):
        self.counts = {}
        for b in brands:
            self.add(b)

    def add(self, brand, n=1):
        if brand:
            self.counts[brand] = self.counts.get(brand, 0) + n

    def infer(self, title, url):
        t = fold(title or "")
        path_slugs = {seg for seg in re.split(r"[/?&=]", unquote(urlparse(url or "").path.lower())) if seg}
        best = None
        for b, n in self.counts.items():
            if len(b) < 2:
                continue
            at_start = t.startswith(b + " ") or t == b
            anywhere = (len(b) >= 5 or " " in b) and n >= 2 and re.search(rf"(?<!\w){re.escape(b)}(?!\w)", t)
            in_url = slug(b) in path_slugs and len(b) >= 3
            if at_start or anywhere or in_url:
                if best is None or len(b) > len(best):
                    best = b
        return best


# ---------- spec values ----------

UNITS = {  # unit -> (dimension, factor to canonical unit)
    "mm": ("len", 1), "cm": ("len", 10), "m": ("len", 1000), "km": ("len", 1e6),
    "in": ("len", 25.4), "inch": ("len", 25.4), "tommer": ("len", 25.4), "tum": ("len", 25.4),
    "zoll": ("len", 25.4), '"': ("len", 25.4), "″": ("len", 25.4),
    "ml": ("vol", 1), "cl": ("vol", 10), "dl": ("vol", 100), "l": ("vol", 1000), "liter": ("vol", 1000),
    "litre": ("vol", 1000), "litres": ("vol", 1000),
    "mg": ("mass", 0.001), "g": ("mass", 1), "gram": ("mass", 1), "kg": ("mass", 1000), "kilograms": ("mass", 1000),
    "lb": ("mass", 453.6), "lbs": ("mass", 453.6), "kgs": ("mass", 1000), "tommers": ("len", 25.4),
    "kb": ("data", 1e-6), "mb": ("data", 0.001), "gb": ("data", 1), "tb": ("data", 1000),
    "w": ("power", 1), "kw": ("power", 1000), "mah": ("charge", 1), "v": ("volt", 1),
    "hz": ("freq", 1e-9), "khz": ("freq", 1e-6), "mhz": ("freq", 0.001), "ghz": ("freq", 1), "mp": ("mp", 1),
}
CANON_UNIT = {"len": "mm", "vol": "ml", "mass": "g", "data": "gb", "power": "w", "charge": "mah", "volt": "v",
              "freq": "ghz", "mp": "mp"}
QTY = re.compile(r"(\d+(?:[.,]\d+)?)\s*(" + "|".join(sorted((re.escape(u) for u in UNITS), key=len, reverse=True))
                 + r")(?![a-zà-ÿ])", re.I)
NUMERIC_KEYS = {"storage", "ram", "screen_size", "volume", "weight", "width", "height", "length", "power",
                "battery", "voltage"}
LETTER_SIZES = ["xxxs", "xxs", "xs", "s", "m", "l", "xl", "xxl", "xxxl", "xxxxl"]


def quantity(value, key=None):
    m = QTY.search(fold(value))
    if not m:
        return None
    num, unit = float(m.group(1).replace(",", ".")), m.group(2).lower()
    dim, factor = UNITS[unit]
    if key == "screen_size" and dim == "len":
        return round(num * factor / 25.4, 1), "inch"
    return round(num * factor, 3), CANON_UNIT[dim]


def fmt_num(n):
    return f"{n:g}"


def norm_size(v):
    s = fold(v)
    s = re.sub(r"^(str\.?|size|størrelse|storlek|größe|rozmiar)\s*:?\s*", "", s)
    s = re.sub(r"\s*-\s*int$|\(int\)", "", s).strip()
    if re.fullmatch(r"(one ?size|onesize|os|one-size|én størrelse|en storlek|ein größe)", s):
        return "one size"
    m = re.fullmatch(r"(\d)\s*xl", s)
    if m:
        return "x" * int(m.group(1)) + "l"
    if s in LETTER_SIZES:
        return s
    if m := re.fullmatch(r"(?:eu\s*)?(\d{2}(?:[.,]5)?)(?:\s*eu)?", s):
        return m.group(1).replace(",", ".")
    if m := re.fullmatch(r"w\s*(\d{2})\s*[/ ]?\s*l\s*(\d{2})", s):
        return f"w{m.group(1)} l{m.group(2)}"
    return s if len(s) <= 15 else None


def norm_condition(v):
    s = fold(v or "")
    if not s:
        return None
    if re.search(r"refurb|renoveret|rekonditioner|generalüberholt", s):
        return "refurbished"
    if re.search(r"used|brugt|begagnad|brukt|gebraucht|używan|second|vintage|pre-?owned|damaged", s):
        return "used"
    if re.search(r"new|ny\b|nyt|neu|now|nowy|nowa", s):
        return "new"
    return None


def norm_spec(key, value):
    """-> list of (key, value, num, unit). Several values for multi-valued attributes."""
    v = str(value).strip()
    if not v:
        return []
    if key == "color":
        cols = list(dict.fromkeys(COLOR_LEX.matches(v)))
        if cols:
            return [("color", c, None, None) for c in cols[:3]]
        return [("color", fold(v), None, None)] if len(v) <= 25 else []
    if key in ("material", "upper", "lining", "sole"):
        # order by percentage when given: "60% bomuld, 40% polyester"
        ordered = []
        for part in re.split(r"[,;/+]|\s(?:og|and|och|und|i|oraz)\s", v):
            pct = re.search(r"(\d{1,3})\s*%", part)
            ordered.append((int(pct.group(1)) if pct else 0, re.sub(r"\d{1,3}\s*%", "", part)))
        names = [n for _, n in sorted(ordered, key=lambda x: -x[0])]
        mats = list(dict.fromkeys(m for n in names for m in MATERIAL_LEX.matches(n)))
        if mats:
            return [(key, m, None, None) for m in mats[:3]]
        return [(key, fold(v), None, None)] if len(v) <= 25 else []
    if key == "gender":
        g = list(dict.fromkeys(GENDER_LEX.matches(v)))
        if len(g) > 1 and set(g) >= {"women", "men"}:
            return [("gender", "unisex", None, None)]
        return [("gender", g[0], None, None)] if g else []
    if key == "size":
        s = norm_size(v)
        return [("size", s, None, None)] if s else []
    if key == "condition":
        c = norm_condition(v)
        return [("condition", c, None, None)] if c else []
    if key == "age":
        m = re.search(r"(\d+)", v)
        return [("age", f"{m.group(1)}+", float(m.group(1)), "years")] if m else []
    if key in NUMERIC_KEYS or QTY.fullmatch(fold(v).replace("ca. ", "").strip()):
        q = quantity(v, key)
        if q:
            return [(key, f"{fmt_num(q[0])}{q[1]}", q[0], q[1])]
    s = fold(v)
    s = re.sub(r"(\d)\s+(?=[^\W\d_])", r"\1", s)  # "128 GB" -> "128gb"
    return [(key, s, None, None)] if len(s) <= 40 else []


def material_from_reversed(key, value):
    """'Bomuld: 100%' (material as label, percentage as value)."""
    if re.fullmatch(r"\s*\d{1,3}\s*%\s*", str(value)) and (m := MATERIAL_LEX.matches(key)):
        return m[0]
    return None


# ---------- departments ----------

def strip_colors(text):
    """Remove color words ('Dark Chocolate', 'Orange', 'Olive') before department matching."""
    return " ".join(t for t in tokens(text) if not COLOR_LEX.match_token(t))


class DepartmentClassifier:
    def __init__(self, embedder=None, threshold=0.33):
        self.embedder, self.threshold = embedder, threshold
        self._proto = None

    def keyword_scores(self, rec):
        scores = {}
        path_text = " ".join(rec.get("category_path") or []) + " " + (rec.get("category_raw") or "")
        url_path = re.sub(r"[-_/.?=&]+", " ", unquote(urlparse(rec.get("url") or "").path))
        # titles: the product noun usually comes first; variant info (color, size) after " - " / " | "
        title = rec.get("title") or ""
        head, _, tail = (re.split(r"(\s[-–|/]\s|,\s)", title, maxsplit=1) + ["", ""])[:3]
        for text, weight in ((path_text, 3), (strip_colors(head), 2), (strip_colors(tail), 0.7), (url_path, 1)):
            hits = DEPT_LEX.matches(text)
            for d in set(hits):
                scores[d] = scores.get(d, 0) + weight * hits.count(d) ** 0.5
        return scores

    def keyword_label(self, rec):
        """(department, clear) from keywords, or (None, False). `clear` = confident enough to train on."""
        ranked = sorted(self.keyword_scores(rec).items(), key=lambda x: -x[1])
        if not ranked:
            return None, False
        top, second = ranked[0][1], (ranked[1][1] if len(ranked) > 1 else 0.0)
        if (top >= 2 and top > second) or (top >= 0.7 and second == 0):
            return ranked[0][0], top >= 2 and top >= 1.5 * second
        return None, False

    def classify_many(self, recs):
        """Returns (department, method) per record; embedding fallback batched."""
        out, fallback = [None] * len(recs), []
        for i, r in enumerate(recs):
            sc = self.keyword_scores(r)
            ranked = sorted(sc.items(), key=lambda x: -x[1])
            if ranked and ranked[0][1] >= 2 and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
                out[i] = (ranked[0][0], "keywords")
            else:
                fallback.append(i)
        if fallback and self.embedder is not None:
            import numpy as np
            if self._proto is None:
                names = list(DEPARTMENTS)
                vecs = self.embedder.encode([DEPARTMENTS[n]["about"] for n in names], normalize_embeddings=True)
                self._proto = (names, np.asarray(vecs))
            names, protos = self._proto
            texts = [" ".join((recs[i].get("category_path") or [])[-3:] + [recs[i].get("category_raw") or "",
                                                                          recs[i].get("title") or ""]) for i in fallback]
            vecs = np.asarray(self.embedder.encode(texts, normalize_embeddings=True, batch_size=64))
            sims = vecs @ protos.T
            for row, i in enumerate(fallback):
                kw = self.keyword_scores(recs[i])
                for d, s in kw.items():  # keyword evidence still counts as a tie-breaker
                    sims[row, names.index(d)] += 0.05 * s
                j = int(sims[row].argmax())
                out[i] = (names[j], "embedding") if sims[row, j] >= self.threshold else ("other", "none")
        for i in range(len(out)):
            out[i] = out[i] or ("other", "none")
        return out


class DepartmentModel:
    """Self-trained fallback: logistic regression on listing embeddings, trained on listings whose
    department the keywords determined confidently. Used only for listings keywords can't place."""

    def __init__(self, min_confidence=0.5):
        self.min_confidence, self.clf = min_confidence, None

    def fit(self, X, y):
        from collections import Counter
        from sklearn.linear_model import LogisticRegression
        counts = Counter(y)
        keep = [i for i, label in enumerate(y) if counts[label] >= 5]  # need a few examples per class
        if len({y[i] for i in keep}) < 2:
            return self
        self.clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")
        self.clf.fit([X[i] for i in keep], [y[i] for i in keep])
        return self

    def predict(self, X):
        """-> list of (department, confidence); 'other' when not confident."""
        if self.clf is None or len(X) == 0:
            return [("other", 0.0)] * len(X)
        proba = self.clf.predict_proba(X)
        out = []
        for row in proba:
            j = int(row.argmax())
            out.append((self.clf.classes_[j], float(row[j])) if row[j] >= self.min_confidence
                       else ("other", float(row[j])))
        return out


# ---------- record normalization ----------

def infer_gender(rec):
    texts = [" ".join(rec.get("category_path") or []), rec.get("title") or "",
             re.sub(r"[-_/]+", " ", urlparse(rec.get("url") or "").path)]
    for t in texts:
        g = set(GENDER_LEX.matches(t))
        if len(g) == 1:
            return g.pop()
        if {"women", "men"} <= g:
            return "unisex"
    return None


def normalize(rec, fx, brands: BrandIndex, department):
    """rec: output of extraction.extract(); department: from DepartmentClassifier."""
    brand = norm_brand(rec.get("brand_raw")) or norm_brand(rec.get("manufacturer_raw")) \
        or brands.infer(rec.get("title"), rec.get("url"))
    gtin = valid_gtin(rec.get("gtin_raw"))
    model_raw = rec.get("model_raw")
    if not gtin and valid_gtin(model_raw):  # "model" that is really an EAN
        gtin, model_raw = valid_gtin(model_raw), None
    model = norm_model(model_raw, brand)
    if not model and department in TECH_DEPARTMENTS:
        model = norm_model(model_from_title(rec.get("title"), brand), brand)

    specs, seen = [], set()
    for k, v in (rec.get("specs_raw") or {}).items():
        if (mat := material_from_reversed(k, v)):
            k, v = "material", mat
        for key, val, num, unit in norm_spec(k, v):
            if (key, val) not in seen and len(specs) < 30:
                seen.add((key, val))
                specs.append({"key": key, "value": val, "num": num, "unit": unit,
                              "w": SPEC_WEIGHTS.get(key, DEFAULT_SPEC_WEIGHT)})
    if department in GENDERED_DEPARTMENTS and not any(s["key"] == "gender" for s in specs):
        if g := infer_gender(rec):
            specs.append({"key": "gender", "value": g, "num": None, "unit": None, "w": SPEC_WEIGHTS["gender"]})

    price = parse_price(rec.get("price_raw"))
    currency = norm_currency(rec.get("currency"), rec.get("source")) if price else None
    rate = fx.get(currency) if currency else None
    category = fold(rec["category_raw"]) if rec.get("category_raw") else None

    out = {
        "url": rec["url"], "file": rec.get("file"), "source": rec["source"], "title": rec.get("title") or "",
        "description": rec.get("description") or "", "manufacturer": brand, "model": model, "gtin": gtin,
        "category": category[:60] if category else None,
        "category_path": [fold(c) for c in rec.get("category_path") or []][:6],
        "department": department, "price": price, "currency": currency,
        "price_eur": round(price / rate, 2) if price and rate else None,
        "availability": rec.get("availability") or "Unknown",
        "condition": norm_condition(rec.get("condition_raw")), "specs": specs,
    }
    out["embed_text"] = embed_text(out)
    return out


def embed_text(i):
    specs = " ".join(f"{s['key']}:{s['value']}" for s in i["specs"] if s["key"] not in ("size",))
    # no department here: the same embedding trains/feeds the department classifier
    return " ".join(filter(None, [i["manufacturer"], i["model"], i["title"], " > ".join(i["category_path"]),
                                  i["category"], specs, i["description"][:300]]))
