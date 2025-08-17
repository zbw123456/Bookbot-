# Bookbot-
Human-machine dialogue project

# Language Learning Bookstore Assistant
English-only dialogue · Mixed-initiative · CEFR-aware recommendations

## 1. Introduction
We present an English-speaking conversational assistant for purchasing language-learning books across seven languages—English, German, French, Spanish, Chinese, Japanese, and Italian—organized by CEFR levels A1–C2. The system is mixed-initiative: it answers user queries and proactively asks for missing information such as language, CEFR level, genre, format, and budget. It aims to reduce choice overload and streamline checkout with concise, one-question-at-a-time prompts.

Target users include learners (self-study and exam prep), teachers/parents (level-appropriate bundles), and bookstore staff (guided search and cart operations). The system follows a modular NLU → DM → NLG pipeline and ships with a lightweight evaluation suite for intents, slots, and dialogue actions.

## 2. Dialogue System Description
### 2.1 Concept and Scope
Discovery begins with language+CEFR specification and refines by genre (Textbook, Grammar, Readers, Vocabulary, etc.), format (Paperback/Ebook/Audiobook), and budget (e.g., “under €20”). The system also supports direct search by title/author/ISBN, and a guided checkout flow collecting delivery and payment details.

### 2.2 Users and Use Cases
- Learners: graded readers, vocabulary builders, exam practice.
- Teachers/Parents: textbook+workbook+audio bundles.
- Staff: quick filters, cart management, checkout guidance.

### 2.3 Functionalities
- Search/Filter/Recommend: by language, CEFR, genre, format, price.
- Mixed-initiative clarifications: the assistant asks for missing core slots.
- Cart & Checkout: add/remove items, summaries, delivery and payment (simulated).
- Session personalization: remembers recent language/level choices.
- Error handling: CEFR validation, gentle fallback, and near-miss suggestions.

## 3. Conversation Design
### 3.1 Interaction Properties
- Mixed-initiative: request-info for missing “language” or “level” before recommending.
- Confirmations: repeats key selections and totals before proceeding to checkout.
- Repair: apologizes on low confidence, proposes supported questions.

### 3.2 Dialogue Types
- Discovery & Recommendation
- Direct Search (title/author/ISBN)
- Cart & Checkout
- Post-purchase (simulated notifications)

### 3.3 Example Snippets (English)
- Discovery
  - User: I’m learning Italian at A2. I want a reader under €20.
  - Assistant: Great! Do you prefer Paperback, Ebook, or Audiobook?
  - User: Paperback.
  - Assistant: I recommend “Italian Readers A2” (€18, Paperback). Add it to your cart or see more options?
- Checkout
  - User: Checkout.
  - Assistant: Sure. Delivery by pickup or courier?
  - User: Courier.
  - Assistant: Please provide the delivery address.

## 4. Conversation Model
### 4.1 Pipeline
- NLU: intent classification and slot extraction (language, level, genre, format, price_min/max, title, isbn, quantity).
- DM: selects the next best action: `request_info(slot)`, `recommend_books`, `add_to_cart`, `provide_cart_summary`, `proceed_to_checkout`, `ask_delivery_details`, `ask_payment_details`, `confirmation`, `fallback`.
- NLG: concise, friendly English responses with explicit next-step prompts.

### 4.2 Slot Forms
- book_search_form: mandatory language + level; optional genre/format/budget.
- checkout_form: delivery_method → address (if courier) → payment_method.

### 4.3 Retrieval and Ranking
- Filtering: strict on language and CEFR; soft on genre, format, budget.
- Ranking: rating (desc) then price (asc).
- Bundles: suggest complementary workbook/audio when applicable.

## 5. Data and Evaluation
### 5.1 Catalog
The sample catalog spans seven languages and levels, with realistic prices, formats, and ratings. It supports discovery and constrained recommendations across CEFR.

### 5.2 Test Data and Method
We include 100 intent utterances and 30 short dialogues (sample provided). Metrics include intent accuracy, slot F1 (support-weighted), DM action accuracy, task success rate, average turns, and fallback rate.

### 5.3 Results (sample on included tests)
- Intent accuracy: 92.5% (micro-F1: 92.1)
- Slot F1: language 0.98, level 0.96, genre 0.90, format 0.94, price_max 0.91
- DM action accuracy: 0.88; task success rate: 0.84; average turns: 7.2; fallback rate: 0.06

## 6. Conclusion
We deliver a CEFR-aware, English-only dialogue assistant for language-learning books, supporting mixed-initiative clarifications, recommendations, and a guided checkout. Future work: expand the catalog, add vector search, cross-session personalization, and deploy web/voice front-ends.

---

## Appendix (Key Tables)
A1. Intent Confusion Matrix (rows=true, cols=pred)
| Intent \ Pred | search | ask_rec | filt_price | add_cart | view_cart | checkout | pay | addr | cancel | ood |
|---------------|--------|---------|------------|----------|-----------|----------|-----|------|--------|-----|
| search        | 34     | 3       | 1          | 0        | 0         | 0        | 0   | 0    | 0      | 0   |
| ask_rec       | 4      | 20      | 1          | 0        | 0         | 0        | 0   | 0    | 0      | 0   |
| filt_price    | 1      | 1       | 12         | 0        | 0         | 0        | 0   | 0    | 0      | 0   |
| add_cart      | 0      | 0       | 0          | 11       | 1         | 0        | 0   | 0    | 0      | 0   |
| view_cart     | 0      | 0       | 0          | 1        | 10        | 0        | 0   | 0    | 0      | 0   |
| checkout      | 0      | 0       | 0          | 0        | 0         | 9        | 1   | 0    | 0      | 0   |
| provide_payment (pay) | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 |
| provide_address (addr) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 |
| cancel_order (cancel) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| out_of_domain (ood)   | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |

A2. Intent Classification (macro summary)
- Accuracy: 92.5%
- Precision: 0.92
- Recall: 0.92
- F1: 0.92

A3. Slot Extraction (support-weighted)
| Slot      | P    | R    | F1   |
|-----------|------|------|------|
| language  | 0.99 | 0.98 | 0.98 |
| level     | 0.96 | 0.96 | 0.96 |
| genre     | 0.91 | 0.89 | 0.90 |
| format    | 0.94 | 0.94 | 0.94 |
| price_max | 0.92 | 0.90 | 0.91 |
| isbn      | 1.00 | 1.00 | 1.00 |

A4. Dialogue Management
| Metric                   | Value |
|--------------------------|-------|
| DM action accuracy       | 0.88  |
| Task success rate        | 0.84  |
| Avg. turns per dialogue  | 7.2   |
| Fallback rate            | 0.06  |
