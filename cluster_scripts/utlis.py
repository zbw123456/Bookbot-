import json, re
from typing import Dict, Any, List
from utils import rule_nlu, load_catalog, filter_books, rank_books, \
                  nlg_request_info, nlg_recommendations, nlg_cart_summary, dm_next_action

def add_to_cart_from_last(results: List[Dict[str,Any]], user_text: str, cart: Dict[str,int]):
    qty = 1
    m = re.search(r"\badd\s+(\d+)", user_text.lower())
    if m:
        try: qty = int(m.group(1))
        except: qty = 1
    m = re.search(r"\badd\s+(\d+)\b", user_text.lower())
    if m:
        idx = int(m.group(1)) - 1
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
    state = {
        "cart": {},
        "last_recommendations": [],
        "delivery_method": None,
        "address": None,
        "payment": None,
        "last_nlu": {}
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
        action = dm_next_action(state)

        if action["type"] == "request_info":
            print("Assistant:", nlg_request_info(action["slot"]))
            continue

        if action["type"] == "recommend_books":
            s = nlu["slots"]
            candidates = filter_books(
                catalog,
                language=s.get("language"),
                level=s.get("level"),
                genre=s.get("genre"),
                fmt=s.get("format"),
                price_min=s.get("price_min"),
                price_max=s.get("price_max")
            )
            ranked = rank_books(candidates)
            state["last_recommendations"] = ranked
            print("Assistant:", nlg_recommendations(ranked))
            continue

        if action["type"] == "add_to_cart":
            msg = add_to_cart_from_last(state["last_recommendations"], user, state["cart"])
            print("Assistant:", msg)
            print("Assistant:", nlg_cart_summary(state["cart"], catalog))
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
            print("Assistant:", nlg_cart_summary(state["cart"], catalog))
            continue

        if action["type"] == "proceed_to_checkout":
            if not state["cart"]:
                print("Assistant: Your cart is empty. Would you like recommendations first?")
                continue
            print("Assistant: Delivery by pickup or courier?")
            state["expecting_delivery"] = True
            continue

        if action["type"] == "ask_delivery_details":
            if "pickup" in user.lower():
                state["delivery_method"] = "pickup"
                print("Assistant: Noted pickup. Please provide your payment method (e.g., Visa/Mastercard).")
            else:
                state["delivery_method"] = "courier"
                print("Assistant: Please provide the delivery address.")
            continue

        if action["type"] == "ack_address":
            state["address"] = user
            print("Assistant: Address received. Please provide your payment method (e.g., Visa/Mastercard).")
            continue

        if action["type"] == "ack_payment":
            state["payment"] = user
            print("Assistant: Payment noted. Your order is confirmed. Order ID: ORD-" + str(abs(hash(user)) % 100000))
            continue

        if action["type"] == "confirmation":
            print("Assistant: Your request has been recorded.")
            continue

        if action["type"] == "help":
            print("Assistant: You can ask for books by language and level (e.g., 'Italian A2 reader under €20'), view cart, add to cart, or checkout.")
            continue

        print("Assistant: Sorry, I didn’t catch that. You can ask for recommendations, filter by format/price, manage cart, or checkout.")

if __name__ == "__main__":
    main()
