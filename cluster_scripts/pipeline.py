import json, re
from typing import Dict, Any, List
from utils import rule_nlu, load_catalog, filter_books, rank_books, load_books_csv, filter_books_csv, csv_rows_to_items, \
                  nlg_request_info, nlg_cart_summary, dm_next_action


def add_to_cart_from_last(results: List[Dict[str,Any]], user_text: str, cart: Dict[str,int]):
    # Default quantity is 1; interpret number after 'add' as index by default
    qty = 1
    text_l = user_text.lower()
    # Optional quantity like 'x3' or '3 copies'
    m_qty = re.search(r"x\s*(\d+)|\b(\d+)\s*(?:copies|qty)\b", text_l)
    if m_qty:
        qty = int(m_qty.group(1) or m_qty.group(2))
    # Index selection: 'add 2' means the 2nd item
    m_idx = re.search(r"\badd\s+(\d+)\b", text_l)
    if m_idx:
        idx = int(m_idx.group(1)) - 1
        if 0 <= idx < len(results):
            isbn = results[idx]["isbn"]
            cart[isbn] = cart.get(isbn, 0) + qty
            return f"Added “{results[idx]['title']}” (x{qty}) to your cart."
    if results:
        isbn = results[0]["isbn"]
        cart[isbn] = cart.get(isbn, 0) + qty
        return f"Added “{results[0]['title']}” (x{qty}) to your cart."
    return "I couldn’t find a referenced item to add."


def main():
    catalog = load_catalog("catalog.json")
    csv_rows = load_books_csv("database/books_catalog.csv")
    state = {
        "cart": {},
        "last_recommendations": [],
        "results_offset": 0,
        "delivery_method": None,
        "pickup_location": None,
        "address": None,
        "payment": None,
        "expecting_delivery": False,
        "order_confirmed": False,
        "last_nlu": {},
        "slots": {}
    }
    print("Assistant: Hi! I can recommend language-learning books by language and CEFR level. What are you studying?")
    while True:
        try:
            user = input("You: ").strip()
        except EOFError:
            break
        if user.lower() in ("quit","exit","bye"):
            print("Assistant: Bye! Have a great day!")
            break

        nlu = rule_nlu(user)
        state["last_nlu"] = nlu
        # Merge newly extracted slots into persistent state
        for k, v in nlu.get("slots", {}).items():
            if v is not None:
                state.setdefault("slots", {})[k] = v
        action = dm_next_action(state)

        if action["type"] == "request_info":
            print("Assistant:", nlg_request_info(action["slot"]))
            continue

        if action["type"] == "recommend_books":
            s = state.get("slots", {})
            lang = s.get("language")
            level = s.get("level")
            genre = s.get("genre")
            fmt = s.get("format")
            pmin = s.get("price_min")
            pmax = s.get("price_max")

            # Build attempts: exact → drop genre → adjacent level(s)
            attempts = []
            attempts.append((lang, level, genre, fmt))
            attempts.append((lang, level, None, fmt))
            # Adjacent level heuristic
            level_order = ["A1","A2","B1","B2","C1","C2"]
            if level in level_order:
                idx = level_order.index(level)
                neighbors = []
                if idx - 1 >= 0:
                    neighbors.append(level_order[idx-1])
                if idx + 1 < len(level_order):
                    neighbors.append(level_order[idx+1])
                for nb in neighbors:
                    attempts.append((lang, nb, genre, fmt))
                    attempts.append((lang, nb, None, fmt))

            chosen_filters = (lang, level, genre, fmt)
            candidates = []
            for L, Lv, G, F in attempts:
                candidates = filter_books(
                    catalog,
                    language=L,
                    level=Lv,
                    genre=G,
                    fmt=F,
                    price_min=pmin,
                    price_max=pmax
                )
                if candidates:
                    chosen_filters = (L, Lv, G, F)
                    break

            ranked = rank_books(candidates)
            # Also list all relevant titles from the CSV with the same filters
            csv_list = filter_books_csv(
                csv_rows,
                language=chosen_filters[0],
                level=chosen_filters[1],
                genre=(None if chosen_filters[2] is None else chosen_filters[2]),
                fmt=chosen_filters[3],
                price_min=pmin,
                price_max=pmax
            )
            csv_items = csv_rows_to_items(csv_list)
            combined = ranked + csv_items
            state["last_recommendations"] = combined
            state["results_offset"] = 0
            # Print unified list with continuous numbering
            print("Assistant: Here are all matching options:")
            for i, b in enumerate(combined, start=1):
                fmts = ", ".join(b.get("format", [])) if isinstance(b.get("format"), list) else str(b.get("format"))
                lang = b.get("language", "").strip()
                cefr = b.get("cefr", "").strip()
                genre = b.get("genre", "").strip()
                price = float(b.get("price", 0))
                rating = float(b.get("rating", 0))
                print("Assistant:", f"{i}. {b['title']} — {lang} {cefr} · {genre} · {fmts} · €{price:.2f} (⭐{rating})")
            print("Assistant:", "Say 'Add 1' to add the first item to cart.")
            continue
        if action.get("type") == "show_more_results":
            if not state["last_recommendations"]:
                print("Assistant: There are no previous results. Tell me what language/level/genre you need.")
                continue
            state["results_offset"] += 3
            remaining = state["last_recommendations"][state["results_offset"]:]
            if not remaining:
                print("Assistant: No more results. Try changing filters (e.g., price or format).")
                continue
            print("Assistant:", nlg_recommendations(remaining))
            continue

        if action["type"] == "add_to_cart":
            msg = add_to_cart_from_last(state["last_recommendations"], user, state["cart"])
            print("Assistant:", msg)
            # Use combined catalog including CSV-derived items so prices resolve
            combined_catalog = catalog + state.get("last_recommendations", [])
            print("Assistant:", nlg_cart_summary(state["cart"], combined_catalog))
            continue

        if action["type"] == "remove_from_cart":
            if state["cart"]:
                isbn, _ = next(iter(state["cart"].items()))
                state["cart"].pop(isbn, None)
                print("Assistant: Removed one item from your cart.")
            else:
                print("Assistant: Your cart is already empty.")
            continue

        if action["type"] == "provide_cart_summary":
            combined_catalog = catalog + state.get("last_recommendations", [])
            print("Assistant:", nlg_cart_summary(state["cart"], combined_catalog))
            continue

        if action["type"] == "proceed_to_checkout":
            if not state["cart"]:
                print("Assistant: Your cart is empty. Would you like recommendations first?")
                continue
            if state.get("delivery_method") is None:
                print("Assistant: Delivery by pickup or courier?")
                state["expecting_delivery"] = True
            elif state["delivery_method"] == "courier" and state.get("address") is None:
                print("Assistant: Please provide the delivery address.")
            elif state.get("payment") is None:
                print("Assistant: Please provide your payment method (e.g., Visa/Mastercard).")
            else:
                print("Assistant: Payment noted. Your order is confirmed. Order ID: ORD-" + str(abs(hash(str(state))) % 100000))
                # reset checkout flags for next session
                state["expecting_delivery"] = False
                state["order_confirmed"] = True
            continue

        if action["type"] == "ask_delivery_details":
            ul = user.lower()
            if "pickup" in ul:
                state["delivery_method"] = "pickup"
                state["expecting_delivery"] = True
                print("Assistant: Noted pickup. Choose a pickup location (e.g., DISI Helpdesk, Povo).")
            elif any(k in ul for k in ["courier","delivery","ship"]):
                state["delivery_method"] = "courier"
                state["expecting_delivery"] = True
                print("Assistant: Please provide the delivery address.")
            else:
                state["expecting_delivery"] = True
                print("Assistant: Delivery by pickup or courier?")
            continue

        if action["type"] == "ack_address":
            state["address"] = user
            print("Assistant: Address received. Please provide your payment method (e.g., Visa/Mastercard).")
            continue

        if action.get("type") == "ask_pickup_location":
            print("Assistant: Please choose a pickup location (e.g., DISI Helpdesk, Povo).")
            continue

        if action.get("type") == "ack_pickup_location":
            state["pickup_location"] = user
            print("Assistant: Pickup location noted. Please provide your payment method (e.g., Visa/Mastercard).")
            continue

        if action["type"] == "ack_payment":
            state["payment"] = user
            print("Assistant: Payment noted. Your order is confirmed. Order ID: ORD-" + str(abs(hash(user)) % 100000))
            state["expecting_delivery"] = False
            state["order_confirmed"] = True
            continue

        if action.get("type") == "ask_payment":
            print("Assistant: Please provide your payment method (e.g., Visa/Mastercard).")
            continue

        if action["type"] == "confirmation":
            print("Assistant: Your request has been recorded.")
            continue

        if action["type"] == "help":
            print("Assistant: You can ask for books by language and level (e.g., 'Italian A2 reader under €20'), view cart, add to cart, or checkout.")
            continue

        if action.get("type") == "payment_help":
            print("Assistant: You can pay during checkout using Visa or Mastercard. Say 'checkout' or 'pay' to start; after delivery choice and (if courier) address, provide the card brand like 'Visa'.")
            continue

        if action.get("type") == "polite_ack":
            if state.get("order_confirmed"):
                print("Assistant: You're welcome! Order confirmed. If you'd like to exit, type 'quit' or 'bye'.")
            else:
                print("Assistant: You're welcome! If you'd like to exit, type 'quit' or 'bye'.")
            continue

        if action.get("type") == "farewell":
            print("Assistant: Bye! Have a great day!")
            continue

        print("Assistant: Sorry, I didn’t catch that. You can ask for recommendations, filter by format/price, manage cart, or checkout.")

if __name__ == "__main__":
    main()
