"""Site-agnostic product extraction from HTML pages (saved files, fetched or rendered pages).

Layers, most reliable first; each one only fills fields that are still empty:
  1. schema.org Product / ProductGroup (JSON-LD, microdata) + OpenGraph/meta tags
  2. label/value pairs harvested from the main content: <table> rows, <dl> lists, "Label: Value" lines,
     and name/value or labels/values pairs in embedded JSON (many sites ship item data that way)
Labels are mapped to canonical keys through vocab.LABEL_SYNONYMS ("Marka"/"Mærke"/"Brand" -> brand).

The result is *raw* (as found on the page). normalize.py turns it into canonical values
(colors, sizes, units, departments, EUR prices, brand inference from titles...).
"""
import html as htmllib
import re
from itertools import chain
from pathlib import Path
from urllib.parse import unquote, urlparse

import warnings

import extruct
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from vocab import IGNORED_LABELS, LABEL_TO_KEY

try:
    import lxml  # noqa: F401  (faster parser if available)
    PARSER = "lxml"
except ImportError:
    PARSER = "html.parser"

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BLOCK_PAGE = re.compile(r"pardon our interruption|access denied|just a moment|are you a robot|"
                        r"captcha|attention required|robot check|client challenge|verify you are human|"
                        r"security check|request blocked|bot protection", re.I)

# Cheap test for "this HTML carries product data" (vs. a JavaScript shell that loads it later).
PRODUCT_SIGNALS = re.compile(r'"@type"\s*:\s*(?:"Product(?:Group)?"|\[[^\]]*"Product)|schema\.org/Product|'
                             r'og:type"\s+content="(?:og:)?product|product:price:amount|itemprop="price"', re.I)

# Value patterns that are contact/legal/opening-hours noise, never product attributes.
NOISE_VALUE = re.compile(r"@|https?://|www\.|^\+?\d[\d\s\-()]{6,}$|\b\d{1,2}[:.]\d{2}\s*[-–]\s*\d{1,2}[:.]\d{2}\b|"
                         r"\bcvr\b|\bmoms\b|\bvat\b|\d\s*:-|\brek\.? ?pris|\bpris\b|\bprice\b", re.I)
WEEKDAYS = re.compile(r"\b(man|tirs|ons|tors|fre|lør|søn|mån|tis|lör|sön|mon|tue|wed|thu|fri|sat|sun)"
                      r"(dag|day)?s?\b", re.I)
MONEY = re.compile(r"^(?:[€$£]\s?[\d.,]+|[\d\s.,]+\s?(?:eur|usd|pln|gbp|chf|dkk|sek|nok|kr\.?|zł|€|\$|£))$", re.I)
# Containers whose text is site chrome (menus, footers, cookie banners), not the product.
CHROME = re.compile(r"footer|header|\bnav|menu|cookie|consent|newsletter|breadcrumb|sidebar|banner|"
                    r"modal|popup|drawer|megamenu", re.I)
# Breadcrumbs that are navigation, not categories.
HOME_CRUMBS = {"home", "forside", "hem", "hjem", "start", "startside", "startsida", "startseite", "strona główna",
               "front page", "shop", "butik", "webshop", "alle produkter", "all products", "gå til forsiden",
               "tilbage", "back", "varumärken", "varemærker", "mærker", "brands", "merker", "marken", "producenter",
               "produsenter", "nyheter", "nyheder", "news", "nyt", "nytt", "new in", "alle styles", "alt det andet",
               "produktkatalog", "kollektion", "kollektioner", "collections", "kampagner", "tilbud", "erbjudanden",
               "udsalg", "rea", "sale", "outlet", "main", "køb her", "se også", "/", "›", ">", "»", "...", "…"}


class BlockedPage(Exception):
    """The HTML is a bot-check/captcha page, not a listing."""


def has_product_signals(html):
    return bool(PRODUCT_SIGNALS.search(html))


def decode_html(raw: bytes, declared=None):
    """UTF-8 if it decodes cleanly, else the declared/meta charset, else cp1252."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:4096])
    for enc in (declared, m.group(1).decode() if m else None, "cp1252"):
        if enc:
            try:
                return raw.decode(enc)
            except (LookupError, UnicodeDecodeError):
                continue
    return raw.decode("utf-8", errors="replace")


def clean(s):
    return re.sub(r"\s+", " ", htmllib.unescape(str(s))).strip(" : \t\n|") if s is not None else ""


def name_of(v):
    if isinstance(v, list):
        v = v[0] if v else None
    return v.get("name") if isinstance(v, dict) else v


def schema_enum(v):
    """'https://schema.org/UsedCondition' -> 'Used'; 'https://schema.org/InStock' -> 'InStock'."""
    return str(v).rsplit("/", 1)[-1].replace("Condition", "") if v else None


# ---------- layer 1: schema.org / meta ----------

def find_typed(items, *type_names):
    for it in items:
        if not isinstance(it, dict):
            continue
        if "@graph" in it and (p := find_typed(it["@graph"], *type_names)):
            return p
        t = it.get("@type")
        types = t if isinstance(t, list) else [t]
        if any(tn in types for tn in type_names):
            return it
    return None


def first_offer(offers):
    if isinstance(offers, list):
        offers = next((o for o in offers if isinstance(o, dict) and o.get("price") is not None),
                      offers[0] if offers else {})
    if not isinstance(offers, dict):
        return {}
    if isinstance(offers.get("offers"), list) and offers["offers"]:  # AggregateOffer with nested offers
        offers = {**offers["offers"][0], **{k: v for k, v in offers.items() if k != "offers"}}
    return offers


def pick_variant(group, url):
    """ProductGroup -> the variant matching this URL (else the first one), merged over the group."""
    variants = [v for v in (group.get("hasVariant") or []) if isinstance(v, dict)]
    if not variants:
        return group
    base = url.split("#")[0]
    chosen = next((v for v in variants if (first_offer(v.get("offers")).get("url") or v.get("url") or "")
                   .split("#")[0] == base), variants[0])
    merged = {**group, **{k: v for k, v in chosen.items() if v not in (None, "", [])}}
    for k in ("name", "brand", "category", "description"):  # group-level values are cleaner
        if group.get(k):
            merged[k] = group[k]
    merged["_variant"] = chosen
    return merged


def meta_content(soup, pattern):
    rx = re.compile(pattern, re.I)
    tag = soup.find("meta", attrs={"property": rx}) or soup.find("meta", attrs={"name": rx}) or \
        soup.find(attrs={"itemprop": rx})
    if not tag:
        return None
    return tag.get("content") or clean(tag.get_text())


def breadcrumbs(structured, soup):
    """Category trail, most general first, without the 'Home' crumb."""
    names = []
    if bc := find_typed(structured, "BreadcrumbList"):
        def pos(i):
            return int(i["position"]) if str(i.get("position", "")).isdigit() else 0
        for i in sorted((i for i in (bc.get("itemListElement") or []) if isinstance(i, dict)), key=pos):
            item = i.get("item")
            n = i.get("name") or (item.get("name") if isinstance(item, dict) else None)
            if n and not str(n).startswith("http"):
                names.append(clean(n))
    if not names:
        for nav in soup.select('[data-testid*="breadcrumb"], nav[aria-label*="readcrumb"], '
                               '[class*="breadcrumb"], ol[itemtype*="BreadcrumbList"]'):
            crumbs = [clean(a.get_text(" ")) for a in nav.find_all(["a", "span", "li"]) if not a.find(["a", "li"])]
            crumbs = [c for c in dict.fromkeys(crumbs) if c and len(c) < 60]
            if len(crumbs) > 1:
                names = crumbs
                break
    return [n for n in dict.fromkeys(names) if n.lower() not in HOME_CRUMBS and " - " not in n
            and not n.lower().startswith(("søgeresultater", "search results", "sökresultat", "resultater for"))]


def canonical_url(soup, product):
    link = soup.find("link", rel="canonical")
    og = soup.find("meta", property="og:url")
    for c in (link and link.get("href"), og and og.get("content"), product.get("url")):
        if c and str(c).startswith("http"):
            return str(c)
    return None


def category_from_value(cat):
    cat = name_of(cat)
    if not cat:
        return None
    cat = str(cat)
    if cat.startswith("http"):  # category given as a URL: use its last path segment if it looks like one
        seg = unquote(urlparse(cat).path.rstrip("/").rsplit("/", 1)[-1])
        seg = re.sub(r"\.\w+$|[-_]?\d{3,}.*$", "", seg).replace("-", " ").replace("_", " ").strip()
        return seg if seg and len(seg) < 50 else None
    parts = [p for p in re.split(r"\s*[>/|›»]\s*", cat) if p]
    return clean(parts[-1]) if parts else None


# ---------- layer 2: label/value harvesting ----------

NAME_VALUE = re.compile(r'"name":\s*"([^"]{1,40})"[^{}]{0,200}?"value":\s*"([^"]{1,80})"')
LABELS_VALUES = re.compile(r'"labels":\s*\[\{[^\]]*?"text":\s*"([^"]{1,40})"[^\]]*\]\s*\}\],\s*'
                           r'"values":\s*\[\{[^\]]*?"text":\s*"([^"]{1,80})"')


def in_chrome(el):
    for parent in el.parents:
        if parent.name in ("footer", "header", "nav", "aside", "form"):
            return True
        if parent.get("role") in ("contentinfo", "navigation", "banner", "dialog"):
            return True
        marker = " ".join(parent.get("class") or []) + " " + (parent.get("id") or "")
        if marker.strip() and CHROME.search(marker):
            return True
    return False


def pairs_from_dom(soup):
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if len(cells) == 2 and not in_chrome(tr):
            yield cells[0].get_text(" "), cells[1].get_text(" ")
    for dt in soup.find_all("dt"):
        if (dd := dt.find_next_sibling("dd")) and not in_chrome(dt):
            yield dt.get_text(" "), dd.get_text(" ")
    for el in soup.find_all(["p", "li"]):
        text = clean(el.get_text(" "))
        if len(text) < 120 and (m := re.match(r"^([^:]{2,40}):\s*(.+)$", text)) and not in_chrome(el):
            yield m.group(1), m.group(2)


def pairs_from_embedded_json(raw_html):
    text = raw_html.replace("\\\\", "\\").replace('\\"', '"').replace("\\/", "/")
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text).replace("\\/", "/")
    yield from NAME_VALUE.findall(text)
    yield from LABELS_VALUES.findall(text)


def harvest_pairs(soup, raw_html):
    """Returns {canonical_key: value}; the first occurrence of a key wins."""
    found = {}
    for label, value in chain(pairs_from_dom(soup), pairs_from_embedded_json(raw_html)):
        label, value = clean(label), clean(value)
        lk = label.lower().rstrip(".:")
        key = LABEL_TO_KEY.get(lk)
        if (not label or not value or lk in IGNORED_LABELS or len(value) > 80 or len(lk.split()) > 5
                or value.startswith(("/", "{", "[")) or NOISE_VALUE.search(value) or NOISE_VALUE.search(lk)
                or not re.search(r"[^\W\d_]", lk) or (MONEY.match(value) and key is None)
                or (key is None and len(value.split()) > 4)  # unknown label + sentence = marketing copy
                or (key is None and (re.search(r"\d", lk) or WEEKDAYS.search(lk)))):  # dates, opening hours
            continue
        found.setdefault(key or lk, value)
    return found


# ---------- main entry ----------

def extract(raw_html, url):
    soup = BeautifulSoup(raw_html, PARSER)
    structured = []
    try:
        data = extruct.extract(raw_html, base_url=url, syntaxes=["json-ld", "microdata"], uniform=True)
        structured = data.get("json-ld", []) + data.get("microdata", [])
    except Exception:
        pass  # malformed structured data: fall through to the other layers
    p = find_typed(structured, "Product", "ProductGroup", "IndividualProduct", "ProductModel") or {}
    if p.get("hasVariant"):
        p = pick_variant(p, url)
    page_title = clean(soup.title.get_text()) if soup.title else ""

    if not p and BLOCK_PAGE.search(page_title):
        raise BlockedPage(f"bot-check page ('{page_title}')")

    offer = first_offer(p.get("offers"))
    price_spec = offer.get("priceSpecification")
    price_spec = price_spec[0] if isinstance(price_spec, list) and price_spec else price_spec
    price = offer.get("price") or offer.get("lowPrice") or \
        (price_spec.get("price") if isinstance(price_spec, dict) else None) or \
        meta_content(soup, r"^(product|og):price:amount$|^price$")

    # specs: schema.org properties first, then harvested label/value pairs
    specs = {}
    props = p.get("additionalProperty") or []
    for s in [props] if isinstance(props, dict) else props:
        if isinstance(s, dict) and s.get("name") and s.get("value") is not None:
            lk = clean(s["name"]).lower()
            if lk not in IGNORED_LABELS:
                specs.setdefault(LABEL_TO_KEY.get(lk, lk), clean(s["value"]))
    for field, key in (("color", "color"), ("size", "size"), ("material", "material"), ("pattern", "pattern"),
                       ("weight", "weight"), ("width", "width"), ("height", "height"), ("depth", "length")):
        v = p.get(field)
        v = (v.get("value") or v.get("name")) if isinstance(v, dict) else name_of(v)
        if v:
            specs.setdefault(key, clean(v))
    if isinstance(p.get("audience"), dict) and p["audience"].get("suggestedGender"):
        specs.setdefault("gender", clean(p["audience"]["suggestedGender"]))
    for k, v in harvest_pairs(soup, raw_html).items():
        specs.setdefault(k, v)

    crumbs = breadcrumbs(structured, soup)
    canonical = canonical_url(soup, p)
    parsed = urlparse(canonical or url)

    title = clean(p.get("name") or meta_content(soup, r"^og:title$") or page_title)
    if not title or title.startswith("http"):
        h1 = soup.find("h1")
        title = clean(h1.get_text(" ")) if h1 else ""

    variant = p.get("_variant") or {}
    return {
        "url": canonical or url,
        "file": url if url.startswith("file:") else None,
        "source": parsed.netloc.lower().removeprefix("www.") if parsed.netloc
        else (Path(parsed.path).parent.name or "local"),
        "title": title,
        "description": clean(p.get("description") or meta_content(soup, r"^(og:)?description$"))[:1000],
        "brand_raw": name_of(p.get("brand")) or specs.pop("brand", None),
        "manufacturer_raw": name_of(p.get("manufacturer")) or specs.pop("manufacturer", None),
        "model_raw": name_of(p.get("model")) or p.get("mpn") or offer.get("mpn") or specs.pop("model", None),
        "gtin_raw": next((str(p[k]) for k in ("gtin", "gtin13", "gtin12", "gtin14", "gtin8") if p.get(k)), None)
        or offer.get("gtin") or offer.get("gtin13") or variant.get("gtin") or specs.pop("gtin", None),
        "category_path": crumbs,
        "category_raw": category_from_value(p.get("category")) or (crumbs[-1] if crumbs else None)
        or category_from_value(meta_content(soup, r"product:category")),
        "price_raw": price,
        "currency": offer.get("priceCurrency") or (price_spec.get("priceCurrency") if isinstance(price_spec, dict)
                                                   else None)
        or meta_content(soup, r"^(product|og):price:currency$|^priceCurrency$"),
        "availability": schema_enum(offer.get("availability"))
        or schema_enum(meta_content(soup, r"^product:availability$")) or "Unknown",
        "condition_raw": schema_enum(offer.get("itemCondition")) or specs.pop("condition", None),
        "specs_raw": {k: v for k, v in specs.items() if k not in ("sku", "brand", "manufacturer", "model", "gtin")},
        "has_structured": bool(p),
    }
