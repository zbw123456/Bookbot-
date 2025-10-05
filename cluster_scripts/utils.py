import json, re, csv
from typing import Dict, Any, List, Optional

# ---------------- NLU -----------------

LANGUAGES = {"english","german","french","spanish","italian","chinese","japanese"}
LEVELS = {"a1","a2","b1","b2","c1","c2"}
GENRES = {"textbook","readers","grammar","vocabulary"}
FORMATS = {"paperback","ebook","audiobook"}
LANG_TO_CODE = {
    "english": "en", "german": "de", "french": "fr", "spanish": "es",
    "italian": "it", "chinese": "zh", "japanese": "ja"
}

def _extract_price(text: str) -> Dict[str, Any]:
    text_l = text.lower()
    slots: Dict[str, Any] = {}
    # under/below <= max
    m = re.search(r"(under|below|<=?\s*|less than)\s*(€|euro)?\s*(\d+\.?\d*)", text_l)
    if m:
        try: slots["price_max"] = float(m.group(3))
        except: pass
    # over/above >= min
    m = re.search(r"(over|above|>=?\s*|more than)\s*(€|euro)?\s*(\d+\.?\d*)", text_l)
    if m:
        try: slots["price_min"] = float(m.group(3))
        except: pass
    # explicit range x-y
    m = re.search(r"(€|euro)?\s*(\d+\.?\d*)\s*[-~to]+\s*(€|euro)?\s*(\d+\.?\d*)", text_l)
    if m:
        try:
            lo, hi = float(m.group(2)), float(m.group(4))
            slots["price_min"], slots["price_max"] = min(lo, hi), max(lo, hi)
        except: pass
    return slots

def rule_nlu(text: str) -> Dict[str, Any]:
    t = text.strip()
    tl = t.lower()
    intent = "unknown"
    slots: Dict[str, Any] = {}

    # language
    for lang in LANGUAGES:
        if lang in tl:
            slots["language"] = lang.capitalize()
            break

    # level (generic)
    m = re.search(r"\b([abc][12])\b", tl)
    if m:
        slots["level"] = m.group(1).upper()
    # target/desired level overrides generic if phrased as need/want/aim for
    m_need = re.search(r"(need|want|aim|target)\s*(?:for|to)?\s*\b([abc][12])\b", tl)
    if m_need:
        slots["level"] = m_need.group(2).upper()

    # genre or skill intent (improve X)
    for g in GENRES:
        if g in tl:
            slots["genre"] = g.capitalize()
            break
    if "improv" in tl or "improve" in tl or "提升" in tl:
        if any(k in tl for k in ["vocab","vocabulary","词汇"]):
            slots["genre"] = "Vocabulary"
        elif any(k in tl for k in ["reading","reader","阅读"]):
            slots["genre"] = "Readers"
        elif any(k in tl for k in ["grammar","语法"]):
            slots["genre"] = "Grammar"

    # format
    for f in FORMATS:
        if f in tl:
            slots["format"] = f.capitalize()
            break

    slots.update(_extract_price(t))

    # intents
    if any(k in tl for k in ["add to cart","add "]):
        intent = "add_to_cart"
    elif any(k in tl for k in ["remove from cart","remove item"]):
        intent = "remove_from_cart"
    elif any(k in tl for k in ["show my cart","view cart","my cart"]):
        intent = "view_cart"
    elif any(k in tl for k in ["checkout","buy now","place order"]):
        intent = "checkout"
    elif any(k in tl for k in ["pickup","courier","delivery"]):
        intent = "choose_delivery"
    elif any(k in tl for k in ["how to send","send to me","shipping","ship to me","how to deliver","delivery method"]):
        intent = "choose_delivery"
    elif any(k in tl for k in ["pay with","visa","mastercard"]):
        intent = "provide_payment"
    elif any(k in tl for k in ["how to pay","how do i pay","how can i pay","payment methods"]):
        intent = "payment_help"
    elif any(k in tl for k in ["pay","payment"]):
        # generic pay intent → drive checkout flow
        intent = "checkout"
    elif any(k in tl for k in ["ship to","address"]):
        intent = "provide_address"
    elif any(k in tl for k in ["more","next","other books","others","another","show more","other"]):
        intent = "more_results"
    elif re.search(r"\bhelp\b", tl) or "what can you do" in tl:
        intent = "help"
    elif any(k in tl for k in ["thanks","thank you","thx","thank u","appreciate it"]):
        intent = "thanks"
    elif any(k in tl for k in ["ok","okay","ok.","ok!","great","nice"]):
        intent = "thanks"
    elif any(k in tl for k in ["goodbye","good bye","bye","see you","good night"]):
        intent = "farewell"
    elif any(k in tl for k in ["find","recommend","reader","textbook","grammar","vocabulary","search"]):
        # searching/recommendations
        intent = "ask_recommendation" if ("under" in tl or "below" in tl or "recommend" in tl) else "search_books"
    elif any(k in tl for k in ["below","under","cheaper","less than"]):
        intent = "filter_by_price"
    else:
        intent = "unknown"

    # If user provided any domain slots, treat as a search to engage slot-filling
    if intent == "unknown" and any(k in slots for k in ("language","level","genre","format","price_min","price_max")):
        intent = "search_books"

    return {"intent": intent, "slots": slots}

# ---------------- Data utils -----------------

def load_catalog(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_books_csv(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # normalize numeric fields
            try:
                r["price"] = float(r.get("price", 0))
            except:
                r["price"] = 0.0
            try:
                r["rating"] = float(r.get("rating", 0))
            except:
                r["rating"] = 0.0
            rows.append(r)
    return rows

def filter_books(catalog: List[Dict[str, Any]],
                 language: Optional[str] = None,
                 level: Optional[str] = None,
                 genre: Optional[str] = None,
                 fmt: Optional[str] = None,
                 price_min: Optional[float] = None,
                 price_max: Optional[float] = None) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for item in catalog:
        if language and item.get("language","" ).lower() != language.lower():
            continue
        if level and item.get("cefr","" ).upper() != level.upper():
            continue
        if genre and item.get("genre","" ).lower() != genre.lower():
            continue
        if fmt and fmt.capitalize() not in item.get("format", []):
            continue
        price = float(item.get("price", 0))
        if price_min is not None and price < price_min:
            continue
        if price_max is not None and price > price_max:
            continue
        results.append(item)
    return results

def rank_books(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(candidates, key=lambda x: (-float(x.get("rating", 0)), float(x.get("price", 0))))

def filter_books_csv(rows: List[Dict[str, Any]],
                     language: Optional[str] = None,
                     level: Optional[str] = None,
                     genre: Optional[str] = None,
                     fmt: Optional[str] = None,
                     price_min: Optional[float] = None,
                     price_max: Optional[float] = None) -> List[Dict[str, Any]]:
    lang_code = None
    if language:
        lang_code = LANG_TO_CODE.get(language.lower())
    topic = None
    if genre:
        g = genre.lower()
        if g == "textbook":
            topic = "coursebook"
        elif g == "grammar":
            topic = "grammar"
        elif g == "vocabulary":
            topic = "vocabulary"
        elif g == "readers":
            # many CSVs may not have readers; leave None to avoid over-filtering
            topic = None
    results: List[Dict[str, Any]] = []
    for r in rows:
        if lang_code and r.get("language") != lang_code:
            continue
        if level and r.get("cefr", "").upper() != level.upper():
            continue
        if topic and r.get("topic") != topic:
            continue
        if fmt and r.get("format", "").lower() != fmt.lower():
            continue
        price = float(r.get("price", 0))
        if price_min is not None and price < price_min:
            continue
        if price_max is not None and price > price_max:
            continue
        results.append(r)
    # rank similarly
    return sorted(results, key=lambda x: (-float(x.get("rating", 0)), float(x.get("price", 0))))

# ---------------- NLG -----------------

def nlg_request_info(slot: str) -> str:
    prompts = {
        "language": "Which language are you studying? (e.g., Italian, German)",
        "level": "Which CEFR level? (A1–C2)",
        "genre": "What type of book? (Textbook, Readers, Grammar, Vocabulary)",
        "format": "Preferred format? (Paperback, Ebook, Audiobook)",
        "price_max": "Any budget cap? For example, under €20."
    }
    return prompts.get(slot, "Could you provide more details?")

def _fmt_book(idx: int, b: Dict[str, Any]) -> str:
    return f"{idx}. {b['title']} — {b['language']} {b['cefr']} · {b['genre']} · {', '.join(b['format'])} · €{b['price']:.2f} (⭐{b.get('rating',0)})"

def nlg_recommendations(books: List[Dict[str, Any]]) -> str:
    if not books:
        return "I couldn't find matching books. Try relaxing filters (level/format/price)."
    lines = ["Here are some options:"] + [_fmt_book(i+1, b) for i, b in enumerate(books)]
    lines.append("Say 'Add 1' to add the first item to cart.")
    return "\n".join(lines)

def nlg_recommendations_from_csv(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    lines: List[str] = ["All relevant titles (from books_catalog.csv):"]
    for i, r in enumerate(rows, start=1):
        series = r.get("series") or "-"
        author = r.get("author") or "-"
        publisher = r.get("publisher") or "-"
        lang = r.get("language") or "-"
        cefr = r.get("cefr") or "-"
        topic = r.get("topic") or "-"
        learning_goal = r.get("learning_goal") or "-"
        fmt = r.get("format") or "-"
        price = float(r.get("price", 0))
        rating = float(r.get("rating", 0))
        lines.append(f"{i}. {r['title']} — {series} — {author} — {publisher} · {lang.upper()} {cefr} · {topic}/{learning_goal} · {fmt} · €{price:.2f} (⭐{rating:.1f})")
    lines.append("Say 'Add 1' to add the first item to cart.")
    return "\n".join(lines)

def csv_rows_to_items(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for r in rows:
        lang_code = r.get("language", "").lower()
        lang_name = None
        for name, code in LANG_TO_CODE.items():
            if code == lang_code:
                lang_name = name.capitalize()
                break
        genre = None
        topic = (r.get("topic") or "").lower()
        if topic == "coursebook":
            genre = "Textbook"
        elif topic == "grammar":
            genre = "Grammar"
        elif topic == "vocabulary":
            genre = "Vocabulary"
        else:
            genre = "Textbook"
        fmt = (r.get("format") or "").capitalize()
        isbn = "CSV-" + str(abs(hash(r.get("title","") + r.get("publisher",""))) % 10**10)
        items.append({
            "isbn": isbn,
            "title": r.get("title") or "Untitled",
            "language": lang_name or "",
            "cefr": (r.get("cefr") or "").upper(),
            "genre": genre,
            "format": [fmt] if fmt else [],
            "price": float(r.get("price", 0)),
            "publisher": r.get("publisher") or "",
            "year": 0,
            "rating": float(r.get("rating", 0)),
            "stock": 999
        })
    return items

def format_csv_lines_with_offset(rows: List[Dict[str, Any]], start_index: int) -> List[str]:
    lines: List[str] = []
    for i, r in enumerate(rows, start=start_index):
        series = r.get("series") or "-"
        author = r.get("author") or "-"
        publisher = r.get("publisher") or "-"
        lang = r.get("language") or "-"
        cefr = r.get("cefr") or "-"
        topic = r.get("topic") or "-"
        learning_goal = r.get("learning_goal") or "-"
        fmt = r.get("format") or "-"
        price = float(r.get("price", 0))
        rating = float(r.get("rating", 0))
        lines.append(f"{i}. {r['title']} — {series} — {author} — {publisher} · {lang.upper()} {cefr} · {topic}/{learning_goal} · {fmt} · €{price:.2f} (⭐{rating:.1f})")
    return lines

def nlg_cart_summary(cart: Dict[str, int], catalog: List[Dict[str, Any]]) -> str:
    if not cart:
        return "Your cart is empty."
    isbn_to_book = {b["isbn"]: b for b in catalog}
    lines: List[str] = []
    total = 0.0
    for isbn, qty in cart.items():
        b = isbn_to_book.get(isbn)
        if not b:
            continue
        line_total = float(b.get("price", 0)) * qty
        total += line_total
        lines.append(f"{b['title']} x{qty} — €{line_total:.2f}")
    lines.append(f"Total: €{total:.2f}")
    return "\n".join(lines)

# ---------------- DM policy -----------------

def dm_next_action(state: Dict[str, Any]) -> Dict[str, Any]:
    nlu = state.get("last_nlu", {})
    intent = nlu.get("intent")
    persistent_slots = state.get("slots", {})
    # combine for actions that need latest, but never lose persistent ones
    slots = dict(persistent_slots)
    for k, v in nlu.get("slots", {}).items():
        if v is not None:
            slots[k] = v

    # Decide next slot to request dynamically; if language missing, ask it first.
    # Otherwise, prefer asking for improvement area (genre) before CEFR level.
    required_order: List[str] = []
    if "language" not in persistent_slots:
        required_order.append("language")
    if "genre" not in persistent_slots:
        required_order.append("genre")
    if "level" not in persistent_slots:
        required_order.append("level")

    # --- Checkout flow priority ---
    cart = state.get("cart", {})
    expecting_delivery = state.get("expecting_delivery", False)
    if cart and len(cart) > 0 and (expecting_delivery or intent in ("checkout","choose_delivery","provide_address","provide_payment")):
        delivery_method = state.get("delivery_method")
        address = state.get("address")
        payment = state.get("payment")
        pickup_location = state.get("pickup_location")
        # If delivery not chosen yet
        if delivery_method is None:
            return {"type": "ask_delivery_details"}
        # If courier and no address yet, accept current utterance as address by default
        if delivery_method == "courier" and not address:
            if intent in ("provide_address", "unknown", "search_books", "ask_recommendation", "filter_by_price"):
                return {"type": "ack_address"}
            else:
                return {"type": "ask_delivery_details"}
        # If pickup and location not chosen yet
        if delivery_method == "pickup" and not pickup_location:
            if intent in ("unknown", "search_books", "ask_recommendation", "filter_by_price"):
                return {"type": "ack_pickup_location"}
            else:
                return {"type": "ask_pickup_location"}
        # If no payment yet
        if not payment:
            if intent == "provide_payment":
                return {"type": "ack_payment"}
            else:
                return {"type": "ask_payment"}

    # If user gave any domain-relevant info, proceed with slot filling even if intent is unknown
    if intent in ("ask_recommendation", "search_books", "filter_by_price", "unknown"):
        # Ask for missing info in dynamic order
        for s in required_order:
            if s not in persistent_slots:
                return {"type": "request_info", "slot": s}
        return {"type": "recommend_books"}

    if intent == "add_to_cart":
        return {"type": "add_to_cart"}

    if intent == "remove_from_cart":
        return {"type": "remove_from_cart"}

    if intent == "view_cart":
        return {"type": "provide_cart_summary"}

    if intent == "checkout":
        return {"type": "proceed_to_checkout"}

    if intent == "choose_delivery":
        return {"type": "ask_delivery_details"}

    if intent == "provide_address":
        return {"type": "ack_address"}

    if intent == "provide_payment":
        return {"type": "ack_payment"}

    if intent == "more_results":
        return {"type": "show_more_results"}

    if intent == "help":
        return {"type": "help"}

    if intent == "thanks":
        return {"type": "polite_ack"}

    if intent == "farewell":
        return {"type": "farewell"}

    if intent == "payment_help":
        return {"type": "payment_help"}

    # fallback
    return {"type": "help"}
